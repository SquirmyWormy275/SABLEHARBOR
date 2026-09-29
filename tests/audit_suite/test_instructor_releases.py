"""Actual private binding/store fixtures; no populated answer service or models."""

import pytest

from enterprise.audit_suite.explanation_binding import bind_snapshot
from enterprise.audit_suite.instructor_releases import InstructorReleases
from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_explanation_binding import workspace


@pytest.fixture
def release(tmp_path):
    engine, args = workspace.__wrapped__(tmp_path)
    receipt = bind_snapshot(engine, **args)
    root = tmp_path / "releases"
    root.mkdir(mode=0o700)
    bindings = {
        args["engagement_id"]: {
            "path": args["output"],
            "manifest_sha256": receipt["manifest_sha256"],
        }
    }
    core = InstructorReleases(root, engine, bindings)
    return core, engine, args


def preview(core, args, **changes):
    p = {
        "recipient_id": args["audited_actor_id"],
        "expected_revision": 0,
        "stage": "HINT",
        "text": "Consider the timing of the selected records.",
        "pointers": [],
    }
    p.update(changes)
    return core.preview(args["instructor_id"], args["engagement_id"], p)


def confirm(core, args, p, command="confirm"):
    return core.confirm(
        args["instructor_id"],
        args["engagement_id"],
        {
            "preview_id": p["preview"]["id"],
            "preview_sha256": p["preview_sha256"],
            "command_id": command,
        },
    )


def change(engine, args, fn):
    actor, eid = args["instructor_id"], args["engagement_id"]
    s = engine.store.get(actor, eid)
    return engine.store.command(
        actor,
        eid,
        {
            "command_id": "change-" + str(s["revision"]),
            "expected_revision": s["revision"],
            "kind": "test.change",
            "payload": {},
        },
        lambda s, c, a: fn(s) or s,
        permissions={"instruct"},
    )


def test_private_preview_explicit_delivery_ack_and_revocation(release):
    core, e, args = release
    teacher, learner, eid = args["instructor_id"], args["audited_actor_id"], args["engagement_id"]
    before = e.store.get(teacher, eid)
    p = preview(core, args)
    assert not p["delivered"] and core.list(learner, eid) == []
    saved = confirm(core, args, p)
    rid = saved["release_id"]
    assert confirm(core, args, p) == saved
    listed = core.list(learner, eid)
    assert listed[0]["delivered"] is False and "content" not in listed[0]
    with pytest.raises(DomainError):
        core.acknowledge(learner, eid, {"release_id": rid, "command_id": "early"})
    received = core.read(learner, eid, rid)
    assert received["content"] == p["preview"]["content"]
    assert "snapshot" not in received and "issues" not in received
    assert core.read(learner, eid, rid) == received
    core.acknowledge(learner, eid, {"release_id": rid, "command_id": "ack"})
    with core._db() as db:
        assert core._actions(db, rid) == ["RELEASED", "DELIVERED", "ACKNOWLEDGED"]
    core.revoke(
        teacher, eid, {"release_id": rid, "command_id": "revoke", "reason": "Withdraw this hint"}
    )
    with pytest.raises(DomainError):
        core.read(learner, eid, rid)
    with pytest.raises(DomainError):
        confirm(core, args, p)
    assert core.list(learner, eid)[0]["status"] == "REVOKED"
    assert e.store.get(teacher, eid) == before


@pytest.mark.parametrize("change_kind", ["revision", "scope", "recipient", "teacher", "key"])
def test_confirm_stale_or_revoked_preview_never_publishes(release, change_kind):
    core, e, args = release
    p = preview(core, args)
    if change_kind == "revision":
        change(e, args, lambda s: s.update(title="Changed work"))
    if change_kind == "scope":
        change(e, args, lambda s: s["scope"].update(period_end="2028-01-01"))
    if change_kind == "recipient":
        e.store.grant(args["engagement_id"], args["audited_actor_id"], "review")
    if change_kind == "teacher":
        e.store.grant(args["engagement_id"], args["instructor_id"], "learn")
    if change_kind == "key":
        core.bindings[args["engagement_id"]]["manifest_sha256"] = "0" * 64
    with pytest.raises(DomainError):
        confirm(core, args, p)
    with core._db() as db:
        assert db.execute("SELECT count(*) FROM documents WHERE kind='RELEASE'").fetchone()[0] == 0


def test_recipient_isolation_and_context_suspend_after_release(release):
    core, e, args = release
    p = preview(core, args)
    rid = confirm(core, args, p)["release_id"]
    other = e.store.provision("Other learner", ["learner"])["id"]
    eid = args["engagement_id"]
    e.store.grant(eid, other, "learn")
    assert core.list(other, eid) == []
    with pytest.raises(DomainError):
        core.read(other, eid, rid)
    change(e, args, lambda s: s["scope"].update(period_end="2028-01-01"))
    assert core.list(args["audited_actor_id"], eid)[0]["status"] == "SUSPENDED"
    with pytest.raises(DomainError):
        core.read(args["audited_actor_id"], eid, rid)


def test_pointer_exact_retained_bytes_and_task_pin(release):
    core, e, args = release
    eid = args["engagement_id"]
    artifact = e.artifacts.retain(
        eid, "local.txt", b"Only this visible original", source={}, coverage={}
    )
    task = {"id": "TASK", "control_id": "CONTROL1", "title": "Declared procedure"}
    change(e, args, lambda s: s.update(tasks=[task], artifacts=[artifact]))
    pointers = [
        {"kind": "artifact", "id": artifact["id"], "sha256": artifact["sha256"]},
        {"kind": "task", "id": "TASK", "sha256": digest(task)},
    ]
    p = preview(core, args, expected_revision=1, stage="POINTER", pointers=pointers)
    rid = confirm(core, args, p)["release_id"]
    assert core.read(args["audited_actor_id"], eid, rid)["content"]["pointers"] == pointers
    (e.artifacts.root / artifact["sha256"]).write_bytes(b"Changed bytes")
    with pytest.raises(DomainError):
        core.read(args["audited_actor_id"], eid, rid)


@pytest.mark.parametrize(
    "stage,pointers",
    [
        ("EXPLANATION", []),
        ("HINT", [{"kind": "task", "id": "x", "sha256": "0" * 64}]),
        ("POINTER", []),
    ],
)
def test_unsupported_or_inconsistent_stages(release, stage, pointers):
    core, e, args = release
    with pytest.raises(DomainError):
        preview(core, args, stage=stage, pointers=pointers)


def test_replay_checks_current_membership_and_changed_command(release):
    core, e, args = release
    p = preview(core, args)
    confirm(core, args, p)
    p2 = preview(core, args, text="Different hint")
    with pytest.raises(DomainError):
        confirm(core, args, p2)
    e.store.grant(args["engagement_id"], args["audited_actor_id"], "review")
    with pytest.raises(DomainError):
        confirm(core, args, p)


def test_private_alias_and_writable_database_rejected(release, tmp_path):
    core, e, args = release
    core.path.chmod(0o644)
    with pytest.raises(DomainError):
        preview(core, args)
    core.path.chmod(0o600)
    alias = tmp_path / "alias"
    alias.symlink_to(core.root, target_is_directory=True)
    with pytest.raises(DomainError):
        InstructorReleases(alias, e, core.bindings)


def test_options_are_metadata_only_and_history_omits_draft_content(release, monkeypatch):
    core, e, args = release
    eid, teacher = args["engagement_id"], args["instructor_id"]
    original = e.artifacts.retain(eid, "visible.txt", b"original", source={}, coverage={})
    private = {**original, "id": "PRIVATE", "audience": "REVIEWER"}
    change(
        e,
        args,
        lambda s: s.update(
            tasks=[{"id": "TASK", "control_id": "CONTROL1", "title": "Work"}],
            artifacts=[original, private],
        ),
    )
    monkeypatch.setattr(e.artifacts, "read", lambda _: pytest.fail("Options must not read bytes"))
    options = core.options(teacher, eid)
    assert options["recipients"] == [{"id": args["audited_actor_id"], "name": "Learner"}]
    assert options["artifacts"] == [
        {"id": original["id"], "name": "visible.txt", "sha256": original["sha256"]}
    ]
    assert set(options["recipients"][0]) == {"id", "name"}
    p = preview(core, args, expected_revision=1)
    assert core.history(teacher, eid) == []
    rid = confirm(core, args, p)["release_id"]
    row = core.history(teacher, eid)[0]
    assert row["release_id"] == rid and row["stage"] == "HINT" and not row["delivered"]
    assert "content" not in row and "text" not in row
    with pytest.raises(DomainError):
        confirm(core, args, p, command="new-command-same-preview")


def test_snapshot_roundtrip_and_malformed_journal_rejected(release):
    from copy import deepcopy

    from enterprise.audit_suite.instructor_releases import validate_snapshot

    core, e, args = release
    p = preview(core, args)
    rid = confirm(core, args, p)["release_id"]
    core.read(args["audited_actor_id"], args["engagement_id"], rid)
    body = core.snapshot()
    assert validate_snapshot(body) == body
    bad = deepcopy(body)
    bad["tables"]["events"][0]["sha"] = "0" * 64
    with pytest.raises(DomainError):
        validate_snapshot(bad)
    bad = deepcopy(body)
    bad["tables"]["documents"][0]["content"] = "{}"
    with pytest.raises(DomainError):
        validate_snapshot(bad)


def test_role_revocation_during_final_check_rolls_back_publication(release, monkeypatch):
    core, e, args = release
    p = preview(core, args)
    real = core._key
    calls = 0

    def revoke_after_key(teacher, eid):
        nonlocal calls
        result = real(teacher, eid)
        calls += 1
        if calls == 1:
            e.store.grant(eid, args["audited_actor_id"], "review")
        return result

    monkeypatch.setattr(core, "_key", revoke_after_key)
    with pytest.raises(DomainError):
        confirm(core, args, p)
    with core._db() as db:
        assert db.execute("SELECT count(*) FROM documents WHERE kind='RELEASE'").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 0
