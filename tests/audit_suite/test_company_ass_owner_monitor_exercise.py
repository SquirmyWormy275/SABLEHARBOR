"""Selected owner self-assessment and local monitoring keep an open omission visible."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_ass_owner_monitor_exercise as ass
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def _build(tmp_path):
    root = tmp_path / "owner-monitor"
    ass.create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


def test_selected_self_assessment_and_second_line_challenge_are_bounded(tmp_path):
    root = _build(tmp_path)
    receipt = ass.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
    assert {side: len(rows) for side, rows in receipt["selected_routes"].items()} == {
        "A": 10,
        "B": 10,
    }
    assert {side: len(rows) for side, rows in receipt["records"].items()} == {
        "CLEAN": 3,
        "MESSY": 5,
    }
    assert receipt["source_complete"] is receipt["audit_task_credit"] is False
    assert receipt["independent_evaluation_completed"] is False
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM versions ORDER BY rowid").fetchall()
        assert len(rows) == 8
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    bodies = {
        (row["branch"], row["system"], row["version"]): json.loads(row["content"]) for row in rows
    }
    assert all(row["imported_at"] < row["event_at"] == row["available_at"] for row in rows)
    clean = bodies[("ASS12-CLEAN", "owner_self_assessment", 1)]
    assert clean["omitted_known_issue"] is False
    assert clean["corporate_certification_accepted"] is False
    messy_first = bodies[("ASS12-MESSY", "owner_self_assessment", 1)]
    messy_observation = bodies[("ASS12-MESSY", "second_line_observation", 1)]
    messy_correction = bodies[("ASS12-MESSY", "owner_self_assessment", 2)]
    escalation = bodies[("ASS12-MESSY", "monitoring_escalation", 1)]
    assert messy_first["omitted_known_issue"] is True
    assert messy_observation["owner_omission_detected"] is True
    assert messy_observation["independent_professional_assurance"] is False
    assert messy_correction["correction_does_not_erase_original"] is True
    assert (
        messy_correction["prior_submission_sha256"]
        == hashlib.sha256(
            json.dumps(messy_first, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    assert escalation["issue_open"] is True
    assert escalation["owner_or_governance_disposition"] == "PENDING"
    assert escalation["status"].endswith("NOT_ACCEPTED_OR_CLOSED")


def test_resealed_false_messy_disposition_fails_native_reperformance(tmp_path):
    root = _build(tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute(
            "SELECT content FROM versions WHERE branch='ASS12-MESSY' "
            "AND system='monitoring_escalation'"
        ).fetchone()
        body = json.loads(row[0])
        body["issue_open"] = False
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch='ASS12-MESSY' "
            "AND system='monitoring_escalation'",
            (raw, digest),
        )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    for ref in receipt["records"]["MESSY"]:
        if ref["system"] == "monitoring_escalation":
            ref["sha256"] = digest
    (root / "RECEIPT.json").write_text(json.dumps(receipt, sort_keys=True))
    manifest = json.loads((root / "MANIFEST.json").read_text())
    manifest["receipt_sha256"] = hashlib.sha256((root / "RECEIPT.json").read_bytes()).hexdigest()
    manifest["company_db_sha256"] = hashlib.sha256(
        (root / "company.sqlite3").read_bytes()
    ).hexdigest()
    (root / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(CompanyStoreError, match="native event, source or clock"):
        ass.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_uncheckpointed_output_sidecar_is_rejected(tmp_path):
    root = _build(tmp_path)
    sidecar = root / "company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="three-file"):
        ass.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_missing_selected_open_finding_cannot_yield_messy_observation():
    _, _, _, originals = ass._context(REPOSITORY, PRIVATE)
    messy = originals["MESSY"]
    del messy["issue"]["issue_finding", "BOISE-KEY-BYPASS-SELECTED", 1]
    with pytest.raises(CompanyStoreError, match="upstream tuple missing"):
        ass._steps("MESSY", messy)
