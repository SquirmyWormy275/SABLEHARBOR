"""Geographic context must retain provenance and never georeference the campus."""

import importlib.util
import json
from pathlib import Path

import pytest
from shapely.geometry import shape

spec = importlib.util.spec_from_file_location(
    "spatial_context", Path(__file__).with_name("context.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ROOT = Path(__file__).resolve().parents[3]


def test_real_context_categories_and_unsited_campus():
    result = module.build_context(ROOT)
    region = result["regions"]["sacramento"]
    assert len(result["sites"]) == 19
    assert {f["category"] for f in region["features"]} == {
        "street",
        "rail",
        "water",
        "path",
        "transit",
        "terrain",
    }
    assert result["conceptual_campus"]["transform_to_real_world"] is None
    assert not result["conceptual_campus"]["georeferenced"]
    assert region["campus_geometry"] is None
    for feature in region["features"]:
        assert shape(feature["geometry"]).is_valid
        assert feature["campus_connection"] is None
        assert feature["source_path"] in result["source_sha256"]
    terrain = [f for f in region["features"] if f["category"] == "terrain"]
    assert len(terrain) == 81
    assert all("elevation_m" in f["source_properties"] for f in terrain)
    assert all(f["geometry"]["type"] == "Point" for f in terrain)
    paths = [f for f in region["features"] if f["category"] == "path"]
    assert all(str(f["source_properties"]["BIKE_CLASS"]) == "1" for f in paths)


def test_projection_clips_source_without_changing_it(tmp_path):
    feature = {
        "id": "TEST-LINE",
        "geometry": {"type": "LineString", "coordinates": [[-121.6, 38.59], [-121.4, 38.59]]},
        "properties": {"name": "Fixture"},
    }
    p = tmp_path / "test.geojson"
    p.write_text(json.dumps({"type": "FeatureCollection", "features": [feature]}))
    before = p.read_bytes()
    result = module.project_region(
        tmp_path,
        {"crs": "EPSG:26910", "extent_wgs84": [-121.51, 38.58, -121.48, 38.60]},
        [{"path": "test.geojson", "id": "FIXTURE", "category": "street"}],
    )
    assert p.read_bytes() == before
    geom = shape(result["features"][0]["geometry"])
    assert geom.length < 3000
    assert geom.bounds[0] >= 0


def test_source_hash_mismatch_fails_before_master_read(tmp_path):
    base = tmp_path / module.BASE
    base.mkdir(parents=True)
    source = tmp_path / "source.json"
    source.write_text("{}")
    (base / "CONTEXT_SOURCES.json").write_text(
        json.dumps(
            {"reference_manifest": {"path": "source.json", "sha256": "0" * 64}, "sources": []}
        )
    )
    with pytest.raises(ValueError, match="stale context source"):
        module.build_context(tmp_path)


def test_invalid_reference_geometry_rejected(tmp_path):
    feature = {
        "id": "BAD",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-121.50, 38.59],
                    [-121.49, 38.60],
                    [-121.49, 38.59],
                    [-121.50, 38.60],
                    [-121.50, 38.59],
                ]
            ],
        },
        "properties": {},
    }
    (tmp_path / "bad.json").write_text(json.dumps({"features": [feature]}))
    with pytest.raises(ValueError, match="invalid source geometry"):
        module.project_region(
            tmp_path,
            {"crs": "EPSG:26910", "extent_wgs84": [-121.51, 38.58, -121.48, 38.61]},
            [{"path": "bad.json", "id": "BAD", "category": "water"}],
        )


def test_unused_spatial_manifest_record_does_not_change_context(monkeypatch):
    original = Path.read_text
    before = module.build_context(ROOT)

    def altered(path, *args, **kwargs):
        text = original(path, *args, **kwargs)
        if path == ROOT / "geospatial/maps/MAP_MANIFEST.json":
            data = json.loads(text)
            data.append(
                {
                    "map_id": "SH-MAP-SPATIAL-UNUSED",
                    "source_sha256": "changed-dependent-context-hash",
                }
            )
            return json.dumps(data)
        return text

    monkeypatch.setattr(Path, "read_text", altered)
    assert module.build_context(ROOT) == before
    assert "geospatial/maps/MAP_MANIFEST.json" not in before["source_sha256"]
    assert "geospatial/maps/facilities/ATLAS_LINKS.json" not in before["source_sha256"]


def test_consumed_context_record_changes_semantic_hash(monkeypatch):
    original = Path.read_text
    before = module.build_context(ROOT)
    consumed = before["navigation_scope"]["payload"]["referenced_context_maps"][0]["map_id"]

    def altered(path, *args, **kwargs):
        text = original(path, *args, **kwargs)
        if path == ROOT / "geospatial/maps/MAP_MANIFEST.json":
            data = json.loads(text)
            next(row for row in data if row["map_id"] == consumed)["title"] += " changed"
            return json.dumps(data)
        return text

    monkeypatch.setattr(Path, "read_text", altered)
    after = module.build_context(ROOT)
    assert before["navigation_scope"]["sha256"] != after["navigation_scope"]["sha256"]
    assert before["sites"] != after["sites"]


def test_wamsutter_region_is_not_assigned_to_other_industrial_anchors():
    sites = {site["site_id"]: site for site in module.build_context(ROOT)["sites"]}
    assert sites["SH-IND-FAC-WAM-INT"]["region_key"] == "wamsutter"
    checked = []
    for sid, site in sites.items():
        if sid == "SH-SITE-0006" or (sid.startswith("SH-IND-") and sid != "SH-IND-FAC-WAM-INT"):
            assert site["region_key"] is None, sid
            assert site["reference_layers"] == [], sid
            assert site["context_links"], sid
            checked.append(sid)
    assert "SH-SITE-0006" in checked
    assert any("RECEIVING" in sid for sid in checked)
    assert any("TAY-" in sid for sid in checked)
    assert any("RAW-" in sid for sid in checked)
