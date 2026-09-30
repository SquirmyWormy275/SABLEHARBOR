"""Selected fictional Board envelope retains member actions and open challenge."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_gov_appetite_exercise as gov
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def _build(tmp_path, *, same_root=False):
    root = tmp_path / "selected-governance"
    repository = PRIVATE if same_root else REPOSITORY
    gov.create(root, repository=repository, private_repository=PRIVATE)
    return root


def test_nine_member_decision_precedes_bounded_ceo_delegation_and_open_messy_challenge(tmp_path):
    root = _build(tmp_path)
    receipt = gov.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
    assert {side: len(rows) for side, rows in receipt["selected_routes"].items()} == {
        "A": 16,
        "B": 16,
    }
    assert {side: len(rows) for side, rows in receipt["records"].items()} == {
        "CLEAN": 16,
        "MESSY": 18,
    }
    assert receipt["real_board_approval"] is receipt["audit_task_credit"] is False
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM versions ORDER BY rowid").fetchall()
        assert len(rows) == 34
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    assert all(row["imported_at"] < row["event_at"] == row["available_at"] for row in rows)
    by_branch = {
        branch: [r for r in rows if r["branch"] == branch]
        for branch in ("GOVAPP-CLEAN", "GOVAPP-MESSY")
    }
    for native in by_branch.values():
        votes = [r for r in native if r["system"] == "board_member_action"]
        assert len(votes) == 9
        assert {r["record"] for r in votes} == set(gov.DIRECTOR_IDS)
        bodies = [json.loads(r["content"]) for r in votes]
        assert sorted(body["vote"] for body in bodies) == ["DISSENT", *["SUPPORT"] * 8]
        assert all(
            body["simulated_member_attestation"] and not body["real_member_signature"]
            for body in bodies
        )
        board = next(r for r in native if r["system"] == "board_decision")
        board_body = json.loads(board["content"])
        assert board["event_at"] > max(r["event_at"] for r in votes)
        assert board_body["dissent_retained"] is True
        assert board_body["real_board_minutes_or_legal_validity"] is False
        assert {x["director_id"] for x in board_body["member_actions"]} == set(gov.DIRECTOR_IDS)
        delegation = next(r for r in native if r["system"] == "ceo_delegation")
        assert delegation["event_at"] > board["event_at"]
        assert json.loads(delegation["content"])["technical_configuration_authority"] == (
            "SEPARATE_SCOPED_APPROVAL_REQUIRED"
        )
    messy = {r["system"]: json.loads(r["content"]) for r in by_branch["GOVAPP-MESSY"]}
    assert messy["waiver_request"]["actual_key_bypass_open"] is True
    assert messy["security_challenge"]["original_challenge_retained"] is True
    assert messy["ceo_disposition"]["status"] == "WAIVER_DENIED_OVERSIGHT_ROUTING_REQUESTED_OPEN"
    assert messy["ceo_disposition"]["committee_acknowledgment"] is False
    assert messy["ceo_disposition"]["challenge_open"] is True
    assert messy["ceo_disposition"]["risk_acceptance"] is False


def test_resealed_erasure_of_director_dissent_fails_reperformance(tmp_path):
    root = _build(tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute(
            "SELECT content FROM versions WHERE branch='GOVAPP-CLEAN' "
            "AND system='board_member_action' AND record='DIR-CALDER'"
        ).fetchone()
        body = json.loads(row[0])
        body["vote"] = "SUPPORT"
        body["dissent_reason"] = None
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch='GOVAPP-CLEAN' "
            "AND system='board_member_action' AND record='DIR-CALDER'",
            (raw, digest),
        )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    for ref in receipt["records"]["CLEAN"]:
        if ref["system"] == "board_member_action" and ref["record"] == "DIR-CALDER":
            ref["sha256"] = digest
    (root / "RECEIPT.json").write_text(json.dumps(receipt, sort_keys=True))
    manifest = json.loads((root / "MANIFEST.json").read_text())
    manifest["receipt_sha256"] = hashlib.sha256((root / "RECEIPT.json").read_bytes()).hexdigest()
    manifest["company_db_sha256"] = hashlib.sha256(
        (root / "company.sqlite3").read_bytes()
    ).hexdigest()
    (root / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(CompanyStoreError, match="native action/authority/clock"):
        gov.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_missing_messy_issue_finding_cannot_support_waiver_disposition():
    _, _, _, directors, originals = gov._context(REPOSITORY, PRIVATE)
    del originals["MESSY"]["issue"]["issue_finding", "BOISE-KEY-BYPASS-SELECTED", 1]
    with pytest.raises(CompanyStoreError, match="original tuple missing"):
        gov._steps("MESSY", directors, originals["MESSY"])


def test_uncheckpointed_native_sidecar_is_rejected(tmp_path):
    root = _build(tmp_path)
    sidecar = root / "company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="three-file"):
        gov.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_main_root_can_hold_both_tracked_and_private_source_families(tmp_path):
    root = _build(tmp_path, same_root=True)
    receipt = gov.verify(root, repository=PRIVATE, private_repository=PRIVATE)
    assert len(receipt["records"]["CLEAN"]) == 16
    assert len(receipt["records"]["MESSY"]) == 18
    assert receipt["source_complete"] is False
