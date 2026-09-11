import copy
import json
from pathlib import Path
import tempfile
import unittest

from enterprise.runtime import model as runtime
from enterprise.services import model as services


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.data = runtime.load()

    def test_every_required_site_field(self):
        for index, site in enumerate(self.data["sites"]["sites"]):
            for key in site:
                with self.subTest(site=site["id"], field=key):
                    changed = copy.deepcopy(self.data)
                    del changed["sites"]["sites"][index][key]
                    with self.assertRaises((ValueError, KeyError)):
                        runtime.validate(changed)

    def test_every_required_capital_field(self):
        for key in self.data["capital"]["owned_site"]:
            changed = copy.deepcopy(self.data)
            del changed["capital"]["owned_site"][key]
            with self.assertRaises((ValueError, KeyError)):
                runtime.validate(changed)

    def test_quantity_types_and_nonfinite(self):
        for value in (True, -1, float("nan"), float("inf"), "100"):
            self.data["sites"]["sites"][0]["initial_usable_it_kw_high"] = value
            with self.assertRaises(ValueError):
                runtime.validate(self.data)

    def test_actual_vs_recorded_knowledge(self):
        self.assertEqual(runtime.world_state(self.data, "2026-09-03"), [])
        self.assertEqual(len(runtime.world_state(self.data, "2026-09-04")), 1)
        self.assertEqual(runtime.world_state(self.data, "2026-09-04", "2026-09-04"), [])
        self.assertEqual(len(runtime.world_state(self.data)), 3)
        self.assertEqual(
            runtime.world_state(self.data, "2030-01-01"), runtime.world_state(self.data)
        )

    def test_provider_substitution_rejected(self):
        self.data["sites"]["sites"][1]["provider"] = "Switch"
        with self.assertRaises(ValueError):
            runtime.validate(self.data)

    def test_no_state_promotion(self):
        for field in ("operating", "contract_executed", "capacity_reserved"):
            data = copy.deepcopy(self.data)
            data["sites"]["sites"][0][field] = True
            with self.assertRaises(ValueError):
                runtime.validate(data)
        self.data["sites"]["sites"][1]["independence_verified"] = True
        with self.assertRaises(ValueError):
            runtime.validate(self.data)

    def test_no_duplicate_or_new_entity(self):
        self.data["sites"]["sites"][0]["entity_id"] = "SHIH"
        with self.assertRaises(ValueError):
            runtime.validate(self.data)

    def test_capital_land_is_included(self):
        self.data["capital"]["owned_site"]["phase_1_total_usd"] += 3000000
        with self.assertRaises(ValueError):
            runtime.validate(self.data)

    def test_loader_consumes_runtime_and_preserves_legacy(self):
        current = services.load()
        self.assertIn("runtime", current)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            for name in services.FILES:
                (source / (name + ".json")).write_bytes(
                    (services.ROOT / "source" / (name + ".json")).read_bytes()
                )
            legacy = services.load(source)
            self.assertNotIn("runtime", legacy)
            self.assertEqual(
                services.compare(current, "owned_colo"),
                services.compare(legacy, "owned_colo"),
            )
            for name, path in runtime.FILES.items():
                (source / Path(path).name).write_text(json.dumps(self.data[name]))
            changed = self.data["sites"]["sites"][0]
            changed["initial_usable_it_kw_high"] = 95
            (source / Path(runtime.FILES["sites"]).name).write_text(
                json.dumps(self.data["sites"])
            )
            loaded = services.load(source)
            self.assertEqual(
                runtime.export(loaded["runtime"])["sites"][0][
                    "initial_usable_it_kw_high"
                ],
                95,
            )
            self.assertNotEqual(
                runtime.export(current["runtime"]), runtime.export(loaded["runtime"])
            )
            (source / Path(runtime.FILES["capital"]).name).unlink()
            with self.assertRaises(ValueError):
                services.load(source)


if __name__ == "__main__":
    unittest.main()
