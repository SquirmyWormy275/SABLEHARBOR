"""Source runtime collection preserves the sealed producer and native chronology."""

import json
import sqlite3

import pytest

from enterprise.audit_suite.company_collection import discover
from enterprise.audit_suite.company_federation import QUALIFICATION
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.operating_source_bridge import sha
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_activity_plan_sources import source as producer_source


def _rows(root, table):
    with sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        order = {
            "versions": "company,branch,system,record,version",
            "systems": "company,branch,system",
        }.get(table, "rowid")
        return [dict(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY {order}")]


def _registry(path, roots):
    value = {
        "schema": "COMPANY_SOURCE_PORTFOLIO_V1",
        "components": {
            key: {
                "root": str(root),
                "company": "SH",
                "branch": branch,
                "namespace": key.upper(),
                "systems": ["application"],
            }
            for key, (root, branch) in roots.items()
        },
        "profiles": {
            key: {"company": "SH", "components": [key], "qualification": QUALIFICATION}
            for key in roots
        },
    }
    path.write_text(json.dumps(value))
    path.chmod(0o600)


def _investigate(audit_root, registry, profile, runtime, branch):
    engine = Engine(audit_root, company_registry=registry, company_profile=profile)
    actor = engine.store.provision("Isolated investigator", ["learner", "instructor"])["id"]
    state = engine.create(
        actor,
        {
            "command_id": "create",
            "title": "Original source chronology",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {"selections": []},
            "scope": {
                "programs": ["SOC2", "HIPAA"],
                "report_type": "Type 2",
                "period_start": "2027-04-01",
                "period_end": "2027-04-30",
                "fieldwork_start": "2027-04-14",
                "timezone": "America/Los_Angeles",
                "boundaries": ["corporate"],
                "control_ids": ["SH-IAM-003"],
            },
        },
    )
    engine.company_bindings[state["id"]] = engine.company_store.binding
    source = CompanyStore(runtime)
    assert not _rows(runtime, "grants") and not _rows(runtime, "collections")
    serial = 0

    def command(kind, payload):
        nonlocal state, serial
        serial += 1
        state = engine.command(
            actor,
            state["id"],
            {
                "command_id": f"step-{serial}",
                "expected_revision": state["revision"],
                "kind": kind,
                "payload": payload,
            },
        )
        return state

    alias = profile.upper() + ":application"
    with pytest.raises(DomainError):
        discover(engine, actor, state["id"], alias)
    source.grant(actor, state["id"], "SH", branch, "application")
    owner = next(
        row["owner"]
        for row in _rows(runtime, "systems")
        if row["branch"] == branch and row["system"] == "application"
    )
    assert owner in state["controls"][0]["owner_ids"]
    command("company.activate", {})
    command("kickoff.start", {})
    command(
        "pbc.create",
        {
            "title": "Original access records",
            "purpose": "Inspect chronology",
            "control_id": "SH-IAM-003",
            "boundary_id": "corporate",
            "person_id": owner,
        },
    )
    request = state["requests"][-1]["id"]
    command("pbc.issue", {"request_id": request})
    payload = {
        "system_id": alias,
        "record_id": "MOVE-01-application",
        "version": 2,
        "request_id": request,
    }
    with pytest.raises(DomainError):
        command("company.collect", payload)
    assert not state["artifacts"] and not _rows(runtime, "collections")
    command("clock.advance", {"mode": "TARGET_DATE", "target": "2027-04-16"})
    for version in (1, 2):
        command("company.collect", payload | {"version": version})
    assert len(state["artifacts"]) == 2
    originals = {
        (r["record"], r["version"]): r for r in _rows(runtime, "versions") if r["branch"] == branch
    }
    for artifact in state["artifacts"]:
        receipt = artifact["source"]["receipt"]
        native = receipt["upstream_receipt"]["source"]
        original = originals[native["record"], native["version"]]
        assert native["company"] == "SH" and native["branch"] == branch
        assert native["system"] == "application"
        assert receipt["source"]["source_system_alias"] == alias
        assert engine.artifacts.read(artifact) == original["content"]
        assert artifact["sha256"] == native["sha256"] == sha(original["content"])
    source.grant(actor, state["id"], "SH", branch, "application", active=False)
    with pytest.raises(DomainError):
        command("company.collect", payload)
    assert len(_rows(runtime, "collections")) == 2
    assert len(_rows(runtime, "access_events")) == 2
    assert not (engine.store.root / "worlds" / state["id"]).exists()
    assert not state["workpapers"] and not state["findings"] and not state["populations"]
    retained = engine.store.history(actor, state["id"])[-1]["state"]
    assert retained["revision"] == state["revision"]
    assert retained["artifacts"] == state["artifacts"]
    return state, actor


def test_activated_runtime_collects_native_history_without_mutating_capsule(tmp_path):
    from enterprise.audit_suite.company_runtime_activation import activate

    fixture = producer_source.__wrapped__(tmp_path)
    capsule = fixture["source_manifest_path"].parent
    originals = {p: sha(p.read_bytes()) for p in capsule.rglob("*") if p.is_file()}
    seed_versions = _rows(fixture["source_root"], "versions")
    seed_systems = _rows(fixture["source_root"], "systems")
    runtimes = {"one": tmp_path / "runtime-one", "two": tmp_path / "runtime-two"}
    for root in runtimes.values():
        receipt = activate(
            capsule, root, expected_manifest_sha256=fixture["expected_manifest_sha256"]
        )
        assert receipt["seed_counts"]["versions"] == 20
        assert all(
            receipt["seed_counts"][table] == 0
            for table in ("grants", "collections", "access_events")
        )
        assert _rows(root, "versions") == seed_versions
        assert _rows(root, "systems") == seed_systems
        assert not any(
            (root / name).exists() for name in ("worlds", "keys", "audit.sqlite3", "state.sqlite3")
        )
    pristine_second = sha((runtimes["two"] / "company.sqlite3").read_bytes())
    registry = tmp_path / "registry.json"
    _registry(
        registry,
        {"one": (runtimes["one"], "activity-clean"), "two": (runtimes["two"], "activity-messy")},
    )
    first, actor = _investigate(
        tmp_path / "audit-one", registry, "one", runtimes["one"], "activity-clean"
    )
    assert sha((runtimes["two"] / "company.sqlite3").read_bytes()) == pristine_second
    assert not _rows(runtimes["two"], "grants")
    # An actor/engagement grant in runtime one never authorizes the other runtime.
    with pytest.raises(CompanyStoreError):
        CompanyStore(runtimes["two"]).read_version(
            actor,
            first["id"],
            "SH",
            "activity-clean",
            "application",
            "MOVE-01-application",
            version=2,
            as_of="2027-05-01T00:00:00Z",
        )
    second, _ = _investigate(
        tmp_path / "audit-two", registry, "two", runtimes["two"], "activity-messy"
    )
    assert first["id"] != second["id"]
    for root in runtimes.values():
        assert _rows(root, "versions") == seed_versions
        assert _rows(root, "systems") == seed_systems
        assert (
            sha((root / "company.sqlite3").read_bytes())
            != originals[fixture["source_root"] / "company.sqlite3"]
        )
    assert all(sha(path.read_bytes()) == digest for path, digest in originals.items())
    assert not _rows(fixture["source_root"], "grants")
    assert not _rows(fixture["source_root"], "collections")
    assert not _rows(fixture["source_root"], "access_events")
