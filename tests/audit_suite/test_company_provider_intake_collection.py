"""Isolated ordinary Engine commands collect already-created planned-provider records."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite.company_collection import discover
from enterprise.audit_suite.company_provider_intake_activity import CONTROLS, generate_pair
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.operating_source_bridge import sha
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_provider_intake_activity import ROOT, recipe

SYSTEM_CONTROL = {
    "planned_dependency_inventory": "SH-TPR-001",
    "import_configuration": "SH-TPR-001",
    "vendor_register": "SH-TPR-001",
    "tier_assessments": "SH-TPR-001",
    "diligence_work_items": "SH-TPR-002",
    "review_schedule": "SH-TPR-004",
    "monitoring_reviews": "SH-TPR-004",
    "coverage_reconciliation": "SH-TPR-001",
    "internal_actions": "SH-TPR-001",
}


def exercise(company_root, audit_root, *, company_id, branches, program_pack=None):
    e = Engine(audit_root, company_root=company_root, program_pack=program_pack)
    actor = e.store.provision("Isolated planned-provider investigator", ["instructor", "learner"])[
        "id"
    ]
    source = e.company_store
    with source._db() as db:
        before = {
            (r["branch"], r["system"], r["record"], r["version"]): r["sha256"]
            for r in db.execute("SELECT * FROM versions")
        }
    results = []
    for branch in branches:
        state = e.create(
            actor,
            {
                "command_id": "create-" + branch,
                "title": "Planned-provider diligence investigation",
                "discipline": "IT",
                "mode": "CLEAN",
                "configuration": {"selections": []},
                "scope": {
                    "programs": ["SOC2", "HIPAA"],
                    "report_type": "Type 2",
                    "period_start": "2027-01-01",
                    "period_end": "2027-04-30",
                    "fieldwork_start": "2027-01-04",
                    "timezone": "UTC",
                    "boundaries": ["corporate"],
                    "control_ids": CONTROLS,
                },
            },
        )
        assert {c["id"] for c in state["controls"]} == set(CONTROLS)
        e.company_bindings[state["id"]] = {"company": company_id, "branch": branch}
        for system in SYSTEM_CONTROL:
            source.grant(actor, state["id"], company_id, branch, system)
        serial = 0

        def command(kind, payload):
            nonlocal state, serial
            serial += 1
            envelope = {
                "command_id": f"action-{serial}",
                "expected_revision": state["revision"],
                "kind": kind,
                "payload": payload,
            }
            state = e.command(actor, state["id"], envelope)
            return envelope

        try:
            command("company.activate", {})
            command("kickoff.start", {})
            requests = {}
            for control in state["controls"]:
                command(
                    "pbc.create",
                    {
                        "title": "Planned-provider internal records for " + control["id"],
                        "purpose": (
                            "Inspect original local intake and review-queue history; "
                            "provider support remains unverified"
                        ),
                        "control_id": control["id"],
                        "boundary_id": "corporate",
                        "person_id": control["owner_ids"][0],
                    },
                )
                requests[control["id"]] = state["requests"][-1]["id"]
                command("pbc.issue", {"request_id": requests[control["id"]]})
            with pytest.raises(DomainError):
                command(
                    "company.collect",
                    {
                        "system_id": "coverage_reconciliation",
                        "record_id": "COVERAGE-BACKFILL",
                        "version": 1,
                        "request_id": requests["SH-TPR-001"],
                    },
                )
            assert not state["artifacts"]
            command("clock.advance", {"mode": "TARGET_DATE", "target": "2027-04-06"})
            source.grant(actor, state["id"], company_id, branch, "vendor_register", active=False)
            with pytest.raises(DomainError):
                discover(e, actor, state["id"], "vendor_register")
            source.grant(actor, state["id"], company_id, branch, "vendor_register")
            for system, control in SYSTEM_CONTROL.items():
                page = discover(e, actor, state["id"], system, limit=100)
                assert page["next_after_record"] is None
                for record in page["records"]:
                    for version in range(1, record["version"] + 1):
                        envelope = command(
                            "company.collect",
                            {
                                "system_id": system,
                                "record_id": record["record"],
                                "version": version,
                                "request_id": requests[control],
                            },
                        )
                        assert e.command(actor, state["id"], envelope) == state
            data = {}
            for artifact in state["artifacts"]:
                native = artifact["source"]["receipt"]["source"]
                content = e.artifacts.read(artifact)
                assert (
                    sha(content)
                    == artifact["sha256"]
                    == before[branch, native["system"], native["record"], native["version"]]
                )
                data[native["system"], native["record"], native["version"]] = json.loads(content)
            initial = data["coverage_reconciliation", "COVERAGE-INITIAL", 1]
            later = data["coverage_reconciliation", "COVERAGE-BACKFILL", 1]
            assert not state["workpapers"] and not state["findings"] and not state["populations"]
            assert not (Path(audit_root) / "worlds" / state["id"]).exists()
            assert all(t.get("status") != "COMPLETE" for t in state["tasks"])
            for (system, _, _), record in data.items():
                if system == "vendor_register":
                    assert (
                        not record["provider"]["operating"]
                        and not record["provider"]["contract_executed"]
                    )
                if system == "diligence_work_items":
                    assert (
                        record["support_status"] == "NOT_OBTAINED"
                        and record["received_document_sha256"] is None
                    )
            results.append(
                {
                    "engagement_id": state["id"],
                    "branch": branch,
                    "artifact_count": len(state["artifacts"]),
                    "initial_missing_provider_ids": initial["missing_provider_ids"],
                    "later_missing_provider_ids": later["missing_provider_ids"],
                    "late_review_provider_ids": later["late_review_provider_ids"],
                    "diligence_support_obtained": later["diligence_support_obtained"],
                    "artifact_pins": [
                        {"id": a["id"], "sha256": a["sha256"], "bytes": a["bytes"]}
                        for a in state["artifacts"]
                    ],
                    "history_events": len(e.store.history(actor, state["id"])),
                    "no_prepared_world": True,
                }
            )
        finally:
            for system in SYSTEM_CONTROL:
                source.grant(actor, state["id"], company_id, branch, system, active=False)
    with source._db() as db:
        assert before == {
            (r["branch"], r["system"], r["record"], r["version"]): r["sha256"]
            for r in db.execute("SELECT * FROM versions")
        }
        assert (
            db.execute(
                "SELECT COUNT(*) FROM grants WHERE principal=? AND active=1", (actor,)
            ).fetchone()[0]
            == 0
        )
    assert results[0]["initial_missing_provider_ids"] == [] and results[1][
        "initial_missing_provider_ids"
    ] == ["CP-IDACORE"]
    assert all(
        not r["later_missing_provider_ids"] and r["diligence_support_obtained"] == 0
        for r in results
    )
    assert results[1]["late_review_provider_ids"] == ["CP-IDACORE"]
    return {
        "status": "PASS_BOUNDED_INTERNAL_SOURCE_COLLECTION",
        "engagements": results,
        "source_versions_unchanged": True,
        "temporary_grants_revoked": True,
        "qualification": (
            "Pre-operating local queues only, no supplier support or acceptance asserted"
        ),
    }


def test_existing_provider_records_collected_without_mode_inference(tmp_path):
    tmp_path.chmod(0o700)
    r = recipe()
    generate_pair(tmp_path / "company", repository=ROOT, recipe=r)
    result = exercise(
        tmp_path / "company",
        tmp_path / "audit",
        company_id=r.company_id,
        branches=[r.complete_branch, r.omission_branch],
    )
    assert len(result["engagements"]) == 2
