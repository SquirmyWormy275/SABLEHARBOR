"""The selected ETH001 source extends only the reviewed partial V10 registry."""

from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v11 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v11 as portfolio
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


@pytest.fixture(scope="module")
def v10():
    return portfolio._v10_review(PRIVATE)


@pytest.fixture(scope="module")
def diagnostic():
    return portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)


@pytest.fixture(scope="module")
def profiles():
    return candidate.candidate_profiles(REPOSITORY, PRIVATE)


def test_exact_reviewed_v10_portfolio_and_candidate_prefix(v10, diagnostic, profiles):
    old_report, old_candidates, _ = v10
    assert portfolio.prior.verify_all(REPOSITORY, private_repository=PRIVATE) == old_report
    assert diagnostic["sources"][:31] == old_report["sources"]
    assert diagnostic["v10_review_sha256"] == portfolio.V10_REVIEW_SHA
    assert (
        diagnostic["source_count"],
        diagnostic["native_versions"],
        diagnostic["source_component_count"],
    ) == (
        32,
        729,
        33,
    )
    for side in "AB":
        old = old_candidates["REPORT.json"]["sides"][side]
        new = profiles[1][side]
        assert new["source_pins"][:-1] == old["source_pins"]
        assert new["manifest"]["components"] | {} == {
            **old_candidates[f"{side}.json"]["components"],
            "scenario-eth001conduct": new["manifest"]["components"]["scenario-eth001conduct"],
        }
        assert new["base_registry_sha256"] == old["base_registry_sha256"]


def test_eth001_is_bounded_selected_source_and_exact_native_pair(diagnostic, profiles):
    row = diagnostic["sources"][-1]
    assert row["source"] == "eth001conduct"
    assert row["native_versions"] == 19
    assert row["branch_versions"] == {"ETH001-CLEAN": 8, "ETH001-MESSY": 11}
    assert row["ledger_system_counts"] == {"native": 4}
    assert row["inherited_audit_journals"] == {
        "grants": 0,
        "collections": 0,
        "access_events": 0,
    }
    assert row["selected_person_count"] == 2
    assert row["fictional_local_approval_only"] is True
    assert row["messy_historical_false_clean_exception_open"] is True
    assert row["real_enterprise_code_approved"] is False
    assert row["actual_distribution_or_attestation"] is False
    assert row["workforce_population_complete"] is False
    assert row["sanctions_or_performance_review_conclusion"] is False
    assert diagnostic["source_complete"] is diagnostic["audit_task_credit"] is False
    assert diagnostic["fresh_audit_pair_created"] is False
    for side, branch in (("A", "ETH001-CLEAN"), ("B", "ETH001-MESSY")):
        profile = profiles[1][side]
        assert (len(profile["manifest"]["components"]), len(profile["source_pins"])) == (46, 33)
        assert sum(len(x["systems"]) for x in profile["manifest"]["components"].values()) == 285
        assert profile["source_pins"][-1] == {
            "source": "eth001conduct",
            "ledger": "native",
            "source_review_sha256": portfolio.ETH_REVIEW_SHA,
            "manifest_sha256": portfolio.ETH_MANIFEST_SHA,
            "receipt_sha256": portfolio.ETH_RECEIPT_SHA,
            "database_sha256": portfolio.ETH_DB_SHA,
            "physical_company": "SABLE-HARBOR-REFERENCE",
            "physical_branch": branch,
            "system_count": 4,
            "inherited_audit_journals": {"grants": 0, "collections": 0, "access_events": 0},
        }
        component = profile["manifest"]["components"]["scenario-eth001conduct"]
        assert component["branch"] == branch
        assert component["systems"] == [
            "conduct_code",
            "conduct_distribution",
            "conduct_reconciliation",
            "selected_attestation",
        ]


def test_private_outputs_reperform_exactly(tmp_path):
    report = portfolio.write_report(REPOSITORY, PRIVATE, tmp_path / "portfolio")
    assert portfolio.verify_report(tmp_path / "portfolio", REPOSITORY, PRIVATE) == report
    routed = candidate.write_candidate(REPOSITORY, PRIVATE, tmp_path / "candidate")
    assert candidate.verify_candidate(tmp_path / "candidate", REPOSITORY, PRIVATE) == routed
    assert routed["reviewed_native_versions"] == 729
    assert routed["v10_independent_review_sha256"] == portfolio.V10_REVIEW_SHA
    assert routed["source_complete"] is routed["audit_task_credit"] is False
    assert routed["fresh_audit_pair_created"] is False
    assert routed["grants_or_collections_created"] is False
    for side in "AB":
        assert (
            routed["sides"][side]["component_count"],
            routed["sides"][side]["scenario_source_component_count"],
            routed["sides"][side]["system_alias_count"],
        ) == (46, 33, 285)


def test_same_count_v10_source_drift_fails_closed(monkeypatch):
    changed = deepcopy(portfolio.prior.verify_all(REPOSITORY, private_repository=PRIVATE))
    changed["sources"][0]["source"] = "UNREVIEWED_SOURCE_ROW"
    monkeypatch.setattr(portfolio.prior, "verify_all", lambda *args, **kwargs: changed)
    with pytest.raises(PortfolioVerificationError, match="Recomputed V10 source prefix"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)


def test_review_pin_and_native_verifier_drift_fail_closed(monkeypatch):
    monkeypatch.setattr(portfolio, "ETH_REVIEW_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="byte pin"):
        portfolio._eth_source(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    monkeypatch.setattr(portfolio.conduct, "verify", lambda *args, **kwargs: {})
    with pytest.raises(PortfolioVerificationError, match="future-only native source"):
        portfolio._eth_source(REPOSITORY, PRIVATE)


def test_same_count_v10_candidate_pin_drift_fails_closed(monkeypatch):
    original = candidate.prior.candidate_profiles

    def changed(*args, **kwargs):
        diagnostic, profiles = original(*args, **kwargs)
        profiles = deepcopy(profiles)
        profiles["A"]["source_pins"][0]["source"] = "UNREVIEWED_PIN"
        return diagnostic, profiles

    monkeypatch.setattr(candidate.prior, "candidate_profiles", changed)
    with pytest.raises(CandidateRegistryError, match="Exact reviewed V10 candidate row/pin"):
        candidate.candidate_profiles(REPOSITORY, PRIVATE)
