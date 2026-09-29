"""Actual source capture and trusted read-only CLI for the optional removal contract."""

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from enterprise.audit_suite.company_federation import QUALIFICATION
from enterprise.audit_suite.company_runtime_activation import activate
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.source_dependency_reconciliation import REF_KEYS, write_report
from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_company_access_remediation_operator import ROOT, write
from tests.audit_suite.test_company_access_remediation_operator import prepared as source_fixture
from tools.audit_suite import generate_company_activity as operator


@pytest.fixture
def context(tmp_path):
    parent, recipe = source_fixture.__wrapped__(tmp_path)
    capsule = tmp_path / "removal-capsule"
    operator.run(
        "access-remediation",
        write(tmp_path / "removal.json", recipe),
        capsule,
        repository=ROOT,
        source_root=parent / "company",
    )
    components = {}
    stores = {}
    capsule_pins = {}
    for key, original, branch, namespace in [
        ("parent", parent, "activity-messy", "IAM"),
        ("removal", capsule, "removal-b", "REM"),
    ]:
        pin = hashlib.sha256((original / "MANIFEST.json").read_bytes()).hexdigest()
        runtime = tmp_path / (key + "-runtime")
        activate(original, runtime, expected_manifest_sha256=pin)
        store = CompanyStore(runtime)
        with store._db() as db:
            systems = [
                r[0] for r in db.execute("SELECT system FROM systems WHERE branch=?", (branch,))
            ]
        components[key] = dict(
            root=str(runtime), company="SH", branch=branch, namespace=namespace, systems=systems
        )
        stores[key] = store
        capsule_pins[str(original)] = {
            name: hashlib.sha256((original / name).read_bytes()).hexdigest()
            for name in json.loads((original / "MANIFEST.json").read_bytes())["members"]
        }
    registry = write(
        tmp_path / "registry.json",
        dict(
            schema="COMPANY_SOURCE_PORTFOLIO_V1",
            components=components,
            profiles={
                "reference": dict(
                    company="SH", components=list(components), qualification=QUALIFICATION
                )
            },
        ),
    )
    engine = Engine(
        tmp_path / "audit", repository=ROOT, company_registry=registry, company_profile="reference"
    )
    actor = engine.store.provision("Source reviewer", ["instructor"])
    state = {key: [] for key in COLLECTIONS}
    state.update(
        scope=dict(period_start="2027-01-01", period_end="2027-12-31", boundaries=["corporate"]),
        simulated_at="2027-07-02T00:00:00.000000+00:00",
        controls=[{"id": "SH-IAM-007"}],
        company_source_binding=engine.company_store.binding,
    )
    state = engine.store.create(actor["id"], state, "create")
    engine.company_bindings[state["id"]] = engine.company_store.binding
    for key, component in components.items():
        for system in component["systems"]:
            stores[key].grant(actor["id"], state["id"], "SH", component["branch"], system)
    refs = []
    ids = {}
    for key, component in components.items():
        with stores[key]._db() as db:
            rows = [
                dict(r)
                for r in db.execute("SELECT * FROM versions WHERE branch=?", (component["branch"],))
            ]
        if key == "parent":
            selected = {(r["system"], r["record"], r["version"]) for r in recipe["source_refs"]}
            rows = [r for r in rows if (r["system"], r["record"], r["version"]) in selected]
        for row in rows:
            native = engine.company_store.read_version(
                actor["id"],
                state["id"],
                "SH",
                "reference",
                component["namespace"] + ":" + row["system"],
                row["record"],
                version=row["version"],
                as_of=state["simulated_at"],
            )
            identity = f"{key}-{row['system']}-{row['record']}-{row['version']}"
            refs.append({"id": identity, **{field: native[field] for field in REF_KEYS - {"id"}}})
            ids[key, row["system"], row["record"], row["version"]] = identity
    parent_ids = {
        field: ids["parent", system, record, version]
        for field, system, record, version in [
            ("population_ref_id", "review_population", "PRIV-2027-Q2", 1),
            ("decisions_ref_id", "review_decisions", "PRIV-2027-Q2", 1),
            ("reconciliation_ref_id", "review_reconciliation", "PRIV-2027-Q2", 1),
            ("application_ref_id", "application", "MOVE-Q2-application", 2),
            ("hr_ref_id", "hr", "MOVE-Q2-hr", 3),
        ]
    }
    contract = dict(
        parent=parent_ids,
        producer_label_expected=recipe["source_store_id"],
        baseline_ref_id=ids["removal", "entitlement_state", "APPLICATION", 1],
        request_ref_id=ids["removal", "removal_requests", "REQUEST", 1],
        attempts=[
            {
                field: ids["removal", system, record, version]
                for field, system, record, version in [
                    ("resolver_ref_id", "permission_resolver", "RESOLVER", attempt),
                    ("execution_ref_id", "execution_attempts", "EXECUTION", attempt),
                    ("state_ref_id", "entitlement_state", "APPLICATION", attempt + 1),
                    ("verification_ref_id", "validation_probes", "VALIDATION", attempt),
                ]
            }
            for attempt in (1, 2)
        ],
        followup_ref_ids=[ids["removal", "remediation_followup", "FOLLOWUP", 1]],
    )
    plan = dict(
        registry_sha256=engine.company_store.binding["registry_sha256"],
        scope_sha256=digest(state["scope"]),
        source_refs=refs,
        adapters=[],
        period_contracts=[],
        access_remediation_contracts=[contract],
    )
    return engine, actor, state, plan, stores, capsule_pins, registry


def test_actual_optional_contract_capture_and_preserved_runtime_and_audit(context, tmp_path):
    engine, actor, state, plan, stores, capsules, registry = context
    # Finish setup writes before taking a physical-byte baseline of this WAL database.
    with closing(sqlite3.connect(engine.store.db_path)) as db:
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    before = engine.store.db_path.read_bytes()
    native_before = {key: store.path.read_bytes() for key, store in stores.items()}
    write_report(engine, actor["id"], state["id"], plan, output=tmp_path / "report")
    report = json.loads((tmp_path / "report/REPORT.json").read_bytes())
    assert len(report["sources"]) == 16
    assert len(report["access_remediation_reconciliation"]) == 1
    observed = report["access_remediation_reconciliation"][0]
    assert observed["baseline_matches_selected_application"]
    assert observed["request_matches_selected_decision"]
    assert observed["metadata_verification"] == "NOT_RECOMPUTABLE_FROM_RETAINED_FIELDS"
    assert observed["recorded_unresolved_population_ids"] == ["P014"]
    assert observed["whole_review_closure"] == "NOT_ESTABLISHED"
    assert all(link["status"] == "EXACT_MATCH" for link in observed["lineage"])
    assert all(item["state_matches_local_transition"] for item in observed["attempts"])
    assert observed["attempts"][0]["recorded_after_rights"] == ["billing-admin", "inventory-admin"]
    assert observed["attempts"][1]["recorded_after_rights"] == ["inventory-admin"]
    assert report["control_effectiveness"] == "NOT_ASSESSED"
    assert report["population_acceptance"] == "NOT_PERFORMED"
    from tools.audit_suite.reconcile_source_dependencies import run

    config = dict(
        audit_root=str(engine.store.root),
        actor_id=actor["id"],
        engagement_id=state["id"],
        company_registry=str(registry),
        company_profile="reference",
        company_bindings=str(write(tmp_path / "bindings.json", engine.company_bindings)),
        plan=str(write(tmp_path / "plan.json", plan)),
    )
    run(write(tmp_path / "config.json", config), tmp_path / "cli-report")
    cli = json.loads((tmp_path / "cli-report/REPORT.json").read_bytes())
    assert cli["access_remediation_reconciliation"] == report["access_remediation_reconciliation"]
    assert engine.store.db_path.read_bytes() == before
    assert all(store.path.read_bytes() == native_before[key] for key, store in stores.items())
    for root, members in capsules.items():
        assert all(
            hashlib.sha256((Path(root) / name).read_bytes()).hexdigest() == pin
            for name, pin in members.items()
        )


@pytest.mark.parametrize("fault", ["revoked", "wrong_digest", "unknown_option"])
def test_optional_report_rejects_inexact_or_unauthorized_sources(context, tmp_path, fault):
    engine, actor, state, plan, stores, *_ = context
    if fault == "revoked":
        stores["removal"].grant(
            actor["id"], state["id"], "SH", "removal-b", "validation_probes", active=False
        )
    elif fault == "wrong_digest":
        plan["source_refs"][-1]["sha256"] = "0" * 64
    else:
        plan["inferred_complete"] = True
    with pytest.raises((DomainError, CompanyStoreError)):
        write_report(engine, actor["id"], state["id"], plan, output=tmp_path / "report")
    assert not (tmp_path / "report").exists()
