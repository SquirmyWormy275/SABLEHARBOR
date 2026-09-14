"""Prompt transport contracts; these do not grade a live model response."""

import json

from enterprise.audit_suite.inference import LocalInference
from tests.audit_suite.test_inference import config


def test_persona_fact_first_instruction_preserves_source_data_and_citation_mapping(
    tmp_path, monkeypatch
):
    provider = LocalInference(config(tmp_path))
    captured = {}

    def complete(messages, **kwargs):
        captured["messages"] = messages
        return {
            "text": "The assignment is due 2027-04-30; completion is not recorded.",
            "source_refs": ["SRC_0001"],
            "claims": [],
            "observations": [],
            "proposed_actions": [],
        }

    monkeypatch.setattr(provider, "_complete", complete)
    record = {
        "record_id": "NEUTRAL-ASSIGNMENT",
        "cycle_id": "LOCAL-CYCLE",
        "course_id": "BASIC",
        "due_at": "2027-04-30",
        "classification": "LOCAL_SYNTHETIC_EXERCISE",
        "status": "ASSIGNED",
    }
    result = provider.generate(
        "persona",
        {
            "allowed_roles": ["persona"],
            "source_ids": ["ORIGINAL"],
            "sources": [{"id": "ORIGINAL", "value": record}],
        },
        [{"role": "user", "content": "What assignment and status does this record show?"}],
    )
    system = captured["messages"][0]["content"]
    assert "supplied record facts first" in system
    assert "due date is not a completion date" in system
    assert "without inventing values or implying linked sources were inspected" in system
    assert (
        "Preserve all relevant scope, synthetic/forecast/proposed and provenance qualifications"
        in system
    )
    context = json.loads(captured["messages"][1]["content"].split(": ", 1)[1])
    assert context["sources"][0]["value"] == record
    assert result["source_refs"] == ["ORIGINAL"]


def test_action_stage_wording_does_not_change_proposal_scope(tmp_path, monkeypatch):
    provider = LocalInference(config(tmp_path))
    captured = {}

    def complete(messages, **kwargs):
        captured["prompt"] = messages[0]["content"]
        captured["schema"] = kwargs["schema"]
        return {
            "text": "No completion is recorded.",
            "source_refs": [],
            "claims": [],
            "observations": [],
            "proposed_actions": [],
        }

    monkeypatch.setattr(provider, "_complete", complete)
    provider.generate(
        "persona",
        {"allowed_roles": ["persona"]},
        [{"role": "user", "content": "Explain the available record."}],
    )
    assert "Proposals are not executed" not in captured["prompt"]
    assert (
        "engine separately validates and may execute allowed scoped actions" in captured["prompt"]
    )
    assert "Never claim an action already succeeded" in captured["prompt"]
    # No allowed actions were supplied: the output cannot introduce a new action kind.
    assert captured["schema"]["properties"]["proposed_actions"]["maxItems"] == 0
