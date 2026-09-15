"""Prospective SB122 invoice tax, separately composed from the immutable FF003 supplement."""

import calendar
import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

SOURCE = Path(__file__).parent / "source/software_sales_tax.json"
Q = D(".0001")


def planning_payment_date(year, month):
    from enterprise.closeout.tax_calendar import observed

    final = date(year, month, calendar.monthrange(year, month)[1])
    memorial = date(year, 5, 31)
    while memorial.weekday() != 0:
        memorial -= timedelta(days=1)
    holidays = {observed(date(year, 1, 1)), observed(date(year + 1, 1, 1)), memorial}
    while final.weekday() > 4 or final in holidays:
        final -= timedelta(days=1)
    return final


class SoftwareTax:
    def __init__(self, operating, source=None):
        self.source = json.loads(SOURCE.read_text()) if source is None else source
        self.rows = []
        self.due = defaultdict(lambda: defaultdict(D))
        self.accrual = defaultdict(list)
        self.input_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        contracts = {c["contract_id"]: c for c in self.source["contracts"]}
        original = {c["contract_id"]: c for c in operating.inputs["contracts"]}
        if set(contracts) != set(original) or len(contracts) != len(self.source["contracts"]):
            raise ValueError("Incomplete/duplicate software contract tax population")
        for cid, c in contracts.items():
            if any(c[k] != original[cid][k] for k in ["customer_id", "unit"]):
                raise ValueError("Wrong software customer/unit")
            if (
                c["california_use_fraction"] != "1"
                or c["product"]
                != "PREWRITTEN_PROVIDER_SOFTWARE_NOT_CUSTOM_OR_CUSTOMER_CODE_INFRASTRUCTURE"
            ):
                raise ValueError("Software use/classification requires new determination")
        rate = D(self.source["rate"])
        if rate != D(".0875"):
            raise ValueError("Changed future planning rate requires source determination")
        totals = defaultdict(D)
        seen = set()
        for invoice in operating.tables["invoices"]:
            cid = invoice["source_id"].split("-TERM-")[0]
            if cid not in contracts:
                continue
            iid = invoice["invoice_id"]
            if iid in seen:
                raise ValueError("Duplicate software tax invoice")
            seen.add(iid)
            m = int(invoice["issue_month"])
            year = 2027 + (m - 1) // 12
            month = (m - 1) % 12 + 1
            case = invoice["scenario"]
            customer = invoice["customer_id"]
            principal = D(invoice["amount_usd"])
            if year < 2027 or year > 2031 or customer != contracts[cid]["customer_id"]:
                raise ValueError("Wrong software invoice period/customer")
            totals[case, customer, year] += principal
            value = (principal * rate).quantize(Q)
            existing = iid == "INV-base-FF-003-TERM-0"
            if existing and (year, month, principal, value) != (2027, 1, D(1740000), D(152250)):
                raise ValueError("Protected FF003 source changed")
            payyear = year + (month == 12)
            paymonth = 1 if month == 12 else month + 1
            paydate = planning_payment_date(payyear, paymonth)
            row = dict(
                invoice_id=iid,
                contract_id=cid,
                customer_id=customer,
                scenario=case,
                entity="SHI",
                unit=invoice["unit"],
                year=year,
                month=month,
                principal_usd=str(principal),
                rate=str(rate),
                tax_usd=str(value),
                source_id="FF-003-TAX" if existing else f"CO-SALES-{iid}",
                state="EXISTING_ISSUANCE_ONLY_NO_REMISSION"
                if existing
                else "AUTHORED_CONDITIONAL_ACCRUAL_AND_CASH_PLAN",
                planned_cash_date="" if existing else paydate.isoformat(),
                known_on="2026-09-15",
            )
            self.rows.append(row)
            if not existing:
                self.accrual[case, year, month].append(row)
                self.due[case, payyear, paymonth][invoice["unit"]] += value
        # The authored population has no insurers, reproduction rights or other digital purchases from SHI.
        # RTC6052 trigger must not be silently ignored when a later source grows past its threshold.
        if any(v > D(5000000) for v in totals.values()):
            raise ValueError("Digital purchaser threshold changes seller/purchaser liability")
        self.population = [
            dict(
                scenario=k[0],
                customer_id=k[1],
                year=k[2],
                digital_purchases_usd=str(v),
                threshold_usd="5000000",
                threshold_exceeded=False,
            )
            for k, v in sorted(totals.items())
        ]

    def post_month(self, books, year, month):
        for row in self.accrual[books.scenario, year, month]:
            if any(r["source_id"] == row["source_id"] for r in books.rows):
                raise ValueError("Duplicate software sales tax overlay")
            value = D(row["tax_usd"])
            books.post(
                "SHI",
                year,
                month,
                [("CO_SOFTWARE_TAX_EXP", value), ("CO_SOFTWARE_TAX_PAY", -value)],
                row["source_id"],
                "SB122 software tax on authored Sacramento use; seller bears tax separately",
                kind="COMPANY_SALES_TAX",
                segment={"foundry-field": "FOUNDRY_FIELD", "atlas-meridian": "ATLAS"}[row["unit"]],
            )
        for unit, value in self.due[books.scenario, year, month].items():
            sid = f"CO-SALES-PAYMENT-{year}-{month}-{unit}"
            if any(r["source_id"] == sid for r in books.rows):
                raise ValueError("Duplicate software tax payment")
            books.post(
                "SHI",
                year,
                month,
                [("CO_SOFTWARE_TAX_PAY", value), ("1000", -value, "OPERATING")],
                f"CO-SALES-PAYMENT-{year}-{month}-{unit}",
                "Authored future monthly sales-tax cash plan; FF003 issuance-only payable excluded",
                kind="COMPANY_SALES_TAX",
                segment={"foundry-field": "FOUNDRY_FIELD", "atlas-meridian": "ATLAS"}[unit],
            )

    def verify(self, rows):
        expected = []
        for (case, year, month), entries in self.accrual.items():
            for row in entries:
                for account, value in [
                    ("CO_SOFTWARE_TAX_EXP", D(row["tax_usd"])),
                    ("CO_SOFTWARE_TAX_PAY", -D(row["tax_usd"])),
                ]:
                    expected.append(
                        (case, "SHI", year, month, row["source_id"], account, value, row["unit"])
                    )
        for (case, year, month), units in self.due.items():
            if year > 2031:
                continue
            for unit, value in units.items():
                for account, amount in [("CO_SOFTWARE_TAX_PAY", value), ("1000", -value)]:
                    expected.append(
                        (
                            case,
                            "SHI",
                            year,
                            month,
                            f"CO-SALES-PAYMENT-{year}-{month}-{unit}",
                            account,
                            amount,
                            unit,
                        )
                    )
        actual = [
            (
                r["scenario"],
                r["entity"],
                int(r["year"]),
                int(r["month"]),
                r["source_id"],
                r["account"],
                D(r["signed_usd"]),
                r["unit"],
            )
            for r in rows
            if r["source_id"].startswith("CO-SALES-")
        ]
        if sorted(actual) != sorted(expected):
            raise ValueError(
                "Software tax posted population differs: omitted/duplicate/reversed/entity/period/unit"
            )
        return {
            "invoice_population": len(self.rows),
            "new_posted_legs": len(actual),
            "ff003_existing_supplement_unchanged": True,
        }
