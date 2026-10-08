"""Real ordinary collection of owned neutral originals, never source recipes."""

import copy
import json
from pathlib import Path

import pytest
from test_collected_byte_recovery_method import ordinary_inputs, row

from enterprise.audit_suite.collected_byte_recovery_method import reference
from enterprise.audit_suite.collected_incident_history import History
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.full_scope_company_pair import (
    GENERAL_METHOD_SCHEMA,
    GENERAL_METHOD_VERDICT,
    FullScopePair,
    PinnedReview,
)
from enterprise.audit_suite.persistent_company_journey import native_rows, write
from enterprise.audit_suite.source_incident_complaints_methods import (
    attempted_intake,
    breach_and_notice,
    contracts,
    corrective_history,
    description_population,
    examine,
    response_history,
    task_plan,
)
from enterprise.audit_suite.source_library_audit import (
    LIBRARY_MANIFEST_SCHEMA,
    LIBRARY_REVIEW_SCHEMA,
    LIBRARY_REVIEW_VERDICT,
    AcceptedLibrary,
    BusinessRoute,
    file_sha,
)

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "enterprise/generated/audit-suite/build/program-pack.json"
pytestmark = pytest.mark.skipif(
    not PACK.is_file(), reason="Exact private409 instruction pack absent"
)


def originals(
    *,
    no_cases=False,
    future_replay=False,
    self_validation=False,
    future_agent=False,
    future_occurrence=False,
    late_contract=False,
    affected_count=500,
):
    values = []

    def add(family, role, record, at, d, version=1):
        r = row(
            family + "." + role,
            record,
            at,
            {
                "engineering_neutral_fixture": True,
                "recorded_at": at,
                **({"incident_id": "INC-NEUTRAL"} if family == "incident-history" else {}),
                **d,
            },
            version=version,
        )
        values.append(r)
        return r

    def refs(*rows):
        return [reference(r["source"]) for r in rows]

    inventory = add(
        "incident-history",
        "inventory",
        "RULES",
        "2027-05-01T09:00:00Z",
        {
            "local_rules": {
                "error_threshold_percent": 50,
                "escalation_due_minutes": 10,
                "recovery_probe_required_successes": 2,
                "recovery_checkpoint_age_limit_minutes": 5,
            },
            "commander": "COMMANDER",
            "responder": "RESPONDER",
            "outside_response_reviewer": "REVIEWER",
            "service_definition_state": "LOCAL_NONPERSONAL_EXERCISE_ONLY",
        },
    )
    monitoring = add(
        "incident-history",
        "monitoring",
        "PROBES",
        "2027-05-02T09:00:00Z",
        {
            "requests": [
                {
                    "request_id": f"FAIL-{n}",
                    "http_status": 503,
                    "observed_at": f"2027-05-02T08:59:4{n}Z",
                }
                for n in (1, 2)
            ],
            "total_requests": 2,
            "error_requests": 2,
            "window_ends_at": "2027-05-02T09:00:00Z",
            "source_refs": refs(inventory),
        },
    )
    ticket = add(
        "incident-history",
        "incident_ticket",
        "INCIDENT",
        "2027-05-02T09:01:00Z",
        {
            "source_refs": refs(monitoring, inventory),
            "discovered_at": "2027-05-02T09:00:00Z",
            "escalation_due_at": "2027-05-02T09:10:00Z",
            "local_severity": "LOCAL-SEV1",
            "decision": "INITIATE_ESCALATION",
        },
    )
    queued = add(
        "incident-history",
        "escalation",
        "PAGE",
        "2027-05-02T09:05:00Z",
        {
            "source_refs": refs(ticket),
            "queued_at": "2027-05-02T09:05:00Z",
            "delivered_at": None,
            "delivery_state": "QUEUED",
            "recipient": "COMMANDER",
        },
    )
    ticket = add(
        "incident-history",
        "incident_ticket",
        "INCIDENT",
        "2027-05-02T09:07:00Z",
        {
            "source_refs": refs(ticket, queued),
            "discovered_at": "2027-05-02T09:00:00Z",
            "escalation_due_at": "2027-05-02T09:10:00Z",
            "local_severity": "LOCAL-SEV1",
            "decision": "COMMAND_ACKNOWLEDGED",
        },
        version=2,
    )
    delivered = add(
        "incident-history",
        "escalation",
        "PAGE",
        "2027-05-02T09:20:00Z",
        {
            "source_refs": refs(ticket, queued),
            "queued_at": "2027-05-02T09:05:00Z",
            "delivered_at": "2027-05-02T09:20:00Z",
            "delivery_state": "DELIVERED",
            "recipient": "COMMANDER",
        },
        version=2,
    )
    recovery = add(
        "incident-history",
        "recovery",
        "RECOVERY",
        "2027-05-02T09:30:00Z",
        {
            "source_refs": refs(ticket, inventory),
            "state": "STARTED",
            "performed_by": "RESPONDER",
            "recovery_credential_ref": "LOCAL-REFERENCE_ONLY",
        },
    )
    monitoring = add(
        "incident-history",
        "monitoring",
        "PROBES",
        "2027-05-02T10:00:00Z",
        {
            "source_refs": refs(recovery),
            "requests": [
                {
                    "request_id": f"SUCCESS-{n}",
                    "http_status": 200,
                    "observed_at": f"2027-05-02T09:59:5{n}Z",
                }
                for n in (1, 2)
            ],
            "total_requests": 2,
            "error_requests": 0,
            "checkpoint_captured_at": "2027-05-02T09:58:00Z",
            "checkpoint_observed_at": "2027-05-02T10:00:00Z",
        },
        version=2,
    )
    restored = add(
        "incident-history",
        "recovery",
        "RECOVERY",
        "2027-05-02T10:01:00Z",
        {
            "source_refs": refs(monitoring, inventory),
            "state": "VERIFIED_BY_RESPONDER",
            "successful_probes": 2,
            "checkpoint_age_minutes": 2,
            "restored_at": "2027-05-02T10:00:00Z",
            "verified_by": "RESPONDER",
            "independent_validation": "NOT_CLAIMED",
        },
        version=2,
    )
    add(
        "incident-history",
        "status_updates",
        "SERVICE-UPDATE",
        "2027-05-02T10:02:00Z",
        {
            "source_refs": refs(restored),
            "audience": ["INTERNAL"],
            "sent_by": "COMMANDER",
            "service_state": "LOCAL_RECOVERY_OBSERVED",
        },
    )
    review = add(
        "incident-history",
        "postincident_review",
        "REVIEW",
        "2027-05-03T09:00:00Z",
        {
            "source_refs": refs(delivered, restored),
            "reviewed_by": "REVIEWER",
            "observed_service_restoration_minutes": 60,
            "outage_cause": "NOT_ESTABLISHED_FROM_PROBES",
            "causal_assessment_status": "MANAGEMENT_INTERPRETATION_ONLY",
            "remaining_investigation": "Need separate diagnostic originals",
            "risk_update": "Inspect dispatch dependency",
        },
    )
    action = add(
        "incident-history",
        "corrective_action",
        "ACTION",
        "2027-05-03T09:01:00Z",
        {
            "source_refs": refs(review),
            "owner": "RESPONDER",
            "due_at": "2027-05-05T09:00:00Z",
            "state": "PLANNED",
            "change": "local queued page timeout",
            "completion_condition": "timed replay",
        },
    )
    action = add(
        "incident-history",
        "corrective_action",
        "ACTION",
        "2027-05-04T09:00:00Z",
        {
            "source_refs": refs(action),
            "owner": "RESPONDER",
            "due_at": "2027-05-05T09:00:00Z",
            "state": "IMPLEMENTED_COMPANY_CLAIM",
            "change": "local queued page timeout",
            "completion_condition": "timed replay",
        },
        version=2,
    )
    replay = add(
        "incident-history",
        "dispatch_replay",
        "REPLAY",
        "2027-05-04T09:59:00Z",
        {
            "source_refs": refs(action),
            "queued_at": "2028-01-01T09:56:00Z" if future_replay else "2027-05-04T09:56:00Z",
            "fallback_delivered_at": "2028-01-01T09:59:00Z"
            if future_replay
            else "2027-05-04T09:59:00Z",
            "timeout_minutes": 3,
            "actor": "RESPONDER",
            "delivery_state": "DELIVERED",
            "production_dispatch": False,
        },
    )
    for n, reported in ((1, 5), (2, 3)):
        add(
            "incident-history",
            "action_validation",
            "VALIDATION",
            f"2027-05-04T10:0{n}Z",
            {
                "source_refs": refs(action, replay),
                "queued_at": "2027-05-04T09:56:00Z",
                "fallback_delivered_at": "2027-05-04T09:59:00Z",
                "expected_timeout_minutes": 3,
                "elapsed_minutes": reported,
                "validated_by": "RESPONDER" if self_validation else "REVIEWER",
            },
            version=n,
        )
    add(
        "assurance",
        "issue_finding",
        "CLOSURE-CLAIM",
        "2027-05-06T09:00:00Z",
        {
            "finding_closed": True,
            "validation_performed": False,
            "durable_bypass_prevention_implemented": False,
            "disclosed_incident_ids": [],
            "source_refs": refs(review),
        },
    )
    denied = add(
        "supplementalops",
        "access_operation",
        "DENIED-OPERATION",
        "2027-05-01T10:00:00Z",
        {"decision": "DENY", "request": {"request_id": "DENIED-OPERATION"}},
    )
    add(
        "supplementalops",
        "incident_intake",
        "ATTEMPT-INBOX",
        "2027-05-02T09:30:00Z",
        {
            "source_operation_ids": ["DENIED-OPERATION"],
            "source_refs": refs(denied),
            "security_incident_definition_includes_attempts": True,
            "received_at": "2027-05-02T09:00:00Z",
            "succeeded": False,
            "intake_type": "ATTEMPTED_UNAUTHORIZED_ACCESS",
            "reported_by": "REPORTER",
            "receiver": "SECURITY",
        },
    )
    add(
        "prdconcern",
        "simulated_inbox",
        "UNVERIFIED-CONCERN",
        "2027-05-07T09:00:00Z",
        {"claimant_customer_identity_verified": False, "real_external_messages_sent": 0},
    )
    policy = add(
        "supplementalops",
        "policy_document",
        "TRAINING-NOTICE-POLICY",
        "2027-05-01T08:00:00Z",
        {
            "training_max_notice_days": 60,
            "training_oral_delay_ceiling_days": 30,
            "training_required_notice_content_fields": [
                "description",
                "data_types",
                "help_contact",
            ],
            "policy_text": "INERT COMPANY BYTES, NEVER EXECUTE ME",
        },
    )
    contract = add(
        "phi_ba",
        "contract_register",
        "TRAINING-NOTICE-CONTRACT",
        "2027-06-01T08:00:00Z" if late_contract else "2027-05-01T08:01:00Z",
        {
            "training_notice_hours": 24,
            "synthetic_terms": [],
            "actual_legal_applicability": "UNDETERMINED",
        },
    )
    awareness = add(
        "supplementalops",
        "incident_intake",
        "AGENT-DISCOVERY",
        "2027-05-08T09:00:00Z",
        {
            "source_operation_ids": [],
            "received_at": "2028-01-01T08:00:00Z" if future_agent else "2027-05-08T08:00:00Z",
            "reported_by": "AGENT",
            "receiver": "SECURITY",
            "security_incident_definition_includes_attempts": False,
        },
    )
    case = {
        "case_id": "FICTIONAL-DISCLOSURE",
        "occurred_at": "2028-01-01T08:00:00Z" if future_occurrence else "2027-05-07T08:00:00Z",
        "phi_involved": True,
        "impermissible_use_or_disclosure": True,
        "encryption_protection_claimed": True,
        "no_notice_claimed": True,
        "risk_factors": {
            "nature_and_extent": "recorded",
            "unauthorized_person": "recorded",
            "actual_acquisition_or_viewing": "unknown",
        },
        "awareness_events": [
            {
                "actor_id": "AGENT",
                "known_at": "2028-01-01T08:00:00Z" if future_agent else "2027-05-08T08:00:00Z",
                "original_ref": reference(awareness["source"]),
                "timestamp_field": "received_at",
            }
        ],
        "clock_started_at": "2027-05-09T08:00:00Z",
        "declared_training_max_notice_days": 60,
        "declared_contract_notice_hours": 24,
        "notice_policy_original": reference(policy["source"]),
        "contract_original": reference(contract["source"]),
        "upstream_notice_delivered_at": "2027-05-10T08:00:00Z",
        "initial_information_incomplete": True,
        "law_enforcement_delay_records": [
            {"kind": "ORAL", "identity": "UNVERIFIED", "specified_days": 90}
        ],
        "affected_individual_ids": [f"PERSON-{n:04d}" for n in range(affected_count)],
        "resident_ids_by_jurisdiction": {
            "STATE-A": [f"PERSON-{n:04d}" for n in range(affected_count)]
        },
        "individual_notice_content": {"description": "synthetic disclosure"},
        "substitute_posting_start_at": "2027-05-08T08:00:00Z",
        "substitute_posting_finish_at": "2027-08-05T08:00:00Z",
        "substitute_phone_record": None,
        "reporting_delegation": "NO_SEPARATE_CE_AUTHORITY_OR_REPORT",
    }
    add(
        "phi_ba",
        "legal_decision",
        "LEGAL-CASE",
        "2027-08-20T09:00:00Z",
        {
            **({"breach_case": case} if not no_cases else {}),
            "legal_role_decision": "TRAINING_ONLY",
            "actual_legal_applicability": "UNDETERMINED",
            "source_refs": refs(policy, contract, awareness),
        },
    )
    return values


def collected(tmp_path, sources):
    tmp_path.chmod(0o700)
    rows, context = ordinary_inputs(tmp_path, sources)
    for r in rows:
        r["retained_bytes"] = r["content"]
        r["content_type"] = "application/json"
        r["logical_family"], r["logical_system"] = r["source"]["system"].split(".", 1)
    return rows, context.simulated_at


@pytest.fixture(scope="module")
def ordinary_pair(tmp_path_factory):
    root = tmp_path_factory.mktemp("b09-company-before-two409")
    root.chmod(0o700)
    base = root / "source"
    base.mkdir(mode=0o700)
    sources = originals()
    store = CompanyStore(base)
    for system in sorted({r["source"]["system"] for r in sources}):
        store.register_system("NEUTRAL-COMPANY", "ALPHA", system, "SOURCE-OWNER")
    for r in sources:
        s = r["source"]
        store.append_version(
            s["company"],
            s["branch"],
            s["system"],
            s["record"],
            expected_version=s["version"] - 1,
            command_id="AUTHOR-" + r["artifact_id"],
            event_at=s["event_at"],
            available_at=s["available_at"],
            content=r["content"],
            provenance=s["provenance"],
        )
    store.register_system("NEUTRAL-COMPANY", "BETA", "prdconcern.simulated_inbox", "BETA-OWNER")
    store.append_version(
        "NEUTRAL-COMPANY",
        "BETA",
        "prdconcern.simulated_inbox",
        "UNUSED-BETA",
        expected_version=0,
        command_id="UNUSED-BETA",
        event_at="2027-01-01T00:00:00Z",
        available_at="2027-01-01T00:00:00Z",
        content=b'{"engineering_neutral_fixture":true}',
        provenance={"source_reference": "neutral-other-branch", "content_type": "application/json"},
    )
    db, manifest, review = base / "company.sqlite3", base / "MANIFEST.json", base / "REVIEW.json"
    write(manifest, {"schema": LIBRARY_MANIFEST_SCHEMA, "files": {"company.sqlite3": file_sha(db)}})
    write(
        review,
        {
            "schema": LIBRARY_REVIEW_SCHEMA,
            "verdict": LIBRARY_REVIEW_VERDICT,
            "source_quality_accepted_for_final_learner_audit": True,
            "library_pins": {"company.sqlite3": file_sha(db), "MANIFEST.json": file_sha(manifest)},
            "native_versions": len(sources) + 1,
            "engineering_neutral_fixture_not_actual_independent_review": True,
        },
    )
    accepted = AcceptedLibrary(
        db, file_sha(db), manifest, file_sha(manifest), review, file_sha(review), len(sources) + 1
    )
    routes = {
        "CLEAN": [
            BusinessRoute("NEUTRAL-COMPANY", "ALPHA", system, *system.split(".", 1))
            for system in sorted({r["source"]["system"] for r in sources})
        ],
        "MESSY": [
            BusinessRoute(
                "NEUTRAL-COMPANY",
                "BETA",
                "prdconcern.simulated_inbox",
                "prdconcern",
                "simulated_inbox",
            )
        ],
    }
    pair = FullScopePair.initialize(
        accepted=accepted,
        repository=REPO,
        program_pack=PACK,
        routes_by_mode=routes,
        destination=root / "pair",
        operator_id="COMPANY-OPERATOR",
        engineering_only=True,
    )
    before = native_rows(pair.world.database)
    room = pair.rooms["CLEAN"]
    records = room.acquire(
        systems=[r.system for r in routes["CLEAN"]],
        control_id="SH-INC-001",
        purpose="B09 exact neutral source examination",
    )
    assert len(records) == len(sources) and native_rows(pair.world.database) == before
    return pair, records, room.state()["simulated_at"]


def hist(ordinary_pair):
    _, records, clock = ordinary_pair
    return History(records, as_of=clock)


def test_company_precedes_two409_and_all26_are_exact_distinct_bounded_examinations(ordinary_pair):
    pair, records, as_of = ordinary_pair
    assert (
        json.loads((pair.world.root / "INITIALIZATION.json").read_bytes())[
            "audit_engagements_at_initialization"
        ]
        == 0
    )
    assert all(len(r.state()["tasks"]) == 409 for r in pair.rooms.values())
    output = examine(records, as_of=as_of, scratch_root=pair.root / "never-opened")
    assert len(output) == len(contracts()) == 26
    assert [v["task_id"] for v in output] == [t["task_id"] for t in task_plan()]
    for value in output:
        assert value["disposition"]["conclusion"] in {"LIMITATION", "FAIL"}
        assert value["result"]["professional_or_actual_source_applicability_accepted"] is False
        for prefix in ("EXACT-TASK-ATTRIBUTES", "EXACT-NATIVE-SUPPORT"):
            parts = [o for o in value["observations"] if o["id"].startswith(prefix)]
            assert {e["artifact_id"] for o in parts for e in o["evidence"]} == set(
                value["artifact_ids"]
            )
            assert all(len(o["evidence"]) <= 20 and len(o["id"]) <= 128 for o in parts)
            assert parts[0]["facts"]["citation_group"]["all_citation_part_ids"] == [
                o["id"] for o in parts
            ]
    for control in {t["control_id"] for t in task_plan()}:
        keys = [
            set(v["result"]["examined_attributes"]["task_kind_primary_attributes"])
            for v in output
            if v["result"]["examined_attributes"]["control_id"] == control
            and v["result"]["examined_attributes"]["exact_clause"]
            in {"TOD", "IMPLEMENTATION", "TOE"}
        ]
        assert len(keys) == 3 and not keys[0] == keys[1] == keys[2]


def test_original_probe_counts_and_late_escalation_not_restarted_at_ack(ordinary_pair):
    out = response_history(hist(ordinary_pair))
    assert [p["calculated_error_percent"] for p in out["monitoring_populations"]] == [100, 0]
    assert all(
        p["reported_total_agrees"] and p["reported_error_agrees"]
        for p in out["monitoring_populations"]
    )
    assert out["escalation_occurrences"][-1]["delivered_by_local_due"] is False
    assert out["escalation_occurrences"][-1]["delivery_interval"]["calculated_minutes"] == 15
    assert out["ticket_occurrences"][-1]["calculated_local_escalation_due_at"].startswith(
        "2027-05-02T09:10:00"
    )
    assert any(p["facet"] == "ESCALATION_DELIVERY" for p in out["exceptions"])


def test_recovery_actual_original_probes_checkpoint_and_review_do_not_establish_cause(
    ordinary_pair,
):
    out = response_history(hist(ordinary_pair))
    assert out["recovery_occurrences"][0]["supported_successful_probe_count"] is None
    last = out["recovery_occurrences"][-1]
    assert (
        last["supported_successful_probe_count"] == 2
        and last["reported_success_count_agrees"] is True
    )
    assert (
        last["checkpoint_age"]["calculated_minutes"] == 2
        and last["reported_checkpoint_age_agrees"] is True
    )
    assert (
        last["local_probe_success_requirement_met"] is True
        and last["checkpoint_within_local_limit"] is True
    )
    review = out["postincident_reviews"][0]
    assert review["source_restoration_interval"]["calculated_minutes"] == 60
    assert review["restoration_claim_agrees"] is True
    assert review["independent_cause_or_qualified_second_line_accepted"] is False


def test_wrong_validation_then_corrected_replay_and_unsupported_finding_closure(ordinary_pair):
    out = corrective_history(hist(ordinary_pair))
    assert [
        p["reported_elapsed_agrees"] for p in out["independent_selected_action_validations"]
    ] == [False, True]
    assert all(
        p["independent_replay_interval"]["calculated_minutes"] == 3
        for p in out["independent_selected_action_validations"]
    )
    assert out["company_closure_discrepancies"][0]["company_closure_claim_supported"] is False
    assert out["technical_retry_or_closed_ticket_does_not_close_enterprise_finding"] is True


def test_attempted_access_is_security_intake_without_automatic_hipaa_breach(ordinary_pair):
    out = attempted_intake(hist(ordinary_pair))
    intake = next(
        x
        for x in out["selected_attempt_intake_occurrences"]
        if x["source"]["record"] == "ATTEMPT-INBOX"
    )
    assert intake["all_selected_original_decisions_deny"] is True
    assert intake["local_attempt_intake_supported"] is True
    assert intake["security_event_without_actual_phi_not_assumed_hipaa_breach"] is True
    assert out["complete_incident_and_dismissed_case_census_established"] is False


def test_exact_agent_discovery_shorter_contract_clock_false_no_notice_and_500_thresholds(
    ordinary_pair,
):
    out = breach_and_notice(hist(ordinary_pair))
    decision = out["explicit_breach_case_examinations"][0]
    assert decision["omitted_examined_risk_factors"] == ["mitigation"]
    assert decision["encryption_claim_has_exact_support_witnesses"] is False
    clock = out["separate_discovery_and_notice_clocks"][0]
    assert clock["earliest_supported_discovery_at"].startswith("2027-05-08T08:00:00")
    assert clock["clock_restarted_after_original_discovery"] is True
    assert clock["earliest_declared_due_at"].startswith("2027-05-09T08:00:00")
    assert clock["upstream_delivery_within_declared_limit"] is False
    assert clock["law_enforcement_authority_and_valid_oral_written_delay_accepted"] is False
    assert (
        clock["original_oral_written_delay_attribute_examinations"][0][
            "oral_duration_exceeds_declared_policy_ceiling"
        ]
        is True
    )
    assert (
        clock["original_oral_written_delay_attribute_examinations"][0]["delay_original_status"]
        == "EXACT_DELAY_REQUEST_ORIGINAL_ABSENT"
    )
    population = out["separate_individual_jurisdiction_and_total_population_examinations"][0]
    assert population["recomputed_total_individuals"] == 500
    assert population["authored_more_than_500_media_training_threshold"]["STATE-A"] is False
    assert population["authored_500_or_more_total_training_threshold"] is True
    assert population["missing_declared_notice_content_fields"] == ["data_types", "help_contact"]
    assert population["meets_authored_90_day_posting_attribute"] is False
    assert (
        population["upstream_associate_notice_separate_from_delegated_individual_media_reporting"]
        is True
    )
    assert {p["facet"] for p in out["exceptions"]} >= {
        "UNSUBSTANTIATED_NO_NOTICE",
        "NOTICE_CLOCK",
        "AFFECTED_POPULATION_OR_NOTICE_ATTRIBUTES",
    }


def test_description_compares_original_incident_census_to_claimed_disclosure(ordinary_pair):
    out = description_population(hist(ordinary_pair))
    assert out["explicit_description_assertion_comparisons"][0][
        "omitted_independent_incident_ids"
    ] == ["INC-NEUTRAL"]
    assert out["change_vendor_disclosure_complete_denominator_established"] is False


@pytest.mark.parametrize(
    "variant",
    [
        "future_replay",
        "self_validation",
        "future_agent",
        "future_occurrence",
        "late_contract",
        "affected_count",
    ],
)
def test_fully_authored_then_ordinary_collected_temporal_role_population_negatives(
    tmp_path, variant
):
    records, as_of = collected(
        tmp_path, originals(**{variant: 501 if variant == "affected_count" else True})
    )
    history = History(records, as_of=as_of)
    if variant in {"future_replay", "self_validation"}:
        result = corrective_history(history)
        last = result["independent_selected_action_validations"][-1]
        if variant == "future_replay":
            assert last["independent_replay_interval"]["calculated_minutes"] is None
            assert (
                last["independent_replay_interval"]["native_occurrence_chronology_supported"]
                is False
            )
        else:
            assert last["distinct_named_action_owner_replayer_and_validator"] is False
        assert result["exceptions"]
    else:
        result = breach_and_notice(history)
        clock = result["separate_discovery_and_notice_clocks"][0]
        if variant in {"future_agent", "future_occurrence"}:
            assert (
                clock["earliest_supported_discovery_at"] is None
                and clock["earliest_declared_due_at"] is None
            )
            assert clock["declared_training_ceiling_supported"] is False
            notice = next(
                v
                for v in examine(records, as_of=as_of, scratch_root=tmp_path / "never-opened")
                if v["task_id"] == "TASK-SH-INC-001-corporate-ACTION-H-NOTICE-CLOCK"
            )
            assert notice["result"]["selected_native_population_before_selection"] == []
            assert notice["result"]["required_task_attribute_population_available"] is False
        elif variant == "late_contract":
            assert clock["contract_original_status"] == "ORIGINAL_UNAVAILABLE_AT_COMPANY_OCCURRENCE"
            assert clock["declared_contract_period_supported"] is False
            assert clock["earliest_declared_due_at"].startswith("2027-07-07T08:00:00")
        else:
            population = result[
                "separate_individual_jurisdiction_and_total_population_examinations"
            ][0]
            assert population["recomputed_total_individuals"] == 501
            assert population["authored_more_than_500_media_training_threshold"]["STATE-A"] is True


def test_missing_breach_cases_stay_exactly_unperformed_despite_role_contract_witnesses(
    ordinary_pair,
):
    pair, records, as_of = ordinary_pair
    selected = [
        r
        for r in records
        if r["logical_family"] in {"phi_ba", "supplementalops"}
        and r["source"]["record"] != "LEGAL-CASE"
    ]
    output = examine(selected, as_of=as_of, scratch_root=pair.root / "never-opened")
    checks = [
        v
        for v in output
        if v["result"]["examined_attributes"]["exact_clause"].startswith("CHECK-HIPAA:")
    ]
    assert len(checks) == 4
    for value in checks:
        assert value["result"]["required_task_attribute_population_available"] is False
        assert value["result"]["selected_native_population_before_selection"] == []
        assert value["disposition"]["conclusion"] == "LIMITATION"
        assert value["observations"][0]["status"] == "SUPPORT_UNAVAILABLE"


@pytest.mark.parametrize(
    "change",
    ["wrong_role", "boolean_version", "boolean_length", "future_real_collection", "changed_bytes"],
)
def test_actual_retained_custody_tampering_refused(ordinary_pair, change):
    _, records, as_of = ordinary_pair
    changed = copy.deepcopy(records)
    if change == "wrong_role":
        changed[0]["logical_system"] = "policy_note"
    elif change == "boolean_version":
        changed[0]["source"]["version"] = True
    elif change == "boolean_length":
        changed[0]["receipt"]["content_bytes"] = True
    elif change == "future_real_collection":
        changed[0]["receipt"]["collected_at"] = "2100-01-01T00:00:00Z"
    else:
        changed[0]["retained_bytes"] += b" "
    with pytest.raises(ProcedureError):
        History(changed, as_of=as_of)


def test_cached_document_is_not_authority_and_missing_replay_is_not_reconstructed(ordinary_pair):
    pair, records, as_of = ordinary_pair
    changed = copy.deepcopy(records)
    for r in changed:
        r["document"] = {"finding_closed": True, "PASS": True}
    assert examine(changed, as_of=as_of, scratch_root=pair.root / "inert") == examine(
        records, as_of=as_of, scratch_root=pair.root / "inert"
    )
    missing = History([r for r in records if r["logical_system"] != "dispatch_replay"], as_of=as_of)
    assert (
        corrective_history(missing)["independent_selected_action_validations"][-1][
            "replay_original"
        ]
        is None
    )
    assert (
        corrective_history(missing)["independent_selected_action_validations"][-1][
            "independent_replay_interval"
        ]["calculated_minutes"]
        is None
    )


def test_exact26_author_neutral_gate_appends_actual_fieldwork_without_other383_task_credit(
    ordinary_pair,
):
    pair, records, _ = ordinary_pair
    room = pair.rooms["CLEAN"]
    before = native_rows(pair.world.database)
    method = REPO / "enterprise/audit_suite/source_incident_complaints_methods.py"
    path = pair.root / "NEUTRAL-B09-REVIEW.json"
    write(
        path,
        {
            "schema": GENERAL_METHOD_SCHEMA,
            "verdict": GENERAL_METHOD_VERDICT,
            "source_execution_authorized": True,
            "method_module_sha256": file_sha(method),
            "dependency_module_sha256": {
                name: file_sha(method.with_name(name))
                for name in (
                    "collected_incident_history.py",
                    "company_store.py",
                    "fresh_sec003_procedure.py",
                    "source_library_audit.py",
                )
            },
            "method_callable": examine.__module__ + "." + examine.__qualname__,
            "selected_task_ids": list(contracts()),
            "task_contracts": contracts(),
            "neutral_author_fixture_not_actual_independent_acceptance": True,
        },
    )
    links = room.append_reviewed_batch(
        batch="neutral-B09", review=PinnedReview(path, file_sha(path)), rows=records, method=examine
    )
    state = room.state()
    assert len(links) == len(state["workpapers"]) == len(state["selections"]) == 26
    assert len(state["sample_executions"]) == sum(len(x["sample_execution_ids"]) for x in links)
    assert {x["task_id"] for x in state["sample_executions"]} == set(contracts())
    assert all(x["automatic_testing_credit"] is False for x in state["sample_executions"])
    assert native_rows(pair.world.database) == before and not state["reviews"]
    assert all(
        t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
        for t in state["tasks"]
        if t["id"] not in contracts()
    )
    assert not pair.rooms["MESSY"].state()["workpapers"]
