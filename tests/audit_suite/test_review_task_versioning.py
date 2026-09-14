from itertools import count

import pytest

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError, digest


def fixture(tmp_path):
    engine = Engine(tmp_path)
    preparer = engine.store.provision("Preparer", ["instructor"])["id"]
    reviewer = engine.store.provision("Reviewer", ["reviewer"])["id"]
    data = {key: [] for key in COLLECTIONS}
    data.update(scope={}, phase="ACTIVE", simulated_at="2028-01-02T09:00:00+00:00")
    state = engine.store.create(preparer, data, "create")
    engine.store.grant(state["id"], reviewer, "review")
    sequence = count()

    def command(actor, kind, payload):
        current = engine.store.get(actor, state["id"])
        return engine.command(
            actor,
            state["id"],
            {
                "command_id": str(next(sequence)),
                "expected_revision": current["revision"],
                "kind": kind,
                "payload": payload,
            },
        )

    return engine, preparer, reviewer, state["id"], command


def test_not_applicable_progress_requires_retained_rationale_atomically(tmp_path):
    engine, preparer, _, engagement, command = fixture(tmp_path)
    state = command(preparer, "task.create", {"title": "Assess scoped procedure"})
    task = state["tasks"][0]
    before = engine.store.get(preparer, engagement)
    with pytest.raises(DomainError, match="rationale"):
        command(preparer, "task.update", {"task_id": task["id"], "status": "NOT_APPLICABLE"})
    assert engine.store.get(preparer, engagement) == before
    state = command(
        preparer,
        "task.update",
        {
            "task_id": task["id"],
            "status": "NOT_APPLICABLE",
            "rationale": "This procedure concerns a service excluded from the approved scope.",
        },
    )
    assert state["tasks"][0]["rationale"].startswith("This procedure")
    assert state["tasks"][0]["conclusion"] == "NOT_RUN"


def test_review_comment_and_correction_pin_separate_original_versions(tmp_path):
    engine, preparer, reviewer, engagement, command = fixture(tmp_path)
    state = command(preparer, "workpaper.add", {"title": "Assessment", "text": "Initial procedure"})
    paper = state["workpapers"][0]
    state = command(
        reviewer,
        "review.comment",
        {
            "workpaper_id": paper["id"],
            "comment": "Clarify the sampled population.",
        },
    )
    comment = state["reviews"][0]
    original_digest = digest(paper["versions"][0])
    assert comment["workpaper_version"] == 1
    assert comment["workpaper_version_digest"] == original_digest
    state = command(
        preparer,
        "workpaper.update",
        {
            "workpaper_id": paper["id"],
            "text": "Revised procedure with explicit population basis",
        },
    )
    latest_digest = digest(state["workpapers"][0]["versions"][-1])
    state = command(
        reviewer,
        "review.resolve",
        {
            "review_id": comment["id"],
            "response": "Reviewed the stated correction in version2.",
        },
    )
    comment = state["reviews"][0]
    assert comment["workpaper_version"] == 1
    assert comment["workpaper_version_digest"] == original_digest
    assert comment["history"][-1]["response_workpaper_version"] == 2
    assert comment["history"][-1]["response_workpaper_version_digest"] == latest_digest
    before = engine.store.get(reviewer, engagement)
    with pytest.raises(DomainError, match="existing workpaper version"):
        command(
            reviewer,
            "review.comment",
            {
                "workpaper_id": paper["id"],
                "workpaper_version": 999,
                "comment": "Invalid version",
            },
        )
    assert engine.store.get(reviewer, engagement) == before


def test_instructor_editor_cannot_independently_review_contributed_version(tmp_path):
    engine, preparer, _, engagement, command = fixture(tmp_path)
    editor = engine.store.provision("Editing instructor", ["instructor"])["id"]
    engine.store.grant(engagement, editor, "instruct")
    state = command(preparer, "workpaper.add", {"title": "Original", "text": "Original work"})
    paper = state["workpapers"][0]
    command(
        editor, "workpaper.update", {"workpaper_id": paper["id"], "text": "Contributor correction"}
    )
    before = engine.store.get(editor, engagement)
    with pytest.raises(DomainError, match="contributor"):
        command(
            editor,
            "review.comment",
            {"workpaper_id": paper["id"], "comment": "My correction is acceptable"},
        )
    assert engine.store.get(editor, engagement) == before
    state = command(
        editor,
        "review.comment",
        {
            "workpaper_id": paper["id"],
            "workpaper_version": 1,
            "comment": "Independent assessment of original version predating contribution",
        },
    )
    assert state["reviews"][-1]["workpaper_version"] == 1
