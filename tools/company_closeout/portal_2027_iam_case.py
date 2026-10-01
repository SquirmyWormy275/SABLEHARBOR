"""Generate the selected two-role Q1 2027 fictional company IAM source ledger.

The future role grants and no-other-selected-role-change assumption are newly
authored scenario inputs. No access-review performance or live deployment follows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .portal_2027_iam_source import sha256, unique

SOURCE = Path("enterprise/operations/source/portal_2027_payroll_release_q1_2026_09_29.json")
POLICY = Path("enterprise/ccf/assurance/design_data/control_procedures.json")


def derive_case(records: dict, case: dict, policy: list[dict]) -> dict:
    if (
        case["state"] != "PROVISIONAL_NEWLY_AUTHORED_FICTIONAL_CASE"
        or case["fact_status"] != "MODELED_FUTURE_CASE_EVENTS_NOT_2026_ACTUAL"
        or case["repository_acceptance_at"] is not None
        or case["available_at"] is not None
        or case["repository_available_at"] is not None
        or records["repository_source_commit"] != case["source_commit"]
    ):
        raise ValueError("Case authority, temporal or source state differs")
    if case["control_id"] != "SH-IAM-007" or case["legal_operator"] != "SHI":
        raise ValueError("Wrong control or legal operator")
    if case["service_id"] != "SH-ESS-PAYROLL-RELEASE":
        raise ValueError("Wrong bounded service")
    procedures = [row for row in policy if row["control_id"] == "SH-IAM-007"]
    if len(procedures) != 1 or not procedures[0]["procedure"].startswith(
        "Quarterly for privileged access"
    ):
        raise ValueError("IAM-007 source procedure differs")

    people = unique(records["tables"]["people"], "person_id")
    principals = unique(records["tables"]["access"], "person_id")
    approvals = unique(records["tables"]["approvals"], "batch_id")
    if len(approvals) != case["august_source_approval_count"] or len(approvals) != 10:
        raise ValueError("Prior payroll approval population differs")
    roles = case["newly_authored_role_grants"]
    unique(roles, "event_id")
    unique(roles, "person_id")
    unique(roles, "service_account_id")
    if len(roles) != 2 or {r["source_approval_field"] for r in roles} != {
        "preparer_id",
        "reviewer_id",
    }:
        raise ValueError("Selected two-role grant population differs")
    for role in roles:
        person_id = role["person_id"]
        if (
            person_id not in people
            or person_id not in principals
            or people[person_id]["legal_employer"] != "SHI"
            or people[person_id]["unit"] != "ess"
            or role["declared_company_principal_id"] != principals[person_id]["principal_id"]
            or role["privileged_for_scope"] is not True
            or role["event_status"] != "MODELED_CASE_GRANT_NOT_REAL_DEPLOYMENT"
            or any(a[role["source_approval_field"]] != person_id for a in approvals.values())
        ):
            raise ValueError("Role holder, privilege or accepted approval lineage differs")
    if {(r["source_approval_field"], r["right"]) for r in roles} != {
        ("preparer_id", "PREPARE_PAYROLL_BATCH"),
        ("reviewer_id", "APPROVE_PAYROLL_BATCH"),
    }:
        raise ValueError("Selected payroll authorization rights differ")

    prior = case["prior_period_bridge"]
    events = unique(records["tables"]["change_events"], "event_id")
    if (
        set(events) != {prior["known_exit_event_id"]}
        or prior["known_exit_is_in_selected_role_scope"] is not False
        or events[prior["known_exit_event_id"]]["person_id"] in {r["person_id"] for r in roles}
        or prior["september_december_complete_company_jml"] is not False
        or prior["unrepresented_jml_count"] is not None
        or not prior["september_december_selected_role_continuity"].startswith("UNKNOWN")
    ):
        raise ValueError("Sep-Dec unknown bridge improperly filled")
    period = case["period"]
    due = case["review_requirement"]
    if (
        period["start"] != "2027-01-01T00:00:00Z"
        or period["end_exclusive"] != "2027-04-01T00:00:00Z"
        or any(r["effective_at"] != period["start"] for r in roles)
        or not period["start"] < due["due_at"] < period["end_exclusive"]
        or due["source_status"] != "NEWLY_AUTHORED_PROVISIONAL_COMPANY_CASE_RULE"
        or due["independent_reviewer_required"] is not True
        or due["owner_decision_source_ids"] != []
        or due["removal_verification_source_ids"] != []
        or due["exception_source_ids"] != []
        or case["other_selected_scope_q1_jml_events"] != []
        or not case["selected_scope_event_population"].startswith(
            "NEWLY_AUTHORED_TWO_GRANTS_AND_NO_OTHER_SELECTED_ROLE_CHANGE"
        )
    ):
        raise ValueError("Q1 period, JML or review performance source differs")
    if set(case["case_branches"]) != {"A", "B"} or any(
        branch != {"common_source": True, "company_delta_state": "NOT_AUTHORED"}
        for branch in case["case_branches"].values()
    ):
        raise ValueError("Public A/B case delta invented")

    return {
        "record_id": "SH-PORTAL-IAM007-PAYROLL-RELEASE-Q1-2027-LEDGER-v0.1",
        "source_record_id": case["record_id"],
        "source_state": case["state"],
        "scenario": case["scenario"],
        "fact_status": case["fact_status"],
        "source_authored_at": case["authored_at"],
        "source_available_at": case["available_at"],
        "repository_available_at": case["repository_available_at"],
        "repository_acceptance_at": None,
        "known_on_state": "PENDING_REPOSITORY_ACCEPTANCE_NOT_QUERYABLE_AS_CASE_EVIDENCE",
        "accepted_august_source_commit": case["source_commit"],
        "accepted_august_approval_ids": sorted(approvals),
        "accepted_august_approval_count": len(approvals),
        "fictional_completion_authority": case["fictional_completion_authority"],
        "control_id": case["control_id"],
        "service_id": case["service_id"],
        "legal_operator": case["legal_operator"],
        "unit": case["unit"],
        "scope": case["scope"],
        "period": period,
        "prior_period_bridge": prior,
        "q1_selected_scope_jml": {
            "declared_2027_grant_count": len(roles),
            "declared_other_change_count": 0,
            "source_state": case["selected_scope_event_population"],
            "events": roles,
            "universal_company_jml_count": None,
        },
        "q1_review_schedule": {
            "campaign_id": due["campaign_id"],
            "due_at": due["due_at"],
            "unit": due["expected_decision_unit"],
            "selected_privileged_role_accounts_due": len(roles),
            "supplied_owner_decision_sources": 0,
            "supplied_removal_verification_sources": 0,
            "due_state_at_authoring": "FUTURE_DUE_NOT_RUN",
            "case_cutoff_without_successor_evidence": "TWO_DECISIONS_WOULD_LACK_SOURCE",
            "actual_q1_performance_conclusion": None,
            "independent_reviewer_required": True,
            "source_status": due["source_status"],
        },
        "case_branches": case["case_branches"],
        "limits": case["limits"],
    }


def load_case(records_path: Path, receipt_path: Path, root: Path) -> dict:
    case = json.loads((root / SOURCE).read_text())
    if sha256(records_path) != case["source_records_sha256"]:
        raise ValueError("Accepted records byte pin mismatch")
    if sha256(receipt_path) != case["source_receipt_sha256"]:
        raise ValueError("Accepted receipt byte pin mismatch")
    receipt = json.loads(receipt_path.read_text())
    if (
        receipt["source_commit"] != case["source_commit"]
        or receipt["status"] != "ACCEPTED_SCOPED_EDITION"
    ):
        raise ValueError("Accepted release scope mismatch")
    records = json.loads(records_path.read_text())
    policy = json.loads((root / POLICY).read_text())
    return derive_case(records, case, policy)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = (
        json.dumps(
            load_case(args.records, args.receipt, args.source_root), indent=2, sort_keys=True
        )
        + "\n"
    ).encode()
    if args.check:
        if args.output.read_bytes() != payload:
            raise ValueError("Stale Q1 case ledger")
    else:
        if args.output.exists():
            raise ValueError("Output exists; use --check or new version")
        args.output.write_bytes(payload)
    print("PASS selected two-role Q1 IAM case ledger")


if __name__ == "__main__":
    main()
