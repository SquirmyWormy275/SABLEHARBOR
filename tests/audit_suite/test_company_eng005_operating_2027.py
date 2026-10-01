"""Selected fictional ENG005 source, exact causality and fail-closed provenance."""

import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_eng005_operating_2027 as source
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE_REPOSITORY = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def _created(tmp_path):
    destination = tmp_path / "eng005-source"
    source.create(destination, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
    return destination


def _bodies(destination):
    with sqlite3.connect(destination / "company.sqlite3") as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM versions ORDER BY branch,event_at").fetchall()
        assert all(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
            for table in ("grants", "collections", "access_events")
        )
        return {
            branch: {
                row["record"]: (json.loads(row["content"]), row)
                for row in rows
                if row["branch"] == branch
            }
            for branch in source.BRANCHES.values()
        }


def test_native_selected_population_and_causal_gates(tmp_path):
    destination = _created(tmp_path)
    assert source.verify(
        destination, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY
    ) == {
        "status": "VERIFIED_FICTIONAL_SELECTED_CHANGE_NO_AUDIT_CREDIT",
        "native_version_counts": {"CLEAN": 12, "MESSY": 22},
    }
    receipt = json.loads((destination / "RECEIPT.json").read_text())
    assert receipt["selected_population"] == ["CHG-RNO-MARKER-2027-01", "CHG-BOI-GATE-2027-02"]
    assert receipt["open_exception_counts"] == {"CLEAN": 0, "MESSY": 2}
    assert receipt["corporate_emergency_authority_status"] == "NOT_EVIDENCED_OPEN"
    assert receipt["historical_exercise_is_operating_source"] is False
    assert receipt["source_complete"] is receipt["audit_task_credit"] is False
    branches = _bodies(destination)
    clean = branches[source.BRANCHES["CLEAN"]]
    messy = branches[source.BRANCHES["MESSY"]]
    assert len(clean) == 12 and len(messy) == 22
    assert clean["ORD-TEST-INITIAL"][0]["passed_tests"] == ["SCHEMA", "BOUNDARY", "RECOVERY"]
    assert clean["ORD-TEST-INITIAL"][0]["test_results"] == {
        "SCHEMA": True,
        "BOUNDARY": True,
        "RECOVERY": True,
    }
    assert (
        clean["ORD-TEST-INITIAL"][0]["value_digests"]["tested_candidate"]
        == (clean["ORD-APPLY-APPROVED"][0]["value_digests"]["applied_value"])
    )
    assert clean["ORD-SECURITY-DECISION"][0]["actor_id"] == "AS-P008"
    assert (
        clean["ORD-APPLY-APPROVED"][0]["source_refs"]["ORD-RELEASE"]["sha256"]
        == (clean["ORD-RELEASE"][1]["sha256"])
    )
    assert clean["EMG-AUTHORITY-GATE"][0]["decision"] == "HOLD_NO_AUTHORITY"
    assert "EMG-INVALID-BYPASS" not in clean
    assert messy["ORD-TEST-INITIAL"][0]["release_gate_passed"] is False
    assert "RECOVERY" not in messy["ORD-TEST-INITIAL"][0]["test_results"]
    assert messy["ORD-SECURITY-DECISION"][0]["decision"] == "HOLD_MISSING_RECOVERY_TEST"
    assert messy["ORD-INVALID-APPLY"][0]["approval_gate_satisfied"] is False
    assert messy["ORD-ROLLBACK"][0]["restored_value"] == 30
    assert messy["ORD-TEST-CORRECTED"][0]["passed_tests"] == ["SCHEMA", "BOUNDARY", "RECOVERY"]
    assert messy["ORD-REVIEW"][0]["historical_exception_open"] is True
    assert messy["EMG-INVALID-BYPASS"][0]["authority_gate_satisfied"] is False
    assert messy["EMG-ROLLBACK"][0]["restored_value"] == 2
    assert (
        messy["EMG-ROLLBACK"][0]["value_digests"]["restored_value"]
        == (messy["EMG-REQUEST"][0]["baseline_config_sha256"])
    )
    assert messy["EMG-RETROSPECTIVE"][0]["independent_of_executor"] is True
    assert messy["EXC-ENG005-EMG-01"][0]["status"] == "OPEN"
    for branch in branches.values():
        for body, row in branch.values():
            assert row["event_at"] < row["available_at"]
            assert row["imported_at"] < "2027-01-01"
            assert body["real_deployment"] is body["actual_phi"] is False
            assert body["external_packets_or_writes"] == 0
            assert body["enterprise_policy_approved"] is body["audit_task_credit"] is False


def test_old_prospective_source_is_pinned_and_distinct(monkeypatch):
    monkeypatch.setattr(source, "HISTORICAL_SHA256", "0" * 64)
    with pytest.raises(CompanyStoreError, match="historical prospective exercise bytes"):
        source._context(REPOSITORY, PRIVATE_REPOSITORY)


def test_dated_office_identity_pin_fails_closed(monkeypatch):
    office_path = "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md"
    monkeypatch.setitem(source.CANON_SHA, office_path, "0" * 64)
    with pytest.raises(CompanyStoreError, match="source/canon bytes"):
        source._context(REPOSITORY, PRIVATE_REPOSITORY)


def test_transition_pin_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(source.sec.TRANSITION_PINS, "company.sqlite3", "0" * 64)
    with pytest.raises(CompanyStoreError, match="transition V3 bytes"):
        source._context(REPOSITORY, PRIVATE_REPOSITORY)


def test_receipt_tamper_and_sidecar_fail_closed(tmp_path):
    destination = _created(tmp_path)
    receipt_path = destination / "RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["open_exception_counts"]["MESSY"] = 0
    receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(CompanyStoreError, match="manifest/receipt"):
        source.verify(destination, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
    destination = source.create(
        tmp_path / "second-source", repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY
    )
    assert destination["native_version_count"] == 34
    sidecar = tmp_path / "second-source/company.sqlite3-wal"
    sidecar.symlink_to(tmp_path / "missing")
    with pytest.raises(CompanyStoreError, match="sidecar"):
        source.verify(
            tmp_path / "second-source", repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY
        )


def test_existing_destination_refused_without_rewriting_native_history(tmp_path):
    destination = _created(tmp_path)
    before = (destination / "company.sqlite3").read_bytes()
    with pytest.raises(CompanyStoreError, match="New private ENG005 destination"):
        source.create(destination, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
    assert (destination / "company.sqlite3").read_bytes() == before
