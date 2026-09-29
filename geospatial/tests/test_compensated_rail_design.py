"""Checks for the fixed-control, exact-40-mile candidate network."""

import json

import pytest
from shapely.geometry import Point, shape
from shapely.ops import transform

from geospatial.engineering_review import build_compensated as compensated
from geospatial.engineering_review import build_worldbuilding_design as design


def test_compensated_case_preserves_exact_total_and_fixed_controls():
    report, geometry = compensated.build()
    assert report["status"].startswith("RECOMMENDED_PROPOSED")
    assert report["fixed_control_count"] == 25
    assert report["candidate_route_miles"]["total"] == 40
    exported_total = sum(
        design.GEOD.geometry_length(shape(feature["geometry"])) / 1609.344
        for feature in geometry["features"]
        if feature["id"] in {"BST-MAIN-COMPENSATED", "BST-EAST-CANDIDATE", "BST-MINERAL-CANDIDATE"}
    )
    assert exported_total == pytest.approx(40, abs=1e-8)
    assert report["candidate_route_miles"]["BST-MAIN"] == pytest.approx(33.155449, abs=1e-6)
    assert report["candidate_route_miles"]["BST-EAST"] == pytest.approx(4.136588, abs=1e-6)
    assert report["candidate_route_miles"]["BST-MINERAL"] == pytest.approx(2.707963, abs=1e-6)
    assert report["main_geodesic_shortening_m"] == pytest.approx(310.648, abs=0.001)
    assert report["compensated_main_minimum_sampled_radius_m"] >= 700
    assert (
        report["compensated_main_minimum_sampled_radius_m"]
        > report["source_main_minimum_sampled_radius_m"]
    )
    assert report["main_waterbody_overlap_m"] == 0
    assert len(report["source_structure_reconciliation"]) == 26
    assert all(row["geometry_offset_m"] == 0 for row in report["source_structure_reconciliation"])
    assert json.loads(compensated.OUTPUT.read_text()) == report
    assert json.loads(compensated.GEOMETRY_OUTPUT.read_text()) == geometry


def test_all_candidate_connections_and_formation_screens():
    report, geometry = compensated.build()
    rows = {row["id"]: row for row in report["candidate_alignments"]}
    assert len(rows) == 8
    assert len(geometry["features"]) == 9
    assert report["mainline_continuous_grade_candidate"]["maximum_grade_pct"] <= 1.8
    assert report["mainline_continuous_grade_candidate"]["maximum_cut_m"] <= 12
    assert report["mainline_continuous_grade_candidate"]["maximum_fill_m"] <= 12
    assert rows["LEAD-TAY-TERMINAL"]["outside_synthetic_site_envelope_m"] > 467
    assert rows["LEAD-TAY-WAREHOUSE"]["outside_synthetic_site_envelope_m"] > 711
    assert all(row["profile"]["maximum_grade_pct"] <= 1.8 for row in rows.values())
    assert all(row["profile"]["maximum_cut_m"] <= 12 for row in rows.values())
    assert all(row["profile"]["maximum_fill_m"] <= 12 for row in rows.values())
    assert all(row["real_land_access_state"].startswith("UNESTABLISHED") for row in rows.values())
    assert all(row["geometry"] is None for row in report["historical_alignment_disposition"])
    lines = {f["id"]: transform(design.TO_UTM, shape(f["geometry"])) for f in geometry["features"]}
    main = lines["BST-MAIN-COMPENSATED"]
    for branch_id in ("BST-EAST", "BST-MINERAL"):
        assert Point(lines[branch_id + "-CANDIDATE"].coords[0]).distance(main) < 0.001
    for lead_id in ("LEAD-TAY-TERMINAL", "LEAD-TAY-WAREHOUSE"):
        assert Point(lines[lead_id].coords[0]).distance(main) < 0.001


def test_insufficient_mainline_compensation_rejected(monkeypatch):
    monkeypatch.setattr(compensated, "SPAN_WEIGHTS", {})
    with pytest.raises(ValueError, match="cannot offset"):
        compensated.build()


def test_stale_prior_candidate_is_rejected(monkeypatch):
    original = design.OUTPUT
    monkeypatch.setattr(design, "OUTPUT", design.ROOT / "MAINTAINERS.md")
    with pytest.raises((ValueError, json.JSONDecodeError)):
        compensated.build()
    monkeypatch.setattr(design, "OUTPUT", original)
