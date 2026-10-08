"""Bounded fictional company assurance operations, not learner audit work.

The company owns independent evaluation and description-reconciliation records.
All source events are authored 2027 history; insertion clocks are actual. No
service-auditor opinion, certification or learner answer is produced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from . import company_ass_owner_monitor_exercise as monitor
from . import company_processing_purpose_2027_simulation as private
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_ASS003_004_OPERATIONS_V1"
COMPANY = monitor.COMPANY
BRANCHES = {"CLEAN": "ASSURANCE-OPS-A", "MESSY": "ASSURANCE-OPS-B"}
SOURCE_REFERENCE = "enterprise/audit_suite/company_assurance_operations_2027.py"
SPEC_REL = "enterprise/audit_suite/assurance_operations_spec_v1.json"
ROUTE_REL = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V17_2026-10-01.json"
PERIOD = {"start": "2027-07-01T00:00:00+00:00", "end": "2027-09-30T23:59:59+00:00"}
TASKS = tuple(
    f"TASK-{control}-corporate-{suffix}"
    for control, suffixes in {
        "SH-ASS-003": ("ACTION-H-EVALUATION", "IMPLEMENTATION", "TOD", "TOE"),
        "SH-ASS-004": ("ACTION-S-DESCRIPTION", "CHECK-SOC2:CC4.1", "IMPLEMENTATION", "TOD", "TOE"),
    }.items()
    for suffix in suffixes
)
SOURCE_PINS = {
    ROUTE_REL: "43b33d7ca19e670eea704193fff947c268c2d1c736f0c8829420a556576e8bcb",
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "docs/governance/ENTERPRISE_SUPPORT_SERVICES_AND_INDEPENDENCE.md": (
        "40b45496c66d6e7e5eb5dcd118c3ba37feb710744760c3617acbddcd899e466f"
    ),
    "docs/governance/committees/AUDIT_AND_COMPLIANCE_COMMITTEE_CHARTER.md": (
        "d59a708310e56dbe67fc28629efbedd4f790a4ef9765d841b651f3335ab8e993"
    ),
    "enterprise/ccf/assurance/completion_data/control_procedures.json": (
        "cb5d2729e555156b3fc9845031c00c445b5d37f7bc4c0536f275ceebecabf1f6"
    ),
    "enterprise/ccf/assurance/design_data/control_procedures.json": (
        "258f5c868e16f3dc197594857dc86a4f2b3ef11e3e5a36dd0a80a9fc6d40c679"
    ),
    SPEC_REL: "67f7f656d5901cdf75e3b8bb524c2141d77bc03d79ac8d8d3869db80cf8edd81",
}
MONITOR_ROOT = "enterprise/generated/audit-suite/company-ass-owner-monitor-2026-09-29"
UPSTREAM = {
    "MONITOR": {
        "root": MONITOR_ROOT + "/main-run-v1",
        "review": MONITOR_ROOT + "/independent-review-main-v1/REVIEW.json",
        "manifest": "716051f60ccb453cccab9dd6e0549026a803c0c908b0927be56df4222bd492a0",
        "receipt": "d1181cd5a4130ecf21ccd863d1f565f966c384193331edc7b969bc34f23767d2",
        "database": "cf50ddd8c698656ac638810c325b608a11eeb68b338810134105b3528c8865c6",
        "review_sha256": "eb47e363e5eaa8538ff3a9a41e98df1098f63cc46e854fdc8c7cc3af43851878",
    },
    "BCM": {
        "root": monitor.BCM,
        "review": monitor.BCM_REVIEW,
        "manifest": monitor.PRIVATE_PINS[f"{monitor.BCM}/MANIFEST.json"],
        "receipt": monitor.PRIVATE_PINS[f"{monitor.BCM}/RECEIPT.json"],
        "database": monitor.PRIVATE_PINS[f"{monitor.BCM}/company.sqlite3"],
        "review_sha256": monitor.PRIVATE_PINS[monitor.BCM_REVIEW],
    },
    "ISSUE": {
        "root": monitor.ISSUE,
        "review": monitor.ISSUE_REVIEW,
        "manifest": monitor.PRIVATE_PINS[f"{monitor.ISSUE}/MANIFEST.json"],
        "receipt": monitor.PRIVATE_PINS[f"{monitor.ISSUE}/RECEIPT.json"],
        "database": monitor.PRIVATE_PINS[f"{monitor.ISSUE}/company.sqlite3"],
        "review_sha256": monitor.PRIVATE_PINS[monitor.ISSUE_REVIEW],
    },
    "TRANSITION": {
        "root": monitor.issue.TRANSITION_REL,
        "review": monitor.issue.TRANSITION_REVIEW,
        "manifest": monitor.issue.PRIVATE_PINS[f"{monitor.issue.TRANSITION_REL}/MANIFEST.json"],
        "receipt": monitor.issue.PRIVATE_PINS[f"{monitor.issue.TRANSITION_REL}/RECEIPT.json"],
        "database": monitor.issue.PRIVATE_PINS[f"{monitor.issue.TRANSITION_REL}/company.sqlite3"],
        "review_sha256": monitor.issue.PRIVATE_PINS[monitor.issue.TRANSITION_REVIEW],
    },
}
SYSTEM_OWNERS = {
    "assurance_programme": "AS-P009",
    "assurance_scope": "AS-P009",
    "assurance_independence": "AS-P009",
    "assurance_access": "AS-P009",
    "assurance_population": "AS-P009",
    "assurance_workpaper": "AS-P009",
    "assurance_review": "AS-P009",
    "assurance_report": "AS-P009",
    "assurance_committee_route": "AS-P004",
    "assurance_followup": "AS-P009",
    "management_assurance_response": "AS-P007",
    "assurance_description": "AS-P007",
    "assurance_description_config": "AS-P007",
    "assurance_disclosure_review": "AS-P009",
    "customer_assurance_request": "AS-P005",
    "customer_assurance_release": "AS-P003",
    "assurance_period_reconciliation": "AS-P009",
}
FIELDS = monitor.SOURCE_FIELDS
LIMITS = [
    "Three selected internal evaluation workstreams for one shared runtime in Q3, "
    "not a complete enterprise audit programme or the learner engagement.",
    "Head of Internal Audit's scoped work follows the locked independence doctrine; "
    "enterprise charter/annual programme approval and broader assurance maturity "
    "remain unresolved.",
    "The distinct quality reviewer is a synthetic specialist role token limited to this "
    "fictional assignment; no actual credential, CPA, external opinion or "
    "incremental hire is asserted.",
    "Historical bypass, capacity, owner-monitor and unaccepted business/customer-objective limits "
    "remain preserved. Company evaluation does not close prior source issues or "
    "earn learner task credit.",
    "Management's description is a selected internal readiness description; customer briefing "
    "release is conditional for a fictional recipient, with no actual communication or SOC report.",
    "No real PHI, actual HIPAA/BA assertion, audit grant/collection, accepted clause/N/A, "
    "fresh engagement, grade, Key, provider certification or Atlas write.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_source(private_repository: Path, name: str) -> dict:
    cfg = UPSTREAM[name]
    root = private_repository / cfg["root"]
    paths = {
        "manifest": root / "MANIFEST.json",
        "receipt": root / "RECEIPT.json",
        "database": root / "company.sqlite3",
        "review_sha256": private_repository / cfg["review"],
    }
    before = private._frozen(paths)
    if {key: value[-1] for key, value in before.items()} != {key: cfg[key] for key in paths}:
        raise CompanyStoreError("Reviewed assurance upstream pin differs")
    review = json.loads(paths["review_sha256"].read_text())
    if not str(review.get("verdict", "")).startswith("PASS"):
        raise CompanyStoreError("Reviewed assurance upstream verdict differs")
    receipt = json.loads(paths["receipt"].read_text())
    selected = {}
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok" or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("Assurance upstream integrity/access boundary differs")
        for scenario in BRANCHES:
            selected[scenario] = {}
            for ref in receipt["records"][scenario]:
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    tuple(ref[k] for k in ("company", "branch", "system", "record", "version")),
                ).fetchone()
                if (
                    row is None
                    or any(row[k] != ref[k] for k in FIELDS)
                    or sha(row["content"]) != ref["sha256"]
                ):
                    raise CompanyStoreError("Assurance upstream native original differs")
                selected[scenario][ref["system"], ref["record"], ref["version"]] = {
                    "ref": {k: ref[k] for k in FIELDS},
                    "body": json.loads(row["content"]),
                }
    if private._frozen(paths) != before:
        raise CompanyStoreError("Assurance upstream changed during read")
    return selected


def _context(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    for relative, expected in SOURCE_PINS.items():
        path = repository / relative
        if path.is_symlink() or not path.is_file() or _digest(path) != expected:
            raise CompanyStoreError("Pinned assurance canon/specification differs")
    spec = json.loads((repository / SPEC_REL).read_text())
    if (
        spec.get("schema") != SCHEMA + "_SPEC"
        or spec.get("period") != PERIOD
        or spec.get("internal_audit_lead") != "AS-P009"
        or spec.get("quality_reviewer") != "SIM-IA-QUALITY-REVIEWER-01"
        or spec.get("no_operating_control_ownership") is not True
        or spec.get("enterprise_charter_approval_asserted") is not False
    ):
        raise CompanyStoreError("Assurance authority specification differs")
    ledger = json.loads((repository / ROUTE_REL).read_text())
    for side in "AB":
        rows = [
            r
            for r in ledger["rows"]
            if r["side"] == side
            and r["control_id"] in {"SH-ASS-003", "SH-ASS-004"}
            and not r["targeted_integrated_source_ids"]
        ]
        if sorted(r["task_id"] for r in rows) != sorted(TASKS) or any(
            r["current_status"] != "NOT_STARTED"
            or r["current_conclusion"] != "NOT_RUN"
            or r["audit_task_credit"] is not False
            for r in rows
        ):
            raise CompanyStoreError("Exact nine unrun assurance routes differ")
    monitor.verify(
        private_repository / UPSTREAM["MONITOR"]["root"],
        repository=repository,
        private_repository=private_repository,
    )
    return {
        "spec": spec,
        "sources": {name: _read_source(private_repository, name) for name in UPSTREAM},
    }


def _source(
    context: dict, scenario: str, family: str, system: str, record: str, version: int = 1
) -> dict:
    try:
        return context["sources"][family][scenario][system, record, version]
    except KeyError as exc:
        raise CompanyStoreError("Required assurance source locator missing") from exc


def _numeric_replay(body: dict) -> dict:
    detail = body["detail"]
    minutes = (
        datetime.fromisoformat(detail["observed_finish_at"])
        - datetime.fromisoformat(detail["exercise_start_at"])
    ).total_seconds() / 60
    if (
        minutes < 0
        or not minutes.is_integer()
        or detail["measured_replay_gap_minutes_simulated"] < 0
    ):
        raise CompanyStoreError("Invalid selected recovery measurement")
    minutes = int(minutes)
    return {
        "reperformed_elapsed_minutes": minutes,
        "reported_elapsed_minutes": detail["measured_restore_minutes_simulated"],
        "elapsed_agrees": minutes == detail["measured_restore_minutes_simulated"],
        "rto_met": minutes <= detail["rto_target_minutes"],
        "rpo_met": detail["measured_replay_gap_minutes_simulated"] <= detail["rpo_target_minutes"],
        "marker_digest_match": detail["marker_digest_match"],
        "application_recovery_proven": False,
    }


def _expected_rows(context: dict, scenario: str) -> list[dict]:
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown assurance branch")
    all_sources = context["sources"]
    original_refs = [
        entry["ref"] for family in all_sources.values() for entry in family[scenario].values()
    ]
    start = datetime.fromisoformat("2027-09-15T09:00:00+00:00")
    if any(datetime.fromisoformat(ref["available_at"]) >= start for ref in original_refs):
        raise CompanyStoreError("Upstream assurance source unavailable before programme")
    selected = monitor.RECORD
    owner_first = _source(context, scenario, "MONITOR", "owner_self_assessment", selected)
    risk_observation = _source(context, scenario, "MONITOR", "second_line_observation", selected)
    exercise_version = 1 if scenario == "CLEAN" else 2
    exercise = _source(
        context, scenario, "BCM", "exercise_result", "MARKER-RECOVERY", exercise_version
    )
    bia = _source(context, scenario, "BCM", "business_impact", "SVC-COMPUTE")
    issue_records = list(all_sources["ISSUE"][scenario].values())
    transition_records = list(all_sources["TRANSITION"][scenario].values())
    latest_issue_open = any(
        row["body"].get("finding_closed") is False and row["ref"]["system"] == "issue_finding"
        for row in issue_records
    )
    replay = _numeric_replay(exercise["body"])
    if replay["elapsed_agrees"] is not True:
        raise CompanyStoreError("Upstream technical replay arithmetic differs")
    rows, local = [], {}

    def add(
        system, record, day, hour, details, dependencies=(), upstream=(), actor=None, version=1
    ):
        at = datetime.fromisoformat(f"2027-09-{day:02d}T{hour:02d}:00:00+00:00")
        event = _time(at.isoformat())
        availability = _time((at + timedelta(minutes=10)).isoformat())
        deps = [local[name] for name in dependencies]
        upstream_refs = list(upstream)
        if any(ref["available_at"] >= event for ref in deps + upstream_refs):
            raise CompanyStoreError("Assurance dependency unavailable at business event")
        prior = local.get(record) if version > 1 else None
        body = {
            "schema": SCHEMA,
            "truth_class": "FUTURE_TRAINING_SCENARIO_ONLY",
            "service_id": "SVC-compute",
            "boundary_id": "corporate",
            "period": PERIOD,
            "business_clock": "FICTIONAL_2027",
            "record_id": record,
            "actor_person_id": actor or SYSTEM_OWNERS[system],
            "event_at": event,
            "available_at": availability,
            "dependencies": deps,
            "upstream_originals": upstream_refs,
            "supersedes": prior,
            "real_world_operation": False,
            "real_phi_payload": False,
            "actual_hipaa_applicability": "UNDETERMINED",
            **details,
        }
        row = {
            "system": system,
            "record": record,
            "version": version,
            "event_at": event,
            "available_at": availability,
            "body": body,
            "sha256": sha(encoded(body)),
        }
        rows.append(row)
        local[record] = {
            "company": COMPANY,
            "branch": BRANCHES[scenario],
            **{
                k: row[k]
                for k in ("system", "record", "version", "sha256", "event_at", "available_at")
            },
        }

    changes = [
        row["ref"]
        for row in transition_records
        if row["ref"]["system"] in {"site_commissioning", "site_release", "exception_event"}
    ]
    add(
        "assurance_programme",
        "PROGRAMME-01",
        15,
        9,
        {
            "action": "REGISTER_SCOPED_INTERNAL_EVALUATION_PROGRAMME",
            "scope": "Q3_SHARED_RUNTIME_SELECTED_CONTROLS",
            "plan_owner": "AS-P009",
            "functional_reporting_route": "BOARD_AUDIT_AND_COMPLIANCE_COMMITTEE",
            "annual_enterprise_programme_approval": "PENDING_NOT_ASSERTED",
            "selected_workstreams": [
                "RECOVERY_TECHNICAL",
                "MONITORING_NONTECHNICAL",
                "DESCRIPTION_RECONCILIATION",
            ],
            "risk_basis": "MATERIAL_SITE_TRANSITION_AND_RECOVERY_CHANGE",
            "second_line_limit": (
                "LOCAL_MONITOR_PREVIOUSLY_SCREENED_ISSUE_NOT_INDEPENDENT_EVALUATION"
            ),
            "selected_issue_condition_count": 1,
            "risk_level": "HIGH_WITH_OPEN_ISSUE"
            if latest_issue_open
            else "MODERATE_TRANSITION_RISK",
            "full_enterprise_programme": False,
        },
        upstream=changes + [risk_observation["ref"]],
    )
    add(
        "assurance_scope",
        "SCOPE-01",
        15,
        10,
        {
            "action": "DEFINE_CRITERIA_BOUNDARY_AND_EXCLUSIONS",
            "scope_services": ["SVC-compute"],
            "scope_sites": ["RUNTIME-RENO-COLO", "RUNTIME-BOISE-DR"],
            "criteria": [
                "LOCALLY_ACCEPTED_RTO_RPO_OR_EXPLICIT_ACCEPTANCE_HOLD",
                "HISTORICAL_RECOVERY_AUTHORITY",
                "OWNER_DISCLOSURE_RECONCILIATION",
                "DESCRIPTION_ASSERTION_SOURCE_SUPPORT",
            ],
            "technical_safeguard": "SELECTED_INDEPENDENT_KEY_RECOVERY_PATH",
            "nontechnical_safeguard": "OWNER_ATTESTATION_AND_ISSUE_ESCALATION",
            "excluded": [
                "FULL_YEAR",
                "CUSTOMER_SLA",
                "REAL_EPHI",
                "ALL_ENTERPRISE_ASSETS",
                "PROVIDER_CONTROLS",
            ],
            "exclusion_reason": "SOURCE_POPULATIONS_ARE_BOUNDED_LOCAL_MARKER_AND_ISSUE_HISTORY",
            "scope_decision_owner": "AS-P009",
            "management_may_not_suppress_direct_report": True,
        },
        ("PROGRAMME-01",),
    )
    add(
        "assurance_independence",
        "INDEPENDENCE-01",
        15,
        11,
        {
            "action": "SCREEN_EVALUATOR_AND_REVIEWER_OBJECTIVITY",
            "preparer_id": "AS-P009",
            "quality_reviewer_id": context["spec"]["quality_reviewer"],
            "excluded_evaluators": [
                {"person_id": "AS-P007", "reason": "OPERATES_RECOVERY_AND_ATTESTS"},
                {"person_id": "AS-P005", "reason": "AUTHORED_PRIOR_ISSUE_SCREENING"},
            ],
            "preparer_operating_control_ownership": False,
            "reviewer_operating_control_ownership": False,
            "reviewer_prepared_tests": False,
            "reviewer_identity_type": "SYNTHETIC_SELECTED_REVIEW_SPECIALIST_TOKEN",
            "competence_basis": (
                "AUTHORED_ASSIGNMENT_MATRIX_RECOVERY_ARITHMETIC_SOURCE_RECONCILIATION"
            ),
            "actual_credentials_verified": False,
            "professional_external_opinion_authority": False,
            "conflicts_declared": [],
            "enterprise_staffing_or_incremental_hire_asserted": False,
        },
        ("SCOPE-01",),
    )
    add(
        "assurance_access",
        "ACCESS-01",
        15,
        12,
        {
            "action": "RECORD_SCOPED_INTERNAL_SOURCE_ACCESS",
            "principal": "AS-P009",
            "source_scope": list(UPSTREAM),
            "objectivity_restriction": "READ_AND_EVALUATE_ONLY_NO_OPERATING_EDITS",
            "direct_escalation_route": "BOARD_AUDIT_AND_COMPLIANCE_COMMITTEE",
            "access_is_live_identity_provider_grant": False,
            "learner_engagement_grant_created": False,
        },
        ("SCOPE-01", "INDEPENDENCE-01"),
    )
    for stream, planned_day in (("RECOVERY", 20), ("MONITORING", 22), ("DESCRIPTION", 26)):
        add(
            "assurance_programme",
            f"ENG-{stream}",
            16,
            9 + (planned_day % 3),
            {
                "action": "SCHEDULE_SELECTED_EVALUATION",
                "workstream": stream,
                "scheduled_start_at": f"2027-09-{planned_day:02d}T09:00:00+00:00",
                "due_at": f"2027-09-{planned_day + 2:02d}T17:00:00+00:00",
                "status": "SCHEDULED",
                "period_scope": PERIOD,
                "material_change_trigger_refs": changes,
                "evaluation_owner": "AS-P009",
            },
            ("PROGRAMME-01", "INDEPENDENCE-01", "ACCESS-01"),
        )
    period_refs = [
        ref for ref in original_refs if PERIOD["start"] <= ref["event_at"] <= PERIOD["end"]
    ]
    context_refs = [ref for ref in original_refs if ref["event_at"] < PERIOD["start"]]
    add(
        "assurance_population",
        "POPULATION-01",
        18,
        9,
        {
            "action": "FREEZE_SELECTED_SOURCE_QUERIES_BEFORE_SELECTION",
            "source_queries": {
                name: "SELECT company,branch,system,record,version,event_at,available_at,sha256 "
                "FROM versions WHERE branch = :selected_branch ORDER BY rowid"
                for name in UPSTREAM
            },
            "query_scope": "EXACT_FROZEN_COMPANY_COHORTS_NOT_ENTERPRISE_POPULATION",
            "source_period_event_refs": period_refs,
            "antecedent_context_refs": context_refs,
            "antecedent_records_counted_as_period_events": False,
            "collection_as_of": "2027-09-18T09:00:00+00:00",
            "source_version_counts": {
                name: len(family[scenario]) for name, family in all_sources.items()
            },
            "source_tuple_sha256": sha(encoded(original_refs)),
            "selection_method": "CENSUS_OF_BOUNDED_COHORT_PLUS_LATEST_AND_ORIGINAL_HISTORY_TRACE",
            "selected_technical_versions": [
                r["ref"]
                for r in all_sources["BCM"][scenario].values()
                if r["ref"]["system"] == "exercise_result"
            ],
            "selected_nontechnical_versions": [
                r["ref"]
                for r in all_sources["MONITOR"][scenario].values()
                if r["ref"]["system"] in {"owner_self_assessment", "second_line_observation"}
            ],
            "full_enterprise_population_complete": False,
        },
        ("ACCESS-01",),
        upstream=original_refs,
    )
    add(
        "assurance_workpaper",
        "WP-TECHNICAL-01",
        20,
        10,
        {
            "action": "REPERFORM_SELECTED_RECOVERY_NUMERICS_AND_AUTHORITY",
            "evaluation_performer": "AS-P009",
            "reperformance": replay,
            "objective_acceptance": bia["body"]["detail"]["accepted_local_objectives"],
            "historical_issue_remains_open": latest_issue_open,
            "historical_failed_versions_retained": [
                r["ref"]
                for r in all_sources["BCM"][scenario].values()
                if r["ref"]["system"] == "exercise_result"
            ],
            "technical_observation": "LATEST_SELECTED_MARKER_NUMERICS_MEET_LOCAL_TARGETS",
            "effectiveness_limit": "MARKER_ONLY_NO_APPLICATION_OR_CUSTOMER_OR_EPHI_RECOVERY",
            "overall_business_recovery_conclusion": "NOT_ESTABLISHED",
        },
        ("POPULATION-01", "ENG-RECOVERY"),
        upstream=[exercise["ref"], bia["ref"]],
    )
    add(
        "assurance_workpaper",
        "WP-NONTECHNICAL-01",
        22,
        10,
        {
            "action": "COMPARE_ATTESTATION_HISTORY_WITH_ISSUE_AND_MONITORING_RECORDS",
            "evaluation_performer": "AS-P009",
            "initial_owner_statement": owner_first["body"]["statement"],
            "open_selected_issue_count": int(latest_issue_open),
            "monitoring_gap": "INITIAL_ATTESTATION_OMITTED_OPEN_ISSUE_LATER_CORRECTED"
            if latest_issue_open
            else "NO_SELECTED_MISMATCH_IN_EXACT_COHORT",
            "second_line_objectivity_limit": "PRIOR_ISSUE_SCREENING_PARTICIPATION",
            "independent_evaluation_separate_from_owner_certification": True,
            "closure_validation_status": "NOT_ESTABLISHED"
            if latest_issue_open
            else "NO_SELECTED_CLOSURE_TEST_REQUIRED",
            "effectiveness_limit": "ONE_OWNER_AND_ONE_SELECTED_CONDITION_ONLY",
        },
        ("POPULATION-01", "ENG-MONITORING"),
        upstream=[owner_first["ref"], risk_observation["ref"]] + [r["ref"] for r in issue_records],
    )
    for name, day in (("RECOVERY", 21), ("MONITORING", 23)):
        wp = "WP-TECHNICAL-01" if name == "RECOVERY" else "WP-NONTECHNICAL-01"
        add(
            "assurance_review",
            f"REVIEW-{name}",
            day,
            10,
            {
                "action": "QUALITY_REVIEW_SELECTED_INTERNAL_EVALUATION",
                "reviewer_id": context["spec"]["quality_reviewer"],
                "preparer_id": "AS-P009",
                "independent_from_preparation_and_operation": True,
                "reviewed_workpaper_record": wp,
                "review_scope": "RECALCULATE_AND_TRACE_SOURCE_TUPLES",
                "review_disposition": "ACCEPT_BOUNDED_OBSERVATIONS_WITH_SCOPE_LIMITS",
                "actual_external_assurance_opinion": False,
            },
            (wp, "INDEPENDENCE-01"),
            actor=context["spec"]["quality_reviewer"],
        )
        add(
            "assurance_programme",
            f"ENG-{name}",
            day,
            11,
            {
                "action": "COMPLETE_SELECTED_EVALUATION",
                "workstream": name,
                "status": "COMPLETED_SCOPED_INTERNAL_EVALUATION",
                "enterprise_conclusion": "NOT_EXPRESSED",
                "prior_failures_and_untested_cases_retained": True,
            },
            (f"REVIEW-{name}",),
            version=2,
        )
    add(
        "assurance_report",
        "REPORT-01",
        24,
        9,
        {
            "action": "ISSUE_SELECTED_INTERNAL_EVALUATION_REPORT",
            "report_owner": "AS-P009",
            "technical_observation": replay,
            "nontechnical_issue_status": "OPEN" if latest_issue_open else "NO_SELECTED_ISSUE",
            "management_action_needed": [
                "APPROVE_AND_IMPLEMENT_BYPASS_PREVENTION",
                "RESOLVE_CAPACITY_AND_OBJECTIVE_HOLD",
                "PRESERVE_AND_DISCLOSE_OWNER_SUBMISSION_HISTORY",
            ]
            if latest_issue_open
            else [],
            "report_is_service_auditor_opinion": False,
            "report_is_provider_certification": False,
            "full_control_or_hipaa_compliance_conclusion": "NOT_EXPRESSED",
            "audience": ["ACCOUNTABLE_MANAGEMENT", "BOARD_AUDIT_AND_COMPLIANCE_COMMITTEE"],
        },
        ("REVIEW-RECOVERY", "REVIEW-MONITORING", "SCOPE-01"),
    )
    add(
        "assurance_committee_route",
        "COMMITTEE-ROUTE-01",
        24,
        10,
        {
            "action": "REGISTER_DIRECT_INTERNAL_AUDIT_COMMUNICATION",
            "sender_person_id": "AS-P009",
            "recipient_role": "BOARD_AUDIT_AND_COMPLIANCE_COMMITTEE",
            "administrative_custodian": "AS-P004",
            "transport": "FICTIONAL_COMMITTEE_RECORDS_QUEUE",
            "queue_receipt_status": "RECORDED",
            "management_preclearance_required": False,
            "committee_collective_decision": "NOT_PERFORMED",
            "chair_acknowledgment_or_quorum_inferred": False,
            "actual_external_message": False,
        },
        ("REPORT-01",),
    )
    add(
        "management_assurance_response",
        "MANAGEMENT-RESPONSE-01",
        25,
        9,
        {
            "action": "ACKNOWLEDGE_SELECTED_REPORT_AND_ASSIGN_FOLLOWUP",
            "accountable_owner": "AS-P007",
            "response": "PLAN_PROPOSED_VALIDATION_PENDING"
            if latest_issue_open
            else "RETAIN_SELECTED_CONTROL_AND_SCOPE_LIMITS",
            "proposed_due_at": "2027-10-15T17:00:00+00:00" if latest_issue_open else None,
            "residual_risk_acceptance": "NOT_PERFORMED",
            "prior_issue_closed": False,
            "enterprise_management_assertion": "NOT_MADE",
        },
        ("REPORT-01",),
    )
    add(
        "assurance_followup",
        "FOLLOWUP-01",
        25,
        10,
        {
            "action": "REGISTER_INDEPENDENT_FOLLOWUP_GATE",
            "followup_owner": "AS-P009",
            "status": "PENDING_NEW_CONTROL_AND_INDEPENDENT_RETEST"
            if latest_issue_open
            else "NO_SELECTED_CORRECTIVE_ACTION",
            "closure_criteria": [
                "APPROVED_AUTHORITY_CONTROL",
                "REPEATED_INDEPENDENT_KEY_RECOVERY",
                "CAPACITY_AND_BIA_ACCEPTANCE",
                "SOURCE_RECONCILIATION",
            ],
            "owner_ACK_is_closure": False,
            "prior_finding_status_changed": False,
        },
        ("MANAGEMENT-RESPONSE-01",),
    )
    add(
        "assurance_description_config",
        "DESCRIPTION-CONFIG-01",
        25,
        11,
        {
            "action": "REGISTER_SELECTED_DESCRIPTION_EXTRACTION_CONFIG",
            "operator": "AS-P007",
            "source_systems": ["BCM", "TRANSITION"] if scenario == "MESSY" else list(UPSTREAM),
            "attestation_cache_version": 1,
            "include_issue_and_exception_history": scenario == "CLEAN",
            "scope": "DRAFT_SELECTED_SHARED_RUNTIME_DESCRIPTION",
            "deployment_is_real_world": False,
        },
        ("SCOPE-01",),
    )
    vendor_refs = [
        r["ref"] for r in transition_records if r["ref"]["system"] == "provider_contract"
    ]
    assertions = [
        {
            "assertion_id": "DESC-BOUNDARY",
            "statement": (
                "One selected shared-runtime marker service, Reno primary and "
                "Boise recovery; customer/enterprise claims excluded."
            ),
            "sources": [
                _source(context, scenario, "BCM", "service_inventory", "SVC-COMPUTE")["ref"]
            ],
        },
        {
            "assertion_id": "DESC-RECOVERY",
            "statement": (
                "Latest selected marker replay meets local numeric targets; "
                "application and customer recovery remain outside this result."
            ),
            "sources": [exercise["ref"], bia["ref"]],
        },
        {
            "assertion_id": "DESC-PROVIDERS",
            "statement": (
                "Synthetic provider contracts support selected sites; provider "
                "controls and independent provider assurance are excluded."
            ),
            "sources": vendor_refs,
        },
    ]
    if scenario == "CLEAN":
        assertions.append(
            {
                "assertion_id": "DESC-ISSUES",
                "statement": (
                    "The exact selected issue/monitoring cohort reports no "
                    "selected defect; enterprise completeness is not established."
                ),
                "sources": [r["ref"] for r in issue_records] + [risk_observation["ref"]],
            }
        )
    add(
        "assurance_description",
        "DESCRIPTION-01",
        26,
        9,
        {
            "action": "PREPARE_MANAGEMENT_SELECTED_SYSTEM_DESCRIPTION",
            "status": "DRAFT_FOR_REVIEW",
            "description_owner": "AS-P007",
            "assertions": assertions,
            "description_is_complete_soc2_system_description": False,
            "formal_management_assertion": "NOT_MADE",
            "customer_release_status": "HELD_FOR_RECONCILIATION",
        },
        ("DESCRIPTION-CONFIG-01", "POPULATION-01", "ENG-DESCRIPTION"),
    )
    description_issue_ids = (
        ["DESC-HISTORICAL-BYPASS", "DESC-OWNER-CORRECTION"] if latest_issue_open else []
    )
    add(
        "assurance_disclosure_review",
        "DISCLOSURE-REVIEW-01",
        27,
        9,
        {
            "action": "INDEPENDENTLY_COMPARE_DESCRIPTION_WITH_CHANGE_VENDOR_AND_ISSUE_POPULATIONS",
            "reviewer": context["spec"]["quality_reviewer"],
            "description_preparer": "AS-P007",
            "population_source_families": list(UPSTREAM),
            "source_counts": {name: len(family[scenario]) for name, family in all_sources.items()},
            "assertion_ids_screened": [a["assertion_id"] for a in assertions],
            "missing_relevant_description_items": description_issue_ids,
            "decision": "RETURN_FOR_MATERIAL_ISSUE_DISCLOSURE"
            if latest_issue_open
            else "ACCEPT_SELECTED_DESCRIPTION_WITH_EXPLICIT_LIMITS",
            "provider_certification_verified": False,
            "external_opinion_available": False,
            "full_description_criteria_conformance": "NOT_CONCLUDED",
        },
        ("DESCRIPTION-01", "POPULATION-01", "REPORT-01"),
        upstream=original_refs,
        actor=context["spec"]["quality_reviewer"],
    )
    if latest_issue_open:
        final_assertions = assertions + [
            {
                "assertion_id": "DESC-HISTORICAL-BYPASS",
                "statement": (
                    "The prior Boise readiness/key-bypass issue and "
                    "capacity/objective holds remain open despite improved marker "
                    "replay numerics."
                ),
                "sources": [r["ref"] for r in issue_records]
                + [_source(context, scenario, "BCM", "closure_gate", "KEY-AND-CAPACITY")["ref"]],
            },
            {
                "assertion_id": "DESC-OWNER-CORRECTION",
                "statement": (
                    "The initial owner submission excluded the selected open "
                    "issue; second-line challenge led to a corrected submission "
                    "and pending escalation."
                ),
                "sources": [r["ref"] for r in all_sources["MONITOR"][scenario].values()],
            },
        ]
        add(
            "assurance_description",
            "DESCRIPTION-01",
            28,
            9,
            {
                "action": "CORRECT_MANAGEMENT_SELECTED_DESCRIPTION",
                "status": "CORRECTED_FOR_REVIEW",
                "description_owner": "AS-P007",
                "assertions": final_assertions,
                "original_draft_retained": True,
                "prior_issue_closed": False,
                "description_is_complete_soc2_system_description": False,
                "formal_management_assertion": "NOT_MADE",
                "customer_release_status": "HELD_FOR_FINAL_REVIEW",
            },
            ("DISCLOSURE-REVIEW-01",),
            version=2,
        )
    add(
        "assurance_review",
        "REVIEW-DESCRIPTION",
        28,
        10,
        {
            "action": "REVIEW_FINAL_SELECTED_DESCRIPTION_SOURCE_SUPPORT",
            "reviewer_id": context["spec"]["quality_reviewer"],
            "preparer_id": "AS-P007",
            "independent_from_preparation_and_operation": True,
            "description_version": 2 if latest_issue_open else 1,
            "review_disposition": "ACCEPT_BOUNDED_DESCRIPTION_WITH_OPEN_ISSUES_AND_EXCLUSIONS",
            "complete_soc2_description_or_external_opinion": False,
        },
        ("DESCRIPTION-01", "DISCLOSURE-REVIEW-01"),
        actor=context["spec"]["quality_reviewer"],
    )
    add(
        "assurance_programme",
        "ENG-DESCRIPTION",
        28,
        11,
        {
            "action": "COMPLETE_SELECTED_DESCRIPTION_EVALUATION",
            "status": "COMPLETED_SCOPED_INTERNAL_EVALUATION",
            "workstream": "DESCRIPTION",
            "enterprise_conclusion": "NOT_EXPRESSED",
            "prior_failures_and_untested_cases_retained": True,
        },
        ("REVIEW-DESCRIPTION",),
        version=2,
    )
    add(
        "customer_assurance_request",
        "CUSTOMER-REQUEST-01",
        29,
        9,
        {
            "action": "REGISTER_SYNTHETIC_CUSTOMER_ASSURANCE_INQUIRY",
            "recipient_id": "SIM-CUSTOMER-ASSURANCE-01",
            "requested_claims": [
                "SOC2_TYPE2_COMPLETE",
                "HIPAA_COMPLIANT",
                "PROVIDER_CONTROLS_IN_SCOPE",
            ],
            "request_is_actual_external_message": False,
            "request_source": "AUTHORED_CUSTOMER_ROLE_TOKEN",
        },
        ("REVIEW-DESCRIPTION",),
    )
    add(
        "customer_assurance_release",
        "CUSTOMER-RELEASE-01",
        29,
        10,
        {
            "action": "LEGAL_SCREEN_CUSTOMER_ASSURANCE_STATEMENT",
            "reviewer": "AS-P003",
            "recipient_id": "SIM-CUSTOMER-ASSURANCE-01",
            "disallowed_claims": ["SOC2_TYPE2_COMPLETE", "HIPAA_COMPLIANT", "PROVIDER_CERTIFIED"],
            "approved_statement": (
                "Fictional selected Q3 internal evaluation only; the company has "
                "no service-auditor opinion or actual HIPAA-compliance assertion. "
                "Provider controls are excluded; limitations and open issues must "
                "accompany the briefing."
            ),
            "release_status": "APPROVED_LIMITED_FICTIONAL_BRIEFING_NOT_TRANSMITTED",
            "approved_description_version": 2 if latest_issue_open else 1,
            "external_opinion_attached": False,
            "actual_customer_message_sent": False,
            "distribution_limit": "NAMED_SYNTHETIC_RECIPIENT_ONLY_NO_SOC_BADGE_OR_CERTIFICATION",
        },
        ("CUSTOMER-REQUEST-01", "REVIEW-DESCRIPTION", "DESCRIPTION-01", "FOLLOWUP-01"),
    )
    add(
        "assurance_period_reconciliation",
        "PERIOD-01",
        30,
        9,
        {
            "action": "RECONCILE_SELECTED_PROGRAMME_AND_OUTPUT_ROSTER",
            "planned_workstreams": 3,
            "completed_workstreams": 3,
            "deferred_workstreams": 0,
            "workstream_record_ids": ["ENG-RECOVERY", "ENG-MONITORING", "ENG-DESCRIPTION"],
            "quality_reviews": 3,
            "selected_internal_reports": 1,
            "customer_assurance_requests": 1,
            "actual_customer_transmissions": 0,
            "open_prior_issue_count": int(latest_issue_open),
            "prior_issue_closed": False,
            "selected_programme_roster_complete": True,
            "enterprise_programme_population_complete": False,
            "source_versions_retained": True,
            "external_assurance_opinion_count": 0,
        },
        (
            "ENG-RECOVERY",
            "ENG-MONITORING",
            "ENG-DESCRIPTION",
            "CUSTOMER-RELEASE-01",
            "COMMITTEE-ROUTE-01",
        ),
    )
    _validate_history(rows, scenario)
    return rows


def _validate_history(rows: list[dict], scenario: str) -> None:
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown assurance validation branch")
    known, completions = {}, []
    for row in rows:
        b = row["body"]
        if (
            b.get("truth_class") != "FUTURE_TRAINING_SCENARIO_ONLY"
            or b.get("real_world_operation") is not False
            or b.get("real_phi_payload") is not False
            or any(
                k in b
                for k in ("scenario", "expected_finding", "false_clean", "rubric", "task_credit")
            )
        ):
            raise CompanyStoreError("Assurance fiction/learner-answer boundary differs")
        for dep in b["dependencies"]:
            key = dep["system"], dep["record"], dep["version"]
            if key not in known or dep != known[key] or dep["available_at"] >= row["event_at"]:
                raise CompanyStoreError("Assurance native dependency identity/availability differs")
        for upstream in b["upstream_originals"]:
            if upstream["available_at"] >= row["event_at"] or upstream["company"] != COMPANY:
                raise CompanyStoreError("Assurance upstream availability/custody differs")
        if b["supersedes"] is not None:
            prior = b["supersedes"]
            if known.get((prior["system"], prior["record"], prior["version"])) != prior:
                raise CompanyStoreError("Assurance superseded original differs")
        if row["system"] == "assurance_review" and b.get("reviewer_id") == b.get("preparer_id"):
            raise CompanyStoreError("Assurance self-review is prohibited")
        if row["system"] == "assurance_programme" and row["version"] == 2:
            completions.append(row["record"])
        if sha(encoded(b)) != row["sha256"]:
            raise CompanyStoreError("Assurance native serialization differs")
        known[row["system"], row["record"], row["version"]] = {
            "company": COMPANY,
            "branch": BRANCHES[scenario],
            **{
                k: row[k]
                for k in ("system", "record", "version", "sha256", "event_at", "available_at")
            },
        }
    if sorted(completions) != ["ENG-DESCRIPTION", "ENG-MONITORING", "ENG-RECOVERY"]:
        raise CompanyStoreError("Assurance planned/completed roster differs")
    period = rows[-1]["body"]
    if (
        period["completed_workstreams"] != len(completions)
        or period["enterprise_programme_population_complete"] is not False
        or period["external_assurance_opinion_count"] != 0
    ):
        raise CompanyStoreError("Assurance period/claim boundary differs")


def _lead_map(refs: list[dict]) -> dict:
    source_sets = {
        "SH-ASS-003": {
            "ACTION-H-EVALUATION": [
                "PROGRAMME-01",
                "SCOPE-01",
                "ENG-RECOVERY",
                "ENG-MONITORING",
                "WP-TECHNICAL-01",
                "WP-NONTECHNICAL-01",
                "REPORT-01",
                "FOLLOWUP-01",
            ],
            "IMPLEMENTATION": ["PROGRAMME-01", "INDEPENDENCE-01", "ACCESS-01", "REPORT-01"],
            "TOD": [
                "PROGRAMME-01",
                "SCOPE-01",
                "INDEPENDENCE-01",
                "COMMITTEE-ROUTE-01",
                "FOLLOWUP-01",
            ],
            "TOE": [
                "POPULATION-01",
                "ENG-RECOVERY",
                "ENG-MONITORING",
                "ENG-DESCRIPTION",
                "PERIOD-01",
            ],
        },
        "SH-ASS-004": {
            "ACTION-S-DESCRIPTION": [
                "POPULATION-01",
                "DESCRIPTION-CONFIG-01",
                "DESCRIPTION-01",
                "DISCLOSURE-REVIEW-01",
                "REVIEW-DESCRIPTION",
                "CUSTOMER-RELEASE-01",
            ],
            "CHECK-SOC2:CC4.1": [
                "PROGRAMME-01",
                "INDEPENDENCE-01",
                "WP-NONTECHNICAL-01",
                "WP-TECHNICAL-01",
                "REVIEW-RECOVERY",
                "REPORT-01",
            ],
            "IMPLEMENTATION": [
                "DESCRIPTION-CONFIG-01",
                "ACCESS-01",
                "POPULATION-01",
                "REVIEW-DESCRIPTION",
            ],
            "TOD": [
                "SCOPE-01",
                "INDEPENDENCE-01",
                "POPULATION-01",
                "DESCRIPTION-CONFIG-01",
                "DISCLOSURE-REVIEW-01",
            ],
            "TOE": [
                "POPULATION-01",
                "WP-TECHNICAL-01",
                "WP-NONTECHNICAL-01",
                "DISCLOSURE-REVIEW-01",
                "PERIOD-01",
            ],
        },
    }
    return {
        f"TASK-{control}-corporate-{suffix}": [
            {k: ref[k] for k in FIELDS} for ref in refs if ref["record"] in names
        ]
        for control, routes in source_sets.items()
        for suffix, names in routes.items()
    }


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
    path.chmod(0o600)


def _provenance(scenario: str) -> dict:
    return {
        "source_reference": SOURCE_REFERENCE,
        "source_pins": SOURCE_PINS,
        "upstream_pins": UPSTREAM,
        "history_branch": BRANCHES[scenario],
        "qualification": (
            "AUTHORED_COMPANY_INTERNAL_EVALUATION_NO_SERVICE_AUDITOR_OPINION_OR_TASK_CREDIT"
        ),
    }


def _receipt(context: dict, records: dict) -> dict:
    return {
        "schema": SCHEMA,
        "company": COMPANY,
        "branches": BRANCHES,
        "records": records,
        "source_pins": SOURCE_PINS,
        "upstream_pins": UPSTREAM,
        "native_versions_per_branch": {s: len(_expected_rows(context, s)) for s in BRANCHES},
        "integration_leads_by_task": {s: _lead_map(records[s]) for s in BRANCHES},
        "selected_period": PERIOD,
        "selected_internal_workstreams_per_branch": 3,
        "prior_originals_changed": False,
        "independent_scenario_acceptance": "PENDING",
        "enterprise_source_complete": False,
        "audit_task_credit": False,
        "external_assurance_opinion_count": 0,
        "actual_external_message_count": 0,
        "fresh_audit_pair_created": False,
        "limits": LIMITS,
    }


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    private._private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("Fresh private assurance destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(
        prefix=".assurance-operations-", dir=destination.parent
    ) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            records[scenario] = []
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            for item in _expected_rows(context, scenario):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    item["system"],
                    item["record"],
                    expected_version=item["version"] - 1,
                    command_id=f"ASSURANCE-{branch}-{item['record']}-V{item['version']}",
                    event_at=item["event_at"],
                    available_at=item["available_at"],
                    content=encoded(item["body"]),
                    provenance=_provenance(scenario),
                )
                if ref["sha256"] != item["sha256"]:
                    raise CompanyStoreError("Assurance native source serialization differs")
                records[scenario].append(ref)
        _write(stage / "RECEIPT.json", _receipt(context, records))
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": sum(len(r) for r in records.values()),
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return manifest


def _verify_immutable_triggers(db: sqlite3.Connection) -> None:
    expected = {
        f"no_{noun}_{verb.lower()}": (
            f"CREATE TRIGGER no_{noun}_{verb.lower()} BEFORE {verb} ON {table} "
            f"BEGIN SELECT RAISE(ABORT,'Immutable {message}'); END"
        )
        for noun, table, message in (
            ("version", "versions", "source"),
            ("collection", "collections", "collection"),
        )
        for verb in ("UPDATE", "DELETE")
    }
    observed = {
        row["name"]: " ".join(row["sql"].split())
        for row in db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")
    }
    if observed != expected:
        raise CompanyStoreError("Assurance exact immutable-source triggers differ")


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = private._private(destination, directory=True)
    paths = {
        "manifest": root / "MANIFEST.json",
        "receipt": root / "RECEIPT.json",
        "database": root / "company.sqlite3",
    }
    if {p.name for p in root.iterdir()} != {"MANIFEST.json", "RECEIPT.json", "company.sqlite3"}:
        raise CompanyStoreError("Exact private three-file assurance source required")
    before = private._frozen(paths)
    manifest = json.loads(paths["manifest"].read_text())
    receipt = json.loads(paths["receipt"].read_text())
    context = _context(repository, private_repository)
    expected = {s: _expected_rows(context, s) for s in BRANCHES}
    count = sum(len(r) for r in expected.values())
    if (
        manifest
        != {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": before["receipt"][-1],
            "company_db_sha256": before["database"][-1],
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": count,
            "audit_task_credit": False,
        }
        or set(receipt.get("records", {})) != set(BRANCHES)
        or receipt != _receipt(context, receipt["records"])
    ):
        raise CompanyStoreError("Assurance manifest/receipt qualification differs")
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        _verify_immutable_triggers(db)
        if (
            db.execute("PRAGMA quick_check").fetchone()[0] != "ok"
            or db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != count
            or {tuple(r) for r in db.execute("SELECT company,branch,system,owner FROM systems")}
            != {
                (COMPANY, branch, system, owner)
                for branch in BRANCHES.values()
                for system, owner in SYSTEM_OWNERS.items()
            }
            or any(
                db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("grants", "collections", "access_events")
            )
        ):
            raise CompanyStoreError("Assurance native custody/integrity/access boundary differs")
        for scenario, branch in BRANCHES.items():
            refs = receipt["records"][scenario]
            if len(refs) != len(expected[scenario]):
                raise CompanyStoreError("Assurance branch roster incomplete")
            for ref, item in zip(refs, expected[scenario], strict=True):
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    (COMPANY, branch, item["system"], item["record"], item["version"]),
                ).fetchone()
                if (
                    row is None
                    or any(
                        ref[k] != item[k]
                        for k in (
                            "system",
                            "record",
                            "version",
                            "sha256",
                            "event_at",
                            "available_at",
                        )
                    )
                    or ref["company"] != COMPANY
                    or ref["branch"] != branch
                    or ref["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["provenance"] != _provenance(scenario)
                    or row["origin"] != ref["origin"]
                    or json.loads(row["provenance"]) != _provenance(scenario)
                    or row["content"] != encoded(item["body"])
                    or row["sha256"] != item["sha256"]
                    or any(row[k] != ref[k] for k in ("event_at", "available_at", "imported_at"))
                    or datetime.fromisoformat(row["imported_at"])
                    >= datetime.fromisoformat(row["event_at"])
                ):
                    raise CompanyStoreError("Assurance native original/provenance/clock differs")
    if private._frozen(paths) != before:
        raise CompanyStoreError("Assurance source changed during verification")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    args = parser.parse_args()
    result = (create if args.action == "create" else verify)(
        args.destination, repository=args.repository, private_repository=args.private_repository
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
