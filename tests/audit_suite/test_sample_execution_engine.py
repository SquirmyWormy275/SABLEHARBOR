"""Maintained Engine dispatch, authorization and replay for an older engagement."""

from copy import deepcopy

import pytest

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError, canonical, digest
from tests.audit_suite.test_sample_execution import trace as trace_fixture


def test_engine_trace_preserves_tasks_and_checks_roles_replay_and_corrections(tmp_path):
    state, artifacts, stamp, payload = trace_fixture.__wrapped__(tmp_path)
    engine = Engine(tmp_path / "engine")
    engine.artifacts = artifacts
    actor = engine.store.provision("Preparer", ["instructor"])["id"]
    reviewer = engine.store.provision("Reviewer", ["reviewer"])["id"]
    for key in COLLECTIONS:
        state.setdefault(key, [])
    state.pop("sample_executions")
    state["simulated_at"] = "2028-01-02T09:00:00+00:00"
    expected_eid = "ENG-" + digest([actor, "create"])[:24]
    previous = state["artifacts"][0]
    retained = artifacts.retain(
        expected_eid,
        "source.csv",
        artifacts.read(previous),
        source=previous["source"],
        coverage=previous["coverage"],
        generated=False,
    )
    state["artifacts"] = [retained]
    state["populations"][0]["artifact_id"] = retained["id"]
    payload["items"][0]["evidence"][0]["artifact_id"] = retained["id"]
    created = engine.store.create(actor, state, "create")
    eid = created["id"]
    engine.store.grant(eid, reviewer, "review")
    envelope = {
        "command_id": "trace",
        "expected_revision": 0,
        "kind": "sample.execution.record",
        "payload": payload,
    }
    before = engine.store.get(actor, eid)
    with pytest.raises(DomainError):
        engine.command(reviewer, eid, envelope)
    assert engine.store.get(actor, eid) == before
    saved = engine.command(actor, eid, envelope)
    assert saved["capabilities"]["sample_executions"] is True
    assert len(saved["sample_executions"]) == 1
    assert saved["tasks"] == before["tasks"] and saved["workpapers"] == before["workpapers"]
    assert canonical(engine.command(actor, eid, envelope)) == canonical(saved)
    original = deepcopy(saved["sample_executions"][0])
    changed = deepcopy(payload)
    changed.update(
        predecessor_id=original["id"],
        predecessor_digest=digest(original),
        correction_rationale="Correct wording while retaining original observation",
    )
    changed["items"][0]["observation"] = "Corrected author wording, same original support"
    corrected = engine.command(
        actor,
        eid,
        {
            "command_id": "correction",
            "expected_revision": 1,
            "kind": "sample.execution.correct",
            "payload": changed,
        },
    )
    assert corrected["sample_executions"][0] == original
    assert corrected["sample_executions"][1]["predecessor_id"] == original["id"]
    assert corrected["tasks"] == before["tasks"]
    assert corrected["populations"] == before["populations"]
    engine.store.grant(eid, actor, "review")
    with pytest.raises(DomainError):
        engine.command(actor, eid, envelope)
