"""Independent identities, boundary cases and live financial driver tests."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from industrial.planning import forecast as model
from industrial.planning.operating_model import calculate


class ForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.source = model.source_data()
        cls.operations = calculate()
        cls.original_hashes = {
            p: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [model.OLD_SOURCE, model.OLD_OPERATIONS]
        }
        cls.result = model.build(cls.root / "baseline", cls.operations, cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_all_periods_journals_and_balance_sheets(self):
        journals = defaultdict(int)
        for row in self.result["journal_rows"]:
            self.assertEqual(row["signed_usd"], row["debit_usd"] - row["credit_usd"])
            journals[row["journal_id"]] += row["signed_usd"]
        self.assertGreater(len(journals), 20000)
        self.assertEqual(set(journals.values()), {0})
        balances = defaultdict(int)
        for row in self.result["trial_balance_rows"]:
            balances[row["scenario"], row["entity"], row["year"], row["month"]] += row["signed_usd"]
        self.assertEqual(len(balances), 360)
        self.assertEqual(set(balances.values()), {0})
        for row in self.result["monthly_rows"]:
            self.assertEqual(
                row["assets_usd"],
                row["liabilities_usd"] + row["equity_including_current_income_usd"],
            )
            self.assertGreaterEqual(row["ending_cash_usd"], 0)

    def test_exact_accepted_opening_and_year_to_year_carry(self):
        opening = defaultdict(dict)
        closing = defaultdict(dict)
        for row in self.result["opening_rows"]:
            opening[row["scenario"], row["entity"], row["year"]][row["account"]] = row["signed_usd"]
        for row in self.result["trial_balance_rows"]:
            if row["month"] == 12:
                closing[row["scenario"], row["entity"], row["year"]][row["account"]] = row[
                    "signed_usd"
                ]
        for scenario in self.source["scenarios"]:
            for entity, anchor in self.source["anchor"]["opening_balances"].items():
                self.assertEqual(opening[scenario, entity, 2027], anchor)
                for year in range(2027, 2031):
                    previous = closing[scenario, entity, year]
                    income = -sum(
                        v
                        for a, v in previous.items()
                        if model.ACCOUNTS[a][1] in ["revenue", "expense"]
                    )
                    expected = {
                        a: v
                        for a, v in previous.items()
                        if model.ACCOUNTS[a][1] not in ["revenue", "expense"] and v
                    }
                    expected["3100"] = previous.get("3100", 0) - income
                    self.assertEqual(
                        {a: v for a, v in opening[scenario, entity, year + 1].items() if v},
                        expected,
                    )
        self.assertEqual(opening["base", "ARU_GROUP", 2027]["1000"], 4198440)
        self.assertEqual(opening["base", "RWH_PS", 2027]["2200"], -17281868)
        self.assertEqual(opening["base", "ARU_GROUP", 2027]["3100"], -3091227)

    def test_cash_rollforward_and_recorded_funding(self):
        equity = defaultdict(int)
        for row in self.result["journal_rows"]:
            if row["source_type"] == "PARENT_EQUITY":
                self.assertIn(row["account"], ["1000", "3000"])
                self.assertEqual(row["cash_flow"], "FINANCING")
                if row["account"] == "1000":
                    equity[row["scenario"], row["entity"], row["year"], row["month"]] += row[
                        "signed_usd"
                    ]
        for row in self.result["funding_rows"]:
            key = row["scenario"], row["entity"], row["year"], row["month"]
            self.assertEqual(equity[key], row["received_equity_usd"])
            self.assertEqual(
                row["required_equity_usd"] - row["available_equity_usd"], row["funding_gap_usd"]
            )
            self.assertGreaterEqual(row["remaining_annual_capacity_usd"], 0)
        for row in self.result["monthly_rows"]:
            self.assertEqual(
                row["ending_cash_usd"],
                row["opening_year_cash_usd"]
                + row["operating_cash_flow_ytd_usd"]
                + row["investing_cash_flow_ytd_usd"]
                + row["financing_cash_flow_ytd_usd"],
            )

    def test_mutated_economic_drivers_propagate(self):
        source = copy.deepcopy(self.source)
        source["adjustments"]["base"]["revenue_price_multiplier"] = 1.1
        source["adjustments"]["downside"]["cash_cost_multiplier"] = 1.05
        source["adjustments"]["expansion"]["payroll_multiplier"] = 1.05
        changed = model.build(self.root / "economic-change", self.operations, source)

        def total(result, scenario, account):
            return sum(
                r["signed_usd"]
                for r in result["journal_rows"]
                if r["scenario"] == scenario
                and r["entity"] == "ARU_GROUP"
                and r["year"] == 2027
                and r["account"] == account
            )

        self.assertLess(total(changed, "base", "4000"), total(self.result, "base", "4000"))
        self.assertGreater(
            total(changed, "downside", "5100"), total(self.result, "downside", "5100")
        )
        self.assertGreater(
            total(changed, "expansion", "5000"), total(self.result, "expansion", "5000")
        )

    def test_zero_equity_cannot_manufacture_cash_or_completed_capital(self):
        source = copy.deepcopy(self.source)
        for years in source["funding"]["annual_conditional_equity_limits_usd"].values():
            for entities in years.values():
                for entity in entities:
                    entities[entity] = 0
        changed = model.build(self.root / "no-parent-capital", self.operations, source)
        self.assertEqual(sum(r["received_equity_usd"] for r in changed["funding_rows"]), 0)
        self.assertGreater(max(r["funding_gap_usd"] for r in changed["funding_rows"]), 0)
        self.assertTrue(any(r["unpaid_due_obligations_usd"] > 0 for r in changed["monthly_rows"]))
        self.assertTrue(any(r["deferred_capex_usd"] > 0 for r in changed["monthly_rows"]))
        for row in changed["monthly_rows"]:
            self.assertGreaterEqual(
                row["ending_cash_usd"], source["funding"]["cash_floor_usd"][row["entity"]]
            )

    def test_debt_rollforwards_maturity_and_finite_refinancing(self):
        for row in self.result["datasets"]["debt"]:
            self.assertEqual(
                row["closing_legacy_term_usd"],
                row["opening_legacy_term_usd"] - row["principal_cash_paid_legacy_term_usd"],
            )
            self.assertEqual(
                row["closing_replacement_term_usd"],
                row["opening_replacement_term_usd"]
                + row["replacement_debt_draw_usd"]
                - row["principal_cash_paid_replacement_term_usd"],
            )
            self.assertEqual(
                row["closing_lease_usd"],
                row["opening_lease_usd"] - row["principal_cash_paid_lease_usd"],
            )
            if row["replacement_debt_draw_usd"]:
                self.assertEqual((row["year"], row["month"]), (2031, 1))
                self.assertLessEqual(
                    row["replacement_debt_draw_usd"], row["conditional_refinance_capacity_usd"]
                )
        base = next(
            r
            for r in self.result["datasets"]["debt"]
            if r["scenario"] == "base" and r["year"] == 2030 and r["month"] == 12
        )
        self.assertEqual(base["closing_legacy_term_usd"], 15375000)
        source = copy.deepcopy(self.source)
        source["debt"]["legacy_quarterly_principal_usd"] = 450000
        changed = model.build(self.root / "debt-change", self.operations, source)
        first = next(
            r
            for r in changed["datasets"]["debt"]
            if r["scenario"] == "base" and r["year"] == 2027 and r["month"] == 12
        )
        self.assertEqual(first["closing_legacy_term_usd"], 21375000 - 4 * 450000)

    def test_nol_tax_goodwill_and_cash_settlement(self):
        previous_nol = defaultdict(int)
        current_expense = defaultdict(int)
        tax_cash = defaultdict(int)
        for row in self.result["datasets"]["tax"]:
            key = row["scenario"], row["entity"], row["year"]
            current_expense[key] += row["current_tax_expense_usd"]
            tax_cash[key] += row["current_tax_cash_paid_usd"]
            self.assertEqual(row["new_nol_dta_recognized_usd"], 0)
            self.assertLessEqual(
                row["nol_utilized_ytd_usd"],
                model.money(Decimal(max(row["taxable_before_nol_ytd_usd"], 0)) * Decimal("0.8")),
            )
            if row["month"] == 12:
                self.assertEqual(current_expense[key], row["current_tax_expense_ytd_usd"])
                opening_settlement = next(
                    (
                        r["signed_usd"]
                        for r in self.result["opening_rows"]
                        if r["scenario"] == row["scenario"]
                        and r["entity"] == row["entity"]
                        and r["year"] == row["year"]
                        and r["account"] == "2700"
                    ),
                    0,
                )
                self.assertEqual(
                    row["current_tax_settlement_signed_usd"],
                    opening_settlement + tax_cash[key] - current_expense[key],
                )
                self.assertEqual(
                    row["opening_year_nol_usd"], previous_nol[row["scenario"], row["entity"]]
                )
                previous_nol[row["scenario"], row["entity"]] = row["modeled_closing_nol_usd"]
                if row["entity"] == "ARU_GROUP" and row["year"] == 2031:
                    self.assertEqual(row["remaining_tax_goodwill_basis_usd"], 7800000)
                    self.assertEqual(row["goodwill_dtl_usd"], 1300000)
                    self.assertEqual(
                        row["reserve_dta_usd"], 0 if row["scenario"] == "downside" else 587500
                    )
        self.assertGreater(previous_nol["downside", "RWH_PS"], 0)

    def test_intercompany_invoices_cash_and_month_end_balances(self):
        events = defaultdict(lambda: defaultdict(int))
        for row in self.result["journal_rows"]:
            if row["source_type"] in ["INTERCOMPANY_SERVICE", "INTERCOMPANY_PAYMENT"]:
                events[row["scenario"], row["source_id"], row["source_type"]][row["account"]] += (
                    row["signed_usd"]
                )
        for (_, _, kind), values in events.items():
            if kind == "INTERCOMPANY_SERVICE":
                self.assertEqual(-values["4100"], values["5150"])
                self.assertEqual(values["1150"], -values["2150"])
            else:
                self.assertEqual(values["1000"], 0)
                self.assertEqual(values["1150"], -values["2150"])
        snapshots = defaultdict(dict)
        for row in self.result["trial_balance_rows"]:
            if row["account"] in ["1150", "2150"]:
                snapshots[row["scenario"], row["year"], row["month"]][
                    row["entity"], row["account"]
                ] = row["signed_usd"]
        for balances in snapshots.values():
            self.assertEqual(
                balances.get(("ARU_GROUP", "1150"), 0), -balances.get(("RWH_PS", "2150"), 0)
            )
        receipts = [
            r
            for r in self.result["journal_rows"]
            if r["account"] == "1150" and r["source_type"] == "INTERCOMPANY_PAYMENT"
        ]
        self.assertEqual({r["segment"] for r in receipts}, {"BST", "TERMINALS", "TRUCKING"})

    def test_canceled_customer_gets_no_future_invoice(self):
        canceled = [
            r
            for r in self.result["datasets"]["contract_revenue"]
            if r["scenario"] == "downside"
            and r["customer_id"] == "ARU-C-001"
            and (r["year"], r["month"]) >= (2028, 6)
        ]
        self.assertTrue(canceled)
        self.assertEqual(sum(r["revenue_usd"] for r in canceled), 0)

    def test_inventory_and_idle_cost_controls(self):
        for row in self.result["datasets"]["inventory"]:
            self.assertEqual(
                row["production_cash_cost_usd"],
                row["capitalized_production_cash_usd"] + row["idle_production_expense_usd"],
            )
            self.assertGreaterEqual(row["ending_cash_inventory_usd"], 0)
            self.assertGreaterEqual(row["ending_dda_inventory_usd"], 0)
        total, stock, idle = model.production_costs(
            {"ore_tons": 0, "production_cash_cost_index": 1.03}, self.source["mine"]
        )
        self.assertGreater(total, 0)
        self.assertEqual(stock, 0)
        self.assertEqual(total, idle)
        base_cost = model.production_costs(
            {"ore_tons": 175000 / 12, "production_cash_cost_index": 1.03, "site_fte": 128},
            self.source["mine"],
        )[0]
        higher_staff_cost = model.production_costs(
            {"ore_tons": 175000 / 12, "production_cash_cost_index": 1.03, "site_fte": 140},
            self.source["mine"],
        )[0]
        self.assertGreater(higher_staff_cost, base_cost)
        for row in self.result["datasets"]["assets"]:
            self.assertEqual(
                row["opening_net_book_usd"] + row["additions_usd"] - row["depreciation_usd"],
                row["closing_net_book_usd"],
            )
            self.assertGreaterEqual(row["closing_net_book_usd"], 0)

    def test_growth_construction_funding_and_service_gates(self):
        totals = defaultdict(int)
        depreciation = defaultdict(int)
        for row in self.result["datasets"]["assets"]:
            key = row["scenario"], row["entity"], row["year"], row["month"]
            totals[*key, row["ledger_account"]] += row["gross_usd"]
            depreciation[key] += row["accumulated_depreciation_usd"]
            if row["project_id"]:
                index = (row["year"] - 2027) * 12 + row["month"]
                if row["asset_status"] == "CONSTRUCTION_IN_PROGRESS":
                    self.assertEqual(row["depreciation_usd"], 0)
                    self.assertEqual(row["accumulated_depreciation_usd"], 0)
                if index <= row["conditional_service_index"]:
                    self.assertEqual(row["depreciation_usd"], 0)
        for row in self.result["trial_balance_rows"]:
            key = row["scenario"], row["entity"], row["year"], row["month"]
            if row["account"] in {"1400", "1410"}:
                self.assertEqual(totals[*key, row["account"]], row["signed_usd"])
            if row["account"] == "1490":
                self.assertEqual(depreciation[key], -row["signed_usd"])
        # Isolate a partially funded project whose service date has passed:
        # paid CIP must survive, and a funding gap cannot authorize depreciation.
        book = model.Book("expansion", "ARU_GROUP", 2028, {"1000": 100, "3000": -100}, self.source)
        state = {
            "projects": {
                "TEST": {
                    "budget_usd": 100,
                    "paid_usd": 50,
                    "service_index": 19,
                    "actual_service_index": None,
                }
            },
            "cards": [{"project_id": "TEST", "first_index": None, "ledger_account": "1410"}],
        }
        model.activate_projects(book, state, 8, 20)
        self.assertIsNone(state["projects"]["TEST"]["actual_service_index"])
        self.assertEqual(book.balance["1400"], 0)
        state["projects"]["TEST"]["paid_usd"] = 100
        model.activate_projects(book, state, 8, 20)
        self.assertEqual(state["projects"]["TEST"]["actual_service_index"], 20)
        self.assertEqual(state["cards"][0]["first_index"], 20)
        self.assertEqual(book.balance["1400"], 100)

    def test_missing_period_or_changed_anchor_rejected(self):
        with self.assertRaisesRegex(ValueError, "every scenario-year-month"):
            model.prepare_rows(self.operations[:-1], self.source)
        changed = copy.deepcopy(self.source)
        changed["anchor"]["opening_balances"]["ARU_GROUP"]["1000"] += 1
        with self.assertRaisesRegex(ValueError, "opening balances"):
            model.source_data(changed)

    def test_future_metadata_preservation_and_repeatability(self):
        for row in self.result["journal_rows"]:
            self.assertEqual(row["period_role"], "CONDITIONAL_FORECAST")
            self.assertEqual(row["available_at"], "2026-09-06T00:00:00-07:00")
        for path, digest in self.original_hashes.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        repeated = model.build(self.root / "repeated", self.operations, self.source)
        first = json.loads((self.root / "baseline/manifest.json").read_text())
        second = json.loads((self.root / "repeated/manifest.json").read_text())
        self.assertEqual(first, second)
        self.assertEqual(self.result["summary"], repeated["summary"])


if __name__ == "__main__":
    unittest.main()
