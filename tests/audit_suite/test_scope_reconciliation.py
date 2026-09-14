from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from enterprise.audit_suite import scope_reconciliation
from enterprise.audit_suite.generation import epoch_directory, private_json, read_plan, request_plan
from enterprise.audit_suite.store import DomainError, canonical, digest


def test_scope_successor_preserves_samples_old_results_and_original_plan(tmp_path, monkeypatch):
    engine = SimpleNamespace(
        repository=Path("."), program_pack=None, store=SimpleNamespace(root=tmp_path)
    )
    assignment = {"primary_person_id": "P1", "custodian_person_id": "P1"}
    monkeypatch.setattr(
        scope_reconciliation,
        "snapshot",
        lambda *args, **kwargs: {
            "control_assignments": [{"control_id": "C2", **assignment}],
            "canonical_people": [],
            "proposed_people": [],
        },
    )
    monkeypatch.setattr(
        scope_reconciliation,
        "control_projection",
        lambda *args, **kwargs: [
            {"id": "C2", "title": "New control"},
        ],
    )
    state = {
        "id": "ENG-abcdef",
        "generation_epoch": 0,
        "phase": "ACTIVE",
        "scope": {"programs": ["SOC2"], "period_start": "2027-01-01", "boundaries": ["old"]},
        "controls": [{"id": "C1"}],
        "people": [],
        "tasks": [{"id": "T1", "conclusion": "FAIL", "history": [{"note": "Original finding"}]}],
        "requests": [{"id": "PBC-0", "plan_unit": 0, "plan_request": 0}],
        "populations": [{"id": "POP1", "immutable": {"records_json": ["original"]}}],
        "selections": [{"id": "SEL1", "population_id": "POP1", "selected_ids": ["R1"]}],
    }
    original_selection = deepcopy(state["selections"])
    original_population = deepcopy(state["populations"][0]["immutable"])
    private_json(
        epoch_directory(engine, state["id"]) / "unit-00000.json",
        {
            "requests": [{"title": "Original evidence"}],
        },
    )
    revised = {
        "programs": ["SOC2"],
        "period_start": "2028-01-01",
        "period_end": "2028-12-31",
        "boundaries": ["new"],
        "temporal_basis": "PERIOD",
    }
    scope_reconciliation.apply(engine, state, revised, "New service period", {"actor": "P1"})
    assert state["generation_epoch"] == 1
    assert state["tasks"][0]["conclusion"] == "FAIL"
    assert state["tasks"][0]["applicability"] == "PRIOR_SCOPE_REQUIRES_REASSESSMENT"
    assert len(state["tasks"]) == 4
    assert all(t["conclusion"] == "NOT_RUN" for t in state["tasks"][1:])
    assert state["selections"] == original_selection
    assert state["populations"][0]["immutable"] == original_population
    private_json(
        epoch_directory(engine, state["id"], 1) / "unit-00000.json",
        {
            "requests": [{"title": "New evidence"}],
        },
    )
    assert request_plan(engine, state, state["requests"][0])["title"] == "Original evidence"
    assert (
        request_plan(engine, state, {"plan_unit": 0, "plan_request": 0, "plan_epoch": 1})["title"]
        == "New evidence"
    )


def test_changed_frozen_delivery_plan_is_rejected(tmp_path):
    path = tmp_path / "unit.json"
    plan = {"plan_integrity_version": 1, "requests": [{"title": "Retained source"}]}
    plan["plan_sha256"] = digest(plan)
    private_json(path, plan)
    assert read_plan(path) == plan
    plan["requests"][0]["title"] = "Altered source"
    path.write_text(canonical(plan))
    with pytest.raises(DomainError, match="integrity failure"):
        read_plan(path)
