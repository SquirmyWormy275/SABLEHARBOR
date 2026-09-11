import copy
import unittest
from build_coverage import build, RUNTIME, COMP, CAT, read
from validate_coverage import validate


class CoverageRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = build()

    def test_complete(self):
        self.assertEqual(validate(self.model), [])

    def test_runtime_census_aliases_and_dynamic_counts(self):
        d = self.model
        self.assertEqual(d["counts"]["catalog_objects"], len(read(CAT)["objects"]))
        self.assertEqual(d["counts"]["service_components"], len(read(COMP)["components"]))
        self.assertEqual(d["counts"]["runtime_sites"], len(read(RUNTIME)["sites"]))
        for site in read(RUNTIME)["sites"]:
            for path, section, ident in [
                (RUNTIME, "sites", site["id"]),
                (COMP, "components", site["facility_id"]),
            ]:
                matches = [
                    x
                    for x in d["census"]
                    if (x["source_path"], x["section"], x["source_id"]) == (path, section, ident)
                ]
                self.assertEqual([x["coverage_id"] for x in matches], [site["geospatial_site_id"]])
        self.assertFalse(
            any(
                x["id"] in {"SERVICE:FAC-PRIMARY", "SERVICE:FAC-RECOVERY", "SERVICE:FAC-OWNED"}
                for x in d["records"]
            )
        )

    def test_runtime_alias_divergence_fails(self):
        d = copy.deepcopy(self.model)
        next(x for x in d["census"] if x["source_id"] == "FAC-PRIMARY")["coverage_id"] = (
            "SH-SITE-0016"
        )
        self.assertTrue(any("runtime alias" in e for e in validate(d)))

    def test_runtime_provider_floor_invention_fails(self):
        d = copy.deepcopy(self.model)
        next(x for x in d["records"] if x["id"] == "SH-SITE-0028")["required_artifacts"].append(
            "floor_plans"
        )
        self.assertTrue(any("provider context" in e for e in validate(d)))

    def test_runtime_owned_floor_omission_fails(self):
        d = copy.deepcopy(self.model)
        next(x for x in d["records"] if x["id"] == "SH-SITE-0030")["planned_floor_ids"] = []
        self.assertTrue(any("owned runtime" in e for e in validate(d)))

    def test_runtime_status_promotion_fails(self):
        d = copy.deepcopy(self.model)
        next(x for x in d["records"] if x["id"] == "SH-SITE-0030")["runtime_state"] = "OPERATING"
        self.assertTrue(any("runtime state" in e for e in validate(d)))

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
