"""Entity-specific California minimum floor and visible unpaid performance."""

import json
from decimal import Decimal as D
from pathlib import Path

SOURCE = Path(__file__).with_name("source") / "california_qualifications.json"


class StateMinimum:
    def __init__(self):
        self.source = json.loads(SOURCE.read_text())
        if {(r["entity"], r["first_taxable_year"]) for r in self.source["facts"]} != {
            ("SHIH", 2024),
            ("PS", 2025),
        }:
            raise ValueError("Qualification history changed; renew minimum-tax periods")
        self.rows = [
            dict(
                entity=r["entity"],
                year=y,
                jurisdiction="CA",
                minimum_usd="800",
                current_expense_usd="800",
                cash_paid_usd="0",
                filing_state="NOT_FILED_SOURCE_RECONSTRUCTION",
                payment_state="UNPAID",
                scope="MINIMUM_FLOOR_NOT_FULL_COMBINED_TAX",
            )
            for r in self.source["facts"]
            for y in range(r["first_taxable_year"] + 1, 2032)
        ]

    def post_opening(self, books):
        books.post(
            "SHIH",
            2026,
            0,
            [("3100", D(800)), ("CO_STATE_MIN_PAY", D(-800))],
            "CO-STATE-MIN-2025-SHIH",
            "Unpaid historical California minimum; first-qualified year 2024 exempt",
            kind="COMPANY_STATE_TAX_MINIMUM",
        )

    def post_month(self, books, year, month):
        if month != 1:
            return
        for entity in ["SHIH", "PS"]:
            sid = f"CO-STATE-MIN-{year}-{entity}"
            if any(r["source_id"] == sid for r in books.rows):
                raise ValueError("Duplicate state minimum")
            books.post(
                entity,
                year,
                month,
                [("CO_STATE_MIN_EXP", D(800)), ("CO_STATE_MIN_PAY", D(-800))],
                sid,
                "California qualified/doing-business minimum floor; no tax remittance inferred",
                kind="COMPANY_STATE_TAX_MINIMUM",
            )
