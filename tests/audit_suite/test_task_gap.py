"""Durable authored gaps retain exact source and retest links without task credit."""

import hashlib

import pytest

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_collection import envelope
from tests.audit_suite.test_company_collection import workspace as source_workspace

A_BYTES = b"retained source for gap test\n"
H_BYTES = b"instructor-only retained source\n"
A_SHA = hashlib.sha256(A_BYTES).hexdigest()
H_SHA = hashlib.sha256(H_BYTES).hexdigest()


def command(state, payload, command_id="gap-1"):
    return {
        "kind": "task.gap.record",
        "command_id": command_id,
        "expected_revision": state["revision"],
        "payload": payload,
    }


def payload(actor, **changes):
    value = {
        "task_id": "T1",
        "cause": "MISSING_OPERATION",
        "owner_id": actor,
        "disposition": "OPEN",
        "narrative": "The selected period has no recorded operation for this task.",
        "artifact_pin": None,
        "retest": None,
        "predecessor_id": None,
    }
    value.update(changes)
    return value


@pytest.fixture
def workspace(tmp_path):
    engine = Engine(tmp_path / "audit")
    for data, sha in ((A_BYTES, A_SHA), (H_BYTES, H_SHA)):
        path = engine.artifacts.root / sha
        path.write_bytes(data)
        path.chmod(0o600)
    auditor = engine.store.provision("Auditor", ["learner"])["id"]
    reviewer = engine.store.provision("Reviewer", ["reviewer"])["id"]
    outsider = engine.store.provision("Outsider", ["reviewer"])["id"]
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Task gap isolation",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at="2027-12-31T00:00:00Z",
        scope={
            "boundaries": ["corporate"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
        },
        configuration={"selections": []},
    )
    state["controls"] = [{"id": "C1", "title": "Declared control", "owner_ids": ["P1"]}]
    state["tasks"] = [
        {
            "id": "T1",
            "control_id": "C1",
            "title": "Selected procedure",
            "status": "NOT_STARTED",
            "conclusion": "NOT_RUN",
            "history": [],
        }
    ]
    state["artifacts"] = [
        {
            "id": "A1",
            "sha256": A_SHA,
            "bytes": len(A_BYTES),
            "status": "AVAILABLE",
            "audience": "LEARNER",
            "source": {
                "receipt": {
                    "source": {
                        "company": "SH",
                        "branch": "base",
                        "system": "backup",
                        "record": "R1",
                        "version": 1,
                        "sha256": A_SHA,
                    }
                }
            },
        },
        {
            "id": "H1",
            "sha256": H_SHA,
            "bytes": len(H_BYTES),
            "status": "AVAILABLE",
            "audience": "INSTRUCTOR",
        },
    ]
    state = engine.store.create(auditor, state, "create-gap-workspace")
    engine.store.grant(state["id"], reviewer, "review")
    return engine, auditor, reviewer, outsider, state


def test_gap_replay_reopen_and_retest_preserve_original_work(workspace):
    engine, actor, reviewer, outsider, state = workspace
    before = engine.store.get(actor, state["id"])
    first = command(state, payload(actor, artifact_pin={"id": "A1", "sha256": A_SHA}))
    result = engine.command(actor, state["id"], first)
    assert engine.command(actor, state["id"], first) == result
    gap = result["task_gaps"][0]
    assert gap["revision"] == state["revision"] + 1
    assert gap["artifact_pin"]["native_source_pin"]["record"] == "R1"
    assert gap["qualification"] == "AUTHOR_RECORDED_GAP_NOT_EVIDENCE_OR_AUDIT_CONCLUSION"
    assert engine.get(reviewer, state["id"])["task_gaps"] == result["task_gaps"]
    assert engine.store.get(actor, state["id"])["tasks"] == before["tasks"]
    assert engine.store.get(actor, state["id"])["artifacts"] == before["artifacts"]
    with pytest.raises(DomainError):
        engine.get(outsider, state["id"])
    with pytest.raises(DomainError):
        engine.command(reviewer, state["id"], command(result, payload(reviewer), "reviewer-write"))

    paper = engine.command(
        actor,
        state["id"],
        {
            "kind": "workpaper.add",
            "command_id": "paper",
            "expected_revision": result["revision"],
            "payload": {
                "title": "Separate retest",
                "control_id": "C1",
                "task_ids": ["T1"],
                "text": "A separate retest observation, not automatic closure.",
            },
        },
    )
    workpaper = paper["workpapers"][0]
    retest = {"workpaper_id": workpaper["id"], "version": 1}
    linked = engine.command(
        actor,
        state["id"],
        command(
            paper,
            payload(
                actor,
                disposition="RETEST_LINKED",
                retest=retest,
                predecessor_id=gap["id"],
                narrative="A separate retest workpaper is linked; sufficiency remains open.",
            ),
            "gap-2",
        ),
    )
    assert linked["task_gaps"][1]["retest"]["version_sha256"]
    assert linked["task_gaps"][1]["predecessor_sha256"]
    reopened = engine.command(
        actor,
        state["id"],
        command(
            linked,
            payload(
                actor,
                predecessor_id=linked["task_gaps"][1]["id"],
                narrative="The linked retest did not resolve the original missing operation.",
            ),
            "gap-3",
        ),
    )
    assert [row["disposition"] for row in reopened["task_gaps"]] == [
        "OPEN",
        "RETEST_LINKED",
        "OPEN",
    ]
    assert reopened["tasks"] == before["tasks"]
    assert engine.store.get(actor, state["id"])["artifacts"] == before["artifacts"]
    assert engine.get(actor, state["id"])["task_gaps"] == reopened["task_gaps"]


def test_stale_revision_bad_pins_and_unlinked_retest_fail_closed(workspace):
    engine, actor, _, _, state = workspace
    bad = payload(actor, artifact_pin={"id": "A1", "sha256": "f" * 64})
    with pytest.raises(DomainError, match="pin changed"):
        engine.command(actor, state["id"], command(state, bad))
    with pytest.raises(DomainError, match="Retest-linked"):
        engine.command(
            actor, state["id"], command(state, payload(actor, disposition="RETEST_LINKED"))
        )
    result = engine.command(actor, state["id"], command(state, payload(actor)))
    with pytest.raises(DomainError, match="changed"):
        engine.command(actor, state["id"], command(state, payload(actor), "stale"))
    with pytest.raises(DomainError, match="successor"):
        _duplicate_successor(engine, actor, result)


@pytest.mark.parametrize("invalid", [[], {}, 5])
def test_nonstring_enums_are_domain_errors(workspace, invalid):
    engine, actor, _, _, state = workspace
    for field in ("cause", "disposition"):
        with pytest.raises(DomainError, match="Explicit gap"):
            engine.command(actor, state["id"], command(state, payload(actor, **{field: invalid})))
    assert engine.store.get(actor, state["id"])["task_gaps"] == []


@pytest.mark.parametrize("damage", ["remove", "tamper"])
def test_missing_or_tampered_retained_bytes_reject_gap(workspace, damage):
    engine, actor, _, _, state = workspace
    path = engine.artifacts.root / A_SHA
    if damage == "remove":
        path.unlink()
    else:
        path.write_bytes(b"tampered retained source\n")
    with pytest.raises(DomainError, match="Retained artifact bytes unavailable or changed"):
        engine.command(
            actor,
            state["id"],
            command(state, payload(actor, artifact_pin={"id": "A1", "sha256": A_SHA})),
        )
    assert engine.store.get(actor, state["id"])["task_gaps"] == []


def test_excluded_task_does_not_accept_operating_gap(workspace):
    engine, actor, _, _, state = workspace
    excluded = engine.command(
        actor,
        state["id"],
        {
            "kind": "task.update",
            "command_id": "exclude",
            "expected_revision": state["revision"],
            "payload": {
                "task_id": "T1",
                "status": "NOT_APPLICABLE",
                "rationale": "Explicit scope exclusion for test",
            },
        },
    )
    with pytest.raises(DomainError, match="Current scoped procedure"):
        engine.command(actor, state["id"], command(excluded, payload(actor)))


def _duplicate_successor(engine, actor, state):
    previous = state["task_gaps"][0]["id"]
    next_state = engine.command(
        actor, state["id"], command(state, payload(actor, predecessor_id=previous), "successor")
    )
    return engine.command(
        actor,
        state["id"],
        command(next_state, payload(actor, predecessor_id=previous), "duplicate"),
    )


def test_hidden_artifact_gap_does_not_leak_to_learner(workspace):
    engine, learner, _, _, state = workspace
    instructor = engine.store.provision("Instructor", ["instructor"])["id"]
    engine.store.grant(state["id"], instructor, "instruct")
    with pytest.raises(DomainError, match="unavailable"):
        engine.command(
            learner,
            state["id"],
            command(state, payload(learner, artifact_pin={"id": "H1", "sha256": H_SHA})),
        )
    result = engine.command(
        instructor,
        state["id"],
        command(
            state, payload(instructor, artifact_pin={"id": "H1", "sha256": H_SHA}), "hidden-gap"
        ),
    )
    assert len(result["task_gaps"]) == 1
    assert engine.get(learner, state["id"])["task_gaps"] == []
    result = engine.command(
        instructor,
        state["id"],
        command(
            result,
            payload(
                instructor,
                predecessor_id=result["task_gaps"][0]["id"],
                narrative="A visible-looking follow-up still inherits the restricted gap context.",
            ),
            "hidden-gap-successor",
        ),
    )
    assert len(result["task_gaps"]) == 2
    assert engine.get(learner, state["id"])["task_gaps"] == []
    assert engine.learner_snapshot(engine.store.get(instructor, state["id"]))["task_gaps"] == []
    assert "hidden-gap" not in str(engine.get(learner, state["id"])["task_gaps"])


def test_gap_pin_from_actual_collected_company_source(tmp_path):
    engine, actor, state = source_workspace.__wrapped__(tmp_path)
    state = engine.command(actor, state["id"], envelope(state))
    artifact = state["artifacts"][0]
    state = engine.command(
        actor,
        state["id"],
        {
            "kind": "task.create",
            "command_id": "create-gap-task",
            "expected_revision": state["revision"],
            "payload": {"title": "Inspect selected source operation"},
        },
    )
    source_path = engine.company_store.path
    before = source_path.read_bytes()
    expected = state["tasks"][-1]
    result = engine.command(
        actor,
        state["id"],
        command(
            state,
            payload(
                actor,
                task_id=expected["id"],
                cause="INSUFFICIENT_SOURCE",
                artifact_pin={"id": artifact["id"], "sha256": artifact["sha256"]},
                narrative="This collected original alone does not cover the selected procedure.",
            ),
            "gap-native-source",
        ),
    )
    pin = result["task_gaps"][0]["artifact_pin"]
    assert pin["native_source_pin"] == artifact["source"]["receipt"]["source"]
    assert source_path.read_bytes() == before
    assert result["tasks"][-1] == expected
    assert result["artifacts"] == state["artifacts"]
