"""Audit collection consumes preexisting incident history through public Engine commands."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite.company_collection import discover
from enterprise.audit_suite.company_incident_activity import generate_incident
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.operating_source_bridge import sha
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_incident_activity import ROOT, recipe

SYSTEM_CONTROL = {
    "inventory": "SH-INC-001",
    "incident_ticket": "SH-INC-001",
    "escalation": "SH-INC-001",
    "monitoring": "SH-INC-002",
    "status_updates": "SH-INC-002",
    "recovery": "SH-INC-002",
    "postincident_review": "SH-INC-003",
    "corrective_action": "SH-INC-004",
    "dispatch_replay": "SH-INC-004",
    "action_validation": "SH-INC-004",
}


def exercise(
    company_root: Path, audit_root: Path, *, company_id, branches, incident_id, program_pack=None
):
    e = Engine(audit_root, company_root=company_root, program_pack=program_pack)
    actor = e.store.provision("Isolated incident investigator", ["instructor", "learner"])["id"]
    source = e.company_store
    with source._db() as db:
        before = {
            (r["branch"], r["system"], r["record"], r["version"]): r["sha256"]
            for r in db.execute("SELECT * FROM versions")
        }
    assert before
    results = []
    for branch, mode in branches:
        state = e.create(
            actor,
            {
                "command_id": "create-" + branch,
                "title": "Incident source investigation",
                "discipline": "IT",
                "mode": mode,
                "configuration": {"selections": []},
                "scope": {
                    "programs": ["SOC2", "HIPAA"],
                    "report_type": "Type 2",
                    "period_start": "2027-03-01",
                    "period_end": "2027-03-31",
                    "fieldwork_start": "2027-03-11",
                    "timezone": "UTC",
                    "boundaries": ["corporate"],
                    "control_ids": sorted(set(SYSTEM_CONTROL.values())),
                },
            },
        )
        assert {c["id"] for c in state["controls"]} == set(SYSTEM_CONTROL.values())
        e.company_bindings[state["id"]] = {"company": company_id, "branch": branch}
        for system in SYSTEM_CONTROL:
            source.grant(actor, state["id"], company_id, branch, system)
        serial = 0

        def command(kind, payload):
            nonlocal state, serial
            serial += 1
            state = e.command(
                actor,
                state["id"],
                {
                    "command_id": f"command-{serial}",
                    "expected_revision": state["revision"],
                    "kind": kind,
                    "payload": payload,
                },
            )

        try:
            command("company.activate", {})
            command("kickoff.start", {})
            requests = {}
            for control in state["controls"]:
                command(
                    "pbc.create",
                    {
                        "title": f"Source records for {control['id']}",
                        "purpose": "Inspect original incident chronology and source lineage",
                        "control_id": control["id"],
                        "boundary_id": "corporate",
                        "person_id": control["owner_ids"][0],
                    },
                )
                requests[control["id"]] = state["requests"][-1]["id"]
                command("pbc.issue", {"request_id": state["requests"][-1]["id"]})
            assert discover(e, actor, state["id"], "escalation")["records"] == []
            with pytest.raises(DomainError):
                command(
                    "company.collect",
                    {
                        "system_id": "escalation",
                        "record_id": incident_id + "-escalation",
                        "version": 2,
                        "request_id": requests["SH-INC-001"],
                    },
                )
            assert state["artifacts"] == []
            command("clock.advance", {"mode": "TARGET_DATE", "target": "2027-03-16"})
            source.grant(actor, state["id"], company_id, branch, "escalation", active=False)
            with pytest.raises(DomainError):
                discover(e, actor, state["id"], "escalation")
            with pytest.raises(DomainError):
                command(
                    "company.collect",
                    {
                        "system_id": "escalation",
                        "record_id": incident_id + "-escalation",
                        "version": 2,
                        "request_id": requests["SH-INC-001"],
                    },
                )
            source.grant(actor, state["id"], company_id, branch, "escalation")
            discovered = []
            for system, control in SYSTEM_CONTROL.items():
                page = discover(e, actor, state["id"], system, limit=100)
                assert page["next_after_record"] is None
                for record in page["records"]:
                    discovered.append(
                        {
                            "system": system,
                            "record": record["record"],
                            "latest_version": record["version"],
                        }
                    )
                    for version in range(1, record["version"] + 1):
                        command(
                            "company.collect",
                            {
                                "system_id": system,
                                "record_id": record["record"],
                                "version": version,
                                "request_id": requests[control],
                            },
                        )
            parsed = {}
            collected = []
            for artifact in state["artifacts"]:
                identity = artifact["source"]["receipt"]["source"]
                original = (branch, identity["system"], identity["record"], identity["version"])
                raw = e.artifacts.read(artifact)
                assert sha(raw) == artifact["sha256"] == before[original]
                parsed[identity["system"], identity["version"]] = json.loads(raw)
                collected.append(
                    {
                        "artifact_id": artifact["id"],
                        "source": {
                            k: identity[k]
                            for k in ["company", "branch", "system", "record", "version", "sha256"]
                        },
                    }
                )
            assert len(collected) == 18
            assert not (e.store.root / "worlds" / state["id"]).exists()
            assert all(r["status"] == "SUBMITTED" for r in state["requests"])
            history = e.store.history(actor, state["id"])
            results.append(
                {
                    "engagement_id": state["id"],
                    "branch": branch,
                    "mode": mode,
                    "scope": state["scope"],
                    "simulated_at": state["simulated_at"],
                    "discovered": discovered,
                    "collected": collected,
                    "history_events": len(history),
                    "future_discovery_empty": True,
                    "future_collect_denied": True,
                    "revoked_discovery_and_collection_denied": True,
                    "prepared_world": False,
                    "initial_probe_sha256": before[
                        branch, "monitoring", incident_id + "-monitoring", 1
                    ],
                    "delivered_at": parsed["escalation", 2]["delivered_at"],
                    "restored_at": parsed["recovery", 2]["restored_at"],
                    "restoration_minutes": parsed["recovery", 2]["elapsed_minutes_from_discovery"],
                    "professional_conclusion": "NOT_ASSESSED",
                }
            )
        finally:
            for system in SYSTEM_CONTROL:
                source.grant(actor, state["id"], company_id, branch, system, active=False)
    with source._db() as db:
        after = {
            (r["branch"], r["system"], r["record"], r["version"]): r["sha256"]
            for r in db.execute("SELECT * FROM versions")
        }
    assert before == after
    assert results[0]["scope"] == results[1]["scope"]
    assert results[0]["initial_probe_sha256"] == results[1]["initial_probe_sha256"]
    assert results[1]["restoration_minutes"] - results[0]["restoration_minutes"] == 30
    return {
        "engagements": results,
        "original_sources_unchanged": True,
        "grants_revoked": True,
        "comparison_basis": "Exact collected source timestamps; no automatic audit conclusion",
        "model_calls": 0,
    }


def test_actual_engine_paired_incident_discovery_and_collection(tmp_path):
    company = tmp_path / "company"
    company.mkdir(mode=0o700)
    generate_incident(CompanyStore(company), repository=ROOT, recipe=recipe())
    audit = tmp_path / "audit"
    assert not audit.exists()
    result = exercise(
        company,
        audit,
        company_id="SH",
        branches=[("incident-clean", "CLEAN"), ("incident-messy", "MESSY")],
        incident_id="INC-01",
    )
    assert all(len(e["collected"]) == 18 for e in result["engagements"])
