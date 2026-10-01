"""Only the reviewed held PRD concern extends the V15 partial candidate."""

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v16 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v16 as portfolio
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
RUN = REPOSITORY / "enterprise/generated/audit-suite/company-source-portfolio-v16-2026-10-01"
RUN_ROLE = "main" if REPOSITORY.resolve() == PRIVATE.resolve() else "isolated"
SOURCE_RUN = RUN / f"{RUN_ROLE}-report-v1"
CANDIDATE_RUN = RUN / f"{RUN_ROLE}-candidate-v1"


@pytest.fixture(scope="module")
def reviewed_v15():
    return portfolio._v15_review(PRIVATE)


@pytest.fixture(scope="module")
def diagnostic():
    return portfolio.verify_report(SOURCE_RUN, REPOSITORY, PRIVATE)


@pytest.fixture(scope="module")
def routed():
    return candidate.verify_candidate(CANDIDATE_RUN, REPOSITORY, PRIVATE)


def test_exact_reviewed_v15_prefix_and_no_credit(reviewed_v15, diagnostic):
    old_report, old_candidates, _ = reviewed_v15
    assert diagnostic["sources"][:36] == old_report["sources"]
    assert diagnostic["v15_review_sha256"] == portfolio.V15_REVIEW_SHA
    assert (
        diagnostic["source_count"],
        diagnostic["native_versions"],
        diagnostic["source_component_count"],
    ) == (37, 840, 38)
    assert old_candidates["REPORT.json"]["reviewed_native_versions"] == 819
    assert diagnostic["source_complete"] is diagnostic["audit_task_credit"] is False
    assert diagnostic["fresh_audit_pair_created"] is False


def test_concern_reviewed_source_keeps_claimant_and_delivery_limits(diagnostic):
    row = diagnostic["sources"][-1]
    assert row["source"] == "prdconcern"
    assert row["review_sha256"] == portfolio.CONCERN_REVIEW_SHA
    assert row["database_sha256"] == {"native": portfolio.CONCERN_DB_SHA}
    assert row["branch_versions"] == {"PRD-CONCERN-CLEAN": 8, "PRD-CONCERN-MESSY": 13}
    assert row["ledger_system_counts"] == {"native": 10}
    assert row["inherited_audit_journals"] == {
        "grants": 0,
        "collections": 0,
        "access_events": 0,
    }
    assert row["selected_concern_count"] == 1
    assert row["local_open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    for key in (
        "selected_claimant_verified",
        "actual_phi_processing",
        "source_complete",
        "audit_task_credit",
    ):
        assert row[key] is False
    for key in (
        "real_external_messages_sent",
        "fictional_accepted_deliveries",
        "customer_acknowledgments",
    ):
        assert row[key] == 0
    source_root = PRIVATE / portfolio.BASE / portfolio.CONCERN_FOLDER / portfolio.CONCERN_RUN
    receipt = json.loads((source_root / "RECEIPT.json").read_text())
    for rows in receipt["records"].values():
        assert all(record["event_at"] != record["imported_at"] for record in rows)
        assert all(record["imported_at"].startswith("2026-") for record in rows)
    with sqlite3.connect(
        (source_root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 21
        for table in ("grants", "collections", "access_events"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_exact_v15_candidate_prefix_and_new_component(reviewed_v15, routed):
    old_candidates = reviewed_v15[1]
    assert routed["reviewed_native_versions"] == 840
    assert routed["v15_independent_review_sha256"] == portfolio.V15_REVIEW_SHA
    assert routed["source_complete"] is routed["audit_task_credit"] is False
    assert routed["fresh_audit_pair_created"] is False
    assert routed["grants_or_collections_created"] is False
    for side, branch in (("A", "PRD-CONCERN-CLEAN"), ("B", "PRD-CONCERN-MESSY")):
        old_manifest = old_candidates[f"{side}.json"]
        new_manifest = json.loads((CANDIDATE_RUN / f"{side}.json").read_text())
        assert new_manifest["components"] == {
            **old_manifest["components"],
            "scenario-prdconcern": new_manifest["components"]["scenario-prdconcern"],
        }
        new = routed["sides"][side]
        old = old_candidates["REPORT.json"]["sides"][side]
        assert new["source_pins"][:37] == old["source_pins"]
        assert new["base_registry_sha256"] == old["base_registry_sha256"]
        assert (
            new["component_count"],
            new["source_cohort_count"],
            new["scenario_source_component_count"],
            new["system_alias_count"],
            len(new["source_pins"]),
        ) == (51, 37, 38, 324, 38)
        assert new["source_pins"][-1] == {
            "source": "prdconcern",
            "ledger": "native",
            "source_review_sha256": portfolio.CONCERN_REVIEW_SHA,
            "manifest_sha256": portfolio.CONCERN_MANIFEST_SHA,
            "receipt_sha256": portfolio.CONCERN_RECEIPT_SHA,
            "database_sha256": portfolio.CONCERN_DB_SHA,
            "physical_company": "SABLE-HARBOR-REFERENCE",
            "physical_branch": branch,
            "system_count": 10,
            "inherited_audit_journals": {"grants": 0, "collections": 0, "access_events": 0},
        }
        assert (
            new_manifest["components"]["scenario-prdconcern"]["systems"]
            == candidate.CONCERN_SYSTEM_ALIASES
        )


def test_review_and_source_pin_drift_fail_closed(monkeypatch):
    monkeypatch.setattr(portfolio, "V15_REVIEW_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="byte pin differs"):
        portfolio._v15_review(PRIVATE)
    monkeypatch.undo()
    monkeypatch.setattr(portfolio, "CONCERN_MODULE_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="tracked source/spec"):
        portfolio._concern_source(REPOSITORY, PRIVATE)


def test_same_count_source_and_candidate_prefix_drift_fail_closed(reviewed_v15, monkeypatch):
    changed = deepcopy(reviewed_v15[0])
    changed["sources"][0]["source"] = "UNREVIEWED_SOURCE_ROW"
    monkeypatch.setattr(portfolio.prior, "verify_all", lambda *args, **kwargs: changed)
    with pytest.raises(PortfolioVerificationError, match="Recomputed V15 source prefix"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
    monkeypatch.undo()
    original = candidate.prior.candidate_profiles

    def changed_profile(*args, **kwargs):
        diagnostic, profiles = original(*args, **kwargs)
        profiles = deepcopy(profiles)
        profiles["A"]["source_pins"][0]["source"] = "UNREVIEWED_PIN"
        return diagnostic, profiles

    monkeypatch.setattr(candidate.prior, "candidate_profiles", changed_profile)
    with pytest.raises(CandidateRegistryError, match="Exact reviewed V15 candidate row/pin"):
        candidate.candidate_profiles(REPOSITORY, PRIVATE)
