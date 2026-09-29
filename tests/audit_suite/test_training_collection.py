"""Actual paired Engine collection; local course facts never award testing credit."""

from pathlib import Path

from enterprise.audit_suite.company_collection import discover
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.company_training_activity import generate_pair
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.store import DomainError, canonical, digest
from tests.audit_suite.test_company_training_activity import ROOT, recipe


def collect_pair(company_root: Path, audit_root: Path, *, source_recipe, program_pack=None):
    source = CompanyStore(company_root)
    with source._db() as db:
        originals = [
            dict(r) for r in db.execute("SELECT * FROM versions ORDER BY branch,system,record")
        ]
    pin = digest([{k: v for k, v in r.items() if k != "content"} for r in originals])
    for system in ("training_roster", "training_matrix", "training_assignments"):
        paired = {
            branch: {
                r["record"]: r["content"]
                for r in originals
                if r["branch"] == branch and r["system"] == system
            }
            for branch in (source_recipe.on_time_branch, source_recipe.late_branch)
        }
        assert paired[source_recipe.on_time_branch] == paired[source_recipe.late_branch]
    e = Engine(audit_root, repository=ROOT, company_root=company_root, program_pack=program_pack)
    operator = e.store.provision("Isolated training source operator", ["instructor"])["id"]
    learner = e.store.provision("Isolated training source learner", ["learner"])["id"]
    branch_results = []
    for branch in (source_recipe.on_time_branch, source_recipe.late_branch):
        state = e.create(
            operator,
            {
                "command_id": "create-" + branch,
                "title": "Local training source investigation " + branch,
                "discipline": "IT",
                "mode": "CLEAN",
                "configuration": {"selections": []},
                "scope": {
                    "programs": ["SOC2", "HIPAA"],
                    "report_type": "Type 2",
                    "period_start": "2027-01-01",
                    "period_end": "2027-02-28",
                    "fieldwork_start": "2027-01-31",
                    "timezone": "UTC",
                    "boundaries": ["corporate"],
                    "control_ids": ["SH-TRN-001", "SH-TRN-002"],
                    "trust_services_categories": ["Security"],
                    "hipaa_role": "BUSINESS_ASSOCIATE",
                },
            },
        )
        e.store.grant(state["id"], learner, "learn")
        e.company_bindings[state["id"]] = {"company": source_recipe.company_id, "branch": branch}
        source_rows = [r for r in originals if r["branch"] == branch]
        systems = sorted({r["system"] for r in source_rows})
        # All six systems registered, even the branch with no follow-up records.
        with source._db() as db:
            registered = [
                dict(r) for r in db.execute("SELECT * FROM systems WHERE branch=?", (branch,))
            ]
        for system in registered:
            source.grant(learner, state["id"], source_recipe.company_id, branch, system["system"])
        serial = 0

        def cmd(kind, payload, actor=learner, branch=branch):
            nonlocal state, serial
            serial += 1
            envelope = {
                "command_id": branch + "-" + str(serial),
                "expected_revision": state["revision"],
                "kind": kind,
                "payload": payload,
            }
            state = e.command(actor, state["id"], envelope)
            return envelope

        cmd("company.activate", {}, operator)
        cmd("kickoff.start", {})
        requests = {}
        for control in state["controls"]:
            cmd(
                "pbc.create",
                {
                    "title": "Local training source records " + control["id"],
                    "purpose": (
                        "Inspect declared cohort, requirements and dated source records; "
                        "no testing conclusion."
                    ),
                    "control_id": control["id"],
                    "person_id": control["assignment"]["primary_person_id"],
                    "boundary_id": "corporate",
                },
            )
            requests[control["id"]] = state["requests"][-1]["id"]
            cmd("pbc.issue", {"request_id": state["requests"][-1]["id"]})
        cmd("clock.advance", {"mode": "TARGET_DATE", "target": "2027-01-31T18:00:00Z"})
        rejected = False
        if branch == source_recipe.late_branch:
            before = state["revision"]
            future_record = (
                source_recipe.cycle_id
                + "-"
                + source_recipe.late_person_id
                + "-"
                + source_recipe.late_course_id
            )
            try:
                cmd(
                    "company.collect",
                    {
                        "system_id": "training_completions",
                        "record_id": future_record,
                        "version": 1,
                        "request_id": requests["SH-TRN-002"],
                    },
                )
            except DomainError as error:
                assert error.status == 403
                rejected = True
            assert rejected and e.store.get(learner, state["id"])["revision"] == before
        seen = set()
        first = None
        for checkpoint in ("2027-01-31T18:00:00Z", "2027-02-03T11:00:00Z"):
            if checkpoint != "2027-01-31T18:00:00Z":
                cmd("clock.advance", {"mode": "TARGET_DATE", "target": checkpoint})
            for system in systems:
                visible = discover(e, learner, state["id"], system, limit=1000)
                for row in visible["records"]:
                    if (system, row["record"]) in seen:
                        continue
                    cid = (
                        "SH-TRN-001"
                        if system in {"training_roster", "training_matrix", "training_assignments"}
                        else "SH-TRN-002"
                    )
                    envelope = cmd(
                        "company.collect",
                        {
                            "system_id": system,
                            "record_id": row["record"],
                            "version": row["version"],
                            "request_id": requests[cid],
                        },
                    )
                    assert canonical(e.command(learner, state["id"], envelope)) == canonical(state)
                    artifact = state["artifacts"][-1]
                    original = next(
                        r
                        for r in source_rows
                        if (r["system"], r["record"]) == (system, row["record"])
                    )
                    assert e.artifacts.read(artifact) == original["content"]
                    assert artifact["sha256"] == original["sha256"]
                    assert artifact["coverage"]["professional_sufficiency"] == "NOT_ASSERTED"
                    seen.add((system, row["record"]))
            if first is None:
                first = len(seen)
        assert len(seen) == len(source_rows)
        assert not (audit_root / "worlds" / state["id"]).exists()
        assert not state["workpapers"] and not state["findings"] and not state["populations"]
        assert all(t["status"] == "NOT_STARTED" for t in state["tasks"])
        branch_results.append(
            {
                "branch": branch,
                "engagement_id": state["id"],
                "first_checkpoint_collected": first,
                "final_collected": len(seen),
                "future_completion_denied": rejected
                if branch == source_recipe.late_branch
                else "NOT_APPLICABLE",
                "all_original_bytes_verified": True,
                "every_collection_replay_verified": True,
                "generated_world": False,
                "testing_credit": False,
                "revision": state["revision"],
                "source_pin": pin,
            }
        )
    with source._db() as db:
        after = [
            dict(r) for r in db.execute("SELECT * FROM versions ORDER BY branch,system,record")
        ]
    assert digest([{k: v for k, v in r.items() if k != "content"} for r in after]) == pin
    return {
        "status": "PASS",
        "source_versions_unchanged": True,
        "identical_cohort_matrix_and_assignments": True,
        "source_versions_sha256": pin,
        "branches": branch_results,
        "recorded_at_semantics": (
            "Actual metadata only; no real employment or accepted policy asserted"
        ),
    }


def test_actual_paired_training_collection(tmp_path):
    tmp_path.chmod(0o700)
    r = recipe()
    generate_pair(tmp_path / "company", repository=ROOT, recipe=r)
    result = collect_pair(tmp_path / "company", tmp_path / "audit", source_recipe=r)
    assert [b["final_collected"] for b in result["branches"]] == [14, 15]
    assert result["branches"][1]["future_completion_denied"] is True
    assert result["source_versions_unchanged"]
