"""Reviewed ENG005 and GOV sources extend only the sealed V16 partial prefix."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v17 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v17 as portfolio
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
RUN = REPOSITORY / "enterprise/generated/audit-suite/company-source-portfolio-v17-2026-10-01"
RUN_ROLE = "main" if REPOSITORY.resolve() == PRIVATE.resolve() else "isolated"
SOURCE_RUN = RUN / f"{RUN_ROLE}-report-v1"
CANDIDATE_RUN = RUN / f"{RUN_ROLE}-candidate-v1"


@pytest.fixture(scope="module")
def reviewed_v16():
    return portfolio.reviewed_v16(REPOSITORY, PRIVATE)


@pytest.fixture(scope="module")
def diagnostic():
    return portfolio.verify_report(SOURCE_RUN, REPOSITORY, PRIVATE)


@pytest.fixture(scope="module")
def routed():
    return candidate.verify_candidate(CANDIDATE_RUN, REPOSITORY, PRIVATE)


def test_exact_reviewed_v16_source_prefix_and_no_credit(reviewed_v16, diagnostic):
    prior, _, _ = reviewed_v16
    assert diagnostic["sources"][:37] == prior["sources"]
    assert diagnostic["v16_review_sha256"] == portfolio.V16_REVIEW_SHA
    assert (
        diagnostic["source_count"],
        diagnostic["native_versions"],
        diagnostic["source_component_count"],
    ) == (39, 897, 40)
    assert diagnostic["source_complete"] is diagnostic["audit_task_credit"] is False
    assert diagnostic["fresh_audit_pair_created"] is False


def test_two_reviewed_native_sources_keep_open_limits(diagnostic):
    eng, gov = diagnostic["sources"][-2:]
    assert eng["source"] == "eng005operating"
    assert eng["review_sha256"] == portfolio.SOURCES[0]["review_sha"]
    assert eng["branch_versions"] == {"ENG005-OPERATED-CLEAN": 12, "ENG005-OPERATED-MESSY": 22}
    assert eng["ledger_system_counts"] == {"native": 10}
    assert eng["open_exception_counts"] == {"CLEAN": 0, "MESSY": 2}
    assert eng["corporate_emergency_authority_status"] == "NOT_EVIDENCED_OPEN"
    for key in (
        "real_deployment",
        "actual_phi",
        "authored_eng005_clause_satisfied",
        "enterprise_policy_approved",
        "full_period_or_enterprise_change_population_complete",
        "source_complete",
        "audit_task_credit",
    ):
        assert eng[key] is False
    assert eng["external_packets_or_writes"] == 0
    assert gov["source"] == "govoversight"
    assert gov["review_sha256"] == portfolio.SOURCES[1]["review_sha"]
    assert gov["branch_versions"] == {"GOV-OVERSIGHT-CLEAN": 9, "GOV-OVERSIGHT-MESSY": 14}
    assert gov["ledger_system_counts"] == {"native": 11}
    assert gov["clean_selected_finding_status"] == "CLOSED_SELECTED_ONLY"
    assert gov["messy_historical_governance_exception_status"] == "OPEN"
    assert gov["messy_historical_sec003_exception_status"] == "OPEN"
    for key in (
        "actual_board_meeting",
        "adopted_minutes",
        "legal_quorum_established",
        "actual_phi_processing",
        "authored_cc12_clause_satisfied",
        "complete_oversight_population",
        "independent_assurance_completed",
        "source_complete",
        "audit_task_credit",
    ):
        assert gov[key] is False
    assert gov["real_external_messages_sent"] == 0
    for row in (eng, gov):
        assert row["inherited_audit_journals"] == {
            "grants": 0,
            "collections": 0,
            "access_events": 0,
        }
        receipt = json.loads((PRIVATE / portfolio.BASE / row["run"] / "RECEIPT.json").read_text())
        for records in receipt["records"].values():
            assert all(record["event_at"] != record["imported_at"] for record in records)
            assert all(record["imported_at"].startswith("2026-") for record in records)


def test_exact_v16_candidate_prefix_and_two_selected_components(reviewed_v16, routed):
    _, old_candidates, _ = reviewed_v16
    assert routed["reviewed_native_versions"] == 897
    assert routed["v16_independent_review_sha256"] == portfolio.V16_REVIEW_SHA
    assert routed["source_complete"] is routed["audit_task_credit"] is False
    assert routed["fresh_audit_pair_created"] is False
    assert routed["grants_or_collections_created"] is False
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        old_manifest = old_candidates[f"{side}.json"]
        manifest = json.loads((CANDIDATE_RUN / f"{side}.json").read_text())
        additions = {
            name: manifest["components"][name]
            for name in (
                "scenario-eng005operating",
                "scenario-govoversight",
            )
        }
        assert manifest["components"] == {**old_manifest["components"], **additions}
        old_side = old_candidates["REPORT.json"]["sides"][side]
        new_side = routed["sides"][side]
        assert new_side["source_pins"][:38] == old_side["source_pins"]
        assert new_side["base_registry_sha256"] == old_side["base_registry_sha256"]
        assert (
            new_side["component_count"],
            new_side["source_cohort_count"],
            new_side["scenario_source_component_count"],
            new_side["system_alias_count"],
            len(new_side["source_pins"]),
        ) == (53, 39, 40, 345, 40)
        for selected, pin in zip(portfolio.SOURCES, new_side["source_pins"][-2:], strict=True):
            assert pin["source"] == selected["source"]
            assert pin["source_review_sha256"] == selected["review_sha"]
            assert pin["physical_branch"] == selected["module"].BRANCHES[scenario]
            assert pin["system_count"] == selected["systems"]
            assert pin["inherited_audit_journals"] == {
                "grants": 0,
                "collections": 0,
                "access_events": 0,
            }
            assert (
                additions["scenario-" + selected["source"]]["systems"]
                == (candidate.ALIASES[selected["source"]])
            )


def test_v16_review_byte_and_verdict_tamper_fail_closed(monkeypatch):
    monkeypatch.setattr(portfolio, "V16_REVIEW_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="byte pin differs"):
        portfolio.reviewed_v16(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    original = portfolio._read_json

    def altered(path: Path):
        value = original(path)
        if path.name == "REVIEW.json" and portfolio.V16_FOLDER in str(path):
            return {**value, "verdict": "NOT_REVIEWED"}
        return value

    monkeypatch.setattr(portfolio, "_read_json", altered)
    with pytest.raises(PortfolioVerificationError, match="Reviewed V16 prefix differs"):
        portfolio.reviewed_v16(REPOSITORY, PRIVATE)


def test_tracked_source_module_drift_fails_closed(monkeypatch):
    selected = {**portfolio.SOURCES[0], "module_sha": "0" * 64}
    with pytest.raises(PortfolioVerificationError, match="tracked module/spec"):
        portfolio._qualify(REPOSITORY, PRIVATE, selected)
