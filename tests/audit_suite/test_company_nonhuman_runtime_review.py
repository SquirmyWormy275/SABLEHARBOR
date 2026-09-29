"""Independent source/runtime integrity boundaries using genuine disposable seed chains."""

import pytest

from enterprise.audit_suite import company_nonhuman_runtime as runtime
from enterprise.audit_suite.company_backup_runtime import database
from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite import test_company_nonhuman_runtime as fixtures


@pytest.fixture
def prepared(tmp_path):
    return fixtures.prepared.__wrapped__(tmp_path)


def inspect(p):
    return runtime.inspect(
        p[0], expected_runtime_sha256=p[1]["runtime_sha256"], as_of="2027-07-02T00:00:00Z"
    )


def test_declaration_metadata_bounded_before_materialization(prepared):
    p = prepared
    with database(p[2]["declaration_root"], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("UPDATE versions SET provenance=?", ("X" * (1024 * 1024),))
    with pytest.raises(CompanyStoreError):
        inspect(p)


def test_registered_custody_cannot_diverge_from_runtime_definition(prepared):
    p = prepared
    with database(p[0], True) as db:
        db.execute("UPDATE systems SET owner='UNDECLARED' WHERE system='nonhuman_operation'")
    with pytest.raises(CompanyStoreError):
        inspect(p)


def test_exact_completed_replay_survives_command_limit(prepared, monkeypatch):
    # Exercise the actual boundary with two genuine committed commands, not 128 expensive seeds.
    p = prepared
    monkeypatch.setattr(runtime, "MAX_COMMANDS", 2)
    opening = inspect(p)
    command = {
        "expected_runtime_sha256": p[1]["runtime_sha256"],
        "expected_revision": 0,
        "expected_state_sha256": opening["state_sha256"],
        "command_id": "first",
        "action": "RECONCILE",
        "payload": {},
        "actor_id": p[3]["primary_person_id"],
        "event_at": "2027-07-02T00:00:00Z",
    }
    first = runtime.execute(p[0], **command)
    later = inspect(p)
    runtime.execute(
        p[0],
        **(
            command
            | {
                "command_id": "second",
                "expected_revision": 1,
                "expected_state_sha256": later["state_sha256"],
            }
        ),
    )
    before = (p[0] / "company.sqlite3").read_bytes()
    assert runtime.execute(p[0], **command) == first
    assert (p[0] / "company.sqlite3").read_bytes() == before
    with pytest.raises(CompanyStoreError):
        runtime.execute(
            p[0],
            **(
                command
                | {
                    "command_id": "third",
                    "expected_revision": 2,
                    "expected_state_sha256": inspect(p)["state_sha256"],
                }
            ),
        )
    assert (p[0] / "company.sqlite3").read_bytes() == before


@pytest.mark.parametrize("target", ["state_revision", "native_version", "systems_null"])
def test_noninteger_scalar_quota_precedes_materialization(prepared, monkeypatch, target):
    import sqlite3
    from contextlib import contextmanager

    p = prepared
    with database(p[0], True) as db:
        if target == "state_revision":
            db.execute("UPDATE nonhuman_state SET revision=?", ("X" * (1024 * 1024),))
        elif target == "systems_null":
            db.execute(
                "UPDATE systems SET company=NULL, owner=? WHERE system='nonhuman_operation'",
                ("X" * (1024 * 1024),),
            )
        else:
            db.execute("DROP TRIGGER no_version_update")
            db.execute(
                "UPDATE versions SET version=? WHERE system='nonhuman_definition'",
                ("X" * (1024 * 1024),),
            )
    original = runtime.database

    @contextmanager
    def checked(*a, **kw):
        with original(*a, **kw) as db:

            def row_factory(cursor, row):
                assert not any(
                    isinstance(v, str) and len(v) > runtime.MAX_ROW_BYTES for v in row
                ), "Unbounded scalar materialized"
                return sqlite3.Row(cursor, row)

            db.row_factory = row_factory
            yield db

    monkeypatch.setattr(runtime, "database", checked)
    with pytest.raises(CompanyStoreError):
        inspect(p)


def test_declaration_import_time_remains_exact_after_initialization(prepared):
    p = prepared
    with database(p[2]["declaration_root"], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("UPDATE versions SET imported_at='2026-01-01T00:00:00.000000+00:00'")
    with pytest.raises(CompanyStoreError):
        inspect(p)
