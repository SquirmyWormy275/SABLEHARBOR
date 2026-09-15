import copy
import json
import unittest

from .performance import DIRECTORY, available_records, validate_workplace
from .restore_rehearsal import run


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((DIRECTORY / "workplace_examinations.json").read_text())

    def test_qualified_completed_population_and_known_on(self):
        self.assertEqual(
            validate_workplace(self.data), {"examinations": 4, "blocked_assignments": 1}
        )
        self.assertEqual(available_records(self.data, "2026-08-31"), [])
        self.assertEqual(len(available_records(self.data, "2026-09-15")), 4)

    def test_omission_duplicate_unqualified_late_and_self_review(self):
        mutations = [
            lambda d: d["examinations"].pop(),
            lambda d: d["examinations"].append(copy.deepcopy(d["examinations"][0])),
            lambda d: d["qualification_records"][0].update(expires_on="2026-07-31"),
            lambda d: d["examinations"][0].update(recorded_at="2026-09-01T00:00:00-06:00"),
            lambda d: d["examinations"][0].update(legal_entity="SHI"),
            lambda d: d["examinations"][1].update(corrected_at="2026-08-31T06:01:00-06:00"),
            lambda d: d["review"].update(reviewer_id=d["review"]["preparer_id"]),
            lambda d: d["attempts"][0].update(authorized_release=True),
        ]
        for mutate in mutations:
            d = copy.deepcopy(self.data)
            mutate(d)
            with self.assertRaises(ValueError):
                validate_workplace(d)

    def test_actual_disk_restore(self):
        receipt = run()
        self.assertEqual(receipt["isolated_disk_restore"], "PASS")
        self.assertTrue(receipt["revoked_principal_denied"])
        self.assertTrue(receipt["held_disclosure_denied"])
        self.assertEqual(receipt["history_entries"], 2)
