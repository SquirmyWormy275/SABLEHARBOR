"""Source lead inventories cannot certify a complete audit registry."""

import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite.source_registry_preflight import PreflightError, analyze, read_state


class Registry:
    def __init__(self, side, components):
        self.profile_id = side
        self.registry_sha256 = "digest-" + side
        self.binding = {"company": "TEST", "branch": side, "registry_sha256": self.registry_sha256}
        self._manifest = {"components": {x: {"systems": ["source"]} for x in components}}


def fixture():
    states, screen, routes, controls, families, registries = {}, [], [], [], [], {}
    for side in ("A", "B"):
        states[side] = {
            "id": "ENG-" + side,
            "revision": 1,
            "company_source_binding": None,
            "controls": [
                {
                    "id": "SH-TEST-001",
                    "owner_ids": ["P001"],
                    "assignment": {"status": "PROPOSED_CURRENT_ASSIGNMENT"},
                }
            ],
            "tasks": [
                {
                    "id": "TASK-OPEN",
                    "control_id": "SH-TEST-001",
                    "kind": "TOE",
                    "status": "NOT_STARTED",
                    "conclusion": "NOT_RUN",
                },
                {
                    "id": "TASK-MATCHED",
                    "control_id": "SH-TEST-001",
                    "kind": "TOD",
                    "status": "NOT_STARTED",
                    "conclusion": "NOT_RUN",
                },
            ],
            "requests": [],
        }
        screen.extend(
            [
                {
                    "side": side,
                    "task_id": "TASK-OPEN",
                    "control_id": "SH-TEST-001",
                    "matched_retained_sources": [],
                    "applicability_status": "NOT_ASSESSED",
                },
                {
                    "side": side,
                    "task_id": "TASK-MATCHED",
                    "control_id": "SH-TEST-001",
                    "matched_retained_sources": [{"match_scope": "CONTROL_LEVEL_ONLY"}],
                    "applicability_status": "NOT_ASSESSED",
                },
            ]
        )
        routes.append(
            {
                "side": side,
                "task_id": "TASK-OPEN",
                "control_id": "SH-TEST-001",
                "next_action": "DOCUMENTARY_DESIGN_ONLY_DISCOVER_OR_PERFORM_NATIVE_PERIOD_ACTIVITY",
                "applicability_status": "NOT_ASSESSED",
            }
        )
        controls.append(
            {
                "side": side,
                "control_id": "SH-TEST-001",
                "existing_native_route": "DOCUMENTARY_ONLY_IN_PINNED_PORTFOLIO",
            }
        )
        families.extend(
            [
                {
                    "side": side,
                    "component_id": "documents",
                    "explicit_control_ids": ["SH-TEST-001"],
                    "classifications": {"DOCUMENTARY_NOT_OPERATING_FACT": 3},
                    "native_versions": 3,
                },
                {
                    "side": side,
                    "component_id": "activity",
                    "explicit_control_ids": ["SH-TEST-001"],
                    "classifications": {"AUTHORED_ACTIVITY_OR_REFERENCE_NOT_OPERATING_FACT": 1},
                    "native_versions": 1,
                },
            ]
        )
        registries[side] = Registry(side, ["documents"])
    return states, screen, routes, controls, families, registries


def test_document_registry_and_unselected_activity_remain_blocked():
    report = analyze(*fixture(), expected_controls=1, expected_tasks=2)
    assert report["status"] == "SOURCE_COMPLETE_NOT_ESTABLISHED"
    assert report["source_complete"] is False
    for side in ("A", "B"):
        rows = report["sides"][side]
        assert rows["counts"]["controls"] == 1 and rows["counts"]["tasks"] == 2
        assert rows["counts"]["unmatched_task_routes"] == 1
        assert rows["counts"]["prior_control_level_associations"] == 1
        assert {x["component_id"] for x in rows["controls"][0]["candidate_components"]} == {
            "documents",
            "activity",
        }
        task = next(x for x in rows["tasks"] if x["task_id"] == "TASK-OPEN")
        assert task["selected_candidate_component_ids"] == ["documents"]
        assert "NATIVE_ACTIVITY_DISCOVERY_OR_AUTHORIZED_NONOCCURRENCE_REQUIRED" in task["flags"]
        assert "CONDITIONAL_APPLICABILITY_UNRESOLVED" in task["flags"]
        assert "PROPOSED_CONTACT_NOT_ACCEPTED_OPERATING_AUTHORITY" in task["flags"]
        assert task["task_credit"] is False


def test_current_collection_does_not_erase_older_discovery_route():
    data = fixture()
    data[0]["A"]["requests"].append(
        {
            "control_id": "SH-TEST-001",
            "company_collections": [{"source_identity": {"source_store_id": "fresh-source"}}],
        }
    )
    report = analyze(*data, expected_controls=1, expected_tasks=2)
    row = next(x for x in report["sides"]["A"]["tasks"] if x["task_id"] == "TASK-OPEN")
    assert "OLDER_ROUTE_REQUIRES_CURRENT_SOURCE_RESCREEN" in row["flags"]
    assert "fresh-source" in row["candidate_component_ids"]
    assert report["source_complete"] is False


def test_missing_or_duplicate_task_screen_fails_closed():
    data = fixture()
    data[1].pop()
    with pytest.raises(PreflightError, match="Exact 2 task screen"):
        analyze(*data, expected_controls=1, expected_tasks=2)
    data = fixture()
    data[1][1]["task_id"] = "TASK-OPEN"
    with pytest.raises(PreflightError, match="Duplicate task screen"):
        analyze(*data, expected_controls=1, expected_tasks=2)


def test_route_screen_disagreement_fails_closed():
    data = list(fixture())
    data[2] = [r for r in data[2] if r["side"] != "B"]
    with pytest.raises(PreflightError, match="Unmatched routes"):
        analyze(*data, expected_controls=1, expected_tasks=2)


def test_unknown_source_classification_cannot_become_activity():
    data = fixture()
    data[4][1]["classifications"] = {"OPERATING_EFFECTIVENESS": 1}
    with pytest.raises(PreflightError, match="Source-family classification"):
        analyze(*data, expected_controls=1, expected_tasks=2)


def test_state_reader_is_byte_preserving_and_does_not_initialize(tmp_path):
    path = tmp_path / "state.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE engagements (state TEXT NOT NULL)")
        db.execute("INSERT INTO engagements VALUES (?)", (json.dumps({"id": "ENG-A"}),))
    before = path.read_bytes()
    assert read_state(path) == {"id": "ENG-A"}
    assert path.read_bytes() == before
    assert not Path(str(path) + "-wal").exists()
    missing = tmp_path / "missing.sqlite3"
    with pytest.raises(FileNotFoundError):
        read_state(missing)
    assert not missing.exists()
