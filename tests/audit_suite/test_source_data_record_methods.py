"""Neutral originals exist before audit birth and enter through ordinary collection."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStore, _time
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.fresh_sec003_procedure import CLOCK_ID, ProcedureError
from enterprise.audit_suite.source_data_record_methods import (
    History,
    activity_observations,
    add_years,
    authored_contracts,
    encoded,
    inspections,
    quality,
    route_screen,
    sha,
    task_contracts,
)

REPO = Path(__file__).resolve().parents[2]
COMPANY, BRANCH = "NEUTRAL-DATA-RECORDS", "SELECTED-OPERATIONS"


def build_originals(tmp_path_factory, *, authorize=False, extra_author=None):
    root = tmp_path_factory.mktemp("data-record-originals")
    root.chmod(0o700)
    source_root = root / "company"
    source_root.mkdir(mode=0o700)
    source, native = CompanyStore(source_root), []

    def put(family, role, record, doc, at, *, version=1, raw=None):
        system = family + "." + role
        source.register_system(COMPANY, BRANCH, system, "neutral-source-owner")
        data = raw if raw is not None else encoded(doc)
        meta = source.append_version(
            COMPANY,
            BRANCH,
            system,
            record,
            expected_version=version - 1,
            command_id=f"original-{system}-{record}-{version}",
            event_at=at,
            available_at=at,
            content=data,
            provenance={
                "source_reference": "Neutral pre-audit business original",
                "name": "original.json",
                "content_type": "application/json",
            },
        )
        native.append(meta)
        return {k: meta[k] for k in CLOCK_ID}

    dataset = put(
        "dataset",
        "dataset_inventory",
        "D1",
        {
            "dataset_id": "neutral-data",
            "custodian": "neutral-steward",
            "accountable_data_owner": "OWNER_PENDING",
            "classification_recommendation": "RESTRICTED",
            "decision_state": "PROPOSED",
            "propagation_status": "NOT_VERIFIED",
            "intake_control_verified": False,
            "retention_rule_approved": False,
            "deletion_rule_approved": False,
            "enterprise_dataset_completeness": "UNDETERMINED",
        },
        "2027-01-02T00:00:00Z",
    )
    label = put(
        "dataset",
        "local_label",
        "D1",
        {
            "dataset_id": "neutral-data",
            "invalid_public_local_metadata_label": True,
            "local_label_quarantined": False,
            "invalid_label_history_open": True,
            "upstream_flow_refs": [dataset],
        },
        "2027-01-03T00:00:00Z",
    )
    put(
        "dataset",
        "label_quarantine",
        "D1",
        {
            "dataset_id": "neutral-data",
            "invalid_public_local_metadata_label": True,
            "local_label_quarantined": True,
            "invalid_label_history_open": True,
            "source_refs": [label],
        },
        "2027-01-04T00:00:00Z",
    )
    put(
        "processing",
        "purpose_review",
        "AI-REQUEST",
        {
            "requested_purpose": "AI_TRAINING",
            "requested_recipient": "neutral-recipient",
            "decision": "REFUSED",
            "contract_purpose_match": False,
            "new_flow_executed": False,
            "real_world_legal_approval": "UNDETERMINED",
            "upstream_flow_refs": [dataset],
        },
        "2027-01-05T00:00:00Z",
    )
    put(
        "dat002rights",
        "record_scope_review",
        "RIGHTS",
        {
            "case_id": "neutral-rights",
            "designated_record_set_determination": "PENDING",
            "complete_record_population": False,
            "record_copy_prepared": False,
            "premature_no_record_mark": True,
            "unreconciled_locations": ["neutral-backup"],
        },
        "2027-01-06T00:00:00Z",
    )
    put(
        "retention",
        "disposition_gate",
        "HELD",
        {
            "legal_hold_disposition": "PENDING",
            "legal_hold_release": "NOT_AUTHORIZED",
            "attempted_premature_disposition": True,
            "attempt_disposition": "DENIED",
            "unlink_executed": False,
            "deletion_verified": False,
            "fixture_copy_retained": True,
            "selected_source_refs": [dataset],
        },
        "2027-01-07T00:00:00Z",
    )
    put(
        "controlled_record",
        "controlled_retrieval",
        "REGISTER",
        {
            "actor_person_id": "neutral-operator",
            "source_integrity_state": "PRESERVED",
            "retrieval_uses_authoritative_original": True,
            "source_context_refs": [dataset],
            "classification_authority": "PENDING",
            "disposition_executed": False,
        },
        "2027-01-08T00:00:00Z",
    )
    policy = put(
        "supplementalops",
        "policy_document",
        "POLICY",
        {
            "contents": "Original neutral operating policy",
            "effective_at": "2027-01-01T00:00:00Z",
        },
        "2027-01-01T00:00:00Z",
    )
    put(
        "supplementalops",
        "policy_document",
        "POLICY",
        {
            "contents": "Superseding neutral operating policy",
            "effective_at": "2027-11-01T00:00:00Z",
            "native_dependencies": [policy],
        },
        "2027-11-01T00:00:00Z",
        version=2,
    )
    put(
        "supplementalops",
        "retention_register",
        "INDEX",
        {
            "required_records": [
                {
                    "id": "POLICY-v1",
                    "class": "SECURITY_POLICY_PROCEDURE",
                    "created_date": "2027-01-01",
                    "last_in_effect_date": "2027-11-01",
                    "current_effective": False,
                    "hold": False,
                    "requested_date": "2028-01-02",
                    "minimum_retain_through": "2033-11-01",
                    "release_eligible_on": "2033-11-02",
                    "decision": "DENY",
                    "actual_deletion": False,
                },
                {
                    "id": "POLICY-v2",
                    "class": "SECURITY_POLICY_PROCEDURE",
                    "created_date": "2027-11-01",
                    "last_in_effect_date": None,
                    "current_effective": True,
                    "hold": False,
                    "requested_date": "2035-01-02",
                    "minimum_retain_through": "2033-11-01",
                    "release_eligible_on": "2033-11-02",
                    "decision": "DENY",
                    "actual_deletion": False,
                },
            ],
            "superseded_original_retrieval": {
                "exact_original_ref": "policy_document/POLICY/1",
                "retrieved": True,
            },
        },
        "2027-11-05T00:00:00Z",
    )
    review = put(
        "supplementalops",
        "procedure_operation",
        "MONTHLY",
        {
            "trigger_id": "NOV",
            "performer": "neutral-reviewer",
            "due_at": "2027-11-03T00:00:00Z",
            "operator_statement": "Review complete",
            "factual_result": "One selected original",
            "input_originals": ["policy_document/POLICY/1"],
            "required_original_retrieval": [
                {"original": policy, "retrieved_sha256": policy["sha256"], "usable_JSON": True}
            ],
        },
        "2027-11-02T00:00:00Z",
    )
    put(
        "supplementalops",
        "procedure_calendar",
        "REVIEW-DUE",
        {
            "program_started": "2027-11-01T00:00:00Z",
            "scheduled": [
                {
                    "trigger_id": "NOV",
                    "trigger_at": "2027-11-01T00:00:00Z",
                    "due_at": "2027-11-03T00:00:00Z",
                },
                {
                    "trigger_id": "DEC",
                    "trigger_at": "2027-12-01T00:00:00Z",
                    "due_at": "2027-12-03T00:00:00Z",
                },
            ],
            "not_scheduled_interval": {
                "start": "2027-01-01",
                "end": "2027-11-01",
                "reason": "Neutral procedure not effective",
            },
        },
        "2027-10-31T00:00:00Z",
    )

    references = [{"entity_id": "E", "category": "CAT"}]
    raw = [
        {"record_id": "R1", "entity_id": "E", "observed_at": "2027-06-01T01:00:00Z", "units": 5},
        {"record_id": "R2", "entity_id": "E", "observed_at": "2027-06-01T02:00:00Z", "units": "7"},
        {"record_id": "R2", "entity_id": "E", "observed_at": "2027-06-01T03:00:00Z", "units": 8},
    ]
    plan = {
        "event_window": {
            "start": "2027-06-01T00:00:00.000000+00:00",
            "end": "2027-06-02T00:00:00.000000+00:00",
        },
        "expected_record_ids": ["R1", "R2", "R3"],
        "reference_rows": references,
        "maximum_units": 20,
    }
    definition = put(
        "rec003", "quality_definition", "RULES", {"plan": plan}, "2027-05-31T00:00:00Z"
    )
    reference = put("rec003", "quality_reference", "REF", references, "2027-05-31T00:00:00Z")
    raw_ref = put("rec003", "quality_raw", "RAW", raw, "2027-06-02T00:00:00Z")
    report = {
        "status": "PARTIAL_UNRELIABLE",
        "input_rows": 3,
        "accepted_rows": 1,
        "failed_rows": 2,
        "intentional_exclusions": 0,
        "expected_in_window_records": 3,
        "missing_expected_in_window_ids": ["R3"],
        "missing_usable_expected_ids": ["R2", "R3"],
        "failures": [
            {
                "index": 1,
                "row_sha256": sha(encoded(raw[1])),
                "reasons": ["DUPLICATE_RECORD_ID", "INVALID_INTEGER_UNITS"],
            },
            {"index": 2, "row_sha256": sha(encoded(raw[2])), "reasons": ["DUPLICATE_RECORD_ID"]},
        ],
        "exclusions": [],
        "query": plan["event_window"],
        "timezone": "UTC",
        "source_acceptance": "NOT_ESTABLISHED",
    }
    derived = put(
        "rec003",
        "quality_derived",
        "TRANSFORM",
        {
            "status": "PARTIAL_UNRELIABLE",
            "records": [
                {
                    "record_id": "R1",
                    "entity_id": "E",
                    "category": "CAT",
                    "units": 5,
                    "observed_at": "2027-06-01T01:00:00.000000+00:00",
                    "source_index": 0,
                    "source_row_sha256": sha(encoded(raw[0])),
                }
            ],
            "query": plan["event_window"],
        },
        "2027-06-02T01:00:00Z",
    )
    aggregate = put(
        "rec003",
        "quality_aggregate",
        "TRANSFORM",
        {
            "status": "PARTIAL_UNRELIABLE",
            "groups": [{"category": "CAT", "accepted_rows": 1, "accepted_units": 5}],
            "accepted_rows_only_total": 5,
            "missing_usable_expected_ids": ["R2", "R3"],
        },
        "2027-06-02T01:00:00Z",
    )
    request = {
        "actor_id": "neutral-operator",
        "operation": "TRANSFORM",
        "event_at": "2027-06-02T01:00:00Z",
    }
    put(
        "rec003",
        "quality_operation",
        "TRANSFORM",
        {
            "request": request,
            "request_sha256": sha(encoded(request)),
            "command_id": "neutral-transform",
            "revision": 1,
            "observation": {
                "definition_pin": definition,
                "reference_pin": reference,
                "input_pin": raw_ref,
                "report": report,
            },
            "outputs": [derived, aggregate],
        },
        "2027-06-02T01:00:00Z",
    )

    clean_raw = [
        {
            "record_id": f"R{i}",
            "entity_id": "E",
            "observed_at": f"2027-06-01T0{i}:00:00Z",
            "units": i,
        }
        for i in range(1, 4)
    ]
    common_definition = put(
        "common-dq", "quality_definition", "COMMON", {"plan": plan}, "2027-05-31T00:00:00Z"
    )
    common_reference = put(
        "common-dq", "quality_reference", "REF", references, "2027-05-31T00:00:00Z"
    )
    common_raw = put("common-dq", "quality_raw", "RAW", clean_raw, "2027-06-02T00:00:00Z")
    altered_raw = deepcopy(clean_raw)
    altered_raw[1]["units"] = 100
    copy = put("integrity", "test_copy", "COPY", altered_raw, "2027-06-03T09:00:00Z")
    altered_report = {
        **report,
        "input_rows": 3,
        "accepted_rows": 2,
        "failed_rows": 1,
        "missing_expected_in_window_ids": [],
        "missing_usable_expected_ids": ["R2"],
        "failures": [
            {
                "index": 1,
                "row_sha256": sha(encoded(altered_raw[1])),
                "reasons": ["INVALID_INTEGER_UNITS"],
            }
        ],
    }
    put(
        "integrity",
        "transform_report",
        "ALTERED",
        {
            "input_copy_ref": copy,
            "integrity_check_ref": None,
            "integrity_state_at_transform": "NOT_CHECKED",
            "source_refs": {
                "definition": common_definition,
                "reference": common_reference,
                "raw": common_raw,
            },
            "dq_report": altered_report,
        },
        "2027-06-03T09:30:00Z",
    )
    check = put(
        "integrity",
        "integrity_check",
        "LATE-CHECK",
        {
            "checked_copy_ref": copy,
            "expected_source_raw_sha256": common_raw["sha256"],
            "observed_copy_sha256": copy["sha256"],
            "result": "MISMATCH_DETECTED",
            "checked_before_first_transform": False,
        },
        "2027-06-03T10:00:00Z",
    )
    corrected = put("integrity", "test_copy", "COPY", clean_raw, "2027-06-03T11:00:00Z", version=2)
    put(
        "integrity",
        "correction_lineage",
        "CORRECTED",
        {
            "before_ref": copy,
            "after_ref": corrected,
            "check_ref": check,
            "source_original_ref": common_raw,
            "prior_exception_remains_open": True,
        },
        "2027-06-03T11:10:00Z",
    )
    for record, handling in (("INITIAL-ACCEPT", "ACCEPT"), ("RETEST", "QUARANTINE")):
        put(
            "supplementalops",
            "integrity_operation",
            record,
            {
                "semantic_valid": True,
                "content_authentic": False,
                "handling": handling,
                "original_sha256": "0" * 64,
                "received_sha256": "1" * 64,
                "expected_tag": "2" * 64,
                "actual_tag": "3" * 64,
                "validator": "SEMANTIC_ONLY" if handling == "ACCEPT" else "AUTHENTICITY_VERIFIER",
            },
            "2027-09-09T10:00:00Z" if handling == "ACCEPT" else "2027-09-10T10:00:00Z",
        )

    members = [dataset, label]
    returned = [dataset]
    query = {
        "company": COMPANY,
        "branch": BRANCH,
        "as_of": "2027-08-01T00:00:00Z",
        "event_window_start": "2027-01-01T00:00:00Z",
        "event_window_end_exclusive": "2027-02-01T00:00:00Z",
        "page_limit": 32,
        "cursor": "START",
        "timezone": "UTC",
        "transformation": "NONE",
    }
    put(
        "extraction",
        "extract_attempt",
        "FIRST",
        {
            "query": query,
            "returned_refs": returned,
            "source_population_refs": members,
            "excluded_refs": [label],
            "returned_count": 1,
            "excluded_count": 1,
            "declared_source_population_count": 2,
            "returned_refs_sha256": sha(encoded(returned)),
            "export_page_truncated": False,
            "next_cursor": None,
        },
        "2027-08-01T00:00:00Z",
    )
    put(
        "extraction",
        "extract_correction",
        "LATER",
        {
            "query": query,
            "returned_refs": members,
            "source_population_refs": members,
            "excluded_refs": [],
            "returned_count": 2,
            "excluded_count": 0,
            "declared_source_population_count": 2,
            "returned_refs_sha256": sha(encoded(members)),
            "export_page_truncated": False,
            "next_cursor": None,
        },
        "2027-08-02T00:00:00Z",
    )

    population = put(
        "supplementalops",
        "workstation_inventory",
        "ASSETS",
        {
            "resources": [
                {"asset_id": "MEDIA-1", "serial": "S1", "custodian": "neutral-custodian"}
            ],
            "source_of_population": "Independent selected assignment register",
        },
        "2027-09-01T00:00:00Z",
    )
    movement = put(
        "supplementalops",
        "media_movement",
        "DENIED",
        {
            "assets": ["MEDIA-1"],
            "copy_receipt": "MISSING",
            "decision": "DENY_RELEASE",
            "actual_departure": False,
            "native_dependencies": [population],
        },
        "2027-09-02T00:00:00Z",
    )
    movement_copy = put(
        "supplementalops",
        "recovery_operation",
        "COPY-RECEIPT",
        {
            "retrieval_at": "2027-09-03T08:00:00Z",
            "retrieved_sha256": "4" * 64,
            "source_sha256": "4" * 64,
            "exact_bytes": True,
        },
        "2027-09-03T09:00:00Z",
    )
    put(
        "supplementalops",
        "media_movement",
        "CUSTODY",
        {
            "assets": [{"asset_id": "MEDIA-1", "serial": "S1"}],
            "source_custodian": "neutral-custodian",
            "destination_custodian": "neutral-receiver",
            "departed_at": "2027-09-03T10:00:00Z",
            "received_at": "2027-09-03T11:00:00Z",
            "status": "RECEIVED",
            "exact_copy_receipt_id": "COPY-RECEIPT",
            "native_dependencies": [movement_copy, movement],
        },
        "2027-09-03T12:00:00Z",
    )
    put(
        "supplementalops",
        "media_movement",
        "REUSE",
        {
            "asset_id": "MEDIA-1",
            "after_size": 0,
            "after_sha256": sha(b""),
            "old_marker_present": False,
            "preserved_copy_retrievable": True,
            "working_fixture": "/must-never-be-read/reused.bin",
        },
        "2027-10-01T00:00:00Z",
    )

    def privacy_put(role, record, details, at):
        at = _time(at)
        common = {
            "service_id": "neutral-service",
            "dataset_id": "neutral-privacy-dataset",
            "customer_id": "neutral-customer",
            "contracting_entity_id": "neutral-entity",
            "payload_bytes": 0,
            "real_phi_payload": False,
            "real_world_processing_or_transfer": False,
            "event_at": at,
            "available_at": at,
            "dependencies": [],
        }
        return put("privacyops", role, record, {**common, **details}, at)

    privacy_put(
        "privacy_legal_review",
        "ROLES",
        {
            "role": "SIMULATED_BA",
            "direct_ba_duties": ["security"],
            "delegated_customer_duties": ["privacy"],
            "not_sable_harbor_functions": ["CLINICAL_TREATMENT"],
            "reasoning": "Separate customer decisions",
            "period_specific_2027_law_not_asserted": True,
        },
        "2027-08-01T00:00:00Z",
    )
    configuration_approval = privacy_put(
        "privacy_change_approval",
        "ROUTER-APPROVAL",
        {
            "approved_by": "neutral-reviewer",
            "real_world_legal_approval": "UNDETERMINED",
            "approved_rule": "Hold unsupported customer/gate authority before release",
        },
        "2027-08-01T01:00:00Z",
    )
    privacy_put(
        "privacy_configuration",
        "ROUTER-CONFIGURATION",
        {
            "rules": ["customer and gate permit", "exact scope and recipient"],
            "executable_enforcement_established": False,
            "dependencies": [configuration_approval],
        },
        "2027-08-02T00:00:00Z",
    )
    privacy_put(
        "privacy_dataset_inventory",
        "LOCATION",
        {
            "location": {"location_id": "BACKUP", "activity": ["MAINTAINED"]},
            "logical_token_count": 1,
            "seen_logical_token_ids": ["T1"],
            "period": {"start": "2027-09-01T00:00:00Z", "end": "2027-10-01T00:00:00Z"},
        },
        "2027-09-27T00:00:00Z",
    )
    cid = "neutral-case"
    req = privacy_put(
        "privacy_request",
        "REQUEST",
        {
            "case_id": cid,
            "recipient_id": "RECIPIENT",
            "logical_token_id": "T1",
            "inlet_sequence": 1,
            "route": "164.506(c)(4)",
            "request_facts": {
                "sender_relationship": True,
                "recipient_relationship": authorize,
                "information_relates_to_both_relationships": authorize,
                "ordinary_consent_present": True,
                "required_authorization": False,
                "operation": "QUALITY_ASSESSMENT",
            },
        },
        "2027-09-21T09:00:00.000000+00:00",
    )
    customer = privacy_put(
        "privacy_customer_decision",
        "CUSTOMER",
        {
            "case_id": cid,
            "recipient_id": "RECIPIENT",
            "decision": "PERMIT" if authorize else "HOLD",
            "dependencies": [req],
        },
        "2027-09-21T10:00:00.000000+00:00",
    )
    gate = privacy_put(
        "privacy_gate_decision",
        "GATE",
        {
            "case_id": cid,
            "recipient_id": "RECIPIENT",
            "decision": "PERMIT" if authorize else "HOLD",
            "allowed_scope": ["T1"] if authorize else [],
            "dependencies": [req, customer],
        },
        "2027-09-21T11:00:00.000000+00:00",
    )
    release = privacy_put(
        "privacy_release",
        "RELEASE",
        {
            "case_id": cid,
            "recipient_id": "RECIPIENT",
            "execution_status": "DELIVERED",
            "released_scope": ["T1"],
            "worker_authority_source": "neutral-ledger",
            "dependencies": [req, customer, gate],
        },
        "2027-09-21T12:00:00.000000+00:00",
    )
    privacy_put(
        "privacy_receipt",
        "RECEIPT",
        {
            "case_id": cid,
            "recipient_id": "RECIPIENT",
            "status": "RECIPIENT_ACKNOWLEDGED",
            "copy_in_recipient_scope": True,
            "dependencies": [release],
        },
        "2027-09-21T13:00:00.000000+00:00",
    )
    privacy_put(
        "privacy_reconciliation",
        "EARLY-CLOSE",
        {
            "period": {"start": "2027-09-01T00:00:00Z", "end": "2027-10-01T00:00:00Z"},
            "case_ids": [cid],
            "inlet_sequence_first": 1,
            "inlet_sequence_last": 1,
            "inlet_sequence_gaps": [],
            "customer_decision_count": 1,
            "counsel_gate_count": 1,
            "execution_journal_count": 1,
            "delivery_status_count": 1,
            "delivered_count": 1,
            "withheld_count": 0,
            "delivery_authority_mismatch_count": 0 if authorize else 1,
        },
        "2027-09-30T20:00:00.000000+00:00",
    )
    put(
        "phi_ba",
        "operation_scope",
        "BOUNDARY",
        {
            "sim_service_id": "neutral-BA-service",
            "sim_customer_id": "neutral-customer",
            "fixture_contains_real_phi": False,
            "declared_responsibilities": ["SYNTHETIC_HOSTING"],
            "actual_legal_applicability": "UNDETERMINED",
        },
        "2027-08-01T00:00:00Z",
    )
    if extra_author:
        extra_author(
            put,
            {
                "policy": policy,
                "review": review,
                "common_raw": common_raw,
                "common_definition": common_definition,
                "common_reference": common_reference,
                "copy": copy,
            },
        )
    put(
        "supplementalops",
        "privacy_responsibility",
        "REGULATOR-BOUNDARY",
        {
            "responsibility": "Preserve and route qualified regulator requests",
            "authority": "PENDING_REQUEST_SPECIFIC_DECISION",
            "ordinary_disclosure_is_not_regulator_request": True,
        },
        "2027-08-01T00:00:00Z",
    )

    # All sources precede the audit. No audit answers or actual Sable Harbor source are imported.
    engine = Engine(root / "audit", repository=REPO, company_root=source_root)
    operator = engine.store.provision("Neutral access operator", ["instructor"])
    auditor = engine.store.provision("Neutral independent examiner", ["learner"])
    state = engine.create(
        operator["id"],
        {
            "command_id": "neutral-data-record-birth",
            "title": "Neutral B05 collected originals",
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
                "control_ids": ["SH-DAT-001"],
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
    requested = command(
        auditor["id"],
        "pbc.create",
        {
            "title": "Selected native data originals",
            "purpose": "Examine neutral dated business records",
            "control_id": "SH-DAT-001",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    rid = requested["requests"][-1]["id"]
    command(auditor["id"], "pbc.issue", {"request_id": rid})
    for meta in native:
        command(
            auditor["id"],
            "company.collect",
            {
                "system_id": meta["system"],
                "record_id": meta["record"],
                "version": meta["version"],
                "request_id": rid,
            },
        )
    state = engine.store.get(auditor["id"], eid)
    rows = []
    for artifact in state["artifacts"]:
        assert (
            artifact["status"] == "AVAILABLE"
            and artifact["source"]["kind"] == "COLLECTED_COMPANY_SOURCE"
        )
        receipt = artifact["source"]["receipt"]
        assert receipt["engagement_id"] == eid and receipt["principal_id"] == auditor["id"]
        src = receipt["source"]
        family, role = src["system"].split(".", 1)
        rows.append(
            {
                "source": src,
                "receipt": receipt,
                "artifact_id": artifact["id"],
                "artifact_sha256": artifact["sha256"],
                "retained_bytes": engine.artifacts.read(artifact),
                "content_type": src["provenance"]["content_type"],
                "logical_family": family,
                "logical_system": role,
            }
        )
    return {
        "rows": rows,
        "as_of": state["simulated_at"],
        "engine": engine,
        "auditor": auditor["id"],
        "engagement": eid,
        "source": source,
        "root": root,
    }


@pytest.fixture(scope="module")
def originals(tmp_path_factory):
    return build_originals(tmp_path_factory)


def outputs(originals):
    return inspections(
        originals["rows"], as_of=originals["as_of"], scratch_root=originals["root"] / "unused"
    )


def obs(result, prefix):
    return [o for o in result["observations"] if prefix in o["id"]]


def task(results, control, clause):
    return next(r for r in results if r["task_id"] == f"TASK-{control}-corporate-{clause}")


def reseal(row, change):
    doc = json.loads(row["retained_bytes"])
    change(doc)
    row["retained_bytes"] = encoded(doc)
    row["source"]["sha256"] = sha(row["retained_bytes"])
    row["artifact_sha256"] = row["source"]["sha256"]
    row["receipt"]["source"] = deepcopy(row["source"])
    row["receipt"]["content_bytes"] = len(row["retained_bytes"])


def test_all_50_exact_tasks_have_distinct_authored_contracts_and_real_collected_observations(
    originals,
):
    results = outputs(originals)
    assert [r["task_id"] for r in results] == authored_contracts()["selected_task_ids"]
    assert len(results) == 50
    assert len({r["performed"] for r in results}) == len({r["unperformed"] for r in results}) == 50
    contracts = task_contracts()
    for result in results:
        assert result["performed"] == contracts[result["task_id"]]["performed"]
        assert result["unperformed"] == contracts[result["task_id"]]["unperformed"]
        assert result["disposition"]["status"] == "IN_PROGRESS"
        assert result["disposition"]["conclusion"] in {"LIMITATION", "FAIL"}
        assert (
            result["result"]["population"]["full_period_enterprise_denominator_established"]
            is False
        )
        assert not result["result"]["professional_pass_or_full_authored_task_completion_asserted"]
        assert result["artifact_ids"]
        assert all(
            0 < len(o["evidence"]) <= 20 and len(o["id"]) <= 128 for o in result["observations"]
        )
        assert all(
            o["status"] in {"OBSERVED", "EXCEPTION_RECORDED", "SUPPORT_UNAVAILABLE"}
            for o in result["observations"]
        )
        assert all(
            e["artifact_id"] in result["artifact_ids"]
            for o in result["observations"]
            for e in o["evidence"]
        )
    assert len(originals["rows"]) == len(
        originals["engine"].store.get(originals["auditor"], originals["engagement"])["artifacts"]
    )


def test_reperforms_actual_typed_quality_rows_and_historical_partial_aggregate(originals):
    result = task(outputs(originals), "SH-REC-003", "TOE")
    facts = obs(result, "quality-transform-")[0]["facts"]
    assert facts["recomputed_report"]["accepted_rows"] == 1
    assert facts["recomputed_report"]["failed_rows"] == 2
    assert facts["recomputed_report"]["missing_expected_in_window_ids"] == ["R3"]
    assert facts["recomputed_aggregate"]["accepted_rows_only_total"] == 5
    assert all(not d for d in facts["recorded_output_differences"].values())
    assert result["disposition"]["conclusion"] == "FAIL"


def test_actual_due_population_keeps_missing_month_and_excluded_preprogram_interval(originals):
    results = activity_observations(History(originals["rows"], originals["as_of"]))
    facts = next(o["facts"] for o in results if o["id"].startswith("activity-due-population-"))
    due = {t["trigger_id"]: t for t in facts["due_tests"]}
    assert set(due) == {"NOV", "DEC"}
    assert not due["NOV"]["missing_due_occurrence"] and due["NOV"]["original_before_due"]
    assert due["DEC"]["missing_due_occurrence"]
    assert facts["scope_excluded_interval"]["reason"] == "Neutral procedure not effective"
    assert facts["complete_activity_log_or_prior_candidate_history_not_established"]


def test_collected_original_does_not_cure_prior_review_retrieval_omission(tmp_path_factory):
    def author(put, unused):
        put(
            "supplementalops",
            "procedure_operation",
            "CLAIMED-COMPLETE",
            {
                "operator_statement": "Review complete",
                "performer": "neutral-reviewer",
                "input_originals": ["policy_document/POLICY/1"],
                "required_original_retrieval": [],
                "retrieval_count": 0,
                "due_at": "2027-11-03T00:00:00Z",
            },
            "2027-11-02T01:00:00Z",
        )

    fixture = build_originals(tmp_path_factory, extra_author=author)
    results = activity_observations(History(fixture["rows"], fixture["as_of"]))
    facts = next(
        o["facts"]
        for o in results
        if o["facts"].get("operator_statement") == "Review complete"
        and o["facts"].get("required_originals_absent_from_recorded_review_retrieval")
    )
    assert len(facts["required_originals_absent_from_recorded_review_retrieval"]) == 1
    assert facts["required_originals"][0]["status"] == "EXACT_COLLECTED_ORIGINAL"
    assert not facts["recorded_retrieval_count_differs"]
    assert next(o["status"] for o in results if o["facts"] is facts) == "EXCEPTION"


def test_calendar_later_of_current_effective_and_actual_superseded_original_retrieval(originals):
    result = task(outputs(originals), "SH-DAT-003", "ACTION-H-RETENTION")
    facts = obs(result, "retention-calendar-")[0]["facts"]
    assert facts["date_tests"][0]["recomputed_floor"] == "2033-11-01"
    assert facts["date_tests"][1]["recomputed_denial"] is True
    assert (
        facts["retrievable_superseded_originals"][0]["actual_collected_status"]
        == "EXACT_COLLECTED_ORIGINAL"
    )
    assert facts["earlier_pending_legal_hold_not_closed"]
    assert add_years("2024-02-29", 6).isoformat() == "2030-02-28"


def test_original_extraction_omission_survives_later_corrected_index(originals):
    facts = [o["facts"] for o in obs(task(outputs(originals), "SH-REC-002", "TOE"), "extraction-")]
    assert facts[0]["omitted_declared_native_members"]
    assert not facts[1]["omitted_declared_native_members"]
    assert all(not f["returned_reference_digest_differs"] for f in facts)
    assert all(f["declared_index_is_not_independent_enterprise_denominator"] for f in facts)


def test_integrity_joins_exact_common_originals_and_keeps_precheck_gap_and_semantic_acceptance(
    originals,
):
    result = task(outputs(originals), "SH-DAT-004", "ACTION-H-INTEGRITY")
    facts = obs(result, "integrity-at-transform-")[0]["facts"]
    assert facts["missing_exact_common_inputs"] == []
    assert facts["actual_copy_matches_collected_baseline_bytes"] is False
    assert facts["effective_pretransform_check_collected"] is False
    assert facts["recomputed_quality_report"]["failed_rows"] == 1
    receipts = obs(result, "copy-authenticity-")
    assert receipts[0]["status"] == "EXCEPTION_RECORDED" and receipts[1]["status"] == "OBSERVED"
    assert all(
        o["facts"]["cryptographic_authentication_and_live_transfer_encryption_reperformed"] is False
        for o in receipts
    )


def test_privacy_route_and_reused_census_are_dynamic_and_do_not_cure_period_tail(
    originals, tmp_path_factory
):
    unauthorized = task(outputs(originals), "SH-DAT-002", "CHECK-HIPAA:164.506")
    assert unauthorized["disposition"]["conclusion"] == "FAIL"
    authorized = build_originals(tmp_path_factory, authorize=True)
    permit = task(outputs(authorized), "SH-DAT-002", "CHECK-HIPAA:164.506")
    assert permit["disposition"]["conclusion"] == "LIMITATION"
    census = obs(task(outputs(authorized), "SH-DAT-002", "TOE"), "privacy-census-")[0]["facts"]
    assert not census["recorded_mismatch_case_ids"]
    assert census["unestablished_period_tail"]
    assert not census["selected_population_corroborated"]


def test_movement_metadata_is_not_collected_copy_or_hardware_sanitization(
    originals,
):
    result = task(outputs(originals), "SH-REC-004", "ACTION-H-PHYSICAL-MOVEMENT")
    facts = [o["facts"] for o in obs(result, "media-custody-")]
    receipt = next(f for f in facts if "copy_receipt_available_before_departure" in f["tests"])
    assert receipt["tests"]["copy_receipt_available_before_departure"]
    assert not receipt["tests"]["exact_working_copy_bytes_collected"]
    reused = next(f for f in facts if "recorded_empty_digest" in f["tests"])
    assert reused["tests"]["recorded_empty_digest"]
    assert not reused["tests"]["actual_reused_working_file_bytes_collected"]


@pytest.mark.parametrize(
    "field",
    [
        "source-version",
        "receipt-version",
        "receipt-count",
        "receipt-actor",
        "future-source",
        "artifact-hash",
        "logical-role",
        "mixed-branch",
    ],
)
def test_rejects_intact_original_receipt_type_identity_clock_and_routing_defects(originals, field):
    rows = deepcopy(originals["rows"])
    row = rows[0]
    if field == "source-version":
        row["source"]["version"] = True
    elif field == "receipt-version":
        row["receipt"]["source"]["version"] = True
    elif field == "receipt-count":
        row["receipt"]["content_bytes"] = True
    elif field == "receipt-actor":
        row["receipt"]["principal_id"] = "another-performer"
    elif field == "future-source":
        row["source"]["available_at"] = "2029-01-01T00:00:00Z"
    elif field == "artifact-hash":
        row["retained_bytes"] += b" "
    elif field == "logical-role":
        row["logical_system"] = "alias"
    else:
        row["source"]["branch"] = "another-branch"
        row["receipt"]["source"]["branch"] = "another-branch"
    with pytest.raises(ProcedureError):
        inspections(rows, as_of=originals["as_of"], scratch_root=originals["root"])


def test_cached_documents_cannot_override_actual_ordinary_collected_bytes(originals):
    rows = deepcopy(originals["rows"])
    for row in rows:
        row["document"] = {"decision": "PERMIT", "actual_deletion": True, "units": 500}
    assert inspections(rows, as_of=originals["as_of"], scratch_root=originals["root"]) == outputs(
        originals
    )


def test_missing_exact_common_dependency_does_not_substitute_rec003_or_cached_result(originals):
    rows = [r for r in originals["rows"] if r["logical_family"] != "common-dq"]
    result = task(
        inspections(rows, as_of=originals["as_of"], scratch_root=originals["root"]),
        "SH-DAT-004",
        "TOE",
    )
    facts = obs(result, "integrity-at-transform-")[0]["facts"]
    assert sorted(facts["missing_exact_common_inputs"]) == ["definition", "raw", "reference"]
    assert facts["actual_copy_matches_collected_baseline_bytes"] is None
    assert facts["recomputed_quality_report"] is None


def test_quality_rejects_bool_units_as_data_failure_and_keeps_outside_window_exclusions_separate():
    reference = [{"entity_id": "E", "category": "C"}]
    plan = {
        "event_window": {"start": "2027-01-01T00:00:00Z", "end": "2027-02-01T00:00:00Z"},
        "expected_record_ids": ["R1"],
        "reference_rows": reference,
        "maximum_units": 10,
    }
    raw = [
        {"record_id": "R1", "entity_id": "E", "observed_at": "2027-01-02T00:00:00Z", "units": True},
        {"record_id": "OUT", "entity_id": "E", "observed_at": "2026-12-31T00:00:00Z", "units": 5},
    ]
    report, _, _ = quality(plan, raw, reference, at="2027-03-01T00:00:00Z")
    assert report["failed_rows"] == 1 and report["intentional_exclusions"] == 1
    assert report["failures"][0]["reasons"] == ["INVALID_INTEGER_UNITS"]


def test_regulator_rights_and_classification_keep_distinct_unperformed_clauses(originals):
    results = outputs(originals)
    regulator = task(results, "SH-REC-002", "ACTION-H-REGULATOR")
    rights = task(results, "SH-DAT-002", "ACTION-H-RIGHTS-ASSISTANCE")
    classification = task(results, "SH-DAT-001", "CHECK-SOC2:C1.1")
    assert (
        obs(regulator, "regulator-authority-")[0]["facts"][
            "actual_selected_regulator_request_originals"
        ]
        == []
    )
    assert (
        obs(rights, "rights-assistance-")[0]["facts"][
            "electronic_copy_accepted_amendment_and_upstream_accounting_reperformed"
        ]
        is False
    )
    assert any(
        o["facts"].get("historical_invalid_local_label")
        for o in obs(classification, "classification-")
    )
    assert regulator["unperformed"] != rights["unperformed"] != classification["unperformed"]


def test_callback_does_not_mutate_source_audit_or_follow_business_paths(originals, monkeypatch):
    before = {
        p: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [originals["source"].path, originals["engine"].store.db_path]
    }
    original = Path.read_bytes

    def guarded(path):
        if "must-never-be-read" in str(path):
            raise AssertionError("Company document path followed")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    outputs(originals)
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before}


def test_actual_ordinary_collected_50_vector_passes_unchanged_shared_pair_preflight(originals):
    from enterprise.audit_suite.full_scope_company_pair import BoundWorkroom

    contracts = task_contracts()
    for result in outputs(originals):
        BoundWorkroom._validate_inspection(
            None, originals["rows"], result, contracts[result["task_id"]]
        )


def test_callback_opens_no_database_and_reuses_accepted_privacy_calculation_once(
    originals, monkeypatch
):
    import sqlite3

    from enterprise.audit_suite import source_data_record_methods as methods

    calls, actual = [], methods.privacy.examine

    def counted(rows, *, as_of):
        calls.append((len(rows), as_of))
        return actual(rows, as_of=as_of)

    def forbidden(*unused, **also_unused):
        raise AssertionError("Pure method attempted database access")

    monkeypatch.setattr(methods.privacy, "examine", counted)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    assert len(outputs(originals)) == 50
    assert len(calls) == 1 and calls[0][1] == originals["as_of"]


def test_collected_native_meeting_note_cannot_replace_exact_common_definition(tmp_path_factory):
    def author(put, refs):
        alias = put(
            "common-dq", "meeting_note", "NOT-DEFINITION", {"plan": {}}, "2027-07-01T00:00:00Z"
        )
        put(
            "integrity",
            "transform_report",
            "ALIAS-TEST",
            {
                "input_copy_ref": refs["copy"],
                "integrity_check_ref": None,
                "source_refs": {
                    "definition": alias,
                    "raw": refs["common_raw"],
                    "reference": refs["common_reference"],
                },
                "dq_report": {},
            },
            "2027-07-02T00:00:00Z",
        )

    fixture = build_originals(tmp_path_factory, extra_author=author)
    with pytest.raises(ProcedureError, match="common quality native role"):
        outputs(fixture)


def test_genuine_delayed_check_publication_cannot_be_pretransform_availability(tmp_path_factory):
    def author(put, refs):
        check = put(
            "integrity",
            "integrity_check",
            "LATE-ORIGINAL",
            {
                "checked_copy_ref": refs["copy"],
                "expected_source_raw_sha256": refs["common_raw"]["sha256"],
                "observed_copy_sha256": refs["copy"]["sha256"],
                "result": "MISMATCH_DETECTED",
                "checked_before_first_transform": True,
            },
            "2027-07-03T00:00:00Z",
        )
        put(
            "integrity",
            "transform_report",
            "CHECK-NOT-YET-AVAILABLE",
            {
                "input_copy_ref": refs["copy"],
                "integrity_check_ref": check,
                "source_refs": {
                    "definition": refs["common_definition"],
                    "raw": refs["common_raw"],
                    "reference": refs["common_reference"],
                },
                "dq_report": {},
            },
            "2027-07-02T00:00:00Z",
        )

    fixture = build_originals(tmp_path_factory, extra_author=author)
    result = task(outputs(fixture), "SH-DAT-004", "TOE")
    facts = [o["facts"] for o in obs(result, "integrity-at-transform-")]
    late = next(
        f for f in facts if f["integrity_check_status_at_transform"] == "UNAVAILABLE_AT_OPERATION"
    )
    assert not late["effective_pretransform_check_collected"]
    assert late["actual_check_claim"]["checked_before_first_transform"] is True


def test_distinct_privacy_clause_screens_use_actual_ordinary_collected_request_facts(
    tmp_path_factory,
):
    cases = [
        (
            "EXPIRED",
            "164.508",
            {
                "authorization_id": "A",
                "authorized_discloser": "CUSTOMER",
                "description": "TOKEN",
                "purpose": "COPY",
                "signature_token": "S",
                "signature_date": "2027-01-01",
                "named_recipient": "R",
                "authority_verified_by_customer": True,
                "plain_language": True,
                "right_to_revoke_statement": True,
                "conditioning_statement": True,
                "redisclosure_statement": True,
                "customer_copy_provided": True,
                "expiration_at": "2027-01-31T00:00:00Z",
                "revoked_at": None,
            },
            "AUTHORIZATION_EXPIRED_OR_UNSPECIFIED",
        ),
        (
            "NOTES",
            "164.508(a)(2)",
            {"separate_notes_authorization": False, "combined_with_general_authorization": True},
            "SEPARATE_NOTES_AUTHORITY_NOT_ESTABLISHED",
        ),
        (
            "MARKETING",
            "164.508(a)(3)",
            {"remuneration": True, "remuneration_statement": False},
            "REMUNERATION_AUTHORITY_NOT_ESTABLISHED",
        ),
        (
            "FAMILY",
            "164.510(b)(2)",
            {
                "individual_available": True,
                "known_preference": "OBJECTS",
                "requested_scope": ["ALL"],
                "relevant_scope": ["CARE"],
            },
            "KNOWN_OBJECTION",
        ),
        (
            "SUBPOENA",
            "164.512(e)(1)(ii)",
            {
                "process_kind": "SUBPOENA_WITHOUT_ORDER",
                "recipient_authority_verified": True,
                "notice_assurance_documented": False,
                "qualified_protective_order_assurance_documented": False,
            },
            "SUBPOENA_ASSURANCE_NOT_ESTABLISHED",
        ),
        (
            "DEID",
            "164.514(b)(2)",
            {
                "method": "SAFE_HARBOR_CANDIDATE",
                "residual_identifier_categories": ["FULL_DATE"],
                "actual_knowledge_of_identifiability": False,
            },
            "RESIDUAL_IDENTIFIERS",
        ),
        (
            "KNOWLEDGE",
            "164.514(b)(2)",
            {
                "method": "SAFE_HARBOR_CANDIDATE",
                "residual_identifier_categories": [],
                "actual_knowledge_of_identifiability": True,
            },
            "ACTUAL_KNOWLEDGE_OF_LINKABILITY",
        ),
        (
            "MINIMUM",
            "164.514(d)",
            {"entire_record_requested": True, "entire_record_necessity_justified": False},
            "ENTIRE_RECORD_MINIMUM_SCOPE_NOT_JUSTIFIED",
        ),
        (
            "LDS",
            "164.514(e)",
            {
                "method": "LIMITED_DATA_SET",
                "dua_executed_in_simulation": False,
                "no_reidentification_no_contact_terms": False,
            },
            "LDS_CUSTOMER_AGREEMENT_NOT_ESTABLISHED",
        ),
        (
            "PRENOTICE",
            "164.522(a)(2)(iii)",
            {
                "individual_agreed_to_termination": False,
                "termination_basis": "CUSTOMER_UNILATERAL_NOTICE",
                "token_created_received_at": "2027-01-01T00:00:00Z",
                "termination_notice_at": "2027-02-01T00:00:00Z",
            },
            "PRENOTICE_RECORD_RESTRICTION_REMAINS",
        ),
        (
            "PAID",
            "164.522(a)(1)(vi)",
            {
                "solely_paid_in_full_item": True,
                "paid_by_individual_not_plan": True,
                "health_plan_disclosure": True,
                "otherwise_required_by_law": False,
            },
            "PAID_IN_FULL_RESTRICTION_REMAINS",
        ),
        (
            "CONTACT",
            "164.522(b)",
            {
                "reasonable_request": True,
                "default_contact_suppressed": False,
                "explanation_demanded": True,
            },
            "CONFIDENTIAL_CONTACT_INSTRUCTION_NOT_ESTABLISHED",
        ),
    ]

    def author(put, unused):
        at = _time("2027-09-28T09:00:00Z")
        for number, (case_id, route, facts, _) in enumerate(cases, 2):
            put(
                "privacyops",
                "privacy_request",
                case_id,
                {
                    "service_id": "neutral-service",
                    "dataset_id": "neutral-privacy-dataset",
                    "customer_id": "neutral-customer",
                    "contracting_entity_id": "neutral-entity",
                    "payload_bytes": 0,
                    "real_phi_payload": False,
                    "real_world_processing_or_transfer": False,
                    "event_at": at,
                    "available_at": at,
                    "dependencies": [],
                    "case_id": case_id,
                    "recipient_id": "R",
                    "inlet_sequence": number,
                    "route": route,
                    "request_facts": facts,
                },
                at,
            )

    fixture = build_originals(tmp_path_factory, extra_author=author)
    history = History(fixture["rows"], fixture["as_of"])
    mapped = {
        r["document"]["case_id"]: r for r in history.select("privacyops", {"privacy_request"})
    }
    for case_id, _, _, expected in cases:
        result = route_screen(mapped[case_id])
        assert expected in result["hold_reasons"]
        assert not result["qualified_period_legal_decision_reperformed"]
