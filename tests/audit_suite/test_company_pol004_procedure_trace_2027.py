"""Selected POL004 local trial must retain source lineage and unsupported status."""

import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_pol004_procedure_trace_2027 as trace
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
RUN_ROOT = REPOSITORY / "enterprise/generated/audit-suite/company-pol004-procedure-trace-2027-09-30"
RUN = next(
    (path for name in ("main-run-v1", "isolated-run-v1") if (path := RUN_ROOT / name).is_dir()),
    RUN_ROOT / "isolated-run-v1",
)


@pytest.fixture(scope="module")
def verified():
    return trace.verify(RUN, repository=REPOSITORY, private_repository=PRIVATE)


def test_exact_source_join_and_pending_authority(verified):
    assert verified["branch_counts"] == {"CLEAN": 7, "MESSY": 9}
    assert verified["native_count"] == 16
    assert verified["route_disposition"]["A"]["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    assert verified["route_disposition"]["B"]["current_conclusion"] == "NOT_RUN"
    assert verified["enterprise_policy_status_2026"] == "OPEN"
    assert verified["design_standard_approved_only"] is True
    assert verified["procedure_authority"] == "PENDING_AUTHORIZED_DECISION"
    for key in (
        "actual_operation",
        "full_policy_or_procedure_population",
        "source_complete",
        "audit_task_credit",
        "active_P1_mutated",
    ):
        assert verified[key] is False
    assert (
        verified["reviewed_private_sha256"][trace.SOURCE_REVIEW]
        == trace.PRIVATE_PINS[trace.SOURCE_REVIEW]
    )


def test_native_originals_and_causal_three_clocks(verified):
    source = json.loads((PRIVATE / trace.SOURCE_RUN / "RECEIPT.json").read_text())
    source_refs = {
        scenario: {row["record"]: trace._ref(row) for row in source["records"][scenario]}
        for scenario in trace.BRANCHES
    }
    with sqlite3.connect(
        (RUN / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 16
        for table in ("grants", "collections", "access_events"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        for scenario, branch in trace.BRANCHES.items():
            prior = None
            selected = [row for row in verified["native_originals"] if row["branch"] == branch]
            assert len(selected) == len(trace.PLAN[scenario])
            for original, (_, record, _, names) in zip(selected, trace.PLAN[scenario], strict=True):
                body = json.loads(
                    db.execute(
                        "SELECT content FROM versions WHERE company=? AND branch=? AND system=? "
                        "AND record=? AND version=1",
                        (original["company"], branch, original["system"], record),
                    ).fetchone()[0]
                )
                assert body["source_originals"] == {
                    name: source_refs[scenario][name] for name in names
                }
                assert all(
                    ref["available_at"] <= original["event_at"]
                    for ref in body["source_originals"].values()
                )
                assert body["previous_original"] == prior
                assert original["event_at"] <= original["available_at"]
                assert original["imported_at"].startswith("2026-")
                assert original["imported_at"] < original["event_at"]
                prior = trace._ref(original)


def test_false_close_correction_and_policy_only_rejection_are_retained(verified):
    with sqlite3.connect(
        (RUN / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        records = {}
        for branch, record, content in db.execute("SELECT branch,record,content FROM versions"):
            records[branch, record] = json.loads(content)
    clean = trace.BRANCHES["CLEAN"]
    messy = trace.BRANCHES["MESSY"]
    for branch in (clean, messy):
        gate = records[branch, "POLICY-ONLY-REJECT"]["detail"]
        assert gate["policy_only_sufficiency"] == "REJECTED"
        assert gate["v0_2_release_approved"] is False
        assert gate["effective_enterprise_procedure"] is False
    assert records[clean, "RESULT"]["detail"]["selected_result"] == "NO_SELECTED_VARIATION"
    assert records[messy, "FALSE-CLOSE"]["detail"]["valid"] is False
    assert records[messy, "CHALLENGE"]["prior_false_close"] == next(
        trace._ref(row)
        for row in verified["native_originals"]
        if row["branch"] == messy and row["record"] == "FALSE-CLOSE"
    )
    correction = records[messy, "CORRECTION"]["detail"]
    assert correction["false_close_corrected"] is True
    assert correction["false_close_erased"] is False
    assert correction["missed_interval_retained"] is True
    assert (
        records[messy, "EXPIRY-REVIEW"]["detail"]["exception_status"] == "OPEN_EXPIRED_UNAPPROVED"
    )
    assert records[messy, "FINAL"]["detail"]["authored_clause_satisfied"] is False


def test_review_drift_and_mismatched_source_verifier_fail_closed(monkeypatch):
    monkeypatch.setitem(trace.PRIVATE_PINS, trace.SOURCE_REVIEW, "0" * 64)
    with pytest.raises(CompanyStoreError, match="reviewed private pin differs"):
        trace._context(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    monkeypatch.setattr(trace.policy, "verify", lambda *args, **kwargs: {"wrong": True})
    with pytest.raises(CompanyStoreError, match="source verifier manifest differs"):
        trace._context(REPOSITORY, PRIVATE)


def test_existing_run_cannot_be_recreated():
    with pytest.raises(CompanyStoreError, match="Fresh ordinary private"):
        trace.create(RUN, repository=REPOSITORY, private_repository=PRIVATE)
