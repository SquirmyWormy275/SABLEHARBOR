"""Independent DCF arithmetic, excluded transfers and ambiguity tests."""

import copy
import unittest
from unittest.mock import patch

from industrial.planning import capital
from industrial.planning import operating_model as operating


class CapitalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = operating.load_capital()
        cls.result = capital.evaluate()

    def test_npv_and_conventional_irr_have_independent_solution(self):
        self.assertAlmostEqual(capital.npv(0.10, [-100, 110]), 0)
        result = capital.irr([-100, 110])
        self.assertEqual(result["status"], "UNIQUE_CONVENTIONAL_IRR")
        self.assertAlmostEqual(result["period_rate"], 0.1)
        self.assertAlmostEqual(result["annualized_rate"], 1.1**12 - 1)
        with self.assertRaises(ValueError):
            capital.npv(-1, [-100, 110])

    def test_multiple_roots_are_not_arbitrarily_selected(self):
        result = capital.irr([-100, 230, -132])
        self.assertEqual(result["status"], "AMBIGUOUS_NONCONVENTIONAL_CASH_FLOW")
        self.assertIsNone(result["period_rate"])
        self.assertAlmostEqual(capital.npv(0.1, [-100, 230, -132]), 0)
        self.assertAlmostEqual(capital.npv(0.2, [-100, 230, -132]), 0)
        self.assertEqual(capital.irr([0, 0, 0])["status"], "NO_IRR_NO_SIGN_CHANGE")

    def test_monthly_cashflow_reconciles_independently_to_npv(self):
        for option in self.result["options"].values():
            flows = option["monthly_cashflows"]
            independent = sum(
                r["incremental_unlevered_cashflow_usd"] / 1.1 ** ((i + 1) / 12)
                for i, r in enumerate(flows)
            )
            self.assertAlmostEqual(independent, option["npv_usd"], places=5)
            for r in flows:
                cash = (
                    r["incremental_cash_operating_margin_usd"]
                    - r["incremental_cash_tax_usd"]
                    - r["incremental_growth_capex_usd"]
                    - r["incremental_replacement_capex_usd"]
                    - r["incremental_nwc_change_usd"]
                    + r["terminal_residual_gross_usd"]
                    + r["terminal_nwc_recovery_usd"]
                )
                self.assertAlmostEqual(cash, r["incremental_unlevered_cashflow_usd"])
                self.assertGreaterEqual(r["ending_project_tax_loss_usd"], 0)
                self.assertGreaterEqual(r["incremental_cash_tax_usd"], 0)

    def test_tax_loss_ceiling_and_following_month_depreciation(self):
        tax, remaining = capital.annual_project_tax(100, 200, self.source)
        self.assertAlmostEqual(tax, 5)
        self.assertAlmostEqual(remaining, 120)
        tax, remaining = capital.annual_project_tax(-40, remaining, self.source)
        self.assertEqual(tax, 0)
        self.assertEqual(remaining, 160)
        rows = self.result["options"]["owned"]["monthly_cashflows"]
        july = next(r for r in rows if (r["year"], r["month"]) == (2028, 7))
        august = next(r for r in rows if (r["year"], r["month"]) == (2028, 8))
        self.assertEqual(july["incremental_tax_depreciation_usd"], 0)
        self.assertAlmostEqual(
            august["incremental_tax_depreciation_usd"],
            (8600000 + july["incremental_replacement_capex_usd"]) / 180,
        )

    def test_contract_renewals_and_cancellations_flow_to_project_revenue(self):
        row = {
            "scenario": "expansion",
            "month": 1,
            "lost_customer_ids": [],
            "segments": {"BST": {"revenue_volume_factor": 1}},
            "assumptions": {"external_price_index": 1},
        }
        contracts = [
            {"month": 1, "segment": "BST", "customer_id": "A", "revenue_usd": 100},
            {"month": 1, "segment": "BST", "customer_id": "B", "revenue_usd": 200},
        ]
        source = {"adjustments": {"expansion": {"contract_renewal_price_multipliers": {"B": 1.03}}}}
        self.assertEqual(capital.contract_revenue(row, contracts, source), 306)
        row["lost_customer_ids"] = ["B"]
        row["segments"]["BST"]["revenue_volume_factor"] = 1 / 3
        self.assertEqual(capital.contract_revenue(row, contracts, source), 100)

    def test_sunk_capital_and_common_mine_capex_do_not_drive_incremental_npv(self):
        changed = copy.deepcopy(self.source)
        changed["retrospective"]["completed_interface_capex_usd"] = 999999999
        for project in changed["growth_projects"]:
            if project["owner"] == "RWH":
                project["growth_cost_usd"] = 16000000
        result = capital.evaluate(changed)
        for name in ("outsource", "owned"):
            self.assertAlmostEqual(
                result["options"][name]["npv_usd"], self.result["options"][name]["npv_usd"]
            )
            self.assertEqual(result["options"][name]["sunk_2026_interface_cost_included_usd"], 0)
            self.assertAlmostEqual(
                result["options"][name]["common_conditional_mine_growth_usd"], 16000000
            )

    def test_intercompany_markup_changes_no_consolidated_cash_margin(self):
        rows = [r for r in operating.calculate() if r["scenario"] == "base"][:2]
        before = capital._economic_rows(rows)
        changed = copy.deepcopy(operating.legacy_operations())
        for rate in changed["interface"]["rates"]:
            rate["rail_rate"] *= 100
            rate["terminal_rate"] *= 100
            rate["dray_rate"] *= 100
        with patch.object(operating, "legacy_operations", return_value=changed):
            after = capital._economic_rows(rows)
        for a, b in zip(before, after, strict=True):
            self.assertAlmostEqual(a["operating_cash_margin_usd"], b["operating_cash_margin_usd"])
            self.assertGreater(
                b["intercompany_revenue_excluded_usd"], a["intercompany_revenue_excluded_usd"]
            )

    def test_residual_value_is_explicit_and_material(self):
        none = copy.deepcopy(self.source)
        none["terminal_disposal"] = False
        result = capital.evaluate(none)
        self.assertLess(
            result["options"]["owned"]["npv_usd"], self.result["options"]["owned"]["npv_usd"]
        )
        for r in result["options"]["owned"]["monthly_cashflows"]:
            self.assertEqual(r["terminal_residual_gross_usd"], 0)
            self.assertEqual(r["terminal_nwc_recovery_usd"], 0)
        actual = self.result["options"]["owned"]["monthly_cashflows"][-1]
        self.assertAlmostEqual(actual["terminal_residual_gross_usd"], 9400000 * 0.45)

    def test_options_face_same_demand_and_different_constraints(self):
        final = self.result["physical_2031"]
        for segment in operating.SEGMENTS:
            self.assertGreaterEqual(final["owned"][segment], final["current"][segment])
            self.assertGreaterEqual(final["outsource"][segment], final["current"][segment])
        self.assertAlmostEqual(self.result["options"]["current"]["npv_usd"], 0)
        self.assertAlmostEqual(
            self.result["options"]["owned"]["incremental_growth_capex_usd"], 9400000
        )


if __name__ == "__main__":
    unittest.main()
