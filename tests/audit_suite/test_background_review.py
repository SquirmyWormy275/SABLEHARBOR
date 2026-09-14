import pytest

from enterprise.audit_suite.background_jobs import BackgroundJobs
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_background_jobs import finish
from tests.audit_suite.test_background_jobs import fixture as original_fixture


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    yield from original_fixture.__wrapped__(tmp_path, monkeypatch)


def test_shared_instances_enforce_one_worker_cap(fixture):
    jobs, engine, actor, state, command, entered, release, calls = fixture
    second = BackgroundJobs(jobs.root, engine, max_workers=4)
    assert second.max_workers == 1  # Initial store capacity survives another process config.
    one = jobs.submit(actor, state["id"], command)
    two = second.submit(actor, state["id"], {**command, "command_id": "another"})
    jobs.start(actor, state["id"], one["id"])
    assert entered.wait(5)
    try:
        with pytest.raises(DomainError, match="capacity"):
            second.start(actor, state["id"], two["id"])
        assert second.read(actor, state["id"], two["id"])["status"] == "PENDING"
        assert len(calls) == 1
    finally:
        release.set()
        finish(jobs, one["id"])
        finish(second, two["id"])


def test_committed_replay_does_not_consume_pending_capacity(fixture):
    jobs, engine, actor, state, command, entered, release, calls = fixture
    release.set()
    completed = engine.command(actor, state["id"], command)
    for number in range(2):
        jobs.submit(
            actor,
            state["id"],
            {
                **command,
                "command_id": f"pending-{number}",
                "expected_revision": completed["revision"],
            },
        )
    replay = jobs.submit(actor, state["id"], command)
    assert replay["status"] == "COMPLETED" and replay["attempts"] == 0
    assert len(calls) == 1
