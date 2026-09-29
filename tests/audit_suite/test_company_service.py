import json

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.engine import COLLECTIONS
from enterprise.audit_suite.service import create_app, load_company_bindings
from enterprise.audit_suite.store import DomainError


def test_company_http_auth_clock_csrf_and_retained_original(tmp_path):
    company = tmp_path / "company"
    company.mkdir(mode=0o700)
    app = create_app(tmp_path / "audit", company_root=company, allowed_hosts=["testserver"])
    e = app.state.engine
    user = e.store.provision("Auditor", ["learner"])
    other = e.store.provision("Other", ["learner"])
    state = {k: [] for k in COLLECTIONS}
    state.update(
        title="Company",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at="2027-06-01T00:00:00Z",
        scope={
            "boundaries": ["corporate"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
        },
        configuration={"selections": []},
    )
    state["requests"] = [{"id": "R1", "status": "ISSUED", "artifact_ids": []}]
    state = e.store.create(user["id"], state, "create")
    e.company_bindings[state["id"]] = {"company": "SH", "branch": "base"}
    s = e.company_store
    s.register_system("SH", "base", "IAM", "owner")
    for record, available in [("past", "2027-01-01T00:00:00Z"), ("future", "2028-01-01T00:00:00Z")]:
        s.append_version(
            "SH",
            "base",
            "IAM",
            record,
            expected_version=0,
            command_id=record,
            event_at=available,
            available_at=available,
            content=b"original record\n",
            provenance={"source_reference": "original", "name": "original.txt"},
        )
    s.grant(user["id"], state["id"], "SH", "base", "IAM")
    client = TestClient(app, base_url="https://testserver")
    url = f"/api/engagements/{state['id']}/company/systems/IAM/records"
    assert client.get(url).status_code == 401
    systems_url = f"/api/engagements/{state['id']}/company/systems"
    assert client.get(systems_url).status_code == 401
    login = client.post("/api/session", json={"credential": user["credential"]})
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}
    assert [r["record"] for r in client.get(url).json()["records"]] == ["past"]
    assert client.get(systems_url).json() == {"systems": [{"system": "IAM", "owner": "owner"}]}
    assert client.get(systems_url + "?branch=other").status_code == 422
    assert (
        client.get(
            systems_url, headers={"Authorization": "Bearer " + other["credential"]}
        ).status_code
        == 403
    )

    assert client.get(url + "?as_of=2030").status_code == 422
    assert (
        client.get(url, headers={"Authorization": "Bearer " + other["credential"]}).status_code
        == 403
    )
    command = {
        "command_id": "collect",
        "expected_revision": state["revision"],
        "kind": "company.collect",
        "payload": {"system_id": "IAM", "record_id": "past", "version": 1, "request_id": "R1"},
    }
    endpoint = f"/api/engagements/{state['id']}/commands"
    assert client.post(endpoint, json=command).status_code == 403
    future_command = {
        **command,
        "command_id": "future-collect",
        "payload": {**command["payload"], "record_id": "future"},
    }
    assert client.post(endpoint, json=future_command, headers=headers).status_code == 403
    result = client.post(endpoint, json=command, headers=headers)
    assert result.status_code == 200, result.text
    artifact = result.json()["artifacts"][0]
    assert e.artifacts.read(artifact) == b"original record\n"
    s.grant(user["id"], state["id"], "SH", "base", "IAM", active=False)
    assert client.get(url).status_code == 403
    assert client.get(systems_url).json() == {"systems": []}
    assert "company.sqlite3" not in client.get("/api/openapi.json").text
    e.company_bindings.clear()
    assert client.get(url).status_code == 404


def test_private_binding_config_exact_schema(tmp_path):
    tmp_path.chmod(0o700)
    path = tmp_path / "bindings.json"
    path.write_text(json.dumps({"ENG-1": {"company": "SH", "branch": "base"}}))
    path.chmod(0o600)
    assert load_company_bindings(path)["ENG-1"]["branch"] == "base"
    for raw in [
        '{"ENG-1":{"company":"SH","branch":"base","as_of":"2030"}}',
        '{"ENG-1":{"company":"SH","company":"OTHER","branch":"base"}}',
        '{"ENG-1":{"company":"../private","branch":"base"}}',
    ]:
        path.write_text(raw)
        with pytest.raises(DomainError):
            load_company_bindings(path)
    path.chmod(0o644)
    with pytest.raises(DomainError):
        load_company_bindings(path)
    alias = tmp_path / "alias"
    alias.symlink_to(path)
    with pytest.raises(DomainError):
        load_company_bindings(alias)
