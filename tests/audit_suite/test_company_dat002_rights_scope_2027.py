"""Selected DAT002 rights inquiry stays a bounded company-native discovery source."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import company_dat002_rights_scope_2027 as rights
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


@pytest.fixture(scope="module")
def context():
    return rights._context(REPOSITORY, PRIVATE)


def test_exact_fifteen_untargeted_and_two_discovery_leads(context):
    assert len(rights.UNTARGETED_TASKS) == 15
    assert len(set(rights.UNTARGETED_TASKS)) == 15
    assert rights.DISCOVERY_TASKS == (
        "TASK-SH-DAT-002-corporate-ACTION-H-RIGHTS-ASSISTANCE",
        "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.501",
    )
    assert set(context) == {"CLEAN", "MESSY"}
    for scenario in rights.BRANCHES:
        assert set(context[scenario]) == {
            "purpose_request",
            "purpose_review",
            "privacy_case_queue",
            "purpose_reconciliation",
        }


def test_clean_and_messy_native_causality_and_unresolved_gates(context):
    clean = rights._expected_rows(context, "CLEAN")
    messy = rights._expected_rows(context, "MESSY")
    assert [row["system"] for row in clean] == [
        "rights_intake",
        "record_scope_review",
        "authority_review",
        "rights_queue",
        "rights_reconciliation",
    ]
    assert [row["system"] for row in messy] == [
        "rights_intake",
        "record_scope_review",
        "rights_queue",
        "authority_review",
        "rights_exception",
        "rights_reconciliation",
    ]
    for scenario, rows in (("CLEAN", clean), ("MESSY", messy)):
        assert rows[0]["body"]["source_previous"] is None
        assert rows[0]["body"]["upstream_purpose_originals"] == {
            name: value["ref"] for name, value in context[scenario].items()
        }
        assert (
            rows[0]["event_at"] > context[scenario]["purpose_reconciliation"]["ref"]["available_at"]
        )
        for previous, current in zip(rows, rows[1:], strict=False):
            assert current["body"]["source_previous"]["sha256"] == previous["sha256"]
            assert current["event_at"] > previous["available_at"]
        assert all(row["body"]["payload_bytes"] == 0 for row in rows)
        assert all(row["body"]["actual_request_or_customer_instruction"] is False for row in rows)
        assert all(row["body"]["actual_rights_response_or_disclosure"] is False for row in rows)
        assert all(row["body"]["actual_hipaa_applicability"] == "UNDETERMINED" for row in rows)
        assert all(row["body"]["task_credit"] is False for row in rows)
        assert rows[-1]["body"]["complete_period_population"] is False
        assert rows[-1]["body"]["actual_disclosure_count"] == 0
        assert rows[-1]["body"]["accepted_amendment_count"] == 0
        assert rows[-1]["body"]["accounting_completion_count"] == 0
    assert clean[1]["body"]["premature_no_record_mark"] is False
    assert clean[2]["body"]["release_decision"] == "HOLD_NO_RESPONSE"
    assert messy[1]["body"]["premature_no_record_mark"] is True
    assert messy[2]["body"]["shortcut_detected"] is True
    assert messy[4]["body"]["exception_id"] == rights.EXCEPTION_ID
    assert messy[4]["body"]["status"] == "OPEN"
    assert messy[-1]["body"]["open_scope_exception_ids"] == [rights.EXCEPTION_ID]


def test_selected_purpose_holds_cannot_be_promoted(context):
    changed = deepcopy(context)
    changed["CLEAN"]["purpose_reconciliation"]["body"]["actual_transfer_count"] = 1
    with pytest.raises(CompanyStoreError, match="purpose hold"):
        rights._expected_rows(changed, "CLEAN")
    changed = deepcopy(context)
    changed["MESSY"]["purpose_request"]["ref"]["branch"] = rights.purpose.BRANCHES["CLEAN"]
    with pytest.raises(CompanyStoreError, match="native identity"):
        rights._expected_rows(changed, "MESSY")
    with pytest.raises(CompanyStoreError, match="Unknown rights branch"):
        rights._expected_rows(context, "UNKNOWN")


def test_create_verify_and_receipt_tamper(tmp_path, context, monkeypatch):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(rights, "_context", lambda *_: context)
    output = parent / "run"
    rights.create(output, repository=tmp_path, private_repository=tmp_path)
    assert (
        rights.verify(output, repository=tmp_path, private_repository=tmp_path)[
            "native_version_count"
        ]
        == 11
    )
    receipt = output / "RECEIPT.json"
    body = json.loads(receipt.read_text())
    assert body["actual_requests_or_external_responses"] == 0
    assert body["open_scope_exception_ids"] == {"CLEAN": [], "MESSY": [rights.EXCEPTION_ID]}
    body["complete_record_or_period_population"] = True
    receipt.write_text(json.dumps(body))
    with pytest.raises(CompanyStoreError):
        rights.verify(output, repository=tmp_path, private_repository=tmp_path)


def test_pinned_source_and_private_sidecar_rejection(tmp_path, monkeypatch):
    pins = dict(rights.SOURCE_PINS)
    key = next(iter(pins))
    pins[key] = "0" * 64
    monkeypatch.setattr(rights, "SOURCE_PINS", pins)
    with pytest.raises(CompanyStoreError, match="Pinned scenario"):
        rights._context(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    db = root / "company.sqlite3"
    db.write_bytes(b"fixture")
    db.chmod(0o600)
    (root / "company.sqlite3-wal").symlink_to("missing")
    with pytest.raises(CompanyStoreError, match="sidecar"):
        rights.purpose._frozen({"database": db})
