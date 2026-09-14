import threading

from fastapi.testclient import TestClient

from enterprise.audit_suite.engine import COLLECTIONS
from enterprise.audit_suite.service import create_app


def test_actual_routes_actor_isolation_durable_completion_and_no_prompt_leak(tmp_path, monkeypatch):
    app = create_app(tmp_path / "audit", background_jobs=True, allowed_hosts=["testserver"])
    engine = app.state.engine
    owner = engine.store.provision("Neutral learner", ["learner"])
    other = engine.store.provision("Other learner", ["learner"])
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Neutral work",
        phase="ACTIVE",
        mode="CLEAN",
        discipline="IT",
        scope={"boundaries": ["corporate"]},
        simulated_at="2027-01-01T00:00:00Z",
        configuration={},
    )
    state["meetings"] = [{"id": "M1", "kind": "KICKOFF", "person_id": "P1", "messages": []}]
    state["people"] = [{"id": "P1", "name": "Neutral contact"}]
    state = engine.store.create(owner["id"], state, "create")
    engine.store.grant(state["id"], other["id"], "learn")
    release = threading.Event()

    def conversation(*args):
        assert release.wait(5)
        return {"text": "Company answer", "source_refs": [], "proposed_actions": []}

    monkeypatch.setattr(engine, "_conversation", conversation)
    client = TestClient(app, base_url="https://testserver")
    path = f"/api/engagements/{state['id']}/jobs"
    headers = {"authorization": f"Bearer {owner['credential']}"}
    command = {
        "command_id": "bg1",
        "expected_revision": state["revision"],
        "kind": "meeting.message",
        "payload": {"meeting_id": "M1", "content": "PRIVATE QUESTION"},
    }
    try:
        response = client.post(path, headers=headers, json=command)
        assert response.status_code == 200, response.text
        job = response.json()
        assert job["status"] in {"PENDING", "RUNNING"}
        assert "PRIVATE QUESTION" not in response.text
        visible = client.get(path, headers=headers)
        assert len(visible.json()["jobs"]) == 1
        assert "payload" not in visible.text
        other_headers = {"authorization": f"Bearer {other['credential']}"}
        assert client.get(path, headers=other_headers).json()["jobs"] == []
        assert (
            client.post(
                path + "/" + job["id"] + "/retry",
                headers=other_headers,
                json={"observed_job_revision": job["job_revision"]},
            ).status_code
            == 404
        )
        assert client.get(path).status_code == 401
        original = client.get(path + "/" + job["id"] + "/input", headers=headers)
        assert original.status_code == 200
        assert original.json() == command
        assert (
            client.get(path + "/" + job["id"] + "/input", headers=other_headers).status_code == 404
        )
    finally:
        release.set()
        for thread in list(app.state.background_jobs.threads.values()):
            thread.join(5)
    completed = client.get(path, headers=headers).json()["jobs"][0]
    assert completed["status"] == "COMPLETED"
    repeated = client.post(path, headers=headers, json=command)
    assert repeated.json()["id"] == completed["id"]
    assert repeated.json()["status"] == "COMPLETED"
    assert (
        client.post(
            path + "/" + job["id"] + "/retry",
            headers=headers,
            json={"observed_job_revision": completed["job_revision"]},
        ).status_code
        == 409
    )
