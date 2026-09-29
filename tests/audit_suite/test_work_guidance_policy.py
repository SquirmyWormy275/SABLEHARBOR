"""Instructor policy is explicit and independent of clean/messy scenario mode."""

import pytest

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError


@pytest.fixture
def policy_context(tmp_path):
    engine = Engine(tmp_path / "audit")
    owner = engine.store.provision("Instructor", ["instructor"])["id"]
    learner = engine.store.provision("Learner", ["learner"])["id"]
    reviewer = engine.store.provision("Reviewer", ["reviewer"])["id"]
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Policy fixture",
        phase="ACTIVE",
        mode="CLEAN",
        discipline="IT",
        scope={"boundaries": ["corporate"]},
        configuration={},
        simulated_at="2027-01-01T00:00:00Z",
    )
    state = engine.store.create(owner, state, "create")
    for actor, permission in [(owner, "instruct"), (learner, "learn"), (reviewer, "review")]:
        engine.store.grant(state["id"], actor, permission)
    return engine, owner, learner, reviewer, state


def envelope(state, enabled=True, command_id="policy"):
    return {
        "kind": "assistance.configure",
        "command_id": command_id,
        "expected_revision": state["revision"],
        "payload": {
            "work_guidance_allowed": enabled,
            "rationale": "Explicit assisted local exercise",
        },
    }


def test_default_off_and_instructor_policy_visible_without_configuration(policy_context):
    engine, instructor, learner, reviewer, state = policy_context
    before = engine.get(learner, state["id"])
    assert before["work_guidance_policy"] == {"allowed": False, "version": 0}
    assert "configuration" not in before
    for actor in [learner, reviewer]:
        with pytest.raises(DomainError) as error:
            engine.command(actor, state["id"], envelope(state))
        assert error.value.status == 403
    result = engine.command(instructor, state["id"], envelope(state))
    assert result["work_guidance_policy"] == {"allowed": True, "version": state["revision"] + 1}
    assert (
        engine.get(learner, state["id"])["work_guidance_policy"] == result["work_guidance_policy"]
    )
    assert "configuration" not in engine.get(learner, state["id"])
    assert len(result["assistance_policy_history"]) == 1
    assert engine.command(instructor, state["id"], envelope(state)) == result
    assert result["tasks"] == state["tasks"] and result["artifacts"] == state["artifacts"]


def test_policy_epoch_changes_even_same_boolean_and_stale_cas_rejected(policy_context):
    engine, instructor, _, _, state = policy_context
    result = engine.command(instructor, state["id"], envelope(state))
    repeated = engine.command(instructor, state["id"], envelope(result, command_id="same-boolean"))
    assert repeated["work_guidance_policy"]["version"] > result["work_guidance_policy"]["version"]
    with pytest.raises(DomainError):
        engine.command(instructor, state["id"], envelope(state, False, "stale"))
    disabled = engine.command(instructor, state["id"], envelope(repeated, False, "disable"))
    assert disabled["work_guidance_policy"]["allowed"] is False
    assert len(disabled["assistance_policy_history"]) == 3


@pytest.mark.parametrize("value", [1, "true", None])
def test_policy_requires_exact_boolean(policy_context, value):
    engine, instructor, _, _, state = policy_context
    with pytest.raises(DomainError):
        engine.command(instructor, state["id"], envelope(state, value))
    assert engine.store.get(instructor, state["id"])["revision"] == state["revision"]


@pytest.mark.parametrize("field", ["work_guidance_allowed", "work_guidance_policy_revision"])
def test_creation_cannot_inject_assistance_authority(policy_context, field):
    engine, _, learner, _, _ = policy_context
    with pytest.raises(DomainError) as error:
        engine.create(
            learner,
            {
                "title": "Injection",
                "mode": "CLEAN",
                "discipline": "IT",
                "configuration": {field: True},
            },
        )
    assert error.value.status == 403
