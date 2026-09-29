"""The adopted 40-mile route is reconciled to sites without inventing rights."""

import json
from pathlib import Path

import pytest

from geospatial.engineering_review.interface_successor_20260929 import build as interfaces

HERE = Path(__file__).resolve().parents[1] / "engineering_review/interface_successor_20260929"


def test_corrected_route_site_register_reproduces_and_preserves_gates():
    result = interfaces.build()
    assert result == json.loads((HERE / "register.json").read_text())
    assert result["population"] == {
        "facilities": 12,
        "track_register": 31,
        "route_tracks": 11,
        "yard_tracks": 20,
        "structures": 26,
        "proposed_curves": 8,
        "proposed_turnout_interfaces": 8,
        "culverts": 20,
        "rail_bridges": 4,
        "third_party_highway_overbridges": 2,
        "real_trackage_rights_geometries": 0,
    }
    assert result["corrected_route_miles"]["total"] == 40
    assert result["separate_yard_track_miles"] == pytest.approx(4.18)
    assert result["no_mine_spur"] is True
    assert result["finished_uranium_custody_authorized"] is False
    assert result["operating_route_or_finance_delta_from_this_register"] == 0
    assert len(result["structure_crosswalk_ids"]) == 26
    assert all(not s["real_property_or_access_verified"] for s in result["site_interfaces"])
    assert all(not s["proposed_lead_in_service"] for s in result["site_interfaces"])
    assert all(
        e["external_client_parcel_or_footprint_id"] is None
        for e in result["external_client_endpoints"]
    )
    assert len(result["proposed_turnout_interfaces"]) == 8
    assert all(t["junction_gap_m"] <= 0.00002 for t in result["proposed_turnout_interfaces"])
    assert all(
        t["target_yard_gap_m"] == 0
        for t in result["proposed_turnout_interfaces"]
        if t["target_yard_track_id"]
    )
    assert all(
        t["hardware_number_or_frog_angle"] is None
        and not t["flangeway_and_vehicle_swept_envelope_verified"]
        for t in result["proposed_turnout_interfaces"]
    )
    assert len(result["structure_design_boundaries"]) == 26
    assert all(
        not s["hydraulic_capacity_verified"] and not s["field_clearance_or_load_rating_verified"]
        for s in result["structure_design_boundaries"]
    )


def test_corrected_route_quantifies_two_missing_site_interfaces():
    sites = {r["facility_id"]: r for r in interfaces.build()["site_interfaces"]}
    assert (
        sites["FAC-TAY-TERMINAL"]["corrected_geometry_state"]
        == "CORRECTED_ROUTE_REQUIRES_LOCAL_LEAD"
    )
    assert sites["FAC-TAY-TERMINAL"]["minimum_yard_to_corrected_route_m"] == 387.457
    assert sites["FAC-TAY-TERMINAL"]["proposed_lead_outside_synthetic_envelope_m"] == 467.848
    assert sites["FAC-TAY-WAREHOUSE"]["minimum_yard_to_corrected_route_m"] == 624.202
    assert sites["FAC-TAY-WAREHOUSE"]["proposed_lead_outside_synthetic_envelope_m"] == 711.04
    assert (
        sum(
            r["corrected_geometry_state"] == "CORRECTED_ROUTE_GEOMETRY_TOUCHES_YARD"
            for r in sites.values()
        )
        == 4
    )
    assert (
        sum(r["corrected_geometry_state"] == "NO_RAIL_TRACK_IN_SOURCE" for r in sites.values()) == 6
    )
    assert all(
        not d["construction_clearance_and_turnout_design_verified"]
        for d in interfaces.build()["proposed_design_screens"]
    )


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("real_title_or_access_state", "VERIFIED", "rights state"),
        ("proposed_lead_state", "IN_SERVICE", "rights state"),
        ("external_customer_footprint_state", "EXACT_PARCEL", "rights state"),
        ("no_mine_spur", False, "rights state"),
    ],
)
def test_unearned_right_or_service_claim_rejected(tmp_path, monkeypatch, field, value, error):
    source = json.loads((HERE / "source.json").read_text())
    source[field] = value
    (tmp_path / "source.json").write_text(json.dumps(source))
    monkeypatch.setattr(interfaces, "HERE", tmp_path)
    with pytest.raises(ValueError, match=error):
        interfaces.build()


def test_changed_pinned_geometry_rejected(tmp_path, monkeypatch):
    source = json.loads((HERE / "source.json").read_text())
    source["input_sha256"][
        "geospatial/engineering_review/COMPENSATED_40_MILE_CANDIDATE.geojson"
    ] = "0" * 64
    (tmp_path / "source.json").write_text(json.dumps(source))
    monkeypatch.setattr(interfaces, "HERE", tmp_path)
    with pytest.raises(ValueError, match="Changed pinned interface input"):
        interfaces.build()


def test_turnout_and_structure_population_is_exact():
    result = interfaces.build()
    turns = {t["alignment_id"]: t for t in result["proposed_turnout_interfaces"]}
    assert turns["BST-EAST"]["parent_alignment_id"] == "BST-MAIN"
    assert turns["BST-EAST"]["parent_projected_chainage_m"] == 23905.897
    assert turns["BST-MINERAL"]["parent_projected_chainage_m"] == 41602.086
    assert turns["LEAD-TAY-TERMINAL"]["parent_projected_chainage_m"] == 53079.762
    assert turns["LEAD-TAY-WAREHOUSE"]["parent_projected_chainage_m"] == 53379.762
    assert all(
        turns[aid]["parent_alignment_id"] == "LEAD-TAY-TERMINAL"
        for aid in turns
        if aid.startswith("LADDER-TAY-TERMINAL-")
    )
    structures = {s["structure_id"]: s for s in result["structure_design_boundaries"]}
    assert len(structures) == 26
    assert structures["CUL-01"]["source_span_m"] == 1.2
    assert structures["BR-02"]["source_restriction"].startswith("10mph")
    assert structures["HWY-I80-1"]["source_inspection_date"] is None
