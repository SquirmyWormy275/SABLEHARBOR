from decimal import Decimal as D
import unittest
from enterprise.runtime import model
from enterprise.runtime.construction_finance import (
    ProjectLedger,
    phase_reconciliation,
    asset_forecast,
)


class ConstructionFinanceTests(unittest.TestCase):
    def setUp(self):
        self.ledger = ProjectLedger(1000)
        self.index = 0

    def post(self, kind, amount, **kwargs):
        self.index += 1
        event = dict(
            id=str(self.index),
            type=kind,
            amount=amount,
            effective_on="2028-01-01",
            recorded_on="2028-01-02",
            authorized_by="SYNTHETIC_TEST_APPROVER",
            evidence_ref="SYNTHETIC_TEST_ONLY",
            origin="SYNTHETIC_ACCEPTED_TEST_EVENT",
            asset_class="CIP",
            life_years=10,
        )
        event.update(kwargs)
        self.ledger.apply(event)

    def test_deposit_accrual_retention_and_acceptance_are_distinct(self):
        self.post("AUTHORIZE", 1000)
        self.post("COMMIT", 1000)
        self.post("REFUNDABLE_DEPOSIT", 100)
        self.assertEqual(self.ledger.balances["cip"], 0)
        self.post("INVOICE", 1000)
        self.post("RETAIN", 50)
        self.post("APPLY_DEPOSIT", 100)
        self.post("PAY", 850)
        self.assertEqual(self.ledger.balances["retention"], 50)
        self.assertEqual(self.ledger.depreciation_at("2030-12-31"), 0)
        self.post("IN_SERVICE", 1000)
        self.assertEqual(self.ledger.depreciation_at("2028-01-31"), 0)
        self.assertEqual(self.ledger.depreciation_at("2028-02-29"), D("8.33"))
        self.post("RELEASE_RETENTION", 50)
        self.post("PAY", 50)
        self.assertEqual(self.ledger.balances["cash"], 0)
        self.assertEqual(self.ledger.balances["payable"], 0)

    def test_unapproved_unfunded_and_duplicate_events_fail(self):
        with self.assertRaises(ValueError):
            self.post("INVOICE", 1)
        self.post("AUTHORIZE", 2000)
        self.post("COMMIT", 2000)
        with self.assertRaises(ValueError):
            self.post("REFUNDABLE_DEPOSIT", 2000)
        with self.assertRaises(ValueError):
            self.post("INVOICE", 100, origin="FORECAST")
        with self.assertRaises(ValueError):
            self.ledger.apply(self.ledger.events[0])

    def test_cancel_does_not_erase_delivered_work(self):
        self.post("AUTHORIZE", 1000)
        self.post("COMMIT", 1000)
        self.post("REFUNDABLE_DEPOSIT", 100)
        self.post("INVOICE", 200)
        with self.assertRaises(ValueError):
            self.post("CANCEL_UNDELIVERED", 900)
        self.post("CANCEL_UNDELIVERED", 800)
        self.post("REFUND_DEPOSIT", 100)
        self.assertEqual(self.ledger.invoiced, 200)
        self.assertEqual(self.ledger.balances["payable"], 200)

    def test_land_not_depreciable(self):
        self.post("AUTHORIZE", 1000)
        self.post("COMMIT", 1000)
        self.post("INVOICE", 1000)
        with self.assertRaises(ValueError):
            self.post("IN_SERVICE", 1000, asset_class="LAND")

    def test_boolean_and_fractional_useful_lives_are_rejected(self):
        self.post("AUTHORIZE", 1000)
        self.post("COMMIT", 1000)
        self.post("INVOICE", 1000)
        for life in (True, False, 1.5, "15"):
            with self.subTest(life=life), self.assertRaises(ValueError):
                self.post("IN_SERVICE", 1000, life_years=life)
        self.assertEqual(self.ledger.balances["cip"], 1000)
        self.assertIsNone(self.ledger.in_service)

    def test_budget_scope_and_asset_forecast(self):
        data = model.load()
        rows = phase_reconciliation(data)
        for row in rows:
            self.assertEqual(
                D(row["land_non_cash_overlay"])
                + D(row["pre_2027_unaccepted_unrecognized_requests"])
                + D(row["conditional_post_2026_cip_requests"])
                + D(row["unspent_reserve"]),
                D(15500000),
            )
        assets = asset_forecast(data)
        self.assertTrue(
            all(
                D(r["cumulative_depreciation"]) == 0 for r in assets if r["year"] < 2029
            )
        )
        self.assertTrue(all(not r["actual_in_service"] for r in assets))
        completed = [r for r in assets if r["scenario"] == "base" and r["year"] == 2029]
        self.assertEqual(
            sum(D(r["conditional_completed_cost"]) for r in completed), D(11800000)
        )
