"""Adversarial constraints and real scenario effects, not output snapshots."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from industrial.planning import operating_model as model


class OperatingModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = model.load_source()
        cls.rows = model.calculate()
        cls.by_key = {(r["scenario"], r["year"], r["month"]): r for r in cls.rows}

    def changed_rows(self, change):
        source = copy.deepcopy(self.source)
        change(source)
        return {(r["scenario"], r["year"], r["month"]): r for r in model.calculate(source)}

    def test_all_months_and_no_authority_grants(self):
        self.assertEqual(len(self.rows), 180)
        self.assertEqual(len(self.by_key), 180)
        self.assertTrue(model.validate(self.rows)["passed"])
        for row in self.rows:
            self.assertFalse(row["authority_granted"])
            self.assertEqual(row["available_at"], "2026-09-06T00:00:00-07:00")
            self.assertEqual(row["mine"]["direct_uranium_custody"], "OPEN_GATED")

    def test_validation_rejects_invalid_physics_without_asserts(self):
        rows = copy.deepcopy(self.rows[:1])
        rows[0]["capacity"]["truck_total_owned_required_hours"] = 1e12
        with self.assertRaisesRegex(ValueError, "driver or tractor hours"):
            model.validate(rows)
        with self.assertRaisesRegex(ValueError, "Duplicate scenario-month"):
            model.validate(self.rows[:1] * 2)

    def test_artifact_hashes_are_deterministic_and_capture_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            model.build(output)
            before = (output / "manifest.json").read_bytes()
            (output / "stale-unrelated.txt").write_text("not generated")
            model.build(output)
            self.assertEqual(before, (output / "manifest.json").read_bytes())
            original = json.loads(before)
            self.assertEqual(len(original["dependency_sha256"]), 4)
            changed = copy.deepcopy(self.source)
            changed["mine"]["uranium_price_2026_usd_lb"] = 60
            model.build(output, changed)
            after = json.loads((output / "manifest.json").read_text())
            self.assertEqual(original["dependency_sha256"], after["dependency_sha256"])
            self.assertNotEqual(original["effective_input_sha256"], after["effective_input_sha256"])
            self.assertNotEqual(original["artifacts"], after["artifacts"])

    def test_integer_allocation_keeps_annual_demand_exact(self):
        for total in [0, 1, 11, 9180, 14500, 589950]:
            values = model.monthly_allocation(total, self.source["monthly_weights"])
            self.assertEqual(sum(values), total)
            self.assertTrue(all(isinstance(x, int) and x >= 0 for x in values))
        self.assertEqual(
            sum(
                r["segments"]["BST"]["demand_units"]
                for r in self.rows
                if r["scenario"] == "base" and r["year"] == 2027
            ),
            9180,
        )

    def test_traction_and_duration_actually_change_capacity(self):
        rail = self.source["rail"]
        self.assertEqual(model.train_limit(109400, 260, rail), 16)
        self.assertLess(
            model.rail_capacity(self.source, 20, False, 2, False)["capacity_cars"],
            model.rail_capacity(self.source, 20, False, 1, False)["capacity_cars"],
        )

        def shorten(source):
            next(e for e in source["events"] if e["type"] == "locomotive_failure")[
                "downtime_service_days"
            ] = 3

        changed = self.changed_rows(shorten)[("downside", 2027, 3)]
        original = self.by_key["downside", 2027, 3]
        self.assertGreater(
            changed["capacity"]["rail"]["capacity_cars"],
            original["capacity"]["rail"]["capacity_cars"],
        )
        self.assertGreater(
            changed["segments"]["BST"]["served_units"], original["segments"]["BST"]["served_units"]
        )

    def test_winter_reduces_throughput_and_increases_cost(self):
        changed = self.changed_rows(
            lambda s: s.update(events=[e for e in s["events"] if e["type"] != "winter"])
        )
        normal, winter = changed["downside", 2027, 1], self.by_key["downside", 2027, 1]
        self.assertGreater(
            normal["capacity"]["rail"]["capacity_cars"], winter["capacity"]["rail"]["capacity_cars"]
        )
        self.assertGreater(
            winter["segments"]["TRUCKING"]["additional_cash_cost_usd"],
            normal["segments"]["TRUCKING"]["additional_cash_cost_usd"],
        )

    def test_customer_loss_preserves_contract_value_mix(self):
        before, after = self.by_key["downside", 2028, 5], self.by_key["downside", 2028, 6]
        self.assertEqual(before["lost_customer_ids"], [])
        self.assertEqual(after["lost_customer_ids"], ["ARU-C-001"])
        self.assertAlmostEqual(
            after["segments"]["BST"]["customer_loss_revenue_fraction"], 3275000 / 15500000
        )
        self.assertGreater(after["segments"]["BST"]["customer_loss_units"], 0)
        self.assertNotAlmostEqual(
            after["segments"]["BST"]["revenue_volume_factor"],
            after["segments"]["BST"]["served_units"]
            / after["segments"]["BST"]["baseline_2025_month_units"],
        )

    def test_mine_interruption_uses_stock_and_repair_cash(self):
        changed = self.changed_rows(
            lambda s: s.update(events=[e for e in s["events"] if e["type"] != "mine_interruption"])
        )
        original, uninterrupted = self.by_key["downside", 2027, 8], changed["downside", 2027, 8]
        self.assertLess(
            original["mine"]["production_u3o8_lb"], uninterrupted["mine"]["production_u3o8_lb"]
        )
        self.assertGreater(
            original["mine"]["additional_cash_cost_usd"],
            uninterrupted["mine"]["additional_cash_cost_usd"],
        )
        self.assertGreaterEqual(original["mine"]["ending_product_inventory_lb"], 60000)

    def test_acid_disruption_cannot_create_missing_reagent(self):
        affected = self.by_key["downside", 2028, 2]["mine"]
        self.assertGreater(affected["inventory_constrained_tons"], 0)
        self.assertAlmostEqual(affected["ending_acid_tons"], 210)
        self.assertAlmostEqual(
            affected["opening_acid_tons"]
            + affected["acid_received_tons"]
            - affected["acid_consumed_tons"],
            affected["ending_acid_tons"],
        )
        self.assertGreaterEqual(affected["ending_binder_tons"], 245)

    def test_capital_precedes_conditional_capacity_and_is_not_duplicated(self):
        expansion = [r for r in self.rows if r["scenario"] == "expansion"]
        self.assertAlmostEqual(sum(r["capital"]["aru_growth_usd"] for r in expansion), 9400000)
        self.assertAlmostEqual(sum(r["capital"]["mine_growth_usd"] for r in expansion), 8000000)
        self.assertEqual(self.by_key["expansion", 2028, 6]["segments"]["TRUCKING"]["fte"], 24)
        self.assertEqual(self.by_key["expansion", 2028, 7]["segments"]["TRUCKING"]["fte"], 28)
        self.assertLess(
            self.by_key["expansion", 2028, 12]["mine"]["operating_capacity_tons"],
            self.by_key["expansion", 2029, 1]["mine"]["operating_capacity_tons"],
        )
        self.assertTrue(all(r["year"] >= 2027 for r in self.rows))

    def test_product_buffer_and_capacity_prevent_unearned_sales(self):
        rows = [r for r in self.rows if r["scenario"] == "base" and r["year"] == 2031]
        self.assertGreater(sum(r["mine"]["lost_sales_u3o8_lb"] for r in rows), 0)
        self.assertAlmostEqual(rows[-1]["mine"]["ending_product_inventory_lb"], 60000)
        for row in rows:
            mine = row["mine"]
            self.assertLessEqual(
                mine["sales_u3o8_lb"],
                mine["opening_product_inventory_lb"] + mine["production_u3o8_lb"],
            )

    def test_procurement_volume_excludes_outside_fulfillment(self):
        outsourced = [
            r for r in self.rows if any(s["outsourced_units"] for s in r["segments"].values())
        ]
        self.assertTrue(outsourced)
        for row in outsourced:
            for s in row["segments"].values():
                self.assertAlmostEqual(
                    s["cost_volume_factor"] * s["baseline_2025_month_units"],
                    s["owned_served_units"],
                )
                self.assertEqual(s["owned_served_units"] + s["outsourced_units"], s["served_units"])


if __name__ == "__main__":
    unittest.main()
