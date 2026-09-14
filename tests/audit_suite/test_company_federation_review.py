"""Adversarial read-through review: no original-store initialization or stale grant disclosure."""

import json

import pytest

from enterprise.audit_suite.company_federation import (
    QUALIFICATION,
    FederatedCompanyStore,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError


def setup(tmp_path, *, system="records"):
    tmp_path.chmod(0o700)
    components = {}
    stores = {}
    for name in ("one", "two"):
        root = tmp_path / name
        root.mkdir(mode=0o700)
        store = CompanyStore(root)
        store.register_system("SH", "branch", system, "OWNER-" + name)
        store.append_version(
            "SH",
            "branch",
            system,
            "R1",
            expected_version=0,
            command_id="create",
            event_at="2027-01-01T00:00:00Z",
            available_at="2027-01-01T00:00:00Z",
            content=b"original",
            provenance={"source_reference": "source", "name": "original.txt"},
        )
        store.grant("actor", "eng", "SH", "branch", system)
        stores[name] = store
        components[name] = {
            "root": str(root),
            "company": "SH",
            "branch": "branch",
            "namespace": name,
            "systems": [system],
        }
    config = {
        "schema": "COMPANY_SOURCE_PORTFOLIO_V1",
        "components": components,
        "profiles": {
            "selected": {
                "company": "LOGICAL",
                "components": ["one", "two"],
                "qualification": QUALIFICATION,
            }
        },
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    return path, stores


def test_systems_rechecks_first_component_revocation_during_aggregation(tmp_path, monkeypatch):
    path, stores = setup(tmp_path)
    facade = FederatedCompanyStore(path, "selected")
    second = facade._stores["two"]
    original = second.list_systems

    def revoke_then_list(*args, **kwargs):
        stores["one"].grant("actor", "eng", "SH", "branch", "records", active=False)
        return original(*args, **kwargs)

    monkeypatch.setattr(second, "list_systems", revoke_then_list)
    result = facade.list_systems("actor", "eng", "LOGICAL", "selected")
    assert [r["system"] for r in result["systems"]] == ["two:records"]


def test_existing_empty_source_database_not_initialized_on_failed_registry(tmp_path):
    path, stores = setup(tmp_path)
    target = tmp_path / "one" / "company.sqlite3"
    target.write_bytes(b"")
    assert target.read_bytes() == b""
    with pytest.raises(CompanyStoreError):
        FederatedCompanyStore(path, "selected")
    assert target.read_bytes() == b""


def test_full_length_native_system_identity_remains_addressable(tmp_path):
    native = "source:" + ("s" * 120)
    path, stores = setup(tmp_path, system=native)
    facade = FederatedCompanyStore(path, "selected")
    alias = "one:" + native
    row = facade.read_version(
        "actor", "eng", "LOGICAL", "selected", alias, "R1", version=1, as_of="2027-02-01T00:00:00Z"
    )
    assert row["system"] == native and row["source_system_alias"] == alias
    assert row["content"] == b"original"


def test_registry_change_after_original_read_fails_closed(tmp_path, monkeypatch):
    path, stores = setup(tmp_path)
    facade = FederatedCompanyStore(path, "selected")
    store = facade._stores["one"]
    original = store.read_version

    def change_then_return(*args, **kwargs):
        result = original(*args, **kwargs)
        config = json.loads(path.read_text())
        config["components"]["one"]["namespace"] = "changed"
        path.write_text(json.dumps(config))
        return result

    monkeypatch.setattr(store, "read_version", change_then_return)
    with pytest.raises(CompanyStoreError, match="changed"):
        facade.read_version(
            "actor",
            "eng",
            "LOGICAL",
            "selected",
            "one:records",
            "R1",
            version=1,
            as_of="2027-02-01T00:00:00Z",
        )


def test_long_alias_through_authenticated_discovery_and_collection_api(tmp_path):
    from urllib.parse import quote

    from fastapi.testclient import TestClient

    from enterprise.audit_suite.engine import COLLECTIONS
    from enterprise.audit_suite.service import create_app

    native = "source:" + "s" * 120
    path, stores = setup(tmp_path, system=native)
    app = create_app(
        tmp_path / "audit",
        company_registry=path,
        company_profile="selected",
        allowed_hosts=["testserver"],
    )
    engine = app.state.engine
    actor = engine.store.provision("Federated learner", ["learner"])
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Exact source lookup",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at="2027-02-01T00:00:00Z",
        scope={
            "boundaries": ["corporate"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
        },
        configuration={"selections": []},
    )
    state["requests"] = [{"id": "R1", "status": "ISSUED", "artifact_ids": []}]
    state = engine.store.create(actor["id"], state, "create")
    engine.company_bindings[state["id"]] = engine.company_store.binding
    stores["one"].grant(actor["id"], state["id"], "SH", "branch", native)
    alias = "one:" + native
    client = TestClient(app, base_url="https://testserver")
    client.post("/api/session", json={"credential": actor["credential"]})
    csrf = client.get("/api/bootstrap").json()["csrf_token"]
    url = f"/api/engagements/{state['id']}/company/systems/{quote(alias, safe='')}/records"
    response = client.get(url)
    assert response.status_code == 200, response.text
    assert response.json()["records"][0]["source_system_alias"] == alias
    command = {
        "command_id": "collect",
        "expected_revision": state["revision"],
        "kind": "company.collect",
        "payload": {"system_id": alias, "record_id": "R1", "version": 1, "request_id": "R1"},
    }
    response = client.post(
        f"/api/engagements/{state['id']}/commands", json=command, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 200, response.text
    artifact = response.json()["artifacts"][0]
    assert engine.artifacts.read(artifact) == b"original"
    assert artifact["source"]["receipt"]["upstream_receipt"]["source"]["system"] == native
