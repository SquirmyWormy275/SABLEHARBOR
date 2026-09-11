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


class SpatialRegisterRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        program_spec = importlib.util.spec_from_file_location(
            "facility_program", Path(__file__).with_name("program.py")
        )
        cls.program = importlib.util.module_from_spec(program_spec)
        program_spec.loader.exec_module(cls.program)

    def test_desks_cannot_drift_from_derived_register(self):
        expected = {"floors": [{"id": "test-floor", "assigned_desks": 4}]}
        actual = copy.deepcopy(expected)
        actual["floors"][0]["assigned_desks"] = 5
        self.assertEqual(self.program.register_errors(expected, expected), [])
        self.assertEqual(self.program.register_errors(actual, expected), ["stale spatial register"])

    def test_unknown_workforce_is_not_zero(self):
        expected = {"sites": [{"id": "test-site", "workforce": {"authorized_positions": None}}]}
        actual = copy.deepcopy(expected)
        actual["sites"][0]["workforce"]["authorized_positions"] = 0
        self.assertEqual(self.program.register_errors(expected, expected), [])
        self.assertEqual(self.program.register_errors(actual, expected), ["stale spatial register"])


class ApprovedR01Regression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        models, _ = validation.load_models()
        cls.site = next(s for s in models if s["site_id"] == "SH-SITE-0001")
        manifest = json.loads((validation.R01_REFERENCE_DIR / "MANIFEST.json").read_text())
        cls.reference_record = next(
            r for r in manifest["files"] if r["filename"] in validation.R01_HASHES
        )
        cls.reference_bytes = (
            validation.R01_REFERENCE_DIR / cls.reference_record["filename"]
        ).read_bytes()

    def test_immutable_originals(self):
        self.assertEqual(validation.validate_r01_references(), [])

    def test_reference_bytes_cannot_be_replaced(self):
        content = bytearray(self.reference_bytes)
        content[-1] ^= 1
        errors = validation.reference_bytes_errors(
            self.reference_record["filename"], bytes(content), self.reference_record
        )
        self.assertTrue(any("reference hash mismatch" in e for e in errors))

    def test_reference_dimensions_cannot_be_relabelled(self):
        record = copy.deepcopy(self.reference_record)
        record["dimensions_px"] = [3240, 2000]
        errors = validation.reference_bytes_errors(record["filename"], self.reference_bytes, record)
        self.assertTrue(any("dimensions mismatch" in e for e in errors))

    def test_approved_program(self):
        self.assertEqual(validation.validate_r01(self.site), [])

    def test_all_ten_floors_required(self):
        site = copy.deepcopy(self.site)
        site["buildings"][0]["floors"].pop()
        self.assertTrue(
            any("required floor stack incomplete" in e for e in validation.validate_r01(site))
        )

    def test_explicit_core_cannot_move(self):
        site = copy.deepcopy(self.site)
        core = site["buildings"][0]["core_zones"][0]
        core["rect_ft"][0] += 1
        core["rect_m"][0] += 0.3048
        self.assertTrue(
            any("approved core coordinates changed" in e for e in validation.validate_r01(site))
        )

    def test_circulation_must_not_overlap_rooms(self):
        site = copy.deepcopy(self.site)
        floor = site["buildings"][0]["floors"][0]
        floor["circulation_zones"][0]["rect_m"] = list(floor["rooms"][0]["rect_m"])
        self.assertTrue(any("overlapping explicit" in e for e in validation.validate_r01(site)))

    def test_workplaces_remain_approved_capacity(self):
        site = copy.deepcopy(self.site)
        site["buildings"][0]["floors"][0]["rooms"][0]["assigned_desks"] += 1
        self.assertTrue(
            any("362 fitted staff workplaces changed" in e for e in validation.validate_r01(site))
        )


if __name__ == "__main__":
    unittest.main()


class VisualArtifactRegression(unittest.TestCase):
    def test_missing_font_lock_is_rejected(self):
        dependencies = [
            validation.BASE / "render.py",
            validation.BASE / "r01_drawing.py",
            validation.ROOT / "geospatial/registers/MAP_ID_REGISTER.json",
            validation.R01_REFERENCE_DIR / "MANIFEST.json",
            *[validation.R01_REFERENCE_DIR / n for n in validation.R01_HASHES],
            *sorted((validation.BASE / "fonts").glob("*")),
        ]
        locks = {str(p.relative_to(validation.ROOT)): validation.sha(p) for p in dependencies}
        self.assertEqual(validation.r02_dependency_errors(locks), [])
        del locks["geospatial/facilities/fonts/DejaVuSans.ttf"]
        self.assertTrue(any("DejaVuSans.ttf" in e for e in validation.r02_dependency_errors(locks)))

    def test_text_outside_page_is_rejected(self):
        import fitz

        with fitz.open() as doc:
            page = doc.new_page(width=1080, height=768)
            page.insert_text((10, 5), "Clipped title", fontsize=20)
            self.assertIn("text overflows page", validation.pdf_page_errors(page))

    def test_wrong_page_shape_and_fallback_font_are_rejected(self):
        import fitz

        with fitz.open() as doc:
            page = doc.new_page(width=1000, height=1000)
            page.insert_text((10, 30), "Fallback Helvetica")
            errors = validation.pdf_page_errors(page, r02=True)
            self.assertTrue(any("proportions" in e for e in errors))
            self.assertTrue(any("fallback font" in e for e in errors))
            self.assertTrue(any("not embedded" in e for e in errors))

    def test_embedded_dejavu_and_approved_shape_pass(self):
        import fitz

        with fitz.open() as doc:
            page = doc.new_page(width=1080, height=768)
            page.insert_font(fontname="SH", fontfile=str(validation.BASE / "fonts/DejaVuSans.ttf"))
            page.insert_text((10, 30), "SABLE HARBOR", fontname="SH")
            self.assertEqual(validation.pdf_page_errors(page, r02=True), [])
