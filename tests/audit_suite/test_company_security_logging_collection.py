"""Actual isolated audit commands consume existing SEC002 originals, never generate them."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite.company_collection import discover
from enterprise.audit_suite.company_security_logging_activity import generate_pair
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.operating_source_bridge import sha
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_security_logging_activity import ROOT, inputs  # noqa: F401


def exercise(company_root, audit_root, *, company_id, branches, program_pack=None):
    e = Engine(audit_root, company_root=company_root, program_pack=program_pack)
    actor = e.store.provision("Isolated logging investigator", ["instructor", "learner"])["id"]
    source = e.company_store
    with source._db() as db:
        original = {
            (r["branch"], r["system"], r["record"], r["version"]): r["sha256"]
            for r in db.execute("SELECT * FROM versions")
        }
        systems = {
            branch: [
                r[0]
                for r in db.execute(
                    "SELECT system FROM systems WHERE company=? AND branch=? ORDER BY system",
                    (company_id, branch),
                )
            ]
            for branch in branches
        }
    results = []
    for branch in branches:
        state = e.create(
            actor,
            {
                "command_id": "create-" + branch,
                "title": "Scoped logging source inspection",
                "discipline": "IT",
                "mode": "CLEAN",
                "configuration": {"selections": []},
                "scope": {
                    "programs": ["SOC2", "HIPAA"],
                    "report_type": "Type 2",
                    "period_start": "2027-02-01",
                    "period_end": "2027-02-28",
                    "fieldwork_start": "2027-02-01",
                    "timezone": "UTC",
                    "boundaries": ["corporate"],
                    "control_ids": ["SH-SEC-002"],
                },
            },
        )
        assert [c["id"] for c in state["controls"]] == ["SH-SEC-002"]
        e.company_bindings[state["id"]] = {"company": company_id, "branch": branch}
        for system in systems[branch]:
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
            command(
                "pbc.create",
                {
                    "title": "Local source coverage and collection originals",
                    "purpose": (
                        "Inspect scoped original chronology and source hashes; "
                        "no effectiveness assertion"
                    ),
                    "control_id": "SH-SEC-002",
                    "boundary_id": "corporate",
                    "person_id": state["controls"][0]["owner_ids"][0],
                },
            )
            request = state["requests"][-1]["id"]
            command("pbc.issue", {"request_id": request})
            with pytest.raises(DomainError):
                command(
                    "company.collect",
                    {
                        "system_id": "coverage_reconciliation",
                        "record_id": "COVERAGE-BACKFILL",
                        "version": 1,
                        "request_id": request,
                    },
                )
            assert not state["artifacts"]
            command("clock.advance", {"mode": "TARGET_DATE", "target": "2027-02-03"})
            source.grant(
                actor, state["id"], company_id, branch, "coverage_reconciliation", active=False
            )
            with pytest.raises(DomainError):
                discover(e, actor, state["id"], "coverage_reconciliation")
            source.grant(actor, state["id"], company_id, branch, "coverage_reconciliation")
            for system in systems[branch]:
                page = discover(e, actor, state["id"], system, limit=100)
                assert page["next_after_record"] is None
                for record in page["records"]:
                    for version in range(1, record["version"] + 1):
                        last = command(
                            "company.collect",
                            {
                                "system_id": system,
                                "record_id": record["record"],
                                "version": version,
                                "request_id": request,
                            },
                        )
                        assert e.command(actor, state["id"], last) == state
            collected = {}
            for artifact in state["artifacts"]:
                retained = artifact["source"]["receipt"]["source"]
                content = e.artifacts.read(artifact)
                assert (
                    sha(content)
                    == original[branch, retained["system"], retained["record"], retained["version"]]
                    == artifact["sha256"]
                )
                collected[retained["system"], retained["record"], retained["version"]] = json.loads(
                    content
                )
            initial = collected["coverage_reconciliation", "COVERAGE-INITIAL", 1]
            final = collected["coverage_reconciliation", "COVERAGE-BACKFILL", 1]
            assert not state["workpapers"] and not state["findings"] and not state["populations"]
            assert not (Path(audit_root) / "worlds" / state["id"]).exists()
            assert all(t.get("status") != "COMPLETE" for t in state["tasks"])
            results.append(
                {
                    "engagement_id": state["id"],
                    "branch": branch,
                    "artifact_count": len(state["artifacts"]),
                    "initial_missing_sequences": initial["missing_sequences"],
                    "later_missing_sequences": final["missing_sequences"],
                    "artifact_pins": [
                        {"id": a["id"], "sha256": a["sha256"], "bytes": a["bytes"]}
                        for a in state["artifacts"]
                    ],
                    "history_events": len(e.store.history(actor, state["id"])),
                    "no_prepared_world": True,
                }
            )
        finally:
            for system in systems[branch]:
                source.grant(actor, state["id"], company_id, branch, system, active=False)
    with source._db() as db:
        assert original == {
            (r["branch"], r["system"], r["record"], r["version"]): r["sha256"]
            for r in db.execute("SELECT * FROM versions")
        }
        assert (
            db.execute(
                "SELECT COUNT(*) FROM grants WHERE principal=? AND active=1", (actor,)
            ).fetchone()[0]
            == 0
        )
    assert results[0]["initial_missing_sequences"] == [] and results[1][
        "initial_missing_sequences"
    ] == [1]
    assert all(r["later_missing_sequences"] == [] for r in results)
    return {
        "status": "PASS_BOUNDED_SOURCE_COLLECTION",
        "engagements": results,
        "source_versions_unchanged": True,
        "temporary_grants_revoked": True,
        "qualification": "Technical source chronology only; no control effectiveness conclusion",
    }


def test_existing_paired_originals_through_engine(inputs, tmp_path):  # noqa: F811
    source, recipe = inputs
    generate_pair(tmp_path / "logging", repository=ROOT, source_root=source, recipe=recipe)
    result = exercise(
        tmp_path / "logging",
        tmp_path / "audit",
        company_id=recipe.company_id,
        branches=[recipe.complete_branch, recipe.omission_branch],
    )
    assert len(result["engagements"]) == 2
