"""The fictional policy source preserves pending authority and missed distribution."""

import hashlib
import json
import os
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_policy_exception_2027_exercise as policy
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def _build(tmp_path: Path) -> Path:
    root = tmp_path / "policy-source"
    policy.create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


def test_pending_revision_local_distribution_and_open_generic_request(tmp_path):
    root = _build(tmp_path)
    receipt = json.loads((root / "RECEIPT.json").read_text())
    manifest = policy.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
    assert manifest["native_version_count"] == 19
    assert receipt["counts"] == {"CLEAN": 7, "MESSY": 12}
    assert receipt["open_generic_exception_ids"] == {
        "CLEAN": [],
        "MESSY": [policy.EXCEPTION_ID],
    }
    canonical = (REPOSITORY / policy.DOC).read_bytes()
    for scenario in policy.BRANCHES:
        for endpoint in policy.ENDPOINTS:
            assert (root / "copies" / scenario / f"{endpoint}.md").read_bytes() == canonical
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row

        def body(branch: str, record: str):
            row = db.execute(
                "SELECT content,event_at,available_at,imported_at FROM versions "
                "WHERE branch=? AND record=?",
                (branch, record),
            ).fetchone()
            assert row is not None
            assert row["imported_at"] < row["event_at"] < row["available_at"]
            return json.loads(row["content"]), row["event_at"]

        clean = policy.BRANCHES["CLEAN"]
        messy = policy.BRANCHES["MESSY"]
        clean_draft, _ = body(clean, "DRAFT")
        clean_review, _ = body(clean, "DRAFT-HOLD")
        clean_reconcile, _ = body(clean, "RECONCILE")
        assert clean_draft["status"] == "PENDING_AUTHORIZED_APPROVAL"
        assert clean_draft["effective_at"] is None
        assert clean_review["approval_granted"] is False
        assert clean_reconcile["on_time"] == list(policy.ENDPOINTS)
        assert clean_reconcile["missing_at_due"] == []

        false_release, release_at = body(messy, "FALSE-RELEASE")
        missed, missed_at = body(messy, "MISSED-AT-DUE")
        request, request_at = body(messy, "EXCEPTION-REQUEST")
        false_waiver, waiver_at = body(messy, "FALSE-WAIVER")
        quarantine, quarantine_at = body(messy, "QUARANTINE")
        late, late_at = body(messy, "DELIVER-SECURITY_LOCAL_QUEUE")
        followup, followup_at = body(messy, "LATE-RECONCILE")
        expiry, expiry_at = body(messy, "EXPIRY-ESCALATE")
        assert release_at < missed_at < request_at < waiver_at < quarantine_at < late_at
        assert late_at < followup_at < expiry_at
        assert false_release["claimed_release_invalid"] is True
        assert missed["missing_at_due"] == ["SECURITY_LOCAL_QUEUE"]
        assert request["approver_id"] is None
        assert request["actual_waiver_effective"] is False
        assert request["addressable_measure_decision"] is False
        assert false_waiver["valid"] is False
        assert quarantine["legal_or_risk_approval_granted"] is False
        assert late["on_time"] is False
        assert followup["missing_at_due"] == ["SECURITY_LOCAL_QUEUE"]
        assert expiry["exception_status"] == "OPEN_EXPIRED_UNAPPROVED"
        assert expiry["waiver_ever_effective"] is False
        assert all(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
            for table in ("grants", "collections", "access_events")
        )


def test_copy_tampering_and_dangling_sqlite_sidecar_fail_closed(tmp_path):
    root = _build(tmp_path)
    copy = root / "copies/CLEAN/RISK_LOCAL_QUEUE.md"
    original = copy.read_bytes()
    copy.write_bytes(original + b"\n")
    with pytest.raises(CompanyStoreError):
        policy.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
    copy.write_bytes(original)
    sidecar = root / "company.sqlite3-wal"
    os.symlink(root / "missing-wal", sidecar)
    with pytest.raises(CompanyStoreError, match="SQLite sidecar"):
        policy._frozen(root / "company.sqlite3")
    with pytest.raises(CompanyStoreError):
        policy.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_ledger_rejoins_22_exact_frozen_tasks_per_side():
    ledger = json.loads((REPOSITORY / policy.LEDGER).read_text())
    route = json.loads((PRIVATE / ledger["source_paths"]["routes"]).read_text())
    screen = json.loads((PRIVATE / ledger["source_paths"]["screen"]).read_text())["rows"]
    screen_by_key = {(x["side"], x["task_id"]): x for x in screen}
    selected = [x for x in route if x.get("control_id") in {f"SH-POL-00{n}" for n in range(1, 5)}]
    assert len(selected) == len(ledger["rows"]) == 44
    assert {(x["side"], x["task_id"]) for x in selected} == {
        (x["side"], x["task_id"]) for x in ledger["rows"]
    }
    assert all(
        row["authored_test_clause"] == screen_by_key[row["side"], row["task_id"]]["test_clause"]
        and row["audit_task_credit"] is False
        for row in ledger["rows"]
    )


def test_resealed_false_waiver_cannot_pass_native_reperformance(tmp_path):
    root = _build(tmp_path)
    db_path = root / "company.sqlite3"
    with sqlite3.connect(db_path) as db:
        db.execute("DROP TRIGGER no_version_update")
        old = db.execute(
            "SELECT content FROM versions WHERE branch=? AND record='EXCEPTION-REQUEST'",
            (policy.BRANCHES["MESSY"],),
        ).fetchone()[0]
        body = json.loads(old)
        body["actual_waiver_effective"] = True
        altered = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        altered_sha = hashlib.sha256(altered).hexdigest()
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch=? AND record='EXCEPTION-REQUEST'",
            (altered, altered_sha, policy.BRANCHES["MESSY"]),
        )
    receipt_path = root / "RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    for ref in receipt["records"]["MESSY"]:
        if ref["record"] == "EXCEPTION-REQUEST":
            ref["sha256"] = altered_sha
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    manifest_path = root / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    manifest["company_db_sha256"] = hashlib.sha256(db_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    with pytest.raises(CompanyStoreError, match="Policy native content"):
        policy.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
