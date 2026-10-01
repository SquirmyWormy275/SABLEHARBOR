"""Changed originals, exact roles and chronology affect assurance examinations."""

import hashlib
import json
from copy import deepcopy

import pytest

from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_assurance_methods import BUSINESS_ID, examine

AS_OF = "2028-01-02T09:00:00Z"


def retained(system, record, body, *, at="2027-09-01T09:00:00Z", version=1):
    family, role = system.split(".", 1)
    raw = json.dumps(body, sort_keys=True).encode()
    source = {
        "company": "NEUTRAL-ASSURANCE",
        "branch": "north",
        "system": system,
        "record": record,
        "version": version,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "event_at": at,
        "available_at": at,
        "imported_at": "2026-10-01T00:00:00Z",
    }
    return {
        "source": source,
        "receipt": {"source": deepcopy(source)},
        "retained_bytes": raw,
        "artifact_id": "ART-" + system + record + str(version),
        "artifact_sha256": source["sha256"],
        "content_type": "application/json",
        "logical_family": family,
        "logical_system": role,
    }


def reference(row):
    return {k: row["source"][k] for k in BUSINESS_ID}


def repin(row, **fields):
    body = json.loads(row["retained_bytes"])
    body.update(fields)
    row["retained_bytes"] = json.dumps(body, sort_keys=True).encode()
    row["source"]["sha256"] = hashlib.sha256(row["retained_bytes"]).hexdigest()
    row["artifact_sha256"] = row["source"]["sha256"]
    row["receipt"]["source"] = deepcopy(row["source"])


def owner_history():
    screen = retained(
        "assurance.issue_screening",
        "issue-x",
        {"issue_manager_person_id": "reviewer"},
        at="2027-08-01T09:00:00Z",
    )
    finding = retained(
        "assurance.issue_finding",
        "issue-x",
        {
            "finding_closed": False,
            "severity": "HIGH",
            "severity_basis": "service interruption",
            "technical_action_owner_person_id": "operator",
            "plan_response_due_at": "2027-09-01T09:00:00Z",
            "closure_criteria": "independent retest",
            "prior_issue_event_sha256": screen["source"]["sha256"],
        },
        at="2027-08-02T09:00:00Z",
    )
    scope = retained(
        "ass001002.monitoring_scope",
        "scope-x",
        {
            "quarter": "2027-Q3",
            "selected_control": "control-x",
            "selected_service": "service-x",
            "upstream_refs": [reference(screen)],
        },
        at="2027-09-05T09:00:00Z",
    )
    owner = retained(
        "ass001002.owner_self_assessment",
        "owner-x",
        {
            "quarter": "2027-Q3",
            "selected_control": "control-x",
            "selected_service": "service-x",
            "statement": "SELECTED_RETEST_PASSED_NO_OPEN_ISSUE_REPORTED",
            "omitted_known_issue": False,
        },
        at="2027-09-08T09:00:00Z",
    )
    technical = retained("bcm.exercise_result", "exercise-x", {}, at="2027-08-03T09:00:00Z")
    observation = retained(
        "ass001002.second_line_observation",
        "observation-x",
        {
            "actor_person_id": "reviewer",
            "owner_submission_sha256": owner["source"]["sha256"],
            "technical_input": reference(technical),
            "nontechnical_input": reference(finding),
            "evaluated_effectiveness": "NOT_CONCLUDED",
        },
        at="2027-09-12T09:00:00Z",
    )
    return [screen, finding, scope, owner, technical, observation]


def test_owner_claim_is_compared_to_actual_issue_not_answer_flag():
    rows = owner_history()
    result = examine(rows, as_of=AS_OF)
    check = result["checks"]["SH-ASS-001"]
    assert check["exceptions"][0]["reason"] == "MANAGEMENT_NO_ISSUE_CLAIM_CONTRADICTED"
    assert len(check["evidence"][0]["actual_prior_open_findings"]) == 1
    assert not result["professional_assurance_concluded"]
    assert not result["task_credit"]
    assert not result["full_period_toe_completed"]


def test_cached_document_cannot_change_recorded_owner_claim():
    rows = owner_history()
    rows[3]["document"] = {"statement": "ALL_CLEAR"}
    assert examine(rows, as_of=AS_OF)["checks"]["SH-ASS-001"]["exceptions"]


def test_later_correction_does_not_erase_initial_management_failure():
    rows = owner_history()
    corrected = deepcopy(rows[3])
    corrected["source"].update(
        version=2, event_at="2027-09-13T09:00:00Z", available_at="2027-09-13T09:00:00Z"
    )
    repin(corrected, statement="CORRECTED_OPEN_HISTORICAL_ISSUE_DISCLOSED")
    result = examine([*rows, corrected], as_of=AS_OF)["checks"]["SH-ASS-001"]
    assert len(result["evidence"]) == 2
    assert len(result["exceptions"]) == 1
    assert result["exceptions"][0]["owner"]["version"] == 1


def test_future_finding_cannot_contradict_earlier_attestation():
    rows = owner_history()
    rows[1]["source"].update(event_at="2027-09-10T09:00:00Z", available_at="2027-09-10T09:00:00Z")
    rows[1]["receipt"]["source"] = deepcopy(rows[1]["source"])
    repin(rows[5], nontechnical_input=reference(rows[1]))
    assert not examine(rows, as_of=AS_OF)["checks"]["SH-ASS-001"]["exceptions"]


def test_second_line_compares_actual_sources_and_prior_issue_screening():
    check = examine(owner_history(), as_of=AS_OF)["checks"]["SH-ASS-002"]
    assert check["exceptions"][0]["reason"] == "EVALUATOR_PREVIOUSLY_SCREENED_ISSUE"
    assert set(check["evidence"][0]["underlying_originals"]) == {
        "technical_input",
        "nontechnical_input",
    }
    assert not check["evidence"][0]["independence_verified"]


def test_genuine_wrong_native_role_cannot_supply_technical_result():
    rows = owner_history()
    wrong = retained("bcm.support_note", "support-x", {}, at="2027-08-03T09:00:00Z")
    repin(rows[5], technical_input=reference(wrong))
    check = examine([*rows, wrong], as_of=AS_OF)["checks"]["SH-ASS-002"]
    assert "technical_input" not in check["evidence"][0]["underlying_originals"]
    assert any(
        x.get("reason") == "ACTUAL_NATIVE_ROLE_DIFFERS"
        for x in check["unperformed"]
        if isinstance(x, dict)
    )


def test_source_published_after_company_event_is_unperformed_support():
    rows = owner_history()
    rows[4]["source"].update(event_at="2027-09-13T09:00:00Z", available_at="2027-09-13T09:00:00Z")
    rows[4]["receipt"]["source"] = deepcopy(rows[4]["source"])
    repin(rows[5], technical_input=reference(rows[4]))
    result = examine(rows, as_of=AS_OF)
    assert any(
        x["status"] == "SOURCE_UNAVAILABLE_AT_COMPANY_EVENT"
        for x in result["native_reference_joins"]
    )
    assert (
        "technical_input"
        not in result["checks"]["SH-ASS-002"]["evidence"][0]["underlying_originals"]
    )


@pytest.mark.parametrize(
    "attack",
    [
        "changed_bytes",
        "receipt_clock",
        "boolean_version",
        "route_alias",
        "future_cutoff",
        "mixed_branch",
    ],
)
def test_custody_attacks_fail_closed(attack):
    rows = owner_history()
    if attack == "changed_bytes":
        rows[0]["retained_bytes"] += b" "
    elif attack == "receipt_clock":
        rows[0]["receipt"]["source"]["available_at"] = "2027-08-02T09:00:00Z"
    elif attack == "boolean_version":
        rows[0]["source"]["version"] = True
        rows[0]["receipt"]["source"]["version"] = True
    elif attack == "route_alias":
        rows[4]["logical_system"] = "policy_note"
    elif attack == "future_cutoff":
        rows[0]["source"].update(
            event_at="2028-01-03T09:00:00Z", available_at="2028-01-03T09:00:00Z"
        )
        rows[0]["receipt"]["source"] = deepcopy(rows[0]["source"])
    else:
        rows[0]["source"]["branch"] = "south"
        rows[0]["receipt"]["source"] = deepcopy(rows[0]["source"])
    with pytest.raises(ProcedureError):
        examine(rows, as_of=AS_OF)


def test_boolean_locator_version_is_not_integer_one_even_after_repinning():
    rows = owner_history()
    ref = reference(rows[0])
    ref["version"] = True
    repin(rows[2], upstream_refs=[ref])
    with pytest.raises(ProcedureError, match="positive-version"):
        examine(rows, as_of=AS_OF)


def test_cross_branch_pointer_is_not_permission_to_read_that_branch():
    rows = owner_history()
    ref = reference(rows[0])
    ref["branch"] = "south"
    repin(rows[2], upstream_refs=[ref])
    result = examine(rows, as_of=AS_OF)
    assert any(
        x["status"] == "OUTSIDE_COLLECTED_BRANCH_AUTHORITY"
        for x in result["native_reference_joins"]
    )


def population_history():
    result = retained("bcm.exercise_result", "arbitrary-exercise", {}, at="2027-07-02T09:00:00Z")
    population = retained(
        "assuranceops.assurance_population",
        "population-x",
        {
            "period": {"start": "2027-07-01T00:00:00Z", "end": "2027-09-30T23:59:59Z"},
            "source_period_event_refs": [reference(result)],
            "antecedent_context_refs": [],
            "source_version_counts": {"BCM": 1},
            "collection_as_of": "2027-09-18T09:00:00Z",
            "source_queries": {"BCM": "DROP TABLE versions;"},
            "selected_technical_versions": [reference(result)],
            "selected_nontechnical_versions": [],
        },
        at="2027-09-18T09:00:00Z",
    )
    wp = retained(
        "assuranceops.assurance_workpaper",
        "workpaper-x",
        {"dependencies": [reference(population)], "upstream_originals": [reference(result)]},
        at="2027-09-20T09:00:00Z",
    )
    review = retained(
        "assuranceops.assurance_review",
        "review-x",
        {"dependencies": [reference(wp)], "reviewer_id": "reviewer", "preparer_id": "author"},
        at="2027-09-21T09:00:00Z",
    )
    return [result, population, wp, review]


def test_population_recomputed_without_executing_stored_query():
    result = examine(population_history(), as_of=AS_OF)
    check = result["checks"]["SH-ASS-004"]
    assert check["evidence"][0]["recomputed_collected_cohort_counts"] == {"BCM": 1}
    assert check["evidence"][0]["stored_query_executed"] is False
    assert not check["exceptions"]
    assert any(
        x.get("reason") == "FROZEN_QUERY_DOES_NOT_COVER_REMAINING_PERIOD"
        for x in check["unperformed"]
        if isinstance(x, dict)
    )
    assert check["evidence"][1]["reviews_of_exact_version"][0]["record"] == "review-x"
    assert not result["company_workpapers_are_auditor_results"]


def test_missing_original_and_forged_count_never_establish_population():
    rows = population_history()
    repin(rows[1], source_version_counts={"BCM": True})
    repin(rows[2], dependencies=[reference(rows[1])])
    repin(rows[3], dependencies=[reference(rows[2])])
    check = examine(rows, as_of=AS_OF)["checks"]["SH-ASS-004"]
    assert check["exceptions"][0]["reason"] == "DECLARED_COHORT_COUNT_DIFFERS_OR_ORIGINAL_MISSING"
    check = examine(rows[1:], as_of=AS_OF)["checks"]["SH-ASS-004"]
    assert any(
        x.get("status") == "ORIGINAL_NOT_COLLECTED"
        for x in check["unperformed"]
        if isinstance(x, dict)
    )


def test_review_of_old_workpaper_does_not_approve_new_version():
    rows = population_history()
    newer = deepcopy(rows[2])
    newer["source"].update(
        version=2, event_at="2027-09-22T09:00:00Z", available_at="2027-09-22T09:00:00Z"
    )
    repin(newer, correction="new documentary claim")
    check = examine([*rows, newer], as_of=AS_OF)["checks"]["SH-ASS-004"]
    entries = [x for x in check["evidence"] if "company_workpaper" in x]
    assert len(entries[0]["reviews_of_exact_version"]) == 1
    assert not entries[1]["reviews_of_exact_version"]


def test_later_technical_correction_is_not_historical_finding_closure():
    rows = owner_history()
    request = retained(
        "assurance.remediation_request",
        "issue-x",
        {
            "finding_closed": False,
            "technical_recovery_correction_observed": True,
            "validation_performed": False,
        },
        at="2027-09-15T09:00:00Z",
    )
    check = examine([*rows, request], as_of=AS_OF)["checks"]["SH-ASS-005"]
    assert check["evidence"][0]["actual_open_finding"] is True
    assert check["evidence"][0]["technical_correction_is_closure"] is False
    assert len(check["evidence"][0]["retained_history"]) == 3


def test_boolean_finding_status_cannot_be_replaced_by_numeric_zero():
    rows = owner_history()
    repin(rows[1], finding_closed=0)
    with pytest.raises(ProcedureError, match="Typed finding closure"):
        examine(rows, as_of=AS_OF)


def programme_history():
    plan = retained(
        "assuranceops.assurance_programme",
        "stream-x",
        {"status": "SCHEDULED", "due_at": "2027-09-22T09:00:00Z"},
        at="2027-09-16T09:00:00Z",
    )
    review = retained(
        "assuranceops.assurance_review",
        "review-x",
        {"reviewer_id": "independent-reviewer", "preparer_id": "author"},
        at="2027-09-21T09:00:00Z",
    )
    complete = retained(
        "assuranceops.assurance_programme",
        "stream-x",
        {"status": "COMPLETED_SCOPED_INTERNAL_EVALUATION", "dependencies": [reference(review)]},
        at="2027-09-21T10:00:00Z",
        version=2,
    )
    close = retained(
        "assuranceops.assurance_period_reconciliation",
        "close-x",
        {
            "workstream_record_ids": ["stream-x"],
            "planned_workstreams": 1,
            "completed_workstreams": 1,
            "period": {"end": "2027-09-30T23:59:59Z"},
        },
        at="2027-09-30T09:00:00Z",
    )
    return [plan, review, complete, close]


def test_actual_plans_completions_and_close_counts_are_separate_from_period_tail():
    check = examine(programme_history(), as_of=AS_OF)["checks"]["SH-ASS-003"]
    assert check["evidence"][1]["recomputed_selected_roster"] == {
        "planned_workstreams": 1,
        "completed_workstreams": 1,
    }
    assert not check["exceptions"]
    assert any(
        x.get("reason") == "RECONCILIATION_PRECEDES_DECLARED_PERIOD_END"
        for x in check["unperformed"]
        if isinstance(x, dict)
    )


def test_company_self_review_flag_cannot_override_equal_actual_identities():
    rows = programme_history()
    repin(rows[1], reviewer_id="author", independent_from_preparation_and_operation=True)
    repin(rows[2], dependencies=[reference(rows[1])])
    check = examine(rows, as_of=AS_OF)["checks"]["SH-ASS-003"]
    assert check["exceptions"][0]["reason"] == "SELF_REVIEW"


def test_uncollected_review_does_not_follow_from_completion_status():
    rows = programme_history()
    check = examine([rows[0], rows[2], rows[3]], as_of=AS_OF)["checks"]["SH-ASS-003"]
    assert not check["evidence"][0]["prior_exact_quality_reviews"]
    assert any(
        x.get("reason") == "EXACT_QUALITY_REVIEW_NOT_COLLECTED"
        for x in check["unperformed"]
        if isinstance(x, dict)
    )


def test_declared_completion_count_is_recomputed_and_boolean_is_not_integer():
    rows = programme_history()
    repin(rows[3], completed_workstreams=True)
    check = examine(rows, as_of=AS_OF)["checks"]["SH-ASS-003"]
    assert check["exceptions"][0]["reason"] == "RECORDED_COUNT_DIFFERS"


def test_screened_defect_without_finding_history_stays_unknown():
    rows = owner_history()
    repin(rows[0], status="SELECTED_DEFECT_REQUIRES_FINDING")
    repin(rows[2], upstream_refs=[reference(rows[0])])
    check = examine([rows[0], rows[2], rows[3]], as_of=AS_OF)["checks"]["SH-ASS-001"]
    assert any(
        x.get("reason") == "SCREENED_DEFECT_FINDING_HISTORY_NOT_COLLECTED"
        for x in check["unperformed"]
        if isinstance(x, dict)
    )
