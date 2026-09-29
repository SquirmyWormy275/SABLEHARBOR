"""Independent guardrails for the source-bound railway engineering review."""

import copy
import json
from pathlib import Path

import pytest

from geospatial.engineering_review import build as review
from geospatial.engineering_review import build_transitions as transitions
from geospatial.engineering_review import build_interfaces as interfaces


def test_historical_route_boundary_and_reconciled_mileage():
    result = review.build()
    epochs = {e["epoch"]: e for e in result["historical_epochs"]}
    assert len(epochs) == 7
    assert epochs["1898"]["route_miles"] is None
    assert epochs["1954"]["surviving_route_miles_low"] == 14
    assert epochs["1954"]["surviving_route_miles_high"] == 16
    assert not epochs["1898"]["georeferenced_alignment_available"]
    assert not epochs["1954"]["georeferenced_alignment_available"]
    assert epochs["1968"]["georeferenced_alignment_available"]
    assert sum(result["current_route_miles"].values()) == pytest.approx(40)
    assert result["net_1954_to_1968_route_growth_miles"] == pytest.approx(
        {"low": 17.34847676361104, "high": 19.34847676361104}
    )


def test_undesignated_vertical_breaks_remain_visible():
    profiles = {p["route_id"]: p for p in review.build()["profiles"]}
    assert set(profiles) == {"BST-MAIN", "BST-EAST", "BST-MINERAL", "ROAD-RW-01"}
    assert profiles["BST-EAST"]["maximum_adjacent_grade_change_percentage_points"] > 3
    assert profiles["ROAD-RW-01"]["maximum_adjacent_grade_change_percentage_points"] > 6
    assert profiles["BST-EAST"]["vertical_curve_design_status"] == "NOT_MODELED"
    assert (
        profiles["BST-MAIN"]["vertical_curve_design_status"]
        == "CONSTRAINED_PRELIMINARY_SCREEN_NOT_CERTIFIED"
    )
    assert profiles["BST-MAIN"]["station_count"] == 769


def test_rejects_backdated_current_geometry(monkeypatch):
    original = review._read

    def altered(path):
        data = copy.deepcopy(original(path))
        if path == review.SOURCES["network"]:
            data["features"][0]["properties"]["valid_from"] = "1954-07-01"
        return data

    monkeypatch.setattr(review, "_read", altered)
    with pytest.raises(ValueError, match="back-projected"):
        review.build()


def test_rejects_invalid_profile_and_stale_generated_review():
    with pytest.raises(ValueError, match="strictly increasing"):
        review.assess_profile("X", [0, 100, 100], [0, 0, 0], [0, 0, 0], 2, "GRADE_ONLY_L1")
    with pytest.raises(ValueError, match="exceeds"):
        review.assess_profile("X", [0, 100, 200], [0, 0, 0], [0, 10, 20], 2, "GRADE_ONLY_L1")
    output = Path(review.OUTPUT)
    assert json.loads(output.read_text()) == review.build()


def test_preliminary_successor_fixes_real_junction_gap_and_grade_breaks():
    old = {p["route_id"]: p for p in review.build()["profiles"]}
    new = {b["route_id"]: b for b in transitions.build()["branches"]}
    assert set(new) == {"BST-EAST", "BST-MINERAL"}
    assert new["BST-EAST"]["source_junction_elevation_gap_m"] == pytest.approx(3.667064, abs=1e-5)
    for route in new:
        candidate = new[route]
        assert candidate["status"] == "PROPOSED_PRELIMINARY_ENGINEERING_SCREEN"
        assert candidate["successor_junction_elevation_gap_m"] == pytest.approx(0)
        assert candidate["maximum_sampled_formation_grade_pct"] <= 1.8 + 1e-8
        assert candidate["maximum_discrete_curvature_fraction"] <= 1 + 1e-8
        assert (
            candidate["maximum_adjacent_grade_change_percentage_points"]
            < old[route]["maximum_adjacent_grade_change_percentage_points"]
        )
    assert new["BST-EAST"]["maximum_adjacent_grade_change_percentage_points"] < 0.81
    assert json.loads(transitions.OUTPUT.read_text()) == transitions.build()


def test_successor_rejects_bad_stations_and_infeasible_junction():
    stations = [
        {"chainage_m": 0, "ground_m": 0},
        {"chainage_m": 100, "ground_m": 0},
        {"chainage_m": 200, "ground_m": 0},
    ]
    with pytest.raises(ValueError, match="No feasible"):
        transitions.solve(stations, 100)
    stations[1]["chainage_m"] = 0
    with pytest.raises(ValueError, match="must increase"):
        transitions.solve(stations, 0)


def test_site_population_and_missing_local_leads_are_explicit():
    result = interfaces.build()
    assert result["facility_count"] == 12
    assert result["structure_count"] == 26
    assert result["yard_track_count"] == 20
    assert result["yard_track_miles_not_route_miles"] == pytest.approx(4.18)
    assert sum(result["route_miles_from_11_register_segments"].values()) == pytest.approx(40)
    assert result["trackage_rights_geometry_count"] == 0
    sites = {r["facility_id"]: r for r in result["site_interfaces"]}
    assert sites["FAC-TAY-TERMINAL"]["minimum_yard_track_to_route_m"] > 386
    assert sites["FAC-TAY-WAREHOUSE"]["minimum_yard_track_to_route_m"] > 624
    assert (
        sites["FAC-TAY-TERMINAL"]["mapped_route_join_state"]
        == "LOCAL_LEAD_NOT_GEOMETRICALLY_CONNECTED"
    )
    assert all(s["real_title_or_access_instrument_id"] is None for s in sites.values())
    assert json.loads(interfaces.OUTPUT.read_text()) == result


def test_site_screen_rejects_fabricated_track_count(monkeypatch):
    original = interfaces._load

    def altered(name):
        data = copy.deepcopy(original(name))
        if name == "operations":
            data["facilities"][0]["track_count"] += 1
        return data

    monkeypatch.setattr(interfaces, "_load", altered)
    with pytest.raises(ValueError, match="track count mismatch"):
        interfaces.build()
