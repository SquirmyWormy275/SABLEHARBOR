"""Independent local delivery integrity and retained-history boundary checks."""

import pytest

from enterprise.audit_suite import company_policy_delivery_runtime as runtime
from enterprise.audit_suite.company_backup_runtime import database
from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite import test_company_policy_delivery_runtime as fixture
from tests.audit_suite.test_company_policy_delivery_runtime import (
    args,
    call,
    view,
)


@pytest.fixture
def prepared(tmp_path):
    return fixture.prepared.__wrapped__(tmp_path)


def test_redelivery_requires_new_read_before_simulated_assertion(prepared):
    call(prepared, "first-delivery")
    call(prepared, "first-read", "READ_RETURN")
    call(prepared, "second-delivery")
    state = view(prepared)
    assert not state["report"]["recipients"][0]["read_return_current_delivery"]
    before = (prepared[0] / "company.sqlite3").read_bytes()
    with pytest.raises(CompanyStoreError, match="current retained read"):
        call(
            prepared,
            "stale-assertion",
            "RECIPIENT_ASSERTION",
            parameters={
                "recipient_id": "AS-P007",
                "document_pin": state["report"]["selected_document_pin"],
                "read_command_id": "first-read",
                "statement": "Explicit simulated statement",
            },
        )
    assert (prepared[0] / "company.sqlite3").read_bytes() == before
    assert view(prepared)["revision"] == 3


@pytest.mark.parametrize("system", ["policy_definition", "policy_document", "policy_operation"])
def test_native_import_time_is_exact_retained_metadata(prepared, system):
    call(prepared, "delivery")
    with database(prepared[0], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET imported_at='2030-01-01T00:00:00Z' WHERE system=?", (system,)
        )
    with pytest.raises(CompanyStoreError, match="metadata"):
        view(prepared)


@pytest.mark.parametrize("version", [True, 1.0])
def test_document_pin_version_requires_exact_integer_before_copy(prepared, version):
    request = args(prepared, "malformed")
    request["parameters"]["document_pin"]["version"] = version
    with pytest.raises(CompanyStoreError):
        runtime.execute(prepared[0], **request)
    assert list((prepared[0] / "attempts").iterdir()) == []
    assert view(prepared)["revision"] == 0


def test_exact_replay_at_command_limit_preserves_native_and_mailbox_bytes(prepared, monkeypatch):
    monkeypatch.setattr(runtime, "MAX_COMMANDS", 2)
    request = args(prepared, "first")
    first = runtime.execute(prepared[0], **request)
    call(prepared, "last", "RECONCILE", parameters={})
    paths = sorted(p for p in prepared[0].rglob("*") if p.is_file())
    before = {str(p): p.read_bytes() for p in paths}
    assert runtime.execute(prepared[0], **request) == first
    assert before == {str(p): p.read_bytes() for p in paths}
    with pytest.raises(CompanyStoreError, match="command limit"):
        call(prepared, "extra", "RECONCILE", parameters={})
