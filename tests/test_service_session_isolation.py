"""Host-shared cookie jars must not merge separate private runtime sessions."""

import re
from http.cookiejar import CookieJar
from http.cookies import SimpleCookie

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.service import create_app


def login(client, credential):
    response = client.post("/api/session", json={"credential": credential})
    assert response.status_code == 200, response.text
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    assert len(cookie) == 1
    name = next(iter(cookie))
    return name, cookie[name], response.json()["csrf_token"]


@pytest.fixture
def workrooms(tmp_path):
    jar = CookieJar()
    applications = [
        create_app(tmp_path / name, allowed_hosts=["localhost"])
        for name in ("private-a", "private-b")
    ]
    clients = [
        TestClient(app, base_url=f"https://localhost:{8788 + i}", cookies=jar)
        for i, app in enumerate(applications)
    ]
    actors = [
        app.state.engine.store.provision(label, ["learner"])
        for app, label in zip(applications, ("A learner", "B learner"), strict=True)
    ]
    assert clients[0].cookies.jar is clients[1].cookies.jar is jar
    yield applications, clients, actors, jar
    for client in clients:
        client.close()


def test_two_ports_share_one_jar_with_distinct_sessions_and_isolated_logout(workrooms):
    apps, clients, actors, jar = workrooms
    names, csrf = [], []
    for client, actor in zip(clients, actors, strict=True):
        name, cookie, token = login(client, actor["credential"])
        assert re.fullmatch(r"sh_audit_session_[0-9a-f]{32}", name)
        assert cookie["httponly"] and cookie["secure"]
        assert cookie["samesite"].lower() == "strict"
        assert cookie["path"] == "/" and cookie["max-age"] == "3600"
        names.append(name)
        csrf.append(token)
    assert names[0] != names[1]
    assert {cookie.name for cookie in jar} == set(names)
    for client, actor in zip(clients, actors, strict=True):
        response = client.get("/api/bootstrap")
        assert response.status_code == 200
        assert response.json()["viewer"]["id"] == actor["id"]
    # Port-specific origin checking and per-session CSRF remain necessary.
    assert clients[0].post("/api/logout").status_code == 403
    assert clients[0].post("/api/logout", headers={"X-CSRF-Token": csrf[1]}).status_code == 403
    assert (
        clients[0]
        .post("/api/logout", headers={"X-CSRF-Token": csrf[0], "Origin": "https://localhost:8789"})
        .status_code
        == 403
    )
    response = clients[0].post("/api/logout", headers={"X-CSRF-Token": csrf[0]})
    assert response.status_code == 200
    removed = SimpleCookie()
    removed.load(response.headers["set-cookie"])
    assert set(removed) == {names[0]}
    assert {cookie.name for cookie in jar} == {names[1]}
    assert clients[0].get("/api/bootstrap").status_code == 401
    assert clients[1].get("/api/bootstrap").json()["viewer"]["id"] == actors[1]["id"]


def test_same_canonical_runtime_namespace_survives_app_restart_and_port_change(workrooms):
    apps, clients, actors, jar = workrooms
    name, _, csrf = login(clients[0], actors[0]["credential"])
    root = apps[0].state.engine.store.root
    restarted = create_app(root / ".", allowed_hosts=["localhost"])
    with TestClient(restarted, base_url="https://localhost:9898", cookies=jar) as client:
        response = client.get("/api/bootstrap")
        assert response.status_code == 200
        assert response.json()["viewer"]["id"] == actors[0]["id"]
        # A second login names the same cookie, without exposing the directory.
        next_name, _, _ = login(client, actors[0]["credential"])
        assert next_name == name and str(root) not in response.text


def test_cross_runtime_and_legacy_cookies_never_fall_back(workrooms):
    _, clients, actors, _ = workrooms
    name_a, cookie_a, _ = login(clients[0], actors[0]["credential"])
    name_b, cookie_b, _ = login(clients[1], actors[1]["credential"])
    foreign = cookie_a.value
    # Explicit Cookie headers prevent the valid jar cookie masking each negative.
    for header in (f"{name_a}={foreign}", f"{name_b}={foreign}", f"sh_audit_session={foreign}"):
        assert clients[1].get("/api/bootstrap", headers={"Cookie": header}).status_code == 401
    assert (
        clients[1]
        .get(
            "/api/bootstrap",
            headers={
                "Cookie": "sh_audit_session=" + foreign,
                "Authorization": "Bearer " + actors[1]["credential"],
            },
        )
        .status_code
        == 200
    )
    assert (
        clients[1]
        .get("/api/bootstrap", headers={"Authorization": "Bearer " + actors[0]["credential"]})
        .status_code
        == 401
    )


def test_explicit_loopback_insecure_cookie_setting_remains_supported(tmp_path):
    app = create_app(tmp_path / "local", allowed_hosts=["localhost"], secure_cookie=False)
    actor = app.state.engine.store.provision("Local learner", ["learner"])
    with TestClient(app, base_url="http://localhost:8788") as client:
        _, cookie, csrf = login(client, actor["credential"])
        assert not cookie["secure"] and cookie["httponly"]
        assert cookie["samesite"].lower() == "strict"
        assert client.get("/api/bootstrap").status_code == 200
        assert client.post("/api/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
