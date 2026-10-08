"""One new writer/caller journey; producer/helper semantics are prior gates."""

import copy
import json
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from tests.audit_suite import test_source_native_operating_methods as recipe
from tools.audit_suite.native_qualified_fieldwork import (
    NativeSupplementInterrupted,
    perform_native_supplement,
)

ROOT = Path(__file__).resolve().parents[2]


def prepare(root, target):
    """Reuse genuine prior source recipe, before any new Engine collection."""
    store = CompanyStore(root)
    with store._db() as db:
        originals = [
            dict(r) for r in db.execute("SELECT * FROM versions ORDER BY system,record,version")
        ]
    scope = {k: originals[0][k] for k in ("company", "branch")}
    engine = Engine(target, repository=ROOT, company_root=root)
    operator = engine.store.provision("Owned operator", ["instructor"])["id"]
    auditor = engine.store.provision("Owned learner", ["learner"])["id"]
    state = engine.create(
        operator,
        {
            "command_id": "OWN-NATIVE-WRITER-BIRTH",
            "title": "Owned qualified native caller",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {"selections": []},
            "scope": {
                "programs": ["SOC2"],
                "report_type": "Type 2",
                "period_start": "2027-01-01",
                "period_end": "2027-12-31",
                "fieldwork_start": "2028-01-18",
                "timezone": "UTC",
                "boundaries": ["corporate"],
                "control_ids": ["SH-POL-001"],
            },
        },
    )
    engagement = state["id"]
    engine.store.grant(engagement, auditor, "learn")
    engine.company_bindings[engagement] = scope
    for system in {r["system"] for r in originals}:
        store.grant(auditor, engagement, scope["company"], scope["branch"], system)

    def command(actor, kind, payload):
        state = engine.store.get(actor, engagement)
        return engine.command(
            actor,
            engagement,
            {
                "command_id": "OWN-PREP-" + str(state["revision"]),
                "expected_revision": state["revision"],
                "kind": kind,
                "payload": payload,
            },
        )

    command(operator, "company.activate", {})
    command(auditor, "kickoff.start", {})
    command(auditor, "clock.advance", {"mode": "TARGET_DATE", "target": recipe.AS_OF})
    state = command(
        auditor,
        "pbc.create",
        {
            "title": "Exact source dependency originals",
            "purpose": "Qualified local examination",
            "control_id": "SH-POL-001",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    request_id = state["requests"][-1]["id"]
    state = command(auditor, "pbc.issue", {"request_id": request_id})
    assert not state["artifacts"] and not state["workpapers"] and not state["findings"]
    return engine, auditor, engagement, request_id, originals


def test_exact_native_acquisition_qualified_writer_and_partial_boundary(
    tmp_path_factory, tmp_path, monkeypatch
):
    # Only the test's audit preparation changes; producer APIs run unchanged.
    monkeypatch.setattr(recipe, "collect", prepare)
    engine, auditor, engagement, request_id, originals = recipe.policy_rows.__wrapped__(
        tmp_path_factory
    )
    refs = [{k: r[k] for k in recipe.methods.PIN} for r in originals]
    state = engine.store.get(auditor, engagement)
    task_id = "TASK-SH-POL-001-corporate-TOE"
    arguments = dict(
        batch="B07",
        request_id=request_id,
        native_refs=refs,
        task_ids=[task_id],
        command_prefix="OWN-NATIVE-CALLER",
        expected_revision=state["revision"],
        scratch_root=tmp_path,
    )
    for changed in ({"expected_revision": state["revision"] - 1}, {"task_ids": ["TASK-FOREIGN"]}):
        with pytest.raises(ProcedureError):
            perform_native_supplement(engine, auditor, engagement, **{**arguments, **changed})
        assert engine.store.get(auditor, engagement) == state
    bad = copy.deepcopy(refs)
    bad[0]["sha256"] = "0" * 64
    with pytest.raises(ProcedureError):
        perform_native_supplement(engine, auditor, engagement, **{**arguments, "native_refs": bad})
    assert engine.store.get(auditor, engagement) == state
    result = perform_native_supplement(engine, auditor, engagement, **arguments)
    after = engine.store.get(auditor, engagement)
    assert result["status"] == "COMPLETED_QUALIFIED_NATIVE_SUPPLEMENT"
    assert len(result["commands"]) == len(refs) + 2
    assert [r["command"]["kind"] for r in result["commands"]][-2:] == [
        "workpaper.add",
        "task.update",
    ]
    assert len(after["artifacts"]) == len(refs) and len(after["workpapers"]) == 1
    version = after["workpapers"][-1]["versions"][-1]
    paper = json.loads(version["text"])
    assert paper["inspection"]["result"]["native_operating_attributes"]
    assert set(version["evidence_ids"]) == {r["artifact_id"] for r in paper["cited_originals"]}
    selected = next(t for t in after["tasks"] if t["id"] == task_id)
    assert selected["status"] == "IN_PROGRESS" and selected["conclusion"] == "FAIL"
    for field in (
        "populations",
        "selections",
        "sample_executions",
        "findings",
        "reviews",
        "controls",
    ):
        assert after[field] == state[field]
    assert [t for t in after["tasks"] if t["id"] != task_id] == [
        t for t in state["tasks"] if t["id"] != task_id
    ]
    with pytest.raises(ProcedureError):
        perform_native_supplement(engine, auditor, engagement, **arguments)
    with pytest.raises(ProcedureError):
        perform_native_supplement(
            engine, auditor, engagement, **{**arguments, "expected_revision": after["revision"]}
        )
    assert engine.store.get(auditor, engagement) == after

    normal_command = engine.command

    def interrupted(actor, eid, command):
        if command["kind"] == "task.update":
            raise RuntimeError("Owned deliberate interruption after durable WP")
        return normal_command(actor, eid, command)

    monkeypatch.setattr(engine, "command", interrupted)
    partial_arguments = {
        **arguments,
        "command_prefix": "OWN-NATIVE-PARTIAL",
        "expected_revision": after["revision"],
    }
    with pytest.raises(NativeSupplementInterrupted) as caught:
        perform_native_supplement(engine, auditor, engagement, **partial_arguments)
    partial = caught.value.receipt
    current = engine.store.get(auditor, engagement)
    assert partial["status"] == "INTERRUPTED_REQUIRING_JOURNAL_RECONCILIATION"
    assert partial["commands"][-1]["command"]["kind"] == "workpaper.add"
    assert partial["links"][-1]["task_update_completed"] is False
    assert len(current["workpapers"]) == 2 and current["tasks"] == after["tasks"]
    with pytest.raises(ProcedureError):
        perform_native_supplement(
            engine,
            auditor,
            engagement,
            **{**partial_arguments, "expected_revision": current["revision"]},
        )
    assert engine.store.get(auditor, engagement) == current
    # Real source originals remain exact; only normal collection journal/ACL is mutable.
    with engine.company_store._db() as db:
        final_originals = [
            dict(r) for r in db.execute("SELECT * FROM versions ORDER BY system,record,version")
        ]
    assert final_originals == originals


def test_postcommit_response_failure_keeps_attempt_even_when_revision_read_refuses(tmp_path):
    """Only receipt reporting: no SQL, source operations or successful writer rerun."""
    from types import SimpleNamespace

    from enterprise.audit_suite.store import digest

    task = "TASK-SH-POL-001-corporate-TOE"
    reference = {
        "company": "OWN-COMPANY",
        "branch": "OWN-BRANCH",
        "system": "business_inventory",
        "record": "OWN-RECORD",
        "version": 1,
        "sha256": "a" * 64,
    }
    for read_refuses in (False, True):
        state = {
            "id": "OWN-ENGAGEMENT",
            "revision": 7,
            "phase": "ACTIVE",
            "simulated_at": "2028-01-18T00:00:00+00:00",
            "tasks": [{"id": task, "control_id": "SH-POL-001"}],
            "requests": [{"id": "OWN-PBC", "status": "ISSUED"}],
            "workpapers": [],
        }
        attempted = []

        def get(actor, engagement, attempted=attempted, read_refuses=read_refuses, state=state):
            if attempted and read_refuses:
                raise RuntimeError("Owned integrity read refusal")
            return copy.deepcopy(state)

        def command(actor, engagement, value, attempted=attempted, state=state):
            attempted.append(copy.deepcopy(value))
            state["revision"] += 1  # Model a durable commit before response projection.
            raise RuntimeError("Owned postcommit projection failure")

        engine = SimpleNamespace(
            store=SimpleNamespace(get=get),
            company_store=SimpleNamespace(read_version=lambda *a, **kw: reference),
            company_bindings={"OWN-ENGAGEMENT": {"company": "OWN-COMPANY", "branch": "OWN-BRANCH"}},
            command=command,
        )
        with pytest.raises(NativeSupplementInterrupted) as caught:
            perform_native_supplement(
                engine,
                "OWN-LEARNER",
                "OWN-ENGAGEMENT",
                batch="B07",
                request_id="OWN-PBC",
                native_refs=[reference],
                task_ids=[task],
                command_prefix="OWN-RESPONSE-BOUNDARY",
                expected_revision=7,
                scratch_root=tmp_path,
            )
        receipt = caught.value.receipt
        assert len(attempted) == 1 and not receipt["commands"] and not receipt["links"]
        assert receipt["commands_extent"] == "CONFIRMED_RETURNED_RESPONSES_ONLY"
        assert receipt["unconfirmed_attempted_command"] == {
            "command": attempted[0],
            "request_sha256": digest(attempted[0]),
        }
        assert receipt["journal_reconciliation_required"] is True
        assert receipt["last_confirmed_returned_revision"] == 7
        assert receipt["current_revision"] == (None if read_refuses else 8)
        if read_refuses:
            assert receipt["current_revision_read_failure_type"] == "RuntimeError"
        assert receipt["status"] == "INTERRUPTED_REQUIRING_JOURNAL_RECONCILIATION"
