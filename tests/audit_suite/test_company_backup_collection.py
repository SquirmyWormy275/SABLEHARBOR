"""Audit collection consumes preexisting backup history through public Engine commands."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite.company_backup_activity import generate_backup_pair
from enterprise.audit_suite.company_collection import discover
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.operating_source_bridge import sha
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_backup_activity import ROOT, recipe

SYSTEM_CONTROL = {
    **{
        system: "SH-BCM-002"
        for system in (
            "inventory",
            "schedule",
            "source_dataset",
            "credential_event",
            "backup_job",
            "backup_object",
            "catalogue",
            "failure_ticket",
            "remediation",
        )
    },
    **{
        system: "SH-BCM-003"
        for system in ("restore_selection", "restored_dataset", "reconciliation", "review")
    },
}


def exercise(
    company_root: Path, audit_root: Path, *, company_id, branches, exercise_id, program_pack=None
):
    e = Engine(audit_root, company_root=company_root, program_pack=program_pack)
    actor = e.store.provision("Isolated backup investigator", ["instructor", "learner"])["id"]
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
                "title": "Backup source investigation",
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
            envelope = {
                "command_id": f"command-{serial}",
                "expected_revision": state["revision"],
                "kind": kind,
                "payload": payload,
            }
            state = e.command(actor, state["id"], envelope)
            if kind == "company.collect":
                history_before = e.store.history(actor, state["id"])
                assert e.command(actor, state["id"], envelope) == state
                assert e.store.history(actor, state["id"]) == history_before

        try:
            command("company.activate", {})
            command("kickoff.start", {})
            requests = {}
            for control in state["controls"]:
                command(
                    "pbc.create",
                    {
                        "title": f"Source records for {control['id']}",
                        "purpose": "Inspect original backup chronology and source lineage",
                        "control_id": control["id"],
                        "boundary_id": "corporate",
                        "person_id": control["owner_ids"][0],
                    },
                )
                requests[control["id"]] = state["requests"][-1]["id"]
                command("pbc.issue", {"request_id": state["requests"][-1]["id"]})
            assert discover(e, actor, state["id"], "restored_dataset")["records"] == []
            with pytest.raises(DomainError):
                command(
                    "company.collect",
                    {
                        "system_id": "restored_dataset",
                        "record_id": exercise_id + "-restored_dataset",
                        "version": 2,
                        "request_id": requests["SH-BCM-003"],
                    },
                )
            assert state["artifacts"] == []
            command("clock.advance", {"mode": "TARGET_DATE", "target": "2027-03-16"})
            source.grant(actor, state["id"], company_id, branch, "restored_dataset", active=False)
            with pytest.raises(DomainError):
                discover(e, actor, state["id"], "restored_dataset")
            with pytest.raises(DomainError):
                command(
                    "company.collect",
                    {
                        "system_id": "restored_dataset",
                        "record_id": exercise_id + "-restored_dataset",
                        "version": 2,
                        "request_id": requests["SH-BCM-003"],
                    },
                )
            source.grant(actor, state["id"], company_id, branch, "restored_dataset")
            tasks_before = json.loads(json.dumps(state["tasks"]))
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
            expected_rows = {r["id"]: r for r in parsed["source_dataset", 2]["records"]}
            for version in (1, 2):
                restored_rows = {r["id"]: r for r in parsed["restored_dataset", version]["records"]}
                reconciliation = parsed["reconciliation", version]
                assert reconciliation["missing_ids"] == sorted(
                    expected_rows.keys() - restored_rows.keys()
                )
                assert reconciliation["changed_ids"] == sorted(
                    k
                    for k in expected_rows.keys() & restored_rows.keys()
                    if expected_rows[k] != restored_rows[k]
                )
                assert (
                    reconciliation["restore_sha256"]
                    == before[
                        branch, "restored_dataset", exercise_id + "-restored_dataset", version
                    ]
                )
            assert parsed["source_dataset", 2] == parsed["restored_dataset", 2]
            assert len(collected) == sum(1 for key in before if key[0] == branch)
            assert state["tasks"] == tasks_before
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
                    "source_snapshot_sha256": before[
                        branch, "source_dataset", exercise_id + "-source_dataset", 2
                    ],
                    "initial_reconciliation": parsed["reconciliation", 1],
                    "retest_reconciliation": parsed["reconciliation", 2],
                    "testing_credit_from_collection": False,
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
    assert results[0]["source_snapshot_sha256"] == results[1]["source_snapshot_sha256"]
    assert results[0]["initial_reconciliation"]["missing_ids"] == []
    assert results[1]["initial_reconciliation"]["missing_ids"] == ["OBJ-03"]
    assert results[1]["initial_reconciliation"]["changed_ids"] == ["OBJ-02"]
    assert all(e["retest_reconciliation"]["missing_ids"] == [] for e in results)
    return {
        "engagements": results,
        "original_sources_unchanged": True,
        "grants_revoked": True,
        "comparison_basis": (
            "Exact collected dataset bytes and derived reconciliation; "
            "no automatic audit conclusion"
        ),
        "model_calls": 0,
    }


def test_actual_engine_paired_backup_discovery_and_collection(tmp_path):
    company = tmp_path / "company"
    company.mkdir(mode=0o700)
    generate_backup_pair(CompanyStore(company), repository=ROOT, recipe=recipe())
    audit = tmp_path / "audit"
    assert not audit.exists()
    result = exercise(
        company,
        audit,
        company_id="SH",
        branches=[("backup-clean", "CLEAN"), ("backup-messy", "MESSY")],
        exercise_id="BACKUP-01",
    )
    assert [len(e["collected"]) for e in result["engagements"]] == [26, 25]
