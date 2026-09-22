"""Saved protected filters cross HTTP and inert recovery boundaries explicitly."""

import pytest

from enterprise.audit_suite.companion_recovery import backup, restore
from tests.audit_suite.test_instructor_debrief_routes import debrief_http as http_fixture


@pytest.fixture
def context(tmp_path):
    return http_fixture.__wrapped__(tmp_path)


def saved(context):
    app, client, state, teacher, student, other, headers, _ = context
    base = f"/api/engagements/{state['id']}"
    key = client.get(base + "/instructor-binding", headers=headers(teacher)).json()
    payload = {
        "view_id": None,
        "kind": "BOUND",
        "key_pin": key["binding"]["manifest_sha256"],
        "user": {
            "title": "Private selected filter",
            "query": "",
            "page": 0,
            "issue_id": None,
            "scope_to_issue": False,
            "source": None,
        },
        "expected_version": 0,
        "expected_engagement_revision": state["revision"],
        "command_id": "save-key-view",
    }
    path = base + "/instructor-key-views"
    response = client.post(path, headers=headers(teacher), json=payload)
    assert response.status_code == 200, response.text
    return path, payload, response.json()


def test_key_views_http_explicit_restore_retry_and_role_boundary(context):
    app, client, state, teacher, student, other, headers, _ = context
    before = app.state.engine.store.get(teacher["id"], state["id"])
    path, payload, value = saved(context)
    replay = client.post(path, headers=headers(teacher), json=payload)
    assert replay.status_code == 200 and replay.json() == value
    listing = client.get(path + "?kind=BOUND", headers=headers(teacher))
    assert listing.status_code == 200, listing.text
    assert listing.json()["views"][0]["navigation"] is None
    assert client.get(path + "?kind=BOUND", headers=headers(student)).status_code == 403
    assert (
        client.get(path + "?kind=BOUND&kind=ARCHIVE", headers=headers(teacher)).status_code == 422
    )
    assert (
        client.post(path + "?actor=other", headers=headers(teacher), json=payload).status_code
        == 422
    )
    command = {
        "expected_version": value["version"],
        "expected_engagement_revision": state["revision"],
        "expected_key_pin": payload["key_pin"],
    }
    route = path + "/" + value["id"] + "/restore"
    response = client.post(route, headers=headers(teacher), json=command)
    assert response.status_code == 200, response.text
    assert response.json()["navigation"] == payload["user"]
    assert client.post(route, headers=headers(student), json=command).status_code == 403
    assert (
        client.post("/api/session", json={"credential": teacher["credential"]}).status_code == 200
    )
    assert client.post(route, json=command).status_code == 403
    assert app.state.engine.store.get(teacher["id"], state["id"]) == before


def test_saved_key_view_recovery_retains_only_inert_archive(context, tmp_path):
    app, _, state, teacher, _, _, _, _ = context
    saved(context)
    core = app.state.instructor_key_views
    before = app.state.engine.store.get(teacher["id"], state["id"])
    root = tmp_path / "key-view-recovery"
    root.mkdir(mode=0o700)
    manifest = backup(root / "backup", instructor_key_views=core)
    assert (
        manifest["instructor_key_views_restore_mode"] == "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
    )
    receipt = restore(root / "backup", root / "restored")
    original = (root / "backup/instructor-key-views.json").read_bytes()
    retained = root / "restored/instructor-key-views-ARCHIVE-ONLY.json"
    assert retained.read_bytes() == original
    assert retained.stat().st_mode & 0o777 == 0o600
    assert not list((root / "restored").rglob("*.sqlite3"))
    assert receipt["instructor_key_views"] == "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
    assert not receipt["credentials_or_grants_restored"]
    assert app.state.engine.store.get(teacher["id"], state["id"]) == before
