"""Supported H2 receipt-tax penalties; no payment or assessment is invented."""
import calendar
from datetime import date
from decimal import ROUND_HALF_UP
from decimal import Decimal as D

from enterprise.ccf.company_closeout.tax_calendar_supplement import business_day, history


def build(cutoff="2026-09-14", *, planning_interest_rate=None):
    end = date.fromisoformat(cutoff)
    if not date(2025, 1, 1) <= end <= date(2031, 12, 31):
        raise ValueError("Interest authority/projection covers only 2025–2031")
    if end.year > 2026 and planning_interest_rate is None:
        raise ValueError("Interest authority covers only 2025–2026; explicit planning rate required")
    future_rate = D(str(planning_interest_rate)) if planning_interest_rate is not None else D(".07")
    if not future_rate.is_finite() or not D(0) <= future_rate <= D(1):
        raise ValueError("Invalid planning interest rate")
    source, _ = history()
    rows = []
    for month in range(7, 13):
        population = [r for r in source if r["month"] == month and r["utility_own_use"]]
        if len(population) != 3 or any(D(r["tax_cash_paid_usd"]) != 0 or r["filing_state"] != "NOT_SUBMITTED" for r in population):
            raise ValueError("Reperform penalty for changed settlement/filing population")
        principal = sum(D(r["receipt_rot_usd"]) for r in population)
        due = business_day(date(2025 + (month == 12), month % 12 + 1, 20))
        days = max(0, (end - due).days)
        interest = D(0)
        for year in range(due.year, end.year + 1):
            period_start = max(due, date(year - 1, 12, 31))
            period_end = min(end, date(year, 12, 31))
            elapsed = max(0, (period_end - period_start).days)
            annual_rate = D(".07") if year <= 2026 else future_rate
            interest += principal * annual_rate * elapsed / D(366 if calendar.isleap(year) else 365)
        rate = D(".10") if days > 30 else D(".02") if days else D(0)
        def money(value):
            return str(value.quantize(D(".01"), rounding=ROUND_HALF_UP))
        rows.append(dict(workpaper_id=f"SH-RWH-ROT-PENALTY-2025{month:02d}", entity="RWH", tax_owner="PS",
                         tax_period=f"2025-{month:02d}", due_on=due.isoformat(), as_of=cutoff, days_overdue=days,
                         source_ids=[r["source_id"] for r in population], principal_usd=str(principal),
                         late_filing_usd=money(min(D(250), principal * D(".02")) if days else D(0)),
                         late_payment_usd=money(principal * rate),
                         interest_usd=money(interest),
                         cash_paid_usd="0", state="CONDITIONAL_UNPAID_PLANNING_RATE" if end.year > 2026 else "MODELED_UNPAID_NOT_REGULATOR_ASSESSMENT",
                         planning_interest_rate=str(future_rate) if end.year > 2026 else None))
    return {"rows": rows, "totals": {k: str(sum(D(r[k]) for r in rows)) for k in
            ("principal_usd", "late_filing_usd", "late_payment_usd", "interest_usd")},
            "authored_on": "2026-09-22", "scope": "H2 2025 utility receipt tax; no 2026 accelerated-payment population inferred"}
