from copy import deepcopy

import pytest

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError


def test_requested_business_day_release_followup_gate_and_private_projection(tmp_path, monkeypatch):
    engine = Engine(tmp_path / "state")

    def artifact(name, private_id):
        row = engine.artifacts.retain(
            "ENG-fixture",
            name,
            b"Fictional record",
            source={"kind": "SYNTHETIC"},
            coverage={},
            generated=True,
        )
        return {**row, "scenario_artifact_id": private_id, "stage": "PRIVATE_STAGE"}

    first, second = artifact("initial.txt", "PRIVATE-A1"), artifact("followup.txt", "PRIVATE-A2")
    definition = {
        "id": "PRIVATE-VARIANT",
        "events": [
            {
                "id": "FIRST",
                "trigger": "REQUEST",
                "offset_business_days": 1,
                "effects": [{"operation": "release_artifact", "target": "PRIVATE-A1"}],
            },
            {
                "id": "SECOND",
                "trigger": "FOLLOWUP",
                "offset_business_days": 1,
                "effects": [{"operation": "release_artifact", "target": "PRIVATE-A2"}],
            },
            {
                "id": "NOTICE",
                "trigger": "CLOCK",
                "offset_business_days": 2,
                "effects": [
                    {
                        "operation": "scope_change",
                        "target": "boundary",
                        "value": "Company proposes a boundary clarification.",
                    }
                ],
            },
        ],
    }
    plan = {"scenario_definition": definition, "prepared_artifacts": [first, second]}
    monkeypatch.setattr("enterprise.audit_suite.generation.request_plan", lambda *args: plan)
    state = {key: [] for key in COLLECTIONS}
    state.update(
        id="ENG-fixture",
        phase="ACTIVE",
        simulated_at="2027-01-08T16:00:00+00:00",
        scope={
            "timezone": "America/Denver",
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
        },
    )
    state["requests"] = [
        {
            "id": "PBC-1",
            "status": "DRAFT",
            "history": [],
            "artifact_ids": [],
            "control_id": "C1",
            "plan_unit": 0,
        }
    ]
    original_scope = deepcopy(state["scope"])
    stamp = {"actor": "learner"}
    with pytest.raises(DomainError, match="initial request"):
        engine._request_command(
            state, "pbc.followup", {"request_id": "PBC-1", "message": "Premature"}, stamp
        )
    assert not state["requests"][0].get("issued_at")
    engine._request_command(state, "pbc.issue", {"request_id": "PBC-1"}, stamp)
    assert state["artifacts"] == []
    anchor = state["requests"][0]["issued_at"]
    state["simulated_at"] = "2027-01-11T16:00:00+00:00"
    engine._deliver_due(state, stamp)
    assert [m["id"] for m in state["artifacts"]] == [first["id"]]
    state["simulated_at"] = "2027-01-12T16:00:00+00:00"
    engine._deliver_due(state, stamp)
    assert len(state["artifacts"]) == 1 and state["scope"] == original_scope
    assert state["scope_change_proposals"][0]["status"] == "PROPOSED"
    engine._request_command(
        state,
        "pbc.followup",
        {"request_id": "PBC-1", "message": "Please provide the follow-up"},
        stamp,
    )
    assert state["requests"][0]["issued_at"] == anchor and len(state["artifacts"]) == 1
    state["simulated_at"] = "2027-01-13T16:00:00+00:00"
    engine._deliver_due(state, stamp)
    engine._deliver_due(state, stamp)
    assert len(state["artifacts"]) == 2
    assert all("scenario_artifact_id" not in m and "stage" not in m for m in state["artifacts"])
    projected = engine.learner_snapshot(state)
    assert (
        "scenario_progress" not in projected["requests"][0]
        and "plan_unit" not in projected["requests"][0]
    )


def test_persona_action_scope_matches_request_status_and_owner(tmp_path):
    engine = Engine(tmp_path / "state")
    state = {
        "controls": [{"id": "C1", "owner_ids": ["P1"]}, {"id": "C2", "owner_ids": ["P2"]}],
        "requests": [
            {"id": "DRAFT", "control_id": "C1", "status": "DRAFT"},
            {"id": "ISSUED", "control_id": "C1", "status": "ISSUED", "issued_at": "2028-01-01"},
            {"id": "CLOSED", "control_id": "C1", "status": "CLOSED", "issued_at": "2028-01-01"},
            {"id": "OTHER", "control_id": "C2", "status": "DRAFT"},
        ],
    }
    context = engine._action_context(state, {"person_id": "P1"})
    assert context["action_scope_by_kind"]["pbc.issue"]["request_ids"] == ["DRAFT"]
    assert context["action_scope_by_kind"]["pbc.followup"]["request_ids"] == ["ISSUED"]
    state["requests"][0]["status"] = "ISSUED"
    state["requests"][0]["issued_at"] = "2028-01-01"
    assert "pbc.issue" not in engine._action_context(state, {"person_id": "P1"})["allowed_actions"]


def test_workpaper_text_references_normalize_before_membership_check(tmp_path):
    engine = Engine(tmp_path / "state")
    state = {"phase": "ACTIVE", "artifacts": [{"id": "A1"}, {"id": "A2"}], "workpapers": []}
    payload = {
        "title": "Manual bounded review",
        "section": "testing",
        "objective": "Inspect originals",
        "procedures": "Read two supplied records",
        "conclusion": "Limited to these records",
        "evidence_ids": "A1,A2",
    }
    engine._workspace_command(state, "workpaper.add", payload, {"actor": "learner"})
    assert state["workpapers"][0]["versions"][0]["evidence_ids"] == ["A1", "A2"]
    with pytest.raises(DomainError):
        engine._workspace_command(
            state, "workpaper.add", {**payload, "evidence_ids": "A1,OTHER"}, {"actor": "learner"}
        )
    assert len(state["workpapers"]) == 1
