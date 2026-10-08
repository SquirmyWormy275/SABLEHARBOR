"""Selected fictional counsel docket keeps its native and legal boundaries."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_leg001_operating_docket_2027 as docket
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    root = tmp_path / "leg001"
    docket.create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


def _bodies(root):
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        return {
            (branch, system, record): json.loads(content)
            for branch, system, record, content in db.execute(
                "SELECT branch,system,record,content FROM versions"
            )
        }


def test_selected_counsel_population_and_exception_boundary(tmp_path):
    root = _build(tmp_path)
    receipt = docket.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
    bodies = _bodies(root)
    assert len(bodies) == 100
    assert {side: len(rows) for side, rows in receipt["records"].items()} == {
        "CLEAN": 50,
        "MESSY": 50,
    }
    assert {side: len(refs) for side, refs in receipt["selected_source_refs"].items()} == {
        "CLEAN": 5,
        "MESSY": 5,
    }
    assert len([key for key in bodies if key[1] == "term_status"]) == 68
    assert len([key for key in bodies if key[1] == "provision_status"]) == 16
    clean = bodies[("LEG-CLEAN", "reconciliation", "LEG001-SELECTED-RECON")]["detail"]
    messy = bodies[("LEG-MESSY", "reconciliation", "LEG001-SELECTED-RECON")]["detail"]
    assert clean["selected_scope_complete"] is True
    assert clean["open_historical_exception_ids"] == []
    assert messy["selected_scope_complete"] is False
    assert messy["open_historical_exception_ids"] == docket.OPEN_EXCEPTIONS
    assert all(
        body["real_hipaa_applicability"] == "UNDETERMINED"
        and body["actual_phi"] is False
        and body["audit_task_credit"] is False
        for body in bodies.values()
    )
    provisions = [body["detail"] for key, body in bodies.items() if key[1] == "provision_status"]
    assert sum(item["conditional_event_not_recurring_control"] for item in provisions) == 6
    assert all(item["not_applicable_conclusion"] is False for item in provisions)
    watches = [body["detail"] for key, body in bodies.items() if key[1] == "matter_watch"]
    assert len(watches) == 6
    assert all(
        item["outside_complaint_or_notice_nonoccurrence_asserted"] is False
        and item["all_company_or_external_matters_reconciled"] is False
        for item in watches
    )
    assert receipt["unsupported_authored_routes_per_side"] == 66
    assert receipt["source_complete"] is False


def test_upstream_review_pin_and_sidecar_are_frozen(tmp_path, monkeypatch):
    root = _build(tmp_path)
    review = docket.TRIAGE_REVIEW
    monkeypatch.setitem(docket.PRIVATE_PINS, review, "0" * 64)
    with pytest.raises(CompanyStoreError, match="private source differs"):
        docket.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
    monkeypatch.undo()
    sidecar = root / "company.sqlite3-wal"
    sidecar.write_bytes(b"active")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="three-file"):
        docket.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_resealed_false_legal_acceptance_is_rejected(tmp_path):
    root = _build(tmp_path)
    db_path = root / "company.sqlite3"
    with sqlite3.connect(db_path) as db:
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute(
            "SELECT content FROM versions WHERE branch='LEG-CLEAN' AND system='reconciliation'"
        ).fetchone()
        body = json.loads(row[0])
        body["detail"]["real_world_legal_conclusion"] = "ACCEPTED"
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch='LEG-CLEAN' "
            "AND system='reconciliation'",
            (raw, digest),
        )
    receipt_path = root / "RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    for ref in receipt["records"]["CLEAN"]:
        if ref["system"] == "reconciliation":
            ref["sha256"] = digest
    receipt_path.write_text(json.dumps(receipt, sort_keys=True))
    manifest_path = root / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    manifest["company_db_sha256"] = hashlib.sha256(db_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(CompanyStoreError, match="native content/clock/provenance differs"):
        docket.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
