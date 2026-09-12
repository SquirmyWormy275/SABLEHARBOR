"""Stable-ID changes drive impact, not list order or imaginary historical heights."""

import copy
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "spatial_compare", Path(__file__).with_name("compare.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    return {
        "revision": "r1",
        "sites": [
            {
                "id": "S",
                "name": "Site",
                "status": "concept",
                "buildings": [
                    {
                        "id": "B",
                        "name": "Building",
                        "rect_m": [0, 0, 20, 10],
                        "height_m": 4,
                        "links": {"sections": "B-section.svg"},
                        "floors": [
                            {
                                "id": "F",
                                "name": "Floor",
                                "height_m": 4,
                                "z_m": 0,
                                "links": {"svg": "F.svg"},
                                "rooms": [
                                    {
                                        "id": "R",
                                        "name": "Room",
                                        "rect_m": [0, 0, 10, 10],
                                        "access": "public",
                                        "assigned_desks": 4,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }


def room(model):
    return model["sites"][0]["buildings"][0]["floors"][0]["rooms"][0]


def test_no_change_and_no_fake_overlay():
    model = fixture()
    result = module.compare_models(model, copy.deepcopy(model))
    assert result["summary"]["changes"] == 0
    assert result["comparisons"][0]["overlays"] == []


@pytest.mark.parametrize(
    "field,value,category",
    [
        ("rect_m", [1, 0, 10, 10], "geometry"),
        ("access", "restricted", "access"),
        ("assigned_desks", 6, "capacity"),
        ("name", "New name", "name"),
        ("status", "proposed", "status"),
    ],
)
def test_room_changes_have_actual_floor_links(field, value, category):
    before = fixture()
    after = copy.deepcopy(before)
    room(after)[field] = value
    result = module.compare_models(before, after)
    change = result["comparisons"][0]["changes"][0]
    assert change["id"] == "R" and change["field"] == field and change["category"] == category
    assert "F.svg" in change["affected_maps"]
    overlay = result["comparisons"][0]["overlays"][0]
    assert overlay["floor_id"] == "F"
    assert (
        overlay["before_rooms"][0][field] != overlay["after_rooms"][0][field]
        if field in room(before)
        else overlay["after_rooms"][0][field] == value
    )


def test_height_change_impacts_child_floor():
    before = fixture()
    after = copy.deepcopy(before)
    after["sites"][0]["buildings"][0]["height_m"] = 5
    result = module.compare_models(before, after)
    assert result["comparisons"][0]["changes"][0]["category"] == "height"
    assert "F.svg" in result["comparisons"][0]["changes"][0]["affected_maps"]
    assert result["summary"]["affected_floors"] == 1


@pytest.mark.parametrize("remove", [True, False])
def test_floor_addition_removal(remove):
    full = fixture()
    empty = copy.deepcopy(full)
    empty["sites"][0]["buildings"][0]["floors"] = []
    result = module.compare_models(full, empty) if remove else module.compare_models(empty, full)
    changes = result["comparisons"][0]["changes"]
    assert {c["id"] for c in changes} == {"F", "R"}
    assert all(c["field"] == ("__removed__" if remove else "__added__") for c in changes)
    overlay = result["comparisons"][0]["overlays"][0]
    assert (overlay["after_rooms"] if remove else overlay["before_rooms"]) == []


@pytest.mark.parametrize("missing", [True, False])
def test_missing_and_duplicate_ids_fail(missing):
    before = fixture()
    after = copy.deepcopy(before)
    if missing:
        room(after).pop("id")
    else:
        room(after)["id"] = "F"
    with pytest.raises(ValueError, match="stable"):
        module.compare_models(before, after)


def test_overlay_export_exclusive_and_escaped(tmp_path):
    before = fixture()
    after = copy.deepcopy(before)
    room(after)["rect_m"] = [2, 0, 10, 10]
    result = module.compare_models(before, after)
    paths = module.export_overlays(result, tmp_path)
    text = Path(paths[0]).read_text()
    assert "Red dashed: before" in text and "<rect" in text
    with pytest.raises(FileExistsError):
        module.export_overlays(result, tmp_path)


def test_real_baseline_is_git_verified():
    result = module.build_comparison(Path(__file__).resolve().parents[3])
    evidence = result["baseline_evidence"]
    assert evidence["accepted_commit"] == module.BASELINE
    assert "geospatial/facilities/source/campus.json" in evidence["git_blob_sha256"]
    assert evidence["baseline_floor_geometry_equal"]
    assert result["summary"]["changes"] == 0
    assert result["informational"][0]["kind"] == "NEW_ARCHITECTURAL_ASSUMPTIONS"
