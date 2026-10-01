"""POL004 collector keeps V13 source access and pending procedure boundaries."""

from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_collection_probe_v14 as probe
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_candidate_registry_v13 import (
    candidate_profiles as prior_profiles,
)
from enterprise.audit_suite.fictional_2027_candidate_registry_v14 import candidate_profiles
from enterprise.audit_suite.fictional_2027_collection_probe_v13 import (
    _component_rows as prior_component_rows,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
ZERO = {"grants": 0, "collections": 0, "access_events": 0}


@pytest.fixture(scope="module")
def profiles() -> dict:
    _, selected = candidate_profiles(REPOSITORY, PRIVATE)
    return selected


def test_exact_v13_route_prefix_and_pol004_final_pins(profiles: dict) -> None:
    _, prior = prior_profiles(REPOSITORY, PRIVATE)
    for side, branch in (("A", "POL004-PROCEDURE-CLEAN"), ("B", "POL004-PROCEDURE-MESSY")):
        rows = probe._component_rows(profiles[side])
        assert len(rows) == 36
        assert rows[:35] == prior_component_rows(prior[side])
        source_id, pin, component = rows[-1]
        assert source_id == "scenario-pol004procedure"
        assert pin["physical_branch"] == component["branch"] == branch
        assert pin["system_count"] == len(component["systems"]) == 8
        assert pin["inherited_audit_journals"] == ZERO
        changed = dict(profiles[side])
        changed["source_pins"] = [dict(item) for item in profiles[side]["source_pins"]]
        changed["source_pins"][-1]["database_sha256"] = "0" * 64
        with pytest.raises(CandidateRegistryError, match="POL004 procedure source route differs"):
            probe._component_rows(changed)


def test_reviewed_v14_and_v13_collector_pins_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V14 package hash differs"):
        probe._reviewed_v14(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    monkeypatch.setattr(probe, "V13_COLLECTOR_REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V13 collector byte pin differs"):
        probe._reviewed_v13_collector(REPOSITORY, PRIVATE)


def test_pol004_final_retains_pending_authority_and_messy_exception(profiles: dict) -> None:
    for side, messy in (("A", False), ("B", True)):
        _, _, component = probe._component_rows(profiles[side])[-1]
        origin = Path(component["root"]) / "company.sqlite3"
        ref, _ = probe._native(origin, component)
        assert (ref["system"], ref["record"], ref["version"]) == ("result_register", "FINAL", 1)
        selected = probe._pol004_final(origin, ref)
        assert selected["procedure_approval"] == "PENDING_AUTHORIZED_DECISION"
        assert selected["enterprise_policy_status_2026"] == "OPEN"
        assert selected["messy_exception_open"] is messy
        assert selected["prior_false_close_retained"] is messy
        assert selected["prior_correction_retained"] is messy
        assert selected["actual_operation"] is False
        assert selected["authored_clause_satisfied"] is False
        assert selected["audit_task_credit"] is False
        with pytest.raises(CandidateRegistryError, match="exact POL004 final"):
            probe._pol004_final(origin, dict(ref, record="FALSE-CLOSE"))


def test_semantic_prefix_fields_cover_adverse_cases() -> None:
    assert set(probe._semantic_prefix_keys()) >= {
        "native_identity",
        "inherited_journal_sha256",
        "cc52_selected_case",
        "sec001_selected_case",
        "eth001_selected_case",
        "addressable_pending_case",
    }
