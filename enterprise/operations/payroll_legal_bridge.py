"""Independent legal-employer check for the August source-envelope allocation."""

from decimal import Decimal as D

SOURCE_IDS = {"CO-PAYROLL-PS-202608", "CO-PAYROLL-RWH-202608"}
CORRECTION = D("78125.00")


def verify(edition, journal_rows, trial_balance_rows):
    """Check source legs and legal monthly expense, never post a second payroll."""
    payroll = sum(
        D(row["gross_usd"]) + D(row["employer_burden_usd"])
        for row in edition["tables"]["payroll"]
        if row["legal_entity"] == "PS"
    )
    if payroll != D("203125.00"):
        raise ValueError("PS payroll changed: reperform the legal allocation source")
    rows = [r for r in journal_rows if r["source_id"] in SOURCE_IDS]
    if not rows or any(int(r["year"]) != 2026 or int(r["month"]) != 8 for r in rows):
        raise ValueError("PS legal correction missing or outside completed August period")
    byscenario = {}
    for row in rows:
        key = row.get("scenario", "base")
        byscenario.setdefault(key, []).append(row)
    for selected in byscenario.values():
        if len(selected) != 4:
            raise ValueError("PS legal correction duplicated or missing source legs")
        expenses = {r["entity"]: D(r["signed_usd"]) for r in selected if r["account"] == "5100"}
        if expenses != {"PS": CORRECTION, "RWH": -CORRECTION}:
            raise ValueError("PS/RWH expense allocation is reversed or wrong entity")
        clearing = [r for r in selected if r["account"] != "5100"]
        if len(clearing) != 2 or any(r["account"] not in {"1150", "2150"} for r in clearing):
            raise ValueError("Paid-on-behalf correction requires reciprocal intercompany legs")
        if {(r["entity"], r["account"]) for r in clearing} != {("PS", "2150"), ("RWH", "1150")}:
            raise ValueError("Wrong intercompany account pairing")
        if {r["entity"]: D(r["signed_usd"]) for r in clearing} != {
            "PS": -CORRECTION,
            "RWH": CORRECTION,
        }:
            raise ValueError("PS/RWH paid-on-behalf balances do not reconcile")

    def value(month):
        return sum(
            D(r["signed_usd"])
            for r in trial_balance_rows
            if r.get("scenario", "base") == "base"
            and r["entity"] == "PS"
            and int(r["year"]) == 2026
            and int(r["month"]) == month
            and r["account"] == "5100"
        )

    if value(8) - value(7) != payroll:
        raise ValueError("PS legal August expense does not support employer payroll")
    return {
        "status": "RECONCILED_LEGAL_EMPLOYER",
        "source_ids": sorted(SOURCE_IDS),
        "period": "2026-08",
        "ps_loaded_payroll_usd": str(payroll),
        "reclassified_usd": str(CORRECTION),
        "additional_group_expense_usd": "0.00",
        "additional_cash_usd": "0.00",
        "settlement": "RWH_PAID_ON_BEHALF_PS_IC_OUTSTANDING",
    }
