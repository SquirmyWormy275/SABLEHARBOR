import io
import json
import urllib.error

import pytest

from enterprise.audit_suite.background_jobs import BackgroundJobs
from enterprise.audit_suite.inference import LocalInference
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_persona_selection import context
from tests.audit_suite.test_inference import config


@pytest.mark.parametrize("wrapped", [False, True])
def test_completion_timeout_is_specific_bounded_and_never_retried(tmp_path, monkeypatch, wrapped):
    provider = LocalInference(config(tmp_path, timeout=600))
    calls = []

    class Opener:
        def open(self, request, *, timeout):
            calls.append((request.full_url, timeout))
            if request.full_url.endswith("/tokenize"):
                return io.BytesIO(json.dumps({"tokens": [1, 2]}).encode())
            error = TimeoutError("PRIVATE SOCKET DETAIL")
            raise urllib.error.URLError(error) if wrapped else error

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: Opener())
    with pytest.raises(DomainError) as failure:
        provider._complete([{"role": "user", "content": "Question"}])
    assert failure.value.code == "INFERENCE_TIMEOUT"
    assert failure.value.status == 504
    assert "PRIVATE" not in str(failure.value)
    assert [timeout for _, timeout in calls] == [10, 600]
    assert LocalInference(config(tmp_path, timeout=10000)).timeout == 900
    assert LocalInference(config(tmp_path)).timeout == 120


def test_timed_out_job_preserves_exact_input_and_commits_no_reply(tmp_path, monkeypatch):
    engine, actor, state, pins = context.__wrapped__(tmp_path)
    root = tmp_path / "jobs"
    root.mkdir(mode=0o700)
    jobs = BackgroundJobs(root, engine, max_workers=1)

    def timeout(*args):
        raise DomainError("PRIVATE TRANSPORT DETAIL", code="INFERENCE_TIMEOUT", status=504)

    monkeypatch.setattr(engine, "_conversation", timeout)
    command = {
        "command_id": "timed-out-question",
        "expected_revision": state["revision"],
        "kind": "meeting.message",
        "payload": {
            "meeting_id": "M1",
            "content": "Inspect this original",
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
    assert (result["status"], result["error_code"], result["attempts"]) == (
        "FAILED",
        "INFERENCE_TIMEOUT",
        1,
    )
    assert "PRIVATE" not in json.dumps(result)
    assert jobs.input(actor, state["id"], job["id"]) == command
    assert engine.store.get(actor, state["id"]) == state
