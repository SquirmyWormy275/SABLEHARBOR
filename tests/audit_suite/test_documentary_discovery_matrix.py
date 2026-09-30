"""Source-route joins must preserve task clauses and reject evidence promotion."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from enterprise.audit_suite import documentary_discovery_matrix as matrix_module
from enterprise.audit_suite.documentary_discovery_matrix import MatrixError, assemble


def _fixture():
    pins = {
        "control_routes": {"sha256": "control-pin"},
        "task_routes": {"sha256": "task-pin"},
    }
    components = {f"native-{n}": {"systems": ["bounded"]} for n in range(13)}
    controls, routes, screens, preflight = [], [], [], {}
    for side in "AB":
        controls.append(
            {
                "side": side,
                "control_id": "SH-ASS-001",
                "existing_native_route": "DOCUMENTARY_ONLY_IN_PINNED_PORTFOLIO",
                "family": "risk_assurance_governance",
                "priority": "P2",
                "frequency": "quarterly",
                "frameworks": ["SOC2"],
                "owner_ids": ["AS-P005"],
                "owner_assignment_status": "PROPOSED_CURRENT_ASSIGNMENT",
                "period_and_clause_gap": (
                    "NO_AUTHORED_2027_ACTIVITY_IN_PINNED_13_COMPONENT_PORTFOLIO"
                ),
                "task_count": 1,
                "task_ids": ["TASK-SH-ASS-001-TOD"],
                "task_credit": False,
            }
        )
        routes.append(
            {
                "side": side,
                "task_id": "TASK-SH-ASS-001-TOD",
                "control_id": "SH-ASS-001",
                "procedure_type": "TOD",
                "requirement_ids": [],
                "next_action": "DISCOVER_NATIVE_ACTIVITY",
            }
        )
        screens.append(
            {
                "side": side,
                "task_id": "TASK-SH-ASS-001-TOD",
                "procedure_type": "TOD",
                "test_clause": None,
                "current_status": "NOT_STARTED",
                "current_conclusion": "NOT_RUN",
            }
        )
        preflight[side] = {
            "selected_components": {name: ["bounded"] for name in components},
            "controls": [
                {
                    "control_id": "SH-ASS-001",
                    "active_retained_control_components": [],
                    "candidate_components": [
                        {
                            "component_id": "documents",
                            "classification": "DOCUMENTARY_DESIGN_ONLY",
                            "selected_in_proposed_registry": False,
                        }
                    ],
                }
            ],
            "tasks": [
                {
                    "task_id": "TASK-SH-ASS-001-TOD",
                    "current_status": "NOT_STARTED",
                    "current_conclusion": "NOT_RUN",
                    "task_credit": False,
                    "flags": ["DOCUMENTARY_DESIGN_ONLY_DISCOVER_OR_PERFORM_NATIVE_PERIOD_ACTIVITY"],
                    "selected_candidate_component_ids": [],
                }
            ],
        }
    data = {
        "plan_manifest": {
            "files": {"CONTROL-ROUTES.json": "control-pin", "TASK-ROUTES.json": "task-pin"}
        },
        "plan_review": {"status": "PASS_INDEPENDENT_ANALYSIS_ONLY"},
        "preflight_manifest": {"source_complete": False},
        "preflight_review": {"verdict": "PASS_BOUNDED_DIAGNOSTIC_NOT_FINAL_GATE"},
        "preflight_report": {"source_complete": False, "sides": preflight},
        "control_routes": controls,
        "task_routes": routes,
        "screen_v2": {"rows": copy.deepcopy(screens)},
        "screen_v3": {"rows": copy.deepcopy(screens)},
        "procedures": [
            {
                "control_id": "SH-ASS-001",
                "proposed_system_of_record": "Control certification register",
                "reviewer_role_description": "Second-line assurance lead",
            }
        ],
        "catalog": (
            "| SH-ASS-001 | Owner certification. | ASS-001 | Control owners | "
            "quarterly | register |\n"
        ),
    }
    for side in "AB":
        data[f"registry_{side.lower()}"] = {
            "components": copy.deepcopy(components),
            "profiles": {f"paired-{side}": {"components": list(components)}},
        }
    return data, pins


def test_candidate_source_is_not_task_credit_or_authored_clause():
    data, pins = _fixture()
    matrix = assemble(data, pins, expected_controls=1, expected_tasks=1)
    assert matrix["counts"]["total_task_routes"] == 2
    for side in "AB":
        group = matrix["sides"][side]["families"][0]["controls"][0]
        task = group["tasks"][0]
        assert group["candidate_native_source_search_target"] == "Control certification register"
        assert group["selected_registry_native_component"] is None
        assert task["authored_test_clause"] is None
        assert task["test_gate_basis"] == "GENERIC_PROCEDURE_GATE_NOT_AN_AUTHORED_CLAUSE"
        assert task["task_credit"] is False


def test_missing_route_or_promoted_documentary_lead_rejected():
    data, pins = _fixture()
    data["task_routes"].pop()
    with pytest.raises(MatrixError, match="route count differs"):
        assemble(data, pins, expected_controls=1, expected_tasks=1)
    data, pins = _fixture()
    data["preflight_report"]["sides"]["A"]["controls"][0]["candidate_components"][0][
        "selected_in_proposed_registry"
    ] = True
    with pytest.raises(MatrixError, match="incorrectly treated as operation"):
        assemble(data, pins, expected_controls=1, expected_tasks=1)


def test_changed_clause_or_started_task_rejected():
    data, pins = _fixture()
    data["screen_v3"]["rows"][0]["test_clause"] = "Unreviewed replacement clause"
    with pytest.raises(MatrixError, match="Task clause"):
        assemble(data, pins, expected_controls=1, expected_tasks=1)
    data, pins = _fixture()
    data["screen_v3"]["rows"][0]["current_status"] = "IN_PROGRESS"
    with pytest.raises(MatrixError, match="Task clause"):
        assemble(data, pins, expected_controls=1, expected_tasks=1)


def test_source_uris_are_portable_across_relative_and_absolute_roots(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    private = tmp_path / "private"
    (repo / "docs").mkdir(parents=True)
    (private / "source").mkdir(parents=True)
    tracked = repo / "docs" / "catalog.md"
    private_file = private / "source" / "routes.json"
    tracked.write_text("source catalog\n")
    private_file.write_text(json.dumps({"routes": []}) + "\n")
    monkeypatch.setattr(
        matrix_module,
        "INPUTS",
        {
            "catalog": ("docs/catalog.md", hashlib.sha256(tracked.read_bytes()).hexdigest()),
            "routes": ("source/routes.json", hashlib.sha256(private_file.read_bytes()).hexdigest()),
        },
    )
    monkeypatch.chdir(repo)
    relative_values, relative_pins = matrix_module._read_inputs(Path("."), private)
    absolute_values, absolute_pins = matrix_module._read_inputs(repo, private)
    assert relative_values == absolute_values
    assert relative_pins == absolute_pins
    assert relative_pins["catalog"]["uri"] == "repo://docs/catalog.md"
    assert relative_pins["routes"]["uri"] == "private://source/routes.json"
