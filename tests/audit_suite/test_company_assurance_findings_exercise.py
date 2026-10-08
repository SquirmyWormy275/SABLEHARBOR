"""Selected company issue history keeps audit findings and closure separate."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite.company_assurance_findings_exercise import create, verify
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    root = tmp_path / "company-issues"
    create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


def test_clean_screen_and_messy_open_finding_with_overdue_route(tmp_path):
    root = _build(tmp_path)
    assert (
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)["native_version_count"] == 6
    )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert {side: len(ids) for side, ids in receipt["selected_route_task_ids"].items()} == {
        "A": 4,
        "B": 4,
    }
    assert {scenario: len(rows) for scenario, rows in receipt["records"].items()} == {
        "CLEAN": 1,
        "MESSY": 5,
    }
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM versions ORDER BY branch,event_at").fetchall()
        bodies = {(row["branch"], row["system"]): json.loads(row["content"]) for row in rows}
        assert len(rows) == 6
        assert all(row["imported_at"] < row["event_at"] == row["available_at"] for row in rows)
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    clean = bodies[("ISSUE-CLEAN", "issue_screening")]
    assert clean["status"] == "NO_SELECTED_DEFECT"
    assert clean["severity"] is None and clean["transition_bypass_exception_open"] is False
    assert {system for branch, system in bodies if branch == "ISSUE-CLEAN"} == {"issue_screening"}
    messy = {system: body for (branch, system), body in bodies.items() if branch == "ISSUE-MESSY"}
    assert messy["issue_finding"]["severity"] == "HIGH_LOCAL_PRELIMINARY"
    assert messy["owner_notification"]["technical_action_owner_person_id"] == "AS-P007"
    assert messy["owner_notification"]["security_oversight_person_id"] == "AS-P008"
    assert messy["remediation_request"]["status"] == "PLAN_REQUESTED_NOT_APPROVED"
    assert messy["remediation_request"]["technical_recovery_correction_observed"] is True
    assert messy["remediation_request"]["durable_bypass_prevention_implemented"] is False
    assert messy["overdue_escalation"]["status"] == "GOVERNANCE_ROUTING_REQUEST_NOT_REVIEWED"
    assert messy["overdue_escalation"]["governance_delivery_status"] == "QUEUED_NOT_ACKNOWLEDGED"
    assert (
        messy["overdue_escalation"]["event_at"]
        > messy["overdue_escalation"]["plan_response_due_at"]
    )
    assert all(body["transition_bypass_exception_open"] for body in messy.values())
    assert all(
        not body["finding_closed"]
        and not body["validation_performed"]
        and body["risk_acceptance"] == "NOT_PERFORMED"
        and body["governance_decision"] == "NOT_PERFORMED"
        and body["audit_task_credit"] is False
        and body["real_world_operation"] is False
        for body in bodies.values()
    )


def test_frozen_transition_sidecar_rejected(tmp_path):
    clone = tmp_path / "private-copy"
    clone.mkdir(mode=0o700)
    for relative in (
        "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3/MANIFEST.json",
        "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3/RECEIPT.json",
        "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3/company.sqlite3",
        "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/independent-review-v3/REVIEW.json",
        "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/run-v2/MATRIX.json",
        "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/independent-review-v2/REVIEW.json",
    ):
        path = clone / relative
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        shutil.copy2(PRIVATE / relative, path)
    sidecar = (
        clone / "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/"
        "run-v3/company.sqlite3-wal"
    )
    sidecar.write_bytes(b"uncheckpointed logical source")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="active sidecar"):
        create(tmp_path / "rejected", repository=REPOSITORY, private_repository=clone)


def test_resealed_false_closure_rejected(tmp_path):
    root = _build(tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute(
            "SELECT content FROM versions WHERE branch='ISSUE-MESSY' AND system='issue_finding'"
        ).fetchone()
        body = json.loads(row[0])
        body["finding_closed"] = True
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch='ISSUE-MESSY' "
            "AND system='issue_finding'",
            (raw, digest),
        )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    for ref in receipt["records"]["MESSY"]:
        if ref["system"] == "issue_finding":
            ref["sha256"] = digest
    (root / "RECEIPT.json").write_text(json.dumps(receipt, sort_keys=True))
    manifest = json.loads((root / "MANIFEST.json").read_text())
    manifest["receipt_sha256"] = hashlib.sha256((root / "RECEIPT.json").read_bytes()).hexdigest()
    manifest["company_db_sha256"] = hashlib.sha256(
        (root / "company.sqlite3").read_bytes()
    ).hexdigest()
    (root / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(CompanyStoreError, match="content or future clock"):
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)
