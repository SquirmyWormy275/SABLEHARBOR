import json
from dataclasses import replace
from pathlib import Path

import pytest

from enterprise.audit_suite.company_change_activity import ChangeRecipe, evaluate, generate_pair
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha

ROOT = Path(__file__).resolve().parents[2]


def recipe():
    return ChangeRecipe(
        "SH",
        "release-a",
        "release-b",
        "LOCAL-CHANGE-001",
        "2027-02-01T00:00:00Z",
        "2027-02-03T00:00:00Z",
        "Local retry budget<=120ms; approved exact artifact review before release.",
    )


def rows(store):
    with store._db() as db:
        return {(r["branch"], r["record"]): dict(r) for r in db.execute("SELECT * FROM versions")}


def test_causal_release_originals_hashes_and_no_grants(tmp_path):
    tmp_path.chmod(0o700)
    receipt = generate_pair(tmp_path / "company", repository=ROOT, recipe=recipe())
    store = CompanyStore(tmp_path / "company")
    values = rows(store)

    def native(branch, record):
        return json.loads(values[branch, record]["content"])

    for identity in [
        "CONFIG-BASELINE",
        "CONFIG-PROPOSED",
        "BUILD-PROPOSED",
        "TEST-PROPOSED",
        "ROLLBACK-PLAN",
    ]:
        assert values["release-a", identity]["content"] == values["release-b", identity]["content"]
    assert ("release-a", "RELEASE-PROPOSED") not in values
    assert native("release-a", "GATE-PROPOSED")["decision"] == "BLOCKED"
    assert native("release-b", "GATE-PROPOSED")["peer_review"] is None
    assert native("release-b", "GATE-PROPOSED")["emergency"] is False
    assert native("release-b", "GATE-PROPOSED")["approved_exception"] is None
    assert (
        native("release-b", "RELEASE-PROPOSED")["local_target_result"][
            "calculated_total_timeout_ms"
        ]
        == 150
    )
    for branch in ["release-a", "release-b"]:
        n = native(branch, "BUILD-PROPOSED")
        assert n["package_sha256"] == sha(encoded(n["package"]))
        c = n["package"]["configuration"]
        assert c["timeout_ms"] * c["attempts"] > c["max_total_ms"]
        assert native(branch, "TEST-PROPOSED")["passed"] is True
        assert native(branch, "TEST-PROPOSED")["test_scope"] == "SCHEMA_ONLY"
        assert native(branch, "REVIEW-PROPOSED")["decision"] == "CHANGES_REQUESTED"
        assert (
            native(branch, "RELEASE-CORRECTED")["local_target_result"]["within_local_limit"] is True
        )
        assert (
            native(branch, "ROLLBACK-REHEARSAL")["restored_local_result"][
                "calculated_total_timeout_ms"
            ]
            == 90
        )

    def refs(value):
        if isinstance(value, dict):
            if {"system_id", "record_id", "version", "sha256", "available_at"} <= value.keys():
                yield value
            for v in value.values():
                yield from refs(v)
        elif isinstance(value, list):
            for v in value:
                yield from refs(v)

    for (branch, _), row in values.items():
        assert sha(row["content"]) == row["sha256"]
        n = json.loads(row["content"])
        assert n["classification"].endswith("NOT_LIVE_DEPLOYMENT")
        assert all(s["operating"] is False for s in n["site_references_only"])
        for ref in refs(n):
            target = values[branch, ref["record_id"]]
            assert target["sha256"] == ref["sha256"] and target["system"] == ref["system_id"]
            assert target["available_at"] <= row["available_at"]
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    assert receipt["owner_id"] == "P005" and receipt["reviewer_id"] == "P002"
    assert receipt["not_exercised"] == ["SH-ENG-005"]
    before = rows(store)
    with pytest.raises(CompanyStoreError):
        generate_pair(tmp_path / "company", repository=ROOT, recipe=recipe())
    assert rows(store) == before


@pytest.mark.parametrize(
    "change",
    [
        {"bypass_branch": "release-a"},
        {"period_end_exclusive": "2027-02-01T10:00:00Z"},
        {"local_requirement_basis": ""},
    ],
)
def test_invalid_recipe_never_publishes(tmp_path, change):
    tmp_path.chmod(0o700)
    with pytest.raises(CompanyStoreError):
        generate_pair(tmp_path / "company", repository=ROOT, recipe=replace(recipe(), **change))
    assert not (tmp_path / "company").exists()


@pytest.mark.parametrize(
    "config",
    [
        dict(timeout_ms=True, attempts=3, max_total_ms=120),
        dict(timeout_ms=30.5, attempts=3, max_total_ms=120),
        dict(timeout_ms=30, attempts=0, max_total_ms=120),
    ],
)
def test_model_rejects_malformed_inputs(config):
    with pytest.raises(CompanyStoreError):
        evaluate(config)


def test_gate_rejects_wrong_artifact_and_preserves_target():
    from enterprise.audit_suite.company_change_activity import LocalTarget, gate_decision

    artifact = {"sha256": "exact-build"}
    passing = {"artifact": artifact, "passed": True}
    wrong = {"artifact": {"sha256": "other-build"}, "decision": "APPROVED"}
    assert gate_decision(artifact, passing, wrong) == "BLOCKED"
    assert gate_decision(artifact, passing, None, override=True) == "OVERRIDE_USED"
    assert (
        gate_decision(artifact, {"artifact": artifact, "passed": False}, None, override=True)
        == "BLOCKED"
    )
    target = LocalTarget({"timeout_ms": 30, "attempts": 3, "max_total_ms": 120})
    before = dict(target.config)
    with pytest.raises(CompanyStoreError):
        target.apply({"timeout_ms": 50, "attempts": 3, "max_total_ms": 120}, "BLOCKED")
    assert target.config == before


def collect_pair(company_root, audit_root, *, source_recipe, program_pack=None):
    """Actual scoped Engine activation/PBC/discovery/collection; no evidence generation."""
    from enterprise.audit_suite.company_collection import discover
    from enterprise.audit_suite.engine import Engine
    from enterprise.audit_suite.store import DomainError, canonical

    store = CompanyStore(company_root)
    originals = rows(store)
    engine = Engine(
        audit_root, repository=ROOT, company_root=company_root, program_pack=program_pack
    )
    operator = engine.store.provision("Local change collection operator", ["instructor"])["id"]
    actor = engine.store.provision("Local change collection learner", ["learner"])["id"]
    receipts = []
    for branch in (source_recipe.gated_branch, source_recipe.bypass_branch):
        state = engine.create(
            operator,
            {
                "command_id": "create-" + branch,
                "title": "Local change source collection",
                "discipline": "IT",
                "mode": "CLEAN",
                "configuration": {"selections": []},
                "scope": {
                    "programs": ["SOC2"],
                    "report_type": "Type 2",
                    "period_start": "2027-02-01",
                    "period_end": "2027-02-02",
                    "fieldwork_start": "2027-02-01",
                    "timezone": "UTC",
                    "boundaries": ["corporate"],
                    "trust_services_categories": ["Security"],
                    "control_ids": [
                        "SH-ENG-001",
                        "SH-ENG-002",
                        "SH-ENG-003",
                        "SH-ENG-004",
                        "SH-ENG-006",
                    ],
                },
            },
        )
        engine.store.grant(state["id"], actor, "learn")
        engine.company_bindings[state["id"]] = {
            "company": source_recipe.company_id,
            "branch": branch,
        }
        source_rows = {key[1]: r for key, r in originals.items() if key[0] == branch}
        systems = sorted({r["system"] for r in source_rows.values()})
        for system in systems:
            store.grant(actor, state["id"], source_recipe.company_id, branch, system)
        serial = 0

        def command(kind, payload, principal=actor, branch=branch):
            nonlocal state, serial
            serial += 1
            envelope = {
                "command_id": branch + "-" + str(serial),
                "expected_revision": state["revision"],
                "kind": kind,
                "payload": payload,
            }
            state = engine.command(principal, state["id"], envelope)
            return envelope

        command("company.activate", {}, operator)
        command("kickoff.start", {})
        command(
            "pbc.create",
            {
                "title": "Original local change records",
                "purpose": "Inspect source facts only.",
                "control_id": "SH-ENG-001",
                "person_id": "P005",
                "boundary_id": "corporate",
            },
        )
        request = state["requests"][-1]["id"]
        command("pbc.issue", {"request_id": request})
        before = state["revision"]
        with pytest.raises(DomainError):
            engine.command(
                actor,
                state["id"],
                {
                    "command_id": "future",
                    "expected_revision": before,
                    "kind": "company.collect",
                    "payload": {
                        "system_id": "local_releases",
                        "record_id": "RELEASE-CORRECTED",
                        "version": 1,
                        "request_id": request,
                    },
                },
            )
        assert engine.store.get(actor, state["id"])["revision"] == before
        command("clock.advance", {"mode": "TARGET_DATE", "target": "2027-02-02T00:00:00Z"})
        collected = []
        for system in systems:
            for item in discover(engine, actor, state["id"], system, limit=1000)["records"]:
                envelope = command(
                    "company.collect",
                    {
                        "system_id": system,
                        "record_id": item["record"],
                        "version": 1,
                        "request_id": request,
                    },
                )
                assert canonical(engine.command(actor, state["id"], envelope)) == canonical(state)
                artifact = state["artifacts"][-1]
                original = source_rows[item["record"]]
                assert engine.artifacts.read(artifact) == original["content"]
                assert artifact["sha256"] == original["sha256"]
                collected.append(
                    {
                        "record_id": item["record"],
                        "artifact_id": artifact["id"],
                        "sha256": artifact["sha256"],
                    }
                )
        assert len(collected) == len(source_rows)
        assert not (audit_root / "worlds" / state["id"]).exists()
        assert not state["workpapers"] and not state["findings"] and not state["populations"]
        assert all(t["status"] == "NOT_STARTED" for t in state["tasks"])
        for system in systems:
            store.grant(actor, state["id"], source_recipe.company_id, branch, system, active=False)
        receipts.append(
            {
                "branch": branch,
                "engagement_id": state["id"],
                "collected": collected,
                "revision": state["revision"],
                "future_release_denied": True,
                "all_replays_identical": True,
                "testing_credit": False,
                "generated_world": False,
            }
        )
    assert rows(store) == originals
    return {
        "status": "PASS",
        "branches": receipts,
        "source_versions_unchanged": True,
        "temporary_grants_revoked": True,
        "no_professional_conclusions": True,
    }


def test_actual_paired_change_collection(tmp_path):
    tmp_path.chmod(0o700)
    r = recipe()
    generate_pair(tmp_path / "company", repository=ROOT, recipe=r)
    result = collect_pair(tmp_path / "company", tmp_path / "audit", source_recipe=r)
    assert result["status"] == "PASS" and len(result["branches"]) == 2
    assert len(result["branches"][1]["collected"]) == len(result["branches"][0]["collected"]) + 2
