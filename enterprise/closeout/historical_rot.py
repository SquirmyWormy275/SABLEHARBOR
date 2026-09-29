"""Unpaid H2 2025 seller ROT: dated noncash opening correction."""

from decimal import Decimal as D

from enterprise.ccf.company_closeout.tax_calendar_supplement import history

PREFIX = "CO-H2-ROT-"


class HistoricalRot:
    def __init__(self):
        self.rows, self.bridge = history()
        self.entries = [r for r in self.rows if r["utility_own_use"]]

    def post_opening(self, books):
        for row in self.entries:
            source = PREFIX + row["source_id"]
            if any(r["source_id"] == source for r in books.rows):
                raise ValueError("Duplicate historical ROT opening correction")
            amount = D(row["accrued_rot_usd"])
            books.post(
                "RWH",
                2026,
                0,
                [("3100", amount), ("CO_RWH_ROT_PAY", -amount)],
                source,
                "H2 2025 seller ROT omitted from predecessor; accrued, unremitted, no tax deduction",
                kind="COMPANY_HISTORICAL_TAX_CORRECTION",
            )

    def verify(self, rows):
        expected = {
            (scenario, PREFIX + r["source_id"], "RWH", 2026, 0, account): D(r["accrued_rot_usd"])
            * sign
            for scenario in ("base", "downside", "expansion")
            for r in self.entries
            for account, sign in (("3100", 1), ("CO_RWH_ROT_PAY", -1))
        }
        actual = {}
        for row in rows:
            if not row["source_id"].startswith(PREFIX):
                continue
            key = (
                row["scenario"],
                row["source_id"],
                row["entity"],
                int(row["year"]),
                int(row["month"]),
                row["account"],
            )
            if key in actual:
                raise ValueError("Duplicate historical ROT leg")
            actual[key] = D(row["signed_usd"])
        if actual != expected:
            raise ValueError("Historical ROT source/entity/period/amount mismatch")
        return {
            "source_invoices": len(self.entries),
            "unpaid_opening_usd": self.bridge["utility_accrued_rot_usd"],
            "cash_usd": "0",
        }
