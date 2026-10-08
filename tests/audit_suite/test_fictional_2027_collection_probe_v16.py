"""Selected PRD concern collection preserves V15 access semantics."""

from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_collection_probe_v16 as probe
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_candidate_registry_v15 import (
    candidate_profiles as prior_profiles,
)
from enterprise.audit_suite.fictional_2027_candidate_registry_v16 import candidate_profiles
from enterprise.audit_suite.fictional_2027_collection_probe_v15 import (
    _component_rows as prior_component_rows,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
ZERO = {"grants": 0, "collections": 0, "access_events": 0}


@pytest.fixture(scope="module")
def profiles() -> dict:
    _, selected = candidate_profiles(REPOSITORY, PRIVATE)
    return selected


def test_exact_v15_route_prefix_and_concern_terminal_pins(profiles: dict) -> None:
    _, prior = prior_profiles(REPOSITORY, PRIVATE)
    for side, branch in (("A", "PRD-CONCERN-CLEAN"), ("B", "PRD-CONCERN-MESSY")):
        rows = probe._component_rows(profiles[side])
        assert len(rows) == 38
        assert rows[:37] == prior_component_rows(prior[side])
        source_id, pin, component = rows[-1]
        assert source_id == "scenario-prdconcern"
        assert pin["physical_branch"] == component["branch"] == branch
        assert pin["system_count"] == len(component["systems"]) == 10
        assert pin["inherited_audit_journals"] == ZERO
        changed = dict(profiles[side])
        changed["source_pins"] = [dict(item) for item in profiles[side]["source_pins"]]
        changed["source_pins"][-1]["database_sha256"] = "0" * 64
        with pytest.raises(CandidateRegistryError, match="PRD concern source route differs"):
            probe._component_rows(changed)


def test_concern_terminal_retains_held_and_open_without_delivery(profiles: dict) -> None:
    for side, messy in (("A", False), ("B", True)):
        _, _, component = probe._component_rows(profiles[side])[-1]
        origin = Path(component["root"]) / "company.sqlite3"
        ref, _ = probe._native(origin, component)
        assert (ref["system"], ref["record"], ref["version"]) == (
            ("exception_register", "EXCEPTION-OPEN", 1)
            if messy
            else ("reconciliation", "RECON-01", 1)
        )
        selected = probe._prd_concern_final(origin, ref)
        assert selected["historical_exception_open"] is messy
        assert selected["claimant_customer_identity_verified"] is False
        assert selected["company_outbound_delivery_accepted"] is False
        assert selected["separate_customer_acknowledgment_exists"] is False
        assert selected["actual_phi_processing"] is False
        assert selected["authored_communication_clause_satisfied"] is False
        assert selected["audit_task_credit"] is False
        with pytest.raises(CandidateRegistryError, match="exact PRD concern selected"):
            probe._prd_concern_final(origin, dict(ref, record="ATTEMPT-01"))


def test_review_pin_gate_fails_closed_until_reviewed_main(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "REVIEW_SHA256", None)
    with pytest.raises(CandidateRegistryError, match="main independent review pins are pending"):
        probe._reviewed_v16(REPOSITORY, PRIVATE)


def test_reviewed_v15_collector_pin_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "V15_COLLECTOR_REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V15 collector byte pin differs"):
        probe._reviewed_v15_collector(REPOSITORY, PRIVATE)


def test_reviewed_v15_collector_verdict_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    original = probe._json

    def altered(path: Path):
        data = original(path)
        if path.name == "REVIEW.json" and "company-collection-probe-v15" in str(path):
            return {**data, "verdict": "NOT_REVIEWED"}
        return data

    monkeypatch.setattr(probe, "_json", altered)
    with pytest.raises(CandidateRegistryError, match="V15 collector verdict differs"):
        probe._reviewed_v15_collector(REPOSITORY, PRIVATE)


def test_semantic_prefix_includes_prior_emergency_selected_case() -> None:
    assert set(probe._semantic_prefix_keys()) >= {
        "native_identity",
        "inherited_journal_sha256",
        "cc52_selected_case",
        "sec001_selected_case",
        "eth001_selected_case",
        "addressable_pending_case",
        "pol004_selected_case",
        "emergency_selected_case",
    }
