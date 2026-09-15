"""Exact target bytes become explicit native originals without changing the target."""

import pytest

from enterprise.audit_suite import company_configuration_export as export
from enterprise.audit_suite import company_configuration_runtime as runtime
from enterprise.audit_suite.company_backup_runtime import database, native
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import sha
from tests.audit_suite.test_company_configuration_runtime import command, ready, snapshot


def args(fixture, identifier="export"):
    values = command(fixture, "RECONCILE", identifier)
    values.pop("operation")
    return values


def test_exact_raw_original_replay_after_change_and_ordinary_source_read(tmp_path):
    fixture = ready.__wrapped__(tmp_path)
    root, initial, *_ = fixture
    before = (root / "objects" / "initial.json").read_bytes()
    action = args(fixture)
    result = export.export_current(root, **action)
    assert result["native_pin"]["sha256"] == sha(before) and result["revision"] == 1
    assert not result["target_changed"]
    assert (root / "objects" / "initial.json").read_bytes() == before
    with database(root) as db:
        assert native(db, result["native_pin"])["content"] == before
        for table in ("grants", "collections", "access_events"):
            assert db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
    runtime.execute(root, **command(fixture, "APPLY", "apply"))
    stable = snapshot(root)
    assert export.export_current(root, **action) == result
    assert snapshot(root) == stable
    pin = result["native_pin"]
    store = CompanyStore(root)
    store.grant("reader", "ENG", pin["company"], pin["branch"], pin["system"])
    raw = store.read_version(
        "reader",
        "ENG",
        pin["company"],
        pin["branch"],
        pin["system"],
        pin["record"],
        version=pin["version"],
        as_of="2027-02-04T00:00:00Z",
    )
    assert raw["content"] == before and raw["sha256"] == sha(before)
    store.grant("reader", "ENG", pin["company"], pin["branch"], pin["system"], active=False)
    with pytest.raises(CompanyStoreError):
        store.read_version(
            "reader",
            "ENG",
            pin["company"],
            pin["branch"],
            pin["system"],
            pin["record"],
            version=pin["version"],
            as_of="2027-02-04T00:00:00Z",
        )
    assert runtime.inspect(root, expected_runtime_sha256=initial["runtime_sha256"])["revision"] == 2


@pytest.mark.parametrize(
    "changes",
    [
        {"expected_revision": 1},
        {"expected_current_sha256": "0" * 64},
        {"operator_id": "OTHER"},
        {"event_at": "2027-02-01T00:00:00Z"},
    ],
)
def test_stale_pins_wrong_operator_or_time_never_append(tmp_path, changes):
    fixture = ready.__wrapped__(tmp_path)
    before = snapshot(fixture[0])
    with pytest.raises(CompanyStoreError):
        export.export_current(fixture[0], **{**args(fixture), **changes})
    assert snapshot(fixture[0]) == before


def test_existing_runtime_command_namespace_and_changed_export_replay(tmp_path):
    fixture = ready.__wrapped__(tmp_path)
    runtime.execute(fixture[0], **command(fixture, "RECONCILE", "existing"))
    with pytest.raises(CompanyStoreError, match="replay"):
        export.export_current(fixture[0], **args(fixture, "existing"))
    action = args(fixture, "new-export")
    export.export_current(fixture[0], **action)
    before = snapshot(fixture[0])
    with pytest.raises(CompanyStoreError, match="replay"):
        export.export_current(fixture[0], **{**action, "rationale": "changed"})
    assert snapshot(fixture[0]) == before


def test_native_insert_failure_rolls_back_registration_and_shared_state(tmp_path, monkeypatch):
    fixture = ready.__wrapped__(tmp_path)
    before = snapshot(fixture[0])
    real = export._append

    def fail(*values, **kwargs):
        real(*values, **kwargs)
        raise OSError("after native insert")

    monkeypatch.setattr(export, "_append", fail)
    with pytest.raises(OSError):
        export.export_current(fixture[0], **args(fixture))
    assert snapshot(fixture[0]) == before
    with database(fixture[0]) as db:
        assert (
            db.execute("SELECT count(*) FROM systems WHERE system=?", (export.SYSTEM,)).fetchone()[
                0
            ]
            == 0
        )


def test_file_change_during_export_does_not_publish_native_copy(tmp_path, monkeypatch):
    fixture = ready.__wrapped__(tmp_path)
    root = fixture[0]
    before = snapshot(root)
    real = export._append

    def alter(*values, **kwargs):
        result = real(*values, **kwargs)
        (root / "objects" / "initial.json").write_bytes(b"{}")
        return result

    monkeypatch.setattr(export, "_append", alter)
    with pytest.raises(CompanyStoreError):
        export.export_current(root, **args(fixture))
    assert snapshot(root) == before


def test_alias_target_parent_cannot_supply_export_bytes(tmp_path):
    fixture = ready.__wrapped__(tmp_path)
    root = fixture[0]
    action = args(fixture)
    before = snapshot(root)
    original = root / "objects"
    original.rename(root / "original-objects")
    original.symlink_to(root / "original-objects", target_is_directory=True)
    with pytest.raises(CompanyStoreError):
        export.export_current(root, **action)
    assert snapshot(root) == before
