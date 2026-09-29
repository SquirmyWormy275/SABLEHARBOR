import json

import pytest

from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.generation import private_json, run_directory
from enterprise.audit_suite.store import DomainError, digest


def setup(tmp_path, monkeypatch, available):
    engine = Engine(tmp_path)
    engine.inference_config = tmp_path / "unused-fixture-provider.json"
    captured = []

    class Provider:
        def __init__(self, config):
            pass

        def generate(self, role, context, messages):
            captured.append((role, context))
            return {"text": "Neutral response", "source_refs": []}

    monkeypatch.setattr("enterprise.audit_suite.inference.LocalInference", Provider)
    state = {
        "id": "ENG-abcdef",
        "phase": "ACTIVE",
        "simulated_at": "2028-06-01T05:30:00+00:00",
        "scope": {"timezone": "America/Denver"},
        "people": [{"id": "P1", "name": "Neutral custodian", "title": "Records custodian"}],
        "meetings": [{"id": "M1", "person_id": "P1", "kind": "CONTROL", "messages": []}],
        "controls": [
            {
                "id": "C1",
                "description": "Neutral control",
                "frequency": "MONTHLY",
                "assignment": {"proposed_contact_ids": ["P1"]},
            }
        ],
        "requests": [{"id": "R1", "control_id": "C1", "plan_unit": 0, "status": "DRAFT"}],
    }
    plan = {
        "plan_integrity_version": 1,
        "actor_knowledge": [
            {"person_id": "P1", "available_by": available, "summary": "Dated source knowledge"},
        ],
    }
    plan["plan_sha256"] = digest(plan)
    path = run_directory(engine, state["id"]) / "unit-00000.json"
    private_json(path, plan)
    return engine, state, captured, path


@pytest.mark.parametrize(
    "available,expected",
    [
        ("2028-06-01T00:00:00-07:00", False),
        ("2028-06-01T09:00:00+05:00", True),
        ("2028-06-01", False),
    ],
)
def test_persona_receives_only_source_knowledge_available_as_an_instant(
    tmp_path,
    monkeypatch,
    available,
    expected,
):
    engine, state, captured, _ = setup(tmp_path, monkeypatch, available)
    engine._conversation(state, {"meeting_id": "M1", "content": "Describe the record"})
    sources = captured[0][1]["sources"]
    assert any(source["kind"] == "PERSONA_KNOWLEDGE" for source in sources) is expected


def test_persona_rejects_changed_frozen_plan_before_any_model_call(tmp_path, monkeypatch):
    engine, state, captured, path = setup(tmp_path, monkeypatch, "2027-01-01")
    plan = json.loads(path.read_text())
    plan["actor_knowledge"][0]["summary"] = "Changed private truth"
    path.write_text(json.dumps(plan))
    with pytest.raises(DomainError, match="integrity"):
        engine._conversation(state, {"meeting_id": "M1", "content": "Describe the record"})
    assert not captured
