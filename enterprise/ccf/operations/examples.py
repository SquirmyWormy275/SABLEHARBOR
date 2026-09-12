"""Invented records exercise assertions and durable workflow; never actual evidence."""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from . import store, testing

AT = "2026-09-10T10:00:00+00:00"
END = "2026-09-09T23:59:59+00:00"
EXPIRY = "2026-10-01T00:00:00+00:00"


def record(adapter, boundary, failed=False):
    early = "2026-09-09T09:00:00+00:00"
    good = "2026-09-09T09:10:00+00:00"
    due = "2026-09-09T09:30:00+00:00"
    late = "2026-09-09T11:00:00+00:00"
    d = {
        "termination": dict(
            enabled=False,
            active_entitlements=0,
            terminated_at=early,
            disabled_at=late if failed else good,
            due_at=due,
        ),
        "access_review": dict(
            reviewer="DEMO-REVIEWER",
            account_owner="DEMO-WORKER",
            reviewed_at=good,
            due_at=due,
            decision="REMOVE",
            active=failed,
            removed_at=good,
            removal_due_at=due,
        ),
        "backup_job": dict(
            status="FAILED" if failed else "SUCCESS",
            scheduled_at=early,
            completed_at=good,
            due_at=due,
            expected_sha256="a" * 64,
            observed_sha256="a" * 64,
        ),
        "restore": dict(
            started_at=early,
            completed_at=late if failed else good,
            recovery_point_at=early,
            rto_seconds=1800,
            rpo_seconds=300,
            expected_sha256="a" * 64,
            observed_sha256="a" * 64,
            dependencies_ready=True,
            suppressed_data_absent=True,
        ),
        "configuration_drift": dict(
            approved_baseline="DEMO-BASELINE-1",
            observed_baseline="DEMO-BASELINE-1",
            unresolved_drift_count=1 if failed else 0,
        ),
        "incident_escalation": dict(
            detected_at=early,
            escalated_at=good,
            due_at=due,
            required_recipient_ids=["DEMO-ONCALL", "DEMO-SECURITY"],
            notified_recipient_ids=["DEMO-ONCALL"] if failed else ["DEMO-ONCALL", "DEMO-SECURITY"],
        ),
        "vulnerability": dict(
            status="REMEDIATED",
            detected_at=early,
            verified_at=late if failed else good,
            due_at=due,
            verifier="DEMO-REVIEWER",
            remediator="DEMO-ENGINEER",
            verification_clear=True,
        ),
        "training": dict(
            required_course_version="DEMO-COURSE-2",
            completed_course_version="DEMO-COURSE-1" if failed else "DEMO-COURSE-2",
            assigned_at=early,
            completed_at=good,
            due_at=due,
            assessment_passed=True,
        ),
    }[adapter]
    return dict(
        id="DEMO-" + adapter,
        origin="SYNTHETIC",
        boundary_id=boundary,
        occurred_at=early,
        kind=adapter,
        data=d,
    )


def scope():
    return dict(
        origin="SYNTHETIC",
        period_start="2026-09-09T00:00:00+00:00",
        period_end=END,
        service="DEMO-SERVICE",
        implementation_version="DEMO-V1",
        criteria_authority="DEMO-CRITERIA-ONLY-NOT-APPROVED-TARGETS",
    )


def population(records):
    ids = [r["id"] for r in records]
    raw = json.dumps(ids)
    return dict(
        expected_ids=ids,
        excluded_ids=[],
        source_count=len(ids),
        source_system="DEMO-EXPORT",
        query="DEMO full independent scoped ID export",
        reconciliation="Invented independent census; no vendor connection",
        criteria_review="Synthetic fixture criteria and manual steps reviewed for demonstration only",
        source_export_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        census_json=raw,
        captured_at="2026-09-10T09:00:00+00:00",
    )


def submission(plan, records):
    return dict(
        raw_json=json.dumps(records),
        captured_at="2026-09-10T09:00:00+00:00",
        expires_at=EXPIRY,
        source_system="DEMO-EXPORT",
        extraction_query="DEMO full scoped records",
        transformation_version="DEMO-JSON-1",
        manual_tests={
            cid: dict(
                result="PASS",
                rationale="SYNTHETIC fixture observation only; no actual procedure or framework acceptance",
                record_ids=[r["id"] for r in records],
            )
            for cid in plan["criteria"]
        },
    )


def principals(boundaries):
    return [
        dict(
            id=who,
            permissions=permissions,
            boundaries=boundaries,
            valid_from="2026-01-01T00:00:00+00:00",
            expires_at="2027-01-01T00:00:00+00:00",
        )
        for who, permissions in [
            ("DEMO-PREPARER", ["prepare"]),
            ("DEMO-REVIEWER", ["review"]),
            ("DEMO-ADMIN", ["admin"]),
        ]
    ]


def build(output, plans):
    output = Path(output)
    output.mkdir(parents=True, mode=0o700)
    boundaries = sorted({p["boundary_id"] for p in plans.values()})
    tokens = store.initialize(output / "workflow.sqlite3", plans, principals(boundaries))
    db = store.connect(output / "workflow.sqlite3")
    outcomes = []
    try:
        with patch.object(store, "now", return_value=AT):
            for cid, adapter in testing.ADAPTERS.items():
                p = next(p for p in plans.values() if p["control_id"] == cid)
                for failed in (False, True):
                    case = "DEMO-" + adapter + ("-negative" if failed else "-positive")
                    rows = [record(adapter, p["boundary_id"], failed)]
                    store.command(
                        db,
                        tokens["DEMO-PREPARER"],
                        case,
                        "create",
                        dict(plan_id=p["id"], scope=scope()),
                        0,
                    )
                    store.command(
                        db, tokens["DEMO-REVIEWER"], case, "population", population(rows), 1
                    )
                    state = store.command(
                        db, tokens["DEMO-PREPARER"], case, "intake", submission(p, rows), 2
                    )
                    state = store.command(
                        db,
                        tokens["DEMO-REVIEWER"],
                        case,
                        "review",
                        dict(
                            submission_id=state["submissions"][-1]["id"],
                            decision="ACCEPT",
                            rationale="Independent synthetic demonstration review",
                        ),
                        3,
                    )
                    expected = "FINDING_OPEN" if failed else "REVIEWED_PASS"
                    if state["state"] != expected:
                        raise ValueError(
                            "Synthetic adapter result differs from expected independent case"
                        )
                    outcomes.append(
                        dict(case=case, control_id=cid, expected=expected, observed=state["state"])
                    )
            case = "DEMO-termination-negative"
            state = store.command(
                db,
                tokens["DEMO-PREPARER"],
                case,
                "remediate",
                dict(
                    change_reference="DEMO-CHANGE-1",
                    action="Correct lifecycle execution prospectively",
                    due_at="2026-09-20T00:00:00+00:00",
                ),
                4,
            )
            p = plans[state["plan_id"]]
            rows = [record("termination", p["boundary_id"])]
            state = store.command(
                db, tokens["DEMO-PREPARER"], case, "intake", submission(p, rows), 5
            )
            state = store.command(
                db,
                tokens["DEMO-REVIEWER"],
                case,
                "review",
                dict(
                    submission_id=state["submissions"][-1]["id"],
                    decision="ACCEPT",
                    rationale="Invented same-period corrected source cannot erase original failed timing",
                ),
                6,
            )
            if state["state"] != "RETEST_PASSED_HISTORICAL_FAILURE":
                raise ValueError("Historical failure was concealed")
        with patch.object(store, "now", return_value="2026-09-12T10:00:00+00:00"):
            future = "DEMO-termination-prospective"
            prospective_scope = scope()
            prospective_scope.update(
                period_start="2026-09-11T00:00:00+00:00",
                period_end="2026-09-11T23:59:59+00:00",
                implementation_version="DEMO-V2",
            )
            rows = json.loads(json.dumps(rows).replace("2026-09-09", "2026-09-11"))
            pop = population(rows)
            pop["captured_at"] = "2026-09-12T09:00:00+00:00"
            sub = submission(p, rows)
            sub["captured_at"] = pop["captured_at"]
            store.command(
                db,
                tokens["DEMO-PREPARER"],
                future,
                "create",
                dict(plan_id=p["id"], scope=prospective_scope),
                0,
            )
            store.command(db, tokens["DEMO-REVIEWER"], future, "population", pop, 1)
            state = store.command(db, tokens["DEMO-PREPARER"], future, "intake", sub, 2)
            store.command(
                db,
                tokens["DEMO-REVIEWER"],
                future,
                "review",
                dict(
                    submission_id=state["submissions"][-1]["id"],
                    decision="ACCEPT",
                    rationale="Independent prospective synthetic validation",
                ),
                3,
            )
            state = store.command(
                db,
                tokens["DEMO-REVIEWER"],
                case,
                "close_prospectively",
                dict(
                    validation_case_id=future,
                    rationale="Later correction validated; original period remains failed",
                ),
                7,
            )
            if state["original_outcome"] != "FAIL":
                raise ValueError("Closure rewrote original result")
            report = store.report(db, tokens["DEMO-REVIEWER"])
    finally:
        db.close()
    summary = dict(
        plans=len(plans),
        baseline_controls=len({p["control_id"] for p in plans.values()}),
        automated_controls=len(testing.ADAPTERS),
        manual_only_controls=len({p["control_id"] for p in plans.values()}) - len(testing.ADAPTERS),
        cases=len(report["cases"]),
        positive_and_negative_checks=outcomes,
        historical_failure_preserved=True,
        authority="SYNTHETIC_LOCAL_EXERCISE_ONLY",
    )
    artifacts = {
        "TEST_PLANS.json": plans,
        "ASSESSMENT_REPORT.json": report,
        "EXERCISE_RESULTS.json": summary,
    }
    for name, value in artifacts.items():
        path = output / name
        path.write_text(json.dumps(value, indent=2) + "\n")
        path.chmod(0o600)
    for subject, token in tokens.items():
        path = output / (subject + ".credential")
        path.write_text(token + "\n")
        path.chmod(0o600)
    start = output / "START_HERE.md"
    start.write_text(
        "# Baseline evidence intake and workflow\n\n"
        "[Test plans](TEST_PLANS.json) · [Exercise results](EXERCISE_RESULTS.json) · [Assessment history](ASSESSMENT_REPORT.json)\n\n"
        f"{summary['plans']} plans cover {summary['baseline_controls']} baseline controls and all three reference boundaries. Eight controls have bounded automated assertions alongside mandatory human tests; 62 use manual tests. These assertions do not establish complete control or framework coverage.\n\n"
        "The retained local database contains 16 positive/negative cases and one prospective validation. It records independently registered populations, raw exports, manual observations, computed assertions, assignments, independent reviews and remediation history. A passing same-period retest leaves the original failure intact; prospective closure links a later independently passed case.\n\n"
        "Every case and credential is explicitly synthetic. No live connection, appointment, deployed service, actual evidence or external assurance is asserted. The local workflow authenticates random credentials with scoped, expiring grants; an administrator with filesystem/database access remains trusted. A trusted local operator controls this store. Isolated multi-user deployment still needs a service boundary and enterprise identity integration.\n\n"
        "For actual intake, initialize a separate private store, configure authorized subjects, create an OPERATOR_SUPPLIED case with explicit service/period/criteria authority, and independently register its source population. Export records as the documented JSON envelope. Source-specific vendor APIs and enterprise identity-provider integration remain external integration work.\n"
    )
    start.chmod(0o600)
    return summary
