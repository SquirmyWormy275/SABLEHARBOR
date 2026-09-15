import copy
import json
import unittest
from .applicability import SOURCE, validate


class ApplicabilityTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SOURCE.read_text())

    def test_declared_source_populations(self):
        result = validate(self.data)
        self.assertEqual(result["unit_boundaries"], 8)
        self.assertIn("NO_OCCURRENCE_IN_DECLARED_SOURCE", result["performance_states"])

    def test_bad_population_identity_timing_and_promotion(self):
        mutations = [
            lambda d: d["records"].pop(),
            lambda d: d["records"].append(copy.deepcopy(d["records"][0])),
            lambda d: d["records"][0].update(population_count=59),
            lambda d: d["records"][0].update(legal_entities=["Foundry Field Inc."]),
            lambda d: d["records"][0].update(available_on="2026-08-31"),
            lambda d: d["records"][0].update(source_sha256="0" * 64),
            lambda d: d["records"][0].update(performance="PASS"),
        ]
        for mutation in mutations:
            data = copy.deepcopy(self.data)
            mutation(data)
            with self.assertRaises(ValueError):
                validate(data)
