"""Independent retained trace export/recovery and ambiguous-reference checks."""

import io
import json
import os
import zipfile
from copy import deepcopy

import pytest

from enterprise.audit_suite import sample_execution
from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.recovery import backup, restore
from enterprise.audit_suite.store import DomainError, Store, digest
from tests.audit_suite.test_sample_execution import trace


def test_duplicate_support_identity_rejected_without_trace(tmp_path):
    state, artifacts, stamp, payload = trace.__wrapped__(tmp_path)
    state["artifacts"].append(deepcopy(state["artifacts"][0]))
    before = deepcopy(state)
    with pytest.raises(DomainError, match="unavailable"):
        sample_execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    assert state == before
    assert sample_execution.input_pins(state)["artifacts"] == []


def test_trace_survives_actual_export_backup_restore_with_original(tmp_path):
    os.chmod(tmp_path, 0o700)
    state, originals, _, payload = trace.__wrapped__(tmp_path)
    engine = Engine(tmp_path / "audit")
    a = state["artifacts"][0]
    raw = originals.read(a)
    (engine.artifacts.root / a["sha256"]).write_bytes(raw)
    (engine.artifacts.root / a["sha256"]).chmod(0o600)
    for key in COLLECTIONS:
        state.setdefault(key, [])
    state["title"] = "Independent disposable source trace"
    actor = engine.store.provision("Local instructor", ["instructor"])
    retained = engine.artifacts.retain(
        "ENG-" + digest([actor["id"], "create"])[:24],
        "source.csv",
        raw,
        source=a["source"],
        coverage=a["coverage"],
        generated=False,
    )
    state["artifacts"] = [retained]
    state["populations"][0]["artifact_id"] = retained["id"]
    payload["items"][0]["evidence"][0]["artifact_id"] = retained["id"]
    a = retained
    created = engine.store.create(actor["id"], state, "create")
    eid = created["id"]
    command = {
        "command_id": "trace",
        "expected_revision": 0,
        "kind": "sample.execution.record",
        "payload": payload,
    }
    recorded = engine.command(actor["id"], eid, command)["sample_executions"]
    original_trace = deepcopy(recorded[0])
    correction = deepcopy(payload)
    correction.update(
        predecessor_id=original_trace["id"],
        predecessor_digest=digest(original_trace),
        correction_rationale="Clarify the observation; preserve original",
    )
    correction["items"][0]["observation"] = "Clarified wording with the same retained source"
    corrected = engine.command(
        actor["id"],
        eid,
        {
            "command_id": "correct",
            "expected_revision": 1,
            "kind": "sample.execution.correct",
            "payload": correction,
        },
    )
    recorded = corrected["sample_executions"]
    assert recorded[0] == original_trace and recorded[1]["predecessor_id"] == original_trace["id"]
    exported = engine.command(
        actor["id"],
        eid,
        {
            "command_id": "export",
            "expected_revision": 2,
            "kind": "review.export",
            "payload": {"edition": "LEARNER"},
        },
    )
    manifest = exported["artifacts"][-1]
    with zipfile.ZipFile(io.BytesIO(engine.artifacts.read(manifest))) as archive:
        assert json.loads(archive.read("engagement.json"))["sample_executions"] == recorded
        history = json.loads(archive.read("history.json"))
        assert history[-1]["state"]["sample_executions"] == recorded
    history_before = engine.store.history(actor["id"], eid)
    backup(engine.store, tmp_path / "backup")
    restore(tmp_path / "backup", tmp_path / "restored")
    recovered = Store(tmp_path / "restored")
    with pytest.raises(DomainError):
        recovered.authenticate(actor["credential"])
    reviewer = recovered.provision("Recovery reviewer", ["reviewer"])
    recovered.grant(eid, reviewer["id"], "review")
    assert recovered.get(reviewer["id"], eid)["sample_executions"] == recorded
    assert recovered.history(reviewer["id"], eid) == history_before
    assert (recovered.root / "artifacts" / a["sha256"]).read_bytes() == raw


def test_ordinary_command_crossing_optional_projection_limit_still_returns_and_replays(tmp_path):
    engine = Engine(tmp_path / "large")
    actor = engine.store.provision("Legacy author", ["instructor"])["id"]
    state = {key: [] for key in COLLECTIONS}
    state.update(scope={}, phase="ACTIVE", simulated_at="2028-01-01T00:00:00Z")
    state["tasks"] = [{"id": f"TASK-{i}"} for i in range(20000)]
    created = engine.store.create(actor, state, "create")
    command = {
        "command_id": "append",
        "expected_revision": 0,
        "kind": "task.create",
        "payload": {"title": "Ordinary new task"},
    }
    saved = engine.command(actor, created["id"], command)
    assert saved["revision"] == 1 and len(saved["tasks"]) == 20001
    assert saved["sample_execution_inputs"]["status"] == "INPUT_LIMIT_EXCEEDED"
    for key in ("tasks", "selections", "workpaper_versions", "artifacts"):
        assert saved["sample_execution_inputs"][key] == []
    assert engine.get(actor, created["id"]) == saved
    assert engine.command(actor, created["id"], command) == saved
    assert engine.store.get(actor, created["id"])["revision"] == 1
