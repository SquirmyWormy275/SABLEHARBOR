"""Accrue supported historical ROT penalties and separately identified interest."""

from calendar import monthrange
from decimal import Decimal as D

from enterprise.ccf.company_closeout.rot_penalty_workpaper import build

TYPES = {
    "CO_ROT_PENALTY_EXP": "expense",
    "CO_ROT_INTEREST_EXP": "expense",
    "CO_ROT_PENALTY_PAY": "liability",
    "CO_ROT_INTEREST_PAY": "liability",
}


class RotPenalties:
    def __init__(self):
        self.opening = build("2025-12-31")
        self.cutoff = build("2026-09-14")
        self.rows = []
        previous = self.amounts(self.opening)
        for year in range(2026, 2032):
            for month in range(1, 13):
                as_of = f"{year}-{month:02d}-{monthrange(year, month)[1]:02d}"
                result = build(
                    as_of, **({"planning_interest_rate": D(".07")} if year > 2026 else {})
                )
                current = self.amounts(result)
                self.rows.append(
                    dict(
                        year=year,
                        month=month,
                        as_of=as_of,
                        penalty_activity_usd=str(current[0] - previous[0]),
                        interest_activity_usd=str(current[1] - previous[1]),
                        closing_penalty_usd=str(current[0]),
                        closing_interest_usd=str(current[1]),
                        cash_paid_usd="0",
                        scope="H2_2025_RECEIPT_TAX_ONLY",
                        fact_state="AUTHORED_COMPLETED_PERIOD"
                        if (year, month) <= (2026, 8)
                        else "CONDITIONAL_UNPAID_SCENARIO",
                        interest_rate_state="VERIFIED_2025_2026"
                        if year <= 2026
                        else "HELD_7_PERCENT_PLANNING_ASSUMPTION",
                    )
                )
                previous = current

    @staticmethod
    def amounts(result):
        t = result["totals"]
        return D(t["late_filing_usd"]) + D(t["late_payment_usd"]), D(t["interest_usd"])

    @staticmethod
    def post(books, year, month, entries, source_id):
        if any(r["source_id"] == source_id for r in books.rows):
            raise ValueError("Duplicate ROT penalty accrual")
        books.post(
            "RWH",
            year,
            month,
            entries,
            source_id,
            "Unpaid H2 receipt-tax penalty/interest; no payment or regulator assessment inferred",
            kind="COMPANY_ROT_PENALTY_SUCCESSOR",
        )

    def post_opening(self, books):
        penalty, interest = self.amounts(self.opening)
        self.post(
            books,
            2026,
            0,
            [
                ("3100", penalty + interest),
                ("CO_ROT_PENALTY_PAY", -penalty),
                ("CO_ROT_INTEREST_PAY", -interest),
            ],
            "CO-ROT-PENALTY-OPEN",
        )

    def post_month(self, books, year, month):
        row = next(r for r in self.rows if (r["year"], r["month"]) == (year, month))
        penalty, interest = D(row["penalty_activity_usd"]), D(row["interest_activity_usd"])
        if penalty or interest:
            self.post(
                books,
                year,
                month,
                [
                    ("CO_ROT_PENALTY_EXP", penalty),
                    ("CO_ROT_INTEREST_EXP", interest),
                    ("CO_ROT_PENALTY_PAY", -penalty),
                    ("CO_ROT_INTEREST_PAY", -interest),
                ],
                f"CO-ROT-PENALTY-{year}{month:02d}",
            )
