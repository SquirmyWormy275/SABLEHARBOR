from decimal import Decimal as D
import unittest
from enterprise.runtime import model, planning as p


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.data = model.load()
        self.a = self.data["capital"]["implementation_assumptions"]

    def test_workload_mutation_changes_power_and_finance(self):
        before = p.capacity(self.a, 2027, "base")
        cost = p.finance(self.data)
        self.a["drivers"]["tasks_per_user_day"] *= 2
        after = p.capacity(self.a, 2027, "base")
        self.assertGreater(after["gpu_systems"], before["gpu_systems"])
        self.assertGreater(after["peak_kw"], before["peak_kw"])
        self.assertNotEqual(cost, p.finance(self.data))

    def test_efficiency_and_growth_are_independent(self):
        before = p.capacity(self.a, 2031, "base")
        self.a["scenarios"]["base"]["efficiency_gain"] = 0
        after = p.capacity(self.a, 2031, "base")
        self.assertEqual(before["users"], after["users"])
        self.assertGreaterEqual(after["gpu_systems"], before["gpu_systems"])

    def test_recovery_capacity_and_full_restore_are_distinct(self):
        size = p.capacity(self.a, 2027, "base", True)
        self.assertLessEqual(size["peak_kw"], 25)
        self.assertGreater(size["full_network_restore_hours"], 8)
        self.assertFalse(size["performance_verified"])
        self.assertGreater(p.capacity(self.a, 2031, "base", True)["peak_kw"], 25)

    def test_gpu_memory_incompatibility_rejected(self):
        self.a["drivers"]["model_parameters_billion"] = 100000
        with self.assertRaises(ValueError):
            p.capacity(self.a, 2027, "base")

    def test_price_not_power_twice(self):
        self.assertEqual(p.colo_charge(14.6, 25, 300, "MEASURED"), D("4380"))
        self.assertEqual(p.colo_charge(14.6, 25, 300, "COMMITTED"), D("7500"))
        with self.assertRaises(ValueError):
            p.colo_charge(14.6, 25, 300, "MEASURED", True, 50)

    def test_terminal_proceeds_only_in_terminal_period(self):
        self.a["commercial"]["terminal_sale_value"] = 1000000
        rows = p.finance(self.data)["annual"]
        self.assertTrue(
            all(D(r["terminal_cash"]) == 0 for r in rows if r["year"] != 2036)
        )
        self.assertTrue(
            all(D(r["terminal_cash"]) == 1000000 for r in rows if r["year"] == 2036)
        )

    def test_no_unapproved_payments(self):
        result = p.finance(self.data)
        self.assertTrue(all(D(r["actual_paid_cash"]) == 0 for r in result["annual"]))
        self.assertEqual(
            result["land_adjustment"]["debit_land"],
            result["land_adjustment"]["credit_unresolved_settlement_clearing"],
        )
        self.a["phases"][1]["paid"] = 1
        with self.assertRaises(ValueError):
            model.validate(self.data)

    def test_reserve_is_not_incurred(self):
        cash = p.phase_cash(self.a, "base")
        self.assertEqual(sum(cash.values()), D(15000000))
        self.assertEqual(sum(x["cost"] for x in self.a["phases"]), 15500000)

    def test_delays_change_cash_dates_not_actual_history(self):
        base = p.phase_cash(self.a, "base")
        delay = p.phase_cash(self.a, "delayed_build")
        self.assertEqual(sum(base.values()), sum(delay.values()))
        self.assertNotEqual(base, delay)
        self.assertFalse(
            any(x["operating"] for x in model.world_state(self.data, "2036-12-31"))
        )

    def test_single_employee_cost_and_continuous_coverage(self):
        w = p.workforce(self.a, True)
        self.assertEqual(w["productive_hours_per_fte"], 1560)
        self.assertAlmostEqual(w["continuous_security_fte"], 8760 / 1560, places=4)
        self.assertEqual(w["proposed_guard_positions"], 6)
        self.assertEqual(w["occupied_new_positions"], 0)
        self.a["workforce"]["roles"][0]["allocated_fraction"] = 1.1
        with self.assertRaises(ValueError):
            model.validate(self.data)
