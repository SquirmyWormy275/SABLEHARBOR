"""Source-linked 2026 RWH utility ROT accrual; collections are not new sales."""

import json
from collections import defaultdict
from decimal import ROUND_HALF_UP
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "enterprise/ccf/company_closeout/industrial_transaction_tax.json"
CONTRACTS = ROOT / "red_wash/source/core_operating_data.json"


class IndustrialTax:
    def __init__(self, result):
        source = json.loads(SOURCE.read_text())
        periods = source["period_contract_2026"]
        contracts = json.loads(CONTRACTS.read_text())["contract_book_2026"]
        weights = {
            r["contract_id"]: D(str(r["pounds"])) * D(str(r["price_usd_lb"])) for r in contracts
        }
        total = sum(weights.values())
        gross = defaultdict(D)
        self.rows = []
        if any(r["source_id"].startswith("SH-RWH-IL-ROT-") for r in result["journal_rows"]):
            raise ValueError("RWH ROT requires pre-adjustment books")
        for r in result["journal_rows"]:
            if (
                r["entity"] == "RWH"
                and int(r["year"]) == 2026
                and int(r["month"]) > 0
                and r["account"] == "4000"
            ):
                gross[r["scenario"], int(r["month"])] -= D(r["signed_usd"])
        if set(gross) != {(s, m) for s in ["base", "downside", "expansion"] for m in range(1, 13)}:
            raise ValueError("Incomplete native RWH 2026 sale population")
        reference = {
            r["contract_id"]: r
            for r in source["rows"]
            if r.get("classification") == "IL_UTILITY_OWN_USE"
        }
        for (scenario, month), amount in sorted(gross.items()):
            period = periods["periods"][month - 1]
            if period["period"] != f"2026-{month:02d}":
                raise ValueError("Wrong tax rate period")
            for contract in periods["contracts"]:
                principal = (amount * weights[contract] / total).quantize(
                    D(".01"), rounding=ROUND_HALF_UP
                )
                tax = (principal * D(period["rate"])).quantize(D(".01"), rounding=ROUND_HALF_UP)
                sid = f"SH-RWH-IL-ROT-2026{month:02d}-{contract}"
                if month == 8:
                    ref = reference[contract]
                    if (principal, tax, sid) != (
                        D(str(ref["principal_usd"])),
                        D(str(ref["sales_tax_usd"])),
                        ref["adjustment_source_id"],
                    ):
                        raise ValueError("August independent invoice tax reconciliation failed")
                self.rows.append(
                    dict(
                        scenario=scenario,
                        year=2026,
                        month=month,
                        entity="RWH",
                        contract_id=contract,
                        source_id=sid,
                        principal_usd=str(principal),
                        tax_rate=period["rate"],
                        tax_expense_usd=str(tax),
                        tax_payable_usd=str(tax),
                        tax_cash_paid_usd="0",
                        customer_tax_billed_usd="0",
                        record_role=period["record_role"],
                        filing_state="RECEIPT_ALLOCATION_AND_RETURN_REVIEW_REQUIRED",
                        measurement="NATIVE_MONTHLY_REVENUE_ALLOCATED_BY_SOURCE_CONTRACT_VALUE",
                    )
                )

    def post_month(self, books, year, month):
        for r in self.rows:
            if (r["scenario"], r["year"], r["month"]) != (books.scenario, year, month):
                continue
            if any(x["source_id"] == r["source_id"] for x in books.rows):
                raise ValueError("Duplicate RWH ROT")
            v = D(r["tax_expense_usd"])
            books.post(
                "RWH",
                year,
                month,
                [("CO_RWH_ROT_EXP", v), ("CO_RWH_ROT_PAY", -v)],
                r["source_id"],
                "Utility own-use Illinois sale: seller ROT accrual; no remittance or reimbursement inferred",
                kind="COMPANY_TRANSACTION_TAX",
            )

    def verify(self, rows):
        expected = {
            (r["scenario"], r["source_id"], "RWH", 2026, r["month"], a): D(r["tax_expense_usd"])
            * sign
            for r in self.rows
            for a, sign in [("CO_RWH_ROT_EXP", 1), ("CO_RWH_ROT_PAY", -1)]
        }
        actual = {}
        for r in rows:
            if not r["source_id"].startswith("SH-RWH-IL-ROT-"):
                continue
            key = (
                r["scenario"],
                r["source_id"],
                r["entity"],
                int(r["year"]),
                int(r["month"]),
                r["account"],
            )
            if key in actual:
                raise ValueError("Duplicate ROT leg")
            actual[key] = D(r["signed_usd"])
        if actual != expected:
            raise ValueError("RWH ROT population, period, entity or sign differs")
        return {
            "invoice_accruals": len(self.rows),
            "cash_paid_usd": "0",
            "reporting_state": "RECEIPT_ALLOCATION_REQUIRED",
        }


def august_receipt_workpaper(edition):
    """Reclassify tax on identified collections; never create another accrual."""
    source = json.loads(SOURCE.read_text())["period_contract_2026"]
    rates = {p["period"]: D(p["rate"]) for p in source["periods"]}
    contracts = set(source["contracts"])
    rows = []
    seen = set()
    for invoice in edition["tables"]["current_customer_invoice_ledger"]:
        contract = invoice.get("source_contract_id")
        if contract not in contracts:
            continue
        ident = invoice["invoice_id"]
        if ident in seen:
            raise ValueError("Duplicate utility receipt-tax invoice")
        seen.add(ident)
        period = invoice["sale_period"]
        if period not in rates or invoice["legal_issuer"] != "RWH":
            raise ValueError("Utility invoice lacks valid underlying sale period/entity")
        paid = D(invoice["paid_august_usd"])
        outstanding = D(invoice["closing_gross_usd"])
        if paid < 0 or outstanding < 0:
            raise ValueError("Negative collection requires separately reviewed credit")
        rows.append(
            dict(
                invoice_id=ident,
                contract_id=contract,
                sale_period=period,
                collection_period="2026-08",
                receipt_principal_usd=str(paid),
                rate=str(rates[period]),
                collected_tax_usd=str(
                    (paid * rates[period]).quantize(D(".01"), rounding=ROUND_HALF_UP)
                ),
                uncollected_tax_usd=str(
                    (outstanding * rates[period]).quantize(D(".01"), rounding=ROUND_HALF_UP)
                ),
                additional_book_expense_usd="0",
                tax_cash_paid_usd="0",
                collection_origin="SOURCE_LINKED_SYNTHETIC_CUSTOMER_RECEIPT",
                return_state="PREPARED_WORKPAPER_NOT_FILED",
                payment_state="NO_TAX_REMITTANCE_EVIDENCE",
                accelerated_payment_state="PRIOR_LOOKBACK_REVIEW_REQUIRED",
            )
        )
    if len(rows) != 9 or {r["sale_period"] for r in rows} != {"2026-06", "2026-07", "2026-08"}:
        raise ValueError("Incomplete June/July/August utility invoice population")
    collected = sum(D(r["collected_tax_usd"]) for r in rows)
    whole = collected.quantize(D(1), rounding=ROUND_HALF_UP)
    bridge = dict(
        collection_period="2026-08",
        collected_tax_cents_usd=str(collected),
        indicative_whole_dollar_tax_usd=str(whole),
        rounding_difference_usd=str(whole - collected),
        ordinary_return_due="2026-09-21",
        due_basis="September20 Sunday shifts to next business day; accelerated installments require separate lookback",
        completeness="THREE_UTILITY_CONTRACTS_ONLY_NOT_COMPLETE_ST1",
        trader_other_period_certificate_state="UNRESOLVED_NOT_ASSUMED_EXEMPT",
        filing_state="NOT_SUBMITTED",
        acknowledgement_state="NONE",
        tax_cash_paid_usd="0",
    )
    return rows, [bridge]
