"""Independent IAM005 definition/code, native custody and bounded-read checks."""

import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_privileged_runtime as runtime
from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite.test_company_privileged_runtime import call, issue
from tests.audit_suite.test_company_privileged_runtime import prepared as fixture


@pytest.fixture
def prepared(tmp_path):
    return fixture.__wrapped__(tmp_path)


def inspect(prepared):
    return runtime.inspect(
        prepared[0],
        expected_runtime_sha256=prepared[1]["runtime_sha256"],
        as_of="2027-05-01T00:00:00Z",
    )


@pytest.mark.parametrize("operation", ["inspect", "execute"])
def test_changed_implementation_cannot_use_prior_runtime_code_pin(
    prepared, tmp_path, monkeypatch, operation
):
    changed = tmp_path / "company_privileged_runtime.py"
    original_directory = Path(runtime.__file__).parent
    for name in runtime._code():
        (tmp_path / name).write_bytes((original_directory / name).read_bytes())
    changed.write_bytes(changed.read_bytes() + b"\n# Changed maintained implementation\n")
    monkeypatch.setattr(runtime, "__file__", str(changed))
    with pytest.raises(CompanyStoreError):
        if operation == "inspect":
            inspect(prepared)
        else:
            runtime.execute(
                prepared[0],
                **call(prepared, "lease", "ISSUE_LEASE", issue(), "2027-05-01T00:00:00Z"),
            )


@pytest.mark.parametrize(
    "system,field,value",
    [
        ("privileged_definition", "provenance", "{}"),
        ("privileged_object", "origin", "UNVERIFIED"),
        ("privileged_definition", "event_at", "2026-01-01T00:00:00Z"),
        ("privileged_object", "available_at", "2028-01-01T00:00:00Z"),
        ("privileged_operation", "provenance", "{}"),
        ("privileged_operation", "command_id", "substituted-command"),
        ("privileged_operation", "input_digest", "0" * 64),
    ],
)
def test_native_metadata_is_part_of_retained_operation_integrity(prepared, system, field, value):
    runtime.execute(
        prepared[0],
        **call(prepared, "lease", "ISSUE_LEASE", issue(), "2027-05-01T00:00:00Z"),
    )
    with sqlite3.connect(prepared[0] / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute(f"UPDATE versions SET {field}=? WHERE system=?", (value, system))
    with pytest.raises(CompanyStoreError):
        inspect(prepared)


def test_oversized_command_receipt_rejected_before_fetching_content(prepared):
    runtime.execute(
        prepared[0],
        **call(prepared, "lease", "ISSUE_LEASE", issue(), "2027-05-01T00:00:00Z"),
    )
    with sqlite3.connect(prepared[0] / "company.sqlite3") as db:
        db.execute("DROP TRIGGER privileged_no_update")
        db.execute(
            "UPDATE privileged_commands SET receipt=?", ('"' + "x" * (2 * 1024 * 1024) + '"',)
        )

    class ReadSpy:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, statement, *args):
            if statement.startswith("SELECT command_id,input_digest,receipt"):
                raise AssertionError("Oversized receipt fetched before SQL size guard")
            return self.connection.execute(statement, *args)

    cfg = runtime._config(prepared[0], prepared[1]["runtime_sha256"])
    with runtime.database(prepared[0]) as db, pytest.raises(CompanyStoreError):
        runtime._history(ReadSpy(db), cfg)


def test_null_native_timestamp_cannot_bypass_metadata_prefetch_bound(prepared):
    with sqlite3.connect(prepared[0] / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET event_at=NULL,provenance=? WHERE system='privileged_object'",
            ("x" * (2 * 1024 * 1024),),
        )

    class ReadSpy:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, statement, *args):
            if statement.startswith("SELECT * FROM versions"):
                raise AssertionError("Oversized metadata fetched before SQL size guard")
            return self.connection.execute(statement, *args)

    cfg = runtime._config(prepared[0], prepared[1]["runtime_sha256"])
    with runtime.database(prepared[0]) as db, pytest.raises(CompanyStoreError):
        runtime._history(ReadSpy(db), cfg)
