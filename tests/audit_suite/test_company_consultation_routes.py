"""HTTP contract for exact prior-statement pins; provider is entirely mocked."""

import copy

import pytest
import test_company_consultation as consultation_cases
from fastapi.testclient import TestClient

from enterprise.audit_suite.service import create_app


@pytest.fixture
def route_context(monkeypatch, tmp_path):
    engine, _, state, pins, command = consultation_cases.exchange.__wrapped__(tmp_path)
    principal = engine.store.provision("Route learner", ["learner"])
    engine.store.grant(state["id"], principal["id"], "learn")
    engine.company_store.grant(principal["id"], state["id"], "SH", "base", "different")
    app = create_app(engine.store.root, engine_factory=lambda: engine, allowed_hosts=["testserver"])
    client = TestClient(app, base_url="https://testserver")
    headers = {"authorization": "Bearer " + principal["credential"]}
    return engine, principal, state, command, client, headers


def test_http_exact_exchange_projection_and_idempotent_reply(route_context, monkeypatch):
    engine, principal, state, command, client, headers = route_context
    calls = consultation_cases.provider(monkeypatch)
    monkeypatch.setattr(
        engine,
        "provider_status",
        lambda: {
            "inference": {"configured": True, "ready": True, "local": True},
            "voice": {"configured": False, "ready": False, "local": True},
        },
    )
    path = f"/api/engagements/{state['id']}"
    assert client.get("/api/bootstrap", headers=headers).json()["capabilities"][
        "company_consultations"
    ]
    before = client.get(path, headers=headers).json()
    assert (
        before["company_consultation_inputs"]["questions"][0]["ref"]
        == command["payload"]["consultation"]["question_ref"]
    )
    response = client.post(path + "/commands", headers=headers, json=command)
    assert response.status_code == 200, response.text
    after = response.json()
    assert after["meetings"][0]["messages"] == before["meetings"][0]["messages"]
    assert after["meetings"][1]["messages"][-1]["consultation"]["relation"] == "CLARIFIES"
    count = len(calls)
    replay = client.post(path + "/commands", headers=headers, json=command)
    assert replay.status_code == 200
    assert replay.json() == after
    assert len(calls) == count
    assert client.get(path).status_code == 401


def test_http_rejects_forged_origin_and_revoked_sources_before_provider(route_context, monkeypatch):
    engine, principal, state, command, client, headers = route_context
    calls = consultation_cases.provider(monkeypatch)
    path = f"/api/engagements/{state['id']}/commands"
    forged = copy.deepcopy(command)
    forged["payload"]["consultation"]["question_ref"]["sha256"] = "0" * 64
    assert client.post(path, headers=headers, json=forged).status_code == 409
    engine.company_store.grant(
        principal["id"], state["id"], "SH", "base", "different", active=False
    )
    response = client.post(path, headers=headers, json=command)
    assert response.status_code == 403, response.text
    assert not calls
    assert engine.store.get(principal["id"], state["id"])["revision"] == state["revision"]
