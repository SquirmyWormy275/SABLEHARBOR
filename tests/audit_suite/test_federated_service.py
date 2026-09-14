import json

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.service import create_app, load_company_bindings
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_federation import portfolio


def test_registry_service_capabilities_authority_and_frozen_configuration(tmp_path):
    facade, stores, config, path = portfolio(tmp_path)
    app = create_app(
        tmp_path / "audit",
        company_registry=path,
        company_profile="portfolio",
        allowed_hosts=["testserver"],
    )
    engine = app.state.engine
    actor = engine.store.provision("Portfolio learner", ["learner"])
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Portfolio",
        phase="ACTIVE",
        mode="CLEAN",
        discipline="IT",
        scope={"boundaries": ["corporate"]},
        configuration={},
        simulated_at="2027-02-01T00:00:00Z",
        company_source_binding=facade.binding,
        evidence_acquisition="COMPANY_SOURCE_COLLECTION",
    )
    state = engine.store.create(actor["id"], state, "create")
    engine.company_bindings[state["id"]] = facade.binding
    for store in stores.values():
        store.grant(actor["id"], state["id"], "NATIVE", "branch", "records")
    client = TestClient(app, base_url="https://testserver")
    headers = {"authorization": "Bearer " + actor["credential"]}
    caps = client.get("/api/bootstrap", headers=headers).json()["capabilities"]
    assert caps["company_sources"] is True
    assert caps["personal_drafts"] is True
    assert caps["workpaper_procedure_links"] is True
    assert caps["company_populations"] is False
    assert caps["company_source_impact"] is True
    route = f"/api/engagements/{state['id']}/company"
    assert client.get(route + "/systems").status_code == 401
    response = client.get(route + "/systems", headers=headers)
    assert response.status_code == 200, response.text
    assert {s["system"] for s in response.json()["systems"]} == {"ONE:records", "TWO:records"}
    assert str(tmp_path) not in response.text
    impact = client.get(route + "/impact", headers=headers)
    assert impact.status_code == 200, impact.text
    assert impact.json()["engagement_revision"] == state["revision"]
    assert impact.json()["compared_artifacts"] == 0
    assert impact.json()["changes"] == []
    assert impact.json()["unavailable_comparisons"] == 0
    assert str(tmp_path) not in impact.text
    config["components"]["two"]["namespace"] = "CHANGED"
    path.write_text(json.dumps(config))
    assert client.get(route + "/systems", headers=headers).status_code == 409
    assert client.get(route + "/impact", headers=headers).status_code == 409
    assert engine.store.get(actor["id"], state["id"]) == state


def test_registry_binding_loader_requires_exact_digest_and_connection_pair(tmp_path):
    tmp_path.chmod(0o700)
    path = tmp_path / "bindings.json"
    bound = {"company": "CO", "branch": "profile", "registry_sha256": "a" * 64}
    path.write_text(json.dumps({"ENG": bound}))
    path.chmod(0o600)
    assert load_company_bindings(path) == {"ENG": bound}
    bound["registry_sha256"] = "not-a-digest"
    path.write_text(json.dumps({"ENG": bound}))
    with pytest.raises(DomainError):
        load_company_bindings(path)
    with pytest.raises(DomainError, match="together"):
        Engine(tmp_path / "absent", company_profile="profile")
    assert not (tmp_path / "absent").exists()
    with pytest.raises(DomainError, match="Choose one"):
        Engine(
            tmp_path / "absent",
            company_root=tmp_path,
            company_registry=path,
            company_profile="profile",
        )
    assert not (tmp_path / "absent").exists()
