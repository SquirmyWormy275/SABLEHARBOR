"""Reviewed V4 prefix and two newly reviewed V5 source routes stay partial."""

from dataclasses import replace
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v5 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v5 as portfolio
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def test_exact_reviewed_roster_and_partial_limits():
    report = portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
    assert (
        report["source_count"],
        report["native_versions"],
        report["source_component_count"],
    ) == (
        26,
        475,
        27,
    )
    assert [row["source"] for row in report["sources"][-2:]] == ["govapp", "sec005operated"]
    assert [row["native_versions"] for row in report["sources"][-2:]] == [34, 40]
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
    assert routed["reviewed_native_versions"] == 475
    assert routed["source_complete"] is routed["audit_task_credit"] is False
    assert routed["fresh_audit_pair_created"] is False
    for side in "AB":
        row = routed["sides"][side]
        assert (row["component_count"], row["scenario_source_component_count"]) == (40, 27)
        assert row["system_alias_count"] == 246
        assert [pin["source"] for pin in row["source_pins"][-2:]] == [
            "govapp",
            "sec005operated",
        ]


def test_unreviewed_attachment_and_review_pin_drift_fail_closed(tmp_path, monkeypatch):
    root = tmp_path / "portfolio"
    portfolio.write_report(REPOSITORY, PRIVATE, root)
    extra = root / "unreviewed.txt"
    extra.write_text("not reviewed")
    extra.chmod(0o600)
    with pytest.raises(PortfolioVerificationError, match="one-file"):
        portfolio.verify_report(root, REPOSITORY, PRIVATE)
    monkeypatch.setattr(portfolio, "V4_REVIEW_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="byte pin"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)


def test_new_source_byte_pin_drift_fails_closed(monkeypatch):
    changed = replace(portfolio.STANDARD[1], database_sha256="0" * 64)
    monkeypatch.setattr(portfolio, "STANDARD", (portfolio.STANDARD[0], changed))
    with pytest.raises(PortfolioVerificationError, match="byte pin"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
