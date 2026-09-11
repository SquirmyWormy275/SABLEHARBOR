"""Fail publication loss and stale links independently of the model renderer."""

import importlib.util
import json
from pathlib import Path
import pytest

BASE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("spatial_package_tests", BASE / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


@pytest.fixture
def package():
    root = BASE.parents[2]
    manifest = json.loads((root / "geospatial/maps/spatial/MANIFEST.json").read_text())
    data = build.build_model(root)
    data["access"] = build.build_access(root)
    return data, manifest


def test_required_sheets(package):
    data, manifest = package
    assert build.validate_package(data, manifest)
    assert len(manifest["maps"]) == 86


def test_missing_floor_schedule_fails(package):
    data, manifest = package
    manifest["maps"] = [m for m in manifest["maps"] if m["kind"] != "schedule"]
    with pytest.raises(ValueError, match="schedule"):
        build.validate_package(data, manifest)


def test_stale_artifact_fails(package):
    data, manifest = package
    manifest["maps"][0]["artifacts"]["png"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="artifact"):
        build.validate_package(data, manifest)


def test_duplicate_map_fails(package):
    data, manifest = package
    manifest["maps"].append(manifest["maps"][0])
    with pytest.raises(ValueError, match="Duplicate"):
        build.validate_package(data, manifest)


def test_missing_floor_target_fails(package):
    data, manifest = package
    data["sites"][0]["buildings"][0]["floors"][0]["links"]["png"] = "does-not-exist.png"
    with pytest.raises(ValueError, match="link"):
        build.validate_package(data, manifest)


def test_global_manifest_and_graph_cover_spatial_maps(package):
    _, manifest = package
    root = BASE.parents[2]
    global_maps = {
        m["map_id"]: m for m in json.loads((root / "geospatial/maps/MAP_MANIFEST.json").read_text())
    }
    graph = json.loads((root / "geospatial/maps/facilities/ATLAS_LINKS.json").read_text())
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = {(e["source"], e["target"]) for e in graph["edges"]}
    for m in manifest["maps"]:
        mid = m["id"]
        assert mid in global_maps and mid in nodes
        parent = m.get("floor_id") or m.get("building_id") or m["site_id"]
        assert (parent, mid) in edges
        for ext, a in m["artifacts"].items():
            assert (mid, mid + ":" + ext) in edges
            assert nodes[mid + ":" + ext]["sha256"] == a["sha256"]
