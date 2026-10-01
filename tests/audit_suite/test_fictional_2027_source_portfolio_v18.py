"""V18 retains reviewed V17 bytes and adds only bounded LEG/DAT sources."""

from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v18 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v18 as portfolio
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


@pytest.fixture(scope="module")
def reviewed():
    old, old_candidates, _ = portfolio.reviewed_v17(REPOSITORY, PRIVATE)
    additions = [portfolio._qualify(REPOSITORY, PRIVATE, item) for item in portfolio.SOURCES]
    return old, old_candidates, additions


def test_exact_reviewed_prefix_and_bounded_additions(reviewed):
    old, _, additions = reviewed
    report = portfolio._compose(old, additions)
    assert report["schema"] == portfolio.SCHEMA
    assert report["sources"][:39] == old["sources"]
    assert [row["source"] for row in report["sources"][-2:]] == ["legprovision", "dat002rights"]
    assert (
        report["source_count"],
        report["native_versions"],
        report["source_component_count"],
    ) == (41, 948, 42)
    assert all(
        report[key] is False
        for key in ("source_complete", "fresh_audit_pair_created", "audit_task_credit")
    )
    for row in additions:
        assert row["inherited_audit_journals"] == {name: 0 for name in portfolio.JOURNALS}
        assert row["source_complete"] is row["audit_task_credit"] is False
    leg, dat = additions
    assert leg["native_versions"] == 40
    assert leg["provision_locator_count_per_branch"] == 18
    assert leg["bounded_authored_provision_candidates_per_side"] == 16
    assert leg["remaining_unmodeled_authored_candidates_per_side"] == 50
    assert len(leg["open_historical_exception_ids"]["MESSY"]) == 2
    assert leg["2027_legal_text_verified"] is False
    assert dat["native_versions"] == 11
    assert dat["branch_versions"] == {"DAT002-RIGHTS-CLEAN": 5, "DAT002-RIGHTS-MESSY": 6}
    assert dat["open_scope_exception_ids"]["MESSY"] == [portfolio.dat.EXCEPTION_ID]
    assert dat["actual_requests_or_external_responses"] == 0
    assert dat["complete_record_or_period_population"] is False


def test_candidate_appends_exact_two_components_and_pins(reviewed):
    old, old_candidates, _ = reviewed
    diagnostic, profiles = candidate.candidate_profiles(REPOSITORY, PRIVATE)
    assert diagnostic["sources"][:39] == old["sources"]
    for side, scenario, aliases in (("A", "CLEAN", 353), ("B", "MESSY", 354)):
        before = old_candidates[f"{side}.json"]["components"]
        after = profiles[side]["manifest"]["components"]
        assert {key: after[key] for key in before} == before
        assert list(after)[-2:] == ["scenario-legprovision", "scenario-dat002rights"]
        assert len(after) == 55
        assert len(profiles[side]["source_pins"]) == 42
        assert (
            profiles[side]["source_pins"][:40]
            == old_candidates["REPORT.json"]["sides"][side]["source_pins"]
        )
        assert [pin["source"] for pin in profiles[side]["source_pins"][-2:]] == [
            "legprovision",
            "dat002rights",
        ]
        assert sum(len(component["systems"]) for component in after.values()) == aliases
        assert after["scenario-dat002rights"]["branch"] == portfolio.dat.BRANCHES[scenario]
        assert len(after["scenario-dat002rights"]["systems"]) == (5 if side == "A" else 6)


def test_tampered_prefix_source_and_promotion_are_rejected(reviewed, monkeypatch):
    old, _, additions = reviewed
    changed = deepcopy(old)
    changed["native_versions"] = 898
    with pytest.raises(PortfolioVerificationError, match="extension boundary"):
        portfolio._compose(changed, additions)
    changed = deepcopy(additions)
    changed[1]["source"] = "not-dat002rights"
    with pytest.raises(PortfolioVerificationError, match="extension boundary"):
        portfolio._compose(old, changed)
    sources = list(portfolio.SOURCES)
    sources[1] = {**sources[1], "receipt_sha": "0" * 64}
    with pytest.raises(PortfolioVerificationError, match="byte pin"):
        portfolio._qualify(REPOSITORY, PRIVATE, sources[1])
    monkeypatch.setattr(portfolio, "V17_REVIEW_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="byte pin"):
        portfolio.reviewed_v17(REPOSITORY, PRIVATE)


def test_read_only_build_matches_snapshot_composition(reviewed):
    old, _, additions = reviewed
    assert portfolio.verify_all(REPOSITORY, private_repository=PRIVATE) == portfolio._compose(
        old, additions
    )


def test_private_report_and_candidate_round_trip(tmp_path, monkeypatch, reviewed):
    old, _, additions = reviewed
    diagnostic = portfolio._compose(old, additions)
    _, profiles = candidate.candidate_profiles(REPOSITORY, PRIVATE)
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(portfolio, "verify_all", lambda *_args, **_kwargs: diagnostic)
    monkeypatch.setattr(candidate, "candidate_profiles", lambda *_args: (diagnostic, profiles))
    report_root = parent / "report"
    candidate_root = parent / "candidate"
    assert portfolio.write_report(REPOSITORY, PRIVATE, report_root) == diagnostic
    assert (
        candidate.write_candidate(REPOSITORY, PRIVATE, candidate_root)["reviewed_native_versions"]
        == 948
    )
    assert (
        candidate.verify_candidate(candidate_root, REPOSITORY, PRIVATE)["sides"]["A"][
            "system_alias_count"
        ]
        == 353
    )
    assert (
        candidate.verify_candidate(candidate_root, REPOSITORY, PRIVATE)["sides"]["B"][
            "system_alias_count"
        ]
        == 354
    )
    (report_root / "REPORT.json").write_text("{}")
    with pytest.raises(PortfolioVerificationError, match="report differs"):
        portfolio.verify_report(report_root, REPOSITORY, PRIVATE)
