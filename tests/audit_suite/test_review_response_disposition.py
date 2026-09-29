"""Explicit review feedback preserves source truth and independently gated resolution."""

from copy import deepcopy

import pytest

from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_review_task_versioning import fixture


def human(tmp_path):
    engine, author, reviewer, engagement, command = fixture(tmp_path)
    learner = engine.store.provision("Responding learner", ["learner"])["id"]
    engine.store.grant(engagement, learner, "learn")
    state = command(author, "workpaper.add", {"title": "Local work", "text": "Original work"})
    paper = state["workpapers"][0]
    state = command(
        reviewer,
        "review.comment",
        {"workpaper_id": paper["id"], "comment": "Explain the procedure."},
    )
    return engine, author, reviewer, learner, engagement, command, paper, state["reviews"][0]


@pytest.mark.parametrize(
    "disposition", ["agree", "disagree", "correct", "missing_context", "human_review"]
)
def test_learner_feedback_does_not_resolve_human_issue(tmp_path, disposition):
    engine, author, reviewer, learner, eid, command, paper, review = human(tmp_path)
    original = deepcopy(review)
    state = command(
        learner,
        "review.resolve",
        {
            "review_id": review["id"],
            "disposition": disposition,
            "response": "My recorded response.",
        },
    )
    row = state["reviews"][0]
    assert row["status"] == "OPEN"
    assert row["comment"] == original["comment"]
    assert row["workpaper_version_digest"] == original["workpaper_version_digest"]
    assert row["history"][-1]["disposition"] == disposition
    assert row["history"][-1]["response_workpaper_version_digest"] == digest(paper["versions"][-1])
    assert row["history"][-1]["actor"] == learner
    assert state["workpapers"][0] == paper
    before = engine.store.get(learner, eid)
    with pytest.raises(DomainError):
        command(
            learner,
            "review.resolve",
            {"review_id": review["id"], "response": "Cannot independently close."},
        )
    assert engine.store.get(learner, eid) == before
    state = command(
        reviewer,
        "review.resolve",
        {"review_id": review["id"], "response": "Independent reviewer records resolution."},
    )
    assert state["reviews"][0]["status"] == "RESOLVED"
    assert state["reviews"][0]["history"][0]["disposition"] == disposition


def test_malformed_stale_and_revoked_feedback_are_atomic(tmp_path):
    engine, author, reviewer, learner, eid, command, paper, review = human(tmp_path)
    before = engine.store.get(learner, eid)
    for value in [None, [], "accept_professionally"]:
        with pytest.raises(DomainError):
            command(
                learner,
                "review.resolve",
                {"review_id": review["id"], "disposition": value, "response": "Invalid."},
            )
        assert engine.store.get(learner, eid) == before
    with pytest.raises(DomainError, match="version changed"):
        command(
            learner,
            "review.resolve",
            {
                "review_id": review["id"],
                "disposition": "correct",
                "response": "Stale.",
                "response_workpaper_version": 99,
            },
        )
    assert engine.store.get(learner, eid) == before
    outsider = engine.store.provision("Outside learner", ["learner"])["id"]
    with pytest.raises(DomainError):
        command(
            outsider,
            "review.resolve",
            {"review_id": review["id"], "disposition": "agree", "response": "Outside."},
        )
    assert engine.store.get(learner, eid) == before


def test_ai_appeal_preserves_suggestion_and_exact_input_and_current_work_version(tmp_path):
    engine, author, reviewer, learner, eid, command, paper, review = human(tmp_path)
    state = engine.store.get(author, eid)
    state["reviews"] = [
        {
            "id": "AI-EXAMPLE",
            "kind": "EXPERIMENTAL_AI",
            "status": "SUGGESTIONS_ONLY",
            "input_digest": "a" * 64,
            "input_layers": {"observable_layer": {"workpaper_ids": [paper["id"]]}},
            "result": {"text": "Unvalidated neutral suggestion"},
            "appeals": [],
            "human_acceptance": "NOT_REVIEWED",
            "whole_audit_grade": None,
        }
    ]
    state = engine.store.create(author, state, "isolated-ai-fixture")
    eid = state["id"]
    engine.store.grant(eid, learner, "learn")

    def apply(payload, command_id="respond"):
        return engine.command(
            learner,
            eid,
            {
                "command_id": command_id,
                "expected_revision": engine.store.get(learner, eid)["revision"],
                "kind": "review.resolve",
                "payload": payload,
            },
        )

    before = engine.store.get(learner, eid)
    with pytest.raises(DomainError, match="digest changed"):
        apply(
            {
                "review_id": "AI-EXAMPLE",
                "disposition": "disagree",
                "response": "Different context.",
                "input_digest": "b" * 64,
            }
        )
    assert engine.store.get(learner, eid) == before
    state = apply(
        {
            "review_id": "AI-EXAMPLE",
            "disposition": "human_review",
            "response": "Please inspect the recorded source.",
            "input_digest": "a" * 64,
        }
    )
    row = state["reviews"][0]
    assert row["status"] == "SUGGESTIONS_ONLY"
    assert row["human_acceptance"] == "NOT_REVIEWED" and row["whole_audit_grade"] is None
    assert row["result"] == before["reviews"][0]["result"]
    assert row["appeals"][0]["input_digest"] == "a" * 64
    assert row["appeals"][0]["review_result_digest"] == digest(row["result"])
    assert row["appeals"][0]["response_workpaper_versions"][0]["digest"] == digest(
        paper["versions"][-1]
    )
    assert state["workpapers"] == before["workpapers"]


def test_feedback_replay_is_exact_and_revoked_actor_cannot_replay(tmp_path):
    engine, author, reviewer, learner, eid, command, paper, review = human(tmp_path)
    envelope = {
        "command_id": "exact-feedback",
        "expected_revision": engine.store.get(learner, eid)["revision"],
        "kind": "review.resolve",
        "payload": {
            "review_id": review["id"],
            "disposition": "disagree",
            "response": "Alternative reasoning.",
        },
    }
    state = engine.command(learner, eid, envelope)
    assert engine.command(learner, eid, envelope) == state
    assert len(state["reviews"][0]["history"]) == 1
    changed = deepcopy(envelope)
    changed["payload"]["disposition"] = "agree"
    with pytest.raises(DomainError):
        engine.command(learner, eid, changed)
    before = engine.store.get(author, eid)
    engine.store.revoke(learner)
    with pytest.raises(DomainError):
        engine.command(learner, eid, envelope)
    assert engine.store.get(author, eid) == before


def test_prepared_input_is_not_a_review_and_cannot_be_resolved(tmp_path):
    engine, author, reviewer, learner, eid, command, paper, review = human(tmp_path)
    state = engine.store.get(author, eid)
    state["reviews"] = [{"id": "INPUT", "kind": "EXPERIMENTAL_INPUT", "status": "PREPARED"}]
    state = engine.store.create(author, state, "prepared-only-fixture")
    eid = state["id"]
    before = engine.store.get(author, eid)
    with pytest.raises(DomainError, match="Only human comments"):
        engine.command(
            author,
            eid,
            {
                "command_id": "invalid",
                "expected_revision": before["revision"],
                "kind": "review.resolve",
                "payload": {
                    "review_id": "INPUT",
                    "disposition": "agree",
                    "response": "Not a suggestion.",
                },
            },
        )
    assert engine.store.get(author, eid) == before


def test_resolution_requires_independence_even_with_current_review_permission(tmp_path):
    engine, author, reviewer, learner, eid, command, paper, review = human(tmp_path)
    command(
        learner, "workpaper.update", {"workpaper_id": paper["id"], "text": "Later contribution"}
    )
    engine.store.grant(eid, learner, "review")
    for actor in [author, learner]:
        before = engine.store.get(actor, eid)
        with pytest.raises(DomainError, match="cannot independently resolve") as exc:
            command(
                actor,
                "review.resolve",
                {
                    "review_id": review["id"],
                    "response": "Cannot resolve own contribution",
                    "response_workpaper_version": 2,
                },
            )
        assert exc.value.status == 403
        assert engine.store.get(actor, eid) == before
        state = command(
            actor,
            "review.resolve",
            {
                "review_id": review["id"],
                "disposition": "correct",
                "response": "Can record my correction claim",
                "response_workpaper_version": 2,
            },
        )
        assert state["reviews"][0]["status"] == "OPEN"
    state = command(
        reviewer,
        "review.resolve",
        {
            "review_id": review["id"],
            "response": "Independent resolution recorded",
            "response_workpaper_version": 2,
        },
    )
    assert state["reviews"][0]["status"] == "RESOLVED"
    assert state["reviews"][0]["history"][-1]["response_workpaper_version"] == 2
    before = engine.store.get(reviewer, eid)
    with pytest.raises(DomainError, match="Only an open human review"):
        command(
            reviewer,
            "review.resolve",
            {
                "review_id": review["id"],
                "response": "Stale second resolution",
                "response_workpaper_version": 2,
            },
        )
    assert engine.store.get(reviewer, eid) == before
