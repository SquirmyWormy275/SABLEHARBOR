"""Bounded performed debt/host chains; source amounts, authored internal timing."""

import argparse
import calendar
import copy
import hashlib
import json
from decimal import Decimal as D
from pathlib import Path

from .availability import apply
from .completed_period import ROOT, read

SOURCE = "enterprise/operations/source/debt_host_2026_08.json"


def build(anchor_rows=None):
    if anchor_rows is None:
        from industrial.planning.enterprise import load_anchor

        anchor_rows = load_anchor()
    result = copy.deepcopy(read(SOURCE))
    selected = [
        r
        for r in anchor_rows
        if r["entity"] == "ARU_GROUP"
        and int(r["year"]) == 2026
        and 1 <= int(r["month"]) <= 8
        and r["source_id"] in {"DEBT26", "LEASE26"}
        and r["account"] == "1000"
    ]
    events = []
    for row in selected:
        month = int(row["month"])
        principal = row["cash_flow"] == "FINANCING" and row["source_id"] == "DEBT26"
        day = 7 if principal else calendar.monthrange(2026, month)[1]
        events.append(
            dict(
                event_id="SH-DEBT-CLEAR-" + row["journal_id"],
                source_journal_id=row["journal_id"],
                source_id=row["source_id"],
                legal_entity="ARU",
                accounting_period=f"2026-{month:02}",
                source_posting_on=f"2026-{month:02}-{calendar.monthrange(2026, month)[1]}",
                settled_on=f"2026-{month:02}-{day:02}",
                amount_usd=str(-D(row["signed_usd"])),
                classification="TERM_PRINCIPAL"
                if principal
                else "LEASE_PRINCIPAL"
                if row["cash_flow"] == "FINANCING"
                else "INTEREST_AND_UNDRAWN_FEE",
                settlement_state="MODELED_INTERNAL_CLEARING_NOT_BANK_CONFIRMED",
                payment_batch_ref="SH-SYN-ARU-" + row["journal_id"],
                preparer_role="ARU_CONTROLLER_TESSA_ROURKE",
                reviewer_role="SHIH_TREASURY",
                available_at=result["available_at"],
            )
        )
    for event in result["host_events"]:
        event["available_at"] = result["available_at"]
    result["debt_settlements"] = events
    term = sum(D(r["amount_usd"]) for r in events if r["classification"] == "TERM_PRINCIPAL")
    leases = sum(D(r["amount_usd"]) for r in events if r["classification"] == "LEASE_PRINCIPAL")
    result["principal_bridge"] = dict(
        term_opening_usd="22500000",
        term_paid_usd=str(term),
        term_closing_usd=str(D("22500000") - term),
        lease_opening_usd="2500000",
        lease_paid_usd=str(leases),
        lease_closing_usd=str(D("2500000") - leases),
        additional_cash_or_expense_posting_usd="0",
    )
    result["source_hashes"] = {
        p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
        for p in [
            SOURCE,
            "industrial/source/finance.json",
            "industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md",
            "docs/canon/CRADLE_CLOSEOUT_2026-09-06.md",
            "enterprise/operations/source/current_company_2026_08.json",
        ]
    }
    validate(result, anchor_rows)
    return apply(result)


def validate(result, anchor_rows):
    expected = {
        r["journal_id"]: -D(r["signed_usd"])
        for r in anchor_rows
        if r["entity"] == "ARU_GROUP"
        and int(r["year"]) == 2026
        and 1 <= int(r["month"]) <= 8
        and r["source_id"] in {"DEBT26", "LEASE26"}
        and r["account"] == "1000"
    }
    rows = result["debt_settlements"]
    if (
        len(rows) != len(expected)
        or {r["source_journal_id"]: D(r["amount_usd"]) for r in rows} != expected
    ):
        raise ValueError("Debt clearing population differs from source cash legs")
    for row in rows:
        if (
            row["legal_entity"] != "ARU"
            or row["settled_on"][:7] != row["accounting_period"]
            or row["preparer_role"] == row["reviewer_role"]
        ):
            raise ValueError("Wrong debt entity, period or independent release")
        if row["classification"] == "TERM_PRINCIPAL" and row["settled_on"] not in {
            "2026-04-07",
            "2026-07-07",
        }:
            raise ValueError("Term principal timing changed")
    source_rows = {r["journal_id"]: r for r in anchor_rows if r["account"] == "1000"}
    for row in rows:
        original = source_rows[row["source_journal_id"]]
        kind = (
            "TERM_PRINCIPAL"
            if original["cash_flow"] == "FINANCING" and original["source_id"] == "DEBT26"
            else "LEASE_PRINCIPAL"
            if original["cash_flow"] == "FINANCING"
            else "INTEREST_AND_UNDRAWN_FEE"
        )
        if row["classification"] != kind or row["source_id"] != original["source_id"]:
            raise ValueError("Debt source classification changed")
    bridge = result["principal_bridge"]
    for category, opening in [("term", D("22500000")), ("lease", D("2500000"))]:
        paid = sum(
            D(r["amount_usd"])
            for r in rows
            if r["classification"] == category.upper() + "_PRINCIPAL"
        )
        if (
            D(bridge[category + "_opening_usd"]) != opening
            or D(bridge[category + "_paid_usd"]) != paid
            or D(bridge[category + "_closing_usd"]) != opening - paid
        ):
            raise ValueError("Debt principal rollforward does not reconcile")
    if result["debt"]["lien_release_status"] != "NOT_ESTABLISHED_INSTRUMENT_POPULATION_MISSING":
        raise ValueError("Paid debt does not establish lien release")
    cradle = read("enterprise/operations/source/current_company_2026_08.json")["cradle"]
    hosts = result["host_events"]
    if len(hosts) != 4 or len({r["event_id"] for r in hosts}) != 4:
        raise ValueError("Selected host event population omitted or duplicated")
    share = next(r for r in hosts if r["event"] == "REFINER_ACCEPTANCE_HOST_SHARE_RECONCILED")
    payment = next(r for r in hosts if r["event"] == "HOST_PARTICIPATION_PAID")
    if (
        D(share["host_participation_usd"]) != D(cradle["host_share_usd"])
        or D(payment["amount_usd"]) != D(cradle["host_share_usd"])
        or D(share["accepted_kg"]) != D(cradle["accepted_product_kg"])
        or D(share["realized_product_value_usd"]) != D(cradle["revenue_usd"])
    ):
        raise ValueError("Host settlement does not match current operating economics")
    if share["effective_on"] >= payment["effective_on"] or payment["effective_on"] != "2026-08-31":
        raise ValueError("Host participation paid before acceptance/receipt")
    return {
        "debt_settlements": len(rows),
        "selected_host_events": len(hosts),
        "status": "RECONCILED_SOURCE_AMOUNTS_AUTHORED_INTERNAL_EVIDENCE",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=ROOT / "enterprise/generated/debt-host-2026-08/records.json"
    )
    args = parser.parse_args()
    result = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["principal_bridge"]))


if __name__ == "__main__":
    main()
