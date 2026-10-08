"""Reviewed V6 prefix and selected SEC003 route stay exact and partial."""

from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v7 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v7 as portfolio
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def test_reviewed_v6_report_and_candidates_match_recomputed_prefix():
    report, candidates, _ = portfolio._v6_review(PRIVATE)
    assert portfolio.prior.verify_all(REPOSITORY, private_repository=PRIVATE) == report
    diagnostic, profiles = candidate.prior.candidate_profiles(REPOSITORY, PRIVATE)
    assert diagnostic == report
    for side in "AB":
        assert profiles[side]["manifest"] == candidates[f"{side}.json"]
        assert (
            profiles[side]["source_pins"] == candidates["REPORT.json"]["sides"][side]["source_pins"]
        )


def test_same_count_v6_source_row_drift_fails_closed(monkeypatch):
    changed = deepcopy(portfolio.prior.verify_all(REPOSITORY, private_repository=PRIVATE))
    changed["sources"][0]["source"] = "UNREVIEWED_SOURCE_ROW"
    monkeypatch.setattr(portfolio.prior, "verify_all", lambda *args, **kwargs: changed)
    with pytest.raises(PortfolioVerificationError, match="Recomputed V6 source prefix"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)


def test_same_count_v6_candidate_pin_drift_fails_closed(monkeypatch):
    original = candidate.prior.candidate_profiles

    def changed(*args, **kwargs):
        diagnostic, profiles = original(*args, **kwargs)
        profiles = deepcopy(profiles)
        profiles["A"]["source_pins"][0]["source"] = "UNREVIEWED_PIN"
        return diagnostic, profiles

    monkeypatch.setattr(candidate.prior, "candidate_profiles", changed)
    with pytest.raises(CandidateRegistryError, match="Exact reviewed V6 candidate row/pin"):
        candidate.candidate_profiles(REPOSITORY, PRIVATE)


def test_unreviewed_sec003_cannot_be_selected(monkeypatch):
    monkeypatch.setattr(portfolio, "SEC_REVIEW_SHA", "PENDING_INDEPENDENT_MAIN_REVIEW")
    with pytest.raises(PortfolioVerificationError, match="main review not yet pinned"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)


def test_reviewed_sec003_route_stays_partial_and_reperformable(tmp_path):
    selected = portfolio.write_report(REPOSITORY, PRIVATE, tmp_path / "portfolio")
    assert portfolio.verify_report(tmp_path / "portfolio", REPOSITORY, PRIVATE) == selected
    assert (
        selected["source_count"],
        selected["native_versions"],
        selected["source_component_count"],
    ) == (28, 529, 29)
    assert selected["sources"][-1]["source"] == "sec003vuln"
    assert selected["sources"][-1]["branch_versions"] == {
        "SEC003-SELECTED-CLEAN": 11,
        "SEC003-SELECTED-MESSY": 18,
    }
    assert selected["source_complete"] is selected["audit_task_credit"] is False
    routed = candidate.write_candidate(REPOSITORY, PRIVATE, tmp_path / "candidate")
    assert candidate.verify_candidate(tmp_path / "candidate", REPOSITORY, PRIVATE) == routed
    assert routed["reviewed_native_versions"] == 529
    assert routed["source_complete"] is routed["audit_task_credit"] is False
    assert routed["fresh_audit_pair_created"] is False
    assert routed["grants_or_collections_created"] is False
    for side in "AB":
        row = routed["sides"][side]
        assert (row["component_count"], row["scenario_source_component_count"]) == (42, 29)
        assert row["system_alias_count"] == 265
        assert row["source_pins"][-1]["source"] == "sec003vuln"


def test_sec003_review_byte_drift_fails_closed(monkeypatch):
    monkeypatch.setattr(portfolio, "SEC_REVIEW_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="byte pin"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
