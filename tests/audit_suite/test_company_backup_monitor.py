"""Explicit scans produce native operational records without audit inputs."""

import pytest

from enterprise.audit_suite import company_backup_monitor as monitor
from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from tests.audit_suite.test_company_backup_runtime import call, inventory, prepared, runtime


@pytest.fixture
def ready(tmp_path):
    rt = runtime.__wrapped__(tmp_path)
    source, lease, _ = prepared(rt)
    first = call(
        rt,
        backup.run_backup,
        3,
        "b1",
        occurrence_id="B1",
        source_pin=source,
        lease_pin=lease,
        attempted_at="2027-01-01T10:00:00Z",
    )
    failed = call(
        rt,
        backup.run_backup,
        4,
        "b2-fail",
        occurrence_id="B2",
        source_pin=source,
        lease_pin=lease,
        attempted_at="2027-01-02T10:00:00Z",
    )
    return rt, source, lease, first, failed


def arguments(rt, revision, command, as_of="2027-01-03T12:00:00Z"):
    result = monitor.inspect(rt[0], expected_runtime_sha256=rt[1], as_of=as_of)
    cfg = backup._config(rt[0], rt[1])
    return dict(
        expected_runtime_sha256=rt[1],
        expected_revision=revision,
        command_id=command,
        expected_jobs_sha256=result["jobs_sha256"],
        as_of=as_of,
        recorded_at=as_of,
        operator_id=cfg["operator_id"],
        rationale="Explicit local scheduled-job scan",
    )


def stable(rt):
    with backup.database(rt[0]) as db:
        return {
            table: [tuple(r) for r in db.execute("SELECT * FROM " + table + " ORDER BY 1,2")]
            for table in ("systems", "versions", "backup_runtime_state", "backup_runtime_commands")
        }


def test_atomic_scan_reuses_exact_failed_ticket_and_deduplicates_missing(ready):
    rt, *_ = ready
    before = inventory(rt)
    declaration = rt[2].path.read_bytes()
    args = arguments(rt, 5, "scan-one")
    receipt = monitor.scan(rt[0], **args)
    assert receipt["revision"] == 6 and receipt["declared_count"] == 4 and receipt["due_count"] == 4
    assert len(receipt["observation_pins"]) == 3
    assert len(receipt["new_ticket_pins"]) == 2
    assert [p["system"] for p in receipt["ticket_pins"]].count("failure_ticket") == 1
    after = inventory(rt)

    def by_id(rows):
        return {tuple(r[k] for k in backup.FIELDS[:-1]): r for r in rows}

    assert all(by_id(after)[k] == v for k, v in by_id(before).items())
    recorded = stable(rt)
    assert monitor.scan(rt[0], **args) == receipt and stable(rt) == recorded
    second = monitor.scan(rt[0], **arguments(rt, 6, "scan-two", "2027-01-03T13:00:00Z"))
    assert not second["new_ticket_pins"] and second["ticket_pins"] == receipt["ticket_pins"]
    assert rt[2].path.read_bytes() == declaration
    with backup.database(rt[0]) as db:
        assert db.execute("SELECT count(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM collections").fetchone()[0] == 0
        for p in receipt["new_ticket_pins"]:
            assert backup.decode(backup.native(db, p)["content"])["status"] == "OPEN"


def test_retry_after_scan_preserves_failed_source_and_monitor_tickets(ready):
    rt, source, lease, first, failed = ready
    scan = monitor.scan(rt[0], **arguments(rt, 5, "scan", "2027-01-02T11:00:00Z"))
    corrected = call(
        rt,
        backup.record_lease,
        6,
        "lease-corrected",
        operation="BACKUP_WRITE",
        enabled=True,
        valid_from="2027-01-02T12:00:00Z",
        expires_at="2027-02-01T00:00:00Z",
        event_at="2027-01-02T12:00:00Z",
        previous_pin=lease,
    )
    call(
        rt,
        backup.run_backup,
        7,
        "b2-retry",
        occurrence_id="B2",
        source_pin=source,
        lease_pin=corrected["lease_pin"],
        prior_attempt_pin=failed["job_pin"],
        attempted_at="2027-01-02T13:00:00Z",
    )
    later = monitor.scan(rt[0], **arguments(rt, 8, "scan-later", "2027-01-02T14:00:00Z"))
    assert later["ticket_pins"] == scan["ticket_pins"] and later["new_ticket_pins"] == []
    snapshot = monitor.inspect(rt[0], expected_runtime_sha256=rt[1], as_of="2027-01-02T14:00:00Z")
    assert snapshot["latest_completed_count"] == 2
    assert any(o["source_job_pin"] == failed["job_pin"] for o in snapshot["observations"])


@pytest.mark.parametrize(
    "field,value",
    [("expected_revision", 4), ("expected_jobs_sha256", "0" * 64), ("operator_id", "WRONG")],
)
def test_stale_inputs_or_operator_reject_without_writes(ready, field, value):
    rt, *_ = ready
    args = arguments(rt, 5, "reject")
    args[field] = value
    before = stable(rt)
    with pytest.raises(CompanyStoreError):
        monitor.scan(rt[0], **args)
    assert stable(rt) == before


def test_native_insert_failure_rolls_back_registration_journal_and_revision(ready, monkeypatch):
    rt, *_ = ready
    before = stable(rt)
    real = backup._insert
    calls = 0

    def fail(db, *args, **kwargs):
        nonlocal calls
        calls += 1
        result = real(db, *args, **kwargs)
        if calls == 2:
            raise OSError("Injected second insert fault")
        return result

    monkeypatch.setattr(backup, "_insert", fail)
    with pytest.raises(OSError):
        monitor.scan(rt[0], **arguments(rt, 5, "fault"))
    assert stable(rt) == before


def test_historical_cutoff_and_global_command_namespace(ready):
    rt, *_ = ready
    old = monitor.inspect(rt[0], expected_runtime_sha256=rt[1], as_of="2027-01-01T09:59:59Z")
    assert old["due_count"] == 0 and old["membership"]["jobs"] == []
    args = arguments(rt, 5, "b1")
    before = stable(rt)
    with pytest.raises(CompanyStoreError, match="replay"):
        monitor.scan(rt[0], **args)
    assert stable(rt) == before
    args = arguments(rt, 5, "future")
    args["recorded_at"] = "2027-01-03T11:00:00Z"
    with pytest.raises(CompanyStoreError):
        monitor.scan(rt[0], **args)


def test_new_monitor_native_source_obeys_ordinary_grants_and_future_cutoff(ready):
    rt, *_ = ready
    receipt = monitor.scan(rt[0], **arguments(rt, 5, "collectable"))
    p = receipt["scan_pin"]
    store = CompanyStore(rt[0])
    # Native read API is tested with exact original identity; no audit is created.
    with pytest.raises(CompanyStoreError):
        store.read_version(
            "learner",
            "ENG",
            p["company"],
            p["branch"],
            p["system"],
            p["record"],
            version=p["version"],
            as_of="2027-01-04T00:00:00Z",
        )
    store.grant("learner", "ENG", p["company"], p["branch"], p["system"])
    with pytest.raises(CompanyStoreError):
        store.read_version(
            "learner",
            "ENG",
            p["company"],
            p["branch"],
            p["system"],
            p["record"],
            version=p["version"],
            as_of="2027-01-03T11:59:59Z",
        )
    metadata = store.read_version(
        "learner",
        "ENG",
        p["company"],
        p["branch"],
        p["system"],
        p["record"],
        version=p["version"],
        as_of="2027-01-04T00:00:00Z",
    )
    assert metadata["sha256"] == p["sha256"] and backup.sha(metadata["content"]) == p["sha256"]
    store.grant("learner", "ENG", p["company"], p["branch"], p["system"], active=False)
    with pytest.raises(CompanyStoreError):
        store.read_version(
            "learner",
            "ENG",
            p["company"],
            p["branch"],
            p["system"],
            p["record"],
            version=p["version"],
            as_of="2027-01-04T00:00:00Z",
        )


def test_exact_replay_still_rejects_corrupt_retained_declaration(ready):
    rt, *_ = ready
    args = arguments(rt, 5, "before-corruption")
    monitor.scan(rt[0], **args)
    before = stable(rt)
    (rt[0] / "DECLARATION.json").write_bytes(b"Changed only in disposable fixture")
    with pytest.raises(CompanyStoreError, match="declaration"):
        monitor.scan(rt[0], **args)
    assert stable(rt) == before
