"""Exact executor-target identity; graph labels must not coerce native identifiers."""

import json

import pytest

from enterprise.audit_suite.instructor_key import migrate_definition
from tests.audit_suite.test_authority_editions import neutral


@pytest.mark.parametrize("artifact_id", [1, True, None])
def test_inspection_edge_does_not_coerce_nonstring_artifact_identity(artifact_id):
    value = neutral("MM-13.03.V01")
    value["artifacts"][0]["id"] = artifact_id
    for event in value["events"]:
        for effect in event["effects"]:
            if effect.get("target") == "A1":
                effect["target"] = artifact_id
    target = str(artifact_id)
    value["playable_paths"][0]["actions"] = ["INSPECT:" + target]
    assert target not in {a["id"] for a in value["artifacts"]}
    raw = json.dumps(value).encode()
    original = migrate_definition(raw)
    successor = migrate_definition(raw, migration_version=2)
    assert successor["explanation"] == original["explanation"] == value
    assert successor["source"] == original["source"]
    assert not any(
        edge["relation"] == "AUTHORED_INSPECTION_TARGET" for edge in successor["graph"]["edges"]
    )
    assert successor["review"]["unlinked_path_actions"] == 1


def test_literal_collision_preserves_old_edge_and_qualifies_typed_relationship():
    value = neutral("MM-13.03.V01")
    # A literal existing event identity also has the executor's INSPECT syntax.
    value["events"][0]["id"] = "INSPECT:A1"
    value["playable_paths"][0]["actions"] = ["INSPECT:A1"]
    raw = json.dumps(value).encode()
    old = migrate_definition(raw)
    new = migrate_definition(raw, migration_version=2)
    assert all(edge in new["graph"]["edges"] for edge in old["graph"]["edges"])
    action_edges = [
        e for e in new["graph"]["edges"] if e["source_pointer"] == "/playable_paths/0/actions/0"
    ]
    assert {(e["relation"], e["to"]) for e in action_edges} == {
        ("EXACT_ACTION_REFERENCE", "event:INSPECT:A1"),
        ("AUTHORED_INSPECTION_TARGET", "artifact:A1"),
    }
    assert "DUAL_LITERAL_AND_INSPECTION_REFERENCES_REQUIRE_REVIEW" in new["review"]["gaps"]
    assert new["review"]["unlinked_path_actions"] == 0
    assert new["review"]["causal_validation"] == new["review"]["grading"] == "NOT_RUN"
    assert new["source"] == old["source"] and new["explanation"] == value
