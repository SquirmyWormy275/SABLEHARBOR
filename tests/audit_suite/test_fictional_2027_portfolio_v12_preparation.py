"""V12 remains blocked while its reviewed SEC001 main source pins are pending."""

from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v12 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v12 as portfolio
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_source_portfolio import PortfolioVerificationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def _synthetic_sec_row() -> dict:
    return {
        "source": "sec001transfer",
        "native_versions": 26,
        "branch_versions": {"SEC001-XFER-CLEAN": 10, "SEC001-XFER-MESSY": 16},
        "ledger_system_counts": {"native": 5},
        "inherited_audit_journals": {"grants": 0, "collections": 0, "access_events": 0},
        "selected_payload_count": 1,
        "messy_historical_exception_open": True,
        "actual_network_transmission": False,
        "population_complete": False,
        "audit_task_credit": False,
    }


def test_all_production_paths_fail_before_creating_output(tmp_path: Path) -> None:
    assert portfolio.SEC_REVIEW_SHA is None
    for operation, output in (
        (lambda: portfolio.verify_all(REPOSITORY, private_repository=PRIVATE), None),
        (lambda: candidate.candidate_profiles(REPOSITORY, PRIVATE), None),
        (lambda: portfolio.write_report(REPOSITORY, PRIVATE, tmp_path / "portfolio"), "portfolio"),
        (
            lambda: candidate.write_candidate(REPOSITORY, PRIVATE, tmp_path / "candidate"),
            "candidate",
        ),
    ):
        with pytest.raises(PortfolioVerificationError, match="main source/review pins pending"):
            operation()
        if output:
            assert not (tmp_path / output).exists()


def test_unaccepted_review_label_cannot_unlock_pins(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "SEC_REVIEW_SHA",
        "SEC_MANIFEST_SHA",
        "SEC_RECEIPT_SHA",
        "SEC_DB_SHA",
        "SEC_MODULE_SHA",
    ):
        monkeypatch.setattr(portfolio, name, "a" * 64)
    monkeypatch.setattr(portfolio, "SEC_INTEGRATION_COMMIT", "b" * 40)
    monkeypatch.setattr(portfolio, "SEC_REVIEW_VERDICT", "PENDING_INDEPENDENT_REVIEW")
    with pytest.raises(PortfolioVerificationError, match="main source/review pins pending"):
        portfolio._require_sec_pins()


def test_full_reviewed_v11_input_prefix_is_exact() -> None:
    report, manifests, _ = portfolio._v11_review(PRIVATE)
    assert (
        report["source_count"],
        report["native_versions"],
        report["source_component_count"],
    ) == (
        32,
        729,
        33,
    )
    assert report["sources"][-1]["source"] == "eth001conduct"
    for side in "AB":
        selected = manifests["REPORT.json"]["sides"][side]
        assert (
            selected["component_count"],
            selected["scenario_source_component_count"],
            selected["system_alias_count"],
            len(selected["source_pins"]),
        ) == (46, 33, 285, 33)
        assert len(manifests[f"{side}.json"]["components"]) == 46


def test_prepared_source_shape_preserves_v11_prefix_and_claims() -> None:
    old, _, _ = portfolio._v11_review(PRIVATE)
    shaped = portfolio._compose_portfolio(old, _synthetic_sec_row())
    assert shaped["sources"][:32] == old["sources"]
    assert shaped["sources"][-1]["source"] == "sec001transfer"
    assert (
        shaped["source_count"],
        shaped["native_versions"],
        shaped["source_component_count"],
    ) == (33, 755, 34)
    assert (
        shaped["source_complete"]
        is shaped["fresh_audit_pair_created"]
        is shaped["audit_task_credit"]
        is False
    )
    changed = deepcopy(_synthetic_sec_row())
    changed["actual_network_transmission"] = True
    with pytest.raises(PortfolioVerificationError, match="selected source scope"):
        portfolio._compose_portfolio(old, changed)
    changed = deepcopy(old)
    changed["sources"][0]["source"] = "UNREVIEWED"
    changed["source_count"] = 31
    with pytest.raises(PortfolioVerificationError, match="V11 source count"):
        portfolio._compose_portfolio(changed, _synthetic_sec_row())


def test_prepared_candidate_shape_is_47_components_34_pins_290_aliases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old, manifests, _ = portfolio._v11_review(PRIVATE)
    selected = {}
    for side in "AB":
        row = manifests["REPORT.json"]["sides"][side]
        selected[side] = {
            "manifest": manifests[f"{side}.json"],
            "source_pins": row["source_pins"],
            "profile_id": row["profile_id"],
            "base_registry_sha256": row["base_registry_sha256"],
        }
    diagnostic = portfolio._compose_portfolio(old, _synthetic_sec_row())
    monkeypatch.setattr(portfolio, "_require_sec_pins", lambda: None)
    monkeypatch.setattr(portfolio, "verify_all", lambda *args, **kwargs: diagnostic)
    monkeypatch.setattr(candidate.prior, "candidate_profiles", lambda *args: (old, selected))

    def component(_private: Path, scenario: str, _row: dict) -> tuple[dict, dict]:
        branch = portfolio.SEC_BRANCHES[("CLEAN", "MESSY").index(scenario)]
        return (
            {
                "root": "/pending-reviewed-source",
                "company": "SABLE-HARBOR-REFERENCE",
                "branch": branch,
                "namespace": "F27SEC001TRANSFER",
                "systems": [
                    "exception_register",
                    "receipt_handling",
                    "security_path",
                    "transfer_authority",
                    "transfer_operations",
                ],
            },
            {"source": "sec001transfer", "physical_branch": branch},
        )

    monkeypatch.setattr(candidate, "_component_for_sec", component)
    result, profiles = candidate.candidate_profiles(REPOSITORY, PRIVATE)
    assert result == diagnostic
    files = {}
    for side in "AB":
        profile = profiles[side]
        assert profile["source_pins"][:33] == selected[side]["source_pins"]
        assert len(profile["source_pins"]) == 34
        assert len(profile["manifest"]["components"]) == 47
        assert (
            sum(len(item["systems"]) for item in profile["manifest"]["components"].values()) == 290
        )
        path = tmp_path / f"{side}.json"
        path.write_text("prepared-shape-only\n")
        files[side] = path
    report = candidate._report(diagnostic, profiles, files)
    assert report["reviewed_native_versions"] == 755
    for side in "AB":
        assert (
            report["sides"][side]["component_count"],
            report["sides"][side]["scenario_source_component_count"],
            report["sides"][side]["system_alias_count"],
        ) == (47, 34, 290)
    assert (
        report["source_complete"]
        is report["fresh_audit_pair_created"]
        is report["audit_task_credit"]
        is report["grants_or_collections_created"]
        is False
    )
    profiles["A"]["manifest"]["components"]["scenario-sec001transfer"]["systems"].append(
        "UNREVIEWED"
    )
    with pytest.raises(CandidateRegistryError, match="selected aliases"):
        candidate._report(diagnostic, profiles, files)
