"""Independent durable-intent and native dependency regressions; disposable fixtures only."""

import sqlite3

import pytest

from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite import company_recovery_period as runner
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_recovery_period import period as period_fixture


@pytest.fixture
def period(tmp_path):
    return period_fixture.__wrapped__(tmp_path)


def run(root, created, steps, revision=0):
    results = []
    for step in steps:
        result = runner.execute_next(
            root,
            expected_runner_sha256=created["runner_sha256"],
            expected_revision=revision,
            step_id=step["id"],
        )
        revision = result["revision"]
        results.append(result)
    return results


def test_intent_committed_before_first_native_call_and_explicit_retry(period, monkeypatch):
    plan, root = period
    created = runner.create(root, plan=plan)
    invoke = runner._invoke

    def stop(*_):
        with sqlite3.connect(root / "runner.sqlite3") as db:
            assert db.execute("SELECT kind FROM journal").fetchone()[0] == "INTENT"
        raise OSError("Before native operation")

    monkeypatch.setattr(runner, "_invoke", stop)
    with pytest.raises(OSError):
        run(root, created, plan["steps"][:1])
    config = plan["bindings"]["configuration"]
    with backup.database(config["root"]) as db:
        assert db.execute("SELECT count(*) FROM configuration_commands").fetchone()[0] == 0
    pending = runner.inspect(root, expected_runner_sha256=created["runner_sha256"])
    monkeypatch.setattr(runner, "_invoke", invoke)
    result = runner.retry_pending(
        root,
        expected_runner_sha256=created["runner_sha256"],
        expected_revision=1,
        intent_sha256=pending["pending"]["sha256"],
    )
    assert result["revision"] == 2
    with backup.database(config["root"]) as db:
        assert db.execute("SELECT count(*) FROM configuration_commands").fetchone()[0] == 1


def test_rehashed_intent_cannot_change_plan_literal_before_retry(period, monkeypatch):
    plan, root = period
    created = runner.create(root, plan=plan)
    invoke = runner._invoke
    monkeypatch.setattr(
        runner, "_invoke", lambda *_: (_ for _ in ()).throw(OSError("Before native call"))
    )
    with pytest.raises(OSError):
        run(root, created, plan["steps"][:1])
    monkeypatch.setattr(runner, "_invoke", invoke)
    with sqlite3.connect(root / "runner.sqlite3") as db:
        db.execute("DROP TRIGGER no_journal_update")
        body = runner.decode(db.execute("SELECT content FROM journal").fetchone()[0])
        body["parameters"]["rationale"] = "Unauthorized replacement of reviewed plan literal"
        db.execute(
            "UPDATE journal SET content=?,sha256=?", (encoded(body).decode(), sha(encoded(body)))
        )
    with pytest.raises(CompanyStoreError):
        runner.retry_pending(
            root,
            expected_runner_sha256=created["runner_sha256"],
            expected_revision=1,
            intent_sha256=sha(encoded(body)),
        )
    with backup.database(plan["bindings"]["configuration"]["root"]) as db:
        assert db.execute("SELECT count(*) FROM configuration_commands").fetchone()[0] == 0


def test_apply_then_export_admit_preserves_actual_changed_bytes(period):
    plan, root = period
    plan = runner.decode(encoded(plan))
    c = plan["bindings"]["configuration"]
    cfg = runner.configuration._config(c["root"], c["runtime_sha256"])
    apply = {
        "id": "apply",
        "kind": "APPLY",
        "parameters": {
            "expected_revision": 0,
            "command_id": "apply",
            "expected_current_sha256": cfg["baseline_sha256"],
            "expected_target_sha256": cfg["approved_sha256"],
            "operator_id": cfg["operator_id"],
            "event_at": "2027-02-03T00:00:00Z",
            "rationale": "Explicit approved local target operation",
        },
        "refs": {},
        "expected_pins": {},
    }

    def replace_hash(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "sha256" and child == cfg["baseline_sha256"]:
                    value[key] = cfg["approved_sha256"]
                else:
                    replace_hash(child)
        elif isinstance(value, list):
            for child in value:
                replace_hash(child)

    replace_hash(plan["steps"])
    plan["steps"][0]["parameters"].update(
        expected_revision=1,
        expected_current_sha256=cfg["approved_sha256"],
        event_at="2027-02-03T00:00:30Z",
    )
    plan["steps"].insert(0, apply)
    created = runner.create(root, plan=plan)
    results = run(root, created, plan["steps"])
    assert results[0]["result"]["current_sha256"] == cfg["approved_sha256"]
    with backup.database(c["root"]) as db:
        exported = backup.native(db, results[1]["result"]["native_pin"])
    with backup.database(plan["bindings"]["backup"]["root"]) as db:
        admitted = backup.native(db, results[2]["result"]["source_pin"])
        assert admitted["content"] == exported["content"]
        assert admitted["sha256"] == cfg["approved_sha256"] != cfg["baseline_sha256"]


@pytest.mark.parametrize("version", [True, 1.0])
def test_native5_job_capture_strict_version_before_output(period, version):
    plan, root = period
    ref = {
        "step_id": "copy",
        "field": "job_pin",
        "sha256_policy": "CAPTURE_FROM_VERIFIED_PRODUCER_RESULT",
        "expected_identity": {
            "company": "LOCAL",
            "branch": "shared-local",
            "system": "backup_job",
            "record": "COPY",
            "version": version,
        },
    }
    plan["steps"][5]["refs"]["backup_pin"] = ref
    with pytest.raises(CompanyStoreError):
        runner.create(root, plan=plan)
    assert not root.exists()
    with backup.database(plan["bindings"]["configuration"]["root"]) as db:
        assert db.execute("SELECT count(*) FROM configuration_commands").fetchone()[0] == 0


def test_repeated_export_and_admission_keep_exact_prior_versions(period):
    from copy import deepcopy

    plan, root = period
    plan = runner.decode(encoded(plan))
    c = plan["bindings"]["configuration"]
    cfg = runner.configuration._config(c["root"], c["runtime_sha256"])
    second_export = deepcopy(plan["steps"][0])
    second_export["id"] = "export-second"
    second_export["parameters"].update(
        expected_revision=1, command_id="export-second", event_at="2027-02-03T00:01:30Z"
    )
    exported_pin = second_export["expected_pins"]["native_pin"]
    exported_pin["record"] = "EXPORT-" + sha(encoded([cfg["target_id"], "export-second"]))
    second_admit = deepcopy(plan["steps"][1])
    second_admit["id"] = "admit-second"
    second_admit["parameters"].update(
        expected_revision=1, command_id="admit-second", event_at="2027-02-03T00:01:40Z"
    )
    second_admit["parameters"].pop("previous_pin")
    second_admit["refs"]["previous_pin"] = {
        "step_id": "admit",
        "field": "source_pin",
        "expected_pin": deepcopy(plan["steps"][1]["expected_pins"]["source_pin"]),
    }
    second_admit["refs"]["source_pin"] = {
        "step_id": "export-second",
        "field": "native_pin",
        "expected_pin": deepcopy(exported_pin),
    }
    second_admit["expected_pins"]["source_pin"]["version"] = 2
    for step in plan["steps"][2:]:
        step["parameters"]["expected_revision"] += 1
        for reference in step["refs"].values():
            if reference["step_id"] == "admit":
                reference["step_id"] = "admit-second"
                reference["expected_pin"]["version"] = 2
    plan["steps"][2:2] = [second_export, second_admit]
    created = runner.create(root, plan=plan)
    results = run(root, created, plan["steps"])
    with backup.database(plan["bindings"]["backup"]["root"]) as db:
        first = backup.native(db, results[1]["result"]["source_pin"])
        second = backup.native(db, results[3]["result"]["source_pin"])
        assert first["version"] == 1 and second["version"] == 2
        assert first["content"] == second["content"]
        assert (
            runner.decode(first["provenance"])["source_admission"]["source_pin"]
            != runner.decode(second["provenance"])["source_admission"]["source_pin"]
        )
        assert db.execute("SELECT count(*) FROM grants").fetchone()[0] == 0
    assert (
        runner.inspect(root, expected_runner_sha256=created["runner_sha256"])["status"]
        == "COMPLETE"
    )


def test_rehashed_completed_result_cannot_authorize_next_consumer(period):
    plan, root = period
    created = runner.create(root, plan=plan)
    run(root, created, plan["steps"][:1])
    with sqlite3.connect(root / "runner.sqlite3") as db:
        db.execute("DROP TRIGGER no_journal_update")
        result = runner.decode(
            db.execute("SELECT content FROM journal WHERE kind='RESULT'").fetchone()[0]
        )
        result["result"]["revision"] = 999
        db.execute(
            "UPDATE journal SET content=?,sha256=? WHERE kind='RESULT'",
            (encoded(result).decode(), sha(encoded(result))),
        )
    with pytest.raises(CompanyStoreError):
        runner.execute_next(
            root,
            expected_runner_sha256=created["runner_sha256"],
            expected_revision=2,
            step_id="admit",
        )
    with backup.database(plan["bindings"]["backup"]["root"]) as db:
        assert db.execute("SELECT count(*) FROM backup_runtime_commands").fetchone()[0] == 0


def test_lost_result_response_retains_completed_journal_without_duplicate_operation(
    period, monkeypatch
):
    plan, root = period
    created = runner.create(root, plan=plan)
    append = runner._append

    def lost(db, kind, value, seq):
        result = append(db, kind, value, seq)
        if kind == "RESULT":
            raise OSError("Response lost after durable result")
        return result

    monkeypatch.setattr(runner, "_append", lost)
    with pytest.raises(OSError):
        run(root, created, plan["steps"][:1])
    monkeypatch.setattr(runner, "_append", append)
    view = runner.inspect(root, expected_runner_sha256=created["runner_sha256"])
    assert (
        view["revision"] == 2 and view["completed_steps"] == ["export"] and view["pending"] is None
    )
    with pytest.raises(CompanyStoreError):
        runner.retry_pending(
            root,
            expected_runner_sha256=created["runner_sha256"],
            expected_revision=2,
            intent_sha256="0" * 64,
        )
    with backup.database(plan["bindings"]["configuration"]["root"]) as db:
        assert db.execute("SELECT count(*) FROM configuration_commands").fetchone()[0] == 1
