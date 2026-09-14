import pytest

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_source_census import QUERY


@pytest.fixture
def workspace(tmp_path):
    company = tmp_path / "company"
    company.mkdir(mode=0o700)
    e = Engine(tmp_path / "audit", company_root=company)
    actor = e.store.provision("Auditor", ["learner"])["id"]
    state = {k: [] for k in COLLECTIONS}
    state.update(
        title="Neutral census",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at="2027-03-01T00:00:00Z",
        scope={
            "boundaries": ["corporate"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
        },
        configuration={"selections": []},
        company_source_binding={"company": "SH", "branch": "branch"},
    )
    state["requests"] = [
        {"id": "REQ", "status": "ISSUED", "boundary_id": "corporate", "artifact_ids": []}
    ]
    state = e.store.create(actor, state, "create")
    e.company_bindings[state["id"]] = {"company": "SH", "branch": "branch"}
    store = e.company_store
    store.register_system("SH", "branch", "records", "owner")
    store.grant(actor, state["id"], "SH", "branch", "records")
    for record, event in [("dated", "2027-01-02T00:00:00Z"), ("undated", None)]:
        store.append_version(
            "SH",
            "branch",
            "records",
            record,
            expected_version=0,
            command_id=record,
            event_at=event,
            available_at="2027-01-05T00:00:00Z",
            content=b'{"source":"original"}',
            origin="REPOSITORY_SYNTHETIC_DOCUMENT" if event is None else "AUTHORED_TRAINING_SOURCE",
            provenance={"source_reference": record, "name": "original.json"},
        )
    return e, actor, state


def envelope(state):
    return {
        "command_id": "census",
        "expected_revision": state["revision"],
        "kind": "company.census.collect",
        "payload": {"request_id": "REQ", "system_id": "records", "query": QUERY},
    }


def test_actual_engine_retains_originals_explicit_provisional_import_and_replay(workspace):
    e, actor, state = workspace
    before = e.company_store.path.read_bytes()
    command = envelope(state)
    result = e.command(actor, state["id"], command)
    receipt = result["requests"][0]["company_census_collections"][0]
    assert receipt["strata"] == {"IN_EVENT_WINDOW": 1, "UNDATED": 1}
    assert receipt["source_versions"] == receipt["distinct_source_records"] == 2
    assert receipt["registration"] == "AWAITING_EXPLICIT_IMPORT"
    assert result["populations"] == [] and result["tasks"] == [] and result["workpapers"] == []
    assert len(result["artifacts"]) == 4
    for native in receipt["native_artifacts"]:
        artifact = next(x for x in result["artifacts"] if x["id"] == native["artifact_id"])
        assert e.artifacts.read(artifact) == b'{"source":"original"}'
        assert artifact["sha256"] == native["source"]["sha256"]
    assert e.command(actor, state["id"], command) == result
    assert len(e.store.history(actor, state["id"])) == 2
    imported = e.command(
        actor,
        state["id"],
        {
            **receipt["next_command"],
            "command_id": "import",
            "expected_revision": result["revision"],
        },
    )
    population = imported["populations"][0]
    assert population["status"] == "PROVISIONAL"
    assert {r["date_stratum"] for r in population["rows"]} == {"IN_EVENT_WINDOW", "UNDATED"}
    assert len(imported["tasks"]) == 0
    # Only native collection journals change; no company versions are generated.
    with e.company_store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 2
    assert before != e.company_store.path.read_bytes()


@pytest.mark.parametrize("mutation", ["scope", "request", "clock", "grant", "unknown_query"])
def test_invalid_collection_keeps_audit_unchanged(workspace, mutation):
    e, actor, state = workspace
    command = envelope(state)
    if mutation == "scope":
        command["payload"]["query"] = {
            **QUERY,
            "event_window": {"start": "2026-01-01T00:00:00Z", "end": "2027-02-01T00:00:00Z"},
        }
    elif mutation == "request":
        command["payload"]["request_id"] = "missing"
    elif mutation == "clock":
        command["payload"]["as_of"] = "2030"
    elif mutation == "grant":
        e.company_store.grant(actor, state["id"], "SH", "branch", "records", active=False)
    else:
        command["payload"]["query"] = {**QUERY, "arbitrary_sql": "no"}
    with pytest.raises(DomainError):
        e.command(actor, state["id"], command)
    assert e.store.get(actor, state["id"])["revision"] == 0
    assert e.store.get(actor, state["id"])["artifacts"] == []


def test_portfolio_engine_collect_preserves_native_and_alias_identities(tmp_path):
    from tests.audit_suite.test_company_federation import portfolio

    facade, stores, _, registry = portfolio(tmp_path)
    e = Engine(tmp_path / "audit", company_registry=registry, company_profile="portfolio")
    actor = e.store.provision("Auditor", ["learner"])["id"]
    state = {k: [] for k in COLLECTIONS}
    state.update(
        title="Portfolio census",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at="2027-03-01T00:00:00Z",
        scope={
            "boundaries": ["corporate"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
        },
        configuration={"selections": []},
        company_source_binding=facade.binding,
    )
    state["requests"] = [
        {"id": "REQ", "status": "ISSUED", "boundary_id": "corporate", "artifact_ids": []}
    ]
    state = e.store.create(actor, state, "create")
    e.company_bindings[state["id"]] = facade.binding
    stores["one"].grant(actor, state["id"], "NATIVE", "branch", "records")
    command = envelope(state)
    command["payload"]["system_id"] = "ONE:records"
    result = e.command(actor, state["id"], command)
    receipt = result["requests"][0]["company_census_collections"][0]
    assert receipt["source_versions"] == 1
    native = receipt["native_artifacts"][0]["source"]
    assert (native["company"], native["branch"], native["system"]) == (
        "NATIVE",
        "branch",
        "records",
    )
    assert native["source_store_id"] == "one" and native["source_system_alias"] == "ONE:records"
    assert native["registry_sha256"] == facade.registry_sha256
    assert receipt["portfolio_binding"] == facade.binding
    assert not result["populations"]
    with stores["two"]._db() as db:
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0


def test_revocation_during_retention_does_not_commit_population_or_artifacts(
    workspace, monkeypatch
):
    e, actor, state = workspace
    original = e.artifacts.retain

    def retain(*args, **kwargs):
        artifact = original(*args, **kwargs)
        e.company_store.grant(actor, state["id"], "SH", "branch", "records", active=False)
        return artifact

    monkeypatch.setattr(e.artifacts, "retain", retain)
    with pytest.raises(DomainError):
        e.command(actor, state["id"], envelope(state))
    unchanged = e.store.get(actor, state["id"])
    assert (
        unchanged["revision"] == 0 and not unchanged["artifacts"] and not unchanged["populations"]
    )
    assert len(e.store.history(actor, state["id"])) == 1


def test_operator_cli_exports_new_private_snapshot_without_audit_mutation(workspace, tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    e, actor, state = workspace
    # This is an explicit operator binding in the test's initial source investigation.
    before = e.store.get(actor, state["id"])
    config = {
        "audit_root": str(e.store.root),
        "actor_id": actor,
        "engagement_id": state["id"],
        "source": {"root": str(e.company_store.path.parent)},
        "system_id": "records",
        "query": QUERY,
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    output = tmp_path / "export"
    tool = Path(__file__).resolve().parents[2] / "tools/audit_suite/source_census.py"
    result = subprocess.run(
        [sys.executable, str(tool), "--config", str(path), "--output", str(output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["source_versions"] == 2
    assert e.store.get(actor, state["id"]) == before
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in output.iterdir())
    repeated = subprocess.run(
        [sys.executable, str(tool), "--config", str(path), "--output", str(output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert repeated.returncode != 0
