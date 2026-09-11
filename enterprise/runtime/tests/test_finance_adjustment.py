from decimal import Decimal as D
import json
import unittest
from enterprise.runtime.finance import RuntimeAdjustment, verify_land_adjustment
from enterprise.runtime.build_finance import replacement_bridge
from industrial.planning import enterprise


class FinanceAdjustmentTests(unittest.TestCase):
    def setUp(self):
        self.adjustment = RuntimeAdjustment()
        self.policy = json.loads(enterprise.SOURCE.read_text())
        self.policy["core"]["payment_deferral_accounts"] = {
            "OPERATING": "CORE_UNPAID",
            "INVESTING": "BIZ_CAPITAL_UNPAID",
            "FINANCING": "BIZ_DEBT_UNPAID",
        }
        self.policy["core"]["additional_deferrable_source_types"] = [
            "RUNTIME_CONDITIONAL_FORECAST_REQUEST"
        ]
        types = self.adjustment.account_types | {
            "1000": "asset",
            "3000": "equity",
            "CORE_UNPAID": "liability",
            "BIZ_CAPITAL_UNPAID": "liability",
            "BIZ_DEBT_UNPAID": "liability",
        }
        self.books = enterprise.Books("base", self.policy, types)

    def test_dated_land_once_and_no_cash(self):
        for month in range(1, 13):
            self.adjustment.post_month(self.books, 2026, month)
        result = verify_land_adjustment(self.books.rows)
        self.assertEqual(result["cash_paid"], "0.0000")
        self.assertEqual(self.books.balances["SHI"]["RT_LAND"], D(3000000))
        self.assertEqual(self.books.balances["SHI"].get("1000", 0), 0)
        with self.assertRaises(ValueError):
            verify_land_adjustment(self.books.rows * 2)

    def test_no_land_or_cip_depreciation(self):
        for month in (1, 2):
            self.adjustment.post_month(self.books, 2027, month)
        dda = [r for r in self.books.rows if r["account"] == "RT_DDA"]
        self.assertTrue(dda)
        self.assertEqual({r["month"] for r in dda}, {2})
        self.assertFalse(any("LAND" in r["source_id"] for r in dda))

    def test_finite_treasury_defers_runtime_capital(self):
        self.policy["scenarios"]["base"]["member_equity_annual_limit_usd"] = "0"
        self.policy["core"]["minimum_cash_usd"] = "0"
        self.adjustment.post_month(self.books, 2027, 1)
        rows = []
        enterprise.member_funding(
            self.books, 2027, 1, D(0), {"core": D(0), "subsidiary": D(0)}, D(0), rows
        )
        self.assertEqual(self.books.balances["SHI"]["1000"], 0)
        self.assertGreater(-self.books.balances["SHI"]["BIZ_CAPITAL_UNPAID"], 0)
        self.assertEqual(rows[0]["feasibility"], "FUNDING_GAP")
        self.assertEqual(self.books.balances["SHI"].get("3000", 0), 0)

    def test_unknown_deferral_source_fails(self):
        self.policy["core"]["additional_deferrable_source_types"] = ["ANYTHING"]
        with self.assertRaises(ValueError):
            enterprise.member_funding(
                self.books, 2027, 1, D(0), {"core": D(0), "subsidiary": D(0)}, D(0), []
            )

    def test_exact_land_successor_bridge(self):
        self.adjustment.post_month(self.books, 2026, 9)
        bridge = replacement_bridge(
            {"journal_rows": []}, {"journal_rows": self.books.rows}
        )
        self.assertEqual(sum(D(r["signed_usd"]) for r in bridge), 0)
        self.assertEqual({r["action"] for r in bridge}, {"ADD_RUNTIME_LAND_OVERLAY"})
