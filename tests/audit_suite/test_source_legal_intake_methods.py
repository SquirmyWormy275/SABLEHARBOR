"""Neutral retained bytes: custody, dynamic census and immutable late corrections."""

import hashlib
import json
from copy import deepcopy

import pytest

from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_legal_intake_methods import examine

AS_OF = "2028-01-15T09:00:00Z"
START, END, STOP = "2027-09-01T00:00:00Z", "2027-09-30T23:59:59Z", "2027-10-01T00:00:00Z"
CHANNELS = ["NEUTRAL-INBOX", "NEUTRAL-OPERATIONS"]
SCOPE = {
    "company_id": "NEUTRAL-LEGAL",
    "boundary": "Single neutral company service legal intake",
    "period_start": START,
    "period_end": END,
    "unregistered_channel_completeness": "NOT_ESTABLISHED",
    "excluded": ["unregistered channels", "other services", "real-world matters"],
}


def retained(family, system, rid, body, at, *, version=1):
    document = {"record_id": rid, "engineering_neutral_fixture": True, **body}
    raw = json.dumps(document, sort_keys=True).encode()
    source = {
        "company": "NEUTRAL-LEGAL",
        "branch": "selected-operations",
        "system": family + "." + system,
        "record": rid,
        "version": version,
        "event_at": at,
        "available_at": at,
        "imported_at": "2026-10-01T00:00:00Z",
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    return {
        "source": source,
        "receipt": {"source": deepcopy(source)},
        "retained_bytes": raw,
        "artifact_sha256": source["sha256"],
        "content_type": "application/json",
        "logical_family": family,
        "logical_system": system,
    }


def replace(row, **fields):
    document = json.loads(row["retained_bytes"])
    document.update(fields)
    row["retained_bytes"] = json.dumps(document, sort_keys=True).encode()
    row["source"]["sha256"] = hashlib.sha256(row["retained_bytes"]).hexdigest()
    row["artifact_sha256"] = row["source"]["sha256"]
    row["receipt"]["source"] = deepcopy(row["source"])


def original_reference(row):
    return {k: v for k, v in row["source"].items() if k != "imported_at"}


def history(*, channels=None, omitted=False, correction=False, startup=False):
    channels = channels or CHANNELS
    established = "2027-09-01T09:00:00Z" if startup else "2027-08-31T09:00:00Z"
    rows = [
        retained(
            "legint",
            "intake_channel_register",
            "REGISTER",
            {"channels": channels, "scope": SCOPE},
            "2027-08-31T08:00:00Z",
        )
    ]
    for channel in channels:
        rows.append(
            retained(
                "legaloriginals",
                "legal_channel_configuration",
                channel,
                {
                    "channel_id": channel,
                    "retained_intake_registry_id": "REGISTER",
                    "operation_established_from": established,
                    "scope": SCOPE,
                },
                established,
            )
        )
    attachment = retained(
        "legaloriginals",
        "legal_inbound_attachment",
        "ATTACHMENT-X",
        {
            "channel_id": channels[-1],
            "inbound_message_id": "MESSAGE-X",
            "text": "Neutral contract questions",
            "official_notice_or_case_identifier": None,
        },
        "2027-09-07T10:00:00Z",
    )
    message = retained(
        "legaloriginals",
        "legal_inbound_message",
        "MESSAGE-X",
        {
            "channel_id": channels[-1],
            "received_at": "2027-09-07T10:00:00Z",
            "text": "Please clarify contract handling",
            "subject": "Neutral contract question",
            "sender_role": "Neutral contract correspondent",
            "actual_external_message": False,
            "attachment_refs": [original_reference(attachment)],
        },
        "2027-09-07T10:00:00Z",
    )
    rows.extend([attachment, message])
    for channel in channels:
        declared = ["MESSAGE-X"] if channel == channels[-1] else []
        rows.append(
            retained(
                "legaloriginals",
                "legal_channel_export",
                "EXPORT-" + channel,
                {
                    "channel_id": channel,
                    "event_window_start": START,
                    "event_window_end_exclusive": STOP,
                    "source_available_as_of": "2027-10-01T09:00:00Z",
                    "source_system": "legal_inbound_message",
                    "event_filter": "received_at >= start AND received_at < end",
                    "registered_channels_only": True,
                    "record_count": len(declared),
                    "declared_message_ids": declared,
                    "query": (
                        "SELECT original versions by company, branch, channel and window"
                    ),
                    "channel_operation_start": established,
                    "window_operational_coverage_start": established if startup else START,
                    "full_window_channel_continuity_established": not startup,
                },
                "2027-10-01T09:00:00Z",
            )
        )
        items = (
            [
                {
                    "item_id": "MESSAGE-X",
                    "received_at": "2027-09-07T10:00:00Z",
                    "subject": "Neutral contract question",
                    "sender_role": "Neutral contract correspondent",
                }
            ]
            if declared
            else []
        )
        rows.append(
            retained(
                "legint",
                "intake_channel_ledger",
                "LEDGER-" + channel,
                {
                    "channel_id": channel,
                    "window_start": START,
                    "window_end": END,
                    "export_cutoff": "2027-09-30T13:00:00Z",
                    "remaining_day_followup_required": True,
                    "intake_items": items,
                    "record_count": len(items),
                    "scope": SCOPE,
                },
                "2027-09-30T14:00:00Z",
            )
        )
    selected = channels[:-1] if omitted else channels
    rows.append(
        retained(
            "legint",
            "monthly_intake_screening",
            "SCREEN",
            {
                "registry_record_id": "REGISTER",
                "reviewed_channel_ids": selected,
                "ledger_record_ids": ["LEDGER-" + c for c in selected],
                "screening_state": "CLOSED" if omitted else "PRELIMINARY",
                "reviewed_through": "2027-09-30T15:00:00Z",
                "scope": SCOPE,
            },
            "2027-09-30T15:00:00Z",
        )
    )
    rows.append(
        retained(
            "legint",
            "intake_tail_reconciliation",
            "TAIL",
            {
                "related_screening_id": "SCREEN",
                "channel_ids": selected,
                "window_start": "2027-09-30T13:00:00Z",
                "window_end": END,
                "additional_intake_items": [],
                "extract_state": "COMPLETED_RECORDED_CHANNELS",
                "scope": SCOPE,
            },
            "2027-10-01T09:00:00Z",
        )
    )
    rows.append(
        retained(
            "legint",
            "quarterly_legal_review",
            "QUARTER",
            {"screening_record_ids": ["SCREEN"], "review_state": "FILED", "scope": SCOPE},
            "2027-09-30T16:00:00Z",
        )
    )
    rows.append(
        retained(
            "legint",
            "quarterly_legal_review",
            "QUARTER",
            {
                "tail_record_versions": {"TAIL": 1},
                "review_state": "RECONCILIATION_REQUIRED"
                if omitted
                else "DECLARED_WINDOW_RECONCILED",
                "scope": SCOPE,
            },
            "2027-10-02T10:00:00Z",
            version=2,
        )
    )
    if correction:
        assert omitted
        rows.append(
            retained(
                "legint",
                "legal_exception_register",
                "EXCEPTION",
                {"status": "OPEN", "affected_records": ["SCREEN", "QUARTER"], "scope": SCOPE},
                "2027-11-04T10:00:00Z",
            )
        )
        rows.append(
            retained(
                "legint",
                "monthly_intake_screening",
                "SCREEN",
                {
                    "registry_record_id": "REGISTER",
                    "reviewed_channel_ids": channels,
                    "ledger_record_ids": ["LEDGER-" + c for c in channels],
                    "screening_state": "CLOSED_AFTER_RECONCILIATION",
                    "classification_record_ids": ["MESSAGE-X"],
                    "historical_exception_id": "EXCEPTION",
                    "scope": SCOPE,
                },
                "2027-11-10T10:00:00Z",
                version=2,
            )
        )
        rows.append(
            retained(
                "legint",
                "intake_tail_reconciliation",
                "TAIL",
                {
                    "related_screening_id": "SCREEN",
                    "related_screening_version": 2,
                    "channel_ids": channels,
                    "window_start": "2027-09-30T13:00:00Z",
                    "window_end": END,
                    "additional_intake_items": [],
                    "extract_state": "RETROSPECTIVE_RECONCILIATION",
                    "scope": SCOPE,
                },
                "2027-11-10T11:00:00Z",
                version=2,
            )
        )
        rows.append(
            retained(
                "legint",
                "quarterly_legal_review",
                "QUARTER",
                {
                    "tail_record_versions": {"TAIL": 2},
                    "review_state": "DECLARED_WINDOW_RECONCILED",
                    "historical_exception_id": "EXCEPTION",
                    "scope": SCOPE,
                },
                "2027-11-12T10:00:00Z",
                version=3,
            )
        )
    rows.append(
        retained(
            "legint",
            "legal_matter_classification",
            "MESSAGE-X",
            {
                "source_item_id": "MESSAGE-X",
                "classification": "CONTRACTUAL_INQUIRY",
                "official_regulator_notice": False,
                "scope": SCOPE,
            },
            "2027-11-09T09:00:00Z" if correction else "2027-09-08T09:00:00Z",
        )
    )
    rows.append(
        retained(
            "legint",
            "regulatory_response_playbook",
            "PLAYBOOK",
            {
                "procedure": [
                    "Preserve correspondence",
                    "Counsel authenticates authority and scope",
                ],
                "2027_primary_authority_status": "RECHECK_AT_TRIGGER",
                "scope": SCOPE,
            },
            "2027-09-02T09:00:00Z",
        )
    )
    return rows


def one(rows, system, *, version=1):
    return next(
        r for r in rows if r["logical_system"] == system and r["source"]["version"] == version
    )


def kinds(result):
    return {d["kind"] for d in result["documentary_discrepancies"]}


def test_dynamic_channel_denominator_original_custody_and_no_external_conclusion():
    for channel_count in (2, 5):
        result = examine(
            history(channels=[f"NEUTRAL-{i}" for i in range(channel_count)]), as_of=AS_OF
        )
        assert result["expected_channel_month_count"] == channel_count
        assert result["original_message_identity_count"] == 1
        assert result["selected_export_original_roster_corroborated"]
        assert result["original_attachment_joins"][0]["attachment_sources"]
        assert not result["enterprise_nonoccurrence_established"]
        assert not result["independent_legal_conclusion"] and result["audit_task_credit"] is None
        assert not result["classification_history"][0][
            "explicit_classification_to_playbook_link_established"
        ]


def test_later_correction_preserves_historical_omission_and_open_quarter_exception():
    result = examine(history(omitted=True, correction=True), as_of=AS_OF)
    assert result["screening_history"][0]["missing_channel_ids"] == [CHANNELS[-1]]
    assert result["screening_history"][1]["missing_channel_ids"] == []
    assert "SCREENING_REGISTERED_CHANNEL_OMISSION" in kinds(result)
    assert result["quarter_history"][-1]["recorded_state"] == "DECLARED_WINDOW_RECONCILED"
    assert result["quarter_history"][-1]["referenced_exception_status"] == "OPEN"
    assert result["exception_history"][0]["recorded_status"] == "OPEN"
    assert not result["tail_history"][-1]["erases_prior_screening_observation"]


def test_startup_gap_is_independent_of_matching_counts_and_false_whole_period_claim():
    result = examine(history(startup=True), as_of=AS_OF)
    assert result["selected_export_original_roster_corroborated"]
    assert len(result["channel_continuity_gaps"]) == 2
    assert not result["whole_period_channel_continuity_established"]
    assert all(not r["full_window_channel_continuity"] for r in result["monthly_exports"])


def test_stored_sql_is_never_executed_and_census_comes_from_typed_window():
    rows = history()
    replace(one(rows, "legal_channel_export"), query="DROP TABLE versions; SELECT imaginary counts")
    result = examine(rows, as_of=AS_OF)
    assert result["original_message_identity_count"] == 1
    assert not result["monthly_exports"][0]["query_executed"]


def test_fully_resealed_false_export_count_is_recomputed_not_trusted():
    rows = history()
    replace(one(rows, "legal_channel_export"), record_count=44)
    result = examine(rows, as_of=AS_OF)
    assert "EXPORT_ORIGINAL_COUNT_OR_ROSTER_MISMATCH" in kinds(result)
    assert not result["selected_export_original_roster_corroborated"]


def test_uncollected_original_and_attachment_remain_unknown_not_no_event():
    rows = [r for r in history() if r["logical_system"] != "legal_inbound_message"]
    result = examine(rows, as_of=AS_OF)
    assert not result["selected_export_original_roster_corroborated"]
    assert result["unresolved_source_links"] and result["unmatched_retained_attachment_sources"]
    assert "EXPORT_ORIGINAL_COUNT_OR_ROSTER_MISMATCH" in kinds(result)


def test_cached_document_cannot_supply_original_evidence():
    rows = history()
    one(rows, "monthly_intake_screening")["document"] = {"reviewed_channel_ids": []}
    result = examine(rows, as_of=AS_OF)
    assert result["screening_history"][0]["missing_channel_ids"] == []


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("bytes", "artifact hash"),
        ("receipt", "receipt differs"),
        ("branch", "One authorized"),
        ("logical", "route differs"),
        ("future", "examination clock"),
        ("scope", "boundary"),
        ("duplicate", "Duplicate"),
        ("count_bool", "integer"),
        ("channels_string", "string list"),
        ("continuity_int", "Boolean"),
    ],
)
def test_actual_custody_route_scope_and_strict_type_boundaries(mutation, match):
    rows = history()
    if mutation == "bytes":
        rows[0]["retained_bytes"] += b" "
    elif mutation == "receipt":
        rows[0]["receipt"]["source"]["sha256"] = "0" * 64
    elif mutation == "branch":
        rows[-1]["source"]["branch"] = "foreign"
        rows[-1]["receipt"]["source"] = deepcopy(rows[-1]["source"])
    elif mutation == "logical":
        one(rows, "legal_channel_export")["logical_system"] = "legal_inbound_message"
    elif mutation == "future":
        rows[-1]["source"]["available_at"] = "2028-02-01T09:00:00Z"
        rows[-1]["receipt"]["source"] = deepcopy(rows[-1]["source"])
    elif mutation == "scope":
        replace(
            one(rows, "intake_channel_ledger"), scope={**SCOPE, "boundary": "other company service"}
        )
    elif mutation == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif mutation == "count_bool":
        replace(one(rows, "legal_channel_export"), record_count=True)
    elif mutation == "channels_string":
        replace(rows[0], channels="NEUTRAL-INBOX")
    else:
        replace(one(rows, "legal_channel_export"), full_window_channel_continuity_established=1)
    with pytest.raises(ProcedureError, match=match):
        examine(rows, as_of=AS_OF)


def test_fully_resealed_future_attachment_witness_is_rejected_at_consumer_event():
    rows = history()
    attachment = one(rows, "legal_inbound_attachment")
    attachment["source"]["available_at"] = "2027-09-08T10:00:00Z"
    attachment["receipt"]["source"] = deepcopy(attachment["source"])
    replace(one(rows, "legal_inbound_message"), attachment_refs=[original_reference(attachment)])
    with pytest.raises(ProcedureError, match="unavailable at its event"):
        examine(rows, as_of=AS_OF)


def test_tail_cutoff_bridge_gap_and_preend_close_are_explicit():
    rows = history()
    tail = one(rows, "intake_tail_reconciliation")
    replace(tail, window_start="2027-09-30T14:00:00Z")
    tail["source"]["event_at"] = tail["source"]["available_at"] = "2027-09-30T20:00:00Z"
    tail["receipt"]["source"] = deepcopy(tail["source"])
    result = examine(rows, as_of=AS_OF)
    assert "TAIL_LEDGER_BRIDGE_GAP" in kinds(result)
    assert "TAIL_PUBLISHED_BEFORE_WINDOW_END" in kinds(result)


def test_later_version_cannot_replace_contemporaneous_quarter_join():
    rows = history(omitted=True, correction=True)
    result = examine(rows, as_of=AS_OF)
    assert result["quarter_history"][0]["screening_sources"][0]["version"] == 1
    assert result["quarter_history"][1]["tail_sources"][0]["version"] == 1
    assert result["quarter_history"][2]["tail_sources"][0]["version"] == 2


def test_external_trigger_unknown_is_never_classified_from_contract_subject():
    rows = [
        r
        for r in history()
        if r["logical_system"]
        not in {"legal_matter_classification", "regulatory_response_playbook"}
    ]
    result = examine(rows, as_of=AS_OF)
    assert result["classification_history"] == [] and result["playbook_history"] == []
    assert not result["independent_legal_conclusion"]


def test_uncollected_attachment_does_not_conflate_matching_counts_with_preservation():
    rows = [r for r in history() if r["logical_system"] != "legal_inbound_attachment"]
    result = examine(rows, as_of=AS_OF)
    assert result["selected_export_original_roster_corroborated"]
    assert not result["original_attachment_custody_corroborated"]
    assert not result["examined_source_links_resolved"]


def test_archive_count_claims_are_reperformed_separately_from_monthly_roster():
    rows = history()
    rows.append(retained("legaloriginals", "legal_archive_reconciliation", "ARCHIVE", {
        "source_scope": SCOPE, "inbound_message_count": 999, "retained_attachment_count": 1,
        "monthly_channel_export_count": len(CHANNELS), "declared_channel_count": len(CHANNELS),
    }, "2028-01-02T11:00:00Z"))
    result = examine(rows, as_of=AS_OF)
    assert "REVIEW_RETAINED_COUNT_MISMATCH" in kinds(result)
    assert result["selected_export_original_roster_corroborated"]
