"""Bounded record assertions plus explicit human tests for every baseline procedure."""

import hashlib
import json
from datetime import datetime, timezone

from enterprise.ccf.registry import digest

ADAPTERS = {
    "SH-IAM-004": "termination",
    "SH-IAM-007": "access_review",
    "SH-BCM-002": "backup_job",
    "SH-BCM-003": "restore",
    "SH-CFG-002": "configuration_drift",
    "SH-INC-001": "incident_escalation",
    "SH-SEC-003": "vulnerability",
    "SH-TRN-002": "training",
    "SH-IAM-001": "identity_creation",
    "SH-IAM-002": "access_grant",
    "SH-IAM-003": "mover_access",
    "SH-IAM-005": "privilege_expiry",
    "SH-IAM-006": "service_account",
    "SH-ENG-002": "revision_review",
    "SH-ENG-003": "release_tests",
    "SH-ENG-004": "deployment_artifact",
    "SH-CFG-001": "asset_inventory",
    "SH-REC-004": "disposal",
    "SH-POL-003": "exception_validity",
    "SH-GOV-003": "delegated_decision",
    "SH-ETH-001": "conduct_acknowledgment",
    "SH-SEC-002": "log_coverage",
    "SH-ASS-005": "corrective_retest",
    "SH-PRD-003": "change_notice",
}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Timestamp requires a time zone")
    return parsed.astimezone(timezone.utc)


def nonempty(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Nonempty text required")
    return value


def plans(reference):
    """Preserve each baseline/added duty; automated assertions never replace them."""
    rows = reference["evidence_checklist"]
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate collection plan")
    result = {}
    reference_digest = digest(reference)
    for r in rows:
        criteria = {"BASE": r["baseline_test"]}
        for step in r["added_steps"]:
            aid = step["action_id"]
            if aid in criteria:
                raise ValueError("Duplicate procedure step")
            criteria[aid] = step["test"]
        body = dict(
            id=r["id"],
            control_id=r["control_id"],
            boundary_id=r["boundary_id"],
            owner_role_id=r["owner_role_id"],
            trigger=r["trigger"],
            proposed_source_system=r["proposed_source_system"],
            required_records=r["required_records"],
            procedure=r["procedure"],
            additional_procedures=r["added_steps"],
            population_rule=r["population"],
            boundary_test=r["boundary_test"],
            criteria=criteria,
            adapter=ADAPTERS.get(r["control_id"]),
            testing_mode="BOUNDED_AUTOMATION_AND_MANUAL"
            if r["control_id"] in ADAPTERS
            else "MANUAL",
            mapping_acceptance="NOT_ASSERTED",
            reference_digest=reference_digest,
        )
        result[r["id"]] = body
    return result


def numeric(value):
    if type(value) not in (int, float) or not 0 <= value < float("inf"):
        raise ValueError("Finite nonnegative number required")
    return value


def boolean(value):
    if type(value) is not bool:
        raise ValueError("Boolean required")
    return value


def identifiers(value):
    if (
        not isinstance(value, list)
        or not all(isinstance(x, str) and x.strip() for x in value)
        or len(value) != len(set(value))
    ):
        raise ValueError("Expected unique identifier list")
    return set(value)


def sha(value):
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("Expected SHA256")
    return value


def sequence(d, *fields):
    """All timestamps are timezone-aware; equality is permitted for atomic events."""
    times = [instant(d[k]) for k in fields]
    return times == sorted(times)


def population_match(expected, actual):
    required, observed = identifiers(expected), identifiers(actual)
    return bool(required) and required == observed


def automated(adapter, row):
    """A PASS covers only these assertions, not the entire control or framework."""
    d = row["data"]
    if adapter == "termination":
        checks = {
            "disabled": boolean(d["enabled"]) is False,
            "rights_removed": type(d["active_entitlements"]) is int
            and d["active_entitlements"] == 0,
            "timely": instant(d["terminated_at"])
            <= instant(d["disabled_at"])
            <= instant(d["due_at"]),
        }
    elif adapter == "access_review":
        checks = {
            "independent": nonempty(d["reviewer"]) != nonempty(d["account_owner"]),
            "timely_review": instant(d["reviewed_at"]) <= instant(d["due_at"]),
            "valid_decision": d["decision"] in {"RETAIN", "REMOVE"},
            "decision_enforced": boolean(d["active"]) == (d["decision"] == "RETAIN"),
            "removal_timely": d["decision"] != "REMOVE"
            or instant(d["reviewed_at"])
            <= instant(d["removed_at"])
            <= instant(d["removal_due_at"]),
        }
    elif adapter == "backup_job":
        checks = {
            "completed": d["status"] == "SUCCESS",
            "timely": instant(d["scheduled_at"])
            <= instant(d["completed_at"])
            <= instant(d["due_at"]),
            "artifact_matches": sha(d["expected_sha256"]) == sha(d["observed_sha256"]),
        }
    elif adapter == "restore":
        start, end, point = (
            instant(d[k]) for k in ("started_at", "completed_at", "recovery_point_at")
        )
        checks = {
            "rto": 0 <= (end - start).total_seconds() <= numeric(d["rto_seconds"]),
            "rpo": 0 <= (start - point).total_seconds() <= numeric(d["rpo_seconds"]),
            "content": sha(d["expected_sha256"]) == sha(d["observed_sha256"]),
            "dependencies": boolean(d["dependencies_ready"]),
            "suppressed_data_absent": boolean(d["suppressed_data_absent"]),
        }
    elif adapter == "configuration_drift":
        checks = {
            "authorized_baseline": nonempty(d["approved_baseline"])
            == nonempty(d["observed_baseline"]),
            "no_unresolved_drift": type(d["unresolved_drift_count"]) is int
            and d["unresolved_drift_count"] == 0,
        }
    elif adapter == "incident_escalation":
        checks = {
            "timely": instant(d["detected_at"])
            <= instant(d["escalated_at"])
            <= instant(d["due_at"]),
            "required_recipients": bool(d["required_recipient_ids"])
            and identifiers(d["required_recipient_ids"])
            <= identifiers(d["notified_recipient_ids"]),
        }
    elif adapter == "vulnerability":
        checks = {
            "remediated": d["status"] == "REMEDIATED",
            "timely": instant(d["detected_at"])
            <= instant(d["verified_at"])
            <= instant(d["due_at"]),
            "independent": nonempty(d["verifier"]) != nonempty(d["remediator"]),
            "verification_clear": boolean(d["verification_clear"]),
        }
    elif adapter == "training":
        checks = {
            "correct_course": nonempty(d["required_course_version"])
            == nonempty(d["completed_course_version"]),
            "timely": instant(d["assigned_at"])
            <= instant(d["completed_at"])
            <= instant(d["due_at"]),
            "assessment_passed": boolean(d["assessment_passed"]),
        }
    elif adapter == "identity_creation":
        checks = {
            "approved_request": nonempty(d["approved_request_id"])
            == nonempty(d["creation_request_id"]),
            "sponsor": nonempty(d["sponsor_id"]) != nonempty(d["identity_id"]),
            "identity_proofed": boolean(d["identity_proofed"]),
            "authorized_window": sequence(d, "approved_at", "start_at", "created_at", "end_at"),
        }
    elif adapter == "access_grant":
        checks = {
            "exact_approved_rights": population_match(
                d["approved_right_ids"], d["actual_right_ids"]
            ),
            "owner_approved": nonempty(d["approver_id"]) == nonempty(d["resource_owner_id"]),
            "independent": nonempty(d["approver_id"]) != nonempty(d["requester_id"]),
            "no_conflicts": not identifiers(d["conflicting_right_ids"]),
            "authorized_window": sequence(d, "approved_at", "granted_at", "expires_at"),
        }
    elif adapter == "mover_access":
        old = identifiers(d["old_right_ids"])
        new = identifiers(d["approved_new_right_ids"])
        actual = identifiers(d["actual_right_ids"])
        checks = {
            "exact_new_rights": actual == new,
            "obsolete_removed": not ((old - new) & actual),
            "timely_change": sequence(d, "approved_at", "effective_at", "reconciled_at", "due_at"),
        }
    elif adapter == "privilege_expiry":
        checks = {
            "separate_identity": nonempty(d["privileged_identity_id"])
            != nonempty(d["ordinary_identity_id"]),
            "limited_duration": sequence(
                d, "approved_at", "activated_at", "revoked_at", "expires_at"
            ),
            "inactive": not boolean(d["active"]),
            "sessions_retained": bool(identifiers(d["session_record_ids"])),
            "independent_review": nonempty(d["reviewer_id"]) != nonempty(d["operator_id"]),
            "review_after_use": sequence(d, "revoked_at", "reviewed_at", "review_due_at"),
        }
    elif adapter == "service_account":
        checks = {
            "owner_assigned": bool(nonempty(d["owner_id"])),
            "workload_assigned": bool(nonempty(d["workload_id"])),
            "exact_approved_rights": population_match(
                d["approved_right_ids"], d["actual_right_ids"]
            ),
            "rotation_current": sequence(d, "rotated_at", "observed_at", "rotation_due_at"),
            "review_current": sequence(d, "reviewed_at", "observed_at", "review_due_at"),
        }
    elif adapter == "revision_review":
        checks = {
            "exact_revision": sha(d["reviewed_revision_sha256"])
            == sha(d["merged_revision_sha256"]),
            "independent": nonempty(d["reviewer_id"]) != nonempty(d["author_id"]),
            "approved": d["decision"] == "APPROVE",
            "protected_branch": boolean(d["protected_branch"]),
            "review_before_merge": sequence(d, "proposed_at", "reviewed_at", "merged_at"),
        }
    elif adapter == "release_tests":
        checks = {
            "complete_mandatory_population": population_match(
                d["required_test_ids"], d["executed_test_ids"]
            ),
            "all_mandatory_passed": identifiers(d["required_test_ids"])
            <= identifiers(d["passed_test_ids"]),
            "no_failed_mandatory": not (
                identifiers(d["required_test_ids"]) & identifiers(d["failed_test_ids"])
            ),
            "consistent_results": not (
                identifiers(d["passed_test_ids"]) & identifiers(d["failed_test_ids"])
            ),
            "results_belong_to_execution": (
                identifiers(d["passed_test_ids"]) | identifiers(d["failed_test_ids"])
            )
            == identifiers(d["executed_test_ids"]),
            "exact_artifact": sha(d["tested_sha256"]) == sha(d["released_sha256"]),
            "before_release": sequence(d, "built_at", "tested_at", "released_at"),
        }
    elif adapter == "deployment_artifact":
        checks = {
            "exact_artifact": sha(d["approved_sha256"])
            == sha(d["pipeline_sha256"])
            == sha(d["runtime_sha256"]),
            "authorized_deployer": nonempty(d["deployment_identity_id"])
            in identifiers(d["authorized_identity_ids"]),
            "environment": nonempty(d["approved_environment"]) == nonempty(d["actual_environment"]),
            "rollback_reference": bool(nonempty(d["rollback_reference"])),
            "chronology": sequence(d, "approved_at", "deployed_at", "observed_at"),
        }
    elif adapter == "asset_inventory":
        checks = {
            "discovery_reconciles": population_match(
                d["discovered_asset_ids"], d["registered_asset_ids"]
            ),
            "ownership_complete": population_match(d["registered_asset_ids"], d["owned_asset_ids"]),
            "current_reconciliation": sequence(d, "discovered_at", "reconciled_at", "due_at"),
        }
    elif adapter == "disposal":
        checks = {
            "no_hold": not boolean(d["legal_hold"]),
            "authorized": nonempty(d["approver_id"]) in identifiers(d["authorized_approver_ids"]),
            "retention_elapsed": sequence(d, "retention_ends_at", "disposed_at"),
            "authorized_before_execution": sequence(d, "approved_at", "disposed_at"),
            "active_copies_deleted": population_match(d["active_copy_ids"], d["deleted_copy_ids"]),
            "backup_lifecycle_recorded": bool(nonempty(d["backup_lifecycle_reference"])),
            "certificate": bool(nonempty(d["destruction_certificate_id"])),
        }
    elif adapter == "exception_validity":
        checks = {
            "specific_requirement": bool(nonempty(d["requirement_id"])),
            "authorized": nonempty(d["approver_id"]) in identifiers(d["authorized_approver_ids"]),
            "unexpired": sequence(d, "approved_at", "effective_at", "observed_at")
            and instant(d["observed_at"]) < instant(d["expires_at"]),
            "compensation_recorded": bool(nonempty(d["compensating_measure_id"])),
            "compensation_observed": boolean(d["compensation_operating"]),
        }
    elif adapter == "delegated_decision":
        checks = {
            "authorized_actor": nonempty(d["approver_id"]) == nonempty(d["delegate_id"]),
            "matter_in_scope": nonempty(d["matter_id"]) in identifiers(d["permitted_matter_ids"]),
            "within_limit": numeric(d["decision_amount"]) <= numeric(d["delegated_limit"]),
            "same_currency": nonempty(d["decision_currency"]) == nonempty(d["limit_currency"]),
            "unexpired": sequence(d, "delegation_starts_at", "decided_at")
            and instant(d["decided_at"]) < instant(d["delegation_expires_at"]),
            "not_revoked": not boolean(d["revoked"]),
        }
    elif adapter == "conduct_acknowledgment":
        checks = {
            "exact_version": nonempty(d["required_version"]) == nonempty(d["acknowledged_version"]),
            "correct_recipient": nonempty(d["required_recipient_id"])
            == nonempty(d["acknowledger_id"]),
            "timely": sequence(d, "distributed_at", "acknowledged_at", "due_at"),
        }
    elif adapter == "log_coverage":
        checks = {
            "required_sources_reporting": bool(identifiers(d["required_source_ids"]))
            and identifiers(d["required_source_ids"]) <= identifiers(d["reporting_source_ids"]),
            "ingestion_gap": numeric(d["max_observed_gap_seconds"])
            <= numeric(d["approved_gap_seconds"]),
            "clock_skew": numeric(d["max_observed_skew_seconds"])
            <= numeric(d["approved_skew_seconds"]),
            "measured_window": instant(d["window_start"])
            < instant(d["window_end"])
            <= instant(d["measured_at"]),
        }
    elif adapter == "corrective_retest":
        checks = {
            "assigned": bool(nonempty(d["owner_id"])),
            "independent_retest": nonempty(d["retester_id"]) != nonempty(d["implementer_id"]),
            "timely_retest": sequence(d, "opened_at", "fixed_at", "retested_at", "due_at"),
            "retest_passed": boolean(d["retest_passed"]),
            "original_failure_retained": sha(d["original_failure_sha256"])
            == sha(d["retained_failure_sha256"]),
        }
    elif adapter == "change_notice":
        checks = {
            "all_required_recipients": bool(identifiers(d["required_recipient_ids"]))
            and identifiers(d["required_recipient_ids"])
            <= identifiers(d["delivered_recipient_ids"]),
            "exact_notice": sha(d["approved_notice_sha256"]) == sha(d["delivered_notice_sha256"]),
            "approved_and_timely": sequence(d, "approved_at", "delivered_at", "notice_due_at"),
            "required_lead_time": (
                instant(d["change_at"]) - instant(d["delivered_at"])
            ).total_seconds()
            >= numeric(d["required_lead_seconds"]),
        }
    else:
        raise ValueError("Unsupported automated adapter")
    return checks


def evaluate(plan, scope, population, submission, at):
    raw = submission["raw_json"]
    if not isinstance(raw, str) or len(raw.encode()) > 10_000_000:
        raise ValueError("Expected a JSON export of at most 10 MB")
    records = json.loads(raw)
    if not isinstance(records, list):
        raise ValueError("Export must contain a JSON array")
    start, end = instant(scope["period_start"]), instant(scope["period_end"])
    if start > end:
        raise ValueError("Assessment period is reversed")
    expected_ids = identifiers(population["expected_ids"])
    now = instant(at)
    captured, expires = instant(submission["captured_at"]), instant(submission["expires_at"])
    if not end <= captured <= now < expires:
        raise ValueError("Collection chronology or freshness invalid")
    for k in ("source_system", "extraction_query", "transformation_version"):
        nonempty(submission[k])
    if submission["source_system"] != population["source_system"]:
        raise ValueError("Source system differs from independently registered population")
    ids, reasons, checks = [], [], []
    for r in records:
        ids.append(nonempty(r["id"]))
        if r["origin"] != scope["origin"]:
            reasons.append("Mixed evidence origins")
        if r["boundary_id"] != plan["boundary_id"] or not start <= instant(r["occurred_at"]) <= end:
            reasons.append("Wrong boundary or period")
    if len(set(ids)) != len(ids) or set(ids) != expected_ids:
        reasons.append("Population does not reconcile to independently registered IDs")
    if reasons:
        return dict(
            outcome="NOT_RUN",
            reasons=sorted(set(reasons)),
            checks=[],
            manual=[],
            raw_digest=hashlib.sha256(raw.encode()).hexdigest(),
            observed_ids=ids,
        )
    if plan["adapter"]:
        applicable = [r for r in records if r["kind"] == plan["adapter"]]
        if len(applicable) != len(records) or not applicable:
            reasons.append("Every population record must use the declared automated adapter")
        for r in applicable:
            try:
                assertions = automated(plan["adapter"], r)
                checks.append(
                    dict(
                        record_id=r["id"],
                        assertions=assertions,
                        result="PASS" if all(assertions.values()) else "FAIL",
                    )
                )
            except (KeyError, TypeError, ValueError, OverflowError):
                reasons.append("Malformed structured record: " + r["id"])
    manual = submission["manual_tests"]
    if not isinstance(manual, dict) or set(manual) - set(plan["criteria"]):
        raise ValueError("Unknown manual criterion")
    for cid in plan["criteria"]:
        if cid not in manual:
            reasons.append("Manual test missing: " + cid)
            continue
        m = manual[cid]
        if m["result"] not in {"PASS", "FAIL", "NOT_RUN"}:
            raise ValueError("Invalid manual result")
        nonempty(m["rationale"])
        if not m["record_ids"] or not identifiers(m["record_ids"]) <= set(ids):
            raise ValueError("Manual test must cite retained evidence records")
        if m["result"] == "NOT_RUN":
            reasons.append("Manual criterion untested: " + cid)
    failed = any(c["result"] == "FAIL" for c in checks) or any(
        m["result"] == "FAIL" for m in manual.values()
    )
    return dict(
        outcome="FAIL" if failed else "NOT_RUN" if reasons else "PASS",
        reasons=reasons,
        checks=checks,
        manual=manual,
        raw_digest=hashlib.sha256(raw.encode()).hexdigest(),
        observed_ids=ids,
    )
