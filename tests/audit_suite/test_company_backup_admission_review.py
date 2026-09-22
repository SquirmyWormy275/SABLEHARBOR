"""Independent admission replay/chronology checks using disposable native runtime fixtures."""

import json

import pytest

from enterprise.audit_suite import company_backup_admission as admission
from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite.test_company_backup_admission import bound as bound_fixture
from tests.audit_suite.test_company_backup_admission import state


@pytest.fixture
def bound(tmp_path):
    return bound_fixture.__wrapped__(tmp_path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("revision", 999),
        ("revision", True),
        ("command_id", "OTHER"),
        ("event_at", "2040-01-01T00:00:00Z"),
        ("status", "UNRELATED_STATUS"),
    ],
)
def test_corrupt_command_receipt_envelope_replay_rejected(bound, field, value):
    target, _, action = bound
    admission.admit_dataset(target[0], **action)
    # Simulate offline corruption in disposable command receipt, not a native source mutation.
    with backup.database(target[0], True) as db:
        for row in list(
            db.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' "
                "AND tbl_name='backup_runtime_commands'"
            )
        ):
            db.execute('DROP TRIGGER "' + row[0].replace('"', '""') + '"')
        row = db.execute(
            "SELECT receipt FROM backup_runtime_commands WHERE command_id=?",
            (action["command_id"],),
        ).fetchone()
        receipt = json.loads(row[0])
        receipt[field] = value
        db.execute(
            "UPDATE backup_runtime_commands SET receipt=? WHERE command_id=?",
            (json.dumps(receipt), action["command_id"]),
        )
    before = state(target[0])
    with pytest.raises(CompanyStoreError):
        admission.admit_dataset(target[0], **action)
    assert state(target[0]) == before


def test_post_commit_integrity_failure_preserves_explicit_committed_operation(bound, monkeypatch):
    target, source, action = bound
    original = admission._read
    calls = 0
    before_source = (source[0] / "company.sqlite3").read_bytes()

    def changed(*args):
        nonlocal calls
        calls += 1
        raw, selected = original(*args)
        if calls == 3:
            selected["identity_basis"] = "CHANGED_AFTER_COMMIT"
        return raw, selected

    monkeypatch.setattr(admission, "_read", changed)
    with pytest.raises(CompanyStoreError, match="before admission receipt"):
        admission.admit_dataset(target[0], **action)
    with backup.database(target[0]) as db:
        assert db.execute("SELECT revision FROM backup_runtime_state").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM backup_runtime_commands").fetchone()[0] == 1
        assert (
            db.execute("SELECT count(*) FROM versions WHERE system='source_dataset'").fetchone()[0]
            == 1
        )
    assert (source[0] / "company.sqlite3").read_bytes() == before_source
    monkeypatch.setattr(admission, "_read", original)
    retained = state(target[0])
    assert admission.admit_dataset(target[0], **action)["revision"] == 1
    assert state(target[0]) == retained


@pytest.mark.parametrize("mutation", ["target", "definition_available"])
def test_repinned_source_metadata_cannot_override_native_definition_binding(bound, mutation):
    _, source, action = bound
    with backup.database(source[0], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        if mutation == "target":
            row = db.execute(
                "SELECT provenance FROM versions WHERE system='configuration_export'"
            ).fetchone()
            metadata = json.loads(row[0])
            metadata["target_id"] = "UNRELATED-TARGET"
            db.execute(
                "UPDATE versions SET provenance=? WHERE system='configuration_export'",
                (json.dumps(metadata),),
            )
        else:
            db.execute(
                "UPDATE versions SET available_at=? WHERE system='configuration_runtime'",
                ("2028-01-01T00:00:00Z",),
            )
    with pytest.raises(CompanyStoreError, match="identity differs|unavailable at export"):
        admission.inspect_source(
            source[0],
            source_pin=action["source_pin"],
            source_definition_pin=action["source_definition_pin"],
        )
