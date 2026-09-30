"""V4's partial native source roster and distinct REC003 snapshot routing."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v3 as previous_candidate
from enterprise.audit_suite import fictional_2027_candidate_registry_v4 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v3 as previous_portfolio
from enterprise.audit_suite import fictional_2027_source_portfolio_v4 as portfolio

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def test_v4_exact_prefix_and_reviewed_private_sources():
    old = previous_portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
    report = portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
    assert report["sources"][:21] == old["sources"]
    assert [row["source"] for row in report["sources"][21:]] == ["rec003", "sec005", "ass001002"]
    assert (
        report["source_count"],
        report["native_versions"],
        report["source_component_count"],
    ) == (24, 401, 25)
    rec = report["sources"][21]
    assert rec["branch_versions"] == {"local-data-quality-a": 11, "local-data-quality-b": 11}
    assert rec["inherited_audit_journals"] == {"grants": 12, "collections": 22, "access_events": 25}
    assert report["source_complete"] is report["audit_task_credit"] is False


def test_candidate_has_one_rec_snapshot_per_profile_and_no_credit(tmp_path):
    tmp_path.chmod(0o700)
    old, old_profiles = previous_candidate.candidate_profiles(REPOSITORY, PRIVATE)
    assert old["source_count"] == 21
    portfolio_root = tmp_path / "portfolio"
    assert portfolio.write_report(REPOSITORY, PRIVATE, portfolio_root) == portfolio.verify_report(
        portfolio_root, REPOSITORY, PRIVATE
    )
    root = tmp_path / "candidate"
    report = candidate.write_candidate(REPOSITORY, PRIVATE, root)
    assert report == candidate.verify_candidate(root, REPOSITORY, PRIVATE)
    for side, branch in (("A", "local-data-quality-a"), ("B", "local-data-quality-b")):
        row = report["sides"][side]
        assert (
            row["component_count"],
            row["scenario_source_component_count"],
            row["system_alias_count"],
        ) == (38, 25, 227)
        assert row["source_pins"][:22] == old_profiles[side]["source_pins"]
        rec = [pin for pin in row["source_pins"] if pin["source"] == "rec003"]
        assert len(rec) == 1 and rec[0]["root_locator"] == "snapshot://" + side
        assert rec[0]["physical_branch"] == branch
        registry = json.loads((root / f"{side}.json").read_text())
        assert registry["components"]["scenario-rec003-dq"]["branch"] == branch
        assert len(registry["components"]) == 38
    assert report["source_complete"] is report["audit_task_credit"] is False
    assert report["grants_or_collections_created"] is False
    data = json.loads((root / "REPORT.json").read_text())
    data["source_complete"] = True
    (root / "REPORT.json").write_text(json.dumps(data))
    with pytest.raises(candidate.CandidateRegistryError, match="report differs"):
        candidate.verify_candidate(root, REPOSITORY, PRIVATE)


def test_rec003_inherited_journal_drift_is_rejected(monkeypatch):
    original = portfolio._frozen_rows

    def wrong(path):
        native, systems, journals = original(path)
        if "company-rec003-native-snapshot" in str(path):
            journals = {**journals, "collections": 23}
        return native, systems, journals

    monkeypatch.setattr(portfolio, "_frozen_rows", wrong)
    with pytest.raises(portfolio.PortfolioVerificationError, match="journal baseline"):
        portfolio._rec003(REPOSITORY, PRIVATE)


def test_standard_source_access_journal_is_rejected(monkeypatch):
    original = portfolio._frozen_rows

    def wrong(path):
        native, systems, journals = original(path)
        return native, systems, {**journals, "grants": 1}

    monkeypatch.setattr(portfolio, "_frozen_rows", wrong)
    with pytest.raises(portfolio.PortfolioVerificationError, match="zero-journal"):
        portfolio._standard(portfolio.STANDARD[0], REPOSITORY, PRIVATE)
