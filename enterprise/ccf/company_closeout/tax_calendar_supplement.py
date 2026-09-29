"""Entity-specific filing dates and historical receipt workpaper; posts no cash."""
import calendar
import json
from datetime import date, timedelta
from decimal import ROUND_HALF_UP
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).with_name("tax_calendar_supplement.json")
CENT = D(".01")


def business_day(day):
    def observed(d):
        return d + timedelta(days=1) if d.weekday() == 6 else d - timedelta(days=1) if d.weekday() == 5 else d
    def nth(month, weekday, n):
        d = date(day.year, month, 1)
        return d + timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))
    holidays = {observed(date(day.year, m, d)) for m, d in [(1, 1), (6, 19), (7, 4), (11, 11), (12, 25)]}
    holidays |= {nth(1, 0, 3), nth(2, 0, 3), nth(9, 0, 1), nth(10, 0, 2), nth(11, 3, 4)}
    memorial = date(day.year, 5, 31)
    holidays.add(memorial - timedelta(days=memorial.weekday()))
    while day.weekday() > 4 or day in holidays:
        day += timedelta(days=1)
    return day


def history(source=None):
    s = json.loads(SOURCE.read_text()) if source is None else source
    contracts = json.loads((ROOT / "red_wash/source/core_operating_data.json").read_text())["contract_book_2026"]
    weights = {r["contract_id"]: D(str(r["pounds"])) * D(str(r["price_usd_lb"])) for r in contracts}
    total = sum(weights.values())
    utility = {"UCA-2019-04", "UCA-2024-11", "UCA-2025-03"}
    if set(weights) != utility | {"SPOT-2026-01"}:
        raise ValueError("Historical receipt contract population changed")
    if [r["month"] for r in s["historical_months"]] != list(range(7, 13)):
        raise ValueError("Missing/duplicate H2 period")
    if sum(D(r["sales_usd"]) for r in s["historical_months"]) != D("12600000") or sum(D(r["receipts_usd"]) for r in s["historical_months"]) != D("8600000"):
        raise ValueError("H2 source sales/receipts changed")
    acquired = s["acquired_receivables"]
    monthly = acquired["monthly_allocation_usd"]
    opening = D(acquired["opening_acquired_ar_usd"])
    collected = D(acquired["collections_usd"])
    closing = D(acquired["closing_acquired_ar_usd"])
    if (
        set(monthly) != {str(m) for m in range(7, 13)}
        or any(D(v) < 0 for v in monthly.values())
        or sum(D(v) for v in monthly.values()) != collected
        or opening != D("4000000") or collected != D("4000000")
        or opening - collected != closing or closing != 0
        or acquired["collection_period"] != "2025-07-18/2025-12-31"
    ):
        raise ValueError("Acquired receivable collection bridge changed")
    balances, rows = {c: D(0) for c in weights}, []
    for month in s["historical_months"]:
        allocations = {}
        for field in ["sales_usd", "receipts_usd"]:
            amount = D(month[field])
            values = {c: (amount * w / total).quantize(CENT, rounding=ROUND_HALF_UP) for c, w in weights.items()}
            values[sorted(values)[-1]] += amount - sum(values.values())
            allocations[field] = values
        for contract in weights:
            sales, receipts = (allocations[f][contract] for f in ["sales_usd", "receipts_usd"])
            balances[contract] += sales - receipts
            if balances[contract] < 0:
                raise ValueError("Historical receipt exceeds invoiced principal")
            tax = (sales * D(".0625")).quantize(CENT, rounding=ROUND_HALF_UP) if contract in utility else None
            receipt_tax = (receipts * D(".0625")).quantize(CENT, rounding=ROUND_HALF_UP) if contract in utility else None
            rows.append(dict(source_id=f"SH-RWH-H2-ROT-2025{month['month']:02d}-{contract}", entity="RWH", tax_owner="PS",
                             year=2025, month=month["month"], contract_id=contract, sales_usd=str(sales), receipts_usd=str(receipts),
                             closing_ar_usd=str(balances[contract]), utility_own_use=contract in utility,
                             accrued_rot_usd=str(tax) if tax is not None else None,
                             receipt_rot_usd=str(receipt_tax) if receipt_tax is not None else None,
                             tax_cash_paid_usd="0", filing_state="NOT_SUBMITTED", origin=s["origin"]))
    accrual = sum(D(r["accrued_rot_usd"]) for r in rows if r["utility_own_use"])
    collected = sum(D(r["receipt_rot_usd"]) for r in rows if r["utility_own_use"])
    return rows, dict(sales_usd="12600000", receipts_usd="8600000", closing_ar_usd=str(sum(balances.values())),
                      acquired_ar_collections_usd="4000000", total_h2_cash_collections_usd="12600000",
                      acquired_ar_new_revenue_usd="0", acquired_ar_new_rot_expense_usd="0",
                      utility_accrued_rot_usd=str(accrual), utility_receipt_rot_usd=str(collected),
                      threshold_monthly_lower_bound_usd=str(collected / 12), accelerated_threshold_exceeded=collected / 12 >= D(20000),
                      trader_tax_state="NOT_AUTOMATICALLY_EXEMPT_SEPARATE_CERTIFICATE_OR_TAX_REVIEW", cash_posted_usd="0")


def build():
    source = json.loads(SOURCE.read_text())
    historical, bridge = history(source)
    rows = []
    cutoff = date.fromisoformat(source["event_cutoff"])
    def add(entity, jurisdiction, year, month, form, due, state, condition, scope):
        adjusted = business_day(due)
        rows.append(dict(calendar_id=f"SH-CAL-{entity}-{jurisdiction}-{year}-{month:02d}-{form}-{due.day}",
                         entity=entity, jurisdiction=jurisdiction, tax_year=year, month=month, form=form,
                         nominal_due_on=due.isoformat(), ordinary_due_on=adjusted.isoformat(),
                         due_state="FUTURE_DUE" if adjusted > cutoff else "DUE_BY_CUTOFF",
                         performance_state=state, condition=condition, scope=scope, payment_cash_posted_usd="0",
                         origin=source["origin"], authority_ids=";".join(source["authorities"]),
                         calendar_basis="ORDINARY_NO_DISASTER_EXTENSION;FUTURE_YEARS_HOLD_RESEARCHED_RULES"))
    add("PS", "IL", 2025, 12, "IL-1120+UB", date(2026, 4, 15), "NOT_SUBMITTED",
        "ANNUAL_RETURN_REQUIRED_EVEN_IF_TAX_ZERO", "PS includes RWH DRE;2025 postclosing population, no ARU/BST acquisition backdating")
    for month in range(7, 13):
        add("RWH", "IL", 2025, month, "ST-1", date(2025 + (month == 12), month % 12 + 1, 20),
            "NOT_SUBMITTED_UNPAID", "MONTHLY_REGISTERED_ACCOUNT", "Authored H2 receipt population; utility tax unremitted; trader review separate")
    for year in range(2026, 2032):
        for jurisdiction, member, form in [("IL", "PS", "IL-1120+UB"), ("WV", "SHI", "CIT-120+UB-CR")]:
            add(member, jurisdiction, year, 12, form, date(year + 1, 4, 15), "NOT_SUBMITTED", "ANNUAL_RETURN_REQUIRED_EVEN_IF_TAX_ZERO",
                "Combined member information; WV separate-combined return, no elective group filing inferred")
            for month in [4, 6, 9, 12]:
                add(member, jurisdiction, year, month, "INCOME_ESTIMATE", date(year, month, 15), "AMOUNT_AND_SETTLEMENT_JOIN_FINANCE_PROVIDER",
                    "IL_NET_TAX_GT400" if jurisdiction == "IL" else "WV_TAXABLE_INCOME_GT10000_NET_TAX_GT650",
                    "Corporate estimate, not payroll deposit or ROT remittance; zero only after tax-base computation")
        for month in range(1, 13):
            following = date(year + (month == 12), month % 12 + 1, 20)
            add("RWH", "IL", year, month, "ST-1", following, "NOT_SUBMITTED_UNPAID",
                "MONTHLY_REGISTERED_ACCOUNT", "Receipt reporting; older sales retain transaction rate; no duplicate accrual")
            for day in [7, 15, 22, calendar.monthrange(year, month)[1]]:
                add("RWH", "IL", year, month, "RR-3", date(year, month, day), "UNPAID" if year == 2026 else "CONDITIONAL_UNPAID",
                    "2025_UTILITY_RECEIPT_LOWER_BOUND_GT20000_MONTHLY;FUTURE_RECHECK_REQUIRED",
                    "Quarter-monthly accelerated payment dates; amount requires receipt-based safe-harbor computation, not one-quarter annual accrual")
    return {"calendar": rows, "historical_receipts": historical, "historical_bridge": bridge, "source": source}
