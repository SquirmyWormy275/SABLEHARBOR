"""Independent exact-original export authority, publication and historical checks."""

import json

import pytest

from enterprise.audit_suite import company_configuration_export as export
from enterprise.audit_suite.company_backup_runtime import database, native
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from tests.audit_suite.test_company_configuration_export import args
from tests.audit_suite.test_company_configuration_runtime import ready as ready
from tests.audit_suite.test_company_configuration_runtime import snapshot


def test_export_owner_conflict_rejects_without_native_or_revision_change(ready):
    root, initial, *_ = ready
    cfg = json.loads((root / "RUNTIME.json").read_bytes())
    CompanyStore(root).register_system(cfg["company"], cfg["branch"], export.SYSTEM, "OTHER")
    before = snapshot(root)
    with pytest.raises(CompanyStoreError, match="owner differs"):
        export.export_current(root, **args(ready))
    assert snapshot(root) == before
    assert initial["revision"] == 0


def test_export_implementation_change_rolls_back_native_registration_and_journal(
    ready, monkeypatch
):
    root = ready[0]
    before = snapshot(root)
    original = export._code_pins
    calls = 0

    def changed():
        nonlocal calls
        calls += 1
        result = original()
        if calls > 1:
            result["export_module"] = "0" * 64
        return result

    monkeypatch.setattr(export, "_code_pins", changed)
    with pytest.raises(CompanyStoreError, match="implementation changed"):
        export.export_current(root, **args(ready))
    assert snapshot(root) == before
    with database(root) as db:
        assert (
            db.execute("SELECT count(*) FROM systems WHERE system=?", (export.SYSTEM,)).fetchone()[
                0
            ]
            == 0
        )


def test_replay_rechecks_exact_retained_export_bytes(ready):
    root = ready[0]
    action = args(ready)
    result = export.export_current(root, **action)
    # Deliberate corruption is confined to this disposable test database.
    with database(root, True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET content=? WHERE system=? AND record=?",
            (b"{}", export.SYSTEM, result["native_pin"]["record"]),
        )
    before = snapshot(root)
    with pytest.raises(CompanyStoreError):
        export.export_current(root, **action)
    assert snapshot(root) == before


def test_export_availability_is_export_time_not_prior_target_time(ready):
    root = ready[0]
    action = {**args(ready), "event_at": "2027-02-05T04:00:00Z"}
    result = export.export_current(root, **action)
    ref = result["native_pin"]
    with database(root) as db:
        row = native(db, ref)
    metadata = json.loads(row["provenance"])
    assert row["event_at"] == row["available_at"] == metadata["exported_at"]
    assert metadata["prior_runtime_operation_at"] < row["available_at"]
    assert metadata["runtime_revision_at_export"] == 0
    assert metadata["authorization"] == "EXPLICIT_LOCAL_OPERATOR_EXPORT_NOT_RELEASE_APPROVAL"
    assert metadata["classification"] == export.QUALIFICATION
    store = CompanyStore(root)
    store.grant("READER", "ENG", ref["company"], ref["branch"], ref["system"])

    def read(at):
        return store.read_version(
            "READER",
            "ENG",
            ref["company"],
            ref["branch"],
            ref["system"],
            ref["record"],
            version=ref["version"],
            as_of=at,
        )

    with pytest.raises(CompanyStoreError):
        read("2027-02-05T03:59:59Z")
    visible = read("2027-02-05T04:00:00Z")
    assert visible["content"] == (root / "objects/initial.json").read_bytes()
    assert visible["sha256"] == result["current_sha256"]
