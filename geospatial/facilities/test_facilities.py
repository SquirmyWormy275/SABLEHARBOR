"""Regression mutations target acceptance failures, not renderer internals."""

import copy
import importlib.util
import json
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


class AtlasGraphRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models, _ = validation.load_models()
        cls.graph = json.loads(
            (validation.ROOT / "geospatial/maps/facilities/ATLAS_LINKS.json").read_text()
        )
        cls.coverage = json.loads((validation.BASE / "coverage/COVERAGE_MATRIX.json").read_text())[
            "records"
        ]

    def test_current_graph(self):
        self.assertEqual(validation.validate_graph(self.graph, self.models, self.coverage), [])

    def test_floor_disconnected(self):
        graph = copy.deepcopy(self.graph)
        floor = self.models[0]["buildings"][0]["floors"][0]["id"]
        graph["edges"] = [e for e in graph["edges"] if e["target"] != floor]
        errors = validation.validate_graph(graph, self.models, self.coverage)
        self.assertTrue(any("unreachable atlas nodes" in e for e in errors))
        self.assertTrue(any("missing building/floor" in e for e in errors))

    def test_source_stale(self):
        graph = copy.deepcopy(self.graph)
        graph["source_sha256"]["geospatial/facilities/source/campus.json"] = "0" * 64
        self.assertTrue(
            any(
                "stale atlas source" in e
                for e in validation.validate_graph(graph, self.models, self.coverage)
            )
        )

    def test_census_omitted(self):
        graph = copy.deepcopy(self.graph)
        graph["coverage"].pop()
        self.assertTrue(
            any(
                "census mismatch" in e
                for e in validation.validate_graph(graph, self.models, self.coverage)
            )
        )


if __name__ == "__main__":
    unittest.main()
