import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).with_name("render.py")
spec = importlib.util.spec_from_file_location("architectural_sheet_renderer", PATH)
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def building():
    return {
        "id": "B",
        "name": "Test building",
        "status": "MODELLED",
        "geometry_role": "program_envelope",
        "height_basis": "Modelled height",
        "height_m": 4,
        "parapet_m": 0.8,
        "rect_m": [0, 0, 20, 10],
        "material": {"wall": "#aaaaaa", "glass": "#666666"},
        "floors": [
            {
                "id": "F",
                "name": "Level 1",
                "level": 1,
                "z_m": 0,
                "height_m": 4,
                "cores": [],
                "circulation": [],
                "rooms": [],
            }
        ],
    }


def sheet():
    return render._sheet({"name": "Test site"}, building(), "sections", "SH-MAP-TEST")


def test_program_zones_remain_dashed():
    b = building()
    b["floors"][0]["rooms"] = [
        {"id": "R01", "rect_m": [0, 0, 20, 10], "geometry_role": "program_zone"}
    ]
    s = sheet()
    render._section(s, b, "X", 440, {"slab_thickness_m": 0.3})
    assert 'stroke-dasharray="9 7"' in "".join(s.parts)
    assert 'fill="blue"' not in "".join(s.parts)
    assert render.D.FILLS["blue"] in "".join(s.parts)
    b["floors"][0]["rooms"][0]["geometry_role"] = "partitioned_room"
    s = sheet()
    render._section(s, b, "X", 440, {"slab_thickness_m": 0.3})
    assert 'stroke-dasharray="9 7"' not in "".join(s.parts)


def test_perimeter_core_prevents_proposed_glazing():
    a = {
        "facade_target_bay_m": 6,
        "facade_glazing_sill_m": 1,
        "facade_glazing_head_clearance_m": 0.7,
    }
    b = building()
    s = sheet()
    render._elevations(s, b, a)
    before = "".join(s.parts).count('fill="#666666"')
    b["floors"][0]["cores"] = [{"rect_m": [0, 0, 20, 10]}]
    s = sheet()
    render._elevations(s, b, a)
    assert before > 0 and 'fill="#666666"' not in "".join(s.parts)


def test_schedule_preserves_unknown_and_zero():
    f = {
        "rooms": [
            {
                "id": "R01",
                "name": "Working room",
                "area_m2": 5,
                "access": "staff",
                "assigned_desks": 0,
            }
        ],
        "gross_area_m2": 5,
        "planned_peak": None,
    }
    s = sheet()
    render._schedule(s, f)
    svg = "".join(s.parts)
    assert "0/?/?" in svg and "planned peak unknown" in svg


def test_schedule_overflow_is_rejected():
    f = {
        "rooms": [{"id": "R01", "name": "long name " * 100, "area_m2": 5, "access": "staff"}],
        "gross_area_m2": 5,
        "planned_peak": None,
    }
    with pytest.raises(ValueError, match="larger page"):
        render._schedule(sheet(), f)


def test_roof_does_not_assert_plant():
    s = sheet()
    render._roof(s, building(), {})
    assert "NO INSTALLED PLANT ASSERTED" in "".join(s.parts)
