"""Adversarial examination of receipts and recorded decisions, without mode keys."""

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timedelta

import pytest

from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_privacy_methods import examine

AS_OF = "2028-01-02T09:00:00Z"


def retained(system, record, details, *, at="2027-09-21T09:00:00+00:00"):
    available = (datetime.fromisoformat(at) + timedelta(minutes=10)).isoformat()
    body = {
        "service_id": "neutral-service",
        "dataset_id": "neutral-dataset",
        "customer_id": "neutral-customer",
        "contracting_entity_id": "neutral-entity",
        "payload_bytes": 0,
        "real_phi_payload": False,
        "real_world_processing_or_transfer": False,
        "event_at": at,
        "available_at": available,
        "dependencies": [],
        **details,
    }
    content = json.dumps(body, sort_keys=True).encode()
    source = {
        "company": "NEUTRAL",
        "branch": "selected",
        "system": "privacyops." + system,
        "record": record,
        "version": 1,
        "sha256": hashlib.sha256(content).hexdigest(),
        "event_at": at,
        "available_at": available,
        "imported_at": "2026-10-01T00:00:00Z",
    }
    return {
        "source": source,
        "receipt": {"source": deepcopy(source)},
        "artifact_id": "ART-" + system + "-" + record,
        "artifact_sha256": source["sha256"],
        "retained_bytes": content,
        "content_type": "application/json",
        "logical_family": "privacyops",
        "logical_system": system,
    }


def change(row, **fields):
    body = json.loads(row["retained_bytes"])
    body.update(fields)
    row["retained_bytes"] = json.dumps(body, sort_keys=True).encode()
    row["source"]["sha256"] = hashlib.sha256(row["retained_bytes"]).hexdigest()
    row["source"]["event_at"] = body["event_at"]
    row["source"]["available_at"] = body["available_at"]
    row["artifact_sha256"] = row["source"]["sha256"]
    row["receipt"]["source"] = deepcopy(row["source"])


def history(*, permitted=True, delivered=None):
    if delivered is None:
        delivered = permitted
    common = {"case_id": "arbitrary-case", "recipient_id": "recipient-1"}
    rows = [
        retained(
            "privacy_request",
            "req",
            {**common, "inlet_sequence": 1, "route": "selected-token-route"},
        ),
        retained(
            "privacy_customer_decision",
            "customer",
            {**common, "decision": "PERMIT" if permitted else "HOLD"},
        ),
        retained(
            "privacy_gate_decision",
            "gate",
            {
                **common,
                "decision": "PERMIT" if permitted else "HOLD",
                "allowed_scope": ["token"] if permitted else [],
            },
        ),
        retained(
            "privacy_release",
            "release",
            {
                **common,
                "execution_status": "DELIVERED" if delivered else "WITHHELD",
                "released_scope": ["token"] if delivered else [],
                "worker_authority_source": "selected-ledger",
            },
        ),
        retained(
            "privacy_receipt",
            "receipt",
            {
                **common,
                "status": "RECIPIENT_ACKNOWLEDGED" if delivered else "NO_DELIVERY",
                "copy_in_recipient_scope": delivered,
            },
        ),
        retained(
            "privacy_reconciliation",
            "close",
            {
                "period": {"start": "2027-09-01T00:00:00Z", "end": "2027-09-30T23:59:59Z"},
                "case_ids": [common["case_id"]],
                "inlet_sequence_first": 1,
                "inlet_sequence_last": 1,
                "inlet_sequence_gaps": [],
                "customer_decision_count": 1,
                "counsel_gate_count": 1,
                "execution_journal_count": 1,
                "delivery_status_count": 1,
                "delivered_count": int(delivered),
                "withheld_count": int(not delivered),
                "delivery_authority_mismatch_count": int(delivered and not permitted),
            },
            at="2027-10-01T00:00:00+00:00",
        ),
    ]
    for hour, row in enumerate(rows[:-1], 9):
        at = f"2027-09-21T{hour:02}:00:00+00:00"
        change(
            row,
            event_at=at,
            available_at=(datetime.fromisoformat(at) + timedelta(minutes=10)).isoformat(),
        )
    return rows


def test_one_method_recomputes_permitted_and_held_cases_without_branch_answers():
    for permitted in (True, False):
        actual = examine(history(permitted=permitted), as_of=AS_OF)
        assert actual["selected_request_count"] == 1
        assert actual["selected_population_corroborated"]
        assert not actual["recorded_mismatch_case_ids"]
        assert not actual["enterprise_population_established"]
        assert not actual["executable_routing_reperformed"]
        assert not actual["legal_applicability_decided"]


def test_recorded_delivery_against_current_hold_is_independently_found():
    actual = examine(history(permitted=False, delivered=True), as_of=AS_OF)
    assert actual["recorded_mismatch_case_ids"] == ["arbitrary-case"]
    assert actual["recomputed_counts"]["delivery_authority_mismatch_count"] == 1
    assert (
        "DELIVERY_WITHOUT_CURRENT_COUNSEL_PERMISSION" in actual["cases"][0]["recorded_mismatches"]
    )


def test_cached_parsed_document_cannot_override_retained_bytes():
    rows = history(permitted=False, delivered=True)
    rows[2]["document"] = {"decision": "PERMIT"}
    assert examine(rows, as_of=AS_OF)["recorded_mismatch_case_ids"]


def test_changed_retained_bytes_are_rejected_before_examination():
    rows = history()
    rows[0]["retained_bytes"] += b" "
    with pytest.raises(ProcedureError, match="artifact hash"):
        examine(rows, as_of=AS_OF)


def test_receipt_cannot_be_replaced_with_another_branch_tuple():
    rows = history()
    rows[0]["receipt"]["source"]["branch"] = "other"
    with pytest.raises(ProcedureError, match="receipt custody"):
        examine(rows, as_of=AS_OF)


def test_duplicate_native_row_is_not_an_additional_request():
    rows = history()
    with pytest.raises(ProcedureError, match="Duplicate collected"):
        examine(rows + [deepcopy(rows[0])], as_of=AS_OF)


def test_future_source_cannot_enter_the_observed_case_census():
    with pytest.raises(ProcedureError, match="after examination clock"):
        examine(history(), as_of="2027-09-30T00:00:00Z")


def test_future_exact_dependency_is_not_available_for_an_earlier_gate():
    rows = history()
    change(rows[1], available_at="2027-09-22T00:00:00+00:00")
    ref = {k: v for k, v in rows[1]["source"].items() if k != "imported_at"}
    change(rows[2], dependencies=[ref])
    with pytest.raises(ProcedureError, match="unavailable at its event"):
        examine(rows, as_of=AS_OF)


def test_exact_cross_branch_dependency_cannot_be_treated_as_authorized():
    rows = history()
    ref = {k: v for k, v in rows[1]["source"].items() if k != "imported_at"}
    ref["branch"] = "other"
    change(rows[2], dependencies=[ref])
    with pytest.raises(ProcedureError, match="branch authority"):
        examine(rows, as_of=AS_OF)


def test_false_monthly_claim_is_reported_against_actual_collected_membership():
    rows = history()
    change(rows[-1], delivered_count=99)
    actual = examine(rows, as_of=AS_OF)
    assert actual["month_close_discrepancies"]["delivered_count"] == {
        "claimed": 99,
        "recomputed": 1,
    }


def test_pre_end_close_does_not_establish_the_remaining_month_tail():
    rows = history()
    change(rows[-1], event_at="2027-09-30T20:00:00+00:00", available_at="2027-09-30T20:10:00+00:00")
    actual = examine(rows, as_of=AS_OF)
    assert not actual["selected_population_corroborated"]
    assert actual["unestablished_period_tail"]["through"] == "2027-09-30T23:59:59Z"


def test_missing_gate_remains_unknown_and_does_not_claim_zero_delivery_mismatches():
    rows = [r for r in history() if r["logical_system"] != "privacy_gate_decision"]
    actual = examine(rows, as_of=AS_OF)
    assert actual["delivery_authority_unknown_case_ids"] == ["arbitrary-case"]
    assert actual["recomputed_counts"]["delivery_authority_mismatch_count"] is None
    assert not actual["selected_population_corroborated"]


def test_wrong_recipient_or_scope_is_visible_in_selected_record_examination():
    rows = history()
    change(rows[3], recipient_id="other-recipient", released_scope=["unapproved-token"])
    actual = examine(rows, as_of=AS_OF)
    assert (
        "DELIVERY_SCOPE_DIFFERS_FROM_COUNSEL_PERMISSION"
        in actual["cases"][0]["recorded_mismatches"]
    )
    assert "DELIVERY_RECIPIENT_DIFFERS_FROM_GATE" in actual["cases"][0]["recorded_mismatches"]


def test_out_of_period_request_is_not_hidden_by_a_matching_export_count():
    rows = history()
    change(rows[0], event_at="2027-10-02T09:00:00+00:00", available_at="2027-10-02T09:10:00+00:00")
    actual = examine(rows, as_of=AS_OF)
    assert actual["requests_outside_declared_period"] == ["arbitrary-case"]
    assert not actual["selected_population_corroborated"]


def test_counsel_first_published_after_delivery_is_not_current_permission():
    rows = history()
    change(rows[2], event_at="2027-09-22T11:00:00+00:00", available_at="2027-09-22T11:10:00+00:00")
    actual = examine(rows, as_of=AS_OF)
    assert actual["recorded_mismatch_case_ids"] == ["arbitrary-case"]
    assert any(
        v["source_system"] == "privacy_gate_decision"
        for v in actual["cases"][0]["causal_availability_violations"]
    )


def test_same_case_identifier_does_not_join_a_different_service_permission():
    rows = history()
    change(rows[2], service_id="different-service")
    with pytest.raises(ProcedureError, match="scopes differ"):
        examine(rows, as_of=AS_OF)


def test_routing_alias_cannot_replace_actual_native_case_system():
    rows = history()
    rows[2]["source"]["system"] = "privacyops.privacy_request"
    rows[2]["receipt"]["source"] = deepcopy(rows[2]["source"])
    with pytest.raises(ProcedureError, match="actual native system"):
        examine(rows, as_of=AS_OF)


def test_unknown_withheld_receipt_state_is_not_known_nondelivery():
    rows = history(permitted=False)
    change(rows[4], status="EXPORT_STATUS_UNDETERMINED")
    actual = examine(rows, as_of=AS_OF)
    assert not actual["cases"][0]["recipient_status_known"]
    assert "RECIPIENT_STATUS_UNDETERMINED" in actual["cases"][0]["recorded_mismatches"]


def test_string_scopes_cannot_be_compared_as_sets_of_characters():
    rows = history()
    change(rows[2], allowed_scope="token")
    change(rows[3], released_scope="token")
    with pytest.raises(ProcedureError, match="string-list"):
        examine(rows, as_of=AS_OF)


def test_integer_one_does_not_establish_a_boolean_recipient_copy():
    rows = history()
    change(rows[4], copy_in_recipient_scope=1)
    with pytest.raises(ProcedureError, match="boolean recipient-copy"):
        examine(rows, as_of=AS_OF)


def test_duplicate_tokens_are_not_collapsed_into_a_valid_scope():
    rows = history()
    change(rows[3], released_scope=["token", "token"])
    with pytest.raises(ProcedureError, match="Duplicate permission/release"):
        examine(rows, as_of=AS_OF)


def test_recipient_identity_cannot_be_an_integer_in_matching_records():
    rows = history()
    for row in rows[:-1]:
        change(row, recipient_id=123)
    with pytest.raises(ProcedureError, match="recipient identity"):
        examine(rows, as_of=AS_OF)


def test_boolean_count_claim_is_not_equivalent_to_integer_one():
    rows = history()
    change(rows[-1], delivered_count=True)
    assert "delivered_count" in examine(rows, as_of=AS_OF)["month_close_discrepancies"]


def test_huge_forged_inlet_range_is_a_discrepancy_without_range_allocation():
    rows = history()
    change(rows[-1], inlet_sequence_last=10**15)
    actual = examine(rows, as_of=AS_OF)
    assert not actual["inlet_sequence_matches"]
    assert not actual["selected_population_corroborated"]
