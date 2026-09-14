"""Neutral command-path acceptance checks; no private scenario answers or seeds."""

import hashlib
import io
import json
import zipfile

import pytest

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError, digest


@pytest.fixture
def workspace(tmp_path):
    engine = Engine(tmp_path / "private")
    learner = engine.store.provision("Neutral preparer", ["learner"])["id"]
    reviewer = engine.store.provision("Neutral reviewer", ["reviewer"])["id"]
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Neutral evidence workflow",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at="2027-01-04T09:00:00+00:00",
        scope={
            "period_start": "2027-01-04",
            "period_end": "2027-12-31",
            "timezone": "UTC",
            "boundaries": ["corporate"],
        },
        configuration={"selections": []},
    )
    state = engine.store.create(learner, state, "neutral-create")
    engine.store.grant(state["id"], reviewer, "review")
    return engine, learner, reviewer, state


def submit(engine, actor, state, kind, payload, command_id):
    return engine.command(
        actor,
        state["id"],
        {
            "command_id": command_id,
            "expected_revision": state["revision"],
            "kind": kind,
            "payload": payload,
        },
    )


def test_human_export_keeps_workpaper_versions_and_independent_review(workspace):
    engine, learner, reviewer, state = workspace
    state = submit(
        engine,
        learner,
        state,
        "workpaper.add",
        {
            "title": "Source comparison",
            "text": "Initial source needs clarification.",
            "conclusion": "LIMITATION",
        },
        "add",
    )
    workpaper_id = state["workpapers"][0]["id"]
    state = submit(
        engine,
        learner,
        state,
        "workpaper.update",
        {
            "workpaper_id": workpaper_id,
            "text": "Follow-up retained; scope remains limited.",
            "conclusion": "LIMITATION",
        },
        "revise",
    )
    with pytest.raises(DomainError):
        submit(
            engine,
            learner,
            state,
            "review.comment",
            {"workpaper_id": workpaper_id, "comment": "Self review"},
            "self-review",
        )
    state = submit(
        engine,
        reviewer,
        state,
        "review.comment",
        {"workpaper_id": workpaper_id, "comment": "Explain the remaining scope limitation."},
        "independent-review",
    )
    state = submit(engine, learner, state, "review.export", {"edition": "EVIDENCE"}, "export")
    artifact = state["artifacts"][-1]
    content = engine.artifacts.read(artifact)
    assert hashlib.sha256(content).hexdigest() == artifact["sha256"]
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        exported = json.loads(archive.read("engagement.json"))
        history = json.loads(archive.read("history.json"))
        assert len(exported["workpapers"][0]["versions"]) == 2
        assert exported["reviews"][0]["actor"] == reviewer
        assert exported["reviews"][0]["workpaper_version"] == 2
        assert exported["reviews"][0]["workpaper_version_digest"] == digest(
            exported["workpapers"][0]["versions"][-1]
        )
        assert exported["workpapers"][0]["prepared_by"] == learner
        assert all(v["conclusion"] == "LIMITATION" for v in exported["workpapers"][0]["versions"])
        assert len(history) >= 4
        assert "configuration" not in exported
        assert {"index.html", "manifest.json", "history.json"} <= set(archive.namelist())


def test_remediation_plan_preserves_original_condition_without_automatic_retest(workspace):
    engine, learner, _, state = workspace
    state = submit(
        engine,
        learner,
        state,
        "finding.create",
        {
            "title": "Unresolved source reference",
            "condition": "A referenced source is unavailable.",
            "classification": "EVIDENCE_LIMITATION",
        },
        "finding",
    )
    finding = state["findings"][0]
    original_period = finding["original_period"]
    state = submit(
        engine,
        learner,
        state,
        "remediation.record",
        {
            "finding_id": finding["id"],
            "action": "Restore the source and independently validate it.",
            "status": "proposed",
            "due_at": "2027-02-01",
        },
        "plan",
    )
    revised = state["findings"][0]
    assert revised["condition"] == "A referenced source is unavailable."
    assert revised["original_period"] == original_period
    assert revised["status"] == "REMEDIATION_PLANNED"
    assert revised["remediations"][0]["retest_result"] == "NOT_RUN"
    assert revised["history"][0]["status"] == "OPEN"
    assert state["tasks"] == []


def test_retest_dates_fail_atomically_and_later_result_preserves_history(workspace):
    engine, learner, _, state = workspace
    state = submit(engine, learner, state, "review.export", {"edition": "EVIDENCE"}, "source")
    evidence = state["artifacts"][-1]["id"]
    original_hash = state["artifacts"][-1]["sha256"]
    state = submit(
        engine,
        learner,
        state,
        "finding.create",
        {
            "title": "Uncorroborated period coverage",
            "condition": "Coverage remains uncorroborated.",
            "classification": "EVIDENCE_LIMITATION",
            "evidence_ids": [evidence],
        },
        "finding",
    )
    finding = state["findings"][-1]
    state = submit(
        engine,
        learner,
        state,
        "remediation.record",
        {
            "finding_id": finding["id"],
            "action": "Obtain new prospective source support.",
            "status": "proposed",
        },
        "remediation",
    )
    remediation = state["findings"][-1]["remediations"][-1]
    payload = {
        "finding_id": finding["id"],
        "remediation_id": remediation["id"],
        "test_date": "2027-01-05",
        "period_start": "2027-01-05",
        "period_end": "2027-01-05",
        "procedures": "Inspect whether the retained package establishes prospective operation.",
        "rationale": "A historical export is not prospective operating evidence.",
        "result": "INCONCLUSIVE",
        "evidence_ids": [evidence],
    }
    before = engine.store.history(learner, state["id"])
    with pytest.raises(DomainError, match="Retest coverage"):
        submit(engine, learner, state, "remediation.retest", payload, "future-retest")
    assert engine.store.history(learner, state["id"]) == before
    state = submit(engine, learner, state, "clock.advance", {"mode": "ONE_BUSINESS_DAY"}, "advance")
    state = submit(engine, learner, state, "remediation.retest", payload, "valid-retest")
    after = state["findings"][-1]
    assert after["condition"] == finding["condition"]
    assert after["original_period"] == finding["original_period"]
    assert after["retests"][-1]["result"] == "INCONCLUSIVE"
    assert after["retests"][-1]["coverage"] == {
        "period_start": "2027-01-05",
        "period_end": "2027-01-05",
    }
    assert after["remediations"][-1]["retest_result"] == "NOT_RUN"
    assert state["artifacts"][0]["sha256"] == original_hash
    assert state["tasks"] == []


def test_learner_cannot_generate_private_reviewer_edition(workspace):
    engine, learner, _, state = workspace
    before = engine.store.history(learner, state["id"])
    with pytest.raises(DomainError):
        submit(engine, learner, state, "review.export", {"edition": "REVIEWER"}, "private-export")
    assert engine.store.history(learner, state["id"]) == before
    assert engine.get(learner, state["id"])["artifacts"] == []
