"""Focused provenance and causal checks for the prospective role review."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite import company_critical_role_2027_simulation as role
from enterprise.audit_suite.company_store import CompanyStoreError


def _context():
    selected = {}
    for scenario, branch in role.TRAINING_BRANCHES.items():
        rows = {}
        for system, record in (
            ("training_roster", "ROSTER-LOCAL-TRN-2027-01"),
            ("training_monitoring", "MONITOR-LOCAL-TRN-2027-01-1"),
            ("training_monitoring", "MONITOR-LOCAL-TRN-2027-01-2"),
            ("training_followup", "FOLLOWUP-LOCAL-TRN-2027-01"),
            ("training_completions", "LOCAL-TRN-2027-01-AS-P007-LOCAL-CHANGE"),
        ):
            rows[system, record] = {
                "ref": {
                    "company": role.COMPANY,
                    "branch": branch,
                    "system": system,
                    "record": record,
                    "version": 1,
                    "sha256": "a" * 64 if scenario == "CLEAN" else "b" * 64,
                    "event_at": "2027-02-03T11:00:00.000000+00:00",
                    "available_at": "2027-02-03T11:00:00.000000+00:00",
                    "imported_at": "2026-09-14T22:39:27.000000+00:00",
                }
            }
        selected[scenario] = rows
    return {
        "selected": selected,
        "role_projection": {"scoped": True},
        "role_projection_sha256": "c" * 64,
    }


def test_clean_messy_training_causality_stays_scoped():
    context = _context()
    clean = role._expected_rows(context, "CLEAN")
    messy = role._expected_rows(context, "MESSY")
    assert len(clean) == len(messy) == 4
    assert clean[1]["body"]["q1_initial_overdue_count"] == 0
    assert messy[1]["body"]["q1_initial_overdue_count"] == 1
    assert "followup" not in clean[1]["body"]["training_source"]
    assert "followup" in messy[1]["body"]["training_source"]
    for rows in (clean, messy):
        assert rows[1]["body"]["qualification_evidence_status"].endswith("VERIFICATION_PENDING")
        assert rows[1]["body"]["backup_evidence_status"].endswith("VERIFICATION_PENDING")
        assert rows[2]["body"]["training_lateness_is_competence_finding"] is False
        assert (
            rows[3]["body"]["action_status"] == "INTERNAL_VERIFICATION_QUEUED_NOT_SENT_OR_APPROVED"
        )
        assert all(r["available_at"] > r["event_at"] for r in rows)


def test_bounded_projection_is_revision_independent_and_pending():
    leadership = {
        "record_id": "SH-ENTERPRISE-PPL-20260913",
        "repository_acceptance_status": "DELEGATED_IMPLEMENTATION_PENDING_ACCEPTED_MERGE",
        "employment_start_dates": "NOT_ESTABLISHED",
        "people": [
            {
                "person_id": person,
                "org_role_id": role_id,
                "appointment_date": "2026-09-13",
                "employment_start": None,
                "source_acceptance": "DELEGATED_IMPLEMENTATION_PENDING_ACCEPTED_MERGE",
            }
            for person, role_id in {
                "AS-P006": "ROLE-32",
                **role.ROLES,
            }.items()
        ],
    }
    initial = role._role_projection(leadership)
    leadership["source_revision"] = "successor-commit"
    assert role._role_projection(leadership) == initial
    assert all(p["employment_start"] is None for p in initial["role_contacts"])
    leadership["people"][0]["employment_start"] = "2026-09-13"
    with pytest.raises(CompanyStoreError, match="contact facts"):
        role._role_projection(leadership)


def test_create_verify_and_tamper_fail_closed(tmp_path: Path, monkeypatch):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(role, "_input_context", lambda repository, training_root: _context())
    output = parent / "source"
    role.create(output, repository=tmp_path, training_root=tmp_path)
    assert (
        role.verify(output, repository=tmp_path, training_root=tmp_path)["source_version_count"]
        == 8
    )
    receipt = output / "RECEIPT.json"
    data = json.loads(receipt.read_text())
    assert data["actual_operation_eligibility_as_of_2026_09_29"] is False
    assert data["audit_task_credit"] is False
    data["q1_late_local_course_counts"]["MESSY"] = 0
    receipt.write_text(json.dumps(data))
    with pytest.raises(CompanyStoreError):
        role.verify(output, repository=tmp_path, training_root=tmp_path)


def test_dangling_sqlite_sidecar_is_rejected(tmp_path: Path):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    database = parent / "company.sqlite3"
    receipt = parent / "RECEIPT.json"
    database.write_bytes(b"frozen")
    receipt.write_bytes(b"{}")
    database.chmod(0o600)
    receipt.chmod(0o600)
    (parent / "company.sqlite3-wal").symlink_to("missing")
    with pytest.raises(CompanyStoreError, match="sidecar"):
        role._frozen({"database": database, "receipt": receipt})
