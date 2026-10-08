"""The selected physical-site route extends exact reviewed V7 rows and pins."""

from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v8 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v8 as portfolio
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def test_reviewed_v7_report_and_all_candidate_rows_match_recomputed_prefix():
    report, candidates, _ = portfolio._v7_review(PRIVATE)
    assert portfolio.prior.verify_all(REPOSITORY, private_repository=PRIVATE) == report
    diagnostic, profiles = candidate.prior.candidate_profiles(REPOSITORY, PRIVATE)
    assert diagnostic == report
    for side in "AB":
        assert profiles[side]["manifest"] == candidates[f"{side}.json"]
        selected = candidates["REPORT.json"]["sides"][side]
        assert profiles[side]["source_pins"] == selected["source_pins"]
        assert profiles[side]["profile_id"] == selected["profile_id"]
        assert profiles[side]["base_registry_sha256"] == selected["base_registry_sha256"]


def test_same_count_v7_source_row_drift_fails_closed(monkeypatch):
    changed = deepcopy(portfolio.prior.verify_all(REPOSITORY, private_repository=PRIVATE))
    changed["sources"][0]["source"] = "UNREVIEWED_SOURCE_ROW"
    monkeypatch.setattr(portfolio.prior, "verify_all", lambda *args, **kwargs: changed)
    with pytest.raises(PortfolioVerificationError, match="Recomputed V7 source prefix"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)


def test_same_count_v7_candidate_pin_drift_fails_closed(monkeypatch):
    original = candidate.prior.candidate_profiles

    def changed(*args, **kwargs):
        diagnostic, profiles = original(*args, **kwargs)
        profiles = deepcopy(profiles)
        profiles["A"]["source_pins"][0]["source"] = "UNREVIEWED_PIN"
        return diagnostic, profiles

    monkeypatch.setattr(candidate.prior, "candidate_profiles", changed)
    with pytest.raises(CandidateRegistryError, match="Exact reviewed V7 candidate row/pin"):
        candidate.candidate_profiles(REPOSITORY, PRIVATE)


def test_unreviewed_physical_source_cannot_be_selected(monkeypatch):
    monkeypatch.setattr(portfolio, "PHYS_REVIEW_SHA", "PENDING_INDEPENDENT_MAIN_REVIEW")
    with pytest.raises(PortfolioVerificationError, match="main review not yet pinned"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)


def test_reviewed_physical_site_route_is_partial_and_reperformable(tmp_path):
    selected = portfolio.write_report(REPOSITORY, PRIVATE, tmp_path / "portfolio")
    assert portfolio.verify_report(tmp_path / "portfolio", REPOSITORY, PRIVATE) == selected
    assert (
        selected["source_count"],
        selected["native_versions"],
        selected["source_component_count"],
    ) == (29, 560, 30)
    physical = selected["sources"][-1]
    assert physical["source"] == "physicalsite"
    assert physical["branch_versions"] == {"PHYSICAL-CLEAN": 13, "PHYSICAL-MESSY": 18}
    assert physical["ledger_system_counts"] == {"native": 8}
    assert physical["inherited_audit_journals"] == {
        "grants": 0,
        "collections": 0,
        "access_events": 0,
    }
    assert selected["source_complete"] is selected["audit_task_credit"] is False
    routed = candidate.write_candidate(REPOSITORY, PRIVATE, tmp_path / "candidate")
    assert candidate.verify_candidate(tmp_path / "candidate", REPOSITORY, PRIVATE) == routed
    assert routed["reviewed_native_versions"] == 560
    assert routed["source_complete"] is routed["audit_task_credit"] is False
    assert routed["fresh_audit_pair_created"] is routed["grants_or_collections_created"] is False
    for side, branch in (("A", "PHYSICAL-CLEAN"), ("B", "PHYSICAL-MESSY")):
        row = routed["sides"][side]
        assert (row["component_count"], row["scenario_source_component_count"]) == (43, 30)
        assert row["system_alias_count"] == 273
        assert row["source_pins"][-1]["source"] == "physicalsite"
        assert row["source_pins"][-1]["physical_branch"] == branch
        assert row["source_pins"][-1]["system_count"] == 8


def test_physical_review_byte_drift_fails_closed(monkeypatch):
    monkeypatch.setattr(portfolio, "PHYS_REVIEW_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="byte pin"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
