"""Reconcile a bounded fictional Q1 HR-to-IAM-to-review source chain.

This consumes, but never edits, the accepted two-account predecessor. The new
company source is a prospective fictional case with one performed review and one
missing decision. It is neither a live IAM deployment nor a whole-company census.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

SOURCE = Path(
    "enterprise/operations/source/portal_2027_payroll_release_q1_successor_2026_09_29.json"
)
DEFAULT_OUTPUT = Path("enterprise/operations/portal_2027_iam/payroll_release_q1_v0.2.json")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def when(value: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), "UTC timestamp required")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Valid UTC timestamp required") from exc


def index(rows: list[dict], key: str) -> dict[str, dict]:
    require(isinstance(rows, list), f"{key} rows required")
    result = {row[key]: row for row in rows}
    require(len(result) == len(rows), f"Duplicate {key}")
    return result


def derive(records: dict, predecessor: dict, source: dict) -> dict:
    accepted = source["accepted_predecessor"]
    require(
        predecessor["record_id"] == accepted["source_record_id"]
        and accepted["accepted_merge_commit"] == "2bbbd004628ec7eb45906c493a847a7c841e3908"
        and when(accepted["repository_available_not_before"]) <= when(source["authored_at"]),
        "Accepted predecessor or authoring chronology differs",
    )
    require(
        source["state"] == "PROVISIONAL_NEWLY_AUTHORED_FICTIONAL_CASE_SUCCESSOR"
        and source["fact_status"] == "MODELED_2027_IN_UNIVERSE_EVENTS_NOT_REAL_DEPLOYMENT"
        and source["repository_available_at"] is None
        and source["repository_acceptance_at"] is None,
        "Unaccepted successor promoted to available or actual",
    )
    release = source["accepted_august_release"]
    require(
        records["repository_source_commit"] == release["source_commit"]
        and len(records["tables"]["people"]) == 702,
        "Accepted August source or person census differs",
    )
    people = index(records["tables"]["people"], "person_id")
    access = index(records["tables"]["access"], "person_id")
    require(set(people) == set(access), "August people and principals differ")

    scope = source["scope"]
    prior_grants = index(predecessor["newly_authored_role_grants"], "service_account_id")
    account_ids = scope["included_service_account_ids"]
    require(
        scope["control_id"] == "SH-IAM-007"
        and scope["service_id"] == "SH-ESS-PAYROLL-RELEASE"
        and scope["legal_operator"] == "SHI"
        and scope["unit"] == "ess"
        and scope["complete_for_declared_function"] is True
        and len(account_ids) == len(set(account_ids)) == 2
        and set(account_ids) == set(prior_grants)
        and scope["period_start"] == predecessor["period"]["start"]
        and scope["period_end_exclusive"] == predecessor["period"]["end_exclusive"],
        "Declared service, period or account population differs",
    )
    start, end = when(scope["period_start"]), when(scope["period_end_exclusive"])
    opening = source["opening_state"]
    require(
        when(opening["as_of_exclusive"]) == start
        and start < when(opening["case_available_at"]) < end
        and opening["service_account_ids"] == []
        and opening["source_state"]
        == "NEWLY_AUTHORED_SYNTHETIC_ZERO_BASELINE_FOR_DECLARED_FUNCTION_ONLY",
        "Selected-service opening population differs",
    )

    delegations = index(source["role_delegations"], "role")
    expected_roles = {
        "SCOPED_SERVICE_OWNER_AND_GRANT_APPROVER": ("SH-EMP-ESS-0005", "ess"),
        "SCOPED_IAM_GRANT_IMPLEMENTER": ("SH-EMP-ESS-0006", "ess"),
        "SCOPED_HR_ROLE_APPROVER": ("SH-EMP-ESS-0007", "ess"),
        "INDEPENDENT_SECOND_LINE_VALIDATOR": (
            "SH-EMP-INTERNAL-AUDIT-0001",
            "internal-audit",
        ),
    }
    require(set(delegations) == set(expected_roles), "Scoped actor roles differ")
    for role, (person_id, unit) in expected_roles.items():
        row = delegations[role]
        require(
            row["person_id"] == person_id
            and people[person_id]["legal_employer"] == "SHI"
            and people[person_id]["unit"] == unit
            and when(row["effective_at"]) <= when(row["case_available_at"]) < start,
            "Delegated actor identity or chronology differs",
        )
    actors = {row["person_id"] for row in delegations.values()}
    require(len(actors) == 4, "Approver, implementer and reviewer must be distinct")
    owner = expected_roles["SCOPED_SERVICE_OWNER_AND_GRANT_APPROVER"][0]
    implementer = expected_roles["SCOPED_IAM_GRANT_IMPLEMENTER"][0]
    hr_approver = expected_roles["SCOPED_HR_ROLE_APPROVER"][0]
    validator = expected_roles["INDEPENDENT_SECOND_LINE_VALIDATOR"][0]

    hr = index(source["hr_role_events"], "person_id")
    authorizations = index(source["grant_authorizations"], "service_account_id")
    iam = index(source["iam_realization_events"], "service_account_id")
    require(
        len(hr) == len(authorizations) == len(iam) == 2
        and {r["person_id"] for r in prior_grants.values()} == set(hr)
        and set(authorizations) == set(iam) == set(account_ids)
        and source["other_selected_service_q1_jml_events"] == []
        and source["selected_service_jml_completion_basis"].startswith(
            "NEWLY_AUTHORED_SYNTHETIC_TWO_GRANT_CENSUS_ONLY"
        ),
        "Selected HR/IAM JML population differs",
    )
    for account_id in account_ids:
        old = prior_grants[account_id]
        person_id = old["person_id"]
        h, a, i = hr[person_id], authorizations[account_id], iam[account_id]
        require(
            person_id not in actors
            and people[person_id]["legal_employer"] == "SHI"
            and people[person_id]["unit"] == "ess"
            and access[person_id]["principal_id"] == old["declared_company_principal_id"]
            and h["action"] == "JOIN_SELECTED_SERVICE_FUNCTION"
            and h["person_id"] == a["person_id"] == i["person_id"] == person_id
            and h["right_requested"] == a["right"] == i["right"] == old["right"]
            and h["approved_by"] == hr_approver
            and a["approved_by"] == owner
            and a["assigned_implementer"] == i["implemented_by"] == implementer
            and a["hr_event_id"] == i["hr_event_id"] == h["event_id"]
            and i["authorization_id"] == a["event_id"]
            and i["modeled_predecessor_grant_id"] == old["event_id"]
            and i["state"] == "SYNTHETIC_IN_UNIVERSE_GRANT_NOT_REAL_DEPLOYMENT",
            "HR to authorization to IAM lineage or separation differs",
        )
        require(
            when(h["recorded_at"])
            <= when(h["case_available_at"])
            <= when(a["approved_at"])
            <= when(a["case_available_at"])
            < start
            and when(h["effective_at"]) == start
            and when(i["effective_at"]) == start
            and start < when(i["case_available_at"]) < end,
            "HR/IAM approval or effective chronology differs",
        )

    population = source["review_population"]
    due = predecessor["review_requirement"]
    require(
        population["campaign_id"] == due["campaign_id"]
        and population["source_state"].startswith(
            "COMPLETE_NEWLY_AUTHORED_SELECTED_FUNCTION_EXPORT"
        )
        and set(population["service_account_ids"]) == set(account_ids)
        and len(population["service_account_ids"]) == 2
        and start
        < when(population["as_of_exclusive"])
        == when(population["extracted_at"])
        < when(population["case_available_at"])
        < when(due["due_at"])
        < end,
        "Quarterly population or due window differs",
    )
    decisions = index(source["review_decisions"], "service_account_id")
    verifications = index(source["independent_verifications"], "service_account_id")
    require(
        len(decisions) == len(verifications) == 1
        and set(decisions) == set(verifications) <= set(account_ids),
        "Performed review population differs",
    )
    reviewed_id = next(iter(decisions))
    decision, verified = decisions[reviewed_id], verifications[reviewed_id]
    require(
        decision["campaign_id"] == population["campaign_id"]
        and decision["person_id"] == iam[reviewed_id]["person_id"]
        and decision["decision"] == "RETAIN_AUTHORIZED"
        and decision["observed_rights"]
        == decision["authorized_rights"]
        == [iam[reviewed_id]["right"]]
        and decision["decided_by"] == owner
        and verified["decision_id"] == decision["event_id"]
        and verified["verified_by"] == validator
        and verified["result"] == "DECISION_MATCHES_AUTHORED_SELECTED_SERVICE_RIGHT",
        "Review decision, rights or independent verification differs",
    )
    require(
        when(population["case_available_at"])
        < when(decision["decided_at"])
        <= when(decision["case_available_at"])
        < when(verified["verified_at"])
        <= when(verified["case_available_at"])
        <= when(due["due_at"]),
        "Review evidence after due or out of sequence",
    )
    missing_ids = set(account_ids) - set(decisions)
    missing = source["missing_decision_response"]
    require(
        len(missing_ids) == 1
        and missing["service_account_id"] in missing_ids
        and missing["campaign_id"] == due["campaign_id"]
        and missing["expected_decision_due_at"] == due["due_at"]
        and missing["owner_decision_source_id"] is None
        and missing["independent_verification_source_id"] is None
        and missing["state"] == "MISSING_OWNER_DECISION_AND_INDEPENDENT_VERIFICATION"
        and missing["escalated_by"] == validator
        and when(missing["detected_at"]) == end
        and end < when(missing["escalated_at"]) < when(missing["case_available_at"]),
        "Missing decision or prospective escalation hidden",
    )
    require(
        set(source["case_branches"]) == {"A", "B"}
        and all(
            b == {"common_source": True, "company_delta_state": "NOT_AUTHORED"}
            for b in source["case_branches"].values()
        ),
        "Private A/B delta invented in public common source",
    )

    groups = (
        ("selected_service_opening", [opening]),
        ("delegation", source["role_delegations"]),
        ("hr_role", source["hr_role_events"]),
        ("grant_authorization", source["grant_authorizations"]),
        ("iam_realization", source["iam_realization_events"]),
        ("review_population", [population]),
        ("review_decision", source["review_decisions"]),
        ("independent_verification", source["independent_verifications"]),
        ("subsequent_missing_response", [missing]),
    )
    event_index = [
        {
            "event_id": row["event_id"],
            "kind": kind,
            "person_id": row.get("person_id"),
            "service_account_id": row.get("service_account_id"),
            "event_at": row.get("effective_at")
            or row.get("as_of_exclusive")
            or row.get("approved_at")
            or row.get("extracted_at")
            or row.get("decided_at")
            or row.get("verified_at")
            or row.get("detected_at"),
            "case_available_at": row["case_available_at"],
            "source_object_sha256": canonical_hash(row),
        }
        for kind, rows in groups
        for row in rows
    ]
    index(event_index, "event_id")
    traces = [
        {
            "person_id": iam[account_id]["person_id"],
            "service_account_id": account_id,
            "opening_source_id": opening["event_id"],
            "hr_event_id": hr[iam[account_id]["person_id"]]["event_id"],
            "authorization_id": authorizations[account_id]["event_id"],
            "iam_realization_id": iam[account_id]["event_id"],
            "review_population_id": population["event_id"],
            "review_decision_id": decisions[account_id]["event_id"]
            if account_id in decisions
            else None,
            "independent_verification_id": verifications[account_id]["event_id"]
            if account_id in verifications
            else None,
            "missing_response_id": missing["event_id"] if account_id in missing_ids else None,
            "q1_review_source_state": "DECIDED_AND_INDEPENDENTLY_VERIFIED"
            if account_id in decisions
            else "MISSING_OWNER_DECISION",
        }
        for account_id in sorted(account_ids)
    ]
    return {
        "record_id": "SH-PORTAL-IAM007-PAYROLL-RELEASE-Q1-2027-LEDGER-v0.2",
        "source_record_id": source["record_id"],
        "state": source["state"],
        "scenario": source["scenario"],
        "fact_status": source["fact_status"],
        "authored_at": source["authored_at"],
        "repository_available_at": None,
        "repository_acceptance_at": None,
        "known_on_state": "PENDING_ACCEPTANCE; CASE_EVENT_AVAILABILITY_FILTERS_APPLY_AFTER_PUBLISH",
        "accepted_predecessor": accepted,
        "scope": scope,
        "service_population": {
            "unit": "human_service_role_account",
            "opening_before_2027_grants": len(opening["service_account_ids"]),
            "opening_source_id": opening["event_id"],
            "q1_grants": len(iam),
            "q1_other_jml_events": 0,
            "closing_at_2027_04_01": len(iam),
            "complete_within_declared_function": True,
            "company_wide_account_denominator": None,
        },
        "review_population": {
            "unit": "scoped_role_account_decision",
            "due": len(account_ids),
            "owner_decision_sources": len(decisions),
            "independently_verified": len(verifications),
            "missing_owner_decision": len(missing_ids),
            "missing_account_ids": sorted(missing_ids),
            "due_at": due["due_at"],
            "status": "PARTIAL_ONE_MISSING_NOT_CONTROL_PASS",
        },
        "portal_intake_contract": {
            "source_path": str(SOURCE),
            "source_hash_state": "PIN_IN_POST_ACCEPTANCE_MANIFEST",
            "source_object_key": "event_id",
            "source_object_hash_field": "source_object_sha256",
            "scenario": source["scenario"],
            "period_start": scope["period_start"],
            "period_end_exclusive": scope["period_end_exclusive"],
            "population_unit": "one scoped human service-role account",
            "due_count_path": "review_population.due",
            "observed_decision_count_path": "review_population.owner_decision_sources",
            "independently_verified_count_path": "review_population.independently_verified",
            "missing_count_path": "review_population.missing_owner_decision",
            "as_of_field": "event_index.event_at",
            "case_known_on_field": "event_index.case_available_at",
            "repository_known_on_gate": (
                "accepted merge commit/time required; null denies all intake"
            ),
            "branch_scope": "A/B common company source; branch-specific deltas not authored",
            "full_company_denominator": None,
            "performance_claim": (
                "ONE_MODELED_IN_UNIVERSE_DECISION_AND_ONE_MISSING; NOT_REAL_DEPLOYMENT"
            ),
        },
        "event_index": event_index,
        "forward_traces": traces,
        "reverse_trace_index": {
            event["event_id"]: [
                t["service_account_id"]
                for t in traces
                if event["event_id"]
                in {v for k, v in t.items() if k.endswith("_id") and v is not None}
            ]
            for event in event_index
        },
        "case_branches": source["case_branches"],
        "limits": source["limits"],
    }


def visible_events(
    ledger: dict, *, as_of: str, known_on: str, repository_available_at: str | None
) -> list[dict]:
    """Return only already-effective, case-available events after accepted publication."""
    as_of_time, known_time = when(as_of), when(known_on)
    if repository_available_at is None:
        return []
    publication = when(repository_available_at)
    require(
        publication >= when(ledger["authored_at"]),
        "Repository availability precedes authoring",
    )
    if known_time < publication:
        return []
    return [
        row
        for row in ledger["event_index"]
        if when(row["event_at"]) < as_of_time and when(row["case_available_at"]) <= known_time
    ]


def load(records_path: Path, receipt_path: Path, root: Path) -> dict:
    source = json.loads((root / SOURCE).read_text())
    prior = source["accepted_predecessor"]
    for path_key, hash_key in (
        ("source_path", "source_sha256"),
        ("derived_path", "derived_sha256"),
    ):
        require(
            sha256(root / prior[path_key]) == prior[hash_key],
            "Accepted predecessor bytes changed",
        )
    release = source["accepted_august_release"]
    require(
        sha256(records_path) == release["records_sha256"]
        and sha256(receipt_path) == release["receipt_sha256"],
        "Accepted August release byte pin mismatch",
    )
    receipt = json.loads(receipt_path.read_text())
    require(
        receipt["source_commit"] == release["source_commit"]
        and receipt["status"] == "ACCEPTED_SCOPED_EDITION",
        "Accepted August release state differs",
    )
    records = json.loads(records_path.read_text())
    predecessor = json.loads((root / prior["source_path"]).read_text())
    return derive(records, predecessor, source)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = (
        json.dumps(load(args.records, args.receipt, args.source_root), indent=2, sort_keys=True)
        + "\n"
    ).encode()
    if args.check:
        require(args.output.read_bytes() == payload, "Stale Q1 IAM successor ledger")
    else:
        require(not args.output.exists(), "Output exists; use --check or new version")
        args.output.write_bytes(payload)
    print("PASS scoped Q1 2027 HR-IAM-review successor source")


if __name__ == "__main__":
    main()
