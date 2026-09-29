"""Anchor exact old workpaper text without changing comment independence or history."""

import pytest

from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_review_task_versioning import fixture


def test_anchor_preserves_unicode_old_version_and_rejects_inexact_input_atomically(tmp_path):
    engine, author, reviewer, eid, command = fixture(tmp_path)
    text = "First 😀 same\nSecond 😀 same"
    state = command(author, "workpaper.add", {"title": "Quoted work", "text": text})
    paper = state["workpapers"][0]
    version = paper["versions"][0]
    anchor = {"field": "text", "start": 20, "end": 26, "excerpt": "😀 same"}
    assert text[20:26] == anchor["excerpt"]
    state = command(
        reviewer,
        "review.comment",
        {
            "workpaper_id": paper["id"],
            "workpaper_version": 1,
            "comment": "Explain this second passage.",
            "anchor": anchor,
        },
    )
    comment = state["reviews"][0]
    assert comment["anchor"] == {**anchor, "offset_unit": "UNICODE_CODEPOINT"}
    assert comment["workpaper_version_digest"] == digest(version)
    state = command(author, "workpaper.update", {"workpaper_id": paper["id"], "text": "Changed"})
    assert state["reviews"][0] == comment
    before = engine.store.get(reviewer, eid)
    for bad in [
        None,
        {**anchor, "start": 18},
        {**anchor, "extra": "ignored"},
        {**anchor, "start": True},
    ]:
        with pytest.raises(DomainError):
            command(
                reviewer,
                "review.comment",
                {
                    "workpaper_id": paper["id"],
                    "workpaper_version": 1,
                    "comment": "Invalid anchor",
                    "anchor": bad,
                },
            )
        assert engine.store.get(reviewer, eid) == before
    with pytest.raises(DomainError, match="Preparer cannot"):
        command(
            author,
            "review.comment",
            {
                "workpaper_id": paper["id"],
                "workpaper_version": 1,
                "comment": "Self review forbidden",
                "anchor": anchor,
            },
        )
    state = command(
        reviewer,
        "review.comment",
        {
            "workpaper_id": paper["id"],
            "workpaper_version": 2,
            "comment": "Legacy unanchored comment",
        },
    )
    assert "anchor" not in state["reviews"][-1]
