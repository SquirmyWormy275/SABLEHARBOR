"""Regression mutations target acceptance failures, not renderer internals."""

import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "facility_validation", Path(__file__).with_name("validate.py")
)
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


class FacilityRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models, _ = validation.load_models()

    def mutant(self):
        return copy.deepcopy(self.models)

    def test_current_sources(self):
        self.assertEqual(validation.validate_models(self.models), [])

    def test_missing_floor(self):
        models = self.mutant()
        models[0]["buildings"][0]["floors"] = []
        self.assertTrue(
            any("missing required floors" in e for e in validation.validate_models(models))
        )

    def test_duplicate_floor(self):
        models = self.mutant()
        floors = models[0]["buildings"][0]["floors"]
        floors.append(copy.deepcopy(floors[0]))
        self.assertTrue(any("duplicate IDs" in e for e in validation.validate_models(models)))

    def test_bad_area(self):
        models = self.mutant()
        models[0]["buildings"][0]["floors"][0]["gross_area_m2"] += 1
        self.assertTrue(any("area" in e for e in validation.validate_models(models)))

    def test_bad_population(self):
        models = self.mutant()
        models[0]["attendance_scenarios"][0]["people"] += 1
        self.assertTrue(any("rollup mismatch" in e for e in validation.validate_models(models)))

    def test_invalid_status(self):
        models = self.mutant()
        models[0]["buildings"][0]["floors"][0]["status"] = "COMPLETE_TRUST_ME"
        self.assertTrue(any("invalid status" in e for e in validation.validate_models(models)))

    def test_uncovered_site(self):
        self.assertTrue(
            any(
                "no coverage disposition" in e
                for e in validation.validate_models(self.models, set())
            )
        )

    def test_overlapping_rooms(self):
        models = self.mutant()
        rooms = models[0]["buildings"][0]["floors"][0]["rooms"]
        rooms[1]["rect_m"] = list(rooms[0]["rect_m"])
        self.assertTrue(any("overlapping rooms" in e for e in validation.validate_models(models)))

    def test_missing_capacity_category(self):
        models = self.mutant()
        del models[0]["buildings"][0]["floors"][0]["rooms"][0]["training_seats"]
        self.assertTrue(any("capacity category" in e for e in validation.validate_models(models)))

    def test_floor_peak_exceeded(self):
        models = self.mutant()
        models[0]["buildings"][0]["floors"][0]["planned_peak"] = 0
        self.assertTrue(
            any("exceeds floor planned peak" in e for e in validation.validate_models(models))
        )


if __name__ == "__main__":
    unittest.main()
