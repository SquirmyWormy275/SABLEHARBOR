"""Selected emergency replay extends only the accepted V14 partial roster."""

import json
import sqlite3
from contextlib import closing
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v15 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v15 as portfolio
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
RUN = REPOSITORY / "enterprise/generated/audit-suite/company-source-portfolio-v15-2026-09-30"
RUN_ROLE = "main" if REPOSITORY.resolve() == PRIVATE.resolve() else "isolated"
SOURCE_RUN = RUN / ("main-report-v1" if RUN_ROLE == "main" else "isolated-run-v1")
CANDIDATE_RUN = RUN / f"{RUN_ROLE}-candidate-v1"


@pytest.fixture(scope="module")
def reviewed_v14():
    return portfolio._v14_review(PRIVATE)


@pytest.fixture(scope="module")
def diagnostic():
    return portfolio.verify_report(SOURCE_RUN, REPOSITORY, PRIVATE)


@pytest.fixture(scope="module")
def routed():
    return candidate.verify_candidate(CANDIDATE_RUN, REPOSITORY, PRIVATE)


def test_exact_v14_source_prefix_and_no_credit(reviewed_v14, diagnostic):
    old_report, old_candidates, _ = reviewed_v14
    assert diagnostic["sources"][:35] == old_report["sources"]
    assert diagnostic["v14_review_sha256"] == portfolio.V14_REVIEW_SHA
    assert (
        diagnostic["source_count"],
        diagnostic["native_versions"],
        diagnostic["source_component_count"],
    ) == (36, 819, 37)
    assert old_candidates["REPORT.json"]["reviewed_native_versions"] == 796
    assert diagnostic["source_complete"] is diagnostic["audit_task_credit"] is False
    assert diagnostic["fresh_audit_pair_created"] is False


def test_replay_main_source_retains_open_exceptions_and_native_rows(diagnostic):
    row = diagnostic["sources"][-1]
    assert row["source"] == "emergencyreplay"
    assert row["review_sha256"] == portfolio.REPLAY_REVIEW_SHA
    assert row["database_sha256"] == {"native": portfolio.REPLAY_DB_SHA}
    assert row["branch_versions"] == {"EMERGENCY-REPLAY-CLEAN": 8, "EMERGENCY-REPLAY-MESSY": 15}
    assert row["ledger_system_counts"] == {"native": 9}
    assert row["inherited_audit_journals"] == {
        "grants": 0,
        "collections": 0,
        "access_events": 0,
    }
    assert row["selected_population_count"] == 1
    assert row["local_open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert row["messy_upstream_gates_remain_open"] is True
    for key in (
        "actual_phi_processing",
        "deployed_recovery_proven",
        "source_complete",
        "audit_task_credit",
    ):
        assert row[key] is False
    source_root = PRIVATE / portfolio.BASE / portfolio.REPLAY_FOLDER / portfolio.REPLAY_RUN
    receipt = json.loads((source_root / "RECEIPT.json").read_text())
    assert receipt["upstream_original_refs"]["MESSY"]["bcm_open_closure"]["record"] == (
        "KEY-AND-CAPACITY"
    )
    with closing(
        sqlite3.connect(
            (source_root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
        )
    ) as db:
        assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 23
        for table in ("grants", "collections", "access_events"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_exact_v14_candidate_prefix_and_new_component(reviewed_v14, routed):
    old_candidates = reviewed_v14[1]
    assert routed["reviewed_native_versions"] == 819
    assert routed["v14_independent_review_sha256"] == portfolio.V14_REVIEW_SHA
    assert routed["source_complete"] is routed["audit_task_credit"] is False
    assert routed["fresh_audit_pair_created"] is False
    assert routed["grants_or_collections_created"] is False
    for side, branch in (("A", "EMERGENCY-REPLAY-CLEAN"), ("B", "EMERGENCY-REPLAY-MESSY")):
        old_manifest = old_candidates[f"{side}.json"]
        new_manifest = json.loads((CANDIDATE_RUN / f"{side}.json").read_text())
        assert new_manifest["components"] == {
            **old_manifest["components"],
            "scenario-emergencyreplay": new_manifest["components"]["scenario-emergencyreplay"],
        }
        new = routed["sides"][side]
        old = old_candidates["REPORT.json"]["sides"][side]
        assert new["source_pins"][:36] == old["source_pins"]
        assert new["base_registry_sha256"] == old["base_registry_sha256"]
        assert (
            new["component_count"],
            new["source_cohort_count"],
            new["scenario_source_component_count"],
            new["system_alias_count"],
            len(new["source_pins"]),
        ) == (50, 36, 37, 314, 37)
        assert new["source_pins"][-1] == {
            "source": "emergencyreplay",
            "ledger": "native",
            "source_review_sha256": portfolio.REPLAY_REVIEW_SHA,
            "manifest_sha256": portfolio.REPLAY_MANIFEST_SHA,
            "receipt_sha256": portfolio.REPLAY_RECEIPT_SHA,
            "database_sha256": portfolio.REPLAY_DB_SHA,
            "physical_company": "SABLE-HARBOR-REFERENCE",
            "physical_branch": branch,
            "system_count": 9,
            "inherited_audit_journals": {"grants": 0, "collections": 0, "access_events": 0},
        }
        assert new_manifest["components"]["scenario-emergencyreplay"]["systems"] == (
            candidate.REPLAY_SYSTEM_ALIASES
        )


def test_review_and_source_pin_drift_fail_closed(monkeypatch):
    monkeypatch.setattr(portfolio, "V14_REVIEW_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="byte pin differs"):
        portfolio._v14_review(PRIVATE)
    monkeypatch.undo()
    monkeypatch.setattr(portfolio, "REPLAY_MODULE_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="source module differs"):
        portfolio._replay_source(REPOSITORY, PRIVATE)


def test_same_count_source_and_candidate_prefix_drift_fail_closed(reviewed_v14, monkeypatch):
    changed = deepcopy(reviewed_v14[0])
    changed["sources"][0]["source"] = "UNREVIEWED_SOURCE_ROW"
    monkeypatch.setattr(portfolio.prior, "verify_all", lambda *args, **kwargs: changed)
    with pytest.raises(PortfolioVerificationError, match="Recomputed V14 source prefix"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
    monkeypatch.undo()
    original = candidate.prior.candidate_profiles

    def changed_profile(*args, **kwargs):
        diagnostic, profiles = original(*args, **kwargs)
        profiles = deepcopy(profiles)
        profiles["A"]["source_pins"][0]["source"] = "UNREVIEWED_PIN"
        return diagnostic, profiles

    monkeypatch.setattr(candidate.prior, "candidate_profiles", changed_profile)
    with pytest.raises(CandidateRegistryError, match="Exact reviewed V14 candidate row/pin"):
        candidate.candidate_profiles(REPOSITORY, PRIVATE)
