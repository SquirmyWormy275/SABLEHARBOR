import copy
import json

import pytest

from enterprise.audit_suite.company_impact import references, report
from tests.audit_suite.test_company_collection import envelope
from tests.audit_suite.test_company_collection import workspace as original_workspace


@pytest.fixture
def workspace(tmp_path):
    return original_workspace.__wrapped__(tmp_path)


def test_visible_correction_only_and_no_snapshot_mutation(workspace):
    engine, actor, state = workspace
    collected = engine.command(actor, state["id"], envelope(state))
    artifact = collected["artifacts"][0]
    command = {
        "command_id": "workpaper",
        "expected_revision": collected["revision"],
        "kind": "workpaper.add",
        "payload": {
            "title": "Specific evidence",
            "evidence_ids": [artifact["id"]],
            "text": "Original support",
        },
    }
    updated = engine.command(actor, state["id"], command)
    assert report(engine, actor, state["id"])["changes"] == []
    for version, available in [(1, "2027-05-01T00:00:00Z"), (2, "2028-01-01T00:00:00Z")]:
        engine.company_store.append_version(
            "SH",
            "base",
            "identity",
            "record",
            expected_version=version,
            command_id=f"version-{version + 1}",
            event_at="2027-01-01T00:00:00Z",
            available_at=available,
            content=f"version{version + 1}".encode(),
            provenance={"source_reference": "correction"},
        )
    result = report(engine, actor, state["id"])
    assert len(result["changes"]) == 1
    change = result["changes"][0]
    assert change["latest_visible_version"] == 2
    assert change["references"] == [
        {
            "collection": "workpapers",
            "id": updated["workpapers"][0]["id"],
            "version": 1,
            "relation": "DIRECT_EVIDENCE_ID",
        }
    ]
    assert engine.store.get(actor, state["id"])["revision"] == updated["revision"]
    assert engine.artifacts.read(artifact) == b"identity record\n"
    engine.company_store.grant(actor, state["id"], "SH", "base", "identity", active=False)
    denied = report(engine, actor, state["id"])
    assert denied["changes"] == [] and denied["unavailable_comparisons"] == 1
    assert "version2" not in json.dumps(denied)


def test_only_explicit_links_and_exact_population_version():
    state = {
        "workpapers": [
            {
                "id": "WP1",
                "versions": [
                    {"version": 1, "evidence_ids": ["ART"]},
                    {"version": 2, "text": "ART"},
                ],
            }
        ],
        "populations": [{"id": "P1", "version": 1, "source_json": '{"source_id":"ART"}'}],
        "selections": [
            {"id": "S1", "population_id": "P1", "population_version": 1},
            {"id": "S2", "population_id": "P1", "population_version": 2},
        ],
        "tasks": [{"id": "T1", "evidence_ids": ["ART"]}, {"id": "T2", "text": "ART"}],
    }
    before = copy.deepcopy(state)
    result = references(state, "ART")
    assert {row["id"] for row in result} == {"WP1", "P1", "S1", "T1"}
    assert state == before
