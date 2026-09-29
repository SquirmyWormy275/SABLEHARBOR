"""Durable runner commands over actual disposable configuration and backup runtimes."""

import copy

import pytest

from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite import company_recovery_period as runner
from enterprise.audit_suite.company_operating_period import create_period
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.organization import snapshot
from tests.audit_suite.test_company_backup_runtime import ROOT
from tests.audit_suite.test_company_configuration_runtime import ready


@pytest.fixture
def period(tmp_path):
    producer = tmp_path / "producer"
    producer.mkdir(mode=0o700)
    config = ready.__wrapped__(producer)
    croot, initial, *_ = config
    ccfg = runner.configuration._config(croot, initial["runtime_sha256"])
    ledger = tmp_path / "ledger"
    ledger.mkdir(mode=0o700)
    owner = next(
        r
        for r in snapshot(ROOT, as_of="2027-01-01")["control_assignments"]
        if r["control_id"] == "SH-BCM-003"
    )["primary_person_id"]
    schedule = []
    for name, control in [
        ("COPY", "SH-BCM-002"),
        ("RESTORE", "SH-BCM-003"),
        ("OMITTED", "SH-BCM-002"),
    ]:
        schedule.append(
            {
                "id": name,
                "inventory_ids": ["DATA"],
                "control_id": control,
                "window_start": "2027-02-03T00:00:00Z",
                "window_end_exclusive": "2027-02-05T00:00:00Z",
                "due_at": "2027-02-04T00:00:00Z",
                "depends_on": [],
            }
        )
    declaration = create_period(
        CompanyStore(ledger),
        repository=ROOT,
        plan={
            "period_id": "PERIOD",
            "company_id": "LOCAL",
            "branch_id": "shared-local",
            "owner_id": owner,
            "control_ids": ["SH-BCM-002", "SH-BCM-003"],
            "period_start": "2027-02-03T00:00:00Z",
            "period_end_exclusive": "2027-02-05T00:00:00Z",
            "declared_at": "2027-02-02T00:00:00Z",
            "inventory": [{"id": "DATA", "description": "Local configuration byte object"}],
            "local_basis": "Explicit local occurrences, no RPO or hosting equivalence",
            "schedule": schedule,
        },
    )
    broot = tmp_path / "backup"
    binit = backup.initialize(
        broot,
        repository=ROOT,
        declaration_root=ledger,
        declaration_ref=backup.pin(declaration),
        datasets=[{"id": "DATA", "format": "BYTES"}],
        bindings=[
            {
                "occurrence_id": x["id"],
                "dataset_id": "DATA",
                "operation": "RESTORE" if x["id"] == "RESTORE" else "BACKUP",
            }
            for x in schedule
        ],
    )
    bcfg = backup._config(broot, binit["runtime_sha256"])
    with backup.database(croot) as db:
        definition = backup.pin(
            db.execute("SELECT * FROM versions WHERE system='configuration_runtime'").fetchone()
        )
    export_pin = {
        "company": ccfg["company"],
        "branch": ccfg["branch"],
        "system": "configuration_export",
        "record": "EXPORT-" + sha(encoded([ccfg["target_id"], "export"])),
        "version": 1,
        "sha256": ccfg["baseline_sha256"],
    }
    dataset_pin = {
        "company": "LOCAL",
        "branch": "shared-local",
        "system": "source_dataset",
        "record": "DATA",
        "version": 1,
        "sha256": export_pin["sha256"],
    }

    def step(id, kind, parameters, refs=None, expected=None):
        return {
            "id": id,
            "kind": kind,
            "parameters": parameters,
            "refs": refs or {},
            "expected_pins": expected or {},
        }

    def ref(id, field, pin):
        return {"step_id": id, "field": field, "expected_pin": pin}

    steps = [
        step(
            "export",
            "EXPORT",
            {
                "expected_revision": 0,
                "command_id": "export",
                "expected_current_sha256": ccfg["baseline_sha256"],
                "operator_id": ccfg["operator_id"],
                "event_at": "2027-02-03T00:00:00Z",
                "rationale": "Explicit local opening state export",
            },
            expected={"native_pin": export_pin},
        ),
        step(
            "admit",
            "ADMIT",
            {
                "expected_revision": 0,
                "command_id": "admit",
                "dataset_id": "DATA",
                "operator_id": bcfg["operator_id"],
                "event_at": "2027-02-03T00:01:00Z",
                "previous_pin": None,
                "metadata_capture": "CAPTURE_EXACT_ONCE",
            },
            {"source_pin": ref("export", "native_pin", export_pin)},
            {"source_pin": dataset_pin},
        ),
    ]
    leases = {}
    for i, op in enumerate(["BACKUP_WRITE", "RESTORE_READ"], 1):
        body = {
            "operation": op,
            "enabled": True,
            "valid_from": "2027-02-03T00:00:00.000000+00:00",
            "expires_at": "2027-02-05T00:00:00.000000+00:00",
            "authority": "LOCAL_ADAPTER_ENFORCEMENT_NOT_CLOUD_CREDENTIAL_OR_PHYSICAL_ISOLATION",
            "principal_id": bcfg["operator_id"],
        }
        pin = {
            "company": "LOCAL",
            "branch": "shared-local",
            "system": "credential_event",
            "record": op,
            "version": 1,
            "sha256": sha(encoded(body)),
        }
        leases[op] = pin
        steps.append(
            step(
                op,
                "LEASE",
                {
                    "expected_revision": i,
                    "command_id": op,
                    "operation": op,
                    "enabled": True,
                    "valid_from": "2027-02-03T00:00:00Z",
                    "expires_at": "2027-02-05T00:00:00Z",
                    "event_at": f"2027-02-03T00:0{i + 1}:00Z",
                    "previous_pin": None,
                },
                expected={"lease_pin": pin},
            )
        )
    copied = {**dataset_pin, "system": "backup_object", "record": "COPY"}
    steps.append(
        step(
            "copy",
            "BACKUP",
            {
                "expected_revision": 3,
                "command_id": "copy",
                "occurrence_id": "COPY",
                "attempted_at": "2027-02-03T01:00:00Z",
                "rationale": "Explicit local protected dataset",
                "prior_attempt_pin": None,
            },
            {
                "source_pin": ref("admit", "source_pin", dataset_pin),
                "lease_pin": ref("BACKUP_WRITE", "lease_pin", leases["BACKUP_WRITE"]),
            },
            {"object_pin": copied},
        )
    )
    steps.append(
        step(
            "restore",
            "RESTORE",
            {
                "expected_revision": 4,
                "command_id": "restore",
                "occurrence_id": "RESTORE",
                "attempted_at": "2027-02-03T02:00:00Z",
                "rationale": "Explicit selected checkpoint retest",
                "prior_attempt_pin": None,
            },
            {
                "backup_pin": ref("copy", "object_pin", copied),
                "comparison_source_pin": ref("admit", "source_pin", dataset_pin),
                "lease_pin": ref("RESTORE_READ", "lease_pin", leases["RESTORE_READ"]),
            },
            {"object_pin": {**dataset_pin, "system": "restored_dataset", "record": "RESTORE"}},
        )
    )
    steps.append(
        step(
            "monitor",
            "MONITOR",
            {
                "expected_revision": 5,
                "command_id": "monitor",
                "as_of": "2027-02-04T01:00:00Z",
                "recorded_at": "2027-02-04T02:00:00Z",
                "operator_id": bcfg["operator_id"],
                "rationale": "Inspect declared missing due occurrence",
                "jobs_capture": "CAPTURE_EXACT_ONCE",
            },
        )
    )
    plan = {
        "format": runner.FORMAT,
        "id": "RUN",
        "period_id": "PERIOD",
        "bindings": {
            "configuration": {
                "root": str(croot),
                "runtime_sha256": initial["runtime_sha256"],
                "revision": 0,
                "current_sha256": ccfg["baseline_sha256"],
                "definition_pin": definition,
            },
            "backup": {
                "root": str(broot),
                "runtime_sha256": binit["runtime_sha256"],
                "revision": 0,
            },
        },
        "omissions": [
            {"occurrence_id": "OMITTED", "reason": "Explicit omitted local copy remains due"}
        ],
        "steps": steps,
    }
    return plan, tmp_path / "runner"


def test_real_period_source_chain_and_independent_missing_denominator(period):
    plan, root = period
    created = runner.create(root, plan=plan)
    revision = 0
    results = []
    for step in plan["steps"]:
        result = runner.execute_next(
            root,
            expected_runner_sha256=created["runner_sha256"],
            expected_revision=revision,
            step_id=step["id"],
        )
        revision = result["revision"]
        results.append(result)
    assert (
        runner.inspect(root, expected_runner_sha256=created["runner_sha256"])["status"]
        == "COMPLETE"
    )
    b = plan["bindings"]["backup"]
    report = backup.reconcile(
        b["root"], expected_runtime_sha256=b["runtime_sha256"], as_of="2027-02-05T00:00:00Z"
    )
    assert report["due_count"] == 3 and report["missing_due_count"] == 1
    assert (
        results[1]["result"]["dependency"]["source_pin"]
        == plan["steps"][0]["expected_pins"]["native_pin"]
    )
    with backup.database(b["root"]) as db:
        restored = backup.native(db, results[5]["result"]["object_pin"])
        admitted = backup.native(db, results[1]["result"]["source_pin"])
        assert restored["content"] == admitted["content"]
        assert db.execute("SELECT count(*) FROM grants").fetchone()[0] == 0


def test_interrupted_producer_commit_requires_exact_pending_retry(period, monkeypatch):
    plan, root = period
    created = runner.create(root, plan=plan)
    original = runner._invoke

    def interrupted(*a):
        original(*a)
        raise OSError("Lost outer receipt after committed producer")

    monkeypatch.setattr(runner, "_invoke", interrupted)
    with pytest.raises(OSError):
        runner.execute_next(
            root,
            expected_runner_sha256=created["runner_sha256"],
            expected_revision=0,
            step_id="export",
        )
    view = runner.inspect(root, expected_runner_sha256=created["runner_sha256"])
    assert view["revision"] == 1 and view["status"] == "PENDING_EXPLICIT_RETRY"
    with pytest.raises(CompanyStoreError):
        runner.execute_next(
            root,
            expected_runner_sha256=created["runner_sha256"],
            expected_revision=1,
            step_id="export",
        )
    monkeypatch.setattr(runner, "_invoke", original)
    result = runner.retry_pending(
        root,
        expected_runner_sha256=created["runner_sha256"],
        expected_revision=1,
        intent_sha256=view["pending"]["sha256"],
    )
    assert result["revision"] == 2
    with backup.database(plan["bindings"]["configuration"]["root"]) as db:
        assert db.execute("SELECT count(*) FROM configuration_commands").fetchone()[0] == 1
        assert (
            db.execute(
                "SELECT count(*) FROM versions WHERE system='configuration_export'"
            ).fetchone()[0]
            == 1
        )


@pytest.mark.parametrize(
    "case", ["unaccounted", "unknown_kind", "future_ref", "arbitrary_path", "duplicate_command"]
)
def test_plan_rejection_before_journal_or_company_operations(period, case):
    plan, root = period
    plan = copy.deepcopy(plan)
    if case == "unaccounted":
        plan["omissions"] = []
    if case == "unknown_kind":
        plan["steps"][0]["kind"] = "EXEC"
    if case == "future_ref":
        plan["steps"][1]["refs"]["source_pin"]["step_id"] = "copy"
    if case == "arbitrary_path":
        plan["steps"][0]["parameters"]["root"] = "/tmp/other"
    if case == "duplicate_command":
        plan["steps"][2]["parameters"]["command_id"] = "admit"
    with pytest.raises(CompanyStoreError):
        runner.create(root, plan=plan)
    assert not root.exists()
    with backup.database(plan["bindings"]["configuration"]["root"]) as db:
        assert db.execute("SELECT count(*) FROM configuration_commands").fetchone()[0] == 0


def test_measured_job_hash_captured_once_and_retry_preserves_first_attempt(period):
    plan, root = period
    first = copy.deepcopy(plan["steps"][4])
    retry = copy.deepcopy(first)
    retry["id"] = "copy-retry"
    retry["parameters"].update(
        expected_revision=4, command_id="copy-retry", attempted_at="2027-02-03T01:30:00Z"
    )
    retry["parameters"].pop("prior_attempt_pin")
    retry["refs"]["prior_attempt_pin"] = {
        "step_id": "copy",
        "field": "job_pin",
        "sha256_policy": "CAPTURE_FROM_VERIFIED_PRODUCER_RESULT",
        "expected_identity": {
            "company": "LOCAL",
            "branch": "shared-local",
            "system": "backup_job",
            "record": "COPY",
            "version": 1,
        },
    }
    retry["expected_pins"]["object_pin"]["version"] = 2
    plan["steps"].insert(5, retry)
    plan["steps"][6]["parameters"]["expected_revision"] += 1
    plan["steps"][7]["parameters"]["expected_revision"] += 1
    created = runner.create(root, plan=plan)
    results = []
    revision = 0
    for step in plan["steps"][:6]:
        result = runner.execute_next(
            root,
            expected_runner_sha256=created["runner_sha256"],
            expected_revision=revision,
            step_id=step["id"],
        )
        results.append(result["result"])
        revision = result["revision"]
    assert results[5]["job_pin"]["version"] == 2
    with runner._locked(root) as db:
        rows = db.execute("SELECT content FROM journal WHERE kind='INTENT' ORDER BY seq").fetchall()
    final = runner.decode(rows[-1][0])
    assert final["parameters"]["prior_attempt_pin"] == results[4]["job_pin"]
    assert (
        final["captured"]["native_refs"]["prior_attempt_pin"]["policy"]
        == "CAPTURE_FROM_VERIFIED_PRODUCER_RESULT"
    )
    with backup.database(plan["bindings"]["backup"]["root"]) as db:
        assert backup.native(db, results[4]["job_pin"])["version"] == 1


def test_changed_code_pin_and_stale_opening_prevent_execution(period, monkeypatch):
    plan, root = period
    created = runner.create(root, plan=plan)
    original = runner._code
    monkeypatch.setattr(runner, "_code", lambda: {**original(), "unexpected": "0" * 64})
    with pytest.raises(CompanyStoreError, match="implementation"):
        runner.execute_next(
            root,
            expected_runner_sha256=created["runner_sha256"],
            expected_revision=0,
            step_id="export",
        )
    monkeypatch.setattr(runner, "_code", original)
    params = plan["steps"][0]["parameters"]
    runner.export.export_current(
        plan["bindings"]["configuration"]["root"],
        expected_runtime_sha256=plan["bindings"]["configuration"]["runtime_sha256"],
        **params,
    )
    with pytest.raises(CompanyStoreError, match="opening"):
        runner.execute_next(
            root,
            expected_runner_sha256=created["runner_sha256"],
            expected_revision=0,
            step_id="export",
        )
    assert runner.inspect(root, expected_runner_sha256=created["runner_sha256"])["revision"] == 0


def test_runner_lock_and_changed_intent_retry_reject(period):
    plan, root = period
    created = runner.create(root, plan=plan)
    with runner._locked(root):
        with pytest.raises(CompanyStoreError, match="busy"):
            runner.execute_next(
                root,
                expected_runner_sha256=created["runner_sha256"],
                expected_revision=0,
                step_id="export",
            )
    with pytest.raises(CompanyStoreError):
        runner.retry_pending(
            root,
            expected_runner_sha256=created["runner_sha256"],
            expected_revision=0,
            intent_sha256="0" * 64,
        )


def test_runner_connections_close_after_create_read_and_error(period, monkeypatch):
    import sqlite3

    plan, root = period
    original = runner.sqlite3.connect
    connections = []

    def tracked(path, *a, **kw):
        connection = original(path, *a, **kw)
        if "runner.sqlite3" in str(path):
            connections.append(connection)
        return connection

    monkeypatch.setattr(runner.sqlite3, "connect", tracked)
    created = runner.create(root, plan=plan)
    runner.inspect(root, expected_runner_sha256=created["runner_sha256"])

    def failed(*a, **kw):
        raise CompanyStoreError("Injected journal validation failure")

    monkeypatch.setattr(runner, "_load", failed)
    with pytest.raises(CompanyStoreError):
        runner.inspect(root, expected_runner_sha256=created["runner_sha256"])
    with pytest.raises(CompanyStoreError):
        runner.execute_next(
            root,
            expected_runner_sha256=created["runner_sha256"],
            expected_revision=0,
            step_id="export",
        )
    assert len(connections) == 4
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")
