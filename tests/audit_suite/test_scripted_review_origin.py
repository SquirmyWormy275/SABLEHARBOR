import pytest

from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_review_task_versioning import fixture


@pytest.mark.parametrize("kind", ["SCRIPTED_ENGINEERING", "SYNTHETIC_TECHNICAL"])
def test_explicit_technical_comment_response_resolution_and_original_actor_version(tmp_path, kind):
    engine, preparer, reviewer, engagement, command = fixture(tmp_path)
    state = command(preparer, "task.create", {"title": "Limited native examination"})
    state = command(
        preparer,
        "task.update",
        {
            "task_id": state["tasks"][0]["id"],
            "status": "IN_PROGRESS",
            "conclusion": "LIMITATION",
            "rationale": "Selected documentary source alone cannot establish effectiveness.",
        },
    )
    original_tasks = digest(state["tasks"])
    state = command(
        preparer,
        "workpaper.add",
        {"title": "Own native examination", "text": "Selected original only."},
    )
    paper = state["workpapers"][0]
    state = command(
        reviewer,
        "review.comment",
        {
            "workpaper_id": paper["id"],
            "review_kind": kind,
            "comment": "Source-backed technical challenge only.",
            "anchor": {"field": "text", "start": 0, "end": 8, "excerpt": "Selected"},
        },
    )
    comment = state["reviews"][-1]
    assert comment["kind"] == kind and comment["professional_acceptance"] == "NOT_ASSERTED"
    assert comment["actor"] == reviewer and comment["workpaper_version_digest"] == digest(
        paper["versions"][0]
    )
    state = command(
        preparer,
        "workpaper.update",
        {
            "workpaper_id": paper["id"],
            "text": "More context; selected examination remains limited.",
        },
    )
    state = command(
        preparer,
        "review.resolve",
        {
            "review_id": comment["id"],
            "disposition": "missing_context",
            "response": "Further context remains needed.",
        },
    )
    assert state["reviews"][-1]["status"] == "OPEN"
    assert state["reviews"][-1]["history"][-1]["response_workpaper_version"] == 2
    with pytest.raises(DomainError, match="contributor"):
        command(
            preparer,
            "review.resolve",
            {"review_id": comment["id"], "response": "Cannot independently resolve own paper."},
        )
    state = command(
        reviewer,
        "review.resolve",
        {"review_id": comment["id"], "response": "Recorded narrow technical resolution."},
    )
    assert state["reviews"][-1]["status"] == "RESOLVED" and state["reviews"][-1]["kind"] == kind
    assert state["reviews"][-1]["workpaper_version"] == 1
    assert digest(state["tasks"]) == original_tasks


@pytest.mark.parametrize("kind", [True, 1, "EXPERIMENTAL_AI", "QUALIFIED_PROFESSIONAL", ""])
def test_other_origins_cannot_claim_independent_or_qualified_review(tmp_path, kind):
    engine, preparer, reviewer, engagement, command = fixture(tmp_path)
    state = command(preparer, "workpaper.add", {"title": "Paper", "text": "Source"})
    before = engine.store.get(reviewer, engagement)
    with pytest.raises(DomainError, match="provenance"):
        command(
            reviewer,
            "review.comment",
            {
                "workpaper_id": state["workpapers"][0]["id"],
                "review_kind": kind,
                "comment": "Explicit origin required.",
            },
        )
    assert engine.store.get(reviewer, engagement) == before
