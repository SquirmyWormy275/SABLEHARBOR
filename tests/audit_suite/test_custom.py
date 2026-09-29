import copy
import json

import pytest

from enterprise.audit_suite import custom
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.store import DomainError, digest


def test_private_draft_digest_scope_and_acceptance_gates(tmp_path):
    engine = Engine(tmp_path / "state")
    instructor = engine.store.provision("Trainer", ["instructor"])
    state = engine.store.create(
        instructor["id"],
        {
            "phase": "CONFIGURING",
            "scope": {"period_start": "2027-01-01"},
            "configuration": {
                "selections": [
                    {"selector_id": "MM-01", "option_id": "MM-01.01", "authoring_mode": "CUSTOM"}
                ]
            },
        },
        "create",
    )
    draft_id = "CUSTOM-" + "a" * 24
    value = {
        "variant": {"id": draft_id},
        "scope_digest": digest(state["scope"]),
        "validation": {"status": "PASS"},
        "critic": {"observations": []},
    }
    metadata = {
        "id": draft_id,
        "selector_id": "MM-01",
        "option_id": "MM-01.01",
        "status": "REVIEW_REQUIRED",
        "variant_digest": digest(value["variant"]),
    }
    state["custom_drafts"] = [metadata]
    path = custom.run_directory(engine, state["id"]) / "custom-drafts"
    path.mkdir(mode=0o700)
    file = path / (draft_id + ".json")
    file.write_text(json.dumps(value))
    file.chmod(0o600)
    with pytest.raises(DomainError, match="Explicit"):
        custom.prepare(engine, state, "scenario.custom.accept", {"draft_id": draft_id})
    modified = copy.deepcopy(state)
    modified["scope"]["period_start"] = "2028-01-01"
    with pytest.raises(DomainError, match="Scope changed"):
        custom.prepare(
            engine, modified, "scenario.custom.accept", {"draft_id": draft_id, "accept": True}
        )
    value["critic"]["observations"] = [{"text": "Unresolved contradiction"}]
    file.write_text(json.dumps(value))
    with pytest.raises(DomainError, match="Resolve"):
        custom.prepare(
            engine, state, "scenario.custom.accept", {"draft_id": draft_id, "accept": True}
        )
    value["critic"]["observations"] = []
    file.write_text(json.dumps(value))
    result = custom.prepare(
        engine, state, "scenario.custom.accept", {"draft_id": draft_id, "accept": True}
    )
    custom.apply(state, "scenario.custom.accept", result)
    assert state["configuration"]["selections"][0]["draft_id"] == draft_id
    value["variant"]["id"] = "tampered"
    file.write_text(json.dumps(value))
    with pytest.raises(DomainError, match="digest"):
        custom.read(engine, state, draft_id)
    with pytest.raises(DomainError, match="identity"):
        custom.read(engine, state, "../../secret")


def test_authorization_and_replay_precede_model_work(tmp_path, monkeypatch):
    engine = Engine(tmp_path / "state")
    user = engine.store.provision("Learner", ["learner"])
    state = engine.store.create(user["id"], {"phase": "CONFIGURING", "artifacts": []}, "create")
    calls = []
    monkeypatch.setattr(custom, "prepare", lambda *a: calls.append(a))
    envelope = {
        "command_id": "author",
        "expected_revision": state["revision"],
        "kind": "scenario.custom.author",
        "payload": {},
    }
    with pytest.raises(DomainError):
        engine.command(user["id"], state["id"], envelope)
    assert calls == []


def test_custom_command_exact_replay_does_not_repeat_inference(tmp_path, monkeypatch):
    engine = Engine(tmp_path / "state")
    user = engine.store.provision("Trainer", ["instructor"])
    state = engine.store.create(
        user["id"],
        {
            "phase": "CONFIGURING",
            "artifacts": [],
            "events": [],
            "simulated_at": "2028-01-01T09:00:00Z",
        },
        "create",
    )
    calls = []

    def draft(*args):
        calls.append(1)
        return {"id": "CUSTOM-fixture", "status": "REVIEW_REQUIRED"}

    monkeypatch.setattr(custom, "prepare", draft)
    envelope = {
        "command_id": "author-once",
        "expected_revision": state["revision"],
        "kind": "scenario.custom.author",
        "payload": {},
    }
    result = engine.command(user["id"], state["id"], envelope)
    replay = engine.command(user["id"], state["id"], envelope)
    assert replay["revision"] == result["revision"] and len(calls) == 1
    engine.store.revoke(user["id"])
    with pytest.raises(DomainError):
        engine.command(user["id"], state["id"], envelope)
    assert len(calls) == 1
