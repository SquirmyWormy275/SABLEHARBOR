"""Reviewed V5 prefix and fictional IAM005 route remain partial and source-pinned."""

from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v6 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v6 as portfolio
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def test_exact_reviewed_iam_roster_and_partial_limits():
    report = portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
    assert (
        report["source_count"],
        report["native_versions"],
        report["source_component_count"],
    ) == (27, 500, 28)
    assert report["sources"][-1]["source"] == "iam005emergency"
    assert report["sources"][-1]["branch_versions"] == {
        "IAM005-EMERGENCY-CLEAN": 9,
        "IAM005-EMERGENCY-MESSY": 16,
    }
    assert all(row["audit_task_credit"] is False for row in report["sources"])
    assert report["source_complete"] is report["audit_task_credit"] is False
    assert report["fresh_audit_pair_created"] is False


def test_private_report_and_candidate_are_reperformable(tmp_path):
    report_root = tmp_path / "portfolio"
    candidate_root = tmp_path / "candidate"
    portfolio.write_report(REPOSITORY, PRIVATE, report_root)
    portfolio.verify_report(report_root, REPOSITORY, PRIVATE)
    routed = candidate.write_candidate(REPOSITORY, PRIVATE, candidate_root)
    assert candidate.verify_candidate(candidate_root, REPOSITORY, PRIVATE) == routed
    assert routed["reviewed_native_versions"] == 500
    assert routed["source_complete"] is routed["audit_task_credit"] is False
    assert routed["fresh_audit_pair_created"] is False
    for side in "AB":
        row = routed["sides"][side]
        assert (row["component_count"], row["scenario_source_component_count"]) == (41, 28)
        assert row["system_alias_count"] == 255
        assert row["source_pins"][-1]["source"] == "iam005emergency"


def test_iam_review_byte_pin_drift_fails_closed(monkeypatch):
    monkeypatch.setattr(portfolio, "IAM_REVIEW_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="byte pin"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)


def test_recomputed_v5_source_row_drift_fails_closed(monkeypatch):
    changed = deepcopy(portfolio.prior.verify_all(REPOSITORY, private_repository=PRIVATE))
    changed["sources"][0]["source"] = "UNREVIEWED_SOURCE_ROW"
    monkeypatch.setattr(portfolio.prior, "verify_all", lambda *args, **kwargs: changed)
    with pytest.raises(PortfolioVerificationError, match="Recomputed V5 prefix"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)


def test_recomputed_v5_candidate_drift_fails_closed(monkeypatch):
    original = candidate.prior.candidate_profiles

    def changed(*args, **kwargs):
        diagnostic, profiles = original(*args, **kwargs)
        profiles = deepcopy(profiles)
        profiles["A"]["source_pins"][0]["source"] = "UNREVIEWED_PIN"
        return diagnostic, profiles

    monkeypatch.setattr(candidate.prior, "candidate_profiles", changed)
    with pytest.raises(CandidateRegistryError, match="Recomputed V5 candidate"):
        candidate.candidate_profiles(REPOSITORY, PRIVATE)
