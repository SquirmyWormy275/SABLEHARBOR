"""Actual scoped collection preserves remediation history without employment promotion."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite.company_collection import discover
from enterprise.audit_suite.company_federation import QUALIFICATION
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.operating_source_bridge import sha
from enterprise.audit_suite.store import DomainError, canonical

ROOT = Path(__file__).resolve().parents[2]


def native_rows(store):
    with store._db() as db:
        return [
            dict(row)
            for row in db.execute(
                "SELECT * FROM versions ORDER BY company,branch,system,record,version"
            )
        ]


def collect_branch(company_root, audit_root, registry_path, *, company, branch):
    source = CompanyStore(company_root)
    original_rows = native_rows(source)
    with source._db() as db:
        prior_collections = db.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
    selected = [row for row in original_rows if row["branch"] == branch]
    assert selected
    systems = sorted({row["system"] for row in selected})
    with source._db() as db:
        owners = {
            row["system"]: row["owner"]
            for row in db.execute(
                "SELECT system,owner FROM systems WHERE company=? AND branch=?", (company, branch)
            )
        }
    registry = {
        "schema": "COMPANY_SOURCE_PORTFOLIO_V1",
        "components": {
            "remediation": {
                "root": str(company_root),
                "company": company,
                "branch": branch,
                "namespace": "REM",
                "systems": systems,
            }
        },
        "profiles": {
            "review": {
                "company": company,
                "components": ["remediation"],
                "qualification": QUALIFICATION,
            }
        },
    }
    registry_path.write_text(json.dumps(registry))
    registry_path.chmod(0o600)
    controls = sorted(
        {cid for row in selected for cid in json.loads(row["provenance"])["control_ids"]}
    )
    first = min(row["available_at"] for row in selected)
    last = max(row["available_at"] for row in selected)
    engine = Engine(
        audit_root, repository=ROOT, company_registry=registry_path, company_profile="review"
    )
    operator = engine.store.provision("Isolated remediation operator", ["instructor"])["id"]
    learner = engine.store.provision("Isolated remediation investigator", ["learner"])["id"]
    state = engine.create(
        operator,
        {
            "command_id": "create",
            "title": "Exact local remediation history",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {"selections": []},
            "scope": {
                "programs": ["SOC2"],
                "report_type": "Internal assessment",
                "period_start": first[:10],
                "period_end": last[:10],
                "fieldwork_start": first[:10],
                "timezone": "UTC",
                "boundaries": ["corporate"],
                "trust_services_categories": ["Security"],
                "control_ids": controls,
            },
        },
    )
    eid = state["id"]
    engine.store.grant(eid, learner, "learn")
    engine.company_bindings[eid] = engine.company_store.binding
    serial = 0

    def command(kind, payload, actor=learner):
        nonlocal state, serial
        serial += 1
        envelope = {
            "command_id": f"step-{serial}",
            "expected_revision": state["revision"],
            "kind": kind,
            "payload": payload,
        }
        state = engine.command(actor, eid, envelope)
        assert canonical(engine.command(actor, eid, envelope)) == canonical(state)
        return envelope

    def alias(system):
        return "REM:" + system

    with pytest.raises(DomainError):
        discover(engine, learner, eid, alias(systems[0]))
    for system in systems:
        source.grant(learner, eid, company, branch, system)
    try:
        command("company.activate", {}, operator)
        command("kickoff.start", {})
        people_before = canonical(state["people"])
        requests = {}
        for system in systems:
            row = next(row for row in selected if row["system"] == system)
            command(
                "pbc.create",
                {
                    "title": "Original remediation " + system,
                    "purpose": "Inspect exact local access findings and later action history",
                    "control_id": json.loads(row["provenance"])["control_ids"][0],
                    "boundary_id": "corporate",
                    "person_id": owners[system],
                },
            )
            requests[system] = state["requests"][-1]["id"]
            command("pbc.issue", {"request_id": requests[system]})
        future = max(selected, key=lambda row: row["available_at"])
        payload = {
            "system_id": alias(future["system"]),
            "record_id": future["record"],
            "version": future["version"],
            "request_id": requests[future["system"]],
        }
        before_denial = canonical(engine.store.get(learner, eid))
        with pytest.raises(DomainError):
            command("company.collect", payload)
        assert canonical(engine.store.get(learner, eid)) == before_denial
        assert not state["artifacts"]
        command("clock.advance", {"mode": "TARGET_DATE", "target": last})
        expected = {(row["system"], row["record"], row["version"]): row for row in selected}
        seen = set()
        collected_artifacts = []
        for system in systems:
            records = discover(engine, learner, eid, alias(system), limit=1000)["records"]
            discovered_ids = {record["record"] for record in records}
            # Discovery presents latest versions. Request exact earlier versions
            # from this explicitly retained native inventory, without rebasing pins.
            for original in (row for row in selected if row["system"] == system):
                assert original["record"] in discovered_ids
                record = original
                key = system, record["record"], record["version"]
                command(
                    "company.collect",
                    {
                        "system_id": alias(system),
                        "record_id": record["record"],
                        "version": record["version"],
                        "request_id": requests[system],
                    },
                )
                artifact = state["artifacts"][-1]
                assert engine.artifacts.read(artifact) == original["content"]
                body = json.loads(engine.artifacts.read(artifact))
                assert body["classification"] == (
                    "LOCAL_ACCESS_REMEDIATION_CONTINUATION_NOT_CANON_EMPLOYMENT_OR_DEPLOYMENT"
                )
                assert body["independent_assurance"] == "NOT_PERFORMED"
                assert body["supersession"] == "NONE_RETAINED_HISTORICAL_REVIEWS_NOT_REINTERPRETED"
                assert artifact["sha256"] == sha(original["content"]) == original["sha256"]
                receipt = artifact["source"]["receipt"]
                native = receipt["upstream_receipt"]["source"]
                for field in ("company", "branch", "system", "record", "version", "sha256"):
                    assert native[field] == original[field]
                assert receipt["source"]["source_system_alias"] == alias(system)
                assert receipt["source"]["source_store_id"] == "remediation"
                collected_artifacts.append(
                    {
                        "artifact_id": artifact["id"],
                        "system": system,
                        "record": record["record"],
                        "version": record["version"],
                        "sha256": artifact["sha256"],
                    }
                )
                seen.add(key)
        assert seen == set(expected)
        assert len(state["artifacts"]) == len(selected)
        assert canonical(state["people"]) == people_before
        assert not state["workpapers"] and not state["findings"] and not state["populations"]
        assert all(task["status"] == "NOT_STARTED" for task in state["tasks"])
        assert not (audit_root / "worlds" / eid).exists()
        source.grant(learner, eid, company, branch, future["system"], active=False)
        before_denial = canonical(engine.store.get(learner, eid))
        with pytest.raises(DomainError):
            command("company.collect", payload)
        assert canonical(engine.store.get(learner, eid)) == before_denial
        history = engine.store.history(learner, eid)  # Verifies every command/state hash link.
        assert history[-1]["revision"] == state["revision"]
        assert {(row["id"], row["sha256"]) for row in history[-1]["state"]["artifacts"]} == {
            (row["id"], row["sha256"]) for row in state["artifacts"]
        }
        with source._db() as db:
            assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[
                0
            ] == prior_collections + len(selected)
        return {
            "status": "PASS",
            "engagement_id": eid,
            "collected": len(seen),
            "branch": branch,
            "revision": state["revision"],
            "artifacts": collected_artifacts,
            "future_denied": True,
            "revoked_denied": True,
            "exact_replays": True,
            "people_unchanged": True,
            "no_testing_or_assurance_credit": True,
        }
    finally:
        for system in systems:
            source.grant(learner, eid, company, branch, system, active=False)
        assert native_rows(source) == original_rows
        with source._db() as db:
            assert db.execute("SELECT COUNT(*) FROM grants WHERE active=1").fetchone()[0] == 0


def test_actual_remediation_pair_federated_collection_preserves_originals_and_status(tmp_path):
    from enterprise.audit_suite.company_access_remediation_activity import (
        AccessRemediationRecipe,
        AccessRemediationSourceRef,
        generate_pair,
    )
    from tests.audit_suite.test_company_access_remediation_operator import prepared

    capsule, body = prepared.__wrapped__(tmp_path)
    source_root = capsule / "company"
    source_bytes = (source_root / "company.sqlite3").read_bytes()
    recipe = AccessRemediationRecipe(
        **{
            **body,
            "source_refs": tuple(AccessRemediationSourceRef(**row) for row in body["source_refs"]),
            "branch_ids": tuple(body["branch_ids"]),
        }
    )
    company_root = tmp_path / "remediation"
    generate_pair(company_root, repository=ROOT, source_root=source_root, recipe=recipe)
    results = [
        collect_branch(
            company_root,
            tmp_path / ("audit-" + branch),
            tmp_path / (branch + "-registry.json"),
            company=recipe.company_id,
            branch=branch,
        )
        for branch in recipe.branch_ids
    ]
    assert len({row["engagement_id"] for row in results}) == 2
    assert sum(row["collected"] for row in results) == 22
    assert (source_root / "company.sqlite3").read_bytes() == source_bytes
