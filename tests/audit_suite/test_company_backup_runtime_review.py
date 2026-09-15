"""Independent backup runtime isolation, native integrity and atomicity checks."""

import json
import sqlite3

import pytest

from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_backup_runtime import ROOT, call, prepared
from tests.audit_suite.test_company_backup_runtime import runtime as runtime


def state(runtime):
    with backup.database(runtime[0]) as db:
        return {
            "versions": [
                tuple(r)
                for r in db.execute(
                    "SELECT * FROM versions ORDER BY company,branch,system,record,version"
                )
            ],
            "commands": [
                tuple(r)
                for r in db.execute("SELECT * FROM backup_runtime_commands ORDER BY command_id")
            ],
            "revision": [tuple(r) for r in db.execute("SELECT * FROM backup_runtime_state")],
        }


def test_re_pinned_other_runtime_configuration_cannot_relabel_database(runtime, tmp_path):
    cfg = json.loads((runtime[0] / "RUNTIME.json").read_bytes())
    other = tmp_path / "other-runtime"
    initialized = backup.initialize(
        other,
        repository=ROOT,
        declaration_root=runtime[2].path.parent,
        declaration_ref=cfg["declaration_ref"],
        bindings=runtime[3],
        datasets=[{"id": name, "format": value} for name, value in cfg["datasets"].items()],
    )
    assert initialized["runtime_sha256"] != runtime[1]
    (other / "RUNTIME.json").write_bytes((runtime[0] / "RUNTIME.json").read_bytes())
    before = state((other, runtime[1]))
    raw = encoded({"records": [{"id": "ITEM", "value": 1}]})
    with pytest.raises(CompanyStoreError):
        call(
            (other, runtime[1]),
            backup.append_dataset,
            0,
            "transplanted",
            dataset_id="DATA",
            content=raw,
            expected_sha256=sha(raw),
            event_at="2027-01-01T08:00:00Z",
        )
    assert state((other, runtime[1])) == before


def test_foreign_company_occurrence_cannot_satisfy_declared_due_slot(runtime):
    cfg = json.loads((runtime[0] / "RUNTIME.json").read_bytes())
    source = CompanyStore(runtime[0])
    source.register_system("FOREIGN", "other-branch", "backup_job", cfg["operator_id"])
    source.append_version(
        "FOREIGN",
        "other-branch",
        "backup_job",
        "B1",
        expected_version=0,
        command_id="foreign-job",
        event_at="2027-01-01T10:00:00Z",
        available_at="2027-01-01T10:00:00Z",
        content=encoded({"status": "COMPLETED"}),
        provenance={"source_reference": "explicit foreign fixture"},
    )
    report = backup.reconcile(
        runtime[0], expected_runtime_sha256=runtime[1], as_of="2027-01-01T10:00:00Z"
    )
    first = next(o for o in report["occurrences"] if o["schedule"]["id"] == "B1")
    assert first["state"] == "MISSING_DUE"
    assert first["history"] == []


@pytest.mark.parametrize(
    "field,value", [("operation", "RESTORE_READ"), ("principal_id", "OTHER"), ("enabled", "false")]
)
def test_forged_wrong_principal_operation_and_boolean_lease_is_rejected(runtime, field, value):
    src, lease, _ = prepared(runtime)
    source = CompanyStore(runtime[0])
    with backup.database(runtime[0]) as db:
        original = backup.native(db, lease)
    body = json.loads(original["content"])
    body[field] = value
    forged = source.append_version(
        lease["company"],
        lease["branch"],
        lease["system"],
        lease["record"],
        expected_version=lease["version"],
        command_id="forged-lease",
        event_at="2027-01-01T09:02:00Z",
        available_at="2027-01-01T09:02:00Z",
        content=encoded(body),
        provenance=json.loads(original["provenance"]),
    )
    before = state(runtime)
    with pytest.raises(CompanyStoreError):
        call(
            runtime,
            backup.run_backup,
            3,
            "bad-lease",
            occurrence_id="B1",
            source_pin=src,
            lease_pin=backup.pin(forged),
            attempted_at="2027-01-01T10:00:00Z",
        )
    assert state(runtime) == before


def test_native_batch_failure_retains_ambiguous_files_but_no_partial_database(runtime, monkeypatch):
    src, lease, _ = prepared(runtime)
    before = state(runtime)
    insert = backup._insert
    calls = 0

    def fail_job(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise sqlite3.IntegrityError("Injected second native insert failure")
        return insert(*args)

    monkeypatch.setattr(backup, "_insert", fail_job)
    with pytest.raises(sqlite3.IntegrityError):
        call(
            runtime,
            backup.run_backup,
            3,
            "interrupted-batch",
            occurrence_id="B1",
            source_pin=src,
            lease_pin=lease,
            attempted_at="2027-01-01T10:00:00Z",
        )
    assert state(runtime) == before
    attempt = runtime[0] / "attempts" / sha(b"interrupted-batch")
    copied = attempt / "copied.bin"
    assert copied.exists() and sha(copied.read_bytes()) == src["sha256"]
    monkeypatch.setattr(backup, "_insert", insert)
    with pytest.raises(CompanyStoreError, match="Interrupted"):
        call(
            runtime,
            backup.run_backup,
            3,
            "interrupted-batch",
            occurrence_id="B1",
            source_pin=src,
            lease_pin=lease,
            attempted_at="2027-01-01T10:00:00Z",
        )
    assert state(runtime) == before


def test_copy_parent_alias_rejected_before_any_external_bytes(runtime, tmp_path):
    src, lease, _ = prepared(runtime)
    before = state(runtime)
    external = tmp_path / "outside-runtime"
    external.mkdir(mode=0o700)
    (runtime[0] / "attempts").rmdir()
    (runtime[0] / "attempts").symlink_to(external, target_is_directory=True)
    with pytest.raises(CompanyStoreError):
        call(
            runtime,
            backup.run_backup,
            3,
            "external-copy",
            occurrence_id="B1",
            source_pin=src,
            lease_pin=lease,
            attempted_at="2027-01-01T10:00:00Z",
        )
    assert list(external.iterdir()) == []
    assert state(runtime) == before


def test_restored_record_type_change_is_not_hidden_by_python_equality(runtime):
    src, lease, restore = prepared(runtime)
    saved = call(
        runtime,
        backup.run_backup,
        3,
        "b1-copy",
        occurrence_id="B1",
        source_pin=src,
        lease_pin=lease,
        attempted_at="2027-01-01T10:00:00Z",
    )
    raw = encoded({"records": [{"id": "ONE", "value": True}]})
    changed = call(
        runtime,
        backup.append_dataset,
        4,
        "boolean-change",
        dataset_id="DATA",
        content=raw,
        expected_sha256=sha(raw),
        previous_pin=src,
        event_at="2027-01-02T09:00:00Z",
    )["source_pin"]
    restored = call(
        runtime,
        backup.run_restore,
        5,
        "compare-types",
        occurrence_id="R1",
        backup_pin=saved["object_pin"],
        comparison_source_pin=changed,
        lease_pin=restore,
        attempted_at="2027-01-02T11:00:00Z",
    )
    with backup.database(runtime[0]) as db:
        result = json.loads(backup.native(db, restored["job_pin"])["content"])
    assert result["byte_copy_matches_selected_backup"] is True
    assert result["comparison_bytes_equal"] is False
    assert result["content_reconciliation"]["changed_ids"] == ["ONE"]


def test_originals_collect_through_company_store_with_time_and_revocation(runtime):
    src, lease, _ = prepared(runtime)
    saved = call(
        runtime,
        backup.run_backup,
        3,
        "public-source",
        occurrence_id="B1",
        source_pin=src,
        lease_pin=lease,
        attempted_at="2027-01-01T10:00:00Z",
    )
    before_job = backup.reconcile(
        runtime[0], expected_runtime_sha256=runtime[1], as_of="2027-01-01T09:59:59Z"
    )
    assert before_job["declared_count"] == 4 and before_job["due_count"] == 0
    assert all(not row["history"] for row in before_job["occurrences"])
    after_due = backup.reconcile(
        runtime[0], expected_runtime_sha256=runtime[1], as_of="2027-01-02T11:00:00Z"
    )
    assert after_due["due_count"] == 3 and after_due["missing_due_count"] == 2
    obj = saved["object_pin"]
    store = CompanyStore(runtime[0])
    args = ("LEARNER", "ISOLATED-ENG", obj["company"], obj["branch"], obj["system"], obj["record"])
    with pytest.raises(CompanyStoreError):
        store.read_version(*args, version=obj["version"], as_of="2027-01-01T11:00:00Z")
    store.grant(*args[:5])
    before = state(runtime)
    with pytest.raises(CompanyStoreError):
        store.read_version(*args, version=obj["version"], as_of="2027-01-01T09:59:59Z")
    original = store.read_version(*args, version=obj["version"], as_of="2027-01-01T11:00:00Z")
    assert sha(original["content"]) == obj["sha256"] == src["sha256"]
    receipt = store.collect(
        *args, version=obj["version"], as_of="2027-01-01T11:00:00Z", command_id="read-original"
    )
    assert backup.pin(receipt["source"]) == obj
    assert (
        store.collect(
            *args, version=obj["version"], as_of="2027-01-01T11:00:00Z", command_id="read-original"
        )
        == receipt
    )
    store.grant(*args[:5], active=False)
    with pytest.raises(CompanyStoreError):
        store.collect(
            *args, version=obj["version"], as_of="2027-01-01T11:00:00Z", command_id="read-original"
        )
    assert state(runtime) == before
    assert "LOCAL" in receipt["source"]["provenance"]["classification"]
