"""Reviewed SEC001 extends only the exact partial V11 portfolio and routing."""

from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v12 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v12 as portfolio
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def v11():
    return portfolio._v11_review(PRIVATE)


@pytest.fixture(scope="module")
def diagnostic():
    return portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)


@pytest.fixture(scope="module")
def profiles():
    return candidate.candidate_profiles(REPOSITORY, PRIVATE)


def test_exact_reviewed_v11_source_and_candidate_prefix(v11, diagnostic, profiles):
    old_report, old_candidates, _ = v11
    assert portfolio.prior.verify_all(REPOSITORY, private_repository=PRIVATE) == old_report
    assert diagnostic["sources"][:32] == old_report["sources"]
    assert diagnostic["v11_review_sha256"] == portfolio.V11_REVIEW_SHA
    assert (
        diagnostic["source_count"],
        diagnostic["native_versions"],
        diagnostic["source_component_count"],
    ) == (33, 755, 34)
    for side in "AB":
        old = old_candidates["REPORT.json"]["sides"][side]
        new = profiles[1][side]
        assert new["source_pins"][:33] == old["source_pins"]
        assert new["manifest"]["components"] == {
            **old_candidates[f"{side}.json"]["components"],
            "scenario-sec001transfer": new["manifest"]["components"]["scenario-sec001transfer"],
        }
        assert new["base_registry_sha256"] == old["base_registry_sha256"]


def test_sec001_reviewed_native_source_and_false_actual_claims(diagnostic, profiles):
    row = diagnostic["sources"][-1]
    assert row["source"] == "sec001transfer"
    assert row["review_sha256"] == portfolio.SEC_REVIEW_SHA
    assert row["database_sha256"] == {"native": portfolio.SEC_DB_SHA}
    assert row["native_versions"] == 26
    assert row["branch_versions"] == {"SEC001-XFER-CLEAN": 10, "SEC001-XFER-MESSY": 16}
    assert row["ledger_system_counts"] == {"native": 5}
    assert row["inherited_audit_journals"] == {
        "grants": 0,
        "collections": 0,
        "access_events": 0,
    }
    assert row["selected_payload_count"] == 1
    assert row["selected_authored_clause"] == portfolio.SEC_CLAUSE
    assert row["messy_blocked_wrong_endpoint"] is True
    assert row["messy_false_close_corrected"] is True
    assert row["messy_historical_exception_open"] is True
    for key in (
        "actual_customer_or_phi_data",
        "actual_deployed_endpoint_or_channel",
        "actual_network_transmission",
        "enterprise_transfer_standard_approved",
        "independent_approval",
        "population_complete",
        "audit_task_credit",
    ):
        assert row[key] is False
    assert diagnostic["source_complete"] is diagnostic["audit_task_credit"] is False
    assert diagnostic["fresh_audit_pair_created"] is False
    for side, branch in (("A", "SEC001-XFER-CLEAN"), ("B", "SEC001-XFER-MESSY")):
        profile = profiles[1][side]
        assert (len(profile["manifest"]["components"]), len(profile["source_pins"])) == (47, 34)
        assert sum(len(x["systems"]) for x in profile["manifest"]["components"].values()) == 290
        assert profile["source_pins"][-1] == {
            "source": "sec001transfer",
            "ledger": "native",
            "source_review_sha256": portfolio.SEC_REVIEW_SHA,
            "manifest_sha256": portfolio.SEC_MANIFEST_SHA,
            "receipt_sha256": portfolio.SEC_RECEIPT_SHA,
            "database_sha256": portfolio.SEC_DB_SHA,
            "physical_company": "SABLE-HARBOR-REFERENCE",
            "physical_branch": branch,
            "system_count": 5,
            "inherited_audit_journals": {"grants": 0, "collections": 0, "access_events": 0},
        }
        component = profile["manifest"]["components"]["scenario-sec001transfer"]
        assert component["branch"] == branch
        assert component["systems"] == [
            "exception_register",
            "receipt_handling",
            "security_path",
            "transfer_authority",
            "transfer_operations",
        ]


def test_private_outputs_reperform_exactly(tmp_path):
    report = portfolio.write_report(REPOSITORY, PRIVATE, tmp_path / "portfolio")
    assert portfolio.verify_report(tmp_path / "portfolio", REPOSITORY, PRIVATE) == report
    routed = candidate.write_candidate(REPOSITORY, PRIVATE, tmp_path / "candidate")
    assert candidate.verify_candidate(tmp_path / "candidate", REPOSITORY, PRIVATE) == routed
    assert routed["reviewed_native_versions"] == 755
    assert routed["v11_independent_review_sha256"] == portfolio.V11_REVIEW_SHA
    assert routed["source_complete"] is routed["audit_task_credit"] is False
    assert routed["fresh_audit_pair_created"] is False
    assert routed["grants_or_collections_created"] is False
    for side in "AB":
        assert (
            routed["sides"][side]["component_count"],
            routed["sides"][side]["scenario_source_component_count"],
            routed["sides"][side]["system_alias_count"],
        ) == (47, 34, 290)


def test_same_count_v11_source_drift_fails_closed(monkeypatch):
    changed = deepcopy(portfolio.prior.verify_all(REPOSITORY, private_repository=PRIVATE))
    changed["sources"][0]["source"] = "UNREVIEWED_SOURCE_ROW"
    monkeypatch.setattr(portfolio.prior, "verify_all", lambda *args, **kwargs: changed)
    with pytest.raises(PortfolioVerificationError, match="Recomputed V11 source prefix"):
        portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)


def test_review_pin_and_source_verifier_drift_fail_closed(monkeypatch):
    monkeypatch.setattr(portfolio, "SEC_REVIEW_SHA", "0" * 64)
    with pytest.raises(PortfolioVerificationError, match="pins pending"):
        portfolio._sec_source(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    monkeypatch.setattr(portfolio.transfer, "verify", lambda *args, **kwargs: {})
    with pytest.raises(PortfolioVerificationError, match="native source verifier"):
        portfolio._sec_source(REPOSITORY, PRIVATE)


def test_same_count_v11_candidate_pin_drift_fails_closed(monkeypatch):
    original = candidate.prior.candidate_profiles

    def changed(*args, **kwargs):
        diagnostic, profiles = original(*args, **kwargs)
        profiles = deepcopy(profiles)
        profiles["A"]["source_pins"][0]["source"] = "UNREVIEWED_PIN"
        return diagnostic, profiles

    monkeypatch.setattr(candidate.prior, "candidate_profiles", changed)
    with pytest.raises(CandidateRegistryError, match="Exact reviewed V11 candidate row/pin"):
        candidate.candidate_profiles(REPOSITORY, PRIVATE)
