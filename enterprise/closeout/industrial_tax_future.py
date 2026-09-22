"""Conditional utility ROT continuation; no customer receipt or remittance fabricated."""
import hashlib
import json
from collections import defaultdict
from decimal import ROUND_HALF_UP
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name("source") / "industrial_tax_future.json"
PREFIX = "SH-RWH-FUTURE-IL-ROT-"
CENT = D(".01")


class FutureIndustrialTax:
    def __init__(self, result):
        source = json.loads(SOURCE.read_text())
        for path, digest in source["source_hashes"].items():
            if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
                raise ValueError("Changed future ROT controlling source")
        contracts = json.loads((ROOT / source["contracts_source"]).read_text())["contract_book_2026"]
        weights = {r["contract_id"]: D(str(r["pounds"])) * D(str(r["price_usd_lb"])) for r in contracts}
        if set(weights) != set(source["allocation_contracts"]):
            raise ValueError("Changed future contract allocation population")
        total = sum(weights.values())
        gross, seen = defaultdict(D), set()
        for row in result["journal_rows"]:
            if row["source_id"].startswith(PREFIX):
                raise ValueError("Future ROT requires pre-adjustment books")
            if row["entity"] != "RWH" or row["account"] != "4000" or int(row["year"]) == 2026 or int(row["month"]) == 0:
                continue
            key = (row["scenario"], int(row["year"]), int(row["month"]))
            identity = key + (row["journal_id"], str(row.get("line_no", row["account"])))
            if identity in seen:
                raise ValueError("Duplicate future mine revenue")
            seen.add(identity)
            gross[key] -= D(row["signed_usd"])
        expected = {(s, y, m) for s in source["scenarios"] for y in source["years"] for m in range(1, 13)}
        if set(gross) != expected or any(v < 0 for v in gross.values()):
            raise ValueError("Wrong or incomplete future mine sale population")
        self.rows, self.allocation_rows = [], []
        for (scenario, year, month), amount in sorted(gross.items()):
            # Reconcile every source cent: residual belongs to last sorted contract,
            # including the separately excluded trader; never inflate utility principals.
            rounded_total = amount.quantize(CENT, rounding=ROUND_HALF_UP)
            principals = {c: (amount * weights[c] / total).quantize(CENT, rounding=ROUND_HALF_UP) for c in sorted(weights)}
            principals[sorted(weights)[-1]] += rounded_total - sum(principals.values())
            for contract, principal in principals.items():
                utility = contract in source["taxable_utility_contracts"]
                self.allocation_rows.append(dict(scenario=scenario, year=year, month=month, contract_id=contract,
                                                principal_usd=str(principal), disposition="UTILITY_OWN_USE" if utility else "TRADER_RESALE_REVIEW_SEPARATE"))
                if not utility:
                    continue
                tax = (principal * D(source["planning_rate"])).quantize(CENT, rounding=ROUND_HALF_UP)
                self.rows.append(dict(scenario=scenario, year=year, month=month, entity="RWH", contract_id=contract,
                                      source_id=f"{PREFIX}{year}{month:02d}-{contract}", principal_usd=str(principal),
                                      tax_rate=source["planning_rate"], tax_expense_usd=str(tax), tax_payable_usd=str(tax),
                                      tax_cash_paid_usd="0", customer_tax_billed_usd="0",
                                      record_role="CONDITIONAL_FORECAST_NOT_COMPLETED_TRANSACTION",
                                      receipt_state="FORECAST_REVENUE_NOT_CUSTOMER_CASH_RECEIPT",
                                      filing_state="NOT_SUBMITTED", payment_state="NO_MODELED_REMITTANCE",
                                      payment_plan_state="COLLECTION_TIMING_AND_ACCELERATED_LOOKBACK_REVIEW_REQUIRED",
                                      rate_state="HELD_2026_PLANNING_RATE_REQUIRES_FUTURE_LAW_REFRESH"))

    def post_month(self, books, year, month):
        for row in self.rows:
            if (row["scenario"], row["year"], row["month"]) != (books.scenario, year, month):
                continue
            if any(r["source_id"] == row["source_id"] for r in books.rows):
                raise ValueError("Duplicate future ROT")
            amount = D(row["tax_expense_usd"])
            books.post("RWH", year, month, [("CO_RWH_ROT_EXP", amount), ("CO_RWH_ROT_PAY", -amount)],
                       row["source_id"], "Conditional utility ROT continuation; seller burden, no remittance assumed",
                       kind="COMPANY_TRANSACTION_TAX")

    def verify(self, rows):
        expected = {(r["scenario"], r["source_id"], "RWH", r["year"], r["month"], a): D(r["tax_expense_usd"]) * sign
                    for r in self.rows for a, sign in [("CO_RWH_ROT_EXP", 1), ("CO_RWH_ROT_PAY", -1)]}
        actual = {}
        for row in rows:
            if not row["source_id"].startswith(PREFIX):
                continue
            key = (row["scenario"], row["source_id"], row["entity"], int(row["year"]), int(row["month"]), row["account"])
            if key in actual:
                raise ValueError("Duplicate future ROT leg")
            actual[key] = D(row["signed_usd"])
        if actual != expected:
            raise ValueError("Future ROT population/entity/period/sign differs")
        return dict(invoice_accruals=len(self.rows), cash_paid_usd="0", allocation_rows=len(self.allocation_rows))
