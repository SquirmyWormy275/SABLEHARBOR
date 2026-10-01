"""Actual ordinary collection proves additional B01 clauses independently of outcomes."""

import hashlib
import json
from copy import deepcopy

import pytest
import test_source_identity_methods as identity_tests

from enterprise.audit_suite import source_workforce_methods as methods
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_identity_methods import CONTRACT_PATH as IDENTITY_CONTRACT


def author_neutral_source(put):
    # Independently authored neutral company originals, all before an audit exists.
    # Match the relationship taxonomy without using real company/canonical names.
    for prefix, total, relationship in [
        ("NEUTRAL-EMP-", 42, "EMPLOYEE"),
        ("NEUTRAL-DIR-", 7, "NONEMPLOYEE_DIRECTOR"),
        ("NEUTRAL-CONTACT-", 9, "PROPOSED_CONTACT"),
        ("NEUTRAL-DELEGATE-", 6, "SERVICE_DELEGATE"),
    ]:
        for n in range(total):
            person = prefix + str(n)
            proposed = relationship in {"PROPOSED_CONTACT", "SERVICE_DELEGATE"}
            put(
                "person-access-history",
                "affiliation_register",
                person,
                {
                    "person_id": person,
                    "relationship_kind": relationship,
                    "included_in_service_boundary": relationship != "PROPOSED_CONTACT",
                    "source_status": "PROPOSED_OFFICE_OCCUPANT"
                    if proposed
                    else "current_employee"
                    if relationship == "EMPLOYEE"
                    else "current_nonemployee_director",
                    "source_titles": [
                        {
                            "title": "Neutral recorded title",
                            "status": "PROPOSED" if proposed else "RECORDED",
                        }
                    ],
                },
                "2027-01-01T00:15:00Z",
            )
    approval = put(
        "eth001conduct",
        "conduct_code",
        "FICTIONAL-LOCAL-APPROVAL",
        {
            "code_id": "NEUTRAL-CODE",
            "real_enterprise_code_approved": False,
        },
        "2027-08-01T09:00:00Z",
    )
    put(
        "eth001conduct",
        "conduct_distribution",
        "SELECTED-ROSTER",
        {
            "code_id": "NEUTRAL-CODE",
            "selected_person_ids": ["neutral-contact-A", "neutral-contact-B"],
            "due_at": "2027-08-02T17:00:00Z",
        },
        "2027-08-01T09:10:00Z",
    )
    for person, late in [("neutral-contact-A", False), ("neutral-contact-B", True)]:
        delivery = put(
            "eth001conduct",
            "conduct_distribution",
            "DISTRIBUTION-" + person,
            {
                "code_id": "NEUTRAL-CODE",
                "recipient_id": person,
                "fictional_approval_original": approval,
                "actual_notice_sent": False,
            },
            "2027-08-01T09:20:00Z",
        )
        put(
            "eth001conduct",
            "selected_attestation",
            "ACK-" + person,
            {
                "subject_id": person,
                "distribution_original": delivery,
                "late_against_selected_due": late,
                "actual_employee_attestation": False,
            },
            "2027-08-03T09:00:00Z" if late else "2027-08-02T09:00:00Z",
        )
    put(
        "eth001conduct",
        "conduct_reconciliation",
        "FINAL",
        {
            "final_state": "SELECTED_ACKS_RETAINED",
            "open_exception_ids": ["NEUTRAL-LATE-ACK"],
            "selected_acknowledgment_count": 2,
            "selected_late_count": 1,
        },
        "2027-08-03T10:00:00Z",
    )

    report = put(
        "supplementalops",
        "workforce_case",
        "ER-2027-REPORT-01",
        {
            "confidential_channel": "local://neutral/protected",
            "case_access": ["neutral-custodian", "neutral-legal"],
        },
        "2027-09-01T09:00:00Z",
    )
    facts = put(
        "supplementalops",
        "workforce_case",
        "ER-2027-FACTS-01",
        {
            "rule_breached": "Separate approval required",
            "substantiated_facts": "Selected denied request",
            "native_dependencies": [report],
        },
        "2027-09-02T09:00:00Z",
    )
    decision = put(
        "supplementalops",
        "workforce_case",
        "ER-2027-CORRECTIVE-DECISION",
        {
            "decision_owner": "neutral-custodian",
            "subject": "neutral-contact-A",
            "decision_target": "2027-09-03T17:00:00Z",
            "sanction": "Selected coaching and local restriction",
            "reporter_adverse_action": False,
            "considerations": {
                "impact": "Denied request",
                "intent": "Mistake",
                "proportionality": "Coaching",
                "protected_reporting": "Reporter protected",
            },
            "native_dependencies": [facts],
        },
        "2027-09-10T09:00:00Z",
    )
    followup = put(
        "supplementalops",
        "workforce_case",
        "ER-2027-FOLLOWUP",
        {
            "coaching_completed": True,
            "case_status": "LOCAL_ACTION_LATE_REVIEW_OPEN",
            "native_dependencies": [decision],
        },
        "2027-09-20T09:00:00Z",
    )
    put(
        "supplementalops",
        "workforce_case",
        "NEUTRAL-PROTECTED-DECISION",
        {
            "decision": "REJECT_ADVERSE_ACTION",
            "action_applied": False,
        },
        "2027-09-04T09:00:00Z",
    )
    put(
        "supplementalops",
        "responsibility_feedback",
        "NEUTRAL-CHECKIN",
        {
            "participant": "neutral-contact-A",
            "manager": "neutral-manager",
            "discussion": {"pressure": "Deadlines do not authorize bypass"},
            "reward_and_pressure_review": "No reward for bypass or report suppression",
            "native_dependencies": [followup],
        },
        "2027-10-01T09:00:00Z",
    )
    put(
        "supplementalops",
        "access_operation",
        "CORRECTIVE-RESTRICTION-SELF",
        {
            "decision": "DENY",
            "returned_bytes": 0,
        },
        "2027-09-10T10:00:00Z",
    )

    common = {
        "requisition_id": "NEUTRAL-REQUISITION",
        "candidate_id": None,
        "background_or_qualification_result": None,
        "qualified_legal_customer_field_applicability": "PENDING_NOT_ASSERTED",
        "actual_candidate_or_employee": False,
        "accepted_people_or_security_delegation": False,
        "actual_assignment_or_access": False,
    }
    put(
        "ppl002",
        "people_requirement_intake",
        "REQUIREMENT-REQUEST",
        {
            **common,
            "requested_inputs": ["SECURITY_TRUST", "LEGAL", "CUSTOMER", "FIELD"],
            "decision": "BLOCK_PENDING_CRITERIA",
        },
        "2027-07-01T09:00:00Z",
    )
    put(
        "ppl002",
        "security_requirement_input",
        "SECURITY-INPUT",
        {
            **common,
            "screening_criteria": "NOT_QUALIFIED_OR_ACCEPTED",
            "clearance": False,
        },
        "2027-07-01T09:05:00Z",
    )
    put(
        "ppl002",
        "people_assignment_gate",
        "NOMINATION",
        {
            **common,
            "decision": "NOMINATION_ATTEMPT",
            "role_nomination_attempted": True,
        },
        "2027-07-01T09:10:00Z",
    )
    put(
        "ppl002",
        "people_assignment_gate",
        "FINAL",
        {
            **common,
            "decision": "BLOCKED",
            "role_status": "UNFILLED_UNASSIGNED",
            "prior_invalid_nomination_preserved": True,
        },
        "2027-07-01T09:20:00Z",
    )

    cycle = "NEUTRAL-CYCLE"
    roster = put(
        "training-history",
        "training_roster",
        "ROSTER",
        {
            "cycle_id": cycle,
            "cohort_count": 2,
            "members": [
                {
                    "person_id": p,
                    "role_id": "ROLE-NEUTRAL",
                    "snapshot_status": "PROPOSED_OFFICE_OCCUPANT",
                }
                for p in ["neutral-contact-A", "neutral-contact-B"]
            ],
        },
        "2027-01-01T00:00:00Z",
    )
    matrix = put(
        "training-history",
        "training_matrix",
        "MATRIX",
        {
            "cycle_id": cycle,
            "courses": [
                {
                    "course_id": "NEUTRAL-BASE",
                    "role_ids": ["ROLE-NEUTRAL"],
                    "title": "Selected neutral course",
                }
            ],
            "due_at": "2027-01-31T17:00:00Z",
            "required_worker_class": "LOCAL_SELECTED_PARTICIPANTS",
            "approval_basis": "LOCAL_EXERCISE_ONLY",
            "approved_by": "neutral-custodian",
            "roster_source": roster,
        },
        "2027-01-01T01:00:00Z",
    )
    for p, late in [("neutral-contact-A", False), ("neutral-contact-B", True)]:
        assignment = put(
            "training-history",
            "training_assignments",
            p,
            {
                "person_id": p,
                "role_id": "ROLE-NEUTRAL",
                "course_id": "NEUTRAL-BASE",
                "cycle_id": cycle,
                "due_at": "2027-01-31T17:00:00Z",
                "matrix_source": matrix,
                "roster_source": roster,
            },
            "2027-01-02T09:00:00Z",
        )
        at = "2027-02-03T10:00:00Z" if late else "2027-01-30T17:00:00Z"
        put(
            "training-history",
            "training_completions",
            p,
            {
                "person_id": p,
                "course_id": "NEUTRAL-BASE",
                "completed_at": at,
                "assignment_source": assignment,
            },
            at,
        )
    first = put(
        "training-history",
        "training_monitoring",
        "MONITOR-1",
        {
            "as_of": "2027-01-31T18:00:00Z",
            "assigned_count": 2,
            "completion_count": 1,
            "overdue_count": 1,
            "late_completed_count": 0,
            "overdue": [{"person_id": "neutral-contact-B", "course_id": "NEUTRAL-BASE"}],
        },
        "2027-01-31T18:00:00Z",
    )
    final = put(
        "training-history",
        "training_monitoring",
        "MONITOR-2",
        {
            "as_of": "2027-02-03T11:00:00Z",
            "assigned_count": 2,
            "completion_count": 2,
            "overdue_count": 0,
            "late_completed_count": 1,
            "overdue": [],
        },
        "2027-02-03T11:00:00Z",
    )
    put(
        "training-history",
        "training_followup",
        "FOLLOWUP",
        {
            "recipients": [{"person_id": "neutral-contact-B", "course_id": "NEUTRAL-BASE"}],
            "sent_by": "neutral-custodian",
            "followup_due_at": "2027-02-03T10:00:00Z",
            "monitoring_source": first,
        },
        "2027-02-01T09:00:00Z",
    )
    put(
        "critical_role",
        "role_scope",
        "SCOPE-APR-2027",
        {
            "role_contacts": [
                {
                    "person_id": "neutral-contact-A",
                    "role_id": "ROLE-NEUTRAL",
                    "contact_status": "PROPOSED_OFFICE_OCCUPANT",
                }
            ],
            "training_roster_source": roster,
        },
        "2027-04-15T09:00:00Z",
    )
    put(
        "critical_role",
        "role_review",
        "REVIEW-APR-2027",
        {
            "reviewed_role_ids": ["ROLE-NEUTRAL"],
            "q1_local_assignment_count": 2,
            "q1_initial_overdue_count": 1,
            "q1_final_overdue_count": 0,
            "q1_late_completion_count": 1,
            "qualification_evidence_status": "NOT_PRESENT_VERIFICATION_PENDING",
            "backup_evidence_status": "NOT_PRESENT_VERIFICATION_PENDING",
            "training_source": {"initial": first, "closeout": final},
        },
        "2027-04-15T10:00:00Z",
    )
    put(
        "critical_role",
        "role_gap",
        "GAP-APR-2027",
        {
            "open_gap_ids": ["NEUTRAL-COMPETENCE-BACKUP-GAP"],
            "training_lateness": "LOCAL_LATE_COMPLETION_RETAINED",
        },
        "2027-04-15T11:00:00Z",
    )
    put(
        "critical_role",
        "role_action",
        "ACTION-APR-2027",
        {
            "action_status": "QUEUED_NOT_APPROVED",
            "required_inputs": ["COMPETENCE", "BACKUP", "CAPACITY"],
            "performance_or_accountability_decision": "UNDETERMINED",
        },
        "2027-04-15T12:00:00Z",
    )
    put(
        "physicalsite",
        "site_authority",
        "ORDER",
        {"detail": {"scope": "neutral cage only"}},
        "2027-09-01T09:00:00Z",
    )
    put(
        "physicalsite",
        "site_zoning",
        "ZONE",
        {"detail": {"zone": "NEUTRAL-CAGE"}},
        "2027-09-01T09:10:00Z",
    )
    put(
        "physicalsite",
        "badge_lifecycle",
        "BADGE",
        {"detail": {"status": "REVOKE_REQUESTED", "role": "fictional token"}},
        "2027-09-02T09:00:00Z",
    )
    put(
        "physicalsite",
        "visitor_access",
        "ENTRY",
        {
            "detail": {
                "authorization": "EXPIRED",
                "controller_entry": "ALLOWED",
                "zone": "NEUTRAL-CAGE",
            }
        },
        "2027-09-03T09:00:00Z",
    )

    catalogue = put(
        "person-access-history",
        "entitlement_catalogue",
        "CORPORATE-LOGICAL",
        {
            "conflicting_rights": [["iam.approve", "iam.provision"]],
        },
        "2027-01-01T00:20:00Z",
    )
    put(
        "person-access-history",
        "meeting_note",
        "NEUTRAL-NOT-AUTHORITY",
        {
            "approved_rights": ["workspace.read"],
            "approved_by": "neutral-approver",
            "provisioner": "neutral-provisioner",
            "subject_id": "P014",
            "decision": "APPROVED",
        },
        "2027-01-01T00:25:00Z",
    )
    approval = put(
        "person-access-history",
        "access_approvals",
        "P014",
        {
            "approved_rights": ["workspace.read"],
            "approved_by": "neutral-approver",
            "provisioner": "neutral-provisioner",
            "subject_id": "P014",
            "decision": "APPROVED",
            "catalogue": catalogue,
        },
        "2027-01-01T00:30:00Z",
    )
    state = {
        "account_id": "P014:application",
        "subject_id": "P014",
        "channel": "application",
        "active": True,
        "rights": ["workspace.read"],
        "credential_epoch": 1,
        "starts": "2027-01-01T01:00:00Z",
        "ends": "2028-01-01T00:00:00Z",
        "review_anchor": "P014",
    }
    active = put(
        "person-access-history",
        "account_application",
        "P014:application",
        {
            "state": state,
            "approval": approval,
        },
        "2027-01-01T01:00:00Z",
    )
    obj = b"Neutral workforce permission object\n"
    original = put(
        "person-access-history",
        "workspace_object",
        "NEUTRAL-WORKSPACE",
        {},
        "2027-01-01T00:45:00Z",
        raw=obj,
    )
    for rid, epoch, decision, at in [
        ("ALLOWED", 1, "ALLOW", "2027-05-01T09:00:00Z"),
        ("STALE", 2, "DENY", "2027-05-01T09:05:00Z"),
    ]:
        put(
            "person-access-history",
            "permission_activity",
            rid,
            {
                "account_id": "P014:application",
                "account_state": active,
                "credential_epoch": epoch,
                "decision_at": at,
                "decision": decision,
                "right": "workspace.read",
                "object_bytes": len(obj),
                "object_sha256": original["sha256"],
                "returned_bytes": len(obj) if decision == "ALLOW" else 0,
                "returned_sha256": original["sha256"] if decision == "ALLOW" else None,
            },
            at,
        )
    revoked = put(
        "person-access-history",
        "account_application",
        "P014:application",
        {
            "state": {**state, "active": False},
            "approval": approval,
        },
        "2028-01-01T00:00:00Z",
        version=2,
    )
    put(
        "person-access-history",
        "permission_activity",
        "ANNUAL-EXPIRY",
        {
            "account_id": "P014:application",
            "account_state": revoked,
            "credential_epoch": 1,
            "decision_at": "2028-01-01T00:01:00Z",
            "decision": "DENY",
            "right": "workspace.read",
            "object_bytes": len(obj),
            "object_sha256": original["sha256"],
            "returned_bytes": 0,
            "returned_sha256": None,
        },
        "2028-01-01T00:01:00Z",
    )
    denominator = put(
        "person-access-history",
        "denominator_snapshot",
        "2027-01",
        {
            "accounts": [{"source": active, "state": state}],
            "registered_subject_ids": ["P014"],
            "cutoff_exclusive": "2027-02-01T00:00:00Z",
            "worker_and_account_counts_are_identical": False,
            "unmodeled_worker_population": "Not established by selected local account census",
        },
        "2027-02-01T00:00:00Z",
    )
    members = [
        {
            "subject_id": "P014",
            "relationship_kind": "EMPLOYEE",
            "accounts": [{"source": active, "state": state}],
        }
    ]
    population = put(
        "person-access-history",
        "periodic_review_population",
        "2027-Q1",
        {
            "members": members,
            "membership_sha256": identity_tests.digest(members),
            "period_end_exclusive": "2027-04-01T00:00:00Z",
            "denominator": denominator,
            "retained_local_review_missing_ids": ["P014"],
        },
        "2027-04-01T01:00:00Z",
    )
    put(
        "person-access-history",
        "periodic_review_decisions",
        "2027-Q1",
        {
            "population": population,
            "wider_estate_reviewed": False,
            "decisions": [
                {
                    "subject_id": "P014",
                    "observed_rights": ["workspace.read"],
                    "remove_rights": [],
                    "removal_confirmation": "NO_REMOVAL_REQUEST",
                }
            ],
        },
        "2027-04-01T02:00:00Z",
    )


@pytest.fixture(scope="module")
def originals(tmp_path_factory):
    return identity_tests.build_originals(tmp_path_factory, author_neutral_source)


def test_all52_exact_task_contracts_and_failure_vs_partial_clauses(originals):
    actual = methods.inspections(originals["records"], as_of=originals["as_of"])
    contracts = methods.task_contracts()
    assert len(actual) == len(contracts) == 52
    assert [t["task_id"] for t in actual] == methods.authored_contracts()["selected_task_ids"]
    selected = json.loads(IDENTITY_CONTRACT.read_text())["selected_task_ids"]
    assert len(selected) == 30
    for task in actual:
        fixed = contracts[task["task_id"]]
        assert (
            task["performed"] == fixed["performed"] and task["unperformed"] == fixed["unperformed"]
        )
        assert {k: task["disposition"][k] for k in ["status", "conclusion"]} in fixed[
            "allowed_dispositions"
        ]
        assert task["observations"] and task["artifact_ids"]
        assert task["result"]["old_audit_outcomes_used"] is False
        if task["task_id"] not in selected:
            assert task["result"]["performed_attributes"]
            assert all(a["unperformed"] for a in task["result"]["performed_attributes"])
            assert not task["result"]["missing_selected_inputs"]
    by = {t["task_id"]: t for t in actual}
    assert by["TASK-SH-ETH-001-corporate-ACTION-H-SANCTIONS"]["disposition"]["conclusion"] == "FAIL"
    assert by["TASK-SH-IAM-002-corporate-CHECK-SOC2:CC6.4"]["disposition"]["conclusion"] == "FAIL"
    assert by["TASK-SH-PPL-002-corporate-IMPLEMENTATION"]["disposition"]["conclusion"] == "FAIL"
    assert by["TASK-SH-TRN-002-corporate-TOE"]["disposition"]["conclusion"] == "FAIL"
    assert by["TASK-SH-TRN-003-corporate-TOD"]["disposition"]["conclusion"] == "LIMITATION"


def test_later_zero_overdue_and_final_block_never_erase_historical_failures(originals):
    history = methods.History(originals["records"], originals["as_of"])
    completions = methods.training_completions(history)[0]["facts"]
    assert len(completions["monitor_tests"][0]["actual_overdue"]) == 1
    assert completions["monitor_tests"][-1]["actual_overdue"] == []
    assert completions["historical_late_pairs"] == [("neutral-contact-B", "NEUTRAL-BASE")]
    screening = methods.screening(history)[1]
    assert screening["exception"] is True
    assert screening["facts"][-1]["role_status"] == "UNFILLED_UNASSIGNED"
    assert methods.sanctions(history)[0]["facts"]["decision_delay_seconds"] > 0


def test_critical_course_completion_does_not_become_competence_or_employment(originals):
    history = methods.History(originals["records"], originals["as_of"])
    capacity = methods.critical(history, purpose="capacity")
    competence = methods.critical(history, purpose="competence")
    assert capacity[0]["attribute"] != competence[0]["attribute"]
    assert capacity[0]["facts"]["role_contacts"][0]["contact_status"] == "PROPOSED_OFFICE_OCCUPANT"
    assert capacity[1]["facts"]["training_count_tests"] and all(
        capacity[1]["facts"]["training_count_tests"].values()
    )
    assert competence[1]["facts"]["course_lateness_is_competence_finding"] is False
    assert "practical capability" in competence[0]["unperformed"]


@pytest.mark.parametrize(
    ("role", "field"),
    [
        ("conduct_reconciliation", "selected_acknowledgment_count"),
        ("training_monitoring", "assigned_count"),
        ("people_assignment_gate", "actual_assignment_or_access"),
    ],
)
def test_resealed_boolean_integer_aliases_or_integer_flags_reject_after_hash_repair(
    originals, role, field
):
    records = deepcopy(originals["records"])
    row = next(
        r
        for r in records
        if r["logical_system"] == role and field in json.loads(r["retained_bytes"])
    )
    bad = False if role == "people_assignment_gate" else True
    if role == "people_assignment_gate":
        bad = 0
    identity_tests.reseal_document(row, lambda d: d.update({field: bad}))
    repair_pointer_closure(records)
    with pytest.raises(ProcedureError, match="Strict"):
        methods.inspections(records, as_of=originals["as_of"])


def test_absent_completion_family_remains_source_specific_unperformed(originals):
    rows = [r for r in originals["records"] if r["logical_family"] != "training-history"]
    actual = {t["task_id"]: t for t in methods.inspections(rows, as_of=originals["as_of"])}
    trn = actual["TASK-SH-TRN-002-corporate-TOE"]
    assert trn["disposition"]["conclusion"] == "LIMITATION"
    assert trn["result"]["missing_selected_inputs"] == ["training/training_assignments"]
    assert actual["TASK-SH-IAM-003-corporate-IMPLEMENTATION"]["disposition"]["conclusion"] == "FAIL"


def repair_pointer_closure(records):
    # Repair every dependent exact native pointer too; fail on the challenged
    # business type, not a stale pointer caused by editing its original bytes.
    hashes = {
        tuple(r["source"][k] for k in methods.identity_methods.NATIVE_ID): r["source"]["sha256"]
        for r in records
    }
    for _ in range(len(records)):
        changed = False
        for original in records:
            if original.get("content_type") != "application/json":
                continue
            body = json.loads(original["retained_bytes"])
            repaired = False

            def walk(value):
                nonlocal repaired
                if isinstance(value, dict):
                    keys = methods.identity_methods.NATIVE_ID
                    if set(keys) <= value.keys() and "sha256" in value:
                        h = hashes.get(tuple(value[k] for k in keys))
                        if h is not None and value["sha256"] != h:
                            value["sha256"] = h
                            repaired = True
                    for child in value.values():
                        walk(child)
                elif isinstance(value, list):
                    for child in value:
                        walk(child)

            walk(body)
            if repaired:
                identity_tests.reseal_document(original, lambda d, body=body: d.update(body))
                hashes[tuple(original["source"][k] for k in methods.identity_methods.NATIVE_ID)] = (
                    original["source"]["sha256"]
                )
                changed = True
        if not changed:
            break
    else:
        raise AssertionError("Neutral pointer closure did not stabilize")


def test_callback_rejects_mutated_task_contract_and_identity_dependency(
    originals, tmp_path, monkeypatch
):
    p = tmp_path / "contract.json"
    p.write_bytes(methods.CONTRACT_PATH.read_bytes() + b" ")
    monkeypatch.setattr(methods, "CONTRACT_PATH", p)
    with pytest.raises(ProcedureError, match="contract pin"):
        methods.inspections(originals["records"], as_of=originals["as_of"])
    monkeypatch.undo()
    monkeypatch.setattr(methods, "IDENTITY_METHOD_SHA256", hashlib.sha256(b"changed").hexdigest())
    with pytest.raises(ProcedureError, match="dependency pin"):
        methods.inspections(originals["records"], as_of=originals["as_of"])


def test_current_workforce_grants_original_object_permission_epochs_and_cutoff_population(
    originals,
):
    history = methods.History(originals["records"], originals["as_of"])
    actual = methods.workforce_access(history)
    assert actual["actual_account_version_count"] == 2
    assert all(g["subject_matches"] and g["approver_distinct"] for g in actual["grant_tests"])
    attempts = {
        a["account_id"] + "/" + a["source"]["record"]: a for a in actual["permission_tests"]
    }
    assert all(
        a["decision_matches"] and a["retained_object_or_empty_denial_matches"]
        for a in attempts.values()
    )
    assert (
        next(a for a in attempts.values() if a["source"]["record"] == "STALE")["recalculated_allow"]
        is False
    )
    month = actual["monthly_denominators"][0]
    assert month["actual_account_subjects"] == ["P014"]
    assert not month["missing_active_accounts"] and not month["unexpected_declared_accounts"]
    assert month["account_join_tests"][0]["date_effective_latest_matches"] is True
    assert month["accounts_equal_people"] is False
    quarter = actual["periodic_reviews"][0]
    assert quarter["membership_digest_matches"] is True
    assert quarter["review_decision_tests"][0]["observed_rights_match"] is True
    assert quarter["retained_local_missing_ids"] == ["P014"]
    assert quarter["historical_missing_ids_erased_by_later_correction"] is False


def test_uncollected_workspace_byte_original_is_not_inferred_from_read_hash(originals):
    rows = [r for r in originals["records"] if r["logical_system"] != "workspace_object"]
    actual = methods.workforce_access(methods.History(rows, originals["as_of"]))
    allowed = next(a for a in actual["permission_tests"] if a["recorded_decision"] == "ALLOW")
    assert allowed["decision_matches"] is True
    assert allowed["retained_object_or_empty_denial_matches"] is None


@pytest.mark.parametrize(
    "case",
    [
        "native_active_integer",
        "snapshot_active_integer",
        "epoch_boolean",
        "byte_boolean",
        "wrong_approval_role",
    ],
)
def test_workforce_strict_states_bytes_and_actual_native_approval_role_after_pointer_repair(
    originals, case
):
    rows = deepcopy(originals["records"])
    if case == "native_active_integer":
        row = next(r for r in rows if r["logical_system"] == "account_application")
        identity_tests.reseal_document(row, lambda d: d["state"].update(active=1))
    elif case == "snapshot_active_integer":
        row = next(r for r in rows if r["logical_system"] == "denominator_snapshot")
        identity_tests.reseal_document(row, lambda d: d["accounts"][0]["state"].update(active=1))
    elif case == "epoch_boolean":
        row = next(r for r in rows if r["logical_system"] == "permission_activity")
        identity_tests.reseal_document(row, lambda d: d.update(credential_epoch=True))
    elif case == "byte_boolean":
        row = next(r for r in rows if r["logical_system"] == "permission_activity")
        identity_tests.reseal_document(row, lambda d: d.update(returned_bytes=False))
    else:
        note = next(r for r in rows if r["logical_system"] == "meeting_note")
        row = next(r for r in rows if r["logical_system"] == "account_application")
        identity_tests.reseal_document(
            row,
            lambda d: d.update(
                approval={k: note["source"][k] for k in methods.identity_methods.CLOCK_ID}
            ),
        )
    repair_pointer_closure(rows)
    with pytest.raises(ProcedureError, match="Strict|native access approval role"):
        methods.inspections(rows, as_of=originals["as_of"])


def test_collected_relationship_counts_keep_directors_former_and_proposed_separate(originals):
    history = methods.History(originals["records"], originals["as_of"])
    affiliations = methods.workforce_access(history)["affiliation_context"]
    counts = affiliations["recorded_relationship_counts"]
    assert counts["EMPLOYEE"] == 44 and counts["NONEMPLOYEE_DIRECTOR"] == 7
    assert counts["FORMER_EMPLOYEE"] == 1
    assert len(affiliations["canonical_people"]) == 52
    assert len(affiliations["proposed_office_contacts"]) == 15
    assert "P008" in affiliations["canonical_people"]
    assert affiliations["people"]["P008"]["service_eligible"] is False
    assert not set(affiliations["canonical_people"]) & set(affiliations["proposed_office_contacts"])
    assert affiliations["appointments_or_planning_positions_inferred"] is False
