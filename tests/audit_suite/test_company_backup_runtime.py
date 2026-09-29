"""Real local copies and failed/corrected history from an independent due ledger."""

import copy
from pathlib import Path

import pytest

from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite.company_operating_period import create_period
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.organization import snapshot

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def runtime(tmp_path):
    ledger = tmp_path / "ledger"
    ledger.mkdir(mode=0o700)
    store = CompanyStore(ledger)
    owner = next(
        r
        for r in snapshot(ROOT, as_of="2027-01-01")["control_assignments"]
        if r["control_id"] == "SH-BCM-003"
    )["primary_person_id"]
    schedule = []
    bindings = []
    for id, day, hour, kind, dataset in [
        ("B1", 1, 10, "BACKUP", "DATA"),
        ("B2", 2, 10, "BACKUP", "DATA"),
        ("R1", 2, 11, "RESTORE", "DATA"),
        ("B3", 3, 10, "BACKUP", "OTHER"),
    ]:
        schedule.append(
            dict(
                id=id,
                inventory_ids=[dataset],
                control_id="SH-BCM-002" if kind == "BACKUP" else "SH-BCM-003",
                window_start=f"2027-01-{day:02}T00:00:00Z",
                window_end_exclusive=f"2027-01-{day + 1:02}T00:00:00Z",
                due_at=f"2027-01-{day:02}T{hour:02}:00:00Z",
                depends_on=[],
            )
        )
        bindings.append(dict(occurrence_id=id, dataset_id=dataset, operation=kind))
    plan = dict(
        period_id="BACKUP-PERIOD",
        company_id="SH",
        branch_id="local-backup",
        owner_id=owner,
        control_ids=["SH-BCM-002", "SH-BCM-003"],
        period_start="2027-01-01T00:00:00Z",
        period_end_exclusive="2027-02-01T00:00:00Z",
        declared_at="2026-12-31T00:00:00Z",
        inventory=[{"id": id, "description": "Explicit local dataset"} for id in ["DATA", "OTHER"]],
        local_basis="Four explicit local occurrences; no RPO or BIA approval.",
        schedule=schedule,
    )
    declaration = create_period(store, repository=ROOT, plan=plan)
    destination = tmp_path / "runtime"
    result = backup.initialize(
        destination,
        repository=ROOT,
        declaration_root=ledger,
        declaration_ref=backup.pin(declaration),
        bindings=bindings,
        datasets=[{"id": "DATA", "format": "JSON_RECORDS"}, {"id": "OTHER", "format": "BYTES"}],
    )
    return destination, result["runtime_sha256"], store, bindings


def call(rt, method, revision, command, **kwargs):
    if method in (backup.run_backup, backup.run_restore):
        kwargs.setdefault("rationale", "Explicit local backup or restore of selected exact bytes")
    return method(
        rt[0],
        expected_runtime_sha256=rt[1],
        expected_revision=revision,
        command_id=command,
        **kwargs,
    )


def prepared(rt):
    data = encoded({"records": [{"id": "ONE", "value": 1}]})
    source = call(
        rt,
        backup.append_dataset,
        0,
        "data",
        dataset_id="DATA",
        content=data,
        expected_sha256=sha(data),
        event_at="2027-01-01T08:00:00Z",
    )
    lease = call(
        rt,
        backup.record_lease,
        1,
        "lease",
        operation="BACKUP_WRITE",
        enabled=True,
        valid_from="2027-01-01T00:00:00Z",
        expires_at="2027-01-02T10:00:00Z",
        event_at="2027-01-01T09:00:00Z",
    )
    restore = call(
        rt,
        backup.record_lease,
        2,
        "restore-lease",
        operation="RESTORE_READ",
        enabled=True,
        valid_from="2027-01-01T00:00:00Z",
        expires_at="2027-01-10T00:00:00Z",
        event_at="2027-01-01T09:01:00Z",
    )
    return source["source_pin"], lease["lease_pin"], restore["lease_pin"]


def inventory(rt):
    with backup.database(rt[0]) as db:
        return [
            dict(r) for r in db.execute("SELECT * FROM versions ORDER BY system,record,version")
        ]


def test_real_multi_occurrence_copies_expiry_correction_and_independent_due_census(runtime):
    declaration_before = runtime[2].path.read_bytes()
    src, lease, restore_lease = prepared(runtime)
    b1 = call(
        runtime,
        backup.run_backup,
        3,
        "b1",
        occurrence_id="B1",
        source_pin=src,
        lease_pin=lease,
        attempted_at="2027-01-01T10:00:00Z",
    )
    changed = encoded({"records": [{"id": "ONE", "value": 2}, {"id": "TWO", "value": 3}]})
    src2 = call(
        runtime,
        backup.append_dataset,
        4,
        "data2",
        dataset_id="DATA",
        content=changed,
        expected_sha256=sha(changed),
        previous_pin=src,
        event_at="2027-01-02T09:00:00Z",
    )["source_pin"]
    failed = call(
        runtime,
        backup.run_backup,
        5,
        "b2-failed",
        occurrence_id="B2",
        source_pin=src2,
        lease_pin=lease,
        attempted_at="2027-01-02T10:00:00Z",
    )
    assert failed["status"] == "FAILED" and failed["object_pin"] is None
    old_restore = call(
        runtime,
        backup.run_restore,
        6,
        "restore-old",
        occurrence_id="R1",
        backup_pin=b1["object_pin"],
        comparison_source_pin=src2,
        lease_pin=restore_lease,
        attempted_at="2027-01-02T11:00:00Z",
    )
    newlease = call(
        runtime,
        backup.record_lease,
        7,
        "lease-corrected",
        operation="BACKUP_WRITE",
        enabled=True,
        valid_from="2027-01-02T12:00:00Z",
        expires_at="2027-02-01T00:00:00Z",
        event_at="2027-01-02T12:00:00Z",
        previous_pin=lease,
    )["lease_pin"]
    fixed = call(
        runtime,
        backup.run_backup,
        8,
        "b2-fixed",
        occurrence_id="B2",
        source_pin=src2,
        lease_pin=newlease,
        attempted_at="2027-01-02T13:00:00Z",
        prior_attempt_pin=failed["job_pin"],
    )
    final = call(
        runtime,
        backup.run_restore,
        9,
        "restore-new",
        occurrence_id="R1",
        backup_pin=fixed["object_pin"],
        comparison_source_pin=src2,
        lease_pin=restore_lease,
        attempted_at="2027-01-02T14:00:00Z",
        prior_attempt_pin=old_restore["job_pin"],
    )
    before = (runtime[0] / "company.sqlite3").read_bytes()
    report = backup.reconcile(
        runtime[0], expected_runtime_sha256=runtime[1], as_of="2027-01-04T00:00:00Z"
    )
    assert report["declared_count"] == report["due_count"] == 4 and report["missing_due_count"] == 1
    assert report["actual_copy_completed_count"] == 3 and report["failed_occurrence_count"] == 0
    by = {o["schedule"]["id"]: o for o in report["occurrences"]}
    assert (
        by["B2"]["prior_failed_attempts"] == 1
        and by["B2"]["history"][1]["recording_timeliness"] == "AFTER_DUE"
    )
    assert by["B3"]["binding"]["dataset_id"] == "OTHER" and by["B3"]["history"] == []
    r1, r2 = by["R1"]["history"]
    assert r1["content_reconciliation"]["missing_ids"] == ["TWO"] and r1["content_reconciliation"][
        "changed_ids"
    ] == ["ONE"]
    assert (
        r2["content_reconciliation"]["missing_ids"]
        == r2["content_reconciliation"]["changed_ids"]
        == []
    )
    assert r1["actual_elapsed_seconds"] >= 0 and r1["checkpoint_age_seconds"] == 27 * 3600
    assert all(r["byte_copy_matches_selected_backup"] for r in (r1, r2))
    with backup.database(runtime[0]) as db:
        assert backup.native(db, final["object_pin"])["content"] == changed
        for table in ["grants", "collections", "access_events"]:
            assert db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
    assert before == (runtime[0] / "company.sqlite3").read_bytes()
    assert declaration_before == runtime[2].path.read_bytes()
    assert report["population_acceptance"] == "NOT_PERFORMED"


def test_exact_replay_changed_commands_and_stale_source_fail_without_native_changes(runtime):
    src, lease, _ = prepared(runtime)
    args = dict(
        occurrence_id="B1", source_pin=src, lease_pin=lease, attempted_at="2027-01-01T10:00:00Z"
    )
    receipt = call(runtime, backup.run_backup, 3, "same", **args)
    before = (runtime[0] / "company.sqlite3").read_bytes()
    assert call(runtime, backup.run_backup, 3, "same", **args) == receipt
    with pytest.raises(CompanyStoreError):
        call(
            runtime,
            backup.run_backup,
            3,
            "same",
            **(args | {"attempted_at": "2027-01-01T10:01:00Z"}),
        )
    bad = copy.deepcopy(src)
    bad["sha256"] = "a" * 64
    with pytest.raises(CompanyStoreError):
        call(
            runtime,
            backup.run_backup,
            4,
            "bad",
            **(args | {"source_pin": bad, "prior_attempt_pin": receipt["job_pin"]}),
        )
    assert before == (runtime[0] / "company.sqlite3").read_bytes()


@pytest.mark.parametrize("stage", ["before_fsync", "after_fsync", "before_commit"])
def test_interrupted_copy_never_commits_job_object_or_command(runtime, monkeypatch, stage):
    src, lease, _ = prepared(runtime)
    before = (runtime[0] / "company.sqlite3").read_bytes()
    original = backup.os.fsync
    if stage != "before_commit":

        def fail(fd):
            if stage == "after_fsync":
                original(fd)
            raise OSError("injected copy interruption")

        monkeypatch.setattr(backup.os, "fsync", fail)
    else:
        insert = backup._insert

        def fail(db, cfg, system, *args):
            value = insert(db, cfg, system, *args)
            if system == "backup_job":
                raise OSError("injected before batch commit")
            return value

        monkeypatch.setattr(backup, "_insert", fail)
    with pytest.raises(OSError):
        call(
            runtime,
            backup.run_backup,
            3,
            "interrupted",
            occurrence_id="B1",
            source_pin=src,
            lease_pin=lease,
            attempted_at="2027-01-01T10:00:00Z",
        )
    assert before == (runtime[0] / "company.sqlite3").read_bytes()
    assert not any(r["system"] in ["backup_job", "backup_object"] for r in inventory(runtime))
    report = backup.reconcile(
        runtime[0], expected_runtime_sha256=runtime[1], as_of="2027-01-01T10:00:00Z"
    )
    assert report["missing_due_count"] == 1


def test_corrupt_persisted_backup_is_not_silently_restored_from_native_blob(runtime):
    src, lease, restore = prepared(runtime)
    job = call(
        runtime,
        backup.run_backup,
        3,
        "b1",
        occurrence_id="B1",
        source_pin=src,
        lease_pin=lease,
        attempted_at="2027-01-01T10:00:00Z",
    )
    (runtime[0] / "attempts" / sha(b"b1") / "copied.bin").write_bytes(b"corrupt")
    result = call(
        runtime,
        backup.run_restore,
        4,
        "restore",
        occurrence_id="R1",
        backup_pin=job["object_pin"],
        comparison_source_pin=src,
        lease_pin=restore,
        attempted_at="2027-01-02T11:00:00Z",
    )
    assert result["status"] == "FAILED" and result["object_pin"] is None
    assert not any(r["system"] == "restored_dataset" for r in inventory(runtime))


def test_changed_configuration_wrong_dataset_and_undated_inputs_fail(runtime):
    src, lease, _ = prepared(runtime)
    with pytest.raises(CompanyStoreError):
        backup.reconcile(runtime[0], expected_runtime_sha256="a" * 64, as_of="2027-01-01T00:00:00Z")
    with pytest.raises(CompanyStoreError):
        call(
            runtime,
            backup.run_backup,
            3,
            "bad-date",
            occurrence_id="B1",
            source_pin=src,
            lease_pin=lease,
            attempted_at="2027-01-01",
        )
    with pytest.raises(CompanyStoreError):
        call(
            runtime,
            backup.run_backup,
            3,
            "wrong-dataset",
            occurrence_id="B3",
            source_pin=src,
            lease_pin=lease,
            attempted_at="2027-01-03T10:00:00Z",
        )


def test_aggregate_native_quota_rejects_without_revision_or_bytes(runtime, monkeypatch):
    before = (runtime[0] / "company.sqlite3").read_bytes()
    monkeypatch.setattr(backup, "MAX_TOTAL_BYTES", 1)
    raw = encoded({"records": [{"id": "ONE", "value": 1}]})
    with pytest.raises(CompanyStoreError, match="byte quota"):
        call(
            runtime,
            backup.append_dataset,
            0,
            "quota",
            dataset_id="DATA",
            content=raw,
            expected_sha256=sha(raw),
            event_at="2027-01-01T08:00:00Z",
        )
    assert (runtime[0] / "company.sqlite3").read_bytes() == before
