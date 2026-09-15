import copy
import json
import unittest

from .validate import SOURCE, validate


class CensusTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SOURCE.read_text())

    def test_complete_source_population(self):
        self.assertEqual(
            validate(self.data), {"red_wash_permit_register": 14, "rail_safety_events": 14}
        )

    def test_omission_duplicate_stale_future_and_false_pass_rejected(self):
        mutations = [
            lambda d: d["records"].pop(),
            lambda d: d["records"].append(copy.deepcopy(d["records"][0])),
            lambda d: d["records"][0].update(source_sha256="0" * 64),
            lambda d: d.update(available_on="2026-08-31"),
            lambda d: d["records"][0].update(performance="PASS"),
            lambda d: d["records"][0]["source_record"].update(status="FILED"),
        ]
        for mutation in mutations:
            data = copy.deepcopy(self.data)
            mutation(data)
            with self.assertRaises(ValueError):
                validate(data)
