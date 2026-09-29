"""Real configuration export to native backup dataset; no actual operational stores."""

import copy

import pytest

from enterprise.audit_suite import company_backup_admission as admission
from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite import company_configuration_export as export
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.inference import _json as decode
from tests.audit_suite.test_company_backup_runtime import runtime
from tests.audit_suite.test_company_configuration_export import args
from tests.audit_suite.test_company_configuration_runtime import ready


def state(root):
    with backup.database(root) as db:
        return {
            name: [tuple(row) for row in db.execute("SELECT * FROM " + name)]
            for name in (
                "versions",
                "systems",
                "backup_runtime_commands",
                "backup_runtime_state",
                "grants",
                "access_events",
                "collections",
            )
        }


@pytest.fixture
def bound(tmp_path):
    source_dir = tmp_path / "producer"
    source_dir.mkdir(mode=0o700)
    source = ready.__wrapped__(source_dir)
    result = export.export_current(source[0], **args(source))
    target_dir = tmp_path / "consumer"
    target_dir.mkdir(mode=0o700)
    target = runtime.__wrapped__(target_dir)
    with backup.database(source[0]) as db:
        definition = backup.pin(
            db.execute("SELECT * FROM versions WHERE system='configuration_runtime'").fetchone()
        )
    selected = admission.inspect_source(
        source[0], source_pin=result["native_pin"], source_definition_pin=definition
    )
    cfg = backup._config(target[0], target[1])
    action = dict(
        expected_runtime_sha256=target[1],
        expected_revision=0,
        command_id="admit",
        dataset_id="OTHER",
        operator_id=cfg["operator_id"],
        event_at="2027-02-03T01:00:00Z",
        source_root=source[0],
        source_store_id=selected["source_store_id"],
        source_pin=result["native_pin"],
        source_definition_pin=definition,
        expected_source_metadata_sha256=selected["metadata_sha256"],
    )
    return target, source, action


def test_exact_native_bytes_and_dependency_atomic_replay(bound):
    target, source, action = bound
    original_db = (source[0] / "company.sqlite3").read_bytes()
    with backup.database(target[0]) as db:
        registered_systems = {tuple(row) for row in db.execute("SELECT * FROM systems")}
    result = admission.admit_dataset(target[0], **action)
    with backup.database(target[0]) as db:
        row = backup.native(db, result["source_pin"])
        assert row["content"] == (source[0] / "objects/initial.json").read_bytes()
        assert decode(row["provenance"])["source_admission"] == result["dependency"]
        assert db.execute("SELECT revision FROM backup_runtime_state").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM backup_runtime_commands").fetchone()[0] == 1
        assert {tuple(row) for row in db.execute("SELECT * FROM systems")} == registered_systems
    retained = state(target[0])
    assert admission.admit_dataset(target[0], **action) == result
    assert state(target[0]) == retained
    assert (source[0] / "company.sqlite3").read_bytes() == original_db


@pytest.mark.parametrize(
    "changes",
    [
        {"expected_revision": 1},
        {"operator_id": "OTHER"},
        {"dataset_id": "ABSENT"},
        {"event_at": "2027-02-02T00:00:00Z"},
        {"expected_source_metadata_sha256": "0" * 64},
        {"source_store_id": "SOURCE-UNVERIFIED"},
        {"dataset_id": "DATA"},
    ],
)
def test_stale_future_binding_and_typed_dataset_reject_without_changes(bound, changes):
    target, _, action = bound
    before = state(target[0])
    with pytest.raises(CompanyStoreError):
        admission.admit_dataset(target[0], **{**action, **changes})
    assert state(target[0]) == before


def test_mid_transaction_source_change_rolls_back_every_native_row(bound, monkeypatch):
    target, _, action = bound
    before = state(target[0])
    original = admission._read
    calls = 0

    def changed(*a):
        nonlocal calls
        calls += 1
        raw, selected = original(*a)
        if calls == 2:
            selected["metadata"]["origin"] = "CHANGED"
        return raw, selected

    monkeypatch.setattr(admission, "_read", changed)
    with pytest.raises(CompanyStoreError, match="changed during"):
        admission.admit_dataset(target[0], **action)
    assert state(target[0]) == before


def test_shared_command_namespace_and_changed_dependency_replay(bound):
    target, _, action = bound
    first = admission.admit_dataset(target[0], **action)
    before = state(target[0])
    with pytest.raises(CompanyStoreError, match="replay"):
        backup.append_dataset(
            target[0],
            expected_runtime_sha256=target[1],
            expected_revision=0,
            command_id=action["command_id"],
            dataset_id="OTHER",
            content=b"x",
            expected_sha256=backup.sha(b"x"),
            event_at=action["event_at"],
        )
    with pytest.raises(CompanyStoreError, match="replay"):
        admission.admit_dataset(target[0], **{**action, "event_at": "2027-02-03T02:00:00Z"})
    assert state(target[0]) == before
    assert first["revision"] == 1


def test_source_path_alias_missing_source_and_copied_store_identity_fail(bound, tmp_path):
    import shutil

    target, source, action = bound
    before = state(target[0])
    alias = tmp_path / "alias"
    alias.symlink_to(source[0], target_is_directory=True)
    copied = tmp_path / "copied"
    shutil.copytree(source[0], copied)
    for root in [alias, copied, tmp_path / "absent", target[0]]:
        with pytest.raises((CompanyStoreError, FileNotFoundError)):
            admission.admit_dataset(target[0], **{**action, "source_root": root})
    assert not (tmp_path / "absent").exists()
    assert state(target[0]) == before


@pytest.mark.parametrize("version", [True, 1.0])
def test_native_version_is_exact_integer(bound, version):
    target, _, action = bound
    action = copy.deepcopy(action)
    action["source_pin"]["version"] = version
    with pytest.raises(CompanyStoreError):
        admission.admit_dataset(target[0], **action)


def test_exact_replay_rechecks_original_integrity(bound):
    target, source, action = bound
    admission.admit_dataset(target[0], **action)
    before = state(target[0])
    # Deliberate administrator tamper in this disposable source, bypassing immutable trigger.
    with backup.database(source[0], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET content=? WHERE system='configuration_export'", (b"corrupt",)
        )
    with pytest.raises(CompanyStoreError, match="pin or bytes"):
        admission.admit_dataset(target[0], **action)
    assert state(target[0]) == before


def test_dataset_correction_requires_exact_prior_and_preserves_both_versions(bound):
    target, _, action = bound
    first = admission.admit_dataset(target[0], **action)
    before = state(target[0])
    next_action = {**action, "expected_revision": 1, "command_id": "admit-next"}
    with pytest.raises(CompanyStoreError):
        admission.admit_dataset(target[0], **next_action)
    assert state(target[0]) == before
    second = admission.admit_dataset(
        target[0], **{**next_action, "previous_pin": first["source_pin"]}
    )
    assert second["source_pin"]["version"] == 2
    with backup.database(target[0]) as db:
        assert backup.native(db, first["source_pin"])["sha256"] == first["source_pin"]["sha256"]


def test_batch_error_after_native_insert_cannot_leave_admitted_original(bound, monkeypatch):
    target, _, action = bound
    before = state(target[0])
    original = backup._insert

    def interrupted(*a, **kw):
        original(*a, **kw)
        raise OSError("Injected commit-path failure")

    monkeypatch.setattr(backup, "_insert", interrupted)
    with pytest.raises(OSError):
        admission.admit_dataset(target[0], **action)
    assert state(target[0]) == before


@pytest.mark.parametrize("mutation", ["delete", "provenance"])
def test_replay_validates_retained_consumer_original(bound, mutation):
    target, _, action = bound
    admission.admit_dataset(target[0], **action)
    with backup.database(target[0], True) as db:
        if mutation == "delete":
            db.execute("DROP TRIGGER no_version_delete")
            db.execute("DELETE FROM versions WHERE system='source_dataset'")
        else:
            db.execute("DROP TRIGGER no_version_update")
            db.execute("UPDATE versions SET provenance='{}' WHERE system='source_dataset'")
    before = state(target[0])
    with pytest.raises(CompanyStoreError):
        admission.admit_dataset(target[0], **action)
    assert state(target[0]) == before


def test_replay_final_source_change_is_not_silently_successful(bound, monkeypatch):
    target, source, action = bound
    admission.admit_dataset(target[0], **action)
    before = state(target[0])
    execute = backup._execute

    def changed(*a, **kw):
        result = execute(*a, **kw)
        with backup.database(source[0], True) as db:
            db.execute("DROP TRIGGER no_version_update")
            db.execute(
                "UPDATE versions SET content=? WHERE system='configuration_export'",
                (b"late tamper",),
            )
        return result

    monkeypatch.setattr(backup, "_execute", changed)
    with pytest.raises(CompanyStoreError):
        admission.admit_dataset(target[0], **action)
    assert state(target[0]) == before
