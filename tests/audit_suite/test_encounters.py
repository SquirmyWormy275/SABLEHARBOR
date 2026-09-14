from copy import deepcopy

import pytest

from enterprise.audit_suite.configuration import rounded_count
from enterprise.audit_suite.encounters import pool
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.store import DomainError


def fixture(selector="MM-08"):
    encounter = {
        "kind": "CONTROL_OWNER_INTERACTION",
        "participant_roles": ["primary_person_id", "operating_reviewer_person_id"],
        "purpose": "Resolve responsibility for the retained approval decision",
    }
    if selector == "MM-09":
        encounter = {
            "kind": "THIRD_PARTY_REQUEST",
            "purpose": "Obtain the provider service report",
            "provider_identity": {
                "id": "PROVIDER-1",
                "name": "Neutral provider",
                "relationship": "Training service provider",
                "origin": "AUTHORED_TRAINING_COUNTERPARTY",
            },
        }
    definition = {
        "id": "V1",
        "selector_id": selector,
        "binding_contract": {"encounter": encounter},
        "events": [{"trigger": "REQUEST"}],
        "artifacts": [{"id": "A1", "stage": "INITIAL"}],
    }
    controls = [
        {
            "id": "C1",
            "assignment": {
                "primary_person_id": "P1",
                "operating_reviewer_person_id": "P2",
                "custodian_person_id": "P1",
            },
        }
    ]
    people = [{"id": "P1"}, {"id": "P2"}]
    units = [
        {"control_id": "C1", "boundary_id": str(n), "implementation_version": "v1"}
        for n in range(4)
    ]
    return definition, units, controls, people


def test_owner_pool_pins_distinct_actual_participants_and_source_requests():
    args = fixture()
    result = pool(*args)
    assert len({row["planned_request_id"] for row in result["encounters"]}) == 4
    assert len({row["id"] for row in result["encounters"]}) == 4
    for row in result["encounters"]:
        assert set(row["participants"].values()) == {"P1", "P2"}
        assert row["initial_source_artifact_ids"] == ["A1"]
    assert rounded_count(1, len(result["encounters"]), positive_minimum=True) == 1
    assert rounded_count(0, len(result["encounters"]), positive_minimum=True) == 0
    args[2][0]["assignment"]["operating_reviewer_person_id"] = "P1"
    excluded = pool(*args)
    assert not excluded["encounters"] and len(excluded["excluded"]) == 4


def test_provider_pool_preserves_counterparty_separate_from_internal_relay():
    args = fixture("MM-09")
    record = pool(*args)["encounters"][0]
    assert record["provider_identity"]["id"] == "PROVIDER-1"
    assert record["custodian_person_id"] == "P1"
    args[0]["binding_contract"]["encounter"]["provider_identity"] = "P1"
    with pytest.raises(DomainError, match="identified provider"):
        pool(*args)


def test_allocation_counts_are_instructor_only_even_in_historical_export(tmp_path):
    engine = Engine(tmp_path)
    instructor = engine.store.provision("Instructor", ["instructor"])
    learner = engine.store.provision("Learner", ["learner"])
    state = engine.store.create(
        instructor["id"],
        {
            "scope": {},
            "artifacts": [],
            "trainer_encounter_counts": [{"planned": 1}],
        },
        "create",
    )
    engine.store.grant(state["id"], learner["id"], "learn")
    assert engine.get(instructor["id"], state["id"])["trainer_encounter_counts"]
    assert "trainer_encounter_counts" not in engine.get(learner["id"], state["id"])
    assert "trainer_encounter_counts" not in engine.learner_snapshot(deepcopy(state))
