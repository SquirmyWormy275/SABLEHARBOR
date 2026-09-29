"""Independent monitor regressions using real local backup execution."""

import pytest

from enterprise.audit_suite import company_backup_monitor as monitor
from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from tests.audit_suite.test_company_backup_monitor import arguments, ready, stable
from tests.audit_suite.test_company_backup_runtime import call


def test_late_restore_does_not_close_previously_missing_ticket(tmp_path):
    rt, source, _, first, _ = ready.__wrapped__(tmp_path)
    scan = monitor.scan(rt[0], **arguments(rt, 5, "missing", "2027-01-02T11:00:00Z"))
    assert len(scan["new_ticket_pins"]) == 1
    ticket = scan["new_ticket_pins"][0]
    with backup.database(rt[0]) as db:
        retained = dict(backup.native(db, ticket))
        lease = backup.pin(
            db.execute(
                "SELECT * FROM versions WHERE system='credential_event' AND record='RESTORE_READ'"
            ).fetchone()
        )
    restored = call(
        rt,
        backup.run_restore,
        6,
        "late-restore",
        occurrence_id="R1",
        backup_pin=first["object_pin"],
        comparison_source_pin=source,
        lease_pin=lease,
        attempted_at="2027-01-02T12:00:00Z",
    )
    assert restored["status"] == "COMPLETED" and restored["revision"] == 7
    later = monitor.scan(rt[0], **arguments(rt, 7, "after-restore", "2027-01-02T13:00:00Z"))
    assert later["new_ticket_pins"] == [] and ticket not in later["ticket_pins"]
    with backup.database(rt[0]) as db:
        assert dict(backup.native(db, ticket)) == retained
        assert backup.decode(retained["content"])["status"] == "OPEN"
    before = stable(rt)
    assert (
        call(
            rt,
            backup.run_restore,
            6,
            "late-restore",
            occurrence_id="R1",
            backup_pin=first["object_pin"],
            comparison_source_pin=source,
            lease_pin=lease,
            attempted_at="2027-01-02T12:00:00Z",
        )
        == restored
    )
    assert stable(rt) == before


def test_source_cutoff_normalizes_offsets_and_excludes_foreign_branch(tmp_path):
    rt, *_ = ready.__wrapped__(tmp_path)
    kwargs = {"expected_runtime_sha256": rt[1]}
    before = monitor.inspect(rt[0], **kwargs, as_of="2027-01-02T10:00:00Z")
    assert monitor.inspect(rt[0], **kwargs, as_of="2027-01-02T03:00:00-07:00") == before
    cfg = backup._config(rt[0], rt[1])
    store = CompanyStore(rt[0])
    store.register_system(
        cfg["plan"]["company_id"], "OTHER-BRANCH", "backup_job", cfg["operator_id"]
    )
    store.append_version(
        cfg["plan"]["company_id"],
        "OTHER-BRANCH",
        "backup_job",
        "B2",
        expected_version=0,
        command_id="foreign",
        event_at="2027-01-02T09:00:00Z",
        available_at="2027-01-02T09:00:00Z",
        content=b'{"status":"COMPLETED"}',
        provenance={"source_reference": "independent neutral fixture"},
    )
    assert monitor.inspect(rt[0], **kwargs, as_of="2027-01-02T10:00:00Z") == before
    historical = monitor.inspect(rt[0], **kwargs, as_of="2027-01-02T09:59:59Z")
    assert len(historical["membership"]["jobs"]) == 1
    assert len(before["membership"]["jobs"]) == 2


def test_declaration_change_during_native_batch_rolls_back_all_rows(tmp_path, monkeypatch):
    rt, *_ = ready.__wrapped__(tmp_path)
    args = arguments(rt, 5, "declaration-race")
    before = stable(rt)
    real = backup._insert

    def change_after_insert(db, *args, **kwargs):
        result = real(db, *args, **kwargs)
        (rt[0] / "DECLARATION.json").write_bytes(b"{}")
        return result

    monkeypatch.setattr(backup, "_insert", change_after_insert)
    with pytest.raises(CompanyStoreError, match="declaration changed"):
        monitor.scan(rt[0], **args)
    assert stable(rt) == before


def test_same_command_changed_scan_inputs_reject_without_authority_activity(tmp_path):
    rt, *_ = ready.__wrapped__(tmp_path)
    args = arguments(rt, 5, "exact-monitor-command")
    receipt = monitor.scan(rt[0], **args)
    before = stable(rt)
    with pytest.raises(CompanyStoreError, match="replay"):
        monitor.scan(rt[0], **{**args, "rationale": "Changed instruction is not exact retry"})
    assert stable(rt) == before
    assert monitor.scan(rt[0], **args) == receipt
    with backup.database(rt[0]) as db:
        for table in ("grants", "collections", "access_events"):
            assert db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
