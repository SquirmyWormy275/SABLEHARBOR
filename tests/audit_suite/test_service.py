import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.service import create_app


@pytest.fixture
def setup(tmp_path):
    app = create_app(tmp_path / "state", allowed_hosts=["testserver"])
    store = app.state.engine.store
    learner = store.provision("Learner", ["learner"])
    other = store.provision("Other", ["learner"])
    client = TestClient(app, base_url="https://testserver")
    login = client.post("/api/session", json={"credential": learner["credential"]})
    csrf = login.json()["csrf_token"]
    return app, client, learner, other, {"X-CSRF-Token": csrf}


def test_cookie_csrf_origin_and_private_routes(setup):
    app, client, learner, other, headers = setup
    assert client.get("/api/bootstrap").status_code == 200
    assert client.get("/api/bootstrap").json()["capabilities"]["review_feedback"] is True
    capabilities = client.get("/api/bootstrap").json()["capabilities"]
    assert capabilities["review_independent_resolution"] is True
    assert client.post("/api/logout").status_code == 403
    assert (
        client.post(
            "/api/logout", headers={**headers, "Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert client.get("/api/private-corpus").status_code == 404
    assert client.post("/api/logout", headers=headers).status_code == 200
    assert client.get("/api/bootstrap").status_code == 401


def test_signed_in_machine_access_still_requires_membership(setup):
    app, client, learner, other, headers = setup
    state = app.state.engine.store.create(
        learner["id"],
        {
            "title": "Test",
            "simulated_at": "2027-01-01",
            "discipline": "IT",
            "mode": "CLEAN",
            "phase": "CONFIGURING",
            "artifacts": [],
        },
        "create",
    )
    response = client.get(
        f"/api/engagements/{state['id']}",
        headers={"Authorization": "Bearer " + other["credential"]},
    )
    assert response.status_code == 403
    response = client.get(f"/api/engagements/{state['id']}")
    assert response.status_code == 200
    app.state.engine.store.revoke(learner["id"])
    assert client.get(f"/api/engagements/{state['id']}").status_code == 401


def test_no_actor_or_permission_grants_from_json(setup):
    app, client, learner, other, headers = setup
    response = client.post(
        "/api/engagements", json={"title": "Test", "actor": other["id"]}, headers=headers
    )
    assert response.status_code == 422
    assert app.state.engine.store.listing(learner["id"]) == []


def test_selected_id_upload_validates_population_and_replays(setup):
    from dataclasses import asdict

    from enterprise.audit_suite.engine import COLLECTIONS
    from enterprise.audit_suite.populations import create_population

    app, client, learner, other, headers = setup
    scope = {
        "boundary_id": "B",
        "unit": "ticket",
        "timezone": "UTC",
        "period_start": "2027-01-01T00:00:00Z",
        "period_end": "2027-12-31T00:00:00Z",
    }
    population = create_population(
        "POP-test",
        1,
        [{"id": "a"}, {"id": "b"}],
        scope=scope,
        source={
            "source_id": "source",
            "query": "supplied rows",
            "original_sha256": "a" * 64,
            "completeness_representation": "Client claim",
        },
    )
    state = {k: [] for k in COLLECTIONS}
    state.update(
        title="Selection import fixture",
        phase="ACTIVE",
        scope=scope,
        simulated_at="2028-01-01T09:00:00Z",
        populations=[{"id": population.id, "immutable": asdict(population)}],
    )
    state = app.state.engine.store.create(learner["id"], state, "create-selection-fixture")
    url = f"/api/engagements/{state['id']}/uploads"
    fields = {
        "kind": "selection",
        "linked_id": population.id,
        "purpose": "Inspect supplied records",
        "rationale": "Manual targeted inspection",
        "expected_revision": str(state["revision"]),
        "command_id": "upload-ids",
    }
    response = client.post(
        url, headers=headers, data=fields, files={"file": ("selected.csv", b"id\na\n", "text/csv")}
    )
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["selections"][0]["selected_ids"] == ["a"]
    assert saved["selections"][0]["import_artifact_id"] == saved["artifacts"][0]["id"]
    replay = client.post(
        url, headers=headers, data=fields, files={"file": ("selected.csv", b"id\na\n", "text/csv")}
    )
    assert replay.status_code == 200 and replay.json()["revision"] == saved["revision"]
    denied = client.post(
        url,
        headers=headers,
        data={**fields, "expected_revision": str(saved["revision"]), "command_id": "unknown-ids"},
        files={"file": ("selected.csv", b"id\nnot-supplied\n", "text/csv")},
    )
    assert denied.status_code == 422
    assert app.state.engine.store.get(learner["id"], state["id"])["revision"] == saved["revision"]
    revised = client.post(
        url,
        headers=headers,
        data={
            **fields,
            "kind": "population_revision",
            "command_id": "revise-population",
            "expected_revision": str(saved["revision"]),
        },
        files={"file": ("population-v2.csv", b"id\na\nb\nc\n", "text/csv")},
    )
    assert revised.status_code == 200, revised.text
    updated = revised.json()
    assert len(updated["populations"]) == 2
    assert updated["populations"][1]["predecessor_id"] == population.id
    assert updated["populations"][1]["id"] != population.id
    assert updated["selections"][0]["population_id"] == population.id
    assert updated["selections"][0]["immutable"] == saved["selections"][0]["immutable"]


def test_private_reviewer_export_is_not_a_learner_download(setup):
    import io
    import zipfile

    from enterprise.audit_suite.engine import COLLECTIONS
    from enterprise.audit_suite.generation import run_directory

    app, client, learner, other, headers = setup
    engine = app.state.engine
    instructor = engine.store.provision("Trainer", ["instructor"])
    state = {k: [] for k in COLLECTIONS}
    state.update(
        title="Private review fixture",
        phase="ACTIVE",
        scope={},
        simulated_at="2028-01-01T09:00:00Z",
    )
    state = engine.store.create(instructor["id"], state, "private-review-fixture")
    engine.store.grant(state["id"], learner["id"], "learn")
    world = run_directory(engine, state["id"]) / "world.json"
    world.write_text('{"private_truth":"PRIVATE-ANSWER-MARKER"}')
    world.chmod(0o600)
    command = {
        "command_id": "reviewer-export",
        "expected_revision": state["revision"],
        "kind": "review.export",
        "payload": {"edition": "REVIEWER"},
    }
    url = f"/api/engagements/{state['id']}"
    assert client.post(url + "/commands", headers=headers, json=command).status_code == 403
    response = client.post(
        url + "/commands",
        headers={"Authorization": "Bearer " + instructor["credential"]},
        json=command,
    )
    assert response.status_code == 200, response.text
    exported = response.json()["artifacts"][-1]
    download = url + "/artifacts/" + exported["id"] + "/download"
    assert client.get(download).status_code == 404
    assert client.get(url).json()["artifacts"] == []
    private = client.get(download, headers={"Authorization": "Bearer " + instructor["credential"]})
    assert private.status_code == 200
    with zipfile.ZipFile(io.BytesIO(private.content)) as archive:
        assert b"PRIVATE-ANSWER-MARKER" in archive.read("private/world.json")
    assert (
        client.get(download, headers={"Authorization": "Bearer " + other["credential"]}).status_code
        == 403
    )


def test_declared_body_limit_login_rate_and_wrong_origin_scheme(setup):
    from enterprise.audit_suite.artifacts import MAX_BYTES

    app, client, learner, other, headers = setup
    response = client.post(
        "/api/session",
        content=b"{}",
        headers={"Content-Type": "application/json", "Content-Length": str(MAX_BYTES + 65537)},
    )
    assert response.status_code == 413
    assert client.get("/api/bootstrap").status_code == 200
    assert (
        client.post("/api/logout", headers={**headers, "Origin": "http://testserver"}).status_code
        == 403
    )
    for _ in range(29):
        assert client.post("/api/session", json={"credential": "invalid"}).status_code == 401
    assert client.post("/api/session", json={"credential": "invalid"}).status_code == 429
    assert client.get("/api/bootstrap").status_code == 200


def test_expired_session_fails_and_fresh_login_recovers(setup):
    import time

    app, client, learner, other, headers = setup
    with app.state.engine.store.connect() as db:
        db.execute("UPDATE sessions SET expires=?", (time.time() - 1,))
    assert client.get("/api/bootstrap").status_code == 401
    login = client.post("/api/session", json={"credential": learner["credential"]})
    assert login.status_code == 200
    assert client.get("/api/bootstrap").status_code == 200


def test_streamed_body_limit_cannot_be_bypassed_without_length():
    import asyncio

    from enterprise.audit_suite.service import BodyLimit
    from enterprise.audit_suite.store import DomainError

    seen = []

    async def app(scope, receive, send):
        try:
            while (await receive()).get("more_body"):
                pass
        except DomainError as exc:
            seen.append((exc.code, exc.status))

    chunks = iter(
        [
            {"type": "http.request", "body": b"a" * 8, "more_body": True},
            {"type": "http.request", "body": b"b" * 8, "more_body": False},
        ]
    )

    async def receive():
        return next(chunks)

    async def send(message):
        pass

    asyncio.run(BodyLimit(app, limit=10)({"type": "http", "headers": []}, receive, send))
    assert seen == [("TOO_LARGE", 413)]
