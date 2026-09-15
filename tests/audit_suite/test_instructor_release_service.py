"""Actual HTTP isolation and explicit preview/confirm for selected assistance."""

from fastapi.testclient import TestClient

from enterprise.audit_suite.service import create_app
from tests.audit_suite.test_bound_instructor import configured
from tests.audit_suite.test_explanation_binding import workspace as base_workspace


def test_explicit_named_release_http_isolation_and_csrf(tmp_path):
    engine, args = base_workspace.__wrapped__(tmp_path)
    engine.store.command(
        args["instructor_id"],
        args["engagement_id"],
        {
            "command_id": "fixture-metadata",
            "expected_revision": 0,
            "kind": "fixture.metadata",
            "payload": {},
        },
        lambda state, command, actor: {
            **state,
            "title": "Release fixture",
            "discipline": "COMPLIANCE",
            "mode": "CLEAN",
            "phase": "ACTIVE",
        },
        permissions={"instruct"},
    )
    config, _ = configured(engine, args)
    teacher = engine.store.provision("Teacher", ["instructor"])
    student = engine.store.provision("Student", ["learner"])
    other = engine.store.provision("Other", ["learner"])
    eid = args["engagement_id"]
    for person, role in [(teacher, "instruct"), (student, "learn"), (other, "learn")]:
        engine.store.grant(eid, person["id"], role)
    app = create_app(engine.store.root, instructor_bindings=config, allowed_hosts=["testserver"])
    client = TestClient(app, base_url="https://testserver")
    base = f"/api/engagements/{eid}"
    th = {"Authorization": "Bearer " + teacher["credential"]}
    sh = {"Authorization": "Bearer " + student["credential"]}
    oh = {"Authorization": "Bearer " + other["credential"]}
    before = client.get(base, headers=sh).json()
    assert client.get("/api/bootstrap", headers=th).json()["capabilities"]["instructor_releases"]
    assert client.get(base + "/instructor-releases/options", headers=sh).status_code == 403
    options = client.get(base + "/instructor-releases/options", headers=th)
    assert options.status_code == 200, options.text
    assert "credential" not in options.text
    payload = {
        "recipient_id": student["id"],
        "expected_revision": before["revision"],
        "stage": "HINT",
        "text": "Compare the dates in the collected records.",
        "pointers": [],
    }
    route = base + "/instructor-releases/preview"
    assert client.post(route, headers=sh, json=payload).status_code == 403
    login = client.post("/api/session", json={"credential": teacher["credential"]})
    assert login.status_code == 200
    assert client.post(route, json=payload).status_code == 403
    response = client.post(route, headers=th, json=payload)
    assert response.status_code == 200, response.text
    preview = response.json()
    assert client.get(base + "/assistance", headers=sh).json() == []
    confirm = {
        "preview_id": preview["preview"]["id"],
        "preview_sha256": preview["preview_sha256"],
        "command_id": "confirm",
    }
    released = client.post(base + "/instructor-releases", headers=th, json=confirm)
    assert released.status_code == 200, released.text
    rid = released.json()["release_id"]
    history = client.get(base + "/instructor-releases", headers=th)
    assert history.status_code == 200
    assert history.json()[0]["recipient_id"] == student["id"]
    assert payload["text"] not in history.text
    assert client.get(base + "/instructor-releases", headers=sh).status_code == 403
    assert (
        client.get(base + "/assistance?recipient_id=" + other["id"], headers=sh).status_code == 422
    )
    assert (
        client.post(base + "/instructor-releases", headers=th, json=confirm).json()
        == released.json()
    )
    assert client.get(base + "/assistance", headers=oh).json() == []
    read = base + "/assistance/" + rid
    assert client.get(read, headers=oh).status_code == 404
    assert client.get(base + "/assistance", headers=sh).json()[0]["delivered"] is False
    content = client.get(read, headers=sh)
    assert content.status_code == 200, content.text
    assert content.json()["content"]["text"] == payload["text"]
    assert client.get(base + "/assistance", headers=sh).json()[0]["delivered"] is True
    assert client.get(base, headers=sh).json() == before
    assert payload["text"] not in client.get(base, headers=th).text
    ack = client.post(
        read + "/acknowledge", headers=sh, json={"release_id": rid, "command_id": "ack"}
    )
    assert ack.status_code == 200, ack.text
    revoked = client.post(
        base + "/instructor-releases/" + rid + "/revoke",
        headers=th,
        json={"release_id": rid, "command_id": "revoke", "reason": "Withdraw this hint"},
    )
    assert revoked.status_code == 200, revoked.text
    assert client.get(read, headers=sh).status_code == 403
    assert client.post(base + "/instructor-releases", headers=th, json=confirm).status_code == 403
    assert client.get(base, headers=sh).json() == before


def test_unconfigured_assistance_has_no_store(tmp_path):
    app = create_app(tmp_path / "ordinary", allowed_hosts=["testserver"])
    user = app.state.engine.store.provision("Learner", ["learner"])
    client = TestClient(app, base_url="https://testserver")
    headers = {"Authorization": "Bearer " + user["credential"]}
    assert (
        client.get("/api/bootstrap", headers=headers).json()["capabilities"]["instructor_releases"]
        is False
    )
    assert client.get("/api/engagements/ENG-missing/assistance", headers=headers).status_code == 503
    assert not (app.state.engine.store.root / "instructor-releases").exists()
