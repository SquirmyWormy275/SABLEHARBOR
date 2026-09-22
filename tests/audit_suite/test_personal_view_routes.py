import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.engine import COLLECTIONS
from enterprise.audit_suite.service import create_app


@pytest.fixture
def setup(tmp_path):
    app = create_app(tmp_path / "audit", workspace_contexts=True, allowed_hosts=["testserver"])
    engine = app.state.engine
    owner = engine.store.provision("Learner", ["learner"])
    other = engine.store.provision("Other learner", ["learner"])
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="View route fixture",
        phase="ACTIVE",
        mode="CLEAN",
        discipline="IT",
        scope={"boundaries": ["corporate"], "programs": ["SOC2"]},
        simulated_at="2027-01-01T00:00:00Z",
        configuration={},
    )
    state["controls"] = [{"id": "C1", "title": "Fixture control"}]
    state = engine.store.create(owner["id"], state, "create")
    engine.store.grant(state["id"], other["id"], "learn")
    client = TestClient(app, base_url="https://testserver")
    headers = {"authorization": "Bearer " + owner["credential"]}
    path = f"/api/engagements/{state['id']}/saved-views"
    ref = client.post(
        path + "/link", headers=headers, json={"kind": "control", "id": "C1", "version": None}
    ).json()
    payload = {
        "title": "My control view",
        "section": "controls",
        "query": "control",
        "framework": "SOC2",
        "reference": ref,
        "table": {"id": "controls", "query": "fixture", "sort": "title", "page": 2},
        "scroll_top": 340,
    }
    return app, client, owner, other, state, path, headers, payload


def test_private_views_round_trip_cas_restore_clear_without_audit_changes(setup):
    app, client, owner, other, state, path, headers, payload = setup
    before = app.state.engine.store.get(owner["id"], state["id"])
    assert client.get("/api/bootstrap", headers=headers).json()["capabilities"]["personal_views"]
    body = {
        "command_id": "create-view",
        "payload": payload,
        "expected_engagement_revision": state["revision"],
    }
    created = client.post(path, headers=headers, json=body)
    assert created.status_code == 200, created.text
    saved = created.json()
    assert saved["navigation"] is None
    assert client.post(path, headers=headers, json=body).json() == saved
    url = path + "/" + saved["id"]
    others = {"authorization": "Bearer " + other["credential"]}
    assert client.get(path, headers=others).json() == {"views": []}
    assert client.get(url, headers=others).status_code == 404
    assert client.get(path).status_code == 401
    pins = {"expected_version": 1, "expected_engagement_revision": state["revision"]}
    assert client.post(url + "/restore", headers=others, json=pins).status_code == 404
    result = client.post(url + "/restore", headers=headers, json=pins)
    assert result.status_code == 200
    assert result.json()["navigation"] == {k: v for k, v in payload.items() if k != "title"}
    changed = {
        **body,
        "command_id": "save-view",
        "expected_version": 1,
        "payload": {**payload, "query": "changed"},
    }
    assert client.put(url, headers=headers, json=changed).json()["version"] == 2
    assert client.post(url + "/restore", headers=headers, json=pins).status_code == 409
    assert (
        client.put(url, headers=headers, json={**changed, "command_id": "stale"}).status_code == 409
    )
    clear = {**pins, "expected_version": 2, "command_id": "clear-view"}
    assert client.post(url + "/clear", headers=headers, json=clear).status_code == 200
    assert client.get(path, headers=headers).json() == {"views": []}
    assert "user" not in client.post(path, headers=headers, json=body).json()
    assert app.state.engine.store.get(owner["id"], state["id"]) == before


def test_cookie_restore_and_save_require_csrf_and_reject_extra_fields(setup):
    _, client, owner, _, state, path, headers, payload = setup
    body = {
        "command_id": "create-view",
        "payload": payload,
        "expected_engagement_revision": state["revision"],
    }
    assert (
        client.post(path, headers=headers, json={**body, "actor": owner["id"]}).status_code == 422
    )
    saved = client.post(path, headers=headers, json=body).json()
    url = path + "/" + saved["id"] + "/restore"
    pins = {"expected_version": 1, "expected_engagement_revision": state["revision"]}
    login = client.post("/api/session", json={"credential": owner["credential"]})
    assert client.post(url, json=pins).status_code == 403
    csrf = {"X-CSRF-Token": login.json()["csrf_token"]}
    assert client.post(url, headers=csrf, json=pins).status_code == 200
    assert (
        client.post(url, headers={**csrf, "Origin": "https://evil.invalid"}, json=pins).status_code
        == 403
    )
    assert (
        client.post(url, headers=csrf, json={**pins, "reference": payload["reference"]}).status_code
        == 422
    )
    assert (
        client.post(
            path,
            headers=csrf,
            json={
                **body,
                "command_id": "stale-context",
                "expected_engagement_revision": state["revision"] + 1,
            },
        ).status_code
        == 409
    )


def test_disabled_personal_views_have_no_store_and_no_capability(tmp_path):
    app = create_app(tmp_path / "audit", allowed_hosts=["testserver"])
    owner = app.state.engine.store.provision("Learner", ["learner"])
    client = TestClient(app, base_url="https://testserver")
    headers = {"authorization": "Bearer " + owner["credential"]}
    assert not client.get("/api/bootstrap", headers=headers).json()["capabilities"][
        "personal_views"
    ]
    assert (
        client.get("/api/engagements/no-engagement/saved-views", headers=headers).status_code == 503
    )
    assert app.state.personal_views is None
    assert not (tmp_path / "audit" / "personal-views").exists()
