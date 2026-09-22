"""Actual native corrections and ordinary commands; no automatic invalidation."""

from copy import deepcopy

import pytest

from enterprise.audit_suite import source_impact_disposition as core
from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_company_collection import envelope
from tests.audit_suite.test_company_collection import workspace as collection_workspace


@pytest.fixture
def workspace(tmp_path):
    engine, actor, state = collection_workspace.__wrapped__(tmp_path)
    state = engine.command(actor, state["id"], envelope(state))
    artifact = state["artifacts"][0]
    state = engine.command(
        actor,
        state["id"],
        {
            "command_id": "paper",
            "expected_revision": state["revision"],
            "kind": "workpaper.add",
            "payload": {
                "title": "Inspect original",
                "text": "Unchanged original work",
                "evidence_ids": [artifact["id"]],
            },
        },
    )
    engine.company_store.append_version(
        "SH",
        "base",
        "identity",
        "record",
        expected_version=1,
        command_id="correct",
        event_at="2027-05-01T00:00:00Z",
        available_at="2027-05-02T00:00:00Z",
        content=b"Corrected original",
        provenance={"source_reference": "Explicit correction"},
    )
    return engine, actor, state, artifact


def command(engine, actor, state, artifact, **changes):
    choices = core.inputs(engine, actor, state["id"], artifact["id"])
    payload = {
        "artifact_id": artifact["id"],
        "comparison_sha256": choices["comparison"]["sha256"],
        "target_sha256": choices["targets"][0]["sha256"],
        "disposition": "REASSESSMENT_NEEDED",
        "rationale": "Later source requires deliberate comparison",
        "intended_action": "Review the exact corrected source and retain prior work",
        "retest_sha256": None,
        "predecessor": None,
    }
    payload.update(changes)
    return {
        "command_id": "disposition",
        "expected_revision": state["revision"],
        "kind": core.COMMAND,
        "payload": payload,
    }


def test_actual_command_stable_comparison_originals_preserved_and_exact_retry(workspace):
    engine, actor, state, artifact = workspace
    a = core.inputs(engine, actor, state["id"], artifact["id"])
    b = core.inputs(engine, actor, state["id"], artifact["id"])
    assert a["comparison"] == b["comparison"]
    assert a["observed"] != b["observed"]
    before = engine.store.get(actor, state["id"])
    cmd = command(engine, actor, state, artifact)
    result = engine.command(actor, state["id"], cmd)
    row = result["source_impact_dispositions"][0]
    assert row["actor"] == actor and row["revision"] == state["revision"] + 1
    assert row["version"] == 1 and row["personal_content_visible"]
    assert row["comparison"]["collected_version"] == 1
    assert row["comparison"]["latest_visible_version"] == 2
    assert row["target"]["record_sha256"] == digest(before["workpapers"][0]["versions"][0])
    assert row["disposition"] == "REASSESSMENT_NEEDED"
    after = engine.store.get(actor, state["id"])
    for key in (
        "artifacts",
        "workpapers",
        "tasks",
        "findings",
        "sample_executions",
        "simulated_at",
    ):
        assert after[key] == before[key]
    assert engine.artifacts.read(artifact) == b"identity record\n"
    assert engine.command(actor, state["id"], cmd) == result
    assert len(engine.store.get(actor, state["id"])["source_impact_dispositions"]) == 1


def test_explicit_successor_exact_raw_predecessor_no_parallel_leaf(workspace):
    engine, actor, state, artifact = workspace
    state = engine.command(actor, state["id"], command(engine, actor, state, artifact))
    raw = engine.store.get(actor, state["id"])["source_impact_dispositions"][0]
    choices = core.inputs(engine, actor, state["id"], artifact["id"])
    assert choices["predecessors"][0]["sha256"] == digest(raw)
    wrong = command(engine, actor, state, artifact)
    wrong["command_id"] = "missing-parent"
    with pytest.raises(DomainError, match="predecessor"):
        engine.command(actor, state["id"], wrong)
    cmd = command(
        engine,
        actor,
        state,
        artifact,
        predecessor={"id": raw["id"], "sha256": digest(raw)},
        disposition="ACKNOWLEDGED",
    )
    cmd["command_id"] = "successor"
    state = engine.command(actor, state["id"], cmd)
    assert [r["version"] for r in state["source_impact_dispositions"]] == [1, 2]
    assert state["source_impact_dispositions"][1]["predecessor"]["sha256"] == digest(raw)


def test_new_native_source_after_choice_rejects_without_audit_commit(workspace):
    engine, actor, state, artifact = workspace
    cmd = command(engine, actor, state, artifact)
    engine.company_store.append_version(
        "SH",
        "base",
        "identity",
        "record",
        expected_version=2,
        command_id="later",
        event_at="2027-05-03T00:00:00Z",
        available_at="2027-05-04T00:00:00Z",
        content=b"Further correction",
        provenance={"source_reference": "later"},
    )
    with pytest.raises(DomainError, match="comparison changed"):
        engine.command(actor, state["id"], cmd)
    assert engine.store.get(actor, state["id"])["revision"] == state["revision"]


def test_revoked_current_source_rejects_new_disposition(workspace):
    engine, actor, state, artifact = workspace
    cmd = command(engine, actor, state, artifact)
    engine.company_store.grant(actor, state["id"], "SH", "base", "identity", active=False)
    with pytest.raises(DomainError, match="source change unavailable"):
        engine.command(actor, state["id"], cmd)
    assert engine.store.get(actor, state["id"])["revision"] == state["revision"]


def test_final_source_race_rejects_append(workspace, monkeypatch):
    engine, actor, state, artifact = workspace
    cmd = command(engine, actor, state, artifact)
    original = core._inputs
    calls = 0

    def change(*args):
        nonlocal calls
        calls += 1
        result = original(*args)
        if calls == 1:
            engine.company_store.grant(actor, state["id"], "SH", "base", "identity", active=False)
        return result

    monkeypatch.setattr(core, "_inputs", change)
    with pytest.raises(DomainError):
        engine.command(actor, state["id"], cmd)
    assert engine.store.get(actor, state["id"])["source_impact_dispositions"] == []


def test_context_change_redacts_formal_history_not_rewrite(workspace):
    engine, actor, state, artifact = workspace
    state = engine.command(actor, state["id"], command(engine, actor, state, artifact))
    raw = engine.store.get(actor, state["id"])
    modified = deepcopy(raw)
    modified["scope"]["period_end"] = "2028-12-31"
    projected = engine._project(actor, modified)
    row = projected["source_impact_dispositions"][0]
    assert row["context_status"] == "CONTEXT_CHANGED" and not row["personal_content_visible"]
    assert "rationale" not in row and "target" not in row and "artifact_id" not in row
    assert engine.store.get(actor, state["id"]) == raw


def test_target_change_and_review_only_authority_fail_closed(workspace):
    engine, actor, state, artifact = workspace
    cmd = command(engine, actor, state, artifact)
    engine.store.grant(state["id"], actor, "review")
    with pytest.raises(DomainError):
        engine.command(actor, state["id"], cmd)
    with pytest.raises(DomainError):
        core.inputs(engine, actor, state["id"], artifact["id"])


def test_linked_retest_requires_distinct_exact_existing_record(workspace):
    engine, actor, state, artifact = workspace
    choices = core.inputs(engine, actor, state["id"], artifact["id"])
    cmd = command(
        engine,
        actor,
        state,
        artifact,
        disposition="RETEST_LINKED",
        retest_sha256=choices["targets"][0]["sha256"],
    )
    with pytest.raises(DomainError, match="Distinct"):
        engine.command(actor, state["id"], cmd)
    state = engine.command(
        actor,
        state["id"],
        {
            "command_id": "second-paper",
            "expected_revision": state["revision"],
            "kind": "workpaper.add",
            "payload": {
                "title": "Explicit reassessment",
                "text": "A separate authored procedure",
                "evidence_ids": [artifact["id"]],
            },
        },
    )
    choices = core.inputs(engine, actor, state["id"], artifact["id"])
    cmd = command(
        engine,
        actor,
        state,
        artifact,
        disposition="RETEST_LINKED",
        retest_sha256=choices["retests"][1]["sha256"],
    )
    state = engine.command(actor, state["id"], cmd)
    row = state["source_impact_dispositions"][0]
    assert row["retest"]["sha256"] == choices["retests"][1]["sha256"]
    assert "NOT_RETEST_RESULT" in row["qualification"]


def test_original_itself_is_target_without_linked_work(workspace):
    engine, actor, state, artifact = workspace
    raw = engine.store.get(actor, state["id"])
    raw["workpapers"] = []
    choices = core._inputs(engine, actor, raw, artifact["id"])
    assert len(choices["targets"]) == 1
    assert choices["targets"][0]["reference"]["collection"] == "artifacts"
    assert choices["targets"][0]["record_sha256"] == digest(artifact)
    assert choices["retests"] == []


def test_descriptive_reference_change_keeps_exact_target_identity(workspace):
    engine, actor, state, artifact = workspace
    raw = engine.store.get(actor, state["id"])
    wp = raw["workpapers"][0]
    initial = {
        "collection": "workpapers",
        "id": wp["id"],
        "version": 1,
        "version_status": "CURRENT",
        "relation": "DIRECT_EVIDENCE_ID",
    }
    later = {**initial, "version_status": "HISTORICAL", "successor_id": "LATER"}
    assert core._choice(raw, initial)["sha256"] == core._choice(raw, later)["sha256"]


def test_replay_uses_current_authorized_artifact_visibility(workspace):
    engine, actor, state, artifact = workspace
    cmd = command(engine, actor, state, artifact)
    recorded = engine.command(actor, state["id"], cmd)
    raw = engine.store.get(actor, state["id"])
    engine.store.command(
        actor,
        state["id"],
        {
            "command_id": "visibility-change",
            "expected_revision": raw["revision"],
            "kind": "technical.visibility",
            "payload": {},
        },
        lambda s, *_: {**s, "artifacts": [{**a, "audience": "INSTRUCTOR"} for a in s["artifacts"]]},
        permissions={"learn"},
    )
    current = engine.get(actor, state["id"])["source_impact_dispositions"][0]
    replay = engine.command(actor, state["id"], cmd)
    assert replay["revision"] == recorded["revision"]
    row = replay["source_impact_dispositions"][0]
    assert row["context_status"] == current["context_status"] == "TARGET_UNAVAILABLE"
    assert "rationale" not in row and "target" not in row
    assert len(engine.store.get(actor, state["id"])["source_impact_dispositions"]) == 1


def test_replay_uses_current_scope_not_historical_response_scope(workspace):
    engine, actor, state, artifact = workspace
    cmd = command(engine, actor, state, artifact)
    recorded = engine.command(actor, state["id"], cmd)
    raw = engine.store.get(actor, state["id"])
    engine.store.command(
        actor,
        state["id"],
        {
            "command_id": "scope-change",
            "expected_revision": raw["revision"],
            "kind": "technical.scope",
            "payload": {},
        },
        lambda s, *_: {**s, "scope": {**s["scope"], "period_end": "2028-12-31"}},
        permissions={"learn"},
    )
    replay = engine.command(actor, state["id"], cmd)
    assert replay["revision"] == recorded["revision"]
    row = replay["source_impact_dispositions"][0]
    assert row["context_status"] == "CONTEXT_CHANGED"
    assert "rationale" not in row
