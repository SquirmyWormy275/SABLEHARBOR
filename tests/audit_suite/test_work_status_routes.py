from fastapi.testclient import TestClient

from enterprise.audit_suite.engine import COLLECTIONS
from enterprise.audit_suite.service import create_app


def test_work_status_authorization_and_no_formal_mutation(tmp_path):
    app = create_app(tmp_path / "audit", allowed_hosts=["testserver"])
    engine = app.state.engine
    owner = engine.store.provision("Learner", ["learner"])
    outsider = engine.store.provision("Other learner", ["learner"])
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Recorded work", phase="ACTIVE", mode="CLEAN", discipline="IT",
        scope={"boundaries": ["corporate"]},
        simulated_at="2027-01-01T00:00:00Z", configuration={},
    )
    state["controls"] = [{"id": "C1", "title": "Control"}]
    state = engine.store.create(owner["id"], state, "create")
    client = TestClient(app, base_url="https://testserver")
    path = f"/api/engagements/{state['id']}/work-status"
    assert client.get(path).status_code == 401
    assert client.get(path, headers={
        "authorization": "Bearer " + outsider["credential"],
    }).status_code in (403, 404)
    response = client.get(path, headers={
        "authorization": "Bearer " + owner["credential"],
    })
    assert response.status_code == 200, response.text
    assert client.get("/api/bootstrap", headers={
        "authorization": "Bearer " + owner["credential"],
    }).json()["capabilities"]["work_status"] is True
    result = response.json()
    assert result["denominators"]["scoped_controls"] == 1
    assert result["controls"][0]["control_effectiveness"] == "NOT_ASSESSED"
    assert result["controls"][0]["reasons"][0]["code"] == "NO_ISSUED_REQUEST"
    assert engine.store.get(owner["id"], state["id"]) == state
