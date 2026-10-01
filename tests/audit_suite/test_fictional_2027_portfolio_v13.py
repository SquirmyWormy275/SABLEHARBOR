"""Selected component source extends only the reviewed V12 partial roster."""

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v13 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v13 as portfolio
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
RUN = REPOSITORY / "enterprise/generated/audit-suite/company-source-portfolio-v13-2026-09-30"


@pytest.fixture(scope="module")
def reviewed_v12():
    return portfolio._v12_review(PRIVATE)


@pytest.fixture(scope="module")
def diagnostic():
    return portfolio.verify_report(RUN / "isolated-run-v1", REPOSITORY, PRIVATE)


@pytest.fixture(scope="module")
def routed():
    return candidate.verify_candidate(RUN / "isolated-candidate-v1", REPOSITORY, PRIVATE)


def test_exact_v12_source_prefix(reviewed_v12, diagnostic):
    old_report, old_candidates, _ = reviewed_v12
    assert diagnostic["sources"][:33] == old_report["sources"]
    assert diagnostic["v12_review_sha256"] == portfolio.V12_REVIEW_SHA
    assert (
        diagnostic["source_count"],
        diagnostic["native_versions"],
        diagnostic["source_component_count"],
    ) == (34, 780, 35)
    assert old_candidates["REPORT.json"]["reviewed_native_versions"] == 755
    assert diagnostic["source_complete"] is diagnostic["audit_task_credit"] is False
    assert diagnostic["fresh_audit_pair_created"] is False


def test_cc52_main_source_canon_boundary_and_native_counts(diagnostic):
    row = diagnostic["sources"][-1]
    assert row["source"] == "sec001component"
    assert row["review_sha256"] == portfolio.COMPONENT_REVIEW_SHA
    assert row["database_sha256"] == {"native": portfolio.COMPONENT_DB_SHA}
    assert row["branch_versions"] == {
        "SEC001-COMPONENT-CLEAN": 10,
        "SEC001-COMPONENT-MESSY": 15,
    }
    assert row["ledger_system_counts"] == {"native": 7}
    assert row["inherited_audit_journals"] == {
        "grants": 0,
        "collections": 0,
        "access_events": 0,
    }
    assert row["selected_component_count"] == 2
    assert row["selected_authored_clause"] == portfolio.component.CLAUSE
    assert row["existing_limited_route_lead"] == "SEC003_SELECTED_VULNERABILITY_V1"
    assert row["messy_false_close_corrected"] is True
    assert row["messy_historical_exception_open"] is True
    for key in (
        "actual_supplier_selected_or_contracted",
        "actual_deployed_component",
        "approved_enterprise_architecture",
        "independent_approval",
        "population_complete",
        "audit_task_credit",
    ):
        assert row[key] is False
    receipt = json.loads(
        (
            PRIVATE
            / portfolio.BASE
            / portfolio.COMPONENT_FOLDER
            / portfolio.COMPONENT_RUN
            / "SOURCE_RECEIPT.json"
        ).read_text()
    )
    assert receipt["selected_component_ids"] == [
        portfolio.component.CORE,
        portfolio.component.OUTSOURCED,
    ]
    assert receipt["route_disposition"]["A"]["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    assert receipt["route_disposition"]["B"]["current_conclusion"] == "NOT_RUN"
    database = (
        PRIVATE
        / portfolio.BASE
        / portfolio.COMPONENT_FOLDER
        / portfolio.COMPONENT_RUN
        / "company.sqlite3"
    )
    with sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 25
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM access_events").fetchone()[0] == 0


def test_exact_v12_candidate_prefix_and_new_component(reviewed_v12, routed):
    old_candidates = reviewed_v12[1]
    assert routed["reviewed_native_versions"] == 780
    assert routed["v12_independent_review_sha256"] == portfolio.V12_REVIEW_SHA
    assert routed["source_complete"] is routed["audit_task_credit"] is False
    assert routed["fresh_audit_pair_created"] is False
    assert routed["grants_or_collections_created"] is False
    for side, branch in (("A", "SEC001-COMPONENT-CLEAN"), ("B", "SEC001-COMPONENT-MESSY")):
        old_manifest = old_candidates[f"{side}.json"]
        new_manifest = json.loads((RUN / "isolated-candidate-v1" / f"{side}.json").read_text())
        assert new_manifest["components"] == {
            **old_manifest["components"],
            "scenario-sec001component": new_manifest["components"]["scenario-sec001component"],
        }
        new = routed["sides"][side]
        old = old_candidates["REPORT.json"]["sides"][side]
        assert new["source_pins"][:34] == old["source_pins"]
        assert new["base_registry_sha256"] == old["base_registry_sha256"]
        assert (
            new["component_count"],
            new["source_cohort_count"],
            new["scenario_source_component_count"],
            new["system_alias_count"],
            len(new["source_pins"]),
        ) == (48, 34, 35, 297, 35)
        assert new["source_pins"][-1] == {
            "source": "sec001component",
            "ledger": "native",
            "source_review_sha256": portfolio.COMPONENT_REVIEW_SHA,
            "manifest_sha256": portfolio.COMPONENT_MANIFEST_SHA,
            "receipt_sha256": portfolio.COMPONENT_RECEIPT_SHA,
            "database_sha256": portfolio.COMPONENT_DB_SHA,
            "physical_company": "SABLE-HARBOR-REFERENCE",
            "physical_branch": branch,
            "system_count": 7,
            "inherited_audit_journals": {"grants": 0, "collections": 0, "access_events": 0},
        }
        assert new_manifest["components"]["scenario-sec001component"]["systems"] == [
            "challenge",
            "component_inventory",
            "control_mapping",
            "exception_register",
            "lifecycle",
            "ownership",
            "supplier_risk",
        ]


def test_review_and_source_pin_drift_fail_closed(monkeypatch):
    monkeypatch.setattr(portfolio, "V12_REVIEW_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="byte pin differs"):
        portfolio._v12_review(PRIVATE)
    monkeypatch.undo()
    monkeypatch.setattr(portfolio, "COMPONENT_MODULE_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="source module differs"):
        portfolio._component_source(REPOSITORY, PRIVATE)


def test_same_count_source_and_candidate_prefix_drift_fail_closed(reviewed_v12, monkeypatch):
    changed = deepcopy(reviewed_v12[0])
    changed["sources"][0]["source"] = "UNREVIEWED_SOURCE_ROW"
    monkeypatch.setattr(portfolio.prior, "verify_all", lambda *args, **kwargs: changed)
    with pytest.raises(PortfolioVerificationError, match="Recomputed V12 source prefix"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
    monkeypatch.undo()
    original = candidate.prior.candidate_profiles

    def changed_profile(*args, **kwargs):
        diagnostic, profiles = original(*args, **kwargs)
        profiles = deepcopy(profiles)
        profiles["A"]["source_pins"][0]["source"] = "UNREVIEWED_PIN"
        return diagnostic, profiles

    monkeypatch.setattr(candidate.prior, "candidate_profiles", changed_profile)
    with pytest.raises(CandidateRegistryError, match="Exact reviewed V12 candidate row/pin"):
        candidate.candidate_profiles(REPOSITORY, PRIVATE)
