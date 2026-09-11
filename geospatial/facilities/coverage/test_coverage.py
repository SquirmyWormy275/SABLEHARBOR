import copy
import unittest
from build_coverage import build
from validate_coverage import validate


class CoverageRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = build()

    def test_complete(self):
        self.assertEqual(validate(self.model), [])

    def test_orphan_fails(self):
        d = copy.deepcopy(self.model)
        d["census"][0]["coverage_id"] = "missing"
        self.assertTrue(any("orphan" in e for e in validate(d)))

    def test_missing_floor_requirement_fails(self):
        d = copy.deepcopy(self.model)
        next(x for x in d["records"] if x["class"] == 3)["required_artifacts"] = ["context"]
        self.assertTrue(any("omitted floors" in e for e in validate(d)))

    def test_duplicate_identity_fails(self):
        d = copy.deepcopy(self.model)
        d["records"].append(d["records"][0])
        self.assertTrue(any("duplicate coverage" in e for e in validate(d)))

    def test_status_missing_fails(self):
        d = copy.deepcopy(self.model)
        d["records"][0]["status"] = ""
        self.assertTrue(any("missing status" in e for e in validate(d)))


if __name__ == "__main__":
    unittest.main()
