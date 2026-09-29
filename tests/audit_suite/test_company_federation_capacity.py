"""Bounded portfolios retain exact native routing and existing isolation guards."""

import json

import pytest

from enterprise.audit_suite import company_federation as federation
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError


def portfolio(tmp_path, count):
    tmp_path.chmod(0o700)
    components, stores = {}, {}
    for i in range(count):
        name = f"source-{i:02d}"
        root = tmp_path / name
        root.mkdir(mode=0o700)
        store = CompanyStore(root)
        store.register_system("NATIVE", "branch", "records", f"owner-{i}")
        store.append_version(
            "NATIVE",
            "branch",
            "records",
            "ROW",
            expected_version=0,
            command_id="create",
            event_at="2027-01-01T00:00:00Z",
            available_at="2027-01-01T00:00:00Z",
            content=json.dumps({"source": i}).encode(),
            provenance={"source_reference": name, "name": "row.json"},
        )
        store.grant("actor", "ENG", "NATIVE", "branch", "records")
        stores[name] = store
        components[name] = {
            "root": str(root),
            "company": "NATIVE",
            "branch": "branch",
            "namespace": name,
            "systems": ["records"],
        }
    config = {
        "schema": federation.SCHEMA,
        "components": components,
        "profiles": {
            "portfolio": {
                "company": "LOGICAL",
                "components": list(components),
                "qualification": federation.QUALIFICATION,
            }
        },
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    return path, config, stores


@pytest.mark.parametrize("count", [34, 64])
def test_larger_portfolio_routes_collects_and_rechecks_authority(tmp_path, count):
    path, _, stores = portfolio(tmp_path, count)
    facade = federation.FederatedCompanyStore(path, "portfolio")
    base = ("actor", "ENG", "LOGICAL", "portfolio")
    systems = facade.list_systems(*base)["systems"]
    assert {row["system"] for row in systems} == {f"{name}:records" for name in stores}
    receipts = []
    for i in (0, count - 1):
        name = f"source-{i:02d}"
        args = (*base, f"{name}:records", "ROW")
        row = facade.read_version(*args, version=1, as_of="2027-02-01T00:00:00Z")
        assert json.loads(row["content"]) == {"source": i}
        assert row["source_store_id"] == name
        assert (row["company"], row["branch"], row["system"]) == (
            "NATIVE",
            "branch",
            "records",
        )
        receipt = facade.collect(
            *args, version=1, as_of="2027-02-01T00:00:00Z", command_id="same-command"
        )
        assert (
            facade.collect(
                *args, version=1, as_of="2027-02-01T00:00:00Z", command_id="same-command"
            )
            == receipt
        )
        assert receipt["source"]["sha256"] == row["sha256"]
        receipts.append(receipt)
    assert receipts[0]["command_id"] != receipts[1]["command_id"]
    last = f"source-{count - 1:02d}"
    stores[last].grant("actor", "ENG", "NATIVE", "branch", "records", active=False)
    with pytest.raises(CompanyStoreError):
        facade.read_version(
            *base, f"{last}:records", "ROW", version=1, as_of="2027-02-01T00:00:00Z"
        )
    assert len(facade.list_systems(*base)["systems"]) == count - 1


@pytest.mark.parametrize("count", [0, 65])
def test_outside_capacity_rejected_before_source_access(tmp_path, monkeypatch, count):
    tmp_path.chmod(0o700)
    config = {
        "schema": federation.SCHEMA,
        "components": {},
        "profiles": {
            "portfolio": {
                "company": "LOGICAL",
                "components": [f"source-{i}" for i in range(count)],
                "qualification": federation.QUALIFICATION,
            }
        },
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(config))
    path.chmod(0o600)

    def unexpected_source(*args, **kwargs):
        pytest.fail("Invalid component count must fail before source construction")

    monkeypatch.setattr(federation._ExistingCompanyStore, "__init__", unexpected_source)
    with pytest.raises(CompanyStoreError, match="Explicit distinct qualified"):
        federation.FederatedCompanyStore(path, "portfolio")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["registry.json"]


@pytest.mark.parametrize("change", ["namespace", "physical_route", "selected_id"])
def test_larger_portfolio_preserves_duplicate_guards(tmp_path, change):
    path, config, _ = portfolio(tmp_path, 34)
    first, last = config["components"]["source-00"], config["components"]["source-33"]
    if change == "namespace":
        last["namespace"] = first["namespace"]
    elif change == "physical_route":
        last["root"] = first["root"]
    else:
        config["profiles"]["portfolio"]["components"][-1] = "source-00"
    path.write_text(json.dumps(config))
    with pytest.raises(CompanyStoreError):
        federation.FederatedCompanyStore(path, "portfolio")


def test_larger_profile_cannot_change_frozen_binding(tmp_path):
    path, config, _ = portfolio(tmp_path, 34)
    facade = federation.FederatedCompanyStore(path, "portfolio")
    bound = facade.binding
    config["profiles"]["portfolio"]["components"].pop()
    path.write_text(json.dumps(config))
    with pytest.raises(CompanyStoreError, match="changed"):
        facade.validate_binding(bound)
    successor = federation.FederatedCompanyStore(path, "portfolio")
    assert successor.binding["registry_sha256"] != bound["registry_sha256"]
    with pytest.raises(CompanyStoreError, match="Frozen"):
        successor.validate_binding(bound)
