"""Company-native neutral originals predate two genuine 409-task workrooms."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from test_collected_byte_recovery_method import ordinary_inputs, row

from enterprise.audit_suite.collected_byte_recovery_method import reference
from enterprise.audit_suite.collected_engineering_history import History
from enterprise.audit_suite.company_store import CompanyStore, _json, _time
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.full_scope_company_pair import (
    GENERAL_METHOD_SCHEMA,
    GENERAL_METHOD_VERDICT,
    FullScopePair,
    PinnedReview,
)
from enterprise.audit_suite.persistent_company_journey import native_rows, write
from enterprise.audit_suite.source_engineering_product_methods import (
    concern_communication,
    contract_commitments,
    contracts,
    emergency,
    examine,
    local_packages,
    operating_changes,
    product_impact,
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
pytestmark = pytest.mark.skipif(not PACK.is_file(), reason="Exact private program pack absent")


def originals(
    *,
    wrong_test_build=False,
    self_review=False,
    future_approval=False,
    empty_tests=False,
    late_configuration=False,
    blocked_gate=False,
):
    result = []

    def add(family, role, record, day, value, *, version=1):
        at = f"2027-{day}T09:00:00Z"
        r = row(
            family + "." + role,
            record,
            at,
            {"engineering_neutral_fixture": True, "recorded_at": at, **value},
            version=version,
        )
        result.append(r)
        return r

    def ref(r):
        return reference(r["source"])

    def refs(*values):
        return {r["source"]["record"]: ref(r) for r in values}

    bad = {"attempts": 3, "timeout_ms": 100, "max_total_ms": 200}
    good = {"attempts": 2, "timeout_ms": 100, "max_total_ms": 200}
    config_bad = add(
        "change-history", "configurations", "CONFIG-BAD", "02-01", {"configuration": bad}
    )
    config_good = add(
        "change-history", "configurations", "CONFIG-GOOD", "02-02", {"configuration": good}
    )
    if late_configuration:
        config_good["source"]["available_at"] = _time("2027-02-25T09:00:00Z")
    build_rows, test_rows, review_rows, gate_rows, release_rows = [], [], [], [], []
    for n, (config, value) in enumerate(((config_bad, bad), (config_good, good)), 1):
        intent = add(
            "change-history",
            "change_intents",
            f"INTENT-{n}",
            f"02-0{n + 2}",
            {
                "cycle_id": f"CYCLE-{n}",
                "owner_id": "AUTHOR",
                "planned_reviewer_id": "REVIEWER",
                "requirement": "Positive integers, combined retry budget <=200",
                "change_type": "NORMAL",
                "baseline": ref(config_bad),
                "candidate": ref(config),
            },
        )
        package = {"format": "LOCAL_CONFIG_PACKAGE_V1", "configuration": value}
        build = add(
            "change-history",
            "builds",
            f"BUILD-{n}",
            f"02-0{n + 4}",
            {
                "cycle_id": f"CYCLE-{n}",
                "source": ref(config),
                "package": package,
                "package_sha256": hashlib.sha256(_json(package).encode()).hexdigest(),
            },
        )
        tested = add(
            "change-history",
            "tests",
            f"TEST-{n}",
            f"02-0{n + 6}",
            {
                "artifact": ref(build_rows[0] if n == 2 and wrong_test_build else build),
                "test_scope": "SCHEMA_ONLY",
                "passed": True,
                "tests": [{"name": "positive_integer_schema", "passed": True}],
            },
        )
        reviewed = add(
            "change-history",
            "peer_reviews",
            f"REVIEW-{n}",
            f"02-1{n}",
            {
                "artifact": ref(build),
                "cycle_id": f"CYCLE-{n}",
                "reviewer_id": "AUTHOR" if self_review and n == 2 else "REVIEWER",
                "decision": "APPROVED",
                "intent": ref(intent),
            },
        )
        gate = add(
            "change-history",
            "release_gate",
            f"GATE-{n}",
            f"02-1{n + 2}",
            {
                "artifact": ref(build),
                "peer_review": ref(reviewed),
                "tests": ref(tested),
                "decision": "BLOCKED" if blocked_gate and n == 2 else "APPROVED",
            },
        )
        release = add(
            "change-history",
            "local_releases",
            f"RELEASE-{n}",
            f"02-1{n + 4}",
            {
                "artifact": ref(build),
                "gate": ref(gate),
                "actor_id": "RELEASE-OPERATOR",
                "active_configuration_sha256": hashlib.sha256(
                    json.dumps(
                        {"engineering_neutral_fixture": True, **value}, sort_keys=True
                    ).encode()
                ).hexdigest(),
            },
        )
        exported = row(
            "configuration-runtime-history.configuration_export",
            "RAW-CONFIG",
            f"2027-02-1{n + 6}T09:00:00Z",
            {"engineering_neutral_fixture": True, **value},
            version=n,
        )
        exported["source"]["provenance"]["operational_metadata"] = {
            "source_references": {"release": ref(release)}
        }
        result.append(exported)
        build_rows.append(build)
        test_rows.append(tested)
        review_rows.append(reviewed)
        gate_rows.append(gate)
        release_rows.append(release)
    add(
        "change-history",
        "recovery",
        "ROLLBACK",
        "02-20",
        {"restore_source": ref(config_good), "method": "RECORDED_LOCAL_ONLY"},
    )

    # Separate later operating requests, with real earlier failure and later good records.
    for n in (1, 2):
        req = add(
            "eng005operating",
            "change_request",
            f"REQUEST-{n}",
            f"03-0{n}",
            {
                "change_id": f"CHANGE-{n}",
                "actor_id": "REQUESTER",
                "baseline": 30,
                "candidate": 20,
                "rollback": 30,
                "business_intent": "nonpersonal checkpoint update",
                "affected_data": "NONPERSONAL_MARKER_ONLY",
                "configuration_key": "checkpoint_minutes",
            },
        )
        risk = add(
            "eng005operating",
            "change_risk",
            f"RISK-{n}",
            f"03-0{n + 2}",
            {
                "test_plan": ["SCHEMA", "BOUNDARY", "RECOVERY"],
                "source_refs": refs(req),
                "rollback_reference": req["source"]["record"],
                "full_service_population": False,
            },
        )
        names = [] if empty_tests and n == 2 else ["SCHEMA", "BOUNDARY", "RECOVERY"]
        tested = add(
            "eng005operating",
            "change_test",
            f"OP-TEST-{n}",
            f"03-0{n + 4}",
            {
                "required_tests": names,
                "passed_tests": names,
                "test_results": {name: name != "RECOVERY" or n == 2 for name in names},
                "tested_candidate": 20,
                "source_refs": refs(req, risk),
            },
        )
        approval = add(
            "eng005operating",
            "change_approval",
            f"APPROVAL-{n}",
            f"03-0{n + 6}",
            {
                "decision": "APPROVE_SELECTED_LOCAL_CHANGE",
                "actor_id": "APPROVER",
                "source_refs": refs(req, risk, tested),
                **({"approved_at": "2028-01-01T00:00:00Z"} if future_approval and n == 2 else {}),
            },
        )
        release = add(
            "eng005operating",
            "change_release",
            f"OP-RELEASE-{n}",
            f"03-1{n}",
            {
                "security_decision_ref": approval["source"]["record"],
                "source_refs": refs(approval),
                "decision": "APPROVE_SELECTED_NONPERSONAL_CONFIG",
                "actor_id": "OPERATOR",
            },
        )
        applied = add(
            "eng005operating",
            "change_application",
            f"APPLICATION-{n}",
            f"03-1{n + 2}",
            {
                "release_ref": release["source"]["record"],
                "source_refs": refs(release),
                "applied_value": 25 if n == 1 else 20,
            },
        )
        verified = add(
            "eng005operating",
            "change_verification",
            f"VERIFY-{n}",
            f"03-1{n + 4}",
            {
                "approved_release_ref": release["source"]["record"],
                "source_refs": refs(applied, release),
                "approved_value": 20,
                "observed_value": 25 if n == 1 else 20,
                "local_match": True,
            },
        )
        recovered = add(
            "eng005operating",
            "change_recovery",
            f"RECOVERY-{n}",
            f"03-1{n + 6}",
            {
                "source_refs": refs(verified),
                "rehearsed_baseline": 30,
                "restored_active_value": 20,
            },
        )
        add(
            "eng005operating",
            "change_review",
            f"OP-REVIEW-{n}",
            f"03-2{n}",
            {
                "source_refs": refs(recovered),
                "historical_exception_open": n == 1,
                "current_selected_value": 20,
                "actor_id": "PROPOSED-REVIEWER",
            },
        )

    definition = add(
        "eng005",
        "emergency_intake",
        "EMERGENCY-DEFINITION",
        "04-01",
        {
            "exercise_id": "LOCAL-URGENT",
            "baseline": good,
            "candidate": bad,
            "baseline_sha256": "a" * 64,
            "local_rule": "NO_AUTHORITY_NO_CHANGE",
        },
    )
    gate = add(
        "eng005",
        "emergency_gate",
        "URGENT-GATE",
        "04-02",
        {"source_previous": ref(definition), "evidence": [], "decision": "NO_AUTHORITY"},
    )
    prior = gate
    for n in (1, 2):
        prior = add(
            "eng005",
            "local_change_state",
            "URGENT-STATE",
            f"04-0{n + 2}",
            {
                "exercise_id": "LOCAL-URGENT",
                "source_previous": ref(prior),
                "candidate_applied": n == 1,
                "active_sha256": "b" * 64 if n == 1 else "a" * 64,
            },
            version=n,
        )
    add(
        "eng005",
        "retrospective_observation",
        "URGENT-RETRO",
        "04-05",
        {"source_previous": ref(prior), "corporate_retroactive_approval": False},
    )
    stage = add(
        "stagegate",
        "stage_input",
        "RISK-INPUT",
        "05-01",
        {"risk_statement": "shared carrier/key risk", "actor_person_id": "TECH"},
    )
    add(
        "stagegate",
        "stage_assessment",
        "RISK-ASSESS",
        "05-02",
        {
            "source_previous": ref(stage),
            "risk_acceptance": "NOT_PERFORMED",
            "technical_decision_scope": "LOCAL_RECOMMENDATION",
        },
    )

    scope = add(
        "provider",
        "operation_scope",
        "DEPENDENCY-SCOPE",
        "06-01",
        {"declared_relationship_ids": ["PRIMARY", "RECOVERY", "SUPPORT"]},
    )
    relationships = [
        add("provider", "relationship_register", dep, "06-02", {"provider_id": dep})
        for dep in ("PRIMARY", "RECOVERY", "SUPPORT")
    ]
    ba_scope = add(
        "phi_ba",
        "operation_scope",
        "SIM-BA-SCOPE",
        "06-03",
        {
            "sim_customer_id": "SIM-CUSTOMER",
            "sim_service_id": "SIM-SERVICE",
            "sim_subcontractor_id": "SIM-SUPPORT",
        },
    )
    contract = add(
        "phi_ba",
        "contract_register",
        "SIM-CONTRACT",
        "06-04",
        {
            "synthetic_terms": [
                {
                    "clause_candidate_id": "responsibility",
                    "declared_obligation": "nonpersonal-marker",
                }
            ]
        },
    )
    add(
        "contract",
        "selected_term_inventory",
        "TERM-CENSUS",
        "06-05",
        {
            "term_occurrence_count": 2,
            "term_occurrences": [
                {
                    "occurrence_id": "TERM-1",
                    "term_id": "responsibility",
                    "term_value": "ePHI-unsupported",
                    "source_ref": ref(contract),
                }
            ],
        },
    )
    commitment = add(
        "prd",
        "commitment_scope",
        "COMMITMENT",
        "06-06",
        {
            "service_id": "SIM-SERVICE",
            "customer_id": "SIM-CUSTOMER",
            "delivery_contacts": {
                "customer_delivery": "DELIVERY",
                "legal_review": "LEGAL",
                "product": "PRODUCT",
            },
            "actual_customer_or_contract_status": "SIMULATED_ONLY",
            "commitment": "marker hosting recovery",
        },
    )
    request = add(
        "prd",
        "change_request",
        "SERVICE-CHANGE",
        "06-07",
        {
            "source_refs": refs(commitment),
            "service_id": "SIM-SERVICE",
            "customer_id": "SIM-CUSTOMER",
            "change_execution_state": "PROPOSED_NOT_APPLIED",
        },
    )
    prior = request
    for n in (1, 2):
        prior = add(
            "prd",
            "impact_assessment",
            "IMPACT",
            f"06-0{n + 7}",
            {
                "source_refs": refs(request, scope, *relationships),
                "source_previous": ref(prior),
                "internal_dependency_ids": ["PRIMARY", "RECOVERY"]
                + (["SUPPORT"] if n == 2 else []),
                "original_recipient_matrix": ["DELIVERY", "LEGAL", "PRODUCT"],
            },
            version=n,
        )
    notice = add(
        "prd",
        "notice_decision",
        "NOTICE",
        "06-11",
        {
            "source_previous": ref(prior),
            "customer_delivery_contact_id": "WRONG",
            "legal_reviewer_id": "LEGAL",
            "send_gate": "BLOCKED_NO_EXTERNAL_DELIVERY",
            "customer_receipt_or_acknowledgment": False,
        },
    )
    add(
        "prd",
        "dependency_discovery",
        "DISCOVERY",
        "06-12",
        {"source_previous": ref(notice), "omitted_dependency_id": "SUPPORT"},
    )
    add(
        "prd",
        "reconciliation",
        "SERVICE-RECON",
        "06-13",
        {
            "source_previous": ref(notice),
            "external_customer_receipts": 0,
            "external_messages_sent": 0,
            "notice_duty_resolved": False,
        },
    )
    inbox = add(
        "prdconcern",
        "simulated_inbox",
        "CONCERN-INBOX",
        "07-01",
        {"claimant_customer_identity_verified": False, "real_external_messages_sent": 0},
    )
    prior = inbox
    for n in (1, 2):
        prior = add(
            "prdconcern",
            "recipient_matrix",
            "AUDIENCE",
            f"07-0{n + 1}",
            {
                "customer_id": "SIM-CUSTOMER",
                "service_id": "SIM-SERVICE",
                "previous_native_content": {
                    "record": prior["source"]["record"],
                    "sha256": prior["source"]["sha256"],
                },
                "selected_internal_recipient_roles": ["CUSTOMER_DELIVERY", "LEGAL", "PRODUCT"]
                + (["SUPPORT_RECOVERY"] if n == 2 else []),
                "company_outbound_delivery_accepted": False,
                "separate_customer_acknowledgment_exists": False,
                "upstream_original_refs": refs(commitment, ba_scope),
            },
            version=n,
        )
    add(
        "prdconcern",
        "dispatch_attempt",
        "CONCERN-SEND",
        "07-05",
        {
            "previous_native_content": {
                "record": prior["source"]["record"],
                "sha256": prior["source"]["sha256"],
            },
            "claimant_customer_identity_verified": False,
            "real_external_messages_sent": 0,
            "status": "INTERNAL_BLOCKED",
        },
    )
    return result


def collected(tmp_path, sources):
    tmp_path.chmod(0o700)
    records, context = ordinary_inputs(tmp_path, sources)
    for r in records:
        r["retained_bytes"] = r["content"]
        r["content_type"] = "application/json"
        r["logical_family"], r["logical_system"] = r["source"]["system"].split(".", 1)
    return records, context.simulated_at


@pytest.fixture(scope="module")
def ordinary_pair(tmp_path_factory):
    root = tmp_path_factory.mktemp("b04-genuine-company-before-two-workrooms")
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
    store.register_system(
        "NEUTRAL-COMPANY", "BETA", "prdconcern.simulated_inbox", "OTHER-SOURCE-OWNER"
    )
    store.append_version(
        "NEUTRAL-COMPANY",
        "BETA",
        "prdconcern.simulated_inbox",
        "UNUSED-OTHER-BRANCH",
        expected_version=0,
        command_id="AUTHOR-OTHER-BRANCH",
        event_at="2027-01-01T00:00:00Z",
        available_at="2027-01-01T00:00:00Z",
        content=b'{"engineering_neutral_fixture":true}',
        provenance={
            "content_type": "application/json",
            "source_reference": "neutral-other-branch-original",
            "name": "other.json",
        },
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
    room = pair.rooms["CLEAN"]
    before = native_rows(pair.world.database)
    records = room.acquire(
        systems=[r.system for r in routes["CLEAN"]],
        control_id="SH-ENG-001",
        purpose="B04 neutral exact company source examination",
    )
    assert len(records) == len(sources) and native_rows(pair.world.database) == before
    return pair, records, room.state()["simulated_at"]


def hist(ordinary_pair):
    _, records, as_of = ordinary_pair
    return History(records, as_of=as_of)


def test_two_full_rooms_and_exact_all37_source_based_examinations(ordinary_pair):
    pair, records, as_of = ordinary_pair
    assert (
        len(pair.rooms["CLEAN"].state()["tasks"])
        == len(pair.rooms["MESSY"].state()["tasks"])
        == 409
    )
    birth = json.loads((pair.world.root / "INITIALIZATION.json").read_bytes())
    assert birth["audit_engagements_at_initialization"] == 0
    values = examine(records, as_of=as_of, scratch_root=pair.root / "never-opened-scratch")
    assert len(values) == len(contracts()) == 37
    assert [r["task_id"] for r in values] == [t["task_id"] for t in task_plan()]
    assert {r["result"]["examined_attributes"]["control_id"] for r in values} == {
        "SH-ENG-00" + str(n) for n in range(1, 7)
    } | {"SH-PRD-00" + str(n) for n in range(2, 5)}
    for value in values:
        assert value["result"]["prior_audit_or_Key_outcomes_used"] is False
        assert value["result"]["professional_or_actual_source_applicability_accepted"] is False
        assert value["disposition"]["conclusion"] in {"LIMITATION", "FAIL"}
        for prefix in ("EXACT-TASK-ATTRIBUTES", "EXACT-NATIVE-SUPPORT"):
            parts = [o for o in value["observations"] if o["id"].startswith(prefix)]
            assert parts
            citations = {e["artifact_id"] for o in parts for e in o["evidence"]}
            assert citations == set(value["artifact_ids"])
            assert all(len(o["evidence"]) <= 20 and len(o["id"]) <= 128 for o in parts)
            assert parts[0]["facts"]["citation_group"]["all_citation_part_ids"] == [
                o["id"] for o in parts
            ]
    for control in {t["control_id"] for t in task_plan()}:
        keys = [
            set(v["result"]["examined_attributes"]["task_kind_primary_attributes"])
            for v in values
            if v["result"]["examined_attributes"]["control_id"] == control
            and v["result"]["examined_attributes"]["exact_clause"]
            in {"TOD", "IMPLEMENTATION", "TOE"}
        ]
        assert len(keys) == 3 and not keys[0] == keys[1] == keys[2]


def test_local_failure_then_supported_exact_build_release_and_rollback(ordinary_pair):
    out = local_packages(hist(ordinary_pair))
    assert [r["local_budget_reperformance"]["within_local_limit"] for r in out["packages"]] == [
        False,
        True,
    ]
    assert [r["independent_local_release_prerequisites"] for r in out["release_gates"]] == [
        False,
        True,
    ]
    assert {r["facet"] for r in out["exceptions"]} >= {
        "PACKAGE",
        "TEST_SCOPE",
        "RELEASE_GATE",
        "RELEASE_AFTER_UNSUPPORTED_GATE",
    }
    assert all(
        r["export_bytes_equal_released_declared_digest"] for r in out["raw_configuration_exports"]
    )
    assert (
        out["rollback_sources"][0]["recomputed_baseline_configuration_budget"]["within_local_limit"]
        is True
    )
    assert (
        out["rollback_sources"][0]["actual_restore_or_representative_rehearsal_performed"] is False
    )


def test_operating_mandatory_results_application_and_false_clean_claim_preserved(ordinary_pair):
    out = operating_changes(hist(ordinary_pair))
    assert [r["mandatory_test_support"] for r in out["releases"]] == [False, True]
    assert [r["local_release_supported"] for r in out["releases"]] == [False, True]
    assert [r["applied_value_equals_exact_requested_candidate"] for r in out["applications"]] == [
        False,
        True,
    ]
    assert [r["independent_recorded_values_match"] for r in out["verifications"]] == [False, True]
    assert out["verifications"][0]["company_match_claim"] is True
    assert {r["facet"] for r in out["exceptions"]} >= {
        "MANDATORY_TESTS",
        "APPLIED_VALUE",
        "POST_CHANGE_VERIFICATION",
    }


def test_emergency_bypass_and_later_rollback_do_not_make_retrospective_approval(ordinary_pair):
    out = emergency(hist(ordinary_pair))
    assert [r["recorded_candidate_applied"] for r in out["dated_states"]] == [True, False]
    assert len(out["exceptions"]) == 1
    assert all(
        r["recorded_retrospective_is_qualified_approval"] is False for r in out["dated_states"]
    )


def test_contract_census_and_terms_are_reperformed_not_provisional_acceptance(ordinary_pair):
    out = contract_commitments(hist(ordinary_pair))
    census = out["selected_term_populations_before_selection"][0]
    assert census["recomputed_term_count"] == 1 and census["company_count_agrees"] is False
    assert census["term_original_examinations"][0]["term_value_equals_exact_original"] is False
    assert out["actual_delivery_capability_or_contract_authority_accepted"] is False


def test_independent_dependency_and_contact_failures_survive_later_impact_repair(ordinary_pair):
    out = product_impact(hist(ordinary_pair))
    assert [
        r["scope_dependencies_omitted_from_impact"]
        for r in out["impact_populations_before_selection"]
    ] == [["SUPPORT"], []]
    assert out["notice_contact_tests"][0]["delivery_contact_matches_declared_owner"] is False
    assert {r["facet"] for r in out["exceptions"]} == {"IMPACT_DEPENDENCIES", "NOTICE_CONTACTS"}
    assert out["internal_change_is_not_external_customer_communication"] is True


def test_independent_ba_support_audience_before_internal_repair_without_external_receipt(
    ordinary_pair,
):
    out = concern_communication(hist(ordinary_pair))
    assert [r["missing_internal_roles"] for r in out["dated_recipient_and_delivery_witnesses"]] == [
        ["SUPPORT_RECOVERY"],
        [],
    ]
    assert len(out["exceptions"]) == 1
    assert all(
        r["actual_external_audience_receipt_established"] is False
        for r in out["dated_recipient_and_delivery_witnesses"]
    )
    assert (
        next(
            r
            for r in out["dated_intake_response_failure_and_exception_versions"]
            if r["source"]["record"] == "CONCERN-SEND"
        )["prior_original_status"]
        == "EXACT_AVAILABLE_SCALAR_WITNESS_NO_NATIVE_VERSION_POINTER"
    )


@pytest.mark.parametrize(
    "variant",
    [
        "wrong_test_build",
        "self_review",
        "future_approval",
        "empty_tests",
        "late_configuration",
        "blocked_gate",
    ],
)
def test_company_before_collection_fully_bound_negative(ordinary_pair, tmp_path, variant):
    records, as_of = collected(tmp_path, originals(**{variant: True}))
    history = History(records, as_of=as_of)
    if variant == "wrong_test_build":
        gate = local_packages(history)["release_gates"][-1]
        assert gate["tests_cover_exact_selected_build"] is False
        assert gate["independent_local_release_prerequisites"] is False
    elif variant == "self_review":
        gate = local_packages(history)["release_gates"][-1]
        assert (
            gate["named_peer_independence"] is False
            and gate["independent_local_release_prerequisites"] is False
        )
    elif variant == "late_configuration":
        out = local_packages(history)
        assert (
            out["packages"][-1]["configuration_original_status"]
            == "ORIGINAL_UNAVAILABLE_AT_COMPANY_OCCURRENCE"
        )
        assert out["release_gates"][-1]["independent_local_release_prerequisites"] is False
    elif variant == "blocked_gate":
        out = local_packages(history)
        assert out["local_releases"][-1]["gate_recorded_release_allowed"] is False
        assert any(
            r["facet"] == "RELEASE_AFTER_UNSUPPORTED_GATE" and r["source"]["record"] == "RELEASE-2"
            for r in out["exceptions"]
        )
    else:
        release = operating_changes(history)["releases"][-1]
        assert release["local_release_supported"] is False
        if variant == "future_approval":
            assert (
                release["approval_original_status"]
                == "RECORDED_ACTION_UNSUPPORTED_AT_NATIVE_OCCURRENCE"
            )
        else:
            assert release["mandatory_test_support"] is False
            assert release["mandatory_test_attributes"][0]["risk_required_tests_omitted"] == [
                "BOUNDARY",
                "RECOVERY",
                "SCHEMA",
            ]


@pytest.mark.parametrize(
    "change",
    [
        "wrong_role",
        "boolean_version",
        "boolean_content_bytes",
        "future_real_receipt",
        "changed_bytes",
    ],
)
def test_strict_custody_refusal(ordinary_pair, change):
    _, records, as_of = ordinary_pair
    altered = copy.deepcopy(records)
    if change == "wrong_role":
        altered[0]["logical_system"] = "meeting_note"
    elif change == "boolean_version":
        altered[0]["source"]["version"] = True
    elif change == "boolean_content_bytes":
        altered[0]["receipt"]["content_bytes"] = True
    elif change == "future_real_receipt":
        altered[0]["receipt"]["collected_at"] = "2100-01-01T00:00:00Z"
    else:
        altered[0]["retained_bytes"] += b" "
    with pytest.raises(ProcedureError):
        History(altered, as_of=as_of)


def test_missing_exact_original_does_not_reconstruct_or_latest_alias(ordinary_pair):
    _, records, as_of = ordinary_pair
    history = History([r for r in records if r["source"]["record"] != "CONFIG-GOOD"], as_of=as_of)
    out = local_packages(history)
    assert out["packages"][-1]["configuration_original_status"] == "ORIGINAL_NOT_COLLECTED"
    assert out["rollback_sources"][0]["restore_original"] is None
    assert out["release_gates"][-1]["independent_local_release_prerequisites"] is False
    assert (
        out["rollback_sources"][0]["recomputed_baseline_configuration_budget"]["within_local_limit"]
        is None
    )


def test_cached_document_cannot_replace_original_and_unavailable_scopes_bounded(ordinary_pair):
    pair, records, as_of = ordinary_pair
    altered = copy.deepcopy(records)
    for r in altered:
        r["document"] = {"passed": True, "magic_expected_outcome": "PASS"}
    assert examine(altered, as_of=as_of, scratch_root=pair.root / "inert") == examine(
        records, as_of=as_of, scratch_root=pair.root / "inert"
    )
    context = [r for r in records if r["logical_family"] == "stagegate"]
    output = examine(context, as_of=as_of, scratch_root=pair.root / "inert")
    eng2 = next(v for v in output if v["task_id"] == "TASK-SH-ENG-002-corporate-TOE")
    assert eng2["result"]["selected_native_population_before_selection"] == []
    assert eng2["result"]["required_task_attribute_population_available"] is False
    assert eng2["disposition"]["conclusion"] == "LIMITATION"


def test_exact37_neutral_gate_writes_ordinary_fieldwork_and_preserves_other372_tasks(ordinary_pair):
    pair, records, _ = ordinary_pair
    room = pair.rooms["CLEAN"]
    source_before = native_rows(pair.world.database)
    method = REPO / "enterprise/audit_suite/source_engineering_product_methods.py"
    review = pair.root / "NEUTRAL-B04-METHOD-REVIEW.json"
    dependencies = {
        name: file_sha(method.with_name(name))
        for name in (
            "collected_engineering_history.py",
            "company_store.py",
            "fresh_sec003_procedure.py",
            "source_library_audit.py",
        )
    }
    write(
        review,
        {
            "schema": GENERAL_METHOD_SCHEMA,
            "verdict": GENERAL_METHOD_VERDICT,
            "source_execution_authorized": True,
            "method_module_sha256": file_sha(method),
            "dependency_module_sha256": dependencies,
            "method_callable": examine.__module__ + "." + examine.__qualname__,
            "selected_task_ids": list(contracts()),
            "task_contracts": contracts(),
            "neutral_author_fixture_not_actual_independent_acceptance": True,
        },
    )
    links = room.append_reviewed_batch(
        batch="neutral-B04",
        review=PinnedReview(review, file_sha(review)),
        rows=records,
        method=examine,
    )
    state = room.state()
    assert len(links) == len(state["workpapers"]) == len(state["selections"]) == 37
    assert len(state["sample_executions"]) == sum(
        len(link["sample_execution_ids"]) for link in links
    )
    assert {r["task_id"] for r in state["sample_executions"]} == set(contracts())
    assert all(r["automatic_testing_credit"] is False for r in state["sample_executions"])
    assert native_rows(pair.world.database) == source_before
    selected = set(contracts())
    assert all(
        t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
        for t in state["tasks"]
        if t["id"] not in selected
    )
    assert not state["reviews"] and not pair.rooms["MESSY"].state()["workpapers"]
    assert all(t["conclusion"] != "PASS" for t in state["tasks"])
