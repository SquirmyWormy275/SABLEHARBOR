"""Independent controls for procurement evidence and cash clearing."""

import copy
import json
import unittest
from decimal import Decimal

from industrial.planning.transactions import (
    OLD_FINANCE,
    attach_procurement_postings,
    detailed_service_and_payroll,
    journal_evidence,
    policy_source,
    procurement_costs,
    procurement_documents,
    split_money,
    validate_procurement,
)


def operating_row(factor=1, cost_index=1):
    return {
        "scenario": "base",
        "year": 2027,
        "month": 1,
        "assumptions": {"cash_cost_index": cost_index},
        "segments": {
            s: {"cost_volume_factor": factor} for s in ["BST", "TERMINALS", "TRUCKING", "WAREHOUSE"]
        },
    }


def posting(ident, month, account, signed):
    return {
        "scenario": "base",
        "entity": "ARU_GROUP",
        "year": 2027,
        "month": month,
        "journal_id": ident,
        "account": account,
        "signed_usd": signed,
        "debit_usd": max(signed, 0),
        "credit_usd": max(-signed, 0),
        "source_id": ident,
    }


class TransactionTests(unittest.TestCase):
    def test_quantity_cost_changes_and_fixed_cost_survives_shutdown(self):
        base = procurement_costs([operating_row()])
        stopped = procurement_costs([operating_row(factor=0)])
        a = next(r for r in base if r["segment"] == "BST")
        b = next(r for r in stopped if r["segment"] == "BST")
        self.assertGreater(a["external_cost_usd"], b["external_cost_usd"])
        self.assertGreater(b["external_cost_usd"], 0)
        self.assertEqual(sum(i["variable_cost_usd"] for i in b["items"]), 0)
        for item in a["items"]:
            expected = (
                Decimal(item["quantity"])
                * Decimal(item["calibrated_unit_rate_usd"])
                * Decimal(item["cost_index"])
            )
            self.assertLessEqual(abs(Decimal(item["variable_cost_usd"]) - expected), Decimal(".5"))

    def test_changed_cost_index_propagates_without_touching_history(self):
        base = procurement_costs([operating_row()])
        higher = procurement_costs([operating_row(cost_index=1.25)])
        self.assertGreater(
            sum(r["external_cost_usd"] for r in higher), sum(r["external_cost_usd"] for r in base)
        )

    def test_foreign_scenario_and_tampered_quantity_rejected(self):
        tables = procurement_documents(procurement_costs([operating_row()]))
        self.assertEqual(validate_procurement(tables), 25)
        bad = copy.deepcopy(tables)
        bad["receipts"][0]["scenario"] = "downside"
        with self.assertRaisesRegex(ValueError, "cross-scenario"):
            validate_procurement(bad)
        bad = copy.deepcopy(tables)
        bad["receipts"][0]["quantity"] = "999999"
        with self.assertRaisesRegex(ValueError, "quantity"):
            validate_procurement(bad)

    def test_procurement_requires_real_corresponding_ledger_posting(self):
        tables = procurement_documents(procurement_costs([operating_row()]))
        with self.assertRaisesRegex(ValueError, "not posted"):
            attach_procurement_postings(tables, [])
        journal = [
            {
                "scenario": r["scenario"],
                "source_id": r["source_id"],
                "account": "5100",
                "signed_usd": r["amount_usd"],
            }
            for r in tables["supplier_invoices"]
        ]
        self.assertEqual(attach_procurement_postings(tables, journal), 25)
        journal[0]["signed_usd"] += 1
        with self.assertRaisesRegex(ValueError, "mismatch"):
            attach_procurement_postings(tables, journal)

    def test_cash_recon_handles_clearance_timing_independently(self):
        journal = [
            posting("OPEN", 0, "1000", 1000),
            posting("OPEN", 0, "3000", -1000),
            posting("BILL", 1, "5100", 400),
            posting("BILL", 1, "1000", -400),
            posting("SALE", 2, "1000", 250),
            posting("SALE", 2, "4000", -250),
        ]
        evidence = journal_evidence(journal)
        january, february, march = evidence["bank_reconciliations"][:3]
        self.assertEqual(january["ledger_cash_usd"], 600)
        self.assertEqual(january["closing_bank_cash_usd"], 1000)
        self.assertEqual(january["outstanding_payments_usd"], 400)
        self.assertEqual(february["closing_bank_cash_usd"], 600)
        self.assertEqual(february["deposits_in_transit_usd"], 250)
        self.assertEqual(march["closing_bank_cash_usd"], 850)
        self.assertTrue(all(r["difference_usd"] == 0 for r in evidence["bank_reconciliations"]))
        self.assertEqual(len(evidence["sales_invoices"]), 1)

    def test_unbalanced_source_cannot_become_balanced_bank_evidence(self):
        journal = [posting("OPEN", 0, "1000", 1000), posting("OPEN", 0, "3000", -999)]
        with self.assertRaisesRegex(ValueError, "unbalanced"):
            journal_evidence(journal)

    def test_duplicate_months_and_invalid_rates_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            procurement_costs([operating_row(), operating_row()])
        source = policy_source()
        source["expense_categories"][0]["variable_fraction"] = "1.1"
        with self.assertRaisesRegex(ValueError, "shares"):
            procurement_costs([operating_row()], source)

    def test_allocation_preserves_signed_amounts(self):
        self.assertEqual(sum(split_money(-101, [1, 1, 1])), -101)
        self.assertEqual(split_money(2, [1, 1, 1]), [1, 1, 0])
        with self.assertRaises(ValueError):
            split_money(1, [0, 0])

    def test_payroll_settlement_and_physical_service_allocations(self):
        source = json.loads(OLD_FINANCE.read_text())
        workforce = [r for r in source["employees"] if r["segment"] == "BST"]
        op = operating_row()
        op["segments"]["BST"].update(fte=sum(r["fte"] for r in workforce) + 2, served_units=701)
        batch = {
            "scenario": "base",
            "entity": "ARU_GROUP",
            "year": 2027,
            "month": 1,
            "source_id": "PAYROLL-base-202701-BST",
            "journal_id": "J1",
            "payroll_batch_id": "W1",
            "segment": "BST",
            "gross_employer_cost_usd": 101,
            "cash_payment_usd": 0,
        }
        contracts = [r for r in source["contracts"] if r["segment"] == "BST"][:2]
        invoices = [
            {
                "scenario": "base",
                "year": 2027,
                "month": 1,
                "source_id": "SALE-base-202701-" + c["contract_id"],
                "invoice_id": "I" + str(i),
                "journal_id": "J" + str(i + 2),
                "amount_usd": 100 + i,
            }
            for i, c in enumerate(contracts)
        ]
        tables = {"payroll_batches": [batch], "sales_invoices": invoices}
        cash = [
            {
                "scenario": "base",
                "source_id": batch["source_id"],
                "account": "1000",
                "signed_usd": -71,
            }
        ]
        detailed_service_and_payroll(tables, [op], cash)
        self.assertEqual(batch["cash_payment_usd"], 71)
        self.assertEqual(batch["unpaid_at_forecast_end_usd"], 30)
        self.assertEqual(sum(r["employer_cost_usd"] for r in tables["payroll_role_details"]), 101)
        self.assertEqual(
            sum(r["allocated_settlement_usd"] for r in tables["payroll_role_details"]), 71
        )
        self.assertEqual(
            sum(Decimal(r["allocated_realized_units"]) for r in tables["service_manifests"]), 701
        )
        self.assertEqual({r["invoice_id"] for r in tables["service_manifests"]}, {"I0", "I1"})
        cash[0]["signed_usd"] = -102
        with self.assertRaisesRegex(ValueError, "exceeds"):
            detailed_service_and_payroll(tables, [op], cash)


if __name__ == "__main__":
    unittest.main()
