from fastapi.testclient import TestClient

from enterprise.audit_suite.engine import COLLECTIONS
from enterprise.audit_suite.service import create_app


def test_personal_saved_context_routes_pin_conflict_and_isolation(tmp_path):
    app = create_app(tmp_path / "audit", workspace_contexts=True, allowed_hosts=["testserver"])
    engine = app.state.engine
    owner = engine.store.provision("Neutral learner", ["learner"])
    other = engine.store.provision("Other learner", ["learner"])
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Neutral context",
        phase="ACTIVE",
        mode="CLEAN",
        discipline="IT",
        scope={"boundaries": ["corporate"]},
        simulated_at="2027-01-01T00:00:00Z",
        configuration={},
    )
    state["controls"] = [{"id": "C1", "title": "Neutral control"}]
    state = engine.store.create(owner["id"], state, "create")
    engine.store.grant(state["id"], other["id"], "learn")
    client = TestClient(app, base_url="https://testserver")
    path = f"/api/engagements/{state['id']}/contexts"
    headers = {"authorization": "Bearer " + owner["credential"]}
    others = {"authorization": "Bearer " + other["credential"]}
    link = client.post(
        path + "/link", headers=headers, json={"kind": "control", "id": "C1", "version": None}
    )
    assert link.status_code == 200
    payload = {
        "title": "My question",
        "question": "What supports this decision?",
        "next_step": "Read the source",
        "links": [link.json()],
    }
    created = client.post(
        path, headers=headers, json={"command_id": "create-context", "payload": payload}
    )
    assert created.status_code == 200, created.text
    record = created.json()
    assert record["link_status"][0]["status"] == "EXACT_PIN_AVAILABLE"
    assert client.get(path, headers=others).json() == {"contexts": []}
    assert client.get(path).status_code == 401
    assert (
        client.put(
            path + "/" + record["id"],
            headers=others,
            json={"command_id": "steal", "expected_version": 1, "payload": payload},
        ).status_code
        == 404
    )
    newer = client.put(
        path + "/" + record["id"],
        headers=headers,
        json={
            "command_id": "v2",
            "expected_version": 1,
            "payload": {**payload, "question": "Updated explicit question"},
        },
    )
    assert newer.status_code == 200
    stale = client.put(
        path + "/" + record["id"],
        headers=headers,
        json={"command_id": "stale", "expected_version": 1, "payload": payload},
    )
    assert stale.status_code == 409
    assert engine.store.get(owner["id"], state["id"])["revision"] == state["revision"]
    assert (
        client.post(
            path + "/" + record["id"] + "/reset",
            headers=headers,
            json={"command_id": "reset", "expected_version": 2},
        ).status_code
        == 200
    )
    assert client.get(path, headers=headers).json() == {"contexts": []}
