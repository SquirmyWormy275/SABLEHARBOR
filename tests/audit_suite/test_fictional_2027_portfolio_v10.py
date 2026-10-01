"""The pending addressable docket extends V9 without deciding applicability."""

from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v10 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v10 as portfolio
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def test_reviewed_v9_full_report_and_candidate_rows_match_recomputed_prefix():
    report, candidates, _ = portfolio._v9_review(PRIVATE)
    assert portfolio.prior.verify_all(REPOSITORY, private_repository=PRIVATE) == report
    diagnostic, profiles = candidate.prior.candidate_profiles(REPOSITORY, PRIVATE)
    assert diagnostic == report
    for side in "AB":
        selected = candidates["REPORT.json"]["sides"][side]
        assert profiles[side]["manifest"] == candidates[f"{side}.json"]
        assert profiles[side]["source_pins"] == selected["source_pins"]
        assert profiles[side]["profile_id"] == selected["profile_id"]
        assert profiles[side]["base_registry_sha256"] == selected["base_registry_sha256"]


def test_same_count_v9_source_row_drift_fails_closed(monkeypatch):
    changed = deepcopy(portfolio.prior.verify_all(REPOSITORY, private_repository=PRIVATE))
    changed["sources"][0]["source"] = "UNREVIEWED_SOURCE_ROW"
    monkeypatch.setattr(portfolio.prior, "verify_all", lambda *args, **kwargs: changed)
    with pytest.raises(PortfolioVerificationError, match="Recomputed V9 source prefix"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)


def test_same_count_v9_candidate_pin_drift_fails_closed(monkeypatch):
    original = candidate.prior.candidate_profiles

    def changed(*args, **kwargs):
        diagnostic, profiles = original(*args, **kwargs)
        profiles = deepcopy(profiles)
        profiles["A"]["source_pins"][0]["source"] = "UNREVIEWED_PIN"
        return diagnostic, profiles

    monkeypatch.setattr(candidate.prior, "candidate_profiles", changed)
    with pytest.raises(CandidateRegistryError, match="Exact reviewed V9 candidate row/pin"):
        candidate.candidate_profiles(REPOSITORY, PRIVATE)


def test_reviewed_addressable_docket_route_remains_partial(tmp_path):
    selected = portfolio.write_report(REPOSITORY, PRIVATE, tmp_path / "portfolio")
    assert portfolio.verify_report(tmp_path / "portfolio", REPOSITORY, PRIVATE) == selected
    assert (
        selected["source_count"],
        selected["native_versions"],
        selected["source_component_count"],
    ) == (31, 710, 32)
    assert (
        selected["sources"][:30]
        == portfolio.prior.verify_all(REPOSITORY, private_repository=PRIVATE)["sources"]
    )
    source = selected["sources"][-1]
    assert source["source"] == "addressabledocket"
    assert source["branch_versions"] == {"ADDR-CLEAN": 24, "ADDR-MESSY": 26}
    assert source["ledger_system_counts"] == {"native": 2}
    assert source["inherited_audit_journals"] == {
        "grants": 0,
        "collections": 0,
        "access_events": 0,
    }
    assert source["pending_source_locators_per_side"] == 22
    assert source["actual_hipaa_applicability"] == "UNDETERMINED"
    assert source["environmental_decisions"] == 0
    assert source["approved_substitutions"] is False
    assert source["implemented_safeguard_claims"] is False
    assert source["messy_historical_exception_open"] is True
    assert source["related_sh_pol003_gap"] == "OPEN_INSUFFICIENT_SOURCE_UNCHANGED"
    assert selected["source_complete"] is selected["audit_task_credit"] is False
    assert selected["fresh_audit_pair_created"] is False

    routed = candidate.write_candidate(REPOSITORY, PRIVATE, tmp_path / "candidate")
    assert candidate.verify_candidate(tmp_path / "candidate", REPOSITORY, PRIVATE) == routed
    assert routed["reviewed_native_versions"] == 710
    assert routed["source_complete"] is routed["audit_task_credit"] is False
    assert routed["fresh_audit_pair_created"] is routed["grants_or_collections_created"] is False
    reviewed = portfolio._v9_review(PRIVATE)[1]
    for side, branch in (("A", "ADDR-CLEAN"), ("B", "ADDR-MESSY")):
        row = routed["sides"][side]
        assert (row["component_count"], row["scenario_source_component_count"]) == (45, 32)
        assert (
            row["system_alias_count"]
            == reviewed["REPORT.json"]["sides"][side]["system_alias_count"] + 2
        )
        assert row["source_pins"][:-1] == reviewed["REPORT.json"]["sides"][side]["source_pins"]
        assert row["source_pins"][-1]["source"] == "addressabledocket"
        assert row["source_pins"][-1]["physical_branch"] == branch
        assert row["source_pins"][-1]["system_count"] == 2
        assert row["source_pins"][-1]["inherited_audit_journals"] == {
            "grants": 0,
            "collections": 0,
            "access_events": 0,
        }


def test_addressable_review_byte_drift_fails_closed(monkeypatch):
    monkeypatch.setattr(portfolio, "ADDR_REVIEW_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="byte pin"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)


def test_addressable_native_verifier_drift_fails_closed(monkeypatch):
    monkeypatch.setattr(portfolio.addressable, "verify", lambda *args, **kwargs: {})
    with pytest.raises(PortfolioVerificationError, match="pending native claim"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
