"""Neutral legal/provider originals predate audit birth and enter ordinary collection."""

import hashlib
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_legal_provider_methods import (
    CLAUSE_FIELDS,
    authored_contracts,
    encoded,
    inspections,
    strict_fields,
    task_contracts,
)

REPO = Path(__file__).resolve().parents[2]
COMPANY, BRANCH = "NEUTRAL-LEGAL-PROVIDER", "SELECTED-OPERATIONS"


def test_exact_undetermined_real_hipaa_declaration_is_preserved_without_boolean_coercion():
    body = {"real_hipaa_applicability": "UNDETERMINED", "actual_phi": False}
    before = deepcopy(body)
    strict_fields(body)
    assert body == before and type(body["real_hipaa_applicability"]) is str


@pytest.mark.parametrize("value", [0, 1, "false", "true", "undetermined", "APPLICABLE", {}, []])
def test_only_exact_undetermined_declaration_supplements_strict_boolean_contract(value):
    with pytest.raises(ProcedureError, match="Strict Boolean field"):
        strict_fields({"real_hipaa_applicability": value})


def test_undetermined_hipaa_declaration_does_not_relax_other_boolean_fields():
    with pytest.raises(ProcedureError, match="Strict Boolean field actual_phi"):
        strict_fields({"real_hipaa_applicability": "UNDETERMINED", "actual_phi": "false"})


def build_originals(
    tmp_path_factory, *, alias_calendar=False, extra_author=None, case_overrides=None
):
    root = tmp_path_factory.mktemp("legal-provider-originals")
    root.chmod(0o700)
    company_root = root / "company"
    company_root.mkdir(mode=0o700)
    source, native = CompanyStore(company_root), []

    def put(family, role, rid, body, at, *, version=1, available_at=None):
        system = family + "." + role
        source.register_system(COMPANY, BRANCH, system, "neutral-business-owner")
        raw = encoded({"record_id": rid, "fictional_company_history": True, **body})
        meta = source.append_version(
            COMPANY,
            BRANCH,
            system,
            rid,
            expected_version=version - 1,
            command_id=f"original-{system}-{rid}-{version}",
            event_at=at,
            available_at=available_at or at,
            content=raw,
            provenance={
                "name": "original.json",
                "content_type": "application/json",
                "source_reference": "Neutral business original, no audit result",
            },
        )
        native.append(meta)
        return {
            k: meta[k]
            for k in (
                "company",
                "branch",
                "system",
                "record",
                "version",
                "event_at",
                "available_at",
                "imported_at",
                "sha256",
            )
        }

    scope = {
        "company_id": COMPANY,
        "boundary": "One neutral selected service",
        "period_start": "2027-09-01T00:00:00Z",
        "period_end": "2027-09-30T23:59:59Z",
        "unregistered_channel_completeness": "NOT_ESTABLISHED",
        "excluded": ["other entities", "unregistered channels", "real-world legal status"],
    }
    channels = ["CUSTOMER-COUNSEL", "OPERATIONS-LEGAL"]
    put(
        "legint",
        "intake_channel_register",
        "REGISTER",
        {"scope": scope, "channels": channels},
        "2027-08-30T08:00:00Z",
    )
    for channel in channels:
        put(
            "legaloriginals",
            "legal_channel_configuration",
            channel,
            {
                "scope": scope,
                "channel_id": channel,
                "retained_intake_registry_id": "REGISTER",
                "operation_established_from": "2027-08-31T09:00:00Z",
            },
            "2027-08-31T09:00:00Z",
        )
    attachment = put(
        "legaloriginals",
        "legal_inbound_attachment",
        "SCOPE-ATTACHMENT",
        {
            "channel_id": channels[1],
            "inbound_message_id": "TERM-QUESTION",
            "text": "Synthetic customer question about recovery support",
            "official_notice_or_case_identifier": None,
        },
        "2027-09-07T10:00:00Z",
    )
    put(
        "legaloriginals",
        "legal_inbound_message",
        "TERM-QUESTION",
        {
            "channel_id": channels[1],
            "received_at": "2027-09-07T10:00:00Z",
            "text": "Clarify downstream scope",
            "subject": "Neutral scope inquiry",
            "sender_role": "Synthetic customer counsel",
            "actual_external_message": False,
            "attachment_refs": [attachment],
        },
        "2027-09-07T10:00:00Z",
    )
    for channel in channels:
        ids = ["TERM-QUESTION"] if channel == channels[1] else []
        put(
            "legaloriginals",
            "legal_channel_export",
            "EXPORT-" + channel,
            {
                "channel_id": channel,
                "event_window_start": scope["period_start"],
                "event_window_end_exclusive": "2027-10-01T00:00:00Z",
                "source_available_as_of": "2027-10-01T09:00:00Z",
                "source_system": "legal_inbound_message",
                "event_filter": "received_at >= start AND received_at < end",
                "registered_channels_only": True,
                "record_count": len(ids),
                "declared_message_ids": ids,
                "query": (
                    "SELECT original versions by declared channel; documentary SQL, never execute"
                ),
                "channel_operation_start": "2027-08-31T09:00:00Z",
                "window_operational_coverage_start": scope["period_start"],
                "full_window_channel_continuity_established": True,
            },
            "2027-10-01T09:00:00Z",
        )
        put(
            "legint",
            "intake_channel_ledger",
            "LEDGER-" + channel,
            {
                "channel_id": channel,
                "window_start": scope["period_start"],
                "window_end": scope["period_end"],
                "export_cutoff": "2027-09-30T13:00:00Z",
                "remaining_day_followup_required": True,
                "intake_items": [
                    {
                        "item_id": "TERM-QUESTION",
                        "received_at": "2027-09-07T10:00:00Z",
                        "subject": "Neutral scope inquiry",
                        "sender_role": "Synthetic customer counsel",
                    }
                ]
                if ids
                else [],
                "record_count": len(ids),
                "scope": scope,
            },
            "2027-09-30T14:00:00Z",
        )
    put(
        "legint",
        "monthly_intake_screening",
        "SCREEN",
        {
            "registry_record_id": "REGISTER",
            "reviewed_channel_ids": channels[:1],
            "ledger_record_ids": ["LEDGER-" + channels[0]],
            "screening_state": "CLOSED",
            "reviewed_through": "2027-09-30T15:00:00Z",
            "scope": scope,
        },
        "2027-09-30T15:00:00Z",
    )
    put(
        "legint",
        "intake_tail_reconciliation",
        "TAIL",
        {
            "related_screening_id": "SCREEN",
            "channel_ids": channels[:1],
            "window_start": "2027-09-30T13:00:00Z",
            "window_end": scope["period_end"],
            "additional_intake_items": [],
            "extract_state": "COMPLETED_RECORDED_CHANNELS",
            "scope": scope,
        },
        "2027-10-01T10:00:00Z",
    )
    put(
        "legint",
        "quarterly_legal_review",
        "QUARTER",
        {"screening_record_ids": ["SCREEN"], "review_state": "FILED", "scope": scope},
        "2027-09-30T16:00:00Z",
    )
    put(
        "legint",
        "legal_exception_register",
        "CHANNEL-OMISSION",
        {"status": "OPEN", "affected_records": ["SCREEN", "QUARTER"], "scope": scope},
        "2027-11-01T10:00:00Z",
    )
    put(
        "legint",
        "monthly_intake_screening",
        "SCREEN",
        {
            "registry_record_id": "REGISTER",
            "reviewed_channel_ids": channels,
            "ledger_record_ids": ["LEDGER-" + c for c in channels],
            "screening_state": "CLOSED_AFTER_RECONCILIATION",
            "historical_exception_id": "CHANNEL-OMISSION",
            "scope": scope,
        },
        "2027-11-02T10:00:00Z",
        version=2,
    )
    put(
        "legint",
        "legal_matter_classification",
        "TERM-QUESTION",
        {
            "source_item_id": "TERM-QUESTION",
            "classification": "CONTRACTUAL_INQUIRY",
            "official_regulator_notice": False,
            "scope": scope,
        },
        "2027-09-08T09:00:00Z",
    )
    put(
        "legint",
        "regulatory_response_playbook",
        "PLAYBOOK",
        {
            "procedure": ["Preserve actual communication", "Counsel verifies authority and scope"],
            "2027_primary_authority_status": "RECHECK_AT_TRIGGER",
            "scope": scope,
        },
        "2027-09-02T09:00:00Z",
    )
    put(
        "leg001docket",
        "scope_decision",
        "LEGAL-SCOPE",
        {
            "detail": {
                "chain": {
                    "customer": "C",
                    "business_associate": "NEUTRAL-ENTITY",
                    "subcontractor": "SUPPORT",
                },
                "counsel_decision": "FICTIONAL_SELECTED_CHAIN_ONLY",
                "open_historical_exception_ids": ["LATE-FLOWDOWN", "PROVIDER-OMISSION"],
            },
            "real_world_operation": False,
        },
        "2027-10-01T00:00:00Z",
    )
    for code in ("160.101", "160.204", "160.412", "160.404", "160.518", "164.535"):
        put(
            "legprovision",
            "provision_locator",
            "LOCATOR-" + code,
            {
                "detail": {
                    "provision": {
                        "id": "45-CFR-" + code,
                        "category": "SELECTED_DOCUMENTARY_CONTEXT",
                    },
                    "locator_status": "HISTORICAL_REFERENCE_ONLY",
                    "source_edition": "2026 training text",
                    "qualified_review_status": "OPEN_PERIOD_PRIMARY_RECHECK",
                    "not_applicable_conclusion": False,
                }
            },
            "2027-10-02T09:00:00Z",
        )
    cases = {
        "160.204": {"request_status": "PENDING", "compliance_stopped": True},
        "160.412": {"waiver_granted": True, "waiver_request": "Requested, no disposition received"},
        "160.404": {
            "exposure_amount": 1000,
            "applicable_date": "2027-09-01",
            "primary_adjustment": None,
        },
        "160.518": {
            "exchange_deadline": "2027-09-10T00:00:00Z",
            "delivered_at": "2027-09-11T00:00:00Z",
        },
        "164.535": {
            "affected_text": "Historical XML",
            "status_analysis": "Judgment/review still absent",
        },
    }
    if case_overrides:
        cases.update(case_overrides)
    for code, facts in cases.items():
        put(
            "legint",
            "legal_response_exercise",
            "EXERCISE-" + code,
            {
                "scope": scope,
                "exercise_only": True,
                "requirement_ids": ["HIPAA:" + code],
                "decision": "Synthetic documentary counterexample",
                **facts,
            },
            "2027-10-03T09:00:00Z",
        )
    put(
        "legint",
        "legal_response_exercise",
        "PROVIDER-UNAVAILABLE",
        {
            "scope": scope,
            "exercise_only": True,
            "provider_copy_state": "TEMPORARILY_UNAVAILABLE",
            "available_company_copy_ids": ["TERM-QUESTION", "SCOPE-ATTACHMENT"],
            "decision": "PRESERVE_AVAILABLE_COMPANY_RECORDS_AND_ESCALATE_PROVIDER_COPY",
        },
        "2027-10-04T00:00:00Z",
    )
    put(
        "legint",
        "legal_response_exercise",
        "URGENT-REPORT",
        {
            "scope": scope,
            "exercise_only": True,
            "urgent_access_path_exercised": False,
            "status": "FOLLOWUP_REQUIRED",
            "customer_disclosure_rule_is_authority_basis": False,
        },
        "2027-10-04T01:00:00Z",
    )
    put(
        "legint",
        "legal_response_exercise",
        "URGENT-RETEST",
        {
            "scope": scope,
            "exercise_only": True,
            "urgent_access_path_exercised": True,
            "prior_report_id": "URGENT-REPORT",
            "decision": "SYNTHETIC_AVAILABLE_COMPANY_COPY_RETRIEVED",
        },
        "2027-10-05T00:00:00Z",
    )
    delegation = put(
        "phi_ba",
        "contract_authority",
        "BA-DELEGATION",
        {
            "limited_delegation_scope": ["UP-CONTRACT", "DOWN-CONTRACT"],
            "delegatee_id": "NEUTRAL-SIGNER",
            "real_world_operation": False,
        },
        "2027-07-01T00:00:00Z",
    )
    terms = [
        {
            "clause_candidate_id": "permitted_uses_and_disclosures",
            "declared_obligation": "Customer-directed synthetic hosting only; no model training",
        },
        {
            "clause_candidate_id": "incident_and_breach_reporting",
            "declared_obligation": "Notify within twelve fictional hours after discovery",
        },
        {
            "clause_candidate_id": "rights_request_support",
            "declared_obligation": "Support customer-directed copy, amendment and accounting",
        },
        {
            "clause_candidate_id": "subcontractor_flowdown",
            "declared_obligation": "Signed equivalent restrictions before downstream access",
        },
        {
            "clause_candidate_id": "return_or_destruction_and_continuing_protection",
            "declared_obligation": "Protect retained copies until feasible destruction",
        },
    ]
    upstream = put(
        "phi_ba",
        "contract_register",
        "UPSTREAM",
        {
            "contract_id": "UP-CONTRACT",
            "contract_party_ids": ["CUSTOMER", "NEUTRAL-ENTITY"],
            "synthetic_terms": terms,
            "limited_delegation_record_id": "BA-DELEGATION",
            "contract_executed_in_simulation": True,
            "simulated_contract_effective_at": "2027-07-02T00:00:00Z",
            "simulated_signer_ids": ["NEUTRAL-SIGNER"],
            "simulated_signer_authority": "SCOPED_FICTIONAL_DELEGATION",
            "real_signature_or_agreement": False,
            "fixture_contains_real_phi": False,
            "native_dependencies": [delegation],
        },
        "2027-07-02T00:00:00Z",
    )
    flow = put(
        "phi_ba",
        "flow_register",
        "PREMATURE-DOWNSTREAM",
        {
            "site_route": "PRIMARY_TO_BOISE_SIMULATION",
            "sim_subcontractor_id": "SUPPORT",
            "flow_marker_id": "SYNTHETIC-NONPERSONAL-MARKER",
            "flow_gate_disposition": "BYPASSED",
            "destination_ack": "UNKNOWN",
            "simulated_copy_reached_support": "UNDETERMINED",
            "exception_open": True,
            "real_world_operation": False,
        },
        "2027-07-03T00:00:00Z",
    )
    downstream = put(
        "phi_ba",
        "contract_register",
        "DOWNSTREAM",
        {
            "contract_id": "DOWN-CONTRACT",
            "contract_party_ids": ["NEUTRAL-ENTITY", "SUPPORT"],
            "synthetic_terms": terms,
            "limited_delegation_record_id": "BA-DELEGATION",
            "contract_executed_in_simulation": True,
            "simulated_contract_effective_at": "2027-07-04T00:00:00Z",
            "native_dependencies": [delegation],
            "real_signature_or_agreement": False,
        },
        "2027-07-04T00:00:00Z",
    )
    put(
        "phi_ba",
        "flow_register",
        "LATER-QUARANTINE",
        {
            "sim_subcontractor_id": "SUPPORT",
            "flow_gate_disposition": "QUARANTINED",
            "cure_status": "LATE_TERMS_DO_NOT_ERASE_HISTORY",
            "exception_open": True,
            "native_dependencies": [flow, downstream],
        },
        "2027-07-05T00:00:00Z",
    )
    master = {
        "service": "Power, cooling and perimeter only",
        "provider_incident_notice_hours": 24,
        "provider_security_report_frequency": "ANNUAL_AND_CHANGE",
        "exit_notice_days": 60,
        "ephi_processing": "NOT_AUTHORIZED_BY_FACILITY_CONTRACT",
    }
    facility = put(
        "transition",
        "provider_contract",
        "FACILITY-CONTRACT",
        {
            "site": {"provider_id": "FACILITY"},
            "fictional_executed_terms": {"master_terms": master},
            "real_external_signature": False,
        },
        "2027-06-01T00:00:00Z",
    )
    target = facility
    if alias_calendar:
        target = put(
            "transition",
            "meeting_note",
            "NOT-A-CONTRACT",
            {"fictional_executed_terms": {"master_terms": master}},
            "2027-06-01T01:00:00Z",
        )
    obligations = [
        {
            "id": "facility_service",
            "source_obligation": master["service"],
            "source_contract_sha256": target["sha256"],
        },
        {
            "id": "site_incident_notice_hours",
            "source_obligation": 24,
            "source_contract_sha256": target["sha256"],
        },
    ]
    calendar = put(
        "provider",
        "obligation_calendar",
        "FACILITY-CALENDAR",
        {
            "provider_id": "FACILITY",
            "source_contract_ref": target,
            "internal_review_due_at": "2027-10-31T00:00:00Z",
            "obligations": obligations,
        },
        "2027-09-01T00:00:00Z",
    )
    put(
        "provider",
        "relationship_register",
        "FACILITY",
        {
            "provider_id": "FACILITY",
            "tier": "LOCAL_CRITICAL",
            "upstream_native_refs": {"contract": facility},
            "actual_provider_assurance_received": False,
        },
        "2027-09-01T01:00:00Z",
    )
    put(
        "provider",
        "population_reconcile",
        "INITIAL-POP",
        {
            "expected_provider_ids": ["FACILITY", "SUPPORT"],
            "missing_provider_ids": ["SUPPORT"],
            "independent_expected_source_refs": {"facility": facility, "support_flow": flow},
            "ba_exception_is_distinct": True,
        },
        "2027-09-02T00:00:00Z",
    )
    put(
        "provider",
        "relationship_register",
        "SUPPORT",
        {
            "provider_id": "SUPPORT",
            "role": "SIMULATED_SUPPORT",
            "entry_reason": "LATE_BACKFILL",
            "upstream_native_refs": {"flow": flow},
        },
        "2027-10-01T00:00:00Z",
    )
    put(
        "provider",
        "population_reconcile",
        "CORRECTED-POP",
        {
            "expected_provider_ids": ["FACILITY", "SUPPORT"],
            "missing_provider_ids": [],
            "independent_expected_source_refs": {"facility": facility, "support_flow": flow},
            "ba_exception_is_distinct": True,
        },
        "2027-10-02T00:00:00Z",
    )
    put(
        "provider",
        "review_register",
        "FACILITY-REVIEW",
        {
            "provider_id": "FACILITY",
            "review_due_at": "2027-10-31T00:00:00Z",
            "obligation_checks": [
                {"id": "facility_service", "external_performance_state": "NOT_VERIFIED"}
            ],
            "review_disposition": "INTERNAL_TERM_INDEX_ONLY",
            "native_dependencies": [calendar],
        },
        "2027-11-02T00:00:00Z",
    )
    occurrences = [
        {
            "occurrence_id": "UPSTREAM:permitted-use",
            "source_ref": upstream,
            "term_id": "permitted_uses_and_disclosures",
            "term_value": terms[0]["declared_obligation"],
            "term_sha256": hashlib.sha256(encoded(terms[0]["declared_obligation"])).hexdigest(),
        },
        {
            "occurrence_id": "FACILITY:service",
            "source_ref": calendar,
            "term_id": "facility_service",
            "term_value": master["service"],
            "term_sha256": hashlib.sha256(encoded(master["service"])).hexdigest(),
        },
    ]
    put(
        "contract",
        "selected_term_inventory",
        "SELECTED-TERMS",
        {
            "term_occurrences": occurrences,
            "term_occurrence_count": 2,
            "actor_attestation_scope": "ONLY_SELECTED_ORIGINALS",
            "qualified_counsel_provision_review": "PENDING",
            "actual_hipaa_applicability": "UNDETERMINED",
        },
        "2027-10-02T11:00:00Z",
    )
    planned = put(
        "provider-history",
        "planned_dependency_inventory",
        "PLANNED",
        {"dependencies": [{"provider_id": "FACILITY"}, {"provider_id": "RESERVE"}]},
        "2027-01-01T00:00:00Z",
    )
    put(
        "provider-history",
        "vendor_register",
        "FACILITY",
        {"provider_id": "FACILITY"},
        "2027-01-02T00:00:00Z",
    )
    put(
        "provider-history",
        "coverage_reconciliation",
        "MISSING-RESERVE",
        {
            "missing_provider_ids": ["RESERVE"],
            "diligence_support_obtained": 0,
            "native_dependencies": [planned],
        },
        "2027-02-01T00:00:00Z",
    )
    put(
        "provider-history",
        "review_schedule",
        "FACILITY-DUE",
        {"provider_id": "FACILITY", "due_at": "2027-03-01T00:00:00Z"},
        "2027-02-01T01:00:00Z",
    )
    put(
        "provider-history",
        "monitoring_reviews",
        "FACILITY-LATE",
        {
            "provider_id": "FACILITY",
            "original_due_at": "2027-03-01T00:00:00Z",
            "late_seconds": 172800,
            "support_status": "NOT_OBTAINED",
            "financial_health": "UNKNOWN_NO_VENDOR_SOURCE",
            "review_result": "PREOPERATING_LOCAL_WORK_QUEUE",
        },
        "2027-03-03T00:00:00Z",
    )
    for number in range(24):
        put(
            "provider-history",
            "diligence_work_items",
            f"SUPPORT-{number}",
            {
                "provider_id": "FACILITY",
                "requirement_id": f"NEUTRAL-SUPPORT-{number}",
                "external_request_status": "NOT_SENT_LOCAL_WORK_ITEM_ONLY",
                "received_document_sha256": None,
                "support_status": "NOT_OBTAINED",
                "report_scope": None,
                "exceptions": None,
            },
            "2027-03-04T00:00:00Z",
        )
    put(
        "processing",
        "reuse_request",
        "AI-REUSE",
        {
            "new_use": "MODEL_TRAINING",
            "attempted_request_only": True,
            "new_flow_executed": False,
            "actual_decision": "REFUSE_AND_KEEP_QUEUED",
            "native_dependencies": [upstream],
        },
        "2027-09-01T09:00:00Z",
    )
    put(
        "dat002rights",
        "rights_register",
        "HELD-COPY",
        {
            "request_kind": "ACCESS_COPY",
            "record_copy_prepared": False,
            "copy_sent": False,
            "premature_no_record_mark": True,
            "requester_authority": "CUSTOMER_OWNER_UNCONFIRMED",
            "native_dependencies": [upstream],
        },
        "2027-09-03T00:00:00Z",
    )
    put(
        "supplementalops",
        "privacy_responsibility",
        "CUSTOMER-BOUNDARY",
        {
            "customer_retained_notice_authority": True,
            "delegated_service_steps": ["Preserve and route request"],
            "not_delegated": "No release, amendment acceptance or covered-customer notice issuance",
            "native_dependencies": [upstream],
        },
        "2027-08-01T00:00:00Z",
    )
    put(
        "supplementalops",
        "communication_event",
        "LATE-NOTICE",
        {
            "agent_discovery_at": "2027-09-01T00:00:00Z",
            "discovery_at": "2027-09-01T02:00:00Z",
            "clock_started_at": "2027-09-02T00:00:00Z",
            "notice_sent_at": "2027-09-02T02:00:00Z",
            "contractual_notice_hours": 12,
            "recipient": "SYNTHETIC-CUSTOMER",
            "law_enforcement_delay": None,
            "native_dependencies": [upstream],
        },
        "2027-09-02T03:00:00Z",
    )
    put(
        "assuranceops",
        "description_assertion",
        "RECOVERY-CLAIM",
        {
            "assertion": "Recovery service operating in fictional period",
            "source_refs": [facility],
            "supplier_report_received": False,
        },
        "2027-10-03T00:00:00Z",
    )
    if extra_author:
        extra_author(
            put,
            {
                "upstream": upstream,
                "scope": scope,
                "calendar": calendar,
                "delegation": delegation,
                "terms": terms,
            },
        )
    assert native
    engine = Engine(root / "audit", repository=REPO, company_root=company_root)
    operator = engine.store.provision("Neutral instructor", ["instructor"])
    auditor = engine.store.provision("Neutral examiner", ["learner"])
    state = engine.create(
        operator["id"],
        {
            "command_id": "neutral-b06-birth",
            "title": "Neutral legal provider examination",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {"selections": []},
            "scope": {
                "programs": ["SOC2"],
                "report_type": "Type 2",
                "period_start": "2027-01-01",
                "period_end": "2027-12-31",
                "fieldwork_start": "2027-12-31",
                "timezone": "UTC",
                "boundaries": ["corporate"],
                "control_ids": ["SH-LEG-001"],
            },
        },
    )
    eid = state["id"]
    engine.store.grant(eid, auditor["id"], "learn")
    engine.company_bindings[eid] = {"company": COMPANY, "branch": BRANCH}

    def command(actor, kind, payload):
        state = engine.store.get(actor, eid)
        return engine.command(
            actor,
            eid,
            {
                "command_id": f"neutral-{state['revision']}-{kind}",
                "kind": kind,
                "expected_revision": state["revision"],
                "payload": payload,
            },
        )

    command(operator["id"], "company.activate", {})
    command(auditor["id"], "kickoff.start", {})
    command(
        auditor["id"], "clock.advance", {"mode": "TARGET_DATE", "target": "2028-01-15T09:00:00Z"}
    )
    for system in sorted({m["system"] for m in native}):
        source.grant(auditor["id"], eid, COMPANY, BRANCH, system)
    state = command(
        auditor["id"],
        "pbc.create",
        {
            "title": "Native legal/provider originals",
            "purpose": "Selected documentary examination",
            "control_id": "SH-LEG-001",
            "person_id": "AS-P003",
            "boundary_id": "corporate",
        },
    )
    request = state["requests"][-1]["id"]
    command(auditor["id"], "pbc.issue", {"request_id": request})
    for meta in native:
        command(
            auditor["id"],
            "company.collect",
            {
                "request_id": request,
                "system_id": meta["system"],
                "record_id": meta["record"],
                "version": meta["version"],
            },
        )
    state = engine.store.get(auditor["id"], eid)
    rows = []
    for artifact in state["artifacts"]:
        receipt = artifact["source"]["receipt"]
        src = receipt["source"]
        family, role = src["system"].split(".", 1)
        rows.append(
            {
                "source": src,
                "receipt": receipt,
                "retained_bytes": engine.artifacts.read(artifact),
                "artifact_id": artifact["id"],
                "artifact_sha256": artifact["sha256"],
                "content_type": "application/json",
                "logical_family": family,
                "logical_system": role,
            }
        )
    return {
        "rows": rows,
        "engine": engine,
        "auditor": auditor["id"],
        "engagement": eid,
        "source": source,
        "root": root,
        "as_of": state["simulated_at"],
    }


@pytest.fixture(scope="module")
def originals(tmp_path_factory):
    return build_originals(tmp_path_factory)


def outputs(originals):
    return inspections(
        originals["rows"], as_of=originals["as_of"], scratch_root=originals["root"] / "unused"
    )


def task(results, control, suffix):
    return next(r for r in results if r["task_id"] == f"TASK-{control}-corporate-{suffix}")


def facts(result, prefix):
    return [
        o["facts"]
        for o in result["observations"]
        if o["facts"].get("calculation_local_observation_id", "").startswith(prefix)
    ]


def test_full99_has_exact_distinct_contracts_actual_source_evidence_and_unchanged_preflight(
    originals,
):
    from enterprise.audit_suite.full_scope_company_pair import BoundWorkroom

    results = outputs(originals)
    contracts = task_contracts()
    room = SimpleNamespace(
        state=lambda: originals["engine"].store.get(
            originals["auditor"], originals["engagement"]
        )
    )
    assert (
        len(results) == 99
        and [r["task_id"] for r in results] == authored_contracts()["selected_task_ids"]
    )
    assert len({r["performed"] for r in results}) == len({r["unperformed"] for r in results}) == 99
    for result in results:
        assert result["performed"] == contracts[result["task_id"]]["performed"]
        assert result["disposition"] in [
            {**d, "rationale": result["disposition"]["rationale"]}
            for d in contracts[result["task_id"]]["allowed_dispositions"]
        ]
        assert result["artifact_ids"] and result["observations"]
        assert all(
            0 < len(o["evidence"]) <= 20 and len(o["id"]) <= 128 for o in result["observations"]
        )
        BoundWorkroom._validate_inspection(
            room, originals["rows"], result, contracts[result["task_id"]]
        )
        assert (
            result["result"]["population"]["full_period_enterprise_denominator_established"]
            is False
        )
        assert (
            result["result"]["professional_pass_or_full_authored_task_completion_asserted"] is False
        )


def test_each_enforcement_clause_has_distinct_actual_fields_and_missing_case_not_nonoccurrence(
    originals,
):
    results = outputs(originals)
    for code, fields in CLAUSE_FIELDS.items():
        result = task(results, "SH-LEG-001", "CHECK-HIPAA:" + code)
        value = facts(result, "legal-clause-")[0]
        assert value["expected_documentary_attributes"] == list(fields)
        assert value["missing_selected_case_does_not_establish_enterprise_nonoccurrence"]
        assert value["source_edition_and_judicial_applicability_accepted"] is False
    assert facts(task(results, "SH-LEG-001", "CHECK-HIPAA:160.526"), "legal-clause-")[0][
        "selected_clause_case_originals_not_collected"
    ]


def test_pending_request_waiver_claim_unverified_amount_and_late_exchange_are_actual_failures(
    originals,
):
    results = outputs(originals)
    expected = {
        "160.204": "PENDING_REQUEST_USED_AS_STOP_AUTHORITY",
        "160.412": "REQUEST_OR_ELIGIBILITY_IS_NOT_GRANTED_DISPOSITION",
        "160.404": "AMOUNT_WITHOUT_VERIFIED_PRIMARY_ADJUSTMENT",
        "160.518": "ACTUAL_AFTER_RECORDED_DEADLINE",
    }
    for code, reason in expected.items():
        result = task(results, "SH-LEG-001", "CHECK-HIPAA:" + code)
        assert result["disposition"]["conclusion"] == "FAIL"
        assert facts(result, "legal-clause-")[0]["exceptions"][0]["reason"] == reason


def test_native_contract_terms_and_calendar_upstream_values_are_recalculated(originals):
    result = task(outputs(originals), "SH-TPR-003", "IMPLEMENTATION")
    values = facts(result, "selected-contract-inventory-")[0]
    assert values["count_matches"] is True
    assert all(
        t["actual_value_matches"] and t["typed_value_sha256_matches"]
        for t in values["term_occurrence_tests"]
    )
    calendar = facts(result, "provider-calendar-upstream-")[0]
    assert calendar["actual_upstream_role_supported"] is True
    assert all(
        t["actual_value_matches"] and t["source_hash_matches"] for t in calendar["obligation_tests"]
    )


def test_genuine_same_json_meeting_note_does_not_supply_contract_role(tmp_path_factory):
    fixture = build_originals(tmp_path_factory, alias_calendar=True)
    result = task(outputs(fixture), "SH-TPR-003", "IMPLEMENTATION")
    value = facts(result, "provider-calendar-upstream-")[0]
    assert value["source_reference_status"] == "EXACT_COLLECTED_ORIGINAL"
    assert value["actual_upstream_role_supported"] is False
    assert not any(t["actual_value_matches"] for t in value["obligation_tests"])
    assert result["disposition"]["conclusion"] == "FAIL"


def test_late_subcontract_does_not_cure_actual_original_downstream_flow(originals):
    result = task(outputs(originals), "SH-TPR-003", "ACTION-H-SUBCONTRACT")
    flow = facts(result, "downstream-flow-signed-scope-")
    prior = next(f for f in flow if f["actual_site_route"])
    assert prior["downstream_route_before_effective_flowdown"] is True
    assert (
        prior["later_contract_versions"]
        and not prior["contract_versions_available_and_effective_at_flow"]
    )
    assert prior["later_terms_or_quarantine_do_not_erase_prior_route"]
    assert result["disposition"]["conclusion"] == "FAIL"


def test_original_provider_omission_survives_corrected_register_and_sources_are_independent(
    originals,
):
    result = task(outputs(originals), "SH-TPR-001", "TOE")
    populations = facts(result, "provider-independent-population-")
    assert populations[0]["actual_missing_provider_ids"] == ["SUPPORT"]
    assert populations[1]["actual_missing_provider_ids"] == []
    assert populations[0]["declared_expected_matches_actual_selected_sources"]
    assert populations[1]["later_register_backfill_does_not_cure_earlier_omission"]
    assert result["disposition"]["conclusion"] == "FAIL"


def test_due_review_lateness_uses_native_event_and_publication_not_internal_result(originals):
    result = task(outputs(originals), "SH-TPR-004", "TOE")
    due = facts(result, "provider-due-review-")
    assert len(due) == 2
    assert all(v["review_tests"][0]["actual_late_seconds"] == 172800 for v in due)
    assert all(not v["review_tests"][0]["native_original_available_by_due"] for v in due)
    assert {v["operating_or_planned_intake_basis"] for v in due} == {"provider", "provider-history"}


def test_notice_clock_uses_agent_discovery_shorter_contract_and_detects_management_reset(originals):
    result = task(outputs(originals), "SH-TPR-003", "ACTION-H-NOTICE-CLOCK")
    notice = next(
        v
        for v in facts(result, "contract-notice-clock-")
        if v["actual_elapsed_hours_from_earliest_recorded_discovery"] is not None
    )
    assert notice["actual_elapsed_hours_from_earliest_recorded_discovery"] == 26
    assert (
        notice["actual_contractual_sla_exceeded"] and notice["recorded_clock_reset_after_discovery"]
    )
    assert notice["statutory_trigger_clock_or_law_enforcement_delay_accepted"] is False


def test_held_rights_request_and_customer_authority_are_not_completed_exercise(originals):
    result = task(outputs(originals), "SH-TPR-003", "ACTION-H-RIGHTS-ASSISTANCE")
    rights = facts(result, "contract-rights-request-support-")[0]
    assert rights["actual_request_records"]["premature_no_record_mark"] is True
    assert rights["copy_amendment_accounting_exercise_complete"] is False
    assert rights["direct_vs_customer_retained_authority"]
    assert result["disposition"]["conclusion"] == "FAIL"


def test_once_reused_legal_intake_preserves_channel_omission_tail_and_original_correspondence(
    originals, monkeypatch
):
    import enterprise.audit_suite.source_legal_provider_methods as module

    count = []
    original = module.intake.examine

    def checked(*args, **kwargs):
        count.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(module.intake, "examine", checked)
    result = outputs(originals)
    assert count == [1]
    toe = task(result, "SH-LEG-001", "TOE")
    value = next(
        o["facts"]
        for o in toe["observations"]
        if o["facts"].get("schema") == "SH_COLLECTED_LEGAL_INTAKE_EXAMINATION_V1"
    )
    assert (
        value["original_message_identity_count"] == 1
        and value["retained_attachment_version_count"] == 1
    )
    assert value["documentary_discrepancies"] and value["screening_history"]
    assert value["whole_period_channel_continuity_established"] is False
    assert value["enterprise_nonoccurrence_established"] is False


def test_complete_citation_membership_and_continuation_links_survive_full99(originals):
    results = outputs(originals)
    for result in results:
        ids = {o["id"] for o in result["observations"]}
        for o in result["observations"]:
            assert set(o["facts"].get("continued_evidence_observation_ids", [])) <= ids
            link = o["facts"].get("supports_complete_calculation_observation_id")
            if link:
                assert link in ids
    description = task(results, "SH-TPR-002", "ACTION-S-DESCRIPTION")
    context = next(
        o
        for o in description["observations"]
        if o["facts"].get("calculation_local_observation_id")
        == "provider-service-description-assertions-and-source-boundary"
    )
    assert context["facts"]["selected_originals"]


@pytest.mark.parametrize(
    "field",
    [
        "source_version",
        "receipt_version",
        "receipt_count",
        "native_route",
        "cached_hash",
        "future_publication",
        "cross_branch",
    ],
)
def test_actual_ordinary_receipt_native_route_type_clock_and_authority_boundaries(originals, field):
    rows = deepcopy(originals["rows"])
    row = rows[0]
    if field == "source_version":
        row["source"]["version"] = True
        row["receipt"]["source"]["version"] = True
    elif field == "receipt_version":
        row["receipt"]["source"]["version"] = True
    elif field == "receipt_count":
        row["receipt"]["content_bytes"] = True
    elif field == "native_route":
        row["logical_system"] = "meeting_note"
    elif field == "cached_hash":
        row["artifact_sha256"] = "0" * 64
    elif field == "future_publication":
        row["source"]["available_at"] = "2029-01-01T00:00:00Z"
        row["receipt"]["source"] = deepcopy(row["source"])
    else:
        row["source"]["branch"] = "OTHER-BRANCH"
        row["receipt"]["source"] = deepcopy(row["source"])
    with pytest.raises(ProcedureError):
        inspections(rows, as_of=originals["as_of"], scratch_root=originals["root"])


def test_cached_document_cannot_override_retained_original_and_callback_reads_no_database(
    originals, monkeypatch
):
    import sqlite3

    rows = deepcopy(originals["rows"])
    for row in rows:
        row["document"] = {
            "actual_trigger": True,
            "waiver_granted": True,
            "review_disposition": "ACCEPTED",
        }

    def forbidden(*args, **kwargs):
        raise AssertionError("Pure callback opened database")

    monkeypatch.setattr(sqlite3, "connect", forbidden)
    actual = inspections(rows, as_of=originals["as_of"], scratch_root=originals["root"])
    assert actual == outputs(originals)


def test_genuine_changed_case_predicates_change_only_supported_selected_conclusions(
    tmp_path_factory,
):
    fixture = build_originals(
        tmp_path_factory,
        case_overrides={
            "160.204": {"request_status": "PENDING", "compliance_stopped": False},
            "160.412": {"waiver_granted": False, "waiver_request": "Requested"},
            "160.404": {"exposure_amount": None, "primary_adjustment": None},
            "160.518": {
                "exchange_deadline": "2027-09-10T00:00:00Z",
                "delivered_at": "2027-09-09T00:00:00Z",
            },
        },
    )
    results = outputs(fixture)
    for code in ("160.204", "160.412", "160.404", "160.518"):
        result = task(results, "SH-LEG-001", "CHECK-HIPAA:" + code)
        value = facts(result, "legal-clause-")[0]
        assert not value["exceptions"]
        assert result["disposition"]["conclusion"] == "LIMITATION"
        assert value["exact_section_case_attribute_tests"][0]["missing_authored_attributes"]
        assert not value["source_edition_and_judicial_applicability_accepted"]


def test_genuine_published_signer_mismatch_and_earliest_employee_discovery_are_detected(
    tmp_path_factory,
):
    def author(put, known):
        put(
            "phi_ba",
            "contract_register",
            "WRONG-SIGNER",
            {
                "contract_id": "UP-CONTRACT",
                "contract_party_ids": ["CUSTOMER", "NEUTRAL-ENTITY"],
                "limited_delegation_record_id": "BA-DELEGATION",
                "simulated_signer_ids": ["OTHER-PERSON"],
                "synthetic_terms": known["terms"],
                "contract_executed_in_simulation": True,
                "simulated_contract_effective_at": "2027-07-02T01:00:00Z",
                "native_dependencies": [known["delegation"]],
            },
            "2027-07-02T01:00:00Z",
        )
        put(
            "supplementalops",
            "communication_event",
            "AGENT-LEARNED-LATER",
            {
                "discovery_at": "2027-09-01T00:00:00Z",
                "agent_discovery_at": "2027-09-01T03:00:00Z",
                "clock_started_at": "2027-09-01T00:00:00Z",
                "notice_sent_at": "2027-09-01T13:00:00Z",
                "contractual_notice_hours": 12,
                "native_dependencies": [known["upstream"]],
            },
            "2027-09-01T14:00:00Z",
        )

    fixture = build_originals(tmp_path_factory, extra_author=author)
    results = outputs(fixture)
    contracts = facts(task(results, "SH-TPR-003", "TOE"), "contract-scope-and-signing-")
    wrong = next(v for v in contracts if v["signer_ids"] == ["OTHER-PERSON"])
    assert wrong["named_scope_includes_contract"] is True
    assert wrong["actual_named_signers_match_published_delegatee"] is False
    notice = facts(task(results, "SH-TPR-003", "ACTION-H-NOTICE-CLOCK"), "contract-notice-clock-")
    selected = next(v for v in notice if v["recorded_event"]["record_id"] == "AGENT-LEARNED-LATER")
    assert selected["actual_elapsed_hours_from_earliest_recorded_discovery"] == 13
    assert (
        selected["actual_contractual_sla_exceeded"]
        and not selected["recorded_clock_reset_after_discovery"]
    )


def test_callback_leaves_native_company_audit_and_stored_business_paths_untouched(
    originals, monkeypatch
):
    before = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [originals["source"].path, originals["engine"].store.db_path]
    }
    original = Path.read_bytes

    def guarded(path):
        if str(path).startswith("/must-never-follow-company"):
            raise AssertionError("Company business path followed")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    outputs(originals)
    after = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [originals["source"].path, originals["engine"].store.db_path]
    }
    assert before == after


def test_empty_exit_register_is_not_no_exit_or_sanitization_proof(originals):
    result = task(outputs(originals), "SH-TPR-005", "TOE")
    value = facts(result, "provider-exit-and-continuing-protection")[0]
    assert value["empty_collected_exit_vector_does_not_establish_no_exits"]
    assert not value["all_access_connections_backup_copies_and_financial_obligations_reconciled"]
    assert result["disposition"]["conclusion"] == "LIMITATION"


def test_regulator_provider_and_urgent_exercise_preserves_failed_original_after_retest(originals):
    result = task(outputs(originals), "SH-LEG-001", "ACTION-H-REGULATOR")
    records = facts(result, "regulator-provider-urgent-exercise-")
    assert len(records) == 3
    original = next(v for v in records if v["urgent_path_exercised"] is False)
    later = next(v for v in records if v["urgent_path_exercised"] is True)
    assert original["actual_exercise_record"]["status"] == "FOLLOWUP_REQUIRED"
    assert later["exact_prior_report_originals"][0]["recorded"]["record_id"] == "URGENT-REPORT"
    assert later["earlier_followup_or_access_failure_remains_separate_after_retest"]
    assert not later["actual_regulator_order_rights_and_response_executed"]
    assert result["disposition"]["conclusion"] == "FAIL"
