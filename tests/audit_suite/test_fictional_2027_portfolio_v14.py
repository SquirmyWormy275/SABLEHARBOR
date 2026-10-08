"""Selected pending POL004 procedure extends only the reviewed V13 partial roster."""

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v14 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v14 as portfolio
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
RUN = REPOSITORY / "enterprise/generated/audit-suite/company-source-portfolio-v14-2026-09-30"
RUN_ROLE = "main" if REPOSITORY.resolve() == PRIVATE.resolve() else "isolated"
SOURCE_RUN = RUN / f"{RUN_ROLE}-run-v1"
CANDIDATE_RUN = RUN / f"{RUN_ROLE}-candidate-v1"


@pytest.fixture(scope="module")
def reviewed_v13():
    return portfolio._v13_review(PRIVATE)


@pytest.fixture(scope="module")
def diagnostic():
    return portfolio.verify_report(SOURCE_RUN, REPOSITORY, PRIVATE)


@pytest.fixture(scope="module")
def routed():
    return candidate.verify_candidate(CANDIDATE_RUN, REPOSITORY, PRIVATE)


def test_exact_v13_source_prefix(reviewed_v13, diagnostic):
    old_report, old_candidates, _ = reviewed_v13
    assert diagnostic["sources"][:34] == old_report["sources"]
    assert diagnostic["v13_review_sha256"] == portfolio.V13_REVIEW_SHA
    assert (
        diagnostic["source_count"],
        diagnostic["native_versions"],
        diagnostic["source_component_count"],
    ) == (35, 796, 36)
    assert old_candidates["REPORT.json"]["reviewed_native_versions"] == 780
    assert diagnostic["source_complete"] is diagnostic["audit_task_credit"] is False
    assert diagnostic["fresh_audit_pair_created"] is False


def test_pol004_main_source_pending_boundary_and_native_counts(diagnostic):
    row = diagnostic["sources"][-1]
    assert row["source"] == "pol004procedure"
    assert row["review_sha256"] == portfolio.PROCEDURE_REVIEW_SHA
    assert row["database_sha256"] == {"native": portfolio.PROCEDURE_DB_SHA}
    assert row["branch_versions"] == {
        "POL004-PROCEDURE-CLEAN": 7,
        "POL004-PROCEDURE-MESSY": 9,
    }
    assert row["ledger_system_counts"] == {"native": 8}
    assert row["inherited_audit_journals"] == {
        "grants": 0,
        "collections": 0,
        "access_events": 0,
    }
    assert row["selected_authored_clause"] == portfolio.procedure.CLAUSE
    assert row["enterprise_policy_status_2026"] == "OPEN"
    assert row["procedure_authority"] == "PENDING_AUTHORIZED_DECISION"
    assert row["design_standard_approved_only"] is True
    assert row["messy_exception_open"] is True
    assert row["messy_false_close_corrected"] is True
    assert row["messy_missed_interval_retained"] is True
    for key in ("actual_operation", "full_policy_or_procedure_population", "audit_task_credit"):
        assert row[key] is False
    receipt = json.loads(
        (
            PRIVATE
            / portfolio.BASE
            / portfolio.PROCEDURE_FOLDER
            / portfolio.PROCEDURE_RUN
            / "SOURCE_RECEIPT.json"
        ).read_text()
    )
    assert receipt["route_disposition"]["A"]["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    assert receipt["route_disposition"]["B"]["current_conclusion"] == "NOT_RUN"
    database = (
        PRIVATE
        / portfolio.BASE
        / portfolio.PROCEDURE_FOLDER
        / portfolio.PROCEDURE_RUN
        / "company.sqlite3"
    )
    with sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 16
        for table in ("grants", "collections", "access_events"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_exact_v13_candidate_prefix_and_new_procedure(reviewed_v13, routed):
    old_candidates = reviewed_v13[1]
    assert routed["reviewed_native_versions"] == 796
    assert routed["v13_independent_review_sha256"] == portfolio.V13_REVIEW_SHA
    assert routed["source_complete"] is routed["audit_task_credit"] is False
    assert routed["fresh_audit_pair_created"] is False
    assert routed["grants_or_collections_created"] is False
    for side, branch in (("A", "POL004-PROCEDURE-CLEAN"), ("B", "POL004-PROCEDURE-MESSY")):
        old_manifest = old_candidates[f"{side}.json"]
        new_manifest = json.loads((CANDIDATE_RUN / f"{side}.json").read_text())
        assert new_manifest["components"] == {
            **old_manifest["components"],
            "scenario-pol004procedure": new_manifest["components"]["scenario-pol004procedure"],
        }
        new = routed["sides"][side]
        old = old_candidates["REPORT.json"]["sides"][side]
        assert new["source_pins"][:35] == old["source_pins"]
        assert new["base_registry_sha256"] == old["base_registry_sha256"]
        assert (
            new["component_count"],
            new["source_cohort_count"],
            new["scenario_source_component_count"],
            new["system_alias_count"],
            len(new["source_pins"]),
        ) == (49, 35, 36, 305, 36)
        assert new["source_pins"][-1] == {
            "source": "pol004procedure",
            "ledger": "native",
            "source_review_sha256": portfolio.PROCEDURE_REVIEW_SHA,
            "manifest_sha256": portfolio.PROCEDURE_MANIFEST_SHA,
            "receipt_sha256": portfolio.PROCEDURE_RECEIPT_SHA,
            "database_sha256": portfolio.PROCEDURE_DB_SHA,
            "physical_company": "SABLE-HARBOR-REFERENCE",
            "physical_branch": branch,
            "system_count": 8,
            "inherited_audit_journals": {"grants": 0, "collections": 0, "access_events": 0},
        }
        assert new_manifest["components"]["scenario-pol004procedure"]["systems"] == [
            "approval_gate",
            "challenge",
            "correction",
            "due_trigger",
            "exception_review",
            "execution_trace",
            "procedure_candidate",
            "result_register",
        ]


def test_review_and_source_pin_drift_fail_closed(monkeypatch):
    monkeypatch.setattr(portfolio, "V13_REVIEW_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="byte pin differs"):
        portfolio._v13_review(PRIVATE)
    monkeypatch.undo()
    monkeypatch.setattr(portfolio, "PROCEDURE_MODULE_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="source module differs"):
        portfolio._procedure_source(REPOSITORY, PRIVATE)


def test_same_count_source_and_candidate_prefix_drift_fail_closed(reviewed_v13, monkeypatch):
    changed = deepcopy(reviewed_v13[0])
    changed["sources"][0]["source"] = "UNREVIEWED_SOURCE_ROW"
    monkeypatch.setattr(portfolio.prior, "verify_all", lambda *args, **kwargs: changed)
    with pytest.raises(PortfolioVerificationError, match="Recomputed V13 source prefix"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
    monkeypatch.undo()
    original = candidate.prior.candidate_profiles

    def changed_profile(*args, **kwargs):
        diagnostic, profiles = original(*args, **kwargs)
        profiles = deepcopy(profiles)
        profiles["A"]["source_pins"][0]["source"] = "UNREVIEWED_PIN"
        return diagnostic, profiles

    monkeypatch.setattr(candidate.prior, "candidate_profiles", changed_profile)
    with pytest.raises(CandidateRegistryError, match="Exact reviewed V13 candidate row/pin"):
        candidate.candidate_profiles(REPOSITORY, PRIVATE)
