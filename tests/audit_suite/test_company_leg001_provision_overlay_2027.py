"""The selected counsel locator overlay cannot turn a legal reference into audit credit."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_leg001_provision_overlay_2027 as source
from enterprise.audit_suite import leg001_66_candidate_gap as gap

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
ROOT = REPOSITORY / "enterprise/generated/audit-suite/company-leg001-provision-overlay-2027-10-01"
RUN = ROOT / "isolated-run-v4"
GAP_STEM = REPOSITORY / "enterprise/audit_suite/LEG001_66_CANDIDATE_GAP_2026-10-01"


@pytest.fixture(scope="module")
def context():
    return source._context(REPOSITORY, PRIVATE)


@pytest.fixture(scope="module")
def receipt():
    return source.verify(RUN, repository=REPOSITORY, private_repository=PRIVATE)


def test_predecessor_native_join_and_branch_isolation(context):
    assert context["freeze"] == source.P1_FREEZE
    for scenario, branch, open_ids in (
        ("CLEAN", "LEG-CLEAN", []),
        ("MESSY", "LEG-MESSY", source.OPEN_EXCEPTIONS),
    ):
        refs = context["refs"][scenario]
        assert len(refs["terms"]) == 34
        assert refs["open_exception_ids"] == open_ids
        assert all(row["branch"] == branch for row in refs["terms"])
        assert refs["scope"]["branch"] == refs["reconciliation"]["branch"] == branch
        if open_ids:
            assert refs["exception_refs"]["ba_flowdown"]["branch"] == "PHI-MESSY"
            assert all(
                ref["branch"] == "LIFE-MESSY"
                for name, ref in refs["exception_refs"].items()
                if name.startswith("provider_support_")
            )
        else:
            assert not refs["exception_refs"]


def test_exact_native_versions_three_clocks_and_no_credit(receipt):
    assert receipt["bounded_authored_provision_candidates_per_side"] == 16
    assert receipt["remaining_unmodeled_authored_candidates_per_side"] == 50
    assert receipt["provision_locator_count_per_branch"] == 18
    assert receipt["selected_term_count_per_branch"] == 34
    assert receipt["open_historical_exception_ids"] == {
        "CLEAN": [],
        "MESSY": source.OPEN_EXCEPTIONS,
    }
    assert receipt["real_hipaa_applicability"] == "UNDETERMINED"
    assert receipt["2027_legal_text_verified"] is False
    assert receipt["actual_phi"] is receipt["real_contract_executed"] is False
    assert receipt["outside_message_sent"] is receipt["audit_task_credit"] is False
    assert receipt["source_complete"] is False
    assert RUN.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in RUN.iterdir())
    with sqlite3.connect(f"file:{RUN / 'company.sqlite3'}?mode=ro&immutable=1", uri=True) as db:
        rows = db.execute(
            "SELECT branch,system,record,version,event_at,available_at,imported_at,content "
            "FROM versions"
        ).fetchall()
    assert len(rows) == 40
    for branch, system, record, version, event, available, imported, content in rows:
        assert branch in {"LEGOV-CLEAN", "LEGOV-MESSY"}
        assert version == 1
        assert event.startswith("2027-12-31")
        assert available > event
        assert imported < "2027-01-01"
        assert b"TASK-SH-LEG" not in content
        assert json.loads(content)["audit_task_credit"] is False
        assert record and system


def test_provision_decisions_separate_locator_trigger_contract_and_performance(context):
    for scenario in ("CLEAN", "MESSY"):
        steps = source._steps(context, scenario)
        assert len(steps) == 20
        details = [
            body["detail"] for system, _, _, _, body in steps if system == "provision_locator"
        ]
        assert len(details) == 18
        assert {detail["provision"]["id"] for detail in details} == {
            row["id"] for row in context["spec"]["provisions"]
        }
        for detail in details:
            assert detail["locator_status"] == "2026_REFERENCE_ONLY"
            assert detail["applicability_status"] == "UNDETERMINED_FOR_REAL_AND_FICTIONAL_2027"
            assert detail["trigger_status"] == "NOT_ESTABLISHED_OUTSIDE_SELECTED_CHAIN"
            assert detail["nonoccurrence_status"] == "NOT_ESTABLISHED_ALL_COMPANY_OR_OUTSIDE"
            assert detail["qualified_review_status"] == "OPEN_2027_PRIMARY_AND_FACT_RECHECK"
            assert detail["performance_fact_status"] == "NOT_ESTABLISHED_BY_LOCATOR"
            assert detail["not_applicable_conclusion"] is False
            assert detail["required_qualified_review_inputs"]
        flagged = [detail for detail in details if detail["publication_status_hold"]]
        assert len(flagged) == 1
        assert flagged[0]["provision"]["id"] == "45-CFR-164.509"
        assert flagged[0]["hhs_vacatur_status_url"] == context["spec"]["hhs_vacatur_status_url"]


def test_exact_66_candidate_gap_and_50_remaining():
    report = gap.build(REPOSITORY, PRIVATE)
    assert report == json.loads(GAP_STEM.with_suffix(".json").read_bytes())
    assert gap.markdown(report) == GAP_STEM.with_suffix(".md").read_text()
    assert report["counts_per_side"] == {
        "authored_routes": 72,
        "unsupported_exact_clauses": 66,
        "bounded_provision_candidates": 16,
        "remaining_matter_candidates": 46,
        "remaining_context_candidates": 4,
        "unmodeled_in_this_iteration": 50,
        "active_p1_tasks_unrun": 409,
    }
    for side in "AB":
        rows = report["rows_by_side"][side]
        assert len(rows) == len({row["task_id"] for row in rows}) == 66
        assert sum(row["new_overlay_cohort"] for row in rows) == 16
        assert all(row["classification"] == "UNSUPPORTED_EXACT_CLAUSE" for row in rows)
        assert all(row["current_conclusion"] == "NOT_RUN" for row in rows)
        assert all(row["audit_task_credit"] is False for row in rows)
    assert report["source_complete"] is report["fresh_audit_pair_created"] is False
    assert report["audit_task_credit"] is False


def test_disposable_tampered_native_byte_and_branch_ref_fail_closed(tmp_path):
    copied = tmp_path / "private"
    shutil.copytree(RUN, copied)
    copied.chmod(0o700)
    for path in copied.iterdir():
        path.chmod(0o600)
    db_path = copied / "company.sqlite3"
    with db_path.open("ab") as f:
        f.write(b"x")
    with pytest.raises(source.CompanyStoreError, match="manifest differs"):
        source.verify(copied, repository=REPOSITORY, private_repository=PRIVATE)
    db_path.write_bytes((RUN / "company.sqlite3").read_bytes())
    changed = json.loads((copied / "RECEIPT.json").read_bytes())
    changed["predecessor_selected_refs"]["CLEAN"]["scope"]["branch"] = "LEG-MESSY"
    receipt_bytes = (json.dumps(changed, indent=2, sort_keys=True) + "\n").encode()
    (copied / "RECEIPT.json").write_bytes(receipt_bytes)
    manifest = json.loads((copied / "MANIFEST.json").read_bytes())
    manifest["receipt_sha256"] = hashlib.sha256(receipt_bytes).hexdigest()
    (copied / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    with pytest.raises(source.CompanyStoreError, match="receipt/scope differs"):
        source.verify(copied, repository=REPOSITORY, private_repository=PRIVATE)


def test_predecessor_review_or_route_pin_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(source.PRIVATE_PINS, source.PREDECESSOR_REVIEW, "0" * 64)
    with pytest.raises(source.CompanyStoreError, match="predecessor bytes differ"):
        source._context(REPOSITORY, PRIVATE)
    monkeypatch.setitem(gap.PINS, gap.LEDGER, "0" * 64)
    with pytest.raises(gap.pinned.SourceRequestError, match="Pinned input differs"):
        gap.build(REPOSITORY, PRIVATE)


def test_fresh_private_producer_replays_selected_source(tmp_path):
    root = tmp_path / "new-private-run"
    root.mkdir(mode=0o700)
    produced = source.create(root / "run-v1", repository=REPOSITORY, private_repository=PRIVATE)
    assert produced["schema"] == source.SCHEMA
    assert len(produced["records"]["CLEAN"]) == len(produced["records"]["MESSY"]) == 20
    assert produced["audit_task_credit"] is False
