"""Actual persistent local target changes, source authorization and failure boundaries."""

import subprocess
import sys

import pytest

from enterprise.audit_suite import company_configuration_runtime as runtime
from enterprise.audit_suite.company_backup_runtime import database, pin
from enterprise.audit_suite.company_change_activity import generate_pair
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded
from tests.audit_suite.test_company_change_activity import ROOT, recipe


@pytest.fixture
def ready(tmp_path):
    tmp_path.chmod(0o700)
    source = tmp_path / "source"
    generate_pair(source, repository=ROOT, recipe=recipe())
    names = {
        "baseline": "CONFIG-BASELINE",
        "configuration": "CONFIG-CORRECTED",
        "build": "BUILD-CORRECTED",
        "tests": "TEST-CORRECTED",
        "review": "REVIEW-CORRECTED",
        "gate": "GATE-CORRECTED",
        "rollback_plan": "ROLLBACK-PLAN",
    }
    with database(source) as db:
        refs = {
            slot: pin(
                db.execute(
                    "SELECT * FROM versions WHERE branch=? AND record=?", ("release-a", name)
                ).fetchone()
            )
            for slot, name in names.items()
        }
    target = tmp_path / "runtime"
    initial = runtime.initialize(
        target,
        source_root=source,
        source_pins=refs,
        as_of="2027-02-02T00:00:00Z",
        target_id="LOCAL-TARGET",
    )
    return target, initial, source, refs


def command(ready, operation, identifier, **changes):
    root, initial, *_ = ready
    state = runtime.inspect(root, expected_runtime_sha256=initial["runtime_sha256"])
    cfg = runtime._config(root, initial["runtime_sha256"])
    args = dict(
        expected_runtime_sha256=initial["runtime_sha256"],
        expected_revision=state["revision"],
        command_id=identifier,
        operation=operation,
        expected_current_sha256=state["current_sha256"],
        operator_id=cfg["operator_id"],
        event_at="2027-02-03T00:00:00Z",
        rationale="Explicit local exercise operation",
    )
    if operation in ("APPLY", "ROLLBACK"):
        args["expected_target_sha256"] = cfg[
            "approved_sha256" if operation == "APPLY" else "baseline_sha256"
        ]
    return {**args, **changes}


def snapshot(root):
    with database(root) as db:
        return {
            t: [tuple(r) for r in db.execute("SELECT * FROM " + t)]
            for t in (
                "versions",
                "configuration_state",
                "configuration_commands",
                "grants",
                "collections",
            )
        }


def test_apply_drift_observe_correct_rollback_survives_new_process(ready):
    root, initial, source, _ = ready
    original = (source / "company.sqlite3").read_bytes()
    approved = runtime.execute(root, **command(ready, "APPLY", "apply"))
    assert approved["prior_sha256"] != approved["current_sha256"]
    drift = {"timeout_ms": 50, "attempts": 3, "max_total_ms": 120}
    runtime.execute(root, **command(ready, "DRIFT", "drift", configuration=drift))
    observation = runtime.execute(root, **command(ready, "RECONCILE", "observe"))
    assert observation["field_differences"] == [
        {"field": "timeout_ms", "actual": 50, "approved": 40}
    ]
    assert not observation["bytes_match_approved"]
    assert observation["automatic_ticket_closure"] is False
    runtime.execute(root, **command(ready, "APPLY", "correct"))
    assert runtime.execute(root, **command(ready, "RECONCILE", "retest"))["field_differences"] == []
    rollback = runtime.execute(root, **command(ready, "ROLLBACK", "rollback"))
    assert rollback["current_sha256"] == initial["current_sha256"]
    script = (
        "import sys,json; from enterprise.audit_suite.company_configuration_runtime import inspect;"
        "print(json.dumps(inspect(sys.argv[1], expected_runtime_sha256=sys.argv[2])))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(root), initial["runtime_sha256"]],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert '"timeout_ms": 30' in result.stdout
    assert (source / "company.sqlite3").read_bytes() == original
    assert snapshot(root)["grants"] == snapshot(root)["collections"] == []


def test_exact_replay_stale_revision_operator_and_type_reject(ready):
    root, *_ = ready
    args = command(ready, "APPLY", "once")
    result = runtime.execute(root, **args)
    before = snapshot(root)
    assert runtime.execute(root, **args) == result
    for changed in ({"rationale": "Changed"}, {"command_id": "stale"}, {"operator_id": "OTHER"}):
        with pytest.raises(CompanyStoreError):
            runtime.execute(root, **{**args, **changed})
    with pytest.raises(CompanyStoreError):
        runtime.execute(
            root,
            **command(
                ready,
                "DRIFT",
                "bool",
                configuration={"timeout_ms": True, "attempts": 3, "max_total_ms": 120},
            ),
        )
    assert snapshot(root) == before


def test_failed_native_insert_keeps_current_pointer_and_orphan_noncurrent(ready, monkeypatch):
    root, *_ = ready
    before = snapshot(root)
    real = runtime._insert

    def fail(*args, **kwargs):
        real(*args, **kwargs)
        raise OSError("before commit")

    monkeypatch.setattr(runtime, "_insert", fail)
    with pytest.raises(OSError):
        runtime.execute(root, **command(ready, "APPLY", "interrupted"))
    assert snapshot(root) == before
    assert len(list((root / "objects").iterdir())) == 2
    assert (
        runtime.inspect(root, expected_runtime_sha256=ready[1]["runtime_sha256"])["revision"] == 0
    )


def test_corrupt_current_file_cannot_be_reconstructed_from_native_records(ready):
    root, initial, *_ = ready
    (root / "objects" / "initial.json").write_bytes(
        encoded({"timeout_ms": 31, "attempts": 3, "max_total_ms": 120})
    )
    with pytest.raises(CompanyStoreError, match="Current file integrity"):
        runtime.inspect(root, expected_runtime_sha256=initial["runtime_sha256"])


def test_source_cross_branch_and_future_gate_fail_before_publication(ready):
    root, _, source, refs = ready
    with pytest.raises(CompanyStoreError):
        runtime.initialize(
            root.parent / "future",
            source_root=source,
            source_pins=refs,
            as_of="2027-02-01T09:59:59Z",
            target_id="FUTURE",
        )
    altered = {**refs, "gate": {**refs["gate"], "branch": "release-b"}}
    with pytest.raises(CompanyStoreError):
        runtime.initialize(
            root.parent / "cross",
            source_root=source,
            source_pins=altered,
            as_of="2027-02-03T00:00:00Z",
            target_id="CROSS",
        )
    assert not (root.parent / "future").exists() and not (root.parent / "cross").exists()


@pytest.mark.parametrize("failure_call", [1, 2])
def test_file_or_directory_fsync_failure_never_publishes_current(ready, monkeypatch, failure_call):
    root, *_ = ready
    before = snapshot(root)
    real = runtime.os.fsync
    calls = 0

    def fail(fd):
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise OSError("injected durable file publication failure")
        return real(fd)

    monkeypatch.setattr(runtime.os, "fsync", fail)
    with pytest.raises(OSError):
        runtime.execute(root, **command(ready, "APPLY", "flush-failure"))
    assert snapshot(root) == before


def test_objects_parent_alias_never_writes_external_files(ready):
    root, initial, *_ = ready
    args = command(ready, "APPLY", "alias")
    (root / "objects").rename(root / "original-objects")
    external = root.parent / "external"
    external.mkdir(mode=0o700)
    (root / "objects").symlink_to(external, target_is_directory=True)
    with pytest.raises(CompanyStoreError):
        runtime.execute(root, **args)
    assert list(external.iterdir()) == []
    assert initial["revision"] == 0
