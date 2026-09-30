"""Bounded SEC-005 local fixture and negative provenance gates."""

import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_sec005_local_boundary_2027 as source
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE_REPOSITORY = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def _created(tmp_path):
    root = tmp_path / "run"
    source.create(root, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
    return root


def test_local_branch_causality_and_exact_native_clocks(tmp_path):
    root = _created(tmp_path)
    assert source.verify(root, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY) == {
        "status": "VERIFIED_LOCAL_NO_AUDIT_CREDIT",
        "native_version_counts": {"CLEAN": 5, "MESSY": 8},
    }
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert receipt["open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert receipt["network_packets_sent"] == receipt["executables_created_or_run"] == 0
    assert receipt["authored_sec005_clause_support"] is False
    assert receipt["audit_task_credit"] is False
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.row_factory = sqlite3.Row
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 13
        rows = db.execute(
            "SELECT branch,system,record,event_at,available_at,imported_at,content "
            "FROM versions ORDER BY branch,event_at"
        ).fetchall()
    by_branch = {side: [] for side in source.BRANCHES.values()}
    for row in rows:
        body = json.loads(row["content"])
        assert row["event_at"] < row["available_at"]
        assert row["imported_at"] < row["event_at"]
        assert body["actual_network_packets_sent"] == 0
        assert body["actual_executables_created_or_run"] == 0
        assert body["actual_phi_present"] is False
        assert body["audit_task_credit"] is False
        by_branch[row["branch"]].append(body)
    clean = by_branch[source.BRANCHES["CLEAN"]]
    messy = by_branch[source.BRANCHES["MESSY"]]
    assert next(x for x in clean if x["record"] == "EGRESS-ATTEMPT-01")["decision"] == (
        "DENIED_BY_LOCAL_SYMBOLIC_RULE"
    )
    assert next(x for x in messy if x["record"] == "EGRESS-ATTEMPT-01")["decision"] == (
        "STAGED_RULE_WOULD_ALLOW_GUARD_QUARANTINED"
    )
    assert (
        next(x for x in messy if x["record"] == "REVIEW-01")["open_historical_exception_id"]
        == "EXC-SIM-SEC005-LATE-RULE-RECONCILIATION"
    )
    assert next(x for x in messy if x["system"] == "local_exception")["status"] == (
        "OPEN_REVIEW_AND_PREVENTION_NOT_ACCEPTED"
    )
    assert all(
        x["decision"] == "DENIED_UNAPPROVED_LOCAL_DIGEST"
        for x in clean + messy
        if x["record"] == "INERT-CANDIDATE-01"
    )


def test_reviewed_route_clause_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(source.AUTHORED, "CHECK-SOC2:CC6.6", "weakened test")
    with pytest.raises(CompanyStoreError, match="route clause or status"):
        source._context(REPOSITORY, PRIVATE_REPOSITORY)


def test_dangling_native_sidecar_fails_closed(tmp_path):
    root = _created(tmp_path)
    (root / "company.sqlite3-wal").symlink_to(root / "missing-target")
    with pytest.raises(CompanyStoreError, match="sidecar"):
        source.verify(root, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)


def test_receipt_mutation_fails_closed(tmp_path):
    root = _created(tmp_path)
    receipt = root / "RECEIPT.json"
    data = json.loads(receipt.read_text())
    data["open_exception_counts"]["MESSY"] = 0
    receipt.write_text(json.dumps(data))
    with pytest.raises(CompanyStoreError, match="manifest/receipt"):
        source.verify(root, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
