"""Financial-case controls exercise drivers, journal identities and disclosure boundaries."""

from __future__ import annotations

import copy
import csv
import importlib.util
import json
import tempfile
import unittest
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "build_financials.py"
SPEC = importlib.util.spec_from_file_location("industrial_financials", MODULE_PATH)
assert SPEC and SPEC.loader
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)


class FinancialCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name) / "first"
        cls.report = MODEL.build(cls.output)
        cls.source, cls.ops, cls.core = MODEL.read_sources()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def rows(self, name):
        with (self.output / name).open(newline="") as stream:
            return list(csv.DictReader(stream))

    def test_journals_and_three_statements_balance_independently(self):
        for name in ["aru_2025_journal.csv", "aru_2026_journal.csv", "red_wash_2026_journal.csv"]:
            journals = defaultdict(int)
            for row in self.rows(name):
                self.assertEqual(
                    int(row["signed_usd"]), int(row["debit_usd"]) - int(row["credit_usd"])
                )
                journals[row["journal_id"]] += int(row["signed_usd"])
            self.assertGreater(len(journals), 100)
            self.assertEqual(set(journals.values()), {0})
        for key in ["aru_2025", "aru_2026_postclose", "mine_integrated_2026"]:
            statement = self.report[key]
            self.assertEqual(
                statement["assets_usd"],
                statement["liabilities_usd"] + statement["equity_including_current_income_usd"],
            )
            self.assertEqual(
                statement["ending_cash_usd"],
                statement["opening_cash_usd"] + sum(statement["cash_flow"].values()),
            )

    def test_contract_price_change_propagates_without_revenue_plug(self):
        changed = copy.deepcopy(self.source)
        changed["contracts"][0]["annual_units"] += 1
        customers, contracts, monthly = MODEL.customer_schedules(changed)
        expected_delta = changed["contracts"][0]["unit_price_usd"]
        self.assertEqual(sum(r["annual_revenue_usd"] for r in customers), 42000000 + expected_delta)
        self.assertEqual(sum(r["revenue_usd"] for r in monthly), 42000000 + expected_delta)
        self.assertEqual(sum(r["annual_units"] for r in contracts if r["segment"] == "BST"), 9001)

    def test_customer_and_payroll_sources_support_selected_scale(self):
        values = sorted(
            (int(r["annual_revenue_usd"]) for r in self.rows("customer_register.csv")), reverse=True
        )
        self.assertEqual(len(values), 25)
        self.assertEqual(sum(values), 42000000)
        self.assertEqual(values[0], 4620000)
        self.assertEqual(sum(values[:5]), 16800000)
        employees = self.rows("employee_census_payroll.csv")
        self.assertEqual(len(employees), 131)
        self.assertEqual(sum(r["segment"] == "BST" for r in employees), 58)
        for row in employees:
            self.assertEqual(
                int(row["annual_loaded_payroll_usd"]),
                int(row["annual_salary_usd"]) + int(row["annual_employer_burden_usd"]),
            )

    def test_interface_invoices_use_physical_cars_and_reconcile_counterparties(self):
        expected_revenue = 0
        rates = {r["commodity"]: r for r in self.ops["interface"]["rates"]}
        self.assertEqual(sum(r["normalized_billable_cars"] for r in rates.values()), 215)
        self.assertEqual(self.ops["interface"]["contingent_unbilled_cars"], 10)
        for month in self.ops["interface"]["monthly_2026"]:
            for commodity, cars in month["carloads"].items():
                rate = rates[commodity]
                expected_revenue += cars * (
                    rate["rail_rate"]
                    + rate["terminal_rate"]
                    + rate["truck_legs_per_car"] * rate["dray_rate"]
                )
        self.assertEqual(expected_revenue, 171380)
        self.assertEqual(
            sum(int(r["revenue_usd"]) for r in self.rows("intercompany_invoices_2026.csv")),
            expected_revenue,
        )
        aru = {r["account"]: int(r["signed_usd"]) for r in self.rows("aru_2026_trial_balance.csv")}
        mine = {
            r["account"]: int(r["signed_usd"]) for r in self.rows("red_wash_2026_trial_balance.csv")
        }
        self.assertEqual(-aru["4100"], mine["5150"])
        self.assertEqual(aru["1150"], -mine["2150"])
        self.assertGreater(aru["1150"], 0)

    def test_purchase_accounting_identifies_temporary_differences(self):
        ppa = self.report["acquisition"]
        self.assertEqual(ppa["deferred_tax_asset_usd"], round((1750000 + 600000) * 0.25))
        self.assertEqual(
            ppa["identifiable_net_assets_before_refinancing_usd"] + ppa["goodwill_usd"], 48000000
        )
        self.assertEqual(ppa["close_sources_before_fees_usd"], ppa["close_uses_before_fees_usd"])
        self.assertEqual(ppa["parent_cash_including_fees_usd"], 39000000 + 900000 + 300000)

    def test_tax_goodwill_current_deferred_and_cash_reconcile(self):
        rows = self.rows("aru_2026_tax_rollforward.csv")
        last = rows[-1]
        goodwill = self.report["acquisition"]["goodwill_usd"]
        tax_goodwill = self.report["acquisition"]["tax_goodwill_basis_usd"]
        allocation = self.report["acquisition"]["tax_allocation"]
        self.assertEqual(allocation["modeled_agub_usd"], 48000000 + 20000000)
        self.assertEqual(
            tax_goodwill,
            allocation["modeled_agub_usd"] - sum(allocation["other_tax_asset_bases_usd"].values()),
        )
        self.assertEqual(tax_goodwill, 13000000)
        self.assertEqual(
            self.report["acquisition"]["initial_book_goodwill_excess_over_tax_usd"], 1762500
        )
        deduction = MODEL.usd(Decimal(tax_goodwill) * 12 / 180)
        self.assertEqual(int(last["cumulative_goodwill_tax_deduction_usd"]), deduction)
        self.assertEqual(
            int(last["deferred_tax_liability_goodwill_usd"]), MODEL.usd(Decimal(deduction) / 4)
        )
        self.assertEqual(int(last["goodwill_book_basis_usd"]), goodwill)
        self.assertEqual(int(last["goodwill_tax_basis_usd"]), tax_goodwill - deduction)
        pretax = sum(int(r["book_pretax_income_usd"]) for r in rows)
        current = sum(int(r["current_tax_expense_usd"]) for r in rows)
        deferred = sum(int(r["deferred_tax_expense_usd"]) for r in rows)
        cash = sum(int(r["current_tax_cash_paid_usd"]) for r in rows)
        self.assertLessEqual(abs(current + deferred - MODEL.usd(Decimal(pretax) / 4)), 1)
        self.assertEqual(current, MODEL.usd(Decimal(pretax - deduction) / 4))
        self.assertEqual(cash - current, int(last["current_tax_settlement_signed_balance_usd"]))
        self.assertEqual(int(last["deferred_tax_asset_interim_loss_usd"]), 0)
        self.assertGreater(int(rows[0]["deferred_tax_asset_interim_loss_usd"]), 0)
        for row in rows:
            if int(row["month"]) not in [3, 6, 9, 12]:
                self.assertEqual(int(row["current_tax_cash_paid_usd"]), 0)

    def run_forecast(self, source):
        _, _, monthly = MODEL.customer_schedules(source)
        _, payroll = MODEL.payroll_schedules(source)
        history, _ = MODEL.build_2025(source, monthly, payroll)
        _, invoices = MODEL.interface_schedules(self.ops)
        ppa = MODEL.acquisition(source, history)
        return MODEL.build_2026(source, self.ops, history, monthly, payroll, invoices, ppa)

    def test_declared_economic_drivers_change_forecast_balances(self):
        base = self.run_forecast(self.source)[0]
        cases = [
            ("forecast_2026", "external_price_increase_pct", 3, "4000", -1),
            ("forecast_2026", "external_volume_growth_pct", 1, "4000", -1),
            ("forecast_2026", "external_cash_opex_inflation_pct", 4, "5000", 1),
            ("forecast_2026", "lease_interest_pct", 6, "5400", 1),
            ("transaction", "new_debt_rate_pct", 7, "5400", 1),
            ("transaction", "new_debt_quarterly_principal", 500000, "2400", 1),
            ("transaction", "new_revolver_undrawn_commitment_fee_pct", 0.5, "5400", 1),
            ("transaction", "debt_issuance_amortization_months", 72, "5400", -1),
        ]
        for section, key, value, account, direction in cases:
            with self.subTest(driver=key):
                changed = copy.deepcopy(self.source)
                changed[section][key] = value
                result = self.run_forecast(changed)[0]
                self.assertGreater(
                    (result.balances[account] - base.balances[account]) * direction, 0
                )
                self.assertEqual(result.summary()["balance_sheet_difference_usd"], 0)
        nwc = {
            "receivables_increase": "1100",
            "inventory_increase": "1200",
            "prepaids_increase": "1300",
            "payables_increase": "2000",
            "operating_accrual_increase": "2100",
        }
        for key, account in nwc.items():
            with self.subTest(driver=key):
                changed = copy.deepcopy(self.source)
                delta = changed["forecast_2026"]["nwc_forecast_drivers"][key]
                changed["forecast_2026"]["nwc_forecast_drivers"][key] *= 2
                result = self.run_forecast(changed)[0]
                self.assertEqual(abs(result.balances[account] - base.balances[account]), delta)
        changed = copy.deepcopy(self.source)
        changed["transaction"]["new_debt_first_payment"] = "2026-05-07"
        debt_rows = self.run_forecast(changed)[6]
        self.assertEqual([r["month"] for r in debt_rows if r["term_principal_usd"]], [5, 8, 11])

    def test_supporting_net_working_capital_and_earnings_bridges(self):
        rail = self.rows("rail_opex_class_bridge.csv")
        self.assertEqual(sum(int(r["reported_opex_usd"]) for r in rail), 14000000)
        for row in rail:
            self.assertEqual(
                int(row["reported_opex_usd"]),
                sum(
                    int(row[k])
                    for k in [
                        "census_payroll_usd",
                        "shared_service_allocation_usd",
                        "external_nonpayroll_budget_usd",
                    ]
                ),
            )
        for row in self.rows("receivables_aging_and_allowance.csv"):
            gross = int(row["gross_external_receivables_usd"])
            self.assertEqual(
                gross - int(row["specific_allowance_usd"]), int(row["net_external_receivables_usd"])
            )
            self.assertEqual(
                gross,
                sum(
                    int(row[k])
                    for k in [
                        "current_0_30_days_usd",
                        "days_31_60_usd",
                        "days_61_90_usd",
                        "days_over_90_usd",
                    ]
                ),
            )
        inventory = defaultdict(int)
        for row in self.rows("parts_fuel_materials_inventory.csv"):
            inventory[row["period_id"]] += int(row["net_inventory_usd"])
            self.assertEqual(
                MODEL.usd(Decimal(row["modeled_quantity"]) * Decimal(row["average_unit_cost_usd"])),
                int(row["net_inventory_usd"]),
            )
        self.assertEqual(
            dict(inventory),
            {"2025_OPENING": 1600000, "2025_CLOSING": 1800000, "2026_CLOSING": 1854000},
        )
        for row in self.rows("reported_to_normalized_ebitda.csv"):
            self.assertEqual(
                int(row["reported_case_ebitda_usd"]),
                sum(
                    int(row[k])
                    for k in [
                        "net_income_usd",
                        "income_tax_usd",
                        "interest_usd",
                        "depreciation_usd",
                    ]
                ),
            )
            self.assertEqual(row["reported_case_ebitda_usd"], row["normalized_case_ebitda_usd"])

    def test_aro_carryforward_is_non_cash_and_settlement_is_not_capex(self):
        bridge = self.report["mine_bridge"]["integrated_aro"]
        expected = int(
            (Decimal(16000000) * (Decimal("1.065") ** (Decimal(167) / 365) - 1)).quantize(
                Decimal(1), rounding=ROUND_HALF_UP
            )
        )
        self.assertEqual(bridge["h2_2025_accretion_usd"], expected)
        self.assertEqual(bridge["opening_2026_aro_usd"], 16000000 + expected)
        self.assertEqual(
            self.report["mine_bridge"]["selected_baseline"]["free_cash_flow_usd"], -7477521
        )
        rows = self.rows("red_wash_closure_cashflow_calibration.csv")
        self.assertEqual(sum(int(r["current_cost_usd"]) for r in rows), 25000000)
        self.assertLessEqual(
            abs(sum(int(r["present_value_usd"]) for r in rows) - bridge["opening_2026_aro_usd"]), 3
        )
        settlement = [
            r for r in self.rows("red_wash_2026_journal.csv") if r["source_id"] == "RW-CLOSURE-CASH"
        ]
        self.assertTrue(settlement)
        self.assertEqual({r["cash_flow"] for r in settlement}, {"OPERATING"})

    def test_separate_legal_books_balance_and_treasury_eliminates(self):
        totals = defaultdict(int)
        for row in self.rows("separate_legal_entity_trial_balances.csv"):
            totals[(row["entity"], row["year"])] += int(row["signed_usd"])
        self.assertEqual(len(totals), 6)
        self.assertEqual(set(totals.values()), {0})
        for row in self.rows("ownership_and_treasury_eliminations.csv"):
            self.assertEqual(int(row["post_elimination_difference_usd"]), 0)
            if row.get("bst_treasury_current_account_signed_usd"):
                self.assertEqual(
                    int(row["bst_treasury_current_account_signed_usd"])
                    + int(row["aru_reciprocal_treasury_account_signed_usd"]),
                    0,
                )
        retention = sum(
            int(r["signed_usd"])
            for r in self.rows("aru_2026_journal.csv")
            if r["account"] == "5700" and r["source_id"] == "RETENTION-POOL"
        )
        consulting = sum(
            int(r["signed_usd"])
            for r in self.rows("aru_2026_journal.csv")
            if r["account"] == "5700" and r["source_id"] == "TOLMAN-CONSULTING"
        )
        self.assertEqual(retention, MODEL.usd(Decimal(500000) * 359 / 365))
        self.assertEqual(consulting, 225000)
        bst_retention = next(
            int(r["signed_usd"])
            for r in self.rows("separate_legal_entity_trial_balances.csv")
            if r["entity"] == "BST" and r["year"] == "2026" and r["account"] == "5700"
        )
        self.assertEqual(bst_retention, MODEL.usd(Decimal(retention) * 80000 / 500000))

    def test_equity_funding_never_enters_revenue_and_cash_flows_are_financing(self):
        for name in ["aru_2026_journal.csv", "red_wash_2026_journal.csv"]:
            rows = self.rows(name)
            ids = {r["journal_id"] for r in rows if r["account"] == "3000" and int(r["month"]) > 0}
            self.assertTrue(ids)
            for row in rows:
                if row["journal_id"] in ids:
                    self.assertIn(row["account"], {"1000", "3000"})
                    self.assertEqual(row["cash_flow"], "FINANCING")

    def test_legal_ownership_driver_changes_allocated_books_and_clearing(self):
        _, _, monthly = MODEL.customer_schedules(self.source)
        _, payroll = MODEL.payroll_schedules(self.source)
        history, _ = MODEL.build_2025(self.source, monthly, payroll)
        _, invoices = MODEL.interface_schedules(self.ops)
        aru = self.run_forecast(self.source)[0]
        mine, _, funding, _, _ = MODEL.build_mine(self.source, self.core, invoices, self.ops)
        changed = copy.deepcopy(self.source)
        changed["legal_book_policy"]["bst_balance_allocation_pct"]["cash"] = 40
        changed["legal_book_policy"]["central_financing_cost_to_bst_pct"] = 10
        _, rows, eliminations = MODEL.legal_book_views(
            changed, history, aru, mine, funding, invoices
        )
        bst = {
            r["account"]: r["signed_usd"]
            for r in rows
            if r["entity"] == "BST" and r["year"] == 2026
        }
        self.assertEqual(bst["1000"], MODEL.usd(Decimal(aru.balances["1000"]) * Decimal("0.4")))
        self.assertEqual(bst["5400"], MODEL.usd(Decimal(aru.balances["5400"]) * Decimal("0.1")))
        self.assertTrue(all(r["post_elimination_difference_usd"] == 0 for r in eliminations))

    def test_no_full_september_or_future_month_calibration(self):
        for name in [
            "aru_2026_journal.csv",
            "red_wash_2026_journal.csv",
            "aru_2026_monthly_statements.csv",
            "aru_2026_fixed_assets.csv",
            "aru_2026_debt_leases.csv",
        ]:
            for row in self.rows(name):
                month = int(row.get("month") or row.get("through_month") or 0)
                self.assertEqual(row["available_at"], "2026-09-05")
                if month >= 9:
                    self.assertEqual(row["period_role"], "MANAGEMENT_FORECAST")
                if row["period_role"] == "SYNTHETIC_CALIBRATION":
                    self.assertLessEqual(row["effective_period_end"], "2026-09-05")
                if month == 0 and "journal" in name:
                    self.assertEqual(
                        row["effective_period_end"],
                        "2026-01-01" if "red_wash" in name else "2026-01-07",
                    )
        for row in self.rows("aru_acquisition_opening_trial_balance.csv"):
            self.assertEqual(row["effective_period_end"], "2026-01-07")

    def test_repeat_build_identical_manifest_and_bytes(self):
        second = Path(self.temp.name) / "second"
        MODEL.build(second)
        self.assertEqual(
            (self.output / "manifest.json").read_bytes(), (second / "manifest.json").read_bytes()
        )
        manifest = json.loads((self.output / "manifest.json").read_text())
        for row in manifest["artifacts"]:
            self.assertEqual(
                (self.output / row["path"]).read_bytes(), (second / row["path"]).read_bytes()
            )


if __name__ == "__main__":
    unittest.main()
