"""Selected emergency replay collection preserves V14 access semantics."""

from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_collection_probe_v15 as probe
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_candidate_registry_v14 import (
    candidate_profiles as prior_profiles,
)
from enterprise.audit_suite.fictional_2027_candidate_registry_v15 import candidate_profiles
from enterprise.audit_suite.fictional_2027_collection_probe_v14 import (
    _component_rows as prior_component_rows,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
ZERO = {"grants": 0, "collections": 0, "access_events": 0}


@pytest.fixture(scope="module")
def profiles() -> dict:
    _, selected = candidate_profiles(REPOSITORY, PRIVATE)
    return selected


def test_exact_v14_route_prefix_and_emergency_terminal_pins(profiles: dict) -> None:
    _, prior = prior_profiles(REPOSITORY, PRIVATE)
    for side, branch in (("A", "EMERGENCY-REPLAY-CLEAN"), ("B", "EMERGENCY-REPLAY-MESSY")):
        rows = probe._component_rows(profiles[side])
        assert len(rows) == 37
        assert rows[:36] == prior_component_rows(prior[side])
        source_id, pin, component = rows[-1]
        assert source_id == "scenario-emergencyreplay"
        assert pin["physical_branch"] == component["branch"] == branch
        assert pin["system_count"] == len(component["systems"]) == 9
        assert pin["inherited_audit_journals"] == ZERO
        changed = dict(profiles[side])
        changed["source_pins"] = [dict(item) for item in profiles[side]["source_pins"]]
        changed["source_pins"][-1]["database_sha256"] = "0" * 64
        with pytest.raises(CandidateRegistryError, match="emergency replay source route differs"):
            probe._component_rows(changed)


def test_reviewed_v15_candidate_pin_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V15 package hash differs"):
        probe._reviewed_v15(REPOSITORY, PRIVATE)


def test_reviewed_v14_collector_pin_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "V14_COLLECTOR_REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V14 collector byte pin differs"):
        probe._reviewed_v14_collector(REPOSITORY, PRIVATE)


def test_terminal_marker_is_payload_free_and_messy_open(profiles: dict) -> None:
    for side, messy in (("A", False), ("B", True)):
        _, _, component = probe._component_rows(profiles[side])[-1]
        origin = Path(component["root"]) / "company.sqlite3"
        ref, _ = probe._native(origin, component)
        assert (ref["system"], ref["record"], ref["version"]) == (
            ("exception_register", "EXCEPTION-STATUS", 1)
            if messy
            else ("replay_review", "REVIEW", 1)
        )
        selected = probe._emergency_final(origin, ref)
        assert selected["selected_population_count"] == 1
        assert selected["payload_free"] is True
        assert selected["messy_local_exception_open"] is messy
        assert selected["messy_upstream_gates_open"] is messy
        for key in ("actual_phi_processing", "deployed_recovery_proven", "audit_task_credit"):
            assert selected[key] is False
        with pytest.raises(CandidateRegistryError, match="exact emergency replay terminal"):
            probe._emergency_final(origin, dict(ref, record="FASTPATH-DENY"))


def test_semantic_prefix_covers_prior_adverse_cases() -> None:
    assert set(probe._semantic_prefix_keys()) >= {
        "native_identity",
        "inherited_journal_sha256",
        "cc52_selected_case",
        "sec001_selected_case",
        "eth001_selected_case",
        "addressable_pending_case",
        "pol004_selected_case",
    }
