"""Independent arithmetic, geography, temporal and operating-contract checks."""

import copy
import importlib.util
import json
import math
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "industrial_operations_build", BASE / "tools/build_operations.py"
)
OPS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OPS)


class OperationsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = OPS.load()
        cls.network = json.loads((BASE / "source/geography/network.geojson").read_text())

    def test_controlled_totals_and_pinned_sources(self):
        result = OPS.validate(self.data)
        self.assertTrue(result["passed"])
        self.assertGreater(result["check_count"], 40)

    def test_rates_reconcile_without_billing_contingency(self):
        rows = self.data["interface"]["rates"]
        self.assertEqual(sum(r["normalized_billable_cars"] for r in rows), 215)
        self.assertEqual(
            sum(r["normalized_billable_cars"] for r in rows if r["commodity"] != "project"), 205
        )
        revenue = sum(
            r["normalized_billable_cars"]
            * (r["rail_rate"] + r["terminal_rate"] + r["truck_legs_per_car"] * r["dray_rate"])
            for r in rows
        )
        costs = sum(
            r["normalized_billable_cars"]
            * (
                r["rail_unit_cost"]
                + r["terminal_unit_cost"]
                + r["truck_legs_per_car"] * r["dray_unit_cost"]
            )
            for r in rows
        )
        self.assertEqual(revenue, 583480)
        self.assertEqual(costs, 332190)
        self.assertEqual(revenue - costs - 48000, 203290)
        self.assertNotEqual(revenue, 875000)
        external = sum(r["normalized_billable_cars"] * r["external_linehaul_per_car"] for r in rows)
        self.assertGreater(external, 0)
        self.assertEqual(OPS.economics(self.data)["normalized_revenue_usd"], revenue)

    def test_road_payloads_and_storage_can_receive_batches(self):
        rows = self.data["interface"]["rates"]
        for r in rows:
            if r["commodity"] in {"acid", "binder", "lime", "steel"}:
                self.assertLessEqual(r["car_payload_short_tons"], 25 * r["truck_legs_per_car"])
        acid, binder = self.data["interface"]["receiving"]
        tank_tons = (
            acid["nominal_tank_gallons"]
            * acid["usable_fraction"]
            * acid["density_lb_per_us_gallon"]
            / 2000
        )
        self.assertGreaterEqual(tank_tons, acid["working_inventory_short_tons"])
        self.assertGreaterEqual(
            acid["working_inventory_short_tons"] - acid["minimum_operating_inventory_short_tons"],
            100,
        )
        self.assertGreaterEqual(
            binder["working_capacity_short_tons"]
            - binder["minimum_operating_inventory_short_tons"],
            100,
        )
        self.assertAlmostEqual(
            acid["annual_pure_acid_short_tons"], acid["annual_as_received_short_tons"] * 0.98
        )

    def test_annual_normalized_and_startup_periods_are_separate(self):
        monthly = self.data["interface"]["monthly_2026"]
        totals = {r["commodity"]: 0 for r in self.data["interface"]["rates"]}
        for m in monthly:
            for c, n in m["carloads"].items():
                totals[c] += n
            if m["month"] >= "2026-09":
                self.assertEqual(m["status"], "FORECAST_AT_2026_09_05")
        self.assertEqual(
            totals, {"acid": 21, "binder": 23, "lime": 4, "steel": 8, "mro": 4, "project": 3}
        )
        self.assertEqual(sum(totals.values()), 63)
        self.assertFalse(self.data["interface"]["current_annual_actual_is_normalized"])
        self.assertEqual(self.data["interface"]["service_start"], "2026-07-07")

    def test_friday_after_cutoff_needs_a_funded_exception(self):
        received = datetime.fromisoformat("2026-07-10T09:00:00-06:00")
        acid = OPS.service_case(received, "acid", self.data)
        self.assertTrue(acid["within_sla"])
        self.assertIn("exception", acid["mode"])
        self.assertLessEqual(acid["elapsed_hours"], 72)
        steel = OPS.service_case(received, "steel", self.data)
        self.assertLessEqual(steel["elapsed_hours"], 96)

    def test_dst_uses_elapsed_utc_hours(self):
        fall = OPS.service_case(
            datetime.fromisoformat("2026-10-31T20:00:00-06:00"), "acid", self.data
        )
        spring = OPS.service_case(
            datetime.fromisoformat("2026-03-07T20:00:00-07:00"), "acid", self.data
        )
        self.assertEqual(fall["elapsed_hours"], 69)
        self.assertEqual(spring["elapsed_hours"], 67)
        with self.assertRaises(ValueError):
            OPS.service_case(datetime(2026, 7, 10, 9), "acid", self.data)

    def test_every_day_arrival_calendar_meets_declared_sla(self):
        # Independent adversarial receipts, including weekends and both DST changes.
        start = datetime(2026, 1, 1, tzinfo=OPS.MOUNTAIN)
        for day in range(365):
            for hour in [0, 7, 9, 23]:
                received = (start + timedelta(days=day)).replace(hour=hour)
                for commodity in ["acid", "binder", "steel", "project"]:
                    result = OPS.service_case(received, commodity, self.data)
                    self.assertTrue(result["within_sla"], result)

    def test_route_geodesy_and_no_mine_spur(self):
        rail = [f for f in self.network["features"] if f["id"].startswith("BST-")]
        lengths = [OPS.line_miles(f["geometry"]["coordinates"]) for f in rail]
        self.assertAlmostEqual(sum(lengths), 40, places=5)
        self.assertAlmostEqual(lengths[1], 4, places=5)
        self.assertAlmostEqual(lengths[2], 2.6515232364, places=5)
        for f in rail:
            self.assertGreater(
                OPS.vincenty_miles(f["geometry"]["coordinates"][-1], [-108.18, 42.22]), 1
            )
        road = next(f for f in self.network["features"] if f["id"] == "ROAD-RW-01")
        self.assertAlmostEqual(OPS.line_miles(road["geometry"]["coordinates"]), 9, places=5)
        self.assertEqual(road["properties"]["mode"], "truck_only")

    def test_branch_junctions_are_geometrically_on_main(self):
        main = self.network["features"][0]["geometry"]["coordinates"]

        def distance(point, a, b):
            cosine = math.cos(math.radians(point[1]))
            x, y = point[0] * cosine, point[1]
            ax, ay = a[0] * cosine, a[1]
            bx, by = b[0] * cosine, b[1]
            t = max(
                0,
                min(
                    1,
                    ((x - ax) * (bx - ax) + (y - ay) * (by - ay))
                    / ((bx - ax) ** 2 + (by - ay) ** 2),
                ),
            )
            return math.hypot(x - (ax + t * (bx - ax)), y - (ay + t * (by - ay))) * 111195

        for f in self.network["features"][1:3]:
            p = f["geometry"]["coordinates"][0]
            self.assertLess(
                min(distance(p, a, b) for a, b in zip(main, main[1:], strict=False)), 0.1
            )  # noqa: E501 — literal SVG/document text

    def test_capital_references_resolve_to_real_source_records(self):
        ids = {
            r["id"]
            for group in [
                "facilities",
                "track_segments",
                "structures",
                "locomotives",
                "railcars",
                "road_equipment",
                "handling_equipment",
            ]
            for r in self.data[group]
        }
        ids.update(f["id"] for f in self.network["features"])
        for r in self.data["catchup_capital"]:
            self.assertTrue(set(r["asset_ids"]) <= ids)
        for r in self.data["interface"]["phase1_capex"]:
            self.assertIn(r["asset_id"], ids)

    def test_staffing_and_external_capacity_are_not_double_counted(self):
        f = self.data["facilities"]
        rail = sum(
            r["assigned_fte"] for r in f if r["owner"] == "Blood, Sweat & Tears Railway Company"
        )
        aru = sum(r["assigned_fte"] for r in f if r["owner"] == "American Resource Utility, Inc.")
        self.assertEqual(rail, 58)
        self.assertEqual(aru, 73)
        self.assertEqual(rail + aru, 131)
        self.assertEqual(sum(r["pallet_slots"] for r in f), 15000)
        self.assertEqual(sum(r["annual_external_ton_capacity"] for r in f), 300000)

    def test_claim_history_does_not_hide_uranium_custody(self):
        claim = self.data["claims"]
        self.assertEqual(claim["closing_reserve_usd"], 600000)
        self.assertEqual(claim["additional_possible_adverse_development_usd"], 700000)
        incident = next(r for r in self.data["safety_events"] if r["date"] == "2026-08-14")
        self.assertIn("acid", incident["description"])
        self.assertIn("no uranium custody", incident["corrective_action"])
        self.assertEqual(self.data["interface"]["direct_uranium_custody"], "OPEN_GATED")

    def test_cross_file_contract_and_physical_capacity_failures_are_detected(self):
        changed = copy.deepcopy(self.data)
        changed["contract_facility_assignments"][0]["annual_units_2025"] += 1
        with self.assertRaisesRegex(ValueError, "physical units reconcile"):
            OPS.validate(changed)
        changed = copy.deepcopy(self.data)
        changed["facility_capacity_bridge"]["trucking"]["available_driver_hours"] = 31000
        with self.assertRaisesRegex(ValueError, "driver and tractor hours"):
            OPS.validate(changed)

    def test_yard_lengths_include_locomotive_and_clearance_space(self):
        changed = copy.deepcopy(self.data)
        track = next(t for t in changed["track_segments"] if t.get("facility_id") == "FAC-WAM-INT")
        self.assertEqual(track["car_spots"], 20)
        track["length_miles"] = 0.22
        with self.assertRaisesRegex(ValueError, "train length fits"):
            OPS.validate(changed)

    def test_historical_epochs_preserve_uncertainty_and_reconcile_growth(self):
        epochs = {r["epoch"]: r for r in self.data["geography"]["historical_route_epochs"]}
        self.assertIsNone(epochs["1898"]["route_miles"])
        self.assertIsNone(epochs["1954"]["route_miles"])
        self.assertEqual(epochs["1954"]["surviving_route_miles_low"], 14)
        self.assertEqual(epochs["1954"]["surviving_route_miles_high"], 16)
        self.assertEqual(
            sorted(r["effective_date"] for r in epochs.values()),
            [r["effective_date"] for r in epochs.values()],
        )
        self.assertAlmostEqual(
            epochs["1968"]["route_miles"] + 4 + epochs["1986"]["added_route_miles"], 40
        )
        changed = copy.deepcopy(self.data)
        changed["geography"]["historical_route_epochs"][0]["route_miles"] = 15
        with self.assertRaisesRegex(ValueError, "early coal route extent"):
            OPS.validate(changed)
        with tempfile.TemporaryDirectory() as directory:
            OPS.historical_map(Path(directory), self.data)
            tree = ET.fromstring((Path(directory) / "bst_historical_routes.svg").read_text())
            text = " ".join(n.text or "" for n in tree.iter() if n.tag.endswith("text"))
            for term in [
                "1898",
                "1954",
                "1968",
                "1972",
                "1986",
                "40.0000",
                "not georeferenced",
                "unlocated",
            ]:
                self.assertIn(term, text)

    def test_every_registered_track_has_exported_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            OPS.geography_outputs(Path(directory), self.data)
            tracks = json.loads((Path(directory) / "track_segments.geojson").read_text())
            self.assertEqual(
                {f["id"] for f in tracks["features"]},
                {t["id"] for t in self.data["track_segments"]},
            )
            for feature in tracks["features"]:
                self.assertGreaterEqual(len(feature["geometry"]["coordinates"]), 2)
                self.assertAlmostEqual(
                    OPS.line_miles(feature["geometry"]["coordinates"]),
                    feature["properties"]["length_miles"],
                    delta=0.002,
                )

    def test_two_builds_have_identical_hashes_and_valid_svg(self):
        with tempfile.TemporaryDirectory() as directory:
            a = Path(directory) / "a"
            b = Path(directory) / "b"
            OPS.build(a)
            OPS.build(b)
            ma = json.loads((a / "manifest.json").read_text())
            mb = json.loads((b / "manifest.json").read_text())
            self.assertEqual(ma, mb)
            for name in ["bst_network.svg", "red_wash_site.svg", "red_wash_underground.svg"]:
                content = (a / "maps" / name).read_text()
                tree = ET.fromstring(content)
                visible = " ".join(n.text or "" for n in tree.iter() if n.tag.endswith("text"))
                self.assertNotIn("106.9213", visible)
                self.assertNotIn("6,420", visible)
                self.assertIn("synthetic", visible.lower())
                self.assertIn("CRS", visible)


if __name__ == "__main__":
    unittest.main()
