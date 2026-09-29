"""Generate one complete, bounded fictional Q1 2027 local control exercise.

Future company event assertions are modeled source facts, not real deployment or
an enterprise control conclusion. Local A/B audit exercises are not consumed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

SOURCE = Path("enterprise/operations/source/portal_2027_reference_controls_case_2026_09_29.json")
EXPECTED_DUE_BY_CONTROL = {
    "SH-IAM-006": 2,
    "SH-BCM-002": 3,
    "SH-BCM-003": 1,
    "SH-IAM-005": 1,
    "SH-REC-004": 2,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def object_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def indexed(rows: list[dict], key: str) -> dict[str, dict]:
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate {key}")
    return result


def instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def derive(records: dict, receipt: dict, case: dict, common: dict, procedures: list[dict]) -> dict:
    if (
        case["state"] != "PROVISIONAL_NEWLY_AUTHORED_FICTIONAL_COMPANY_EXERCISE"
        or case["fact_status"] != "MODELED_FUTURE_EVENTS_NOT_2026_ACTUAL_OR_REAL_DEPLOYMENT"
        or case["repository_available_at"] is not None
        or case["repository_acceptance_at"] is not None
        or receipt["status"] != "ACCEPTED_SCOPED_EDITION"
        or receipt["source_commit"] != case["accepted_august_release"]["source_commit"]
        or records["repository_source_commit"] != receipt["source_commit"]
    ):
        raise ValueError("Source edition, fictional authority or availability differs")
    period = case["period"]
    if (
        period["start"] != "2027-01-01T00:00:00Z"
        or period["end_exclusive"] != "2027-04-01T00:00:00Z"
        or period["case_cutoff"] != period["end_exclusive"]
        or not instant(case["authored_at"]) < instant(period["start"])
    ):
        raise ValueError("Wrong case period or future authoring")
    scope = case["scope"]
    if (
        scope["legal_entity_id"] != "SHI"
        or scope["physical_site_id"] is not None
        or scope["hosted_production"] is not False
        or scope["real_deployment"] is not False
        or scope["customer_data"] is not False
        or scope["personal_data"] is not False
        or scope["complete_selected_population"] is not True
        or scope["company_wide_population_complete"] is not False
        or scope["company_2027_annual_control_effectiveness"] is not None
        or scope["scope_id"] != "SH-REFCTRL-2027-Q1"
        or common["boundary"]["legal_entity_id"] != "SHI"
        or common["boundary"]["company_2027_opening_complete"] is not False
    ):
        raise ValueError("Local case promoted to deployed or company-wide scope")
    if not set(scope["service_reference_ids"]) <= set(common["boundary"]["service_ids"]):
        raise ValueError("Wrong parent service reference")
    if set(case["branch_inputs"]) != {"A", "B"} or any(
        value != {"common_source": True, "company_delta_state": "NOT_AUTHORED"}
        for value in case["branch_inputs"].values()
    ):
        raise ValueError("A/B private or unsupported company delta")
    people = indexed(records["tables"]["people"], "person_id")
    access = indexed(records["tables"]["access"], "person_id")
    selected = indexed(case["selected_personnel"], "person_id")
    if set(selected) != {"SH-EMP-ESS-0003", "SH-EMP-ESS-0004"}:
        raise ValueError("Wrong selected case persons")
    for person_id, person in selected.items():
        if (
            person_id not in people
            or person_id not in access
            or people[person_id]["legal_employer"] != "SHI"
            or people[person_id]["unit"] != "ess"
            or person["legal_employer"] != "SHI"
            or person["unit_at_august"] != "ess"
            or person["modeled_2027_assignment"]
            != "PROSPECTIVE_CASE_ONLY_NOT_EMPLOYMENT_CONTINUITY_PROOF"
        ):
            raise ValueError("Selected person does not join accepted SHI roster")
    if {p["case_role"] for p in selected.values()} != {
        "LOCAL_EXERCISE_OPERATOR",
        "LOCAL_EXERCISE_REVIEWER",
    }:
        raise ValueError("Case role separation differs")
    authority = case["local_authorization"]
    operator = authority["prepared_by"]
    reviewer = authority["approved_by"]
    approved_at = authority.get("approved_at")
    if (
        not isinstance(approved_at, str)
        or not instant(case["authored_at"])
        <= instant(approved_at)
        <= instant(authority["modeled_effective_at"])
        <= instant(authority["fictional_available_at"])
        or operator == reviewer
        or selected[operator]["case_role"] != "LOCAL_EXERCISE_OPERATOR"
        or selected[reviewer]["case_role"] != "LOCAL_EXERCISE_REVIEWER"
        or authority["corporate_policy_status"] != "LOCAL_CASE_RULE_NOT_ENTERPRISE_POLICY"
        or authority["modeled_effective_at"] != period["start"]
        or instant(authority["fictional_available_at"]) < instant(authority["modeled_effective_at"])
        or instant(authority["fictional_available_at"]) >= instant(period["end_exclusive"])
    ):
        raise ValueError("Local authorization or reviewer separation differs")
    briefings = indexed(case["exercise_briefings"], "briefing_id")
    if len(briefings) != 2 or {b["person_id"] for b in briefings.values()} != set(selected):
        raise ValueError("Local case briefing population incomplete")
    for briefing in briefings.values():
        if (
            briefing["reviewed_by"] == briefing["person_id"]
            or briefing["reviewed_by"] not in selected
            or not instant(authority["fictional_available_at"])
            <= instant(briefing["modeled_completed_at"])
            <= instant(briefing["fictional_available_at"])
            < instant(period["end_exclusive"])
            or "no enterprise qualification claim" not in briefing["case_scope"]
        ):
            raise ValueError("Local case briefing chronology or scope differs")
    expected_procedures = indexed(procedures, "control_id")
    if not set(EXPECTED_DUE_BY_CONTROL) <= set(expected_procedures):
        raise ValueError("Missing CCF control procedure")
    inv = case["inventory"]
    datasets = indexed(inv["datasets"], "dataset_id")
    accounts = indexed(inv["nonhuman_accounts"], "account_id")
    grants = indexed(inv["privileged_grants"], "grant_id")
    copies = indexed(inv["copies"], "copy_id")
    if (len(datasets), len(accounts), len(grants), len(copies)) != (1, 1, 1, 2):
        raise ValueError("Declared selected inventory incomplete")
    dataset = next(iter(datasets.values()))
    account = next(iter(accounts.values()))
    grant = next(iter(grants.values()))
    if (
        not instant(authority["fictional_available_at"])
        <= instant(inv["modeled_opened_at"])
        <= instant(inv["fictional_available_at"])
        < instant(period["end_exclusive"])
        or object_sha256(dataset["fixture_payload"]) != dataset["fixture_sha256"]
        or dataset["classification"] != "NONPERSONAL_LOCAL_FIXTURE"
        or dataset["owner_person_id"] != operator
        or account["owner_person_id"] != operator
        or grant["account_id"] != account["account_id"]
        or grant["owner_person_id"] != operator
        or grant["reviewer_person_id"] != reviewer
        or grant["state"] != "MODELED_CASE_GRANT_NOT_LIVE"
        or instant(grant["effective_at"]) < instant(approved_at)
        or grant["expires_at"] != period["end_exclusive"]
        or any(copy["dataset_id"] != dataset["dataset_id"] for copy in copies.values())
    ):
        raise ValueError("Fixture, account, privilege or copy join differs")
    schedule = indexed(case["schedule"], "due_id")
    if (
        len(schedule) != 9
        or Counter(row["control_id"] for row in schedule.values()) != EXPECTED_DUE_BY_CONTROL
    ):
        raise ValueError("Nine selected due occurrences not complete")
    valid_objects = set(datasets) | set(accounts) | set(grants) | set(copies)
    for due in schedule.values():
        if (
            due["object_id"] not in valid_objects
            or due["authority_id"] != authority["authorization_id"]
            or not instant(period["start"])
            <= instant(due["window_start"])
            < instant(due["due_at"])
            < instant(due["window_end_exclusive"])
            <= instant(period["end_exclusive"])
        ):
            raise ValueError("Due object, authority or time boundary differs")
    performed = indexed(case["performed_events"], "event_id")
    if len(performed) != 7:
        raise ValueError("Selected timely event count differs")
    performed_by_due = {}
    for event in performed.values():
        due_id = event["due_id"]
        if due_id not in schedule or due_id in performed_by_due:
            raise ValueError("Wrong or duplicate performed due event")
        due = schedule[due_id]
        if (
            event["actor_person_id"] != operator
            or event["reviewer_person_id"] != reviewer
            or event["result"] not in {"SUCCESS", "FAIL"}
            or not instant(due["window_start"])
            <= instant(event["event_at"])
            < instant(due["window_end_exclusive"])
            or not instant(event["event_at"]) <= instant(event["fictional_available_at"])
            or instant(event["event_at"]) <= instant(inv["fictional_available_at"])
            or any(
                instant(event["event_at"]) <= instant(b["fictional_available_at"])
                for b in briefings.values()
            )
            or instant(event["fictional_available_at"]) > instant(period["end_exclusive"])
            or event["source_kind"]
            != "NEWLY_AUTHORED_SYNTHETIC_COMPANY_EXERCISE_EVENT_NOT_REAL_DEPLOYMENT"
        ):
            raise ValueError("On-time event chronology, actor or status differs")
        if (
            "expected_sha256" in event["detail"]
            and event["detail"]["expected_sha256"] != dataset["fixture_sha256"]
        ):
            raise ValueError("Restore fixture source hash differs")
        if event["result"] == "FAIL" and due["control_id"] not in {"SH-BCM-003", "SH-REC-004"}:
            raise ValueError("Unexpected failed case event")
        if due["control_id"] == "SH-BCM-003" and (
            event["result"] != "FAIL"
            or event["detail"]["recovered_sha256"] == dataset["fixture_sha256"]
        ):
            raise ValueError("Original restore failure overwritten")
        if (
            due["control_id"] == "SH-REC-004"
            and due["object_id"] == "SH-REFCTRL-COPY-BACKUP"
            and event["result"] != "FAIL"
        ):
            raise ValueError("Original backup disposal failure overwritten")
        performed_by_due[due_id] = event
    remediation = indexed(case["remediation_events"], "event_id")
    if len(remediation) != 5:
        raise ValueError("Selected follow-up event count differs")
    for event in remediation.values():
        due_id = event["due_id"]
        if due_id is not None and due_id not in schedule:
            raise ValueError("Follow-up references wrong due occurrence")
        if (
            event["actor_person_id"] != operator
            or event["reviewer_person_id"] != reviewer
            or not instant(event["event_at"]) <= instant(event["fictional_available_at"])
            or (
                due_id is not None
                and not instant(event["event_at"])
                >= instant(schedule[due_id]["window_end_exclusive"])
            )
            or (
                due_id is not None
                and due_id in performed_by_due
                and performed_by_due[due_id]["result"] != "FAIL"
            )
        ):
            raise ValueError("Follow-up time or actor differs")
        if due_id is None and (
            event["result"] != "COMPENSATING_RESPONSE"
            or event["detail"].get("grant_id") != grant["grant_id"]
        ):
            raise ValueError("Unscoped follow-up differs")
    tickets = indexed(case["exception_tickets"], "ticket_id")
    if len(tickets) != 4:
        raise ValueError("Selected exception population differs")
    for ticket in tickets.values():
        due_id = ticket["trigger_due_id"]
        if due_id not in schedule:
            raise ValueError("Exception references wrong due occurrence")
        failed_event = performed_by_due.get(due_id)
        trigger_at = (
            failed_event["event_at"]
            if failed_event is not None and failed_event["result"] == "FAIL"
            else schedule[due_id]["window_end_exclusive"]
        )
        disposition = remediation.get(ticket["disposition_event_id"])
        if (
            disposition is None
            or disposition["due_id"] != due_id
            or disposition["detail"].get("ticket_id") != ticket["ticket_id"]
            or instant(ticket["opened_at"]) < instant(trigger_at)
            or instant(ticket["opened_at"]) > instant(disposition["event_at"])
            or not instant(ticket["opened_at"])
            <= instant(ticket["fictional_available_at"])
            <= instant(disposition["event_at"])
            or (
                failed_event is not None
                and instant(ticket["fictional_available_at"])
                < instant(failed_event["fictional_available_at"])
            )
        ):
            raise ValueError("Exception/disposition join or chronology differs")
    if {ticket["trigger_due_id"] for ticket in tickets.values()} != {
        due_id
        for due_id, due in schedule.items()
        if due_id not in performed_by_due or performed_by_due[due_id]["result"] == "FAIL"
    }:
        raise ValueError("Failed or missing due occurrence lacks ticket")
    due_rows = []
    for due_id, due in sorted(schedule.items(), key=lambda item: (item[1]["due_at"], item[0])):
        event = performed_by_due.get(due_id)
        due_rows.append(
            {
                **due,
                "status_at_case_cutoff": "MISSING" if event is None else event["result"],
                "timely_event_id": event["event_id"] if event else None,
                "timely_event_sha256": object_sha256(event) if event else None,
                "follow_up_event_ids": sorted(
                    e["event_id"] for e in remediation.values() if e["due_id"] == due_id
                ),
                "exception_ticket_ids": sorted(
                    t["ticket_id"] for t in tickets.values() if t["trigger_due_id"] == due_id
                ),
                "exception_ticket_ids_at_case_cutoff": sorted(
                    t["ticket_id"]
                    for t in tickets.values()
                    if t["trigger_due_id"] == due_id
                    and instant(t["fictional_available_at"]) <= instant(period["case_cutoff"])
                ),
            }
        )
    per_control = []
    for control in EXPECTED_DUE_BY_CONTROL:
        rows = [row for row in due_rows if row["control_id"] == control]
        counts = Counter(row["status_at_case_cutoff"] for row in rows)
        per_control.append(
            {
                "control_id": control,
                "due": len(rows),
                "observed": counts["SUCCESS"] + counts["FAIL"],
                "success": counts["SUCCESS"],
                "failed": counts["FAIL"],
                "missing": counts["MISSING"],
                "corporate_control_effectiveness": None,
            }
        )
    total = {
        key: sum(row[key] for row in per_control)
        for key in ("due", "observed", "success", "failed", "missing")
    }
    if total != {"due": 9, "observed": 7, "success": 5, "failed": 2, "missing": 2}:
        raise ValueError("Selected due/observation/failure reconciliation differs")
    if any(
        row["due"] != row["observed"] + row["missing"]
        or row["observed"] != row["success"] + row["failed"]
        for row in per_control
    ):
        raise ValueError("Control occurrence reconciliation unbalanced")
    return {
        "record_id": "SH-REFCTRL-2027-Q1-LEDGER-v0.1",
        "source_record_id": case["record_id"],
        "state": case["state"],
        "scenario": case["scenario"],
        "fact_status": case["fact_status"],
        "authored_at": case["authored_at"],
        "repository_available_at": None,
        "repository_acceptance_at": None,
        "known_on_state": "PENDING_REPOSITORY_ACCEPTANCE_FUTURE_SCENARIO_PREVIEW_ONLY",
        "source_pins": case["source_pins"],
        "accepted_august_release": case["accepted_august_release"],
        "period": period,
        "scope": scope,
        "authorization": authority,
        "exercise_briefings": case["exercise_briefings"],
        "selected_personnel": case["selected_personnel"],
        "inventory": inv,
        "due_rows": due_rows,
        "performed_events": [{**e, "event_sha256": object_sha256(e)} for e in performed.values()],
        "remediation_events": [
            {**e, "event_sha256": object_sha256(e)} for e in remediation.values()
        ],
        "exception_tickets": list(tickets.values()),
        "per_control": per_control,
        "totals": total,
        "company_wide_2027_due_count": None,
        "company_wide_2027_observed_count": None,
        "company_wide_2027_missing_count": None,
        "case_branches": case["branch_inputs"],
        "limits": case["limits"],
    }


def case_view(ledger: dict, *, as_of: str, known_on: str, allow_provisional: bool = False) -> dict:
    """Time-filter a scenario preview; never turn it into accepted company evidence."""
    if not allow_provisional:
        raise ValueError("Provisional future case is not accepted company evidence")
    if instant(known_on) < instant(ledger["authorization"]["fictional_available_at"]):
        return {"due_ids": [], "visible_event_ids": [], "preview_only": True}
    selected_due = [d for d in ledger["due_rows"] if instant(d["due_at"]) <= instant(as_of)]
    selected_events = [
        e
        for e in ledger["performed_events"] + ledger["remediation_events"]
        if instant(e["event_at"]) <= instant(as_of)
        and instant(e["fictional_available_at"]) <= instant(known_on)
    ]
    return {
        "due_ids": [d["due_id"] for d in selected_due],
        "visible_event_ids": [e["event_id"] for e in selected_events],
        "preview_only": True,
    }


def load(records_path: Path, receipt_path: Path, root: Path) -> dict:
    case_path = root / SOURCE
    case = json.loads(case_path.read_text())
    release = case["accepted_august_release"]
    if (
        sha256(records_path) != release["records_sha256"]
        or sha256(receipt_path) != release["receipt_sha256"]
    ):
        raise ValueError("Accepted August release byte pin mismatch")
    inputs = {}
    for key, pin in case["source_pins"].items():
        path = root / pin["path"]
        if sha256(path) != pin["sha256"]:
            raise ValueError(f"Changed source: {key}")
        inputs[key] = json.loads(path.read_text())
    return derive(
        json.loads(records_path.read_text()),
        json.loads(receipt_path.read_text()),
        case,
        inputs["common_boundary"],
        inputs["ccf_procedures"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = (
        json.dumps(load(args.records, args.receipt, args.source_root), sort_keys=True, indent=2)
        + "\n"
    ).encode()
    if args.check:
        if args.output.read_bytes() != payload:
            raise ValueError("Stale reference-controls case ledger")
    else:
        if args.output.exists():
            raise ValueError("Output exists; use --check or new version")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
    print("PASS bounded fictional Q1 reference-controls ledger")


if __name__ == "__main__":
    main()
