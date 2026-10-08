"""All 52 B01 tasks examined from retained ordinary company collections.

Each task keeps its authored clause, actual selected observations and unperformed
attributes. Source examinations provide no professional PASS or whole-enterprise
population assertion. Restricted archive witnesses are never native authority.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from . import source_identity_methods as identity_methods
from . import source_native_operating_methods as native_operating
from .company_store import _time
from .fresh_sec003_procedure import require
from .inference import _json
from .source_identity_methods import History, MissingOriginal, count, custody, flag, tokens
from .store import digest

CONTRACT_PATH = Path(__file__).with_name("source_workforce_method_contracts_v1.json")
CONTRACT_SHA256 = "16cae845f9418b4c7b51d9933eaf0d332bb4c777469b9c671c6069cf67208bab"
IDENTITY_METHOD_SHA256 = "502f2c229ff5dc709291dc0e244084572c658f78410bf7d43dc9ead58f7acd6d"
retained_inputs = native_operating.retained_inputs


def authored_contracts():
    require(
        hashlib.sha256(Path(identity_methods.__file__).read_bytes()).hexdigest()
        == IDENTITY_METHOD_SHA256,
        "Collected identity dependency pin differs",
    )
    raw = CONTRACT_PATH.read_bytes()
    require(
        hashlib.sha256(raw).hexdigest() == CONTRACT_SHA256, "Workforce task contract pin differs"
    )
    value = _json(raw)
    old = identity_methods.authored_contracts()
    require(
        value["schema"] == "SH_COLLECTED_WORKFORCE_METHOD_CONTRACTS_V1"
        and len(value["selected_task_ids"]) == len(set(value["selected_task_ids"])) == 52
        and len(value["additional_task_ids"]) == len(set(value["additional_task_ids"])) == 22
        and set(value["additional_task_ids"]) == set(value["tasks"])
        and set(value["selected_task_ids"])
        == set(old["selected_task_ids"]) | set(value["additional_task_ids"])
        and not set(old["selected_task_ids"]) & set(value["additional_task_ids"]),
        "Exact complete B01 task membership required",
    )
    return value


def selected(history, component, role, *, needed=True):
    rows = history.selected(component, role)
    if needed and not rows:
        raise MissingOriginal(component + "/" + role)
    return rows


def pointer(history, row, value):
    target, state = history.resolve(row, value)
    return target, state


def attribute(name, performed, facts, *, limit=None, exception=False):
    return {
        "attribute": name,
        "performed": performed,
        "facts": facts,
        "unperformed": limit,
        "exception": exception,
    }


def conduct(history):
    approval = history.exact("conduct", "conduct_code", "FICTIONAL-LOCAL-APPROVAL")
    roster = history.exact("conduct", "conduct_distribution", "SELECTED-ROSTER")
    p, r = approval["document"], roster["document"]
    flag(p["real_enterprise_code_approved"], "real enterprise code approval")
    ids = tokens(r["selected_person_ids"], "selected conduct recipient identities")
    due = _time(r["due_at"])
    distribution = selected(history, "conduct", "conduct_distribution")
    attestations = selected(history, "conduct", "selected_attestation", needed=False)
    tests = []
    for person in sorted(ids):
        delivery = [d for d in distribution if d["document"].get("recipient_id") == person]
        acks = [a for a in attestations if a["document"]["subject_id"] == person]
        require(
            len(delivery) <= 1 and len(acks) <= 1, "Distinct selected conduct occurrences required"
        )
        actual = {
            "person_id": person,
            "delivery_present": bool(delivery),
            "ack_present": bool(acks),
        }
        if delivery:
            d = delivery[0]
            target, state = pointer(history, d, d["document"]["fictional_approval_original"])
            actual.update(
                delivery_source=custody(d),
                approval_join=state,
                code_matches=d["document"]["code_id"] == r["code_id"] == p["code_id"],
                approval_available=target is approval and state == "EXACT_AVAILABLE_NATIVE_JOIN",
                actual_notice_sent=flag(
                    d["document"]["actual_notice_sent"], "actual conduct notice"
                ),
            )
        if acks:
            a = acks[0]
            target, state = pointer(history, a, a["document"]["distribution_original"])
            late = _time(a["source"]["event_at"]) > due
            actual.update(
                acknowledgment_source=custody(a),
                distribution_join=state,
                delivery_original_matches=bool(delivery) and target is delivery[0],
                due_at=due,
                late=late,
                declared_lateness_matches=flag(
                    a["document"]["late_against_selected_due"], "conduct lateness"
                )
                == late,
                actual_employee_attestation=flag(
                    a["document"]["actual_employee_attestation"], "actual employee attestation"
                ),
            )
        tests.append(actual)
    missing = [t["person_id"] for t in tests if not t["delivery_present"] or not t["ack_present"]]
    late = [t["person_id"] for t in tests if t.get("late")]
    reconciliations = []
    for row in selected(history, "conduct", "conduct_reconciliation"):
        d = row["document"]
        item = {
            "source": custody(row),
            "final_state": d.get("final_state"),
            "open_exception_ids": d.get("open_exception_ids", []),
        }
        if "selected_acknowledgment_count" in d:
            seen = [
                a
                for a in attestations
                if _time(a["source"]["available_at"]) <= _time(row["source"]["event_at"])
            ]
            item["count_matches_actual_available_acks"] = count(
                d["selected_acknowledgment_count"], "conduct acknowledgments"
            ) == len(seen)
            item["late_count_matches_actual_acks"] = count(
                d["selected_late_count"], "late conduct acknowledgments"
            ) == sum(_time(a["source"]["event_at"]) > due for a in seen)
        reconciliations.append(item)
    return [
        attribute(
            "approval_and_effective_distribution",
            "Join selected approval and code IDs to actual delivery originals.",
            {
                "approval": custody(approval),
                "real_enterprise_code_approved": p["real_enterprise_code_approved"],
                "recipient_tests": tests,
            },
            limit=(
                "This fictional selected code approval is not an approved whole-company "
                "conduct policy or an actual employee signature."
            ),
        ),
        attribute(
            "recipient_denominator_and_due_acknowledgments",
            (
                "Recompute selected recipient delivery/acknowledgment availability, due "
                "time and lateness."
            ),
            {
                "selected_ids": sorted(ids),
                "missing_ids": missing,
                "historical_late_ids": late,
                "reconciliations": reconciliations,
            },
            limit=(
                "Two selected scenario identities do not establish the onboarding/annual "
                "eligible workforce denominator or actual notices."
            ),
            exception=bool(missing or late)
            or any(
                not x.get("count_matches_actual_available_acks", True)
                or not x.get("late_count_matches_actual_acks", True)
                for x in reconciliations
            ),
        ),
    ]


def sanctions(history):
    report = history.exact("supplemental", "workforce_case", "ER-2027-REPORT-01")
    facts = history.exact("supplemental", "workforce_case", "ER-2027-FACTS-01")
    decision = history.exact("supplemental", "workforce_case", "ER-2027-CORRECTIVE-DECISION")
    followup = history.exact("supplemental", "workforce_case", "ER-2027-FOLLOWUP")
    d, f, r = decision["document"], facts["document"], report["document"]
    require(
        all(
            isinstance(d["considerations"].get(k), str) and d["considerations"][k]
            for k in ("impact", "intent", "proportionality", "protected_reporting")
        ),
        "Reasoned selected sanction considerations required",
    )
    delay = (
        datetime.fromisoformat(_time(decision["source"]["event_at"]))
        - datetime.fromisoformat(_time(d["decision_target"]))
    ).total_seconds()
    protections = []
    for row in selected(history, "supplemental", "workforce_case"):
        x = row["document"]
        if "action_applied" in x:
            protections.append(
                {
                    "source": custody(row),
                    "decision": x["decision"],
                    "action_applied": flag(x["action_applied"], "reporter adverse action"),
                }
            )
    dependency_states = [
        j for j in history.joins if j["from"]["system"] == report["source"]["system"]
    ]
    feedback = [
        {
            "source": custody(row),
            "participant": row["document"]["participant"],
            "manager": row["document"]["manager"],
            "discussion": row["document"]["discussion"],
            "reward_and_pressure_review": row["document"]["reward_and_pressure_review"],
        }
        for row in selected(history, "supplemental", "responsibility_feedback", needed=False)
    ]
    restriction = [
        {"source": custody(row), "recorded": row["document"]}
        for row in selected(history, "supplemental", "access_operation", needed=False)
        if row["source"]["record"].startswith("CORRECTIVE-RESTRICTION")
    ]
    return [
        attribute(
            "substantiated_case_and_reasoned_decision",
            (
                "Trace separately collected protected report, investigator facts, "
                "sanction rationale and decision deadline."
            ),
            {
                "report": custody(report),
                "facts": custody(facts),
                "decision": custody(decision),
                "rule": f["rule_breached"],
                "substantiated_facts": f["substantiated_facts"],
                "sanction": d["sanction"],
                "considerations": d["considerations"],
                "decision_delay_seconds": max(0, delay),
                "decision_owner_distinct_from_subject": d["decision_owner"] != d["subject"],
                "reporter_adverse_action": flag(
                    d["reporter_adverse_action"], "sanction reporter adverse action"
                ),
                "dependency_states": dependency_states,
            },
            limit=(
                "Reasonableness and applicability of actual legal sanctions and the "
                "complete case population require qualified acceptance; a local source "
                "record does not establish that acceptance."
            ),
            exception=delay > 0 or d["reporter_adverse_action"],
        ),
        attribute(
            "protected_reporting_enforcement_and_feedback",
            (
                "Inspect confidential routing/access, preserved adverse proposals, "
                "separate protective decisions, corrective follow-up and responsibility "
                "feedback."
            ),
            {
                "channel": r["confidential_channel"],
                "case_access": sorted(tokens(r["case_access"], "protected case access")),
                "protections": protections,
                "followup": custody(followup),
                "coaching_completed": flag(
                    followup["document"]["coaching_completed"], "coaching completion"
                ),
                "case_status": followup["document"]["case_status"],
                "restriction_observations": restriction,
                "responsibility_feedback": feedback,
            },
            limit=(
                "Technical restriction records are selected local marker histories. "
                "Complete enforcement, performance review cadence, sanctions consistency "
                "and reporter protection across the enterprise remain unproved."
            ),
            exception=any(p["action_applied"] for p in protections),
        ),
    ]


def screening(history):
    requests = selected(history, "screening", "people_requirement_intake")
    inputs = selected(history, "screening", "security_requirement_input")
    gates = selected(history, "screening", "people_assignment_gate")
    keys = {r["document"]["requisition_id"] for r in requests + inputs + gates}
    require(len(keys) == 1, "One exact selected screening requisition required")
    tests = []
    for row in sorted(gates, key=lambda r: r["source"]["event_at"]):
        d = row["document"]
        actual = {
            "source": custody(row),
            "recorded_decision": d.get("decision"),
            "role_status": d.get("role_status"),
            "candidate_id": d["candidate_id"],
            "screening_result": d["background_or_qualification_result"],
            "qualified_applicability": d["qualified_legal_customer_field_applicability"],
        }
        for key in (
            "actual_candidate_or_employee",
            "accepted_people_or_security_delegation",
            "actual_assignment_or_access",
            "role_nomination_attempted",
            "prior_invalid_nomination_preserved",
        ):
            if key in d:
                actual[key] = flag(d[key], "screening " + key)
        tests.append(actual)
    return [
        attribute(
            "role_jurisdiction_requirements_before_assignment",
            (
                "Inspect selected People request and security criteria input before "
                "local assignment-gate states."
            ),
            {
                "requisition": next(iter(keys)),
                "requirement_requests": [
                    {
                        "source": custody(r),
                        "requested_inputs": r["document"].get("requested_inputs"),
                        "decision": r["document"].get("decision"),
                    }
                    for r in requests
                ],
                "security_inputs": [
                    {
                        "source": custody(r),
                        "criteria": r["document"]["screening_criteria"],
                        "clearance": flag(r["document"]["clearance"], "screening clearance"),
                    }
                    for r in inputs
                ],
            },
            limit=(
                "Qualified role/jurisdiction/customer/legal screening applicability and "
                "an approved permitted-checks design remain pending; security input is "
                "not clearance."
            ),
        ),
        attribute(
            "pending_gate_and_preserved_invalid_nomination",
            (
                "Retain actual assignment gate chronology and any attempted nomination "
                "independently of later blocking/withdrawal."
            ),
            tests,
            limit=(
                "No selected candidate, actual permitted screening/qualification result "
                "or dated authorized exception proves completed screening before "
                "sensitive access; a blocked gate is not a performed check."
            ),
            exception=any(
                t.get("role_nomination_attempted") or t.get("actual_assignment_or_access")
                for t in tests
            ),
        ),
    ]


def training_matrix(history):
    rosters = selected(history, "training", "training_roster")
    matrices = selected(history, "training", "training_matrix")
    assignments = selected(history, "training", "training_assignments")
    require(len(rosters) == len(matrices) == 1, "One selected training cycle required")
    roster, matrix = rosters[0], matrices[0]
    r, m = roster["document"], matrix["document"]
    people = [x["person_id"] for x in r["members"]]
    require(
        len(people) == len(set(people)) == count(r["cohort_count"], "training cohort"),
        "Distinct actual training roster count differs",
    )
    course_ids = [c["course_id"] for c in m["courses"]]
    require(
        len(course_ids) == len(set(course_ids)), "Distinct selected course definitions required"
    )
    expected = {
        (p["person_id"], c["course_id"])
        for p in r["members"]
        for c in m["courses"]
        if p["role_id"] in tokens(c["role_ids"], "course eligible roles")
    }
    observed = [(a["document"]["person_id"], a["document"]["course_id"]) for a in assignments]
    require(len(observed) == len(set(observed)), "Duplicate actual training assignment")
    tests = [
        {
            "source": custody(a),
            "person_id": a["document"]["person_id"],
            "course_id": a["document"]["course_id"],
            "role_matches_roster": any(
                p["person_id"] == a["document"]["person_id"]
                and p["role_id"] == a["document"]["role_id"]
                for p in r["members"]
            ),
            "due_matches_matrix": _time(a["document"]["due_at"]) == _time(m["due_at"]),
            "assignment_available_before_due": _time(a["source"]["available_at"])
            <= _time(a["document"]["due_at"]),
        }
        for a in assignments
    ]
    return [
        attribute(
            "scoped_class_role_course_assignment",
            (
                "Recompute declared roster role-to-course cross-product and actual "
                "assignment membership/due dates."
            ),
            {
                "roster": custody(roster),
                "matrix": custody(matrix),
                "recorded_worker_class": m["required_worker_class"],
                "approval_basis": m["approval_basis"],
                "expected_pairs": sorted(expected),
                "missing_pairs": sorted(expected - set(observed)),
                "unexpected_pairs": sorted(set(observed) - expected),
                "assignment_tests": tests,
                "roster_member_statuses": r["members"],
            },
            limit=(
                "Explicit local cohort/course rules do not establish approved corporate "
                "training by employee/contractor class; proposed contacts are not "
                "appointed employees."
            ),
            exception=set(observed) != expected
            or any(
                not t["role_matches_roster"]
                or not t["due_matches_matrix"]
                or not t["assignment_available_before_due"]
                for t in tests
            ),
        ),
        attribute(
            "course_version_cadence_and_competency_conditions",
            (
                "Inspect actual selected course definitions, deadline, approval basis "
                "and available native dependency status."
            ),
            {
                "courses": m["courses"],
                "due_at": m["due_at"],
                "approved_by": m["approved_by"],
                "cycle": m["cycle_id"],
            },
            limit=(
                "Content/version approvals, onboarding/change triggers, refresher "
                "cadence and competency assessment criteria across "
                "conduct/security/privacy/incident curricula remain unproved; titles and "
                "course IDs do not establish content coverage."
            ),
        ),
    ]


def training_completions(history):
    assignments = selected(history, "training", "training_assignments")
    completions = selected(history, "training", "training_completions", needed=False)
    monitors = selected(history, "training", "training_monitoring")
    assigned = {(a["document"]["person_id"], a["document"]["course_id"]): a for a in assignments}
    require(len(assigned) == len(assignments), "Distinct actual assigned learner/course required")
    done = {}
    for row in completions:
        d = row["document"]
        key = (d["person_id"], d["course_id"])
        require(key not in done, "Completion version requires explicit disposition")
        require(
            _time(d["completed_at"]) == _time(row["source"]["event_at"]),
            "Completion event/body clocks differ",
        )
        done[key] = row
    monitors_test = []
    for row in sorted(monitors, key=lambda r: r["source"]["event_at"]):
        d = row["document"]
        at = _time(d["as_of"])
        require(at <= _time(row["source"]["event_at"]), "Training monitor uses future cutoff")
        available_assignments = {
            k: a for k, a in assigned.items() if _time(a["source"]["available_at"]) <= at
        }
        available_done = {
            k: c
            for k, c in done.items()
            if k in available_assignments and _time(c["source"]["available_at"]) <= at
        }
        overdue = {
            k
            for k, a in available_assignments.items()
            if _time(a["document"]["due_at"]) < at and k not in available_done
        }
        late = {
            k
            for k, c in available_done.items()
            if _time(c["document"]["completed_at"]) > _time(assigned[k]["document"]["due_at"])
        }
        declared_overdue = {(x["person_id"], x["course_id"]) for x in d["overdue"]}
        counts_match = (
            count(d["assigned_count"], "monitor assigned count") == len(available_assignments)
            and count(d["completion_count"], "monitor completion count") == len(available_done)
            and count(d["overdue_count"], "monitor overdue count") == len(overdue)
            and count(d["late_completed_count"], "monitor late completion count") == len(late)
        )
        monitors_test.append(
            {
                "source": custody(row),
                "as_of": at,
                "actual_assigned": len(available_assignments),
                "actual_available_completed": len(available_done),
                "actual_overdue": sorted(overdue),
                "historical_late_completions": sorted(late),
                "counts_match": counts_match,
                "overdue_members_match": overdue == declared_overdue,
            }
        )
    followups = [
        {
            "source": custody(row),
            "recipients": [(x["person_id"], x["course_id"]) for x in row["document"]["recipients"]],
            "sent_by": row["document"]["sent_by"],
            "followup_due_at": row["document"]["followup_due_at"],
        }
        for row in selected(history, "training", "training_followup", needed=False)
    ]
    late_all = [
        k
        for k, c in done.items()
        if k in assigned
        and _time(c["document"]["completed_at"]) > _time(assigned[k]["document"]["due_at"])
    ]
    return [
        attribute(
            "available_completions_and_overdue_checkpoints",
            (
                "Recompute each collected monitor from actual available "
                "assignments/completion bytes and original due time."
            ),
            {
                "monitor_tests": monitors_test,
                "historical_late_pairs": sorted(late_all),
                "unexpected_completion_pairs": sorted(set(done) - set(assigned)),
                "later_completion_erases_historical_delay": False,
            },
            limit=(
                "Only the selected January cycle is established; complete monthly "
                "lifecycle/LMS denominators and ordinary whole-enterprise training "
                "records remain unproved."
            ),
            exception=bool(late_all)
            or bool(set(done) - set(assigned))
            or any(not t["counts_match"] or not t["overdue_members_match"] for t in monitors_test),
        ),
        attribute(
            "overdue_followup_manager_escalation_and_exceptions",
            (
                "Inspect actual selected overdue recipient follow-up without inferring "
                "manager delivery or approved exceptions."
            ),
            {"followups": followups, "completion_sources": [custody(r) for r in completions]},
            limit=(
                "Manager notifications, persistent-gap escalation, formally approved "
                "exceptions and training effectiveness are not established by the local "
                "requested-action record."
            ),
        ),
    ]


def critical(history, *, purpose):
    scope = history.exact("critical", "role_scope", "SCOPE-APR-2027")
    review = history.exact("critical", "role_review", "REVIEW-APR-2027")
    gap = history.exact("critical", "role_gap", "GAP-APR-2027")
    action = history.exact("critical", "role_action", "ACTION-APR-2027")
    s, r, g, a = (x["document"] for x in (scope, review, gap, action))
    roles = tokens(r["reviewed_role_ids"], "critical reviewed roles")
    declared = {x["role_id"] for x in s["role_contacts"]}
    gaps = tokens(g["open_gap_ids"], "critical open gaps")
    for key in (
        "q1_local_assignment_count",
        "q1_initial_overdue_count",
        "q1_final_overdue_count",
        "q1_late_completion_count",
    ):
        count(r[key], key)
    training_result = None
    try:
        training_result = training_completions(history)[0]["facts"]
    except MissingOriginal:
        pass
    recalculation = {}
    if training_result:
        checkpoints = training_result["monitor_tests"]
        recalculation = {
            "assignment_count_matches": r["q1_local_assignment_count"]
            == checkpoints[0]["actual_assigned"],
            "initial_overdue_matches": r["q1_initial_overdue_count"]
            == len(checkpoints[0]["actual_overdue"]),
            "final_overdue_matches": r["q1_final_overdue_count"]
            == len(checkpoints[-1]["actual_overdue"]),
            "late_completion_count_matches": r["q1_late_completion_count"]
            == len(training_result["historical_late_pairs"]),
        }
    if purpose == "capacity":
        label = "critical_workload_vacancy_deputy_and_handover"
        performed = (
            "Join selected proposed critical-role contacts to reviewed roles, open "
            "competence/backup gaps and queued verification inputs."
        )
        limit = (
            "Workload/capacity measurements, appointed primary/deputy availability, "
            "accepted backup competence, practical handover tests and semiannual "
            "enterprise coverage are unperformed; planning occupancy and local delegated "
            "service scope cannot create employees."
        )
    else:
        label = "role_specific_qualification_practical_competence_and_remedy"
        performed = (
            "Separate selected course completion from critical-role qualification/backup "
            "evidence and inspect pending gap/remedy conditions."
        )
        limit = (
            "Role-specific qualification originals, licenses/certifications or practical "
            "capability tests and completed remedial training/supervision/backup "
            "verification remain unproved; late course completion is not a competence "
            "finding."
        )
    return [
        attribute(
            label,
            performed,
            {
                "scope": custody(scope),
                "role_contacts": s["role_contacts"],
                "reviewed_roles": sorted(roles),
                "scoped_roles_match": roles == declared,
                "qualification_evidence_status": r["qualification_evidence_status"],
                "backup_evidence_status": r["backup_evidence_status"],
                "gap_source": custody(gap),
                "open_gap_ids": sorted(gaps),
                "action_source": custody(action),
                "action_status": a["action_status"],
                "required_inputs": a["required_inputs"],
                "recorded_performance_decision": a["performance_or_accountability_decision"],
            },
            limit=limit,
            exception=roles != declared,
        ),
        attribute(
            "training_history_context_without_capability_inference",
            (
                "Recalculate the critical review's selected training counts against "
                "ordinary collected training originals where present."
            ),
            {
                "review": custody(review),
                "training_count_tests": recalculation,
                "training_originals_available": training_result is not None,
                "training_lateness": g["training_lateness"],
                "course_lateness_is_competence_finding": False,
            },
            limit=(
                "Missing training originals remain untested. A queued action, local "
                "course completion, or role contact title does not establish competence, "
                "accepted succession or accountability action."
            ),
            exception=any(not x for x in recalculation.values()),
        ),
    ]


def physical_rights(history):
    badges = selected(history, "physical", "badge_lifecycle")
    visits = selected(history, "physical", "visitor_access")
    authority = selected(history, "physical", "site_authority")
    zones = selected(history, "physical", "site_zoning")
    tests = []
    latest = {}
    for row in sorted(badges, key=lambda r: r["source"]["event_at"]):
        latest[row["source"]["record"]] = row
    for row in visits:
        d = row["document"]["detail"]
        bad = d.get("authorization") == "EXPIRED" and d.get("controller_entry") == "ALLOWED"
        tests.append(
            {
                "source": custody(row),
                "recorded_detail": d,
                "expired_authorization_controller_allows": bad,
            }
        )
    exceptions = [
        {"source": custody(row), "detail": row["document"]["detail"]}
        for row in selected(history, "physical", "site_exception", needed=False)
    ]
    return [
        attribute(
            "physical_credential_site_zone_and_actual_entry",
            (
                "Inspect selected site delegation/zoning, dated badge lifecycle and "
                "actual recorded visitor/controller detail separately from logical "
                "identity grants."
            ),
            {
                "site_authorities": [
                    {"source": custody(r), "detail": r["document"]["detail"]} for r in authority
                ],
                "zones": [{"source": custody(r), "detail": r["document"]["detail"]} for r in zones],
                "latest_badge_states": [
                    {"source": custody(r), "detail": r["document"]["detail"]}
                    for r in latest.values()
                ],
                "entry_tests": tests,
                "historical_exceptions": exceptions,
            },
            limit=(
                "Selected fictional cage tokens cannot be joined to employee "
                "duty/approval or full provider perimeter solely by a similar name. "
                "Complete physical credential population, dated owner approval, "
                "conflicts, controller enforcement and closure across sites remain "
                "unproved."
            ),
            exception=any(x["expired_authorization_controller_allows"] for x in tests),
        ),
    ]


def workforce_access(history):
    """Recalculate collected local workforce account/lease operations, not employment."""
    accounts = [
        r
        for r in history.selected("workforce")
        if r["logical_system"].startswith("account_") and "state" in r["document"]
    ]
    if not accounts:
        raise MissingOriginal("workforce actual account states")
    affiliations = identity_methods.workforce_context(history)
    catalogue = history.exact("workforce", "entitlement_catalogue", "CORPORATE-LOGICAL")
    states, grant_tests, permission_tests, monthly, quarters = {}, [], [], [], []

    def checked_state(st):
        require(isinstance(st, dict), "Actual account state object required")
        flag(st["active"], "account active state")
        require(
            type(st["credential_epoch"]) is int and st["credential_epoch"] > 0,
            "Strict positive account credential epoch required",
        )
        require(
            all(
                isinstance(st.get(k), str) and st[k]
                for k in ("account_id", "subject_id", "channel")
            ),
            "Explicit account, subject and channel identities required",
        )
        tokens(st["rights"], "actual account rights")
        require(_time(st["starts"]) < _time(st["ends"]), "Account operating interval differs")

    for row in accounts:
        d, st = row["document"], row["document"]["state"]
        checked_state(st)
        rights = tokens(st["rights"], "actual account rights")
        require(
            st["account_id"] == row["source"]["record"],
            "Native account ID differs from actual account state",
        )
        require(
            row["logical_system"] == "account_" + st["channel"],
            "Actual native account channel role differs",
        )
        states[identity_methods.identity(row["source"])] = st
        if "approval" in d:
            approval, state = pointer(history, row, d["approval"])
            facts = {
                "account": custody(row),
                "subject_id": st["subject_id"],
                "approval_join": state,
            }
            if approval is not None:
                require(
                    approval["component"] == "workforce"
                    and approval["logical_system"] == "access_approvals",
                    "Actual native access approval role required",
                )
                a = approval["document"]
                approved = tokens(a["approved_rights"], "actual approved rights")
                facts.update(
                    approval=custody(approval),
                    subject_matches=a["subject_id"] == st["subject_id"],
                    excess_rights=sorted(rights - approved),
                    missing_rights=sorted(approved - rights),
                    approver_distinct=a["approved_by"] != a["provisioner"],
                    conflicts=[
                        pair
                        for pair in catalogue["document"]["conflicting_rights"]
                        if tokens(pair, "conflicting logical rights") <= rights
                    ],
                    decision=a["decision"],
                )
            grant_tests.append(facts)

    def effective_accounts(cutoff):
        latest = {}
        for account in accounts:
            if _time(account["source"]["available_at"]) >= cutoff:
                continue
            aid = account["source"]["record"]
            if aid not in latest or account["source"]["version"] > latest[aid]["source"]["version"]:
                latest[aid] = account
        return {
            aid: account
            for aid, account in latest.items()
            if account["document"]["state"]["active"]
            and _time(account["document"]["state"]["starts"])
            < cutoff
            <= _time(account["document"]["state"]["ends"])
        }

    def member_account(row, declared, cutoff, active, subject=None):
        checked_state(declared["state"])
        target, joined = pointer(history, row, declared["source"])
        if target is not None:
            require(
                identity_methods.identity(target["source"]) in states,
                "Actual native account role required for population member",
            )
            require(
                target["source"]["record"] == declared["state"]["account_id"],
                "Population member account differs from native account ID",
            )
        aid = declared["state"]["account_id"]
        latest_matches = target is not None and target is active.get(aid)
        subject_matches = subject is None or declared["state"]["subject_id"] == subject
        available = joined == "EXACT_AVAILABLE_NATIVE_JOIN"
        state_matches = (
            available
            and latest_matches
            and subject_matches
            and target["document"]["state"] == declared["state"]
        )
        return target, {
            "account_id": aid,
            "native_join": joined,
            "actual_state_matches": state_matches,
            "date_effective_latest_matches": latest_matches,
            "available_at_population_occurrence": available,
            "available_before_period_cutoff": target is not None
            and _time(target["source"]["available_at"]) < cutoff,
            "subject_matches_member": subject_matches,
        }

    objects = selected(history, "workforce", "workspace_object", needed=False)
    require(len(objects) <= 1, "One exact selected workforce workspace object required")
    for row in selected(history, "workforce", "permission_activity", needed=False):
        d = row["document"]
        require(
            type(d["credential_epoch"]) is int and d["credential_epoch"] > 0,
            "Strict positive attempted credential epoch required",
        )
        n = count(d["returned_bytes"], "permission returned bytes")
        count(d["object_bytes"], "permission object bytes")
        require(
            d["decision"] in {"ALLOW", "DENY"}, "Explicit workforce permission decision required"
        )
        require(
            _time(d["decision_at"]) <= _time(row["source"]["event_at"]),
            "Workforce permission uses future decision time",
        )
        target, state = pointer(history, row, d["account_state"])
        permitted = None
        if target is not None and state == "EXACT_AVAILABLE_NATIVE_JOIN":
            require(
                identity_methods.identity(target["source"]) in states,
                "Actual native account role required for permission decision",
            )
            st = target["document"]["state"]
            require(
                st["account_id"] == d["account_id"], "Attempt account differs from its native state"
            )
            permitted = (
                st["active"]
                and st["credential_epoch"] == d["credential_epoch"]
                and _time(st["starts"]) <= _time(d["decision_at"]) < _time(st["ends"])
                and d["right"] in st["rights"]
            )
        exact_bytes = n == 0 and d["returned_sha256"] is None if d["decision"] == "DENY" else None
        if d["decision"] == "ALLOW" and objects:
            original = objects[0]
            exact_bytes = (
                n == len(original["retained_bytes"]) == d["object_bytes"]
                and d["returned_sha256"] == d["object_sha256"] == original["source"]["sha256"]
            )
        permission_tests.append(
            {
                "source": custody(row),
                "account_id": d["account_id"],
                "right": d["right"],
                "attempted_epoch": d["credential_epoch"],
                "decision_at": d["decision_at"],
                "recorded_decision": d["decision"],
                "account_join": state,
                "recalculated_allow": permitted,
                "decision_matches": None
                if permitted is None
                else permitted == (d["decision"] == "ALLOW"),
                "retained_object_or_empty_denial_matches": exact_bytes,
                "actual_live_corporate_authorization_reperformed": False,
            }
        )
    for row in selected(history, "workforce", "denominator_snapshot", needed=False):
        d = row["document"]
        cutoff = _time(d["cutoff_exclusive"])
        require(
            cutoff <= _time(row["source"]["event_at"]), "Denominator uses future operating state"
        )
        flag(d["worker_and_account_counts_are_identical"], "worker/account population identity")
        active = effective_accounts(cutoff)
        declared = {a["state"]["account_id"]: a for a in d["accounts"]}
        require(len(declared) == len(d["accounts"]), "Distinct denominator accounts required")
        join_tests = []
        for a in declared.values():
            _, tests = member_account(row, a, cutoff, active)
            join_tests.append(tests)
        observed_subjects = sorted({r["document"]["state"]["subject_id"] for r in active.values()})
        unmatched = sorted(
            {
                r["document"]["state"]["subject_id"]
                for r in active.values()
                if r["document"]["state"]["review_anchor"] is None
            }
        )
        monthly.append(
            {
                "source": custody(row),
                "cutoff_exclusive": cutoff,
                "declared_registered_subjects": sorted(
                    tokens(d["registered_subject_ids"], "declared registered subjects")
                ),
                "actual_account_subjects": observed_subjects,
                "unmatched_review_subjects": unmatched,
                "missing_active_accounts": sorted(set(active) - set(declared)),
                "unexpected_declared_accounts": sorted(set(declared) - set(active)),
                "account_join_tests": join_tests,
                "unmodeled_worker_population": d["unmodeled_worker_population"],
                "accounts_equal_people": d["worker_and_account_counts_are_identical"],
            }
        )
    for row in selected(history, "workforce", "periodic_review_population", needed=False):
        d = row["document"]
        cutoff = _time(d["period_end_exclusive"])
        require(cutoff <= _time(row["source"]["event_at"]), "Quarter population uses future cutoff")
        active = effective_accounts(cutoff)
        subject_ids = [m["subject_id"] for m in d["members"]]
        require(
            len(subject_ids) == len(set(subject_ids)),
            "Distinct actual periodic review subjects required",
        )
        found, actual_members, account_ids = [], {}, set()
        for member in d["members"]:
            tested, actual_rights = [], set()
            for a in member["accounts"]:
                target, tests = member_account(row, a, cutoff, active, member["subject_id"])
                require(
                    tests["account_id"] not in account_ids, "Distinct quarterly accounts required"
                )
                account_ids.add(tests["account_id"])
                found.append({"subject_id": member["subject_id"], **tests})
                tested.append(tests["actual_state_matches"])
                if tests["actual_state_matches"]:
                    actual_rights.update(
                        tokens(target["document"]["state"]["rights"], "native review rights")
                    )
            actual_members[member["subject_id"]] = {
                "all_accounts_supported": bool(tested) and all(tested),
                "actual_native_rights": actual_rights,
            }
        decision_rows = [
            r
            for r in selected(history, "workforce", "periodic_review_decisions", needed=False)
            if r["source"]["record"] == row["source"]["record"]
        ]
        decisions = []
        for review in decision_rows:
            r = review["document"]
            population, population_join = pointer(history, review, r["population"])
            if population is not None:
                require(
                    population["component"] == "workforce"
                    and population["logical_system"] == "periodic_review_population",
                    "Actual native quarterly population role required for decisions",
                )
            exact_population = (
                population is row and population_join == "EXACT_AVAILABLE_NATIVE_JOIN"
            )
            flag(r["wider_estate_reviewed"], "wider estate review")
            for dec in r["decisions"]:
                member = actual_members.get(dec["subject_id"])
                supported = (
                    exact_population and member is not None and member["all_accounts_supported"]
                )
                observed = tokens(dec["observed_rights"], "periodic observed rights")
                decisions.append(
                    {
                        "subject_id": dec["subject_id"],
                        "population_native_join": population_join,
                        "decision_targets_exact_population": exact_population,
                        "member_original_present": supported,
                        "observed_rights_match": observed == member["actual_native_rights"]
                        if supported
                        else None,
                        "removal_rights": dec["remove_rights"],
                        "removal_confirmation": dec["removal_confirmation"],
                        "actual_removal_implementation_proved": False,
                    }
                )
        quarters.append(
            {
                "source": custody(row),
                "period_end_exclusive": d["period_end_exclusive"],
                "membership_digest_matches": digest(d["members"]) == d["membership_sha256"],
                "native_member_tests": found,
                "review_decision_tests": decisions,
                "retained_local_missing_ids": d["retained_local_review_missing_ids"],
                "historical_missing_ids_erased_by_later_correction": False,
            }
        )
    authority = selected(history, "workforce", "company_authority", needed=False)
    authority_facts = [
        {
            "source": custody(r),
            "recorded_scope": r["document"].get("scope"),
            "reserved_authority": r["document"].get("reserved_authority"),
            "appointments_made": r["document"].get("employment_appointments_made"),
            "earlier_operating_history": r["document"].get("earlier_operating_history"),
        }
        for r in authority
    ]
    duty_limits = [
        {
            "source": custody(r),
            "subject_id": r["document"]["subject_id"],
            "approval_document_at_fact_time": r["document"]["approval_document_at_fact_time"],
            "source_scope": r["document"]["source_scope"],
            "canonical_job_title_changed": flag(
                r["document"]["canonical_job_title_changed"], "canonical job title change"
            ),
            "restricted_witness_is_native_authority": False,
        }
        for r in selected(history, "workforce", "duty_authorizations", needed=False)
    ]
    return {
        "affiliation_context": affiliations,
        "authority_context": authority_facts,
        "retained_duty_authority_limits": duty_limits,
        "actual_account_version_count": len(accounts),
        "grant_tests": grant_tests,
        "permission_tests": permission_tests,
        "monthly_denominators": monthly,
        "periodic_reviews": quarters,
        "scope": "COLLECTED_DECLARED_LOCAL_SERVICE_NOT_ENTERPRISE_EMPLOYMENT_OR_PRODUCTION_IAM",
        "full_employment_or_estate_population_asserted": False,
    }


PERFORMED = {
    "SH-ETH-001": (
        "Recompute selected conduct approval/distribution/attestation chronology, "
        "recipient membership, due time, historical lateness and protected case routing."
    ),
    "SH-PPL-002": (
        "Inspect the selected synthetic requisition's requirement request, security "
        "input and pending assignment gate, preserving invalid nomination chronology."
    ),
    "SH-PPL-005": (
        "Reconcile selected critical-role contacts/review/open gaps and queued "
        "capacity/backup inputs; inspect training context without inventing staff "
        "appointments or handover performance."
    ),
    "SH-TRN-001": (
        "Recompute selected roster role-to-course requirements against actual "
        "assignments and due dates; inspect local approval/course definitions separately "
        "from enterprise policy acceptance."
    ),
    "SH-TRN-002": (
        "Recompute selected completion/overdue counts at each actual monitor cutoff and "
        "inspect recorded recipient follow-up; preserve late completion despite later "
        "zero overdue."
    ),
    "SH-TRN-003": (
        "Compare selected critical-role qualification/backup pending statuses with "
        "actual course history and retained gap/remedy inputs; course completion "
        "provides no automatic competence credit."
    ),
    "SH-IAM-002": (
        "Inspect selected site authority/zoning, dated badge states and recorded "
        "entry/visitor details separately from logical mover permissions for CC6.4."
    ),
}
UNPERFORMED = {
    "SH-ETH-001": (
        "Approved enterprise conduct design, complete onboarding/annual workforce "
        "recipient census and protected routing/enforcement across all cases remain "
        "unproved."
    ),
    "SH-PPL-002": (
        "Qualified role/jurisdiction/customer/legal requirements, permitted candidate "
        "checks, screening results or authorized exceptions before sensitive access and "
        "complete candidate census remain unproved."
    ),
    "SH-PPL-005": (
        "Semiannual whole-enterprise workload/vacancy/critical-skill census, appointed "
        "primary/deputy competence, accepted backup capacity, practical handover and "
        "completed capacity escalation remain unproved."
    ),
    "SH-TRN-001": (
        "Corporate employee/contractor training population, approved course "
        "content/versions, onboarding/change/refresher cadence and competency criteria "
        "remain unproved."
    ),
    "SH-TRN-002": (
        "Full-year monthly worker/LMS denominator, ordinary actual personnel completion "
        "records, manager delivery, persistent-gap escalation, authorized exceptions and "
        "effectiveness remain unproved."
    ),
    "SH-TRN-003": (
        "Critical-role qualification originals/practical capability, approved backups "
        "and completed training/supervision/remediation or enterprise competence census "
        "remain unproved."
    ),
    "SH-IAM-002": (
        "Employee/resource-owner physical duty authorization, physical "
        "conflict/credential denominator and provider/system enforcement across every "
        "zone remain unproved; fictional tokens do not establish employee access."
    ),
}
KIND_LIMITS = {
    "TOD": "Effective enterprise design and exact source applicability acceptance remain unproved.",
    "IMPLEMENTATION": (
        "The selected dated records do not establish every authored implementation step "
        "or actual external enforcement."
    ),
    "TOE": (
        "Full-period independently reconciled due population and every required "
        "occurrence remain unproved."
    ),
    "ADDITIONAL_DUTY": (
        "The additional source requirement is tested separately and receives no "
        "automatic credit from the mapped control."
    ),
}


def task_contracts():
    value = authored_contracts()
    out = identity_methods.task_contracts()
    old_tasks = identity_methods.authored_contracts()["tasks"]
    for task_id, contract in out.items():
        number = int(old_tasks[task_id]["control_id"][-3:])
        current = {
            1: "Reconcile current affiliation/authority context with actual approved grants.",
            2: "Recalculate current grants/conflicts and recorded local permission decisions.",
            3: "Inspect current affiliations/grants and retained duty authority limits separately.",
            4: "Recalculate local lease/epoch decisions and expired denial byte state.",
            5: "Inspect current local grants, permissions and available periodic review sources.",
            6: "Recalculate local credential epochs and original-object read/denial bytes.",
            7: "Recalculate local monthly/quarterly populations and retained authority limits.",
        }[number]
        contract["performed"] += " " + current
        contract["unperformed"] += (
            " Local service affiliation/account records do not establish complete employment "
            "history, whole-estate IAM authority or full authored clause acceptance."
        )
    for task_id, task in value["tasks"].items():
        performed = PERFORMED[task["control_id"]]
        unperformed = UNPERFORMED[task["control_id"]] + " " + KIND_LIMITS[task["kind"]]
        if task_id.endswith("ACTION-H-SANCTIONS"):
            performed = (
                "Trace collected protected report and substantiated facts to reasoned "
                "sanction, deadline, separate reporter protection, selected restriction "
                "records and responsibility feedback."
            )
            unperformed = (
                "Complete substantiated case denominator, accepted sanction "
                "authority/applicability, enterprise technical enforcement, "
                "performance-review cadence and consistent legal/protected-reporting "
                "treatment remain unproved. "
            ) + KIND_LIMITS[task["kind"]]
        elif task_id.endswith("ACTION-S-ACCOUNTABILITY"):
            performed += (
                " Examine collected responsibility feedback and selected corrective "
                "follow-up separately from unverified capability or capacity."
            )
            unperformed += (
                " Whole-enterprise recurring failure/workload analysis, responsibility "
                "review cadence and accepted completed accountability action remain "
                "unproved."
            )
        performed += " Exact task focus: " + task["task_kind_rule"]
        out[task_id] = {
            "performed": performed,
            "unperformed": unperformed,
            "allowed_dispositions": [
                {"status": "IN_PROGRESS", "conclusion": "LIMITATION"},
                {"status": "IN_PROGRESS", "conclusion": "FAIL"},
            ],
        }
    return out


def task_methods(task):
    control, clause = task["control_id"], task["clause_group"]
    if control == "SH-ETH-001":
        return (
            [("sanctions", sanctions)] if clause == "ACTION-H-SANCTIONS" else [("conduct", conduct)]
        )
    if control == "SH-PPL-002":
        return [("screening", screening)]
    if control == "SH-PPL-005":
        base = [("capacity", lambda h: critical(h, purpose="capacity"))]
    elif control == "SH-TRN-003":
        base = [("competence", lambda h: critical(h, purpose="competence"))]
    elif control == "SH-TRN-001":
        return [("matrix", training_matrix)]
    elif control == "SH-TRN-002":
        return [("completions", training_completions)]
    elif control == "SH-IAM-002":
        return [("physical", physical_rights)]
    else:
        raise ValueError("Unreviewed B01 task")
    return [*base, ("accountability", sanctions)] if clause == "ACTION-S-ACCOUNTABILITY" else base


TASK_COMPONENTS = {
    "SH-ETH-001": {"conduct", "supplemental", "workforce"},
    "SH-PPL-002": {"screening", "workforce"},
    "SH-PPL-005": {"critical", "training", "workforce", "supplemental"},
    "SH-TRN-001": {"training", "workforce"},
    "SH-TRN-002": {"training", "workforce"},
    "SH-TRN-003": {"critical", "training", "workforce", "supplemental"},
    "SH-IAM-002": {"physical", "identity", "workforce"},
}


def bounded_observations(observations):
    """Preserve complete calculations/custody within the reviewed 20-citation limit."""
    out = []
    for original in observations:
        literal_id = original["id"]
        if isinstance(literal_id, str) and len(literal_id) > 128:
            require(
                "original_observation_id" not in original["facts"]
                or original["facts"]["original_observation_id"] == literal_id,
                "Original observation identity fact must not be overwritten",
            )
            original = {
                **original,
                "id": "OBSERVATION-" + hashlib.sha256(literal_id.encode()).hexdigest(),
                "facts": {**original["facts"], "original_observation_id": literal_id},
            }
        evidence = original["evidence"]
        if len(evidence) <= 20:
            out.append(original)
            continue
        parts = [evidence[start : start + 20] for start in range(0, len(evidence), 20)]
        continuation_ids = [
            "CUSTODY-" + hashlib.sha256(literal_id.encode()).hexdigest() + f"-{number}"
            for number in range(2, len(parts) + 1)
        ]
        out.append(
            {
                **original,
                "evidence": parts[0],
                "facts": {
                    **original["facts"],
                    "continued_evidence_observation_ids": continuation_ids,
                    "complete_citation_count": len(evidence),
                    "custody_part": 1,
                    "custody_part_count": len(parts),
                },
            }
        )
        for number, part in enumerate(parts[1:], 2):
            out.append(
                {
                    "id": "CUSTODY-"
                    + hashlib.sha256(literal_id.encode()).hexdigest()
                    + f"-{number}",
                    "status": original["status"],
                    "evidence": part,
                    "facts": {
                        "supports_complete_calculation_observation_id": original["id"],
                        "custody_part": number,
                        "custody_part_count": len(parts),
                        "complete_citation_count": len(evidence),
                    },
                }
            )
    return out


def inspections(records, *, as_of, scratch_root=None):
    """Pure exact 52-task batch callback; no writes, source grants or old outcomes."""
    legacy, native = native_operating.partition(records)
    if native:
        observations = native_operating.examine(records, as_of=as_of)
        legacy = [
            r
            for r in legacy
            if r["logical_family"] in identity_methods.COMPONENTS
            # This exact documentary original supports native policy replay. It is
            # not one of identity's declared text roles; other type errors still refuse.
            and not (
                r["source"]["system"] == "supplementalops.policy_document"
                and r["content_type"] == "text/plain"
            )
        ]
        if legacy:
            outputs = inspections(legacy, as_of=as_of, scratch_root=scratch_root)
        else:
            value = authored_contracts()
            tasks = {**identity_methods.authored_contracts()["tasks"], **value["tasks"]}
            outputs = native_operating.unsupported_tasks(
                [{"task_id": t, **tasks[t]} for t in value["selected_task_ids"]], task_contracts()
            )
        return native_operating.add_observations(
            outputs, observations, {"IAM": {"SH-IAM-003", "SH-IAM-007"}, "PERIOD": {"SH-IAM-007"}},
            contracts=task_contracts(),
        )
    value = authored_contracts()
    contracts = task_contracts()
    history = History(records, as_of)
    old = identity_methods.inspections(records, as_of=as_of, scratch_root=scratch_root)
    out = {r["task_id"]: r for r in old}
    try:
        workforce = {"state": "EXAMINED_SELECTED_ORIGINALS", "result": workforce_access(history)}
    except MissingOriginal as error:
        workforce = {"state": "SUPPORT_UNAVAILABLE", "missing_original": str(error)}
    for task_id, inspected in out.items():
        inspected["performed"] = contracts[task_id]["performed"]
        inspected["unperformed"] = contracts[task_id]["unperformed"]
        number = int(inspected["result"]["authored_task"]["control_id"][-3:])
        fields = {
            1: (
                "affiliation_context",
                "authority_context",
                "actual_account_version_count",
                "grant_tests",
            ),
            2: ("authority_context", "grant_tests", "permission_tests"),
            3: (
                "affiliation_context",
                "authority_context",
                "grant_tests",
                "retained_duty_authority_limits",
            ),
            4: ("authority_context", "permission_tests"),
            5: ("authority_context", "grant_tests", "permission_tests", "periodic_reviews"),
            6: ("authority_context", "permission_tests"),
            7: (
                "affiliation_context",
                "monthly_denominators",
                "periodic_reviews",
                "retained_duty_authority_limits",
            ),
        }[number]
        context = {k: workforce["result"][k] for k in fields} if "result" in workforce else None
        inspected["result"]["company_workforce_access"] = (
            {
                "state": workforce["state"],
                "selected_attributes": context,
                "full_employment_or_estate_population_asserted": False,
            }
            if context is not None
            else workforce
        )
        if context is not None:
            rows = history.selected("workforce")
            inspected["artifact_ids"] = list(
                dict.fromkeys([*inspected["artifact_ids"], *(r["artifact_id"] for r in rows)])
            )
            inspected["observations"].append(
                {
                    "id": task_id + "/CURRENT-COLLECTED-LOCAL-SERVICE-ATTRIBUTES",
                    "facts": {
                        "task_id": task_id,
                        "current_source_examination": context,
                        "source_scope": workforce["result"]["scope"],
                    },
                    "status": "OBSERVED",
                    "evidence": [
                        {
                            "artifact_id": r["artifact_id"],
                            "sha256": r["artifact_sha256"],
                            "locator": "$; native state, grants, decision or population fields",
                        }
                        for r in rows
                    ],
                }
            )
    cache = {}
    for task_id in value["additional_task_ids"]:
        task = value["tasks"][task_id]
        results, missing, attributes = {}, [], []
        for name, method in task_methods(task):
            if name not in cache:
                try:
                    cache[name] = {
                        "state": "EXAMINED_SELECTED_ORIGINALS",
                        "attributes": method(history),
                    }
                except MissingOriginal as error:
                    cache[name] = {"state": "SUPPORT_UNAVAILABLE", "missing_original": str(error)}
            results[name] = cache[name]
            if cache[name]["state"] == "SUPPORT_UNAVAILABLE":
                missing.append(cache[name]["missing_original"])
            else:
                attributes.extend(cache[name]["attributes"])
        chosen = [r for r in history.rows if r["component"] in TASK_COMPONENTS[task["control_id"]]]
        observations = []
        for row in chosen:
            facts = {
                "native": custody(row),
                "actual_role": row["logical_system"],
                "task_id": task_id,
                "selected_document": row["document"],
                "whole_enterprise_authority_or_population_inferred": False,
            }
            observations.append(
                {
                    "id": "/".join(str(row["source"][k]) for k in identity_methods.NATIVE_ID),
                    "facts": facts,
                    "status": "OBSERVED",
                    "evidence": [
                        {
                            "artifact_id": row["artifact_id"],
                            "sha256": row["artifact_sha256"],
                            "locator": "$; explicit document fields and selected recalculation"
                            if row["document"] is not None
                            else "Native whole object bytes",
                        }
                    ],
                }
            )
        for a in attributes:
            observations.append(
                {
                    "id": task_id + "/RECALCULATION/" + a["attribute"],
                    "facts": {"task_id": task_id, "selected_attribute": a},
                    "status": "EXCEPTION_RECORDED" if a["exception"] else "OBSERVED",
                    "evidence": [
                        {
                            "artifact_id": r["artifact_id"],
                            "sha256": r["artifact_sha256"],
                            "locator": "$; original fields used in the named recalculation",
                        }
                        for r in chosen
                    ],
                }
            )
        conclusion = (
            "FAIL"
            if task["kind"] != "TOD" and any(a["exception"] for a in attributes)
            else "LIMITATION"
        )
        out[task_id] = {
            "task_id": task_id,
            "artifact_ids": [r["artifact_id"] for r in chosen],
            "observations": observations,
            "performed": contracts[task_id]["performed"],
            "unperformed": contracts[task_id]["unperformed"],
            "result": {
                "authored_task": task,
                "method_results": results,
                "performed_attributes": attributes,
                "missing_selected_inputs": missing,
                "native_join_limits": [
                    j
                    for j in history.joins
                    if j["from"]["system"] in {r["source"]["system"] for r in chosen}
                    and j["state"] != "EXACT_AVAILABLE_NATIVE_JOIN"
                ],
                "enterprise_population_complete": False,
                "professional_acceptance": "NOT_ASSERTED",
                "old_audit_outcomes_used": False,
            },
            "disposition": {
                "status": "IN_PROGRESS",
                "conclusion": conclusion,
                "rationale": (
                    "Observed selected source failure retained; broader authored clauses "
                    "unfinished. "
                )
                + contracts[task_id]["unperformed"]
                if conclusion == "FAIL"
                else "Selected original attributes examined; broader authored clauses unfinished. "
                + contracts[task_id]["unperformed"],
            },
        }
    for inspected in out.values():
        inspected["observations"] = bounded_observations(inspected["observations"])
    return [out[tid] for tid in value["selected_task_ids"]]
