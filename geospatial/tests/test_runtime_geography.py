import importlib.util
import json
from pathlib import Path
import unittest
from pyproj import Geod
from shapely.geometry import shape
from enterprise.runtime import model

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "sync_runtime", ROOT / "geospatial/scripts/sync_runtime.py"
)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class RuntimeGeographyTests(unittest.TestCase):
    def test_area_and_coordinate_order(self):
        data = model.load()
        site = data["sites"]["sites"][2]
        geometry, area = sync.parcel(site)
        poly = shape(geometry)
        self.assertTrue(poly.is_valid)
        self.assertAlmostEqual(
            abs(Geod(ellps="WGS84").geometry_area_perimeter(poly)[0]) / 4046.8564224, 7.5, places=3
        )
        self.assertAlmostEqual(poly.centroid.x, -119.455, places=4)
        self.assertIsNone(site["real_apn"])

    def test_sync_idempotence_and_mutation(self):
        catalog = json.loads((ROOT / "geospatial/sources/catalog.json").read_text())
        runtime = model.load()
        first, geo = sync.synchronize(catalog, runtime)
        self.assertEqual((first, geo), sync.synchronize(first, runtime))
        runtime["sites"]["sites"][0]["name"] = "Changed source display name"
        changed, _ = sync.synchronize(first, runtime)
        self.assertNotEqual(first, changed)
        original = {
            o["object_id"]: o
            for o in catalog["objects"]
            if o.get("source_id") != "SRC-RUNTIME-20260911"
        }
        after = {o["object_id"]: o for o in changed["objects"] if o["object_id"] in original}
        self.assertEqual(original, after)
