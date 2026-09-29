"""Actual protected bound/archive sources; no model or operational authority restoration."""

import json
from copy import deepcopy

import pytest

from enterprise.audit_suite import instructor_key
from enterprise.audit_suite.instructor_key_views import InstructorKeyViews, validate_archive
from enterprise.audit_suite.store import DomainError, canonical, digest
from tests.audit_suite.test_authority_editions import neutral
from tests.audit_suite.test_instructor_releases import change
from tests.audit_suite.test_instructor_releases import release as release_fixture


@pytest.fixture
def views(tmp_path, monkeypatch):
    release, engine, args = release_fixture.__wrapped__(tmp_path)
    definitions = tmp_path / "definitions"
    definitions.mkdir()
    scenario = "MM-13.03.V01"
    (definitions / f"{scenario}.json").write_text(json.dumps(neutral(scenario)))
    monkeypatch.setattr(instructor_key, "obligations", lambda: [scenario])
    parent = tmp_path / "private-corpus"
    parent.mkdir(mode=0o700)
    archive = parent / "archive"
    instructor_key.build_archive(definitions, archive)
    root = tmp_path / "views"
    root.mkdir(mode=0o700)
    core = InstructorKeyViews(root, engine, release.bindings, archive)
    return core, engine, args


def request(core, args, kind="BOUND", **changes):
    context = core._context(args["instructor_id"], args["engagement_id"], kind)
    if kind == "BOUND":
        source = context["data"]["sources"][0]
        user = {
            "title": "My protected view",
            "query": "outside-filter",
            "issue_id": "I1",
            "scope_to_issue": True,
            "source": {k: source[k] for k in ("id", "version", "sha256")},
            "page": 0,
        }
    else:
        row = context["data"]["entries"][0]
        user = {
            "title": "Archive filter",
            "query": "MM",
            "selector": "MM-13",
            "option": "MM-13.03",
            "review": "UNVALIDATED",
            "scenario": {"id": row["id"], "key_sha256": row["key_sha256"]},
            "page": 0,
        }
    value = {
        "view_id": None,
        "kind": kind,
        "key_pin": context["key"],
        "user": user,
        "expected_version": 0,
        "expected_engagement_revision": context["state"]["revision"],
        "command_id": "save-" + kind,
    }
    value.update(changes)
    return value


@pytest.mark.parametrize("kind", ["BOUND", "ARCHIVE"])
def test_save_reload_explicit_restore_delete_and_exact_replay(views, kind):
    core, engine, args = views
    actor, eid = args["instructor_id"], args["engagement_id"]
    before = engine.store.get(actor, eid)
    saved = core.save(actor, eid, request(core, args, kind))
    assert saved["navigation"] is None and saved["personal_content_visible"]
    assert core.save(actor, eid, request(core, args, kind)) == saved
    loaded = InstructorKeyViews(core.root, engine, core.bindings, core.archive_root)
    assert loaded.listing(actor, eid, kind)["views"] == [saved]
    restored = loaded.restore(
        actor,
        eid,
        saved["id"],
        {
            "expected_version": 1,
            "expected_engagement_revision": 0,
            "expected_key_pin": saved["key_pin"],
        },
    )
    assert restored["navigation"] == saved["user"]
    deleted = loaded.delete(
        actor,
        eid,
        saved["id"],
        {"expected_version": 1, "expected_engagement_revision": 0, "command_id": "delete"},
    )
    assert deleted["status"] == "DELETED" and not deleted["personal_content_visible"]
    assert "user" not in deleted and deleted["navigation"] is None
    with pytest.raises(DomainError):
        loaded.save(actor, eid, request(core, args, kind))
    validate_archive(loaded.snapshot())
    assert engine.store.get(actor, eid) == before


def test_ordinary_revision_advances_without_rebinding_historical_key(views):
    core, engine, args = views
    actor, eid = args["instructor_id"], args["engagement_id"]
    saved = core.save(actor, eid, request(core, args))
    change(engine, args, lambda s: s.update(title="Later learner work"))
    row = core.read(actor, eid, saved["id"])
    assert row["context_status"] == "CURRENT" and row["revision_status"] == "ENGAGEMENT_ADVANCED"
    with pytest.raises(DomainError):
        core.restore(
            actor,
            eid,
            row["id"],
            {
                "expected_version": 1,
                "expected_engagement_revision": 0,
                "expected_key_pin": row["key_pin"],
            },
        )
    assert (
        core.restore(
            actor,
            eid,
            row["id"],
            {
                "expected_version": 1,
                "expected_engagement_revision": 1,
                "expected_key_pin": row["key_pin"],
            },
        )["navigation"]
        == row["user"]
    )


@pytest.mark.parametrize("damage", ["scope", "binding", "key"])
def test_stale_personal_metadata_redacted(views, damage):
    core, engine, args = views
    actor, eid = args["instructor_id"], args["engagement_id"]
    saved = core.save(actor, eid, request(core, args))
    if damage == "scope":
        change(engine, args, lambda s: s["scope"].update(period_end="2028-01-01"))
    elif damage == "binding":
        change(engine, args, lambda s: s.update(evidence_acquisition={"changed": True}))
    else:
        core.bindings[eid]["manifest_sha256"] = "f" * 64
    row = core.read(actor, eid, saved["id"])
    assert row["context_status"] != "CURRENT" and not row["personal_content_visible"]
    assert all(k not in row for k in ("user", "key_pin", "title", "query", "source"))
    assert row["navigation"] is None


def test_other_actor_and_noninstructor_isolation(views):
    core, engine, args = views
    actor, eid = args["instructor_id"], args["engagement_id"]
    saved = core.save(actor, eid, request(core, args))
    other = engine.store.provision("Other instructor", ["instructor"])["id"]
    engine.store.grant(eid, other, "instruct")
    assert core.listing(other, eid, "BOUND")["views"] == []
    with pytest.raises(DomainError) as error:
        core.read(other, eid, saved["id"])
    assert error.value.status == 404
    for permission in ("learn", "review"):
        engine.store.grant(eid, actor, permission)
        with pytest.raises(DomainError) as error:
            core.listing(actor, eid, "BOUND")
        assert error.value.status == 403


@pytest.mark.parametrize(
    "damage", ["page", "source_version", "boolean", "issue", "extra", "scenario"]
)
def test_strict_selected_filters(views, damage):
    core, _, args = views
    p = request(core, args, "ARCHIVE" if damage == "scenario" else "BOUND")
    if damage == "page":
        p["user"]["page"] = 1
    if damage == "source_version":
        p["user"]["source"]["version"] = True
    if damage == "boolean":
        p["user"]["scope_to_issue"] = 1
    if damage == "issue":
        p["user"]["issue_id"] = "missing"
    if damage == "extra":
        p["user"]["hidden_text"] = "not permitted"
    if damage == "scenario":
        p["user"]["scenario"]["key_sha256"] = "0" * 64
    with pytest.raises(DomainError):
        core.save(args["instructor_id"], args["engagement_id"], p)
    assert core.snapshot()["events"] == []


def test_cas_final_role_rollback_and_archive_tamper(views, monkeypatch):
    core, engine, args = views
    actor, eid = args["instructor_id"], args["engagement_id"]
    p = request(core, args)
    original = core._finish

    def revoked(*a):
        engine.store.grant(eid, actor, "learn")
        original(*a)

    monkeypatch.setattr(core, "_finish", revoked)
    with pytest.raises(DomainError):
        core.save(actor, eid, p)
    assert core.snapshot()["events"] == []
    engine.store.grant(eid, actor, "instruct")
    monkeypatch.setattr(core, "_finish", original)
    saved = core.save(actor, eid, p)
    q = {**p, "view_id": saved["id"], "command_id": "stale", "expected_version": 0}
    with pytest.raises(DomainError):
        core.save(actor, eid, q)
    archive = deepcopy(core.snapshot())
    body = json.loads(archive["events"][0]["content"])
    body["user"]["private_key_prose"] = "forbidden"
    archive["events"][0].update(content=canonical(body), sha256=digest(body))
    with pytest.raises(DomainError):
        validate_archive(archive)


def test_active_limit_and_reserved_delete_capacity(views, monkeypatch):
    from enterprise.audit_suite import instructor_key_views

    core, _, args = views
    actor, eid = args["instructor_id"], args["engagement_id"]
    p = request(core, args)
    saved = core.save(actor, eid, p)
    for n in range(1, 16):
        core.save(actor, eid, {**p, "command_id": f"new-{n}"})
    with pytest.raises(DomainError):
        core.save(actor, eid, {**p, "command_id": "over-limit"})
    monkeypatch.setattr(instructor_key_views, "MAX_VERSIONS", 1)
    with pytest.raises(DomainError):
        core.save(
            actor,
            eid,
            {**p, "view_id": saved["id"], "expected_version": 1, "command_id": "edit-limit"},
        )
    deleted = core.delete(
        actor,
        eid,
        saved["id"],
        {"expected_version": 1, "expected_engagement_revision": 0, "command_id": "still-delete"},
    )
    assert deleted["status"] == "DELETED"


def test_private_alias_and_live_history_tamper_fail_closed(views, tmp_path):
    core, engine, args = views
    core.save(args["instructor_id"], args["engagement_id"], request(core, args))
    alias = tmp_path / "alias"
    alias.symlink_to(core.root, target_is_directory=True)
    with pytest.raises(DomainError):
        InstructorKeyViews(alias, engine, core.bindings)
    import sqlite3

    with sqlite3.connect(core.path) as db:
        db.execute("DROP TRIGGER key_views_no_update")
        db.execute("UPDATE events SET content='{}'")
    with pytest.raises(DomainError):
        core.listing(args["instructor_id"], args["engagement_id"], "BOUND")


def test_archive_original_change_redacts_saved_metadata(views):
    core, _, args = views
    actor, eid = args["instructor_id"], args["engagement_id"]
    saved = core.save(actor, eid, request(core, args, "ARCHIVE"))
    original = next((core.archive_root / "sources").glob("*.json"))
    original.write_bytes(original.read_bytes() + b" ")
    row = core.read(actor, eid, saved["id"])
    assert row["context_status"] == "KEY_UNAVAILABLE"
    assert "user" not in row and row["navigation"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", []),
        ("view_id", []),
        ("expected_version", True),
        ("expected_engagement_revision", 0.0),
    ],
)
def test_malformed_command_types_fail_closed(views, field, value):
    core, _, args = views
    p = request(core, args)
    p[field] = value
    with pytest.raises(DomainError):
        core.save(args["instructor_id"], args["engagement_id"], p)
