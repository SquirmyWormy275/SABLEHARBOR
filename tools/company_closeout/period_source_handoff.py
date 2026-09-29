"""Reconcile selected August 2026 company source populations for portal intake.

This is a read-only source contract. It creates no company event, audit command,
grant, occurrence ledger, or conclusion about professional sufficiency.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

SOURCE_COMMIT = "ddca0d93b16c743e90ce5ac3f9cc74fb74ec6d1f"
RECEIPT_SHA256 = "bc0b66500d682c1ea1705601bc1fc1b45e1c6e166d3d28b308df9c729c53767e"
RECORDS_SHA256 = "5dd78a2bc6c6a08f333a7a6a0d09f7a310e3f2bd0fe027926c6b120a7b4a795e"
PACKAGE_SHA256 = "8136d8cae07dd4f9fc1f488a7d1034275f5c4149f8606774c6370bbaff7c597c"
SOURCE_PATHS = (
    "enterprise/operations/source/completed_period_2026_08.json",
    "enterprise/operations/source/current_company_2026_08.json",
    "enterprise/ccf/company_closeout/obligation_census.json",
    "enterprise/ccf/company_closeout/current_activity_successor.json",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity_digest(values) -> str:
    raw = json.dumps(sorted(values), separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def unique(rows, field):
    values = [row[field] for row in rows]
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {field}")
    return set(values)


def derive(records: dict, completed: dict, obligations: dict) -> dict:
    tables = records["tables"]
    people = unique(tables["people"], "person_id")
    pay_dates = completed["payroll"]["pay_dates"]
    if len(pay_dates) != len(set(pay_dates)) or any(
        not date.startswith("2026-08-") for date in pay_dates
    ):
        raise ValueError("Invalid August pay-date schedule")
    due_pay = {(person, day) for person in people for day in pay_dates}
    payroll = tables["payroll"]
    observed_pay = {(row["person_id"], row["pay_date"]) for row in payroll}
    if len(observed_pay) != len(payroll) or observed_pay != due_pay:
        raise ValueError("Missing, duplicated or extra payroll occurrence")
    pay_ids = unique(payroll, "pay_id")
    if unique(tables["settlements"], "pay_id") != pay_ids:
        raise ValueError("Payroll settlement population differs")
    if any(row["settlement_state"] != "MODELED_PAID" for row in payroll):
        raise ValueError("Payroll settlement state differs")
    batches = {row["batch_id"] for row in payroll}
    if unique(tables["approvals"], "batch_id") != batches:
        raise ValueError("Payroll approval batch population differs")
    directors = unique(tables["nonemployees"], "person_id")
    if directors & people:
        raise ValueError("Nonemployee directors overlap employee payroll")

    contracts = unique(tables["current_contracts"], "contract_id")
    for table in (
        "current_authorities",
        "current_deliveries",
        "current_delivery_evidence",
        "current_invoices",
    ):
        if unique(tables[table], "contract_id") != contracts:
            raise ValueError(f"{table} contract population differs")
    invoices = unique(tables["current_invoices"], "invoice_id")
    if unique(tables["current_receipts"], "invoice_id") != invoices:
        raise ValueError("Invoice disposition population differs")
    receipt_states = Counter(row["state"] for row in tables["current_receipts"])
    if set(receipt_states) != {"NEWLY_AUTHORED_SYNTHETIC_CLEARING", "MODELED_UNPAID"}:
        raise ValueError("Unexpected receipt disposition")
    for row in tables["current_receipts"]:
        if row["state"] == "MODELED_UNPAID" and (
            row["paid_on"] is not None or row["cash_usd"] != "0.00"
        ):
            raise ValueError("Unpaid invoice presented as cash")
        if row["state"] == "NEWLY_AUTHORED_SYNTHETIC_CLEARING" and not row["paid_on"]:
            raise ValueError("Paid invoice lacks modeled payment date")

    declared_chains = {row["chain_id"]: row for row in completed["operating_chains"]}
    observed_chains = unique(tables["operating_quantities"], "chain_id")
    if observed_chains != set(declared_chains):
        raise ValueError("Selected chain population differs")
    events = tables["operating_events"]
    if len(events) != sum(len(row["stages"]) for row in declared_chains.values()):
        raise ValueError("Selected stage count differs")
    if unique(events, "event_id") != {
        f"{row['chain_id']}-{number:02d}"
        for row in declared_chains.values()
        for number, _ in enumerate(row["stages"], 1)
    }:
        raise ValueError("Selected stage identity differs")
    chain_cases = Counter(row["case"] for row in tables["operating_quantities"])

    projects = unique(tables["current_projects"], "project_id")
    rail = [r for r in obligations["records"] if r["population"] == "rail_safety_events"]
    rail_august = [r for r in rail if r["effective_period"].startswith("2026-08-")]
    if len(rail_august) != 1 or rail_august[0]["expected_occurrences"] != 1:
        raise ValueError("August rail-event review population differs")
    if rail_august[0]["performance"] != "MISSING_EVIDENCE":
        raise ValueError("August rail-event review disposition differs")
    permits = [r for r in obligations["records"] if r["population"] == "red_wash_permit_register"]
    if any(r["expected_occurrences"] is not None or r["due_date"] is not None for r in permits):
        raise ValueError("Permit cadence invented or changed")
    if any(r["performance"] != "MISSING_EVIDENCE" for r in permits):
        raise ValueError("Permit performance disposition differs")

    return {
        "payroll": {
            "unit": "person_pay_date",
            "due": len(due_pay),
            "observed": len(payroll),
            "missing": 0,
            "modeled_paid": len(tables["settlements"]),
            "approval_batches": len(batches),
            "excluded_nonemployee_people": len(directors),
            "id_set_sha256": identity_digest(pay_ids),
        },
        "contract_delivery_invoice": {
            "unit": "august_contract",
            "due": len(contracts),
            "observed_delivery": len(tables["current_deliveries"]),
            "observed_evidence": len(tables["current_delivery_evidence"]),
            "observed_invoice": len(tables["current_invoices"]),
            "missing": 0,
            "modeled_paid_invoices": receipt_states["NEWLY_AUTHORED_SYNTHETIC_CLEARING"],
            "modeled_unpaid_invoices": receipt_states["MODELED_UNPAID"],
            "id_set_sha256": identity_digest(contracts),
        },
        "selected_operating_chains": {
            "unit": "selected_case",
            "declared": len(declared_chains),
            "observed": len(observed_chains),
            "missing_within_selection": 0,
            "stage_records": len(events),
            "cases": dict(sorted(chain_cases.items())),
            "full_month_transaction_denominator": None,
            "id_set_sha256": identity_digest(observed_chains),
        },
        "current_projects": {
            "unit": "project",
            "represented": len(projects),
            "willow": sum(r["unit"] == "willow" for r in tables["current_projects"]),
            "cradle": sum(r["unit"] == "project-cradle" for r in tables["current_projects"]),
            "statutory_due_occurrences": None,
            "id_set_sha256": identity_digest(projects),
        },
        "august_rail_event_review": {
            "unit": "event_review",
            "expected": 1,
            "represented_event": 1,
            "performance_evidence": 0,
            "missing_evidence": 1,
            "other_historical_events_excluded": len(rail) - 1,
            "reporting_determination": "OPEN_2026_EVENT_DATE_AUTHORITY",
            "source_event_id": rail_august[0]["id"],
        },
        "red_wash_permit_conditions": {
            "unit": "permit_condition_set",
            "represented": len(permits),
            "due_occurrences": None,
            "performance_evidence_missing_sets": len(permits),
            "missing_occurrence_count": None,
            "id_set_sha256": identity_digest(r["id"] for r in permits),
        },
        "september_hr_change_excluded_from_august": {
            "unit": "change_event",
            "count": len(tables["change_events"]),
            "id_set_sha256": identity_digest(r["event_id"] for r in tables["change_events"]),
        },
    }


def contract(records_path: Path, receipt_path: Path, source_root: Path) -> dict:
    if digest(records_path) != RECORDS_SHA256 or digest(receipt_path) != RECEIPT_SHA256:
        raise ValueError("Accepted release/input byte pin mismatch")
    records = json.loads(records_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    if (
        records["repository_source_commit"] != SOURCE_COMMIT
        or receipt["source_commit"] != SOURCE_COMMIT
        or receipt["status"] != "ACCEPTED_SCOPED_EDITION"
    ):
        raise ValueError("Accepted source/receipt scope mismatch")
    if receipt["cutoff"]["completed_period"] != "2026-08-31":
        raise ValueError("Accepted completed-period cutoff changed")
    sources = {path: digest(source_root / path) for path in SOURCE_PATHS}
    for path, sha in sources.items():
        if path in records["source_hashes"] and records["source_hashes"][path] != sha:
            raise ValueError("Accepted generator source changed")
    completed = json.loads((source_root / SOURCE_PATHS[0]).read_text())
    obligations = json.loads((source_root / SOURCE_PATHS[2]).read_text())
    activity = json.loads((source_root / SOURCE_PATHS[3]).read_text())
    for table, declaration in activity["populations"].items():
        ids = unique(records["tables"][table], declaration["primary_key"])
        if declaration["count"] != len(ids) or set(declaration["ids"]) != ids:
            raise ValueError(f"Current activity population differs: {table}")
    populations = derive(records, completed, obligations)
    return {
        "record_id": "SH-PORTAL-PERIOD-SOURCE-HANDOFF-2026-08-v1",
        "version": "1.0.0",
        "state": "REVIEWABLE_SOURCE_INPUT_NOT_AUDIT_ACCEPTANCE",
        "edition": "sable-harbor-company-edition-v1.2.0",
        "accepted_source_commit": SOURCE_COMMIT,
        "release_receipt_sha256": RECEIPT_SHA256,
        "release_package_sha256": PACKAGE_SHA256,
        "records_json_sha256": RECORDS_SHA256,
        "completed_period": {
            "start": "2026-08-01",
            "end_exclusive": "2026-09-01",
            "timezone": "America/Los_Angeles",
        },
        "repository_source_available_at": records["repository_source_available_at"],
        "release_published_at": "2026-09-22T23:50:07Z",
        "source_sha256": sources,
        "populations": populations,
        "limits": [
            "Due counts are source-declared schedules, not independently validated "
            "statutory duties.",
            "Modeled payment and clearing records are not independent bank or "
            "counterparty confirmation.",
            "Selected operating chains do not establish the full physical month denominator.",
            "Null permit due counts and cash-payment due dates are unknown, not zero.",
            "No August effective record was available in an August known-on view; "
            "source and release availability govern.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = (
        json.dumps(contract(args.records, args.receipt, args.source_root), indent=2, sort_keys=True)
        + "\n"
    ).encode()
    if args.check:
        if args.output.read_bytes() != data:
            raise ValueError("Stale period handoff")
    else:
        if args.output.exists():
            raise ValueError("Output already exists; use --check or a new version")
        args.output.write_bytes(data)
    print("PASS exact accepted-source period population handoff")


if __name__ == "__main__":
    main()
