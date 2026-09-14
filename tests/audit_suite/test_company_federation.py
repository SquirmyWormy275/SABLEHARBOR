import json
from pathlib import Path

import pytest

from enterprise.audit_suite.company_collection import binding
from enterprise.audit_suite.company_federation import QUALIFICATION, SCHEMA, FederatedCompanyStore
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.store import DomainError


def portfolio(tmp_path):
    tmp_path.chmod(0o700)
    stores, components = {}, {}
    for name in ("one", "two"):
        root = tmp_path / name
        root.mkdir(mode=0o700)
        store = CompanyStore(root)
        store.register_system("NATIVE", "branch", "records", "owner")
        store.append_version(
            "NATIVE",
            "branch",
            "records",
            "ROW",
            expected_version=0,
            command_id="original",
            event_at="2027-01-01T00:00:00Z",
            available_at="2027-01-01T00:00:00Z",
            content=b'{"original":"same"}',
            provenance={"source_reference": "original", "name": "records.json"},
        )
        store.append_version(
            "NATIVE",
            "branch",
            "records",
            "ROW",
            expected_version=1,
            command_id="future",
            event_at="2027-04-01T00:00:00Z",
            available_at="2027-04-01T00:00:00Z",
            content=b'{"later":"version"}',
            provenance={"source_reference": "future", "name": "records.json"},
        )
        store.grant("actor", "ENG", "NATIVE", "branch", "records")
        stores[name] = store
        components[name] = {
            "root": str(root),
            "company": "NATIVE",
            "branch": "branch",
            "namespace": name.upper(),
            "systems": ["records"],
        }
    config = {
        "schema": SCHEMA,
        "components": components,
        "profiles": {
            "portfolio": {
                "company": "LOGICAL",
                "components": ["one", "two"],
                "qualification": QUALIFICATION,
            }
        },
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    return FederatedCompanyStore(path, "portfolio"), stores, config, path


def args(alias="ONE:records"):
    return "actor", "ENG", "LOGICAL", "portfolio", alias, "ROW"


def test_native_identity_bytes_receipt_and_component_scoped_replay(tmp_path):
    facade, stores, _, _ = portfolio(tmp_path)
    assert {s["system"] for s in facade.list_systems(*args()[:4])["systems"]} == {
        "ONE:records",
        "TWO:records",
    }
    receipts = []
    for source_id in ("one", "two"):
        alias = source_id.upper() + ":records"
        row = facade.read_version(*args(alias), version=1, as_of="2027-02-01T00:00:00Z")
        assert row["content"] == b'{"original":"same"}'
        assert (row["company"], row["branch"], row["system"]) == ("NATIVE", "branch", "records")
        assert row["source_store_id"] == source_id and row["source_system_alias"] == alias
        receipt = facade.collect(
            *args(alias), version=1, as_of="2027-02-01T00:00:00Z", command_id="same"
        )
        assert (
            facade.collect(*args(alias), version=1, as_of="2027-02-01T00:00:00Z", command_id="same")
            == receipt
        )
        assert receipt["idempotency_scope"] == "SOURCE_COMPONENT_AND_PROFILE"
        with stores[source_id]._db() as db:
            original = json.loads(db.execute("SELECT receipt FROM collections").fetchone()[0])
        assert receipt["upstream_receipt"] == original
        assert receipt["source"]["sha256"] == original["source"]["sha256"]
        receipts.append(receipt)
    assert receipts[0]["command_id"] != receipts[1]["command_id"]
    assert receipts[0]["source"]["source_store_id"] != receipts[1]["source"]["source_store_id"]


def test_future_revoked_cross_namespace_and_other_engagement_fail(tmp_path):
    facade, stores, _, _ = portfolio(tmp_path)
    assert facade.list_records(*args()[:5], as_of="2026-01-01T00:00:00Z")["records"] == []
    with pytest.raises(CompanyStoreError):
        facade.read_version(*args(), version=2, as_of="2027-02-01T00:00:00Z")
    for alias in ("records", "ONE:unknown", "UNKNOWN:records"):
        with pytest.raises(CompanyStoreError):
            facade.read_version(*args(alias), version=1, as_of="2027-02-01T00:00:00Z")
    with pytest.raises(CompanyStoreError):
        facade.read_version("actor", "OTHER", *args()[2:], version=1, as_of="2027-02-01T00:00:00Z")
    stores["one"].grant("actor", "ENG", "NATIVE", "branch", "records", active=False)
    with pytest.raises(CompanyStoreError):
        facade.read_version(*args(), version=1, as_of="2027-02-01T00:00:00Z")
    assert [s["system"] for s in facade.list_systems(*args()[:4])["systems"]] == ["TWO:records"]


def test_changed_registry_cannot_rebind_or_return_midread(tmp_path, monkeypatch):
    facade, _, config, path = portfolio(tmp_path)
    original = facade._stores["one"].read_version

    def changed(*a, **kw):
        result = original(*a, **kw)
        config["components"]["two"]["namespace"] = "CHANGED"
        path.write_text(json.dumps(config))
        return result

    monkeypatch.setattr(facade._stores["one"], "read_version", changed)
    with pytest.raises(CompanyStoreError, match="changed"):
        facade.read_version(*args(), version=1, as_of="2027-02-01T00:00:00Z")
    from types import SimpleNamespace

    engine = SimpleNamespace(company_store=facade, company_bindings={"ENG": facade.binding})
    with pytest.raises(DomainError):
        binding(engine, {"id": "ENG", "company_source_binding": facade.binding})


@pytest.mark.parametrize(
    "change", ["namespace", "missing_db", "registry_mode", "alias", "duplicate_route"]
)
def test_invalid_operator_registry_does_not_create_sources(tmp_path, change):
    _, _, config, path = portfolio(tmp_path)
    if change == "namespace":
        config["components"]["one"]["namespace"] = "BAD:NAME"
    if change == "missing_db":
        empty = tmp_path / "empty"
        empty.mkdir(mode=0o700)
        config["components"]["one"]["root"] = str(empty)
    if change == "registry_mode":
        path.chmod(0o644)
    if change == "alias":
        alias = tmp_path / "alias"
        alias.symlink_to(tmp_path / "one", target_is_directory=True)
        config["components"]["one"]["root"] = str(alias)
    if change == "duplicate_route":
        config["components"]["two"]["root"] = config["components"]["one"]["root"]
    path.write_text(json.dumps(config))
    with pytest.raises(CompanyStoreError):
        FederatedCompanyStore(path, "portfolio")
    if change == "missing_db":
        assert not (empty / "company.sqlite3").exists()


def test_no_faked_crossstore_database_or_population(tmp_path):
    facade, _, _, _ = portfolio(tmp_path)
    assert not facade.capabilities["company_populations"]
    with pytest.raises(DomainError) as error:
        facade._db()
    assert error.value.code == "FEDERATION_OPERATION_UNSUPPORTED"
    from enterprise.audit_suite.company_population import export_population

    with pytest.raises(DomainError) as error:
        export_population(
            facade,
            principal_id="actor",
            engagement_id="ENG",
            company_id="LOGICAL",
            branch_id="portfolio",
            query={},
            repository=Path.cwd(),
        )
    assert error.value.code == "FEDERATION_OPERATION_UNSUPPORTED"


def test_actual_engine_retains_identical_native_ids_from_distinct_stores(tmp_path):
    from enterprise.audit_suite.company_impact import report
    from enterprise.audit_suite.engine import Engine

    facade, stores, _, path = portfolio(tmp_path)
    engine = Engine(tmp_path / "audit", company_registry=path, company_profile="portfolio")
    actor = engine.store.provision("Portfolio investigator", ["instructor", "learner"])["id"]
    state = engine.create(
        actor,
        {
            "command_id": "create",
            "title": "Original sources",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {"selections": []},
            "scope": {
                "programs": ["SOC2", "HIPAA"],
                "report_type": "Type 2",
                "period_start": "2027-01-01",
                "period_end": "2027-01-31",
                "fieldwork_start": "2027-02-01",
                "timezone": "UTC",
                "boundaries": ["corporate"],
                "control_ids": ["SH-IAM-003"],
            },
        },
    )
    engine.company_bindings[state["id"]] = facade.binding
    for store in stores.values():
        store.grant(actor, state["id"], "NATIVE", "branch", "records")
    serial = 0

    def command(kind, payload):
        nonlocal state, serial
        serial += 1
        state = engine.command(
            actor,
            state["id"],
            {
                "command_id": str(serial),
                "expected_revision": state["revision"],
                "kind": kind,
                "payload": payload,
            },
        )

    command("company.activate", {})
    command("kickoff.start", {})
    control = state["controls"][0]
    command(
        "pbc.create",
        {
            "title": "Original records",
            "purpose": "Inspect original bytes",
            "control_id": control["id"],
            "boundary_id": "corporate",
            "person_id": control["owner_ids"][0],
        },
    )
    request = state["requests"][-1]["id"]
    command("pbc.issue", {"request_id": request})
    for alias in ("ONE:records", "TWO:records"):
        command(
            "company.collect",
            {"system_id": alias, "record_id": "ROW", "version": 1, "request_id": request},
        )
    assert len(state["artifacts"]) == 2
    assert len(state["requests"][-1]["company_collections"]) == 2
    assert {a["source"]["receipt"]["source"]["source_store_id"] for a in state["artifacts"]} == {
        "one",
        "two",
    }
    assert len({a["sha256"] for a in state["artifacts"]}) == 1
    assert all(engine.artifacts.read(a) == b'{"original":"same"}' for a in state["artifacts"])
    assert not (engine.store.root / "worlds" / state["id"]).exists()
    impact = report(engine, actor, state["id"])
    assert impact["changes"] == [] and impact["compared_artifacts"] == 2
    assert impact["snapshot_isolation"] == "PER_SOURCE_OPERATION_NOT_GLOBAL"
    from enterprise.audit_suite.audit_readiness import summarize

    source_refs = summarize(state)["controls"][0]["sources"]
    assert {s["source_identity"]["source_store_id"] for s in source_refs} == {"one", "two"}
    assert all(
        s["source_identity"]["registry_sha256"] == facade.registry_sha256 for s in source_refs
    )
    from enterprise.audit_suite.explanation_binding import bind_snapshot

    with pytest.raises(DomainError) as error:
        bind_snapshot(
            engine,
            instructor_id=actor,
            audited_actor_id=actor,
            engagement_id=state["id"],
            source_operator_id=actor,
            source_as_of="2027-02-01T00:00:00Z",
            source_refs=[],
            authored={},
            output=tmp_path / "unsupported-binding",
        )
    assert error.value.code == "FEDERATION_OPERATION_UNSUPPORTED"
    assert not (tmp_path / "unsupported-binding").exists()
    with pytest.raises(DomainError) as error:
        command(
            "company.population.collect",
            {
                "request_id": request,
                "query": {
                    "table": "contract_versions",
                    "source_scenario": "base",
                    "month_start": 1,
                    "month_end": 1,
                    "units": ["corporate"],
                },
            },
        )
    assert error.value.code == "FEDERATION_OPERATION_UNSUPPORTED"
