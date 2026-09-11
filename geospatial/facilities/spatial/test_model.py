"""Mutation checks for coordinated stacks, physical scope and atlas completeness."""

import importlib.util
from pathlib import Path
import sys
import pytest

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location("spatial_model_tests", BASE / "model.py")
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


@pytest.fixture
def data():
    return model.build_model()


def test_population_scope(data):
    assert len(data["sites"]) == 19
    buildings = [b for s in data["sites"] for b in s["buildings"]]
    assert len(buildings) == 18
    assert sum(len(b["floors"]) for b in buildings) == 25
    assert len(data["room_schedule"]) == 236
    assert all(not s["georeferenced"] and s["geographic_transform"] is None for s in data["sites"])


def test_bad_stack_fails(data):
    data["sites"][0]["buildings"][0]["floors"][0]["z_m"] = 1
    with pytest.raises(ValueError, match="stack"):
        model.validate(data)


def test_room_outside_fails(data):
    data["sites"][0]["buildings"][0]["floors"][0]["rooms"][0]["rect_m"][0] = 100000
    with pytest.raises(ValueError, match="outside"):
        model.validate(data)


def test_duplicate_id_fails(data):
    data["sites"][1]["id"] = data["sites"][0]["id"]
    with pytest.raises(ValueError, match="Duplicate"):
        model.validate(data)


def test_floorplate_area_fails(data):
    data["sites"][0]["buildings"][0]["floors"][0]["gross_area_m2"] += 10
    with pytest.raises(ValueError, match="area"):
        model.validate(data)


def test_no_invented_external_buildings(data):
    for s in data["sites"]:
        if s["id"] in ("SH-SITE-0028", "SH-SITE-0029"):
            assert not s["buildings"]
    for s in data["sites"]:
        for b in s["buildings"]:
            if s["id"] != "SH-SITE-0001":
                assert all(
                    r["geometry_role"] == "program_zone" for f in b["floors"] for r in f["rooms"]
                )
