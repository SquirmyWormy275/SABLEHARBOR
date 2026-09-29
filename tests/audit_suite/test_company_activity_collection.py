"""Actual Engine collection of preexisting operational sources, without worlds."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite.company_activity import generate_pair
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.operating_source_bridge import sha
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_activity import ROOT, recipe


def exercise(company_root: Path, audit_root: Path, *, company_id, branches, event_id):
    engine = Engine(audit_root, company_root=company_root)
    actor = engine.store.provision("Local activity investigator", ["instructor", "learner"])["id"]
    source = engine.company_store
    with source._db() as db:
        original = {
            (r["branch"], r["system"], r["record"], r["version"]): r["sha256"]
            for r in db.execute("SELECT * FROM versions")
        }
    results = []
    # The second test also runs swapped mode labels. Mode is not a source predicate.
    for branch, mode in branches:
        state = engine.create(
            actor,
            {
                "command_id": f"create-{branch}",
                "title": "Scoped mover source investigation",
                "discipline": "IT",
                "mode": mode,
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
        assert [c["id"] for c in state["controls"]] == ["SH-IAM-003"]
        engine.company_bindings[state["id"]] = {"company": company_id, "branch": branch}
        for system in ["hr", "directory", "application", "site_access", "access_review"]:
            source.grant(actor, state["id"], company_id, branch, system)
        serial = 0

        def command(kind, payload):
            nonlocal state, serial
            serial += 1
            state = engine.command(
                actor,
                state["id"],
                {
                    "command_id": f"command-{serial}",
                    "expected_revision": state["revision"],
                    "kind": kind,
                    "payload": payload,
                },
            )
            return state

        command("company.activate", {})
        command("kickoff.start", {})
        command(
            "pbc.create",
            {
                "title": "Mover source lineage",
                "purpose": "Reconcile HR authorization, directory, application and site changes",
                "control_id": "SH-IAM-003",
                "boundary_id": "corporate",
                "person_id": state["controls"][0]["owner_ids"][0],
            },
        )
        request_id = state["requests"][0]["id"]
        command("pbc.issue", {"request_id": request_id})

        def collect(system, version, request_id=request_id):
            return command(
                "company.collect",
                {
                    "request_id": request_id,
                    "system_id": system,
                    "record_id": f"{event_id}-{system}",
                    "version": version,
                },
            )

        with pytest.raises(DomainError):
            collect("application", 2)
        assert not state["artifacts"]
        command("clock.advance", {"mode": "TARGET_DATE", "target": "2027-04-16"})
        source.grant(actor, state["id"], company_id, branch, "application", active=False)
        with pytest.raises(DomainError):
            collect("application", 2)
        assert not state["artifacts"]
        source.grant(actor, state["id"], company_id, branch, "application")
        for system, versions in [
            ("hr", [1, 2, 3]),
            ("directory", [1, 2]),
            ("application", [1, 2]),
            ("site_access", [1, 2]),
            ("access_review", [1]),
        ]:
            for version in versions:
                collect(system, version)
        assert len(state["artifacts"]) == 10
        parsed = {}
        for artifact in state["artifacts"]:
            identity = artifact["source"]["receipt"]["source"]
            key = (branch, identity["system"], identity["record"], identity["version"])
            content = engine.artifacts.read(artifact)
            assert sha(content) == artifact["sha256"] == original[key]
            parsed[f"{identity['system']}:{identity['version']}"] = json.loads(content)
        assert not (engine.store.root / "worlds" / state["id"]).exists()
        history = engine.store.history(actor, state["id"])
        results.append(
            {
                "engagement_id": state["id"],
                "branch": branch,
                "mode": mode,
                "scope": state["scope"],
                "simulated_at": state["simulated_at"],
                "artifact_hashes": {a["id"]: a["sha256"] for a in state["artifacts"]},
                "application_rights": parsed["application:2"]["rights"],
                "initial_rights": parsed["application:1"]["rights"],
                "history_events": len(history),
                "future_denied": True,
                "revocation_denied": True,
                "prepared_world": False,
            }
        )
        for system in ["hr", "directory", "application", "site_access", "access_review"]:
            source.grant(actor, state["id"], company_id, branch, system, active=False)
    with source._db() as db:
        after = {
            (r["branch"], r["system"], r["record"], r["version"]): r["sha256"]
            for r in db.execute("SELECT * FROM versions")
        }
    assert after == original
    assert results[0]["scope"] == results[1]["scope"]
    assert results[0]["initial_rights"] == results[1]["initial_rights"]
    assert results[0]["application_rights"] != results[1]["application_rights"]
    return {
        "results": results,
        "original_source_hashes_unchanged": True,
        "professional_sufficiency": "NOT_ASSESSED",
        "model_conversation": "NOT_RUN",
    }


@pytest.mark.parametrize("modes", [("CLEAN", "MESSY"), ("MESSY", "CLEAN")])
def test_actual_paired_collection_is_source_driven(tmp_path, modes):
    company = tmp_path / "company"
    company.mkdir(mode=0o700)
    generate_pair(CompanyStore(company), repository=ROOT, recipe=recipe())
    result = exercise(
        company,
        tmp_path / "audits",
        company_id="SH",
        branches=list(zip(["activity-clean", "activity-messy"], modes, strict=True)),
        event_id="MOVE-01",
    )
    assert result["results"][0]["application_rights"] == ["coordination-read"]
    assert result["results"][1]["application_rights"] == ["support-read", "coordination-read"]
