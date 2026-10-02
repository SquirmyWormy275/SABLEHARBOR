import json

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.draft_store import MAX_WORKPAPER_BYTES, DraftStore
from enterprise.audit_suite.service import create_app
from enterprise.audit_suite.store import DomainError, digest


@pytest.fixture
def setup(tmp_path):
    app = create_app(tmp_path / "audit", allowed_hosts=["testserver"])
    store = app.state.engine.store
    user = store.provision("Learner", ["learner"])
    other = store.provision("Other", ["learner"])
    state = store.create(
        user["id"],
        {
            "title": "Draft",
            "scope": {"period": "2027"},
            "workpapers": [{"id": "WP1", "versions": [{"version": 1}]}],
        },
        "create",
    )
    store.grant(state["id"], other["id"], "learn")
    return app, user, other, state


def payload(command="save", version=0, fields=None, base=None):
    return {
        "command_id": command,
        "expected_version": version,
        "fields": fields if fields is not None else {"text": "PERSONAL_UNSUBMITTED_TEXT"},
        "base_workpaper_version": base,
    }


def test_large_workpaper_draft_preserves_full_text_citations_and_existing_quotas(setup):
    app, user, other, state = setup
    drafts = DraftStore(app.state.engine.store)
    args = (user["id"], state["id"], "workpaper.update", "WP1")
    text = "Exact calculation 🧭\n" * 225000
    ids = [f"ART-{i:04d}" for i in range(1694)]
    fields = {"text": text, "evidence_ids": ids}
    written = drafts.write(*args, payload(fields=fields, base=1))
    assert written["fields"] == fields
    assert DraftStore(app.state.engine.store).get(*args)["fields"] == fields
    assert drafts.get(other["id"], *args[1:])["status"] == "EMPTY"
    assert "Exact calculation" not in json.dumps(
        app.state.engine.store.history(user["id"], state["id"])
    )
    with pytest.raises(DomainError):
        drafts.write(
            *args,
            payload("oversize", 1, fields={"text": "🧭" * (MAX_WORKPAPER_BYTES // 4)}, base=1),
        )
    with pytest.raises(DomainError):
        drafts.write(
            *args,
            payload("ids", 1, fields={"evidence_ids": [f"ART-{i}" for i in range(5001)]}, base=1),
        )
    with pytest.raises(DomainError):
        drafts.write(
            *args,
            payload("tasks", 1, fields={"task_ids": [f"TASK-{i}" for i in range(501)]}, base=1),
        )
    with pytest.raises(DomainError):
        drafts.write(user["id"], state["id"], "note.create", "new", payload(fields={"text": text}))
    with pytest.raises(DomainError) as quota:
        drafts.write(
            user["id"], state["id"], "workpaper.add", "new", payload(fields={"text": "x" * 6000000})
        )
    assert quota.value.status == 413
    assert drafts.get(*args) == written


def test_personal_content_not_history_other_user_or_backup_state(setup):
    app, user, other, state = setup
    store = app.state.engine.store
    drafts = DraftStore(store)
    args = (user["id"], state["id"], "note.create", "new")
    written = drafts.write(*args, payload())
    assert written["version"] == 1
    assert drafts.write(*args, payload()) == written
    assert DraftStore(store).get(*args) == written
    assert drafts.get(other["id"], state["id"], "note.create", "new")["status"] == "EMPTY"
    assert "PERSONAL_UNSUBMITTED_TEXT" not in json.dumps(store.history(user["id"], state["id"]))
    assert drafts.path.stat().st_mode & 0o077 == 0
    with pytest.raises(DomainError):
        drafts.write(*args, payload("conflict", 0))
    with pytest.raises(DomainError):
        drafts.write(*args, payload(fields={"actor": "other"}))
    deleted = drafts.write(*args, {"command_id": "discard", "expected_version": 1}, discard=True)
    assert deleted["status"] == "EMPTY" and deleted["version"] == 2
    assert (
        drafts.write(*args, {"command_id": "discard", "expected_version": 1}, discard=True)
        == deleted
    )


def test_scope_change_hides_text_and_workpaper_version_change_marks_stale(setup):
    app, user, _, state = setup
    store = app.state.engine.store
    drafts = DraftStore(store)
    args = (user["id"], state["id"], "workpaper.update", "WP1")
    drafts.write(*args, payload(base=1))

    def revise(s, c, a):
        s["workpapers"][0]["versions"].append({"version": 2})
        return s

    out = store.command(
        user["id"],
        state["id"],
        {
            "command_id": "revision",
            "expected_revision": state["revision"],
            "kind": "test",
            "payload": {},
        },
        revise,
        permissions={"learn"},
    )
    assert drafts.get(*args)["workpaper_stale"] is True
    assert drafts.get(*args)["fields"]["text"] == "PERSONAL_UNSUBMITTED_TEXT"

    def scope(s, c, a):
        s["scope"] = {"period": "2028"}
        return s

    store.command(
        user["id"],
        state["id"],
        {
            "command_id": "scope",
            "expected_revision": out["revision"],
            "kind": "test",
            "payload": {},
        },
        scope,
        permissions={"learn"},
    )
    assert drafts.get(*args)["status"] == "STALE"
    assert "fields" not in drafts.get(*args)
    with pytest.raises(DomainError):
        drafts.write(*args, payload("overwrite", 1, base=2))
    store.revoke(user["id"])
    with pytest.raises(DomainError):
        drafts.get(*args)


def test_acquisition_change_withholds_old_draft_and_does_not_rehash_legacy_row(setup):
    app, user, _, state = setup
    store = app.state.engine.store
    drafts = DraftStore(store)
    args = (user["id"], state["id"], "workpaper.update", "WP1")
    drafts.write(
        *args, payload(base=1, fields={"text": "Authored analysis", "evidence_ids": ["OLD"]})
    )
    assert drafts.get(*args)["status"] == "DRAFT"

    def change_acquisition(s, c, a):
        s["evidence_acquisition"] = "RETAINED_COPY"
        return s

    changed = store.command(
        user["id"],
        state["id"],
        {
            "command_id": "acquisition-change",
            "expected_revision": state["revision"],
            "kind": "fixture",
            "payload": {},
        },
        change_acquisition,
        permissions={"learn"},
    )
    stale = drafts.get(*args)
    assert stale["status"] == "STALE" and "fields" not in stale
    with pytest.raises(DomainError):
        drafts.write(*args, payload("stale-overwrite", 1, base=1))
    assert store.get(user["id"], state["id"])["revision"] == changed["revision"]

    # Pre-change rows used a digest without acquisition. Preserve their bytes;
    # the new context must treat even a matching current acquisition as stale.
    legacy = digest(
        [
            state["id"],
            "learn",
            changed["scope"],
            changed.get("generation_epoch", 0),
            changed.get("company_source_binding"),
        ]
    )
    with drafts._db() as db:
        db.execute(
            "UPDATE drafts SET context_digest=? WHERE principal=? AND engagement=? "
            "AND action=? AND object_id=?",
            (legacy, *args),
        )
    old_format = drafts.get(*args)
    assert old_format["status"] == "STALE_SOURCE"
    assert old_format["fields"] == {"text": "Authored analysis"}
    assert "OLD" not in json.dumps(old_format)
    with drafts._db() as db:
        assert (
            db.execute(
                "SELECT context_digest FROM drafts WHERE principal=? AND engagement=? "
                "AND action=? AND object_id=?",
                args,
            ).fetchone()[0]
            == legacy
        )
    with pytest.raises(DomainError):
        drafts.write(*args, payload("legacy-overwrite", 1, base=1))

    def change_source(s, c, a):
        s["company_source_binding"] = {"branch": "messy"}
        return s

    store.command(
        user["id"],
        state["id"],
        {
            "command_id": "source-change",
            "expected_revision": changed["revision"],
            "kind": "fixture",
            "payload": {},
        },
        change_source,
        permissions={"learn"},
    )
    assert drafts.get(*args)["status"] == "STALE"
    assert "fields" not in drafts.get(*args)
    store.revoke(user["id"])
    with pytest.raises(DomainError):
        drafts.get(*args)


def test_routes_auth_csrf_and_signout_preserves_draft(setup):
    app, user, _, state = setup
    client = TestClient(app, base_url="https://testserver")
    url = f"/api/engagements/{state['id']}/drafts/note.create/new"
    assert client.get(url).status_code == 401
    response = client.post("/api/session", json={"credential": user["credential"]})
    headers = {"X-CSRF-Token": response.json()["csrf_token"]}
    assert client.put(url, json=payload()).status_code == 403
    assert client.put(url, json=payload(), headers=headers).status_code == 200
    assert client.post("/api/logout", headers=headers).status_code == 200
    assert client.get(url).status_code == 401
    client.post("/api/session", json={"credential": user["credential"]})
    assert client.get(url).json()["fields"]["text"] == "PERSONAL_UNSUBMITTED_TEXT"


def test_size_permission_digest_and_expired_principal(setup):
    app, user, _, state = setup
    store = app.state.engine.store
    drafts = DraftStore(store)
    args = (user["id"], state["id"], "note.create", "new")
    with pytest.raises(DomainError):
        drafts.write(*args, payload(fields={"text": "界" * 40000}))
    drafts.write(*args, payload())
    store.grant(state["id"], user["id"], "review")
    with pytest.raises(DomainError):
        drafts.get(*args)
    store.grant(state["id"], user["id"], "instruct")
    assert drafts.get(*args)["status"] == "STALE"
    assert "PERSONAL_UNSUBMITTED_TEXT" not in json.dumps(drafts.get(*args))
    with store.connect() as db:
        db.execute("UPDATE principals SET expires=0 WHERE id=?", (user["id"],))
    with pytest.raises(DomainError):
        drafts.get(*args)


def test_note_control_choice_must_be_in_actual_scope(setup):
    app, user, _, state = setup
    store = app.state.engine.store

    def add_control(s, c, a):
        s["controls"] = [{"id": "C1"}]
        return s

    store.command(
        user["id"],
        state["id"],
        {
            "command_id": "scope-control",
            "expected_revision": state["revision"],
            "kind": "fixture",
            "payload": {},
        },
        add_control,
        permissions={"learn"},
    )
    drafts = DraftStore(store)
    args = (user["id"], state["id"], "note.create", "new")
    result = drafts.write(*args, payload(fields={"title": "Observation", "control_id": "C1"}))
    assert result["fields"]["control_id"] == "C1"
    with pytest.raises(DomainError):
        drafts.write(*args, payload("wrong-control", 1, fields={"control_id": "OTHER"}))
    assert drafts.get(*args) == result
