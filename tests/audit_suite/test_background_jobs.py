import threading

import pytest

from enterprise.audit_suite.background_jobs import BackgroundJobs
from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    engine = Engine(tmp_path / "audit")
    actor = engine.store.provision("Local learner", ["learner"])["id"]
    state = {k: [] for k in COLLECTIONS}
    state.update(
        title="Background exercise",
        phase="ACTIVE",
        mode="CLEAN",
        discipline="IT",
        scope={"boundaries": ["corporate"]},
        simulated_at="2027-01-01T00:00:00Z",
        configuration={},
    )
    state["meetings"] = [{"id": "M1", "kind": "KICKOFF", "person_id": "P1", "messages": []}]
    state["people"] = [{"id": "P1", "name": "Local contact"}]
    state = engine.store.create(actor, state, "create")
    entered, release = threading.Event(), threading.Event()
    calls = []

    def conversation(*args):
        calls.append(1)
        entered.set()
        assert release.wait(5)
        return {"text": "Bounded company statement", "source_refs": [], "proposed_actions": []}

    monkeypatch.setattr(engine, "_conversation", conversation)
    path = tmp_path / "jobs"
    path.mkdir(mode=0o700)
    jobs = BackgroundJobs(path, engine, max_workers=1, max_pending=2)
    command = {
        "command_id": "message1",
        "expected_revision": state["revision"],
        "kind": "meeting.message",
        "payload": {"meeting_id": "M1", "content": "PRIVATE QUESTION"},
    }
    yield jobs, engine, actor, state, command, entered, release, calls
    release.set()
    for thread in list(jobs.threads.values()):
        thread.join(5)


def finish(jobs, job_id):
    thread = jobs.threads.get(job_id)
    if thread:
        thread.join(5)
        assert not thread.is_alive()


def test_delayed_actual_engine_command_survives_reload_and_deduplicates(fixture):
    jobs, e, actor, s, command, entered, release, calls = fixture
    job = jobs.submit(actor, s["id"], command)
    jobs.start(actor, s["id"], job["id"])
    assert entered.wait(5)
    assert jobs.submit(actor, s["id"], command)["id"] == job["id"]
    reloaded = BackgroundJobs(jobs.root, e)
    assert reloaded.read(actor, s["id"], job["id"])["status"] == "RUNNING"
    reloaded.start(actor, s["id"], job["id"])
    assert "PRIVATE QUESTION" not in str(reloaded.listing(actor, s["id"]))
    release.set()
    finish(jobs, job["id"])
    assert jobs.read(actor, s["id"], job["id"])["status"] == "COMPLETED"
    assert len(calls) == 1
    assert len(e.store.get(actor, s["id"])["meetings"][0]["messages"]) == 2
    assert jobs.submit(actor, s["id"], command)["status"] == "COMPLETED"


def test_revision_conflict_never_rebases_or_retries(fixture):
    jobs, e, actor, s, command, entered, release, calls = fixture
    job = jobs.submit(actor, s["id"], command)
    jobs.start(actor, s["id"], job["id"])
    assert entered.wait(5)
    other = {**command, "command_id": "other", "kind": "local-neutral-change", "payload": {}}
    e.store.command(actor, s["id"], other, lambda state, *_: state, permissions={"learn"})
    release.set()
    finish(jobs, job["id"])
    result = jobs.read(actor, s["id"], job["id"])
    assert result["status"] == "CONFLICTED"
    assert jobs.submit(actor, s["id"], command)["status"] == "CONFLICTED"
    with pytest.raises(DomainError):
        jobs.retry(actor, s["id"], job["id"], observed_job_revision=result["job_revision"])
    assert not e.store.get(actor, s["id"])["meetings"][0]["messages"]


def test_current_permissions_rechecked_and_private_failure_sanitized(fixture):
    jobs, e, actor, s, command, entered, release, calls = fixture
    job = jobs.submit(actor, s["id"], command)
    jobs.start(actor, s["id"], job["id"])
    assert entered.wait(5)
    e.store.grant(s["id"], actor, "review")
    with pytest.raises(DomainError):
        jobs.read(actor, s["id"], job["id"])
    release.set()
    finish(jobs, job["id"])
    e.store.grant(s["id"], actor, "learn")
    result = jobs.read(actor, s["id"], job["id"])
    assert result["status"] == "FAILED" and result["error_code"] == "ACCESS_DENIED"
    assert not e.store.get(actor, s["id"])["meetings"][0]["messages"]
    other = e.store.provision("Other learner", ["learner"])["id"]
    e.store.grant(s["id"], other, "learn")
    with pytest.raises(DomainError):
        jobs.read(other, s["id"], job["id"])


def test_interrupted_restart_requires_explicit_inspection_retry(fixture):
    jobs, e, actor, s, command, entered, release, calls = fixture
    job = jobs.submit(actor, s["id"], command)
    with jobs._db() as db:
        jobs._transition(db, job["id"], "RUNNING")
    restarted = BackgroundJobs(jobs.root, e)
    interrupted = restarted.read(actor, s["id"], job["id"])
    assert interrupted["status"] == "INTERRUPTED" and calls == []
    with pytest.raises(DomainError):
        restarted.retry(actor, s["id"], job["id"], observed_job_revision=0)
    release.set()
    restarted.retry(actor, s["id"], job["id"], observed_job_revision=interrupted["job_revision"])
    finish(restarted, job["id"])
    assert restarted.read(actor, s["id"], job["id"])["status"] == "COMPLETED"


def test_pending_quota_and_worker_bound(fixture):
    jobs, e, actor, s, command, entered, release, calls = fixture
    first = jobs.submit(actor, s["id"], command)
    second = jobs.submit(actor, s["id"], {**command, "command_id": "message2"})
    with pytest.raises(DomainError, match="quota"):
        jobs.submit(actor, s["id"], {**command, "command_id": "message3"})
    jobs.start(actor, s["id"], first["id"])
    assert entered.wait(5)
    with pytest.raises(DomainError, match="capacity"):
        jobs.start(actor, s["id"], second["id"])
    assert jobs.read(actor, s["id"], second["id"])["status"] == "PENDING"
    release.set()
    finish(jobs, first["id"])


def test_private_exception_message_never_enters_status(fixture, monkeypatch):
    jobs, e, actor, s, command, entered, release, calls = fixture

    def fail(*args):
        raise RuntimeError("/private/path SECRET MODEL CONTENT")

    monkeypatch.setattr(e, "_conversation", fail)
    job = jobs.submit(actor, s["id"], command)
    jobs.start(actor, s["id"], job["id"])
    finish(jobs, job["id"])
    result = jobs.read(actor, s["id"], job["id"])
    assert result["status"] == "FAILED" and result["error_code"] == "EXECUTION_FAILED"
    assert "SECRET" not in str(result) and "/private" not in str(result)


def test_interrupted_after_committed_command_replays_receipt_without_compute(fixture):
    jobs, e, actor, s, command, entered, release, calls = fixture
    job = jobs.submit(actor, s["id"], command)
    release.set()
    e.command(actor, s["id"], command)
    assert len(calls) == 1
    with jobs._db() as db:
        jobs._transition(db, job["id"], "RUNNING")
    restarted = BackgroundJobs(jobs.root, e)
    interrupted = restarted.read(actor, s["id"], job["id"])
    restarted.retry(actor, s["id"], job["id"], observed_job_revision=interrupted["job_revision"])
    finish(restarted, job["id"])
    assert restarted.read(actor, s["id"], job["id"])["status"] == "COMPLETED"
    assert len(calls) == 1
    assert len(e.store.get(actor, s["id"])["meetings"][0]["messages"]) == 2


def test_explicit_input_inspection_is_authorized_and_not_in_listing(fixture):
    jobs, e, actor, s, command, entered, release, calls = fixture
    job = jobs.submit(actor, s["id"], command)
    assert jobs.input(actor, s["id"], job["id"]) == command
    assert "PRIVATE QUESTION" not in str(jobs.listing(actor, s["id"]))
    other = e.store.provision("Other", ["learner"])["id"]
    e.store.grant(s["id"], other, "learn")
    with pytest.raises(DomainError):
        jobs.input(other, s["id"], job["id"])
    e.store.grant(s["id"], actor, "review")
    with pytest.raises(DomainError):
        jobs.input(actor, s["id"], job["id"])
