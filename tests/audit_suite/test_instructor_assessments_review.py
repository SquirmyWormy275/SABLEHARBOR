"""Independent selection, history and disclosure boundary regressions."""

from copy import deepcopy

import pytest

from enterprise.audit_suite.instructor_assessments import InstructorAssessments
from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_explanation_binding import workspace
from tests.audit_suite.test_instructor_assessments import assessment as base_assessment
from tests.audit_suite.test_instructor_assessments import payload
from tests.audit_suite.test_instructor_comparison import advance, bound


@pytest.fixture
def assessment(tmp_path):
    return base_assessment.__wrapped__(tmp_path)


def test_task_linked_historical_work_without_source_intersection_is_selectable(tmp_path):
    engine, args = workspace.__wrapped__(tmp_path)
    old = {"version": 1, "task_ids": ["T1"], "evidence_ids": [], "conclusion": "Limited work"}
    advance(
        engine,
        args,
        lambda s: {
            **s,
            "tasks": [{"id": "T1", "control_id": "CONTROL1"}],
            "workpapers": [{"id": "WP1", "control_id": "CONTROL1", "versions": [old]}],
        },
    )
    args["authored"]["expectations"][0]["task_ids"] = ["T1"]
    engine, args, bindings = bound((engine, args))
    root = tmp_path / "assessment-review"
    root.mkdir(mode=0o700)
    core = InstructorAssessments(root, engine, bindings)
    actor, eid = args["instructor_id"], args["engagement_id"]
    options = core.options(actor, eid, 1)
    wp = next((r for r in options["references"] if r["kind"] == "workpaper"), None)
    assert wp is not None, "Exact authored-task-linked work must not require source overlap"
    assert wp["version"] == 1 and wp["content_sha256"] == digest(old)
    p = payload(core, args, 1)
    p["dimensions"][2]["reference_ids"] = [wp["id"]]
    saved = core.save(actor, eid, p)
    advance(
        engine,
        args,
        lambda s: {
            **s,
            "workpapers": [
                {
                    "id": "WP1",
                    "control_id": "CONTROL1",
                    "versions": [old, {**old, "version": 2, "task_ids": []}],
                }
            ],
        },
    )
    assert (
        core.read(actor, eid, saved["id"])["document"]["references"]
        == saved["document"]["references"]
    )


def test_multi_issue_expectation_requires_every_explicit_issue(assessment, monkeypatch):
    core, _, args = assessment
    original = core.options

    def options(*a):
        result = deepcopy(original(*a))
        result["issues"].append({**result["issues"][0], "id": "I2"})
        result["expectations"][0]["issue_ids"] = ["I1", "I2"]
        return result

    monkeypatch.setattr(core, "options", options)
    p = payload(core, args)
    with pytest.raises(DomainError, match="issue closure"):
        core.save(args["instructor_id"], args["engagement_id"], p)
    assert core.snapshot()["documents"] == []
    p["issue_ids"].append("I2")
    assert (
        len(
            core.save(args["instructor_id"], args["engagement_id"], p)["document"][
                "selected_issues"
            ]
        )
        == 2
    )


def test_exact_retry_after_context_change_cannot_reveal_prior_authored_text(assessment):
    core, engine, args = assessment
    actor, eid = args["instructor_id"], args["engagement_id"]
    p = payload(core, args)
    saved = core.save(actor, eid, p)
    before = core.snapshot()
    advance(engine, args, lambda s: {**s, "evidence_acquisition": "CHANGED"})
    replay = core.save(actor, eid, p)
    assert replay["id"] == saved["id"]
    assert replay["context_status"] == "CONTEXT_CHANGED"
    assert not replay["personal_content_visible"] and not replay["correction_allowed"]
    assert "title" not in replay and "document" not in replay
    assert core.snapshot() == before


def test_final_list_membership_loss_returns_no_private_metadata(assessment, monkeypatch):
    core, engine, args = assessment
    actor, eid = args["instructor_id"], args["engagement_id"]
    core.save(actor, eid, payload(core, args))
    before = core.snapshot()
    dto = core._dto

    def revoke(*a, **kw):
        result = dto(*a, **kw)
        engine.store.grant(eid, actor, "learn")
        return result

    monkeypatch.setattr(core, "_dto", revoke)
    with pytest.raises(DomainError) as failure:
        core.listing(actor, eid)
    assert failure.value.status == 403
    assert core.snapshot() == before
