import pytest

from enterprise.audit_suite.company_collection import discover
from enterprise.audit_suite.company_nonhuman_identity_activity import (
    CONTROL,
    generate_pair,
    read_inputs,
)
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.operating_source_bridge import sha
from enterprise.audit_suite.store import DomainError, canonical
from tests.audit_suite.test_company_nonhuman_identity_activity import ROOT
from tests.audit_suite.test_company_nonhuman_identity_activity import inputs as base_inputs
from tests.audit_suite.test_company_nonhuman_identity_activity import versions as rows


@pytest.fixture
def inputs(tmp_path):
    return base_inputs.__wrapped__(tmp_path)


def collect_pair(company_root, audit_root, *, source_root, recipe, program_pack=None):
    before = rows(company_root)
    source_before = (source_root / "company.sqlite3").read_bytes()
    source = CompanyStore(company_root)
    with source._db() as db:
        owners = {
            (r["branch"], r["system"]): r["owner"] for r in db.execute("SELECT * FROM systems")
        }
    engine = Engine(
        audit_root, repository=ROOT, company_root=company_root, program_pack=program_pack
    )
    operator = engine.store.provision("Isolated nonhuman identity operator", ["instructor"])["id"]
    learner = engine.store.provision("Isolated nonhuman identity investigator", ["learner"])["id"]
    result = []
    for branch in recipe.branch_ids:
        available = [r for r in before if r["branch"] == branch]
        state = engine.create(
            operator,
            {
                "command_id": "create-" + branch,
                "title": "Local nonhuman credential originals",
                "discipline": "IT",
                "mode": "CLEAN",
                "configuration": {"selections": []},
                "scope": {
                    "programs": ["SOC2"],
                    "report_type": "Type 2",
                    "period_start": recipe.period_start[:10],
                    "period_end": recipe.review_at[:10],
                    "fieldwork_start": recipe.period_start[:10],
                    "timezone": "UTC",
                    "boundaries": ["corporate"],
                    "trust_services_categories": ["Security"],
                    "control_ids": [CONTROL],
                },
            },
        )
        eid = state["id"]
        engine.store.grant(eid, learner, "learn")
        engine.company_bindings[eid] = {"company": recipe.company_id, "branch": branch}
        systems = sorted({r["system"] for r in available})
        serial = 0
        for system in systems:
            source.grant(learner, eid, recipe.company_id, branch, system)

        def command(kind, payload, actor=learner, *, branch=branch, eid=eid):
            nonlocal state, serial
            serial += 1
            envelope = {
                "command_id": branch + "-" + str(serial),
                "expected_revision": state["revision"],
                "kind": kind,
                "payload": payload,
            }
            state = engine.command(actor, eid, envelope)
            assert canonical(engine.command(actor, eid, envelope)) == canonical(state)
            return state

        collected = []
        try:
            command("company.activate", {}, operator)
            command("kickoff.start", {})
            requests = {}
            for system in systems:
                cid = CONTROL
                command(
                    "pbc.create",
                    {
                        "title": "Original local " + system,
                        "purpose": "Inspect exact fictional workload identity records",
                        "control_id": cid,
                        "person_id": owners[branch, system],
                        "boundary_id": "corporate",
                    },
                )
                requests[system] = state["requests"][-1]["id"]
                command("pbc.issue", {"request_id": requests[system]})
            future = max(available, key=lambda r: r["available_at"])
            revision = state["revision"]
            with pytest.raises(DomainError):
                engine.command(
                    learner,
                    eid,
                    {
                        "command_id": "future-" + branch,
                        "expected_revision": revision,
                        "kind": "company.collect",
                        "payload": {
                            "system_id": future["system"],
                            "record_id": future["record"],
                            "version": future["version"],
                            "request_id": requests[future["system"]],
                        },
                    },
                )
            assert engine.store.get(learner, eid)["revision"] == revision
            originals = {(r["system"], r["record"], r["version"]): r for r in available}
            seen = set()
            checkpoints = [None, recipe.reconcile_at, recipe.correction_at, recipe.review_at]
            for checkpoint in checkpoints:
                if checkpoint:
                    command("clock.advance", {"mode": "TARGET_DATE", "target": checkpoint})
                for system in systems:
                    for record in discover(engine, learner, eid, system, limit=1000)["records"]:
                        key = (system, record["record"], record["version"])
                        if key in seen:
                            continue
                        original = originals[key]
                        command(
                            "company.collect",
                            {
                                "system_id": system,
                                "record_id": record["record"],
                                "version": record["version"],
                                "request_id": requests[system],
                            },
                        )
                        artifact = state["artifacts"][-1]
                        assert engine.artifacts.read(artifact) == original["content"]
                        assert artifact["sha256"] == original["sha256"]
                        collected.append(
                            {
                                "artifact_id": artifact["id"],
                                "system": system,
                                "record": record["record"],
                                "version": record["version"],
                                "sha256": artifact["sha256"],
                            }
                        )
                        seen.add(key)
            assert len(collected) == len(available)
            assert len(available) == (18 if branch == recipe.branch_ids[0] else 17)
            assert not state["workpapers"] and not state["findings"] and not state["populations"]
            assert all(t["status"] == "NOT_STARTED" for t in state["tasks"])
            assert not (audit_root / "worlds" / eid).exists()
            result.append(
                {
                    "branch": branch,
                    "engagement_id": eid,
                    "revision": state["revision"],
                    "collected": collected,
                    "future_denied": True,
                    "exact_replays": True,
                    "no_model_world_or_testing_credit": True,
                }
            )
        finally:
            for system in systems:
                source.grant(learner, eid, recipe.company_id, branch, system, active=False)
    assert rows(company_root) == before
    assert (source_root / "company.sqlite3").read_bytes() == source_before
    assert read_inputs(source_root, recipe.source_refs)[1] == recipe.source_versions_sha256
    with source._db() as db:
        assert db.execute("SELECT COUNT(*) FROM grants WHERE active=1").fetchone()[0] == 0
    return {
        "status": "PASS",
        "branches": result,
        "all_original_versions_unchanged": True,
        "upstream_database_sha256": sha(source_before),
        "temporary_grants_revoked": True,
    }


def test_actual_nonhuman_pair_collects_initial_and_later_versions(tmp_path, inputs):
    source, recipe = inputs
    generate_pair(tmp_path / "nonhuman", repository=ROOT, source_root=source, recipe=recipe)
    result = collect_pair(
        tmp_path / "nonhuman", tmp_path / "audit", source_root=source, recipe=recipe
    )
    assert len(result["branches"]) == 2
