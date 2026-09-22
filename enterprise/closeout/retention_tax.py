"""July 2026 employer retention levy, separate from retained regular-salary burden."""

import hashlib
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

from enterprise.operations.completed_period import ROOT, make_roster, read
from enterprise.operations.completed_period import SOURCE as HR_SOURCE
from enterprise.operations.retention_payroll import SOURCE as TAX_SOURCE
from enterprise.operations.retention_payroll import workpapers

PAYABLE = "CO_PAYROLL_EMP_TAX_PAY"
SOURCE_IDS = {"ARU": "CO-RETENTION-EMP-TAX-ARU-202607", "BST": "CO-RETENTION-EMP-TAX-BST-202607"}


def source_bonus_rows():
    source = read(HR_SOURCE)
    people = make_roster(source)[0]
    return [r for r in workpapers(source, people) if r["payment_kind"] == "RETENTION"]


class RetentionTax:
    account_types = {"5000": "expense", PAYABLE: "liability"}

    def __init__(self, payroll_workpapers=None):
        expected = source_bonus_rows()
        supplied = (
            expected
            if payroll_workpapers is None
            else [r for r in payroll_workpapers if r["payment_kind"] == "RETENTION"]
        )
        fields = [
            "event_id",
            "person_id",
            "employee_name",
            "legal_entity",
            "event_period",
            "payment_kind",
            "opening_ytd_usd",
            "gross_usd",
            "closing_ytd_usd",
            "employee_withholding_usd",
            "employee_net_usd",
            "employer_known_taxes_usd",
            "tax_components",
            "paid_on",
            "source_id",
        ]

        def normalize(rows):
            return sorted(
                [{key: r.get(key) for key in fields} for r in rows], key=lambda r: r["event_id"]
            )

        if normalize(supplied) != normalize(expected):
            raise ValueError(
                "Retention employer levy differs from accepted-award wage/tax workpapers"
            )
        self.totals = defaultdict(D)
        for row in supplied:
            self.totals[row["legal_entity"]] += D(row["employer_known_taxes_usd"])
        if dict(self.totals) != {"ARU": D("16065.00"), "BST": D("8201.75")}:
            raise ValueError(
                "Retention compensation or tax rules changed; reperform correction scope"
            )
        self.source_hashes = {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                ROOT / HR_SOURCE,
                ROOT / TAX_SOURCE,
                ROOT / "industrial/source/finance.json",
                ROOT / "enterprise/operations/retention_payroll.py",
                ROOT / "enterprise/operations/completed_period.py",
                Path(__file__),
            ]
        }
        self.input_hash = hashlib.sha256("".join(self.source_hashes.values()).encode()).hexdigest()

    def post_month(self, books, year, month):
        if (year, month) != (2026, 7):
            return
        if any(row["source_id"] in SOURCE_IDS.values() for row in books.rows):
            raise ValueError("Duplicate retention employer-tax correction")
        if any(books.types.get(account) != kind for account, kind in self.account_types.items()):
            raise ValueError(
                "Retention expense/liability account classification is missing or wrong"
            )
        for entity, value in self.totals.items():
            books.post(
                entity,
                year,
                month,
                [("5000", value), (PAYABLE, -value)],
                SOURCE_IDS[entity],
                "July retention employer levy; separate from regular burden, unremitted",
                kind="COMPANY_RETENTION_EMPLOYER_TAX",
                segment="CORPORATE",
            )

    def receipt(self):
        return {
            "period": "2026-07",
            "account_types": self.account_types,
            "source_ids": SOURCE_IDS,
            "employer_levy_usd": {k: str(v) for k, v in self.totals.items()},
            "total_usd": str(sum(self.totals.values())),
            "cash_paid_usd": "0.00",
            "settlement_state": "ACCRUED_UNREMITTED_EMPLOYER_LEVY",
            "gross_retention_source_cash_unchanged_usd": "250000.00",
            "source_hashes": self.source_hashes,
            "limits": [
                "Existing regular-salary burden and gross employee bonus batch remain unchanged.",
                "No January2027 award, phantom carry, new salary or new financing is created.",
                "Tax deduction timing, deposit deadlines and penalties have separate workpapers.",
            ],
        }
