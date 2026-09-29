import json

import pytest

from enterprise.audit_suite.background_jobs import BackgroundJobs
from tests.audit_suite.test_company_persona_selection import context


@pytest.mark.parametrize("reason", ["SOURCE_CONTEXT_UNAVAILABLE", "INVALID_SOURCE_SELECTION"])
def test_actual_queued_source_failure_is_specific_and_sanitized(tmp_path, monkeypatch, reason):
    engine, actor, state, pins = context.__wrapped__(tmp_path)
    root = tmp_path / "jobs"
    root.mkdir(mode=0o700)
    jobs = BackgroundJobs(root, engine, max_workers=1)

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid or unauthorized source selection must not invoke inference")

    monkeypatch.setattr("enterprise.audit_suite.inference.LocalInference", forbidden)
    command = {
        "command_id": "selected-background",
        "expected_revision": state["revision"],
        "kind": "meeting.message",
        "payload": {
            "meeting_id": "M1",
            "content": "PRIVATE QUESTION CONTENT",
            "source_records": [pins["different"]] if reason == "SOURCE_CONTEXT_UNAVAILABLE" else [],
        },
    }
    job = jobs.submit(actor, state["id"], command)
    jobs.start(actor, state["id"], job["id"])
    thread = jobs.threads.get(job["id"])
    if thread:
        thread.join(5)
        assert not thread.is_alive()
    result = jobs.read(actor, state["id"], job["id"])
    assert result["status"] == "FAILED"
    assert result["error_code"] == reason
    assert "new command" in result["error_message"]
    public = json.dumps(jobs.listing(actor, state["id"]))
    assert "PRIVATE QUESTION CONTENT" not in public
    assert pins["different"]["sha256"] not in public
    assert str(tmp_path) not in public
    assert jobs.input(actor, state["id"], job["id"]) == command
    assert engine.get(actor, state["id"])["revision"] == state["revision"]
    assert not engine.get(actor, state["id"])["meetings"][0]["messages"]


@pytest.mark.parametrize("status", [409, 422])
def test_source_context_failure_is_not_relabelled_revision_or_command_error(
    tmp_path, monkeypatch, status
):
    from enterprise.audit_suite.store import DomainError

    engine, actor, state, pins = context.__wrapped__(tmp_path)
    root = tmp_path / "jobs"
    root.mkdir(mode=0o700)
    jobs = BackgroundJobs(root, engine, max_workers=1)

    def failure(*args):
        raise DomainError(
            "PRIVATE INTERNAL CONTEXT DETAIL", code="SOURCE_CONTEXT_UNAVAILABLE", status=status
        )

    monkeypatch.setattr(engine, "_conversation", failure)
    command = {
        "command_id": "source-failure",
        "expected_revision": state["revision"],
        "kind": "meeting.message",
        "payload": {
            "meeting_id": "M1",
            "content": "Inspect source",
            "source_records": [pins["z-operations"]],
        },
    }
    job = jobs.submit(actor, state["id"], command)
    jobs.start(actor, state["id"], job["id"])
    thread = jobs.threads.get(job["id"])
    if thread:
        thread.join(5)
        assert not thread.is_alive()
    result = jobs.read(actor, state["id"], job["id"])
    assert (result["status"], result["error_code"]) == ("FAILED", "SOURCE_CONTEXT_UNAVAILABLE")
    assert "PRIVATE INTERNAL" not in json.dumps(result)
