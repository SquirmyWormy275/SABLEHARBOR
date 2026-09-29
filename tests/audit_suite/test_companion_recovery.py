import json

import pytest

from enterprise.audit_suite.companion_recovery import backup, restore
from enterprise.audit_suite.instructor_access import InstructorAccessLog
from enterprise.audit_suite.store import DomainError
from enterprise.audit_suite.workspace_context import WorkspaceContexts
from tests.audit_suite.test_background_jobs import fixture as jobs_fixture
from tests.audit_suite.test_workspace_context import payload
from tests.audit_suite.test_workspace_context import workspace as context_fixture


@pytest.fixture
def workspace(tmp_path):
    return context_fixture.__wrapped__(tmp_path)


@pytest.fixture
def jobs(tmp_path, monkeypatch):
    yield from jobs_fixture.__wrapped__(tmp_path, monkeypatch)


def test_context_exact_history_new_owner_current_auth_and_log(workspace, tmp_path):
    contexts, engine, old, state = workspace
    root = tmp_path / "recovery"
    root.mkdir(mode=0o700)
    saved = contexts.create(old, state["id"], payload(contexts, old, state), command_id="save")
    log = InstructorAccessLog(root / "access")
    log.append(actor=old, engagement=state["id"], target=None, outcome="SUCCESS", http_status=200)
    manifest = backup(root / "backup", contexts=contexts, instructor_access_root=log.root)
    new = engine.store.provision("Replacement owner", ["learner"])["id"]
    engine.store.grant(state["id"], new, "learn")
    engine.store.revoke(old)
    receipt = restore(root / "backup", root / "restored", engine=engine, principal_map={old: new})
    recovered = WorkspaceContexts(root / "restored" / "contexts", engine)
    actual = recovered.read(new, state["id"], saved["id"])
    assert actual["user"] == saved["user"]
    assert actual["context_basis_sha256"] == saved["context_basis_sha256"]
    assert actual["version"] == 1
    assert receipt["automatic_execution"] is False
    assert manifest["globally_atomic"] is False
    assert set(manifest["component_captured_at"]) == {"contexts", "instructor_access"}
    with pytest.raises(DomainError):
        recovered.read(old, state["id"], saved["id"])
    with recovered._db() as db:
        with pytest.raises(Exception, match="Immutable context history"):
            db.execute("UPDATE history SET content='changed'")
    archived = InstructorAccessLog(root / "restored" / "instructor-access-archive")
    assert archived.verify() == log.verify()
    assert (archived.root / "access.jsonl").read_bytes() == (log.root / "access.jsonl").read_bytes()
    updated = recovered.save(
        new, state["id"], saved["id"], saved["user"], expected_version=1, command_id="new-edit"
    )
    assert updated["version"] == 2


def test_corrupted_pins_and_unauthorized_restore_create_no_target(workspace, tmp_path):
    contexts, engine, old, state = workspace
    root = tmp_path / "recovery"
    root.mkdir(mode=0o700)
    contexts.create(old, state["id"], payload(contexts, old, state), command_id="save")
    backup(root / "backup", contexts=contexts)
    other = engine.store.provision("Unassigned", ["learner"])["id"]
    with pytest.raises(DomainError):
        restore(root / "backup", root / "denied", engine=engine, principal_map={old: other})
    assert not (root / "denied").exists()
    file = root / "backup" / "contexts.json"
    file.write_bytes(file.read_bytes() + b" ")
    with pytest.raises(DomainError, match="integrity"):
        restore(root / "backup", root / "bad", engine=engine, principal_map={old: old})
    assert not (root / "bad").exists()


def test_running_job_is_archived_without_restart(jobs, tmp_path):
    queue, engine, actor, state, command, entered, release, calls = jobs
    job = queue.submit(actor, state["id"], command)
    queue.start(actor, state["id"], job["id"])
    assert entered.wait(5)
    root = tmp_path / "recovery"
    root.mkdir(mode=0o700)
    backup(root / "backup", jobs=queue)
    receipt = restore(root / "backup", root / "restored")
    archived = json.loads((root / "restored" / "jobs-ARCHIVE-ONLY.json").read_bytes())
    assert archived["tables"]["jobs"][0]["status"] == "RUNNING"
    assert archived["tables"]["jobs"][0]["actor"] == actor
    assert json.loads(archived["tables"]["jobs"][0]["command"]) == command
    assert len(calls) == 1
    assert receipt["jobs"] == "ARCHIVE_ONLY"
    assert not list((root / "restored").rglob("jobs.sqlite3"))
    release.set()


def test_alias_and_existing_target_rejected(workspace, tmp_path):
    contexts, engine, actor, state = workspace
    root = tmp_path / "recovery"
    root.mkdir(mode=0o700)
    backup(root / "backup", contexts=contexts)
    alias = root / "alias"
    alias.symlink_to(root / "backup", target_is_directory=True)
    with pytest.raises(DomainError, match="aliases"):
        restore(alias, root / "bad", engine=engine, principal_map={})
    existing = root / "existing"
    existing.mkdir(mode=0o700)
    with pytest.raises(DomainError, match="New recovery"):
        restore(root / "backup", existing, engine=engine, principal_map={})


def test_rehashed_bundle_cannot_hide_broken_history_or_log_head(workspace, tmp_path):
    import hashlib

    contexts, engine, actor, state = workspace
    root = tmp_path / "recovery"
    root.mkdir(mode=0o700)
    contexts.create(actor, state["id"], payload(contexts, actor, state), command_id="save")
    log = InstructorAccessLog(root / "log")
    log.append(actor=actor, engagement=state["id"], target=None, outcome="DENIED", http_status=403)
    backup(root / "backup", contexts=contexts, instructor_access_root=log.root)
    manifest_path = root / "backup" / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_bytes())
    history_path = root / "backup" / "contexts.json"
    original = history_path.read_bytes()
    body = json.loads(original)
    body["tables"]["history"][0]["content"] = "{}"
    raw = json.dumps(body).encode()
    history_path.write_bytes(raw)
    manifest["members"]["contexts.json"] = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(DomainError, match="history integrity"):
        restore(root / "backup", root / "bad-history", engine=engine, principal_map={actor: actor})
    history_path.write_bytes(original)
    manifest["members"]["contexts.json"] = {
        "sha256": hashlib.sha256(original).hexdigest(),
        "bytes": len(original),
    }
    head = root / "backup" / "head.json"
    raw = b'{"count":0,"sha256":"wrong"}'
    head.write_bytes(raw)
    manifest["members"]["head.json"] = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="head mismatch"):
        restore(root / "backup", root / "bad-log", engine=engine, principal_map={actor: actor})
    assert not (root / "bad-history").exists()
    assert not (root / "bad-log").exists()


def test_restore_publication_failure_keeps_backup_exact_and_retryable(
    workspace, tmp_path, monkeypatch
):
    from enterprise.audit_suite import private_publication

    contexts, engine, actor, state = workspace
    root = tmp_path / "recovery"
    root.mkdir(mode=0o700)
    saved = contexts.create(actor, state["id"], payload(contexts, actor, state), command_id="save")
    backup(root / "backup", contexts=contexts)
    originals = {p.name: p.read_bytes() for p in (root / "backup").iterdir()}
    destination = root / "restored"
    sync = private_publication._sync

    def fail_final_sync(path):
        if path == destination:
            raise OSError("publication unavailable")
        return sync(path)

    with monkeypatch.context() as patch:
        patch.setattr(private_publication, "_sync", fail_final_sync)
        with pytest.raises(OSError, match="publication unavailable"):
            restore(root / "backup", destination, engine=engine, principal_map={actor: actor})
    assert not destination.exists()
    assert {p.name: p.read_bytes() for p in (root / "backup").iterdir()} == originals
    restore(root / "backup", destination, engine=engine, principal_map={actor: actor})
    actual = WorkspaceContexts(destination / "contexts", engine).read(
        actor, state["id"], saved["id"]
    )
    assert actual["user"] == saved["user"]
