"""Owned neutral company originals genuinely precede two fresh409-task workrooms."""

import copy
import json
from pathlib import Path

import pytest
from test_collected_byte_recovery_method import ordinary_inputs, row

from enterprise.audit_suite.collected_byte_recovery_method import reference
from enterprise.audit_suite.company_store import CompanyStore, _time
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.full_scope_company_pair import (
    GENERAL_METHOD_SCHEMA,
    GENERAL_METHOD_VERDICT,
    FullScopePair,
    PinnedReview,
)
from enterprise.audit_suite.persistent_company_journey import native_rows, write
from enterprise.audit_suite.source_governance_methods import (
    History,
    _addressable,
    _communications,
    _conflicts,
    _ethics,
    _fraud,
    _governing_decisions,
    _material_changes,
    _procedure_due,
    _retention,
    _risk,
    _threshold_routes,
    contracts,
    examine,
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
pytestmark = pytest.mark.skipif(not PACK.is_file(), reason="Exact private409 pack absent")


def originals(
    *,
    future_calendar=False,
    wrong_configuration=False,
    future_receipt=False,
    self_recusal=False,
    omitted_audience=False,
    boolean_count=False,
):
    records = []

    def add(system, record, at, body, *, version=1):
        r = row(system, record, at, {"engineering_neutral_fixture": True, **body}, version=version)
        records.append(r)
        return r

    def ref(r):
        return reference(r["source"])

    def deps(*rs):
        return [ref(r) for r in rs]

    policy = add(
        "supplementalops.policy_document",
        "POLICY",
        "2027-01-01T09:00:00Z",
        {
            "policy_text": "Two-person review and preservation",
            "effective_at": "2027-01-01T09:00:00Z",
        },
    )
    motion = add(
        "govapp.appetite_motion",
        "ENVELOPE",
        "2027-01-02T09:00:00Z",
        {
            "internal_marker_rpo_minutes_max": 5,
            "internal_marker_rto_minutes_max": 30,
            "unreviewed_boise_key_gate_bypass_tolerance": 0,
            "customer_service_commitment": "NONE",
        },
    )
    votes = []
    for i, vote in enumerate(("SUPPORT", "DISSENT")):
        votes.append(
            add(
                "govapp.board_member_action",
                "DIR-" + str(i),
                f"2027-01-03T09:0{i}:00Z",
                {
                    "actor_id": "DIR-" + str(i),
                    "motion_sha256": motion["source"]["sha256"],
                    "vote": vote,
                },
            )
        )
    board = add(
        "govapp.board_decision",
        "BOARD",
        "2027-01-04T09:00:00Z",
        {
            "accepted_motion_sha256": motion["source"]["sha256"],
            "member_actions": [
                {
                    "action_sha256": v["source"]["sha256"],
                    "director_id": v["source"]["record"],
                    "vote": json.loads(v["content"])["vote"],
                    "event_at": v["source"]["event_at"],
                }
                for v in votes
            ],
            "support_count": True if boolean_count else 1,
            "dissent_count": 1,
            "effective_at": "2027-01-04T09:00:00Z",
            "expires_at": "2027-12-31T23:59:59Z",
            "reserved_boundary_route": "COLLECTIVE_BOARD_FOR_MATERIAL_DEPARTURE",
        },
    )
    add(
        "govapp.ceo_delegation",
        "DELEGATE",
        "2027-01-05T09:00:00Z",
        {
            "board_decision_sha256": board["source"]["sha256"],
            "actor_id": "CEO",
            "scope": "LOCAL_ONLY",
            "security_official_designation": "NOT_MADE",
            "waiver_of_board_envelope": False,
        },
    )
    add(
        "govapp.control_mapping",
        "MAPPING",
        "2027-01-06T09:00:00Z",
        {
            "source_decision_sha256": board["source"]["sha256"],
            "accountable_roles": {"technical_owner": "TECH", "security_challenge": "SECURITY"},
        },
    )
    waiver = add(
        "govapp.waiver_request",
        "WAIVER",
        "2027-06-01T09:00:00Z",
        {
            "board_decision_sha256": board["source"]["sha256"],
            "actual_key_bypass_open": True,
            "claimed_selected_retest_restore_minutes": 20,
            "claimed_selected_retest_replay_gap_minutes": 2,
        },
    )
    challenge = add(
        "govapp.security_challenge",
        "CHALLENGE",
        "2027-06-02T09:00:00Z",
        {
            "board_decision_sha256": board["source"]["sha256"],
            "waiver_request_sha256": waiver["source"]["sha256"],
        },
    )
    add(
        "govapp.ceo_disposition",
        "DISPOSITION",
        "2027-06-03T09:00:00Z",
        {
            "board_decision_sha256": board["source"]["sha256"],
            "waiver_request_sha256": waiver["source"]["sha256"],
            "security_challenge_sha256": challenge["source"]["sha256"],
            "risk_acceptance": False,
            "issue_closed": False,
            "requested_body": "BOARD",
        },
    )
    assessment = add(
        "risk-history.risk_assessments",
        "RISK",
        "2027-02-01T09:00:00Z",
        {
            "risks": [
                {
                    "id": "SUPPLIER",
                    "input_id": "EXT",
                    "likelihood": 2,
                    "impact": 4,
                    "projected_likelihood": 1,
                    "projected_impact": 3,
                    "inherent_local_score": 9,
                    "projected_residual_local_score": 3,
                    "management_owner_id": "OWNER",
                    "assumption_rationale": "Hypothesis, not observed supplier cause",
                    "risk_acceptance": "NONE",
                }
            ]
        },
    )
    add(
        "risk-history.risk_reconciliation",
        "CENSUS",
        "2027-02-02T09:00:00Z",
        {
            "declared_input_ids": ["EXT", "INT"],
            "imported_input_ids": ["EXT"],
            "missing_declared_input_ids": [],
            "previous_events": deps(assessment),
        },
    )
    for i in range(1, 23):
        candidate = add(
            "addressabledocket.addressable_candidate",
            f"SPEC-{i}",
            "2027-03-01T09:00:00Z",
            {"source_locator": f"LOCAL-SPEC-{i}", "docket_state": "PENDING_AT_THIS_DATE"},
        )
        decision = add(
            "supplementalops.risk_decision",
            f"DECISION-{i}",
            "2027-03-02T09:00:00Z",
            {
                "specification": f"LOCAL-SPEC-{i}",
                "assessment": {
                    k: "Named local environmental basis"
                    for k in (
                        "size_complexity_capability",
                        "infrastructure",
                        "cost",
                        "probability_and_criticality",
                    )
                },
                "decision": "IMPLEMENT_IN_LOCAL_MODEL",
                "reasoned_treatment": "Local setting only",
                "planned_configuration_record": f"security_configuration/SETTING-{i}/1",
                "native_dependencies": deps(candidate),
            },
        )
        add(
            "supplementalops.security_configuration",
            f"SETTING-{i}",
            "2027-03-03T09:00:00Z",
            {
                "specification": f"LOCAL-SPEC-{i}",
                "implementation_decision_original": f"risk_decision/DECISION-{i}/1",
                "observed_values": {"local_setting": True},
                "native_dependencies": deps(policy if i == 1 and wrong_configuration else decision),
            },
        )
    procedure = add(
        "supplementalops.procedure_document",
        "PROCEDURE",
        "2027-08-01T09:00:00Z",
        {
            "owner": "OPERATOR",
            "performer": "OPERATOR",
            "frequency_and_trigger": "Declared monthly due calendar",
            "native_dependencies": deps(policy),
        },
    )
    cal = add(
        "supplementalops.procedure_calendar",
        "CALENDAR",
        "2027-08-02T09:00:00Z",
        {
            "scheduled": [
                {"trigger_at": "2027-09-01T09:00:00Z", "due_at": "2027-09-03T17:00:00Z"},
                {"trigger_at": "2027-10-01T09:00:00Z", "due_at": "2027-10-03T17:00:00Z"},
            ],
            "native_dependencies": deps(procedure),
        },
    )
    if future_calendar:
        cal["source"]["available_at"] = _time("2027-10-04T09:00:00Z")
    add(
        "supplementalops.procedure_operation",
        "SEPTEMBER",
        "2027-09-04T09:00:00Z",
        {
            "due_at": "2027-09-03T17:00:00Z",
            "factual_result": "Successful but late",
            "native_dependencies": deps(cal),
        },
    )
    add(
        "supplementalops.procedure_operation",
        "OCTOBER",
        "2027-10-02T09:00:00Z",
        {
            "due_at": "2027-10-03T17:00:00Z",
            "factual_result": "On time",
            "native_dependencies": deps(cal),
        },
    )
    directory = add(
        "supplementalops.communication_directory",
        "DIRECTORY",
        "2027-08-03T09:00:00Z",
        {
            "required_internal_recipients": ["OWNER", "RECORDS"],
            "external_concern_address": "correct.invalid",
        },
    )
    add(
        "supplementalops.communication_event",
        "DELIVERY",
        "2027-08-04T09:00:00Z",
        {
            "required_recipients": ["OWNER"] if omitted_audience else ["OWNER", "RECORDS"],
            "delivery_receipts": [
                {
                    "recipient": "OWNER",
                    "received_at": "2028-01-01T09:00:00Z"
                    if future_receipt
                    else "2027-08-04T08:00:00Z",
                }
            ],
            "external_template_contact": "retired.invalid",
            "native_dependencies": deps(directory),
        },
    )
    revised = add(
        "supplementalops.communication_directory",
        "DIRECTORY",
        "2027-11-01T09:00:00Z",
        {
            "required_internal_recipients": ["OWNER", "RECORDS", "PRIVACY"],
            "external_concern_address": "new.invalid",
            "risk_review_due_at": "2027-11-02T09:00:00Z",
            "native_dependencies": deps(directory),
        },
        version=2,
    )
    add(
        "risk-history.risk_followup",
        "REVISION-REVIEW",
        "2027-11-03T09:00:00Z",
        {"reason": "No local procedure change needed", "native_dependencies": deps(revised)},
    )
    add(
        "supplementalops.retention_register",
        "RETENTION",
        "2027-11-04T09:00:00Z",
        {
            "classes": {"SECURITY_POLICY_PROCEDURE": "Later-of six years"},
            "retrievable_original_refs": ["policy_document/POLICY/1"],
            "native_dependencies": deps(policy),
            "required_records": [
                {
                    "id": "POLICY-v1",
                    "class": "SECURITY_POLICY_PROCEDURE",
                    "created_date": "2027-01-01",
                    "last_in_effect_date": "2027-11-01",
                    "current_effective": False,
                    "hold": False,
                    "requested_date": "2028-01-01",
                    "minimum_retain_through": "2033-11-01",
                    "decision": "DENY",
                    "actual_deletion": False,
                },
                {
                    "id": "PROCEDURE",
                    "created_date": "2027-08-01",
                    "last_in_effect_date": None,
                    "current_effective": True,
                    "hold": False,
                    "requested_date": "2038-01-01",
                    "minimum_retain_through": "2033-08-01",
                    "decision": "DENY",
                    "actual_deletion": False,
                },
            ],
        },
    )
    question = add(
        "govoversight.conflict_questionnaire",
        "QUESTION",
        "2027-11-05T09:00:00Z",
        {"case_id": "CASE", "actor_id": "SUBJECT", "detail": {"self_report_only": True}},
    )
    add(
        "govoversight.eligibility_review",
        "REVIEW",
        "2027-11-06T09:00:00Z",
        {
            "case_id": "CASE",
            "detail": {
                "subject_recused_from_own_review": "SUBJECT",
                "review_contacts": ["SUBJECT"] if self_recusal else ["OTHER"],
            },
            "native_dependencies": deps(question),
        },
    )
    intake = add(
        "eth003.report_intake",
        "REPORT",
        "2027-09-10T09:00:00Z",
        {"case_id": "ETH", "actor": "HR", "case_existence_sent_to_implicated_line": True},
    )
    triage = add(
        "eth003.separate_triage",
        "TRIAGE",
        "2027-09-11T09:00:00Z",
        {
            "case_id": "ETH",
            "actor": "RISK",
            "investigation_complete": False,
            "previous_source": ref(intake),
        },
    )
    add(
        "eth003.case_state",
        "PENDING",
        "2027-09-12T09:00:00Z",
        {
            "case_id": "ETH",
            "actor": "RISK",
            "committee_disposition": "PENDING",
            "previous_source": ref(triage),
        },
    )
    facts = add(
        "supplementalops.workforce_case",
        "FACTS",
        "2027-09-15T09:00:00Z",
        {"substantiated_facts": "Denied unapproved action; reporter not culpable"},
    )
    sanction = add(
        "supplementalops.workforce_case",
        "SANCTION",
        "2027-09-28T09:00:00Z",
        {
            "subject": "OPERATOR",
            "sanction": "Coaching",
            "decision_target": "2027-09-19T17:00:00Z",
            "reporter_adverse_action": False,
            "considerations": {
                k: "Recorded reason"
                for k in ("intent", "impact", "proportionality", "protected_reporting")
            },
            "native_dependencies": deps(facts),
        },
    )
    add(
        "supplementalops.responsibility_feedback",
        "FEEDBACK",
        "2027-10-01T09:00:00Z",
        {
            "discussion": {"responsibility": "Seek approval"},
            "reward_and_pressure_review": "No reward for bypass",
            "native_dependencies": deps(sanction),
        },
    )
    fraud = add(
        "eth004.conflict_intake",
        "FRAUD",
        "2027-05-01T09:00:00Z",
        {"indicator_id": "INDICATOR", "opportunity_id": "OPPORTUNITY", "indicator_included": False},
    )
    hold = add(
        "eth004.conflict_gate",
        "HOLD",
        "2027-05-02T09:00:00Z",
        {
            "indicator_id": "INDICATOR",
            "opportunity_id": "OPPORTUNITY",
            "opportunity_held": True,
            "draft_recommendation_active": False,
            "previous_source": ref(fraud),
        },
    )
    add(
        "eth004.risk_review",
        "FRAUD-REVIEW",
        "2027-05-03T09:00:00Z",
        {
            "indicator_id": "INDICATOR",
            "opportunity_id": "OPPORTUNITY",
            "risk_themes": ["RELATED_PARTY", "CONTROL_OVERRIDE", "DISHONEST_REPORTING"],
            "substantiated_fraud": False,
            "previous_source": ref(hold),
        },
    )
    message = add(
        "legaloriginals.legal_inbound_message",
        "CONTRACT-QUESTION",
        "2027-10-10T09:00:00Z",
        {"received_at": "2027-10-10T09:00:00Z", "sender_role": "Fictional contract manager"},
    )
    add(
        "legint.legal_matter_classification",
        "LEGAL-CLASS",
        "2027-10-11T09:00:00Z",
        {
            "classification": "CONTRACTUAL_CUSTOMER_INSTRUCTION",
            "official_regulator_notice": False,
            "source_ref": ref(message),
        },
    )
    add(
        "legint.legal_response_exercise",
        "EXERCISE",
        "2027-10-12T09:00:00Z",
        {
            "exercise_only": True,
            "urgent_access_path_exercised": True,
            "available_company_copy_ids": ["QUESTION"],
            "source_ref": ref(message),
        },
    )
    return records


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
    root = tmp_path_factory.mktemp("b07-company-before-two409")
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
        control_id="SH-ERM-001",
        purpose="B07 exact neutral source examination",
    )
    assert len(records) == len(sources) and native_rows(pair.world.database) == before
    return pair, records, room.state()["simulated_at"]


def hist(ordinary_pair):
    _, records, clock = ordinary_pair
    return History(records, clock)


def test_owned_company_before_two409_and_exact_distinct62_tasks(ordinary_pair):
    pair, records, at = ordinary_pair
    assert (
        json.loads((pair.world.root / "INITIALIZATION.json").read_bytes())[
            "audit_engagements_at_initialization"
        ]
        == 0
    )
    assert all(len(r.state()["tasks"]) == 409 for r in pair.rooms.values())
    values = examine(records, as_of=at, scratch_root=pair.root / "never-opened")
    assert len(values) == len(contracts()) == 62
    assert [v["task_id"] for v in values] == [t["task_id"] for t in task_plan()]
    for control in {t["control_id"] for t in task_plan()}:
        primary = [
            v["result"]["task_specific_primary_attributes"]["primary_attribute"]
            for v in values
            if v["result"]["task_specific_primary_attributes"]["control_id"] == control
            and v["result"]["task_specific_primary_attributes"]["task_kind"]
            in {"TOD", "IMPLEMENTATION", "TOE"}
        ]
        assert len(primary) == len(set(primary)) == 3
    for v in values:
        assert len({o["id"] for o in v["observations"]}) == len(v["observations"])
        assert v["disposition"]["conclusion"] in {"LIMITATION", "FAIL"}
        assert not v["result"]["professional_or_enterprise_acceptance_asserted"]
        for o in v["observations"]:
            assert 1 <= len(o["evidence"]) <= 20 and len(o["id"]) <= 128
            if "aggregate_facts" in o["facts"]:
                parts = o["facts"]["all_citation_part_ids"]
                assert set(parts) <= {x["id"] for x in v["observations"]}
    assert not (pair.root / "never-opened").exists()


def test_risk_arithmetic_and_declared_input_omission_preserve_false_company_claim(ordinary_pair):
    out = _risk(hist(ordinary_pair))
    risks = next(o["facts"]["native_scenarios"] for o in out if "native_scenarios" in o["facts"])
    assert risks[0]["recomputed_inherent_local_score"] == 8
    assert not risks[0]["score_matches"]
    reconciliation = next(o["facts"] for o in out if "recomputed_missing_inputs" in o["facts"])
    assert reconciliation["recomputed_missing_inputs"] == ["INT"]
    assert reconciliation["reported_missing_inputs"] == []


def test_individual_vote_census_dissent_and_reserved_bypass_survive_numeric_retest(ordinary_pair):
    votes = _governing_decisions(hist(ordinary_pair))[0]["facts"]
    assert votes["distinct_actual_member_actions"] == 2
    assert votes["recomputed_votes"] == {"SUPPORT": 1, "DISSENT": 1}
    assert votes["recorded_vote_counts_match_collected_individual_actions"]
    out = _threshold_routes(hist(ordinary_pair))
    assert all(o["facts"]["unreviewed_key_bypass_exceeds_zero_tolerance"] for o in out)
    assert all(
        not o["facts"]["numeric_retest_closes_independent_key_bypass_or_capacity_issue"]
        for o in out
    )
    disposition = next(o["facts"] for o in out if o["facts"]["requested_body"] == "BOARD")
    assert disposition["elapsed_hours_from_selected_request"] == 48
    assert disposition["challenge_bound_same_exact_request"]
    assert not disposition["actual_accepted_residual_risk_or_collective_disposition"]


def test_declared_due_census_binds_calendar_and_due_without_trigger_ids(ordinary_pair):
    out = _procedure_due(hist(ordinary_pair))
    due = [o["facts"] for o in out if "declared_due_occurrence" in o["facts"]]
    assert [d["missing_or_late_at_due"] for d in due] == [True, False]
    assert all(
        d["actual_selected_operation_versions"][0]["exact_calendar_and_due_match"] for d in due
    )
    assert all(not d["later_success_cures_prior_missed_interval"] for d in due)


def test_retention_later_of_current_hold_and_actual_superseded_bytes(ordinary_pair):
    out = _retention(hist(ordinary_pair))[0]["facts"]
    assert out["exact_retrieval_population"][0]["same_original_explicit_native_dependency"]
    dates = out["recomputed_required_record_dates"]
    assert dates[0]["recomputed_six_calendar_year_later_of_floor"].startswith("2033-11-01")
    assert dates[1]["current_effective_without_end_held"]
    assert all(d["computed_local_disposition"] == "DENY" for d in dates)
    assert not out["actual_disposition_operation_executed_by_method"]


def test_all22_exact_candidate_decision_configuration_chains(ordinary_pair):
    out = _addressable(hist(ordinary_pair))
    chains = [o["facts"] for o in out if "selected_configuration_chain" in o["facts"]]
    assert len(chains) == 22
    assert all(c["exact_candidate_native_pointer_present"] for c in chains)
    assert all(c["selected_configuration_chain"][0]["exact_typed_prior_decision"] for c in chains)
    assert all(c["selected_configuration_chain"][0]["exact_planned_setting"] for c in chains)
    assert not any(c["legal_equivalence_or_actual_hipaa_environment_accepted"] for c in chains)


def test_recusal_and_material_change_exact_followup_deadline(ordinary_pair):
    out = _conflicts(hist(ordinary_pair))[0]["facts"]
    assert out["subject_excluded_from_named_review"]
    assert out["same_exact_review_case"]
    changes = _material_changes(hist(ordinary_pair))[0]
    assert changes["status"] == "EXCEPTION_RECORDED"
    assert (
        changes["facts"]["exact_causally_linked_followups"][0]["within_explicit_review_due"]
        is False
    )


def test_policy_actual_audience_contact_sanction_delay_and_fraud_gate(ordinary_pair):
    communication = _communications(hist(ordinary_pair))[0]["facts"]
    assert communication["missing_actual_receipts"] == ["RECORDS"]
    assert communication["template_contact_matches_effective_directory"] is False
    ethics = _ethics(hist(ordinary_pair))
    assert any(o["facts"].get("case_existence_sent_to_implicated_line") is True for o in ethics)
    sanction = next(o["facts"] for o in ethics if o["facts"].get("recorded_sanction"))
    assert sanction["exact_substantiated_facts_original"]
    assert sanction["decision_late_against_original_target"]
    fraud = _fraud(hist(ordinary_pair))
    assert any(o["status"] == "EXCEPTION_RECORDED" for o in fraud)
    assert (
        next(o["facts"] for o in fraud if o["facts"]["declared_non_intrusion_risk_themes"])[
            "missing_override_reporting_related_party_themes"
        ]
        == []
    )


@pytest.mark.parametrize(
    "variant",
    [
        "future_calendar",
        "wrong_configuration",
        "future_receipt",
        "self_recusal",
        "omitted_audience",
        "boolean_count",
    ],
)
def test_fully_authored_before_ordinary_collection_negative(tmp_path, variant):
    sources = originals(**{variant: True})
    required = {
        "future_calendar": {"CALENDAR", "SEPTEMBER", "OCTOBER"},
        "wrong_configuration": {"SPEC-1", "DECISION-1", "SETTING-1", "POLICY"},
        "future_receipt": {"DIRECTORY", "DELIVERY"},
        "self_recusal": {"QUESTION", "REVIEW"},
        "omitted_audience": {"DIRECTORY", "DELIVERY"},
        "boolean_count": {"BOARD", "ENVELOPE", "DIR-0", "DIR-1"},
    }[variant]
    sources = [r for r in sources if r["source"]["record"] in required]
    records, at = collected(tmp_path, sources)
    history = History(records, at)
    if variant == "future_calendar":
        out = _procedure_due(history)
        assert all(o["facts"]["missing_or_late_at_due"] for o in out)
        assert not any(o["facts"]["calendar_available_at_trigger"] for o in out)
    elif variant == "wrong_configuration":
        chain = next(
            o["facts"]
            for o in _addressable(history)
            if o["facts"].get("specification") == "LOCAL-SPEC-1"
        )
        assert chain["selected_configuration_chain"][0]["exact_typed_prior_decision"] is False
    elif variant == "future_receipt":
        c = _communications(history)[0]["facts"]
        assert c["missing_actual_receipts"] == ["OWNER", "RECORDS"]
    elif variant == "self_recusal":
        assert _conflicts(history)[0]["facts"]["subject_excluded_from_named_review"] is False
    elif variant == "omitted_audience":
        c = _communications(history)[0]["facts"]
        assert c["declared_required_audience_omissions"] == ["RECORDS"]
    elif variant == "boolean_count":
        with pytest.raises(ProcedureError, match="vote count"):
            _governing_decisions(history)


@pytest.mark.parametrize("tamper", ["bytes", "version", "receipt_size", "native_role"])
def test_actual_custody_and_physical_role_remain_strict(ordinary_pair, tamper):
    _, records, at = ordinary_pair
    values = copy.deepcopy(records)
    if tamper == "bytes":
        values[0]["retained_bytes"] += b" "
    elif tamper == "version":
        values[0]["source"]["version"] = True
    elif tamper == "receipt_size":
        values[0]["receipt"]["content_bytes"] = True
    else:
        values[0]["logical_family"] = "eth004"
    with pytest.raises(ProcedureError):
        History(values, at)


def test_cached_document_not_authority_and_missing_pointer_never_aliased(ordinary_pair):
    _, records, at = ordinary_pair
    values = copy.deepcopy(records)
    for r in values:
        r["document"] = {"support_count": 99}
    assert _governing_decisions(History(values, at))[0]["facts"]["recomputed_votes"] == {
        "SUPPORT": 1,
        "DISSENT": 1,
    }
    candidates = [
        r for r in records if r["source"]["system"] != "addressabledocket.addressable_candidate"
    ]
    out = _addressable(History(candidates, at))
    assert out[0]["facts"]["distinct_candidate_original_count"] == 0
    assert out[0]["status"] == "SUPPORT_UNAVAILABLE"


def test_exact62_reviewed_neutral_writer_preserves_other347_and_company_history(ordinary_pair):
    pair, records, _ = ordinary_pair
    room = pair.rooms["CLEAN"]
    before = native_rows(pair.world.database)
    module = REPO / "enterprise/audit_suite/source_governance_methods.py"
    path = pair.root / "NEUTRAL-B07-REVIEW.json"
    write(
        path,
        {
            "schema": GENERAL_METHOD_SCHEMA,
            "verdict": GENERAL_METHOD_VERDICT,
            "source_execution_authorized": True,
            "method_module_sha256": file_sha(module),
            "dependency_module_sha256": {
                name: file_sha(module.with_name(name))
                for name in ("company_store.py", "fresh_sec003_procedure.py")
            },
            "method_callable": examine.__module__ + "." + examine.__qualname__,
            "selected_task_ids": list(contracts()),
            "task_contracts": contracts(),
            "neutral_author_fixture_not_actual_independent_acceptance": True,
        },
    )
    links = room.append_reviewed_batch(
        batch="neutral-B07", review=PinnedReview(path, file_sha(path)), rows=records, method=examine
    )
    state = room.state()
    assert len(links) == len(state["workpapers"]) == len(state["selections"]) == 62
    assert native_rows(pair.world.database) == before
    assert not state["reviews"] and not pair.rooms["MESSY"].state()["workpapers"]
    assert all(t["status"] == "NOT_STARTED" for t in state["tasks"] if t["id"] not in contracts())
    assert len(state["sample_executions"]) == sum(len(x["sample_execution_ids"]) for x in links)
    assert {x["task_id"] for x in state["sample_executions"]} == set(contracts())


@pytest.mark.parametrize(
    "variant", ["future_risk_action", "boolean_risk_factor", "missing_fraud_theme"]
)
def test_new_small_native_temporal_bool_and_analysis_negatives(tmp_path, variant):
    from test_collected_byte_recovery_method import reseal_document

    sources = originals()
    if variant.startswith("future") or variant.startswith("boolean"):
        target = next(
            r for r in sources if r["source"]["system"] == "risk-history.risk_assessments"
        )
        body = json.loads(target["content"])
        if variant == "future_risk_action":
            body["recorded_at"] = "2028-01-01T09:00:00Z"
        else:
            body["risks"][0]["likelihood"] = True
        reseal_document(target, body)
        sources = [target]
        rows, at = collected(tmp_path, sources)
        history = History(rows, at)
        if variant == "boolean_risk_factor":
            with pytest.raises(ProcedureError, match="ordinal"):
                _risk(history)
        else:
            assert _risk(history)[0]["status"] == "SUPPORT_UNAVAILABLE"
            values = examine(rows, as_of=at)
            assert len(values) == 62
            assert any(
                o["facts"].get("recorded_action_chronology_supported") is False
                for o in values[0]["observations"]
            )
    else:
        target = next(r for r in sources if r["source"]["system"] == "eth004.risk_review")
        body = json.loads(target["content"])
        body["risk_themes"] = ["RELATED_PARTY"]
        reseal_document(target, body)
        sources = [r for r in sources if r["source"]["system"].startswith("eth004.")]
        rows, at = collected(tmp_path, sources)
        output = _fraud(History(rows, at))
        review = next(o for o in output if o["facts"]["declared_non_intrusion_risk_themes"])
        assert review["status"] == "EXCEPTION_RECORDED"
        assert review["facts"]["missing_override_reporting_related_party_themes"] == [
            "CONTROL_OVERRIDE",
            "DISHONEST_REPORTING",
        ]
