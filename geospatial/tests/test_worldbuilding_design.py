"""Independent population and physics guards for the proposed rail design case."""

import copy
import json
from pathlib import Path

import pytest
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform

from geospatial.engineering_review import build_worldbuilding_design as design


def test_proposed_design_has_explicit_source_mileage_and_access_boundary():
    report, geometry = design.build()
    assert report["accepted_source_population"] == {
        "route_miles": 40,
        "route_tracks": 11,
        "yard_tracks": 20,
        "facilities": 12,
        "structures": 26,
    }
    bridge = report["candidate_measurement_bridge"]
    assert bridge["candidate_geodesic_route_miles"] == pytest.approx(40.193028, abs=1e-6)
    assert bridge["projected_branch_length_increase_m"] == pytest.approx(310.775, abs=0.001)
    assert "UNCHANGED_ACCEPTED" in bridge["source_40_mile_status"]
    rows = {row["id"]: row for row in report["candidate_alignments"]}
    assert len(rows) == len(geometry["features"]) == 8
    assert {key for key in rows if key.startswith("LADDER-")} == {
        "LADDER-TAY-TERMINAL-legacyteam",
        "LADDER-TAY-TERMINAL-phase1generalA",
        "LADDER-TAY-TERMINAL-phase1generalB",
        "LADDER-TAY-TERMINAL-phase1liquid",
    }
    assert rows["LEAD-TAY-TERMINAL"]["outside_synthetic_site_envelope_m"] > 467
    assert rows["LEAD-TAY-WAREHOUSE"]["outside_synthetic_site_envelope_m"] > 711
    assert all(row["real_land_access_state"].startswith("UNESTABLISHED") for row in rows.values())
    assert all(record["geometry"] is None for record in report["historical_alignment_disposition"])
    assert json.loads(Path(design.OUTPUT).read_text()) == report
    assert json.loads(Path(design.GEOMETRY_OUTPUT).read_text()) == geometry


def test_candidate_curves_and_profiles_preserve_source_crossings_and_limits():
    report, geometry = design.build()
    rows = {row["id"]: row for row in report["candidate_alignments"]}
    assert report["mainline_continuous_grade_candidate"]["station_count"] == 769
    assert report["mainline_continuous_grade_candidate"]["maximum_grade_pct"] <= 1.8
    assert report["mainline_continuous_grade_candidate"]["maximum_source_formation_change_m"] < 0.62
    for route in ("BST-EAST", "BST-MINERAL"):
        row = rows[route]
        assert row["curve_minimum_sampled_radius_m"] >= 150
        assert row["curve_waterbody_overlap_m"] == 0
        assert row["profile"]["maximum_grade_pct"] <= 1.8
        assert row["profile"]["maximum_cut_m"] <= 12
        assert row["profile"]["maximum_fill_m"] <= 12
        assert len(row["local_road_crossing_ids_preserved"]) == (6 if route == "BST-EAST" else 3)
    for site in ("LEAD-TAY-TERMINAL", "LEAD-TAY-WAREHOUSE"):
        row = rows[site]
        assert row["minimum_sampled_radius_m"] >= 100
        assert row["waterbody_overlap_m"] == 0
        assert row["local_road_crossing_ids"] == []
        assert row["profile"]["end_grade_pct"] == 0
    for row in rows.values():
        assert row["profile"]["maximum_grade_pct"] <= 1.8
    assert len(report["source_structure_reconciliation"]) == 26
    assert all(
        row["source_geometry_offset_m"] == 0 for row in report["source_structure_reconciliation"]
    )
    assert (
        max(
            abs(row["source_milepost_difference"])
            for row in report["source_structure_reconciliation"]
        )
        < 0.001
    )
    assert all(
        row["candidate_geometry_offset_m"] == 0 for row in report["source_structure_reconciliation"]
    )


def test_terminal_ladder_topology_reaches_all_five_source_tracks_without_crossing():
    report, geometry = design.build()
    to_utm = Transformer.from_crs(4326, 26913, always_xy=True).transform
    lines = {
        feature["id"]: transform(to_utm, shape(feature["geometry"]))
        for feature in geometry["features"]
    }
    source = {
        feature["id"].removeprefix("IND-"): transform(to_utm, shape(feature["geometry"]))
        for feature in design._read("tracks")["features"]
    }
    main = transform(
        to_utm,
        shape(
            next(
                feature
                for feature in design._read("network")["features"]
                if feature["id"] == "BST-MAIN"
            )["geometry"]
        ),
    )
    for lead_id in ("LEAD-TAY-TERMINAL", "LEAD-TAY-WAREHOUSE"):
        row = next(x for x in report["candidate_alignments"] if x["id"] == lead_id)
        line = lines[lead_id]
        assert Point(line.coords[0]).distance(main) < 0.001
        assert Point(line.coords[-1]).distance(source[row["joins_source_yard_track_id"]]) < 0.001
    terminal_ids = [key for key in lines if key.startswith("LADDER-")]
    assert len(terminal_ids) == 4
    for id in terminal_ids:
        row = next(x for x in report["candidate_alignments"] if x["id"] == id)
        line = lines[id]
        assert Point(line.coords[0]).distance(lines["LEAD-TAY-TERMINAL"]) < 0.001
        assert Point(line.coords[-1]).distance(source[row["joins_source_yard_track_id"]]) < 0.001
        assert row["minimum_sampled_radius_m"] >= 30
    for i, first in enumerate(terminal_ids):
        for second in terminal_ids[i + 1 :]:
            assert lines[first].intersection(lines[second]).is_empty


def test_continuous_profile_solver_rejects_unsupported_or_infeasible_input():
    x = [0, 100, 200]
    g = [0, 0, 0]
    z, slope = design.solve_continuous_profile(x, g, 0, 0, 0, 0)
    assert max(abs(z)) < 1e-8
    assert max(abs(slope)) < 1e-8
    with pytest.raises(ValueError, match="chainage"):
        design.solve_continuous_profile([0, 100, 100], g, 0, 0)
    with pytest.raises(ValueError, match="infeasible"):
        design.solve_continuous_profile(x, g, 50, 0)


def test_missing_source_track_is_rejected(monkeypatch):
    original = design._read

    def missing(name):
        result = copy.deepcopy(original(name))
        if name == "tracks":
            result["features"].pop()
        return result

    monkeypatch.setattr(design, "_read", missing)
    with pytest.raises(ValueError, match="population changed"):
        design.build()
