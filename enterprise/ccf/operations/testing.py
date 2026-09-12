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
}


def instant(value):
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
        or not all(isinstance(x, str) and x for x in value)
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
            or instant(d["removed_at"]) <= instant(d["removal_due_at"]),
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
    if len(set(ids)) != len(ids) or set(ids) != set(population["expected_ids"]):
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
        if not applicable:
            reasons.append("No structured records for the declared automated adapter")
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
