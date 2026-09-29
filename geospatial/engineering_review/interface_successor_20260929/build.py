"""Reperform corrected synthetic rail/site interfaces and explicit rights gaps."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TO_UTM = Transformer.from_crs(4326, 26913, always_xy=True).transform


def tangent_angle_deg(parent, branch, parent_chainage: float) -> float:
    """Sample a five-metre plan tangent; this is not a switch specification."""
    step = min(5.0, branch.length / 10)
    a = branch.interpolate(0)
    b = branch.interpolate(step)
    before = parent.interpolate(max(0.0, parent_chainage - step / 2))
    after = parent.interpolate(min(parent.length, parent_chainage + step / 2))
    av = (b.x - a.x, b.y - a.y)
    pv = (after.x - before.x, after.y - before.y)
    cosine = sum(x * y for x, y in zip(av, pv, strict=True)) / (math.hypot(*av) * math.hypot(*pv))
    return round(math.degrees(math.acos(min(1.0, max(-1.0, abs(cosine))))), 3)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text())


def build() -> dict:
    source = json.loads((HERE / "source.json").read_text())
    if (
        source["state"] != "SYNTHETIC_ENGINEERING_INTERFACE_REPERFORMANCE_NOT_REAL_CONSTRUCTION"
        or source["proposed_lead_state"] != "OUT_OF_SERVICE_NOT_ASSET_OR_CASH"
        or source["real_title_or_access_state"] != "NOT_SUPPLIED"
        or source["external_customer_footprint_state"] != "UNKNOWN_RESTRICTED_PRECISION"
        or source["no_mine_spur"] is not True
        or source["finished_uranium_custody_authorized"] is not False
    ):
        raise ValueError("Rail/site design or rights state changed")
    for relative, expected in source["input_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Changed pinned interface input: {relative}")
    operations = load("industrial/source/operations.json")
    selector = load("industrial/successors/rail_2026_09_29/source.json")
    candidate = load("geospatial/engineering_review/COMPENSATED_40_MILE_CANDIDATE.json")
    candidate_geo = load("geospatial/engineering_review/COMPENSATED_40_MILE_CANDIDATE.geojson")
    old_screen = load("geospatial/engineering_review/TRACK_SITE_INTERFACE_SCREEN.json")
    facility_geo = load("geospatial/geojson/industrial_facilities.geojson")
    track_geo = load("geospatial/geojson/industrial_tracks.geojson")
    rights_geo = load("geospatial/geojson/rail_trackage_rights.geojson")
    if rights_geo["features"]:
        raise ValueError("New trackage rights require actual instrument review")
    routes = {
        f["properties"]["source_route_id"]: transform(TO_UTM, shape(f["geometry"]))
        for f in candidate_geo["features"]
        if f["properties"].get("source_route_id") in {"BST-MAIN", "BST-EAST", "BST-MINERAL"}
    }
    if set(routes) != {"BST-MAIN", "BST-EAST", "BST-MINERAL"}:
        raise ValueError("Three route population differs")
    expected_miles = selector["route_miles"]
    if (
        not math.isclose(sum(expected_miles.values()), 40, abs_tol=1e-8)
        or any(
            candidate["candidate_route_miles"][route] != value
            for route, value in expected_miles.items()
        )
        or candidate["candidate_route_miles"]["total"] != 40
    ):
        raise ValueError("Dated synthetic 40-mile route selector differs")
    facilities = operations["facilities"]
    tracks = operations["track_segments"]
    structures = operations["structures"]
    if (len(facilities), len(tracks), len(structures)) != (12, 31, 26):
        raise ValueError("Accepted facility/track/structure population differs")
    facilities_by_id = {f["id"].removeprefix("IND-"): f for f in facility_geo["features"]}
    tracks_by_id = {f["id"].removeprefix("IND-"): f for f in track_geo["features"]}
    if len(facilities_by_id) != 12 or len(tracks_by_id) != 31:
        raise ValueError("Geometric facility or track IDs are not unique")
    if set(facilities_by_id) != {f["id"] for f in facilities} or set(tracks_by_id) != {
        t["id"] for t in tracks
    }:
        raise ValueError("Facility or track geometry does not join operations")
    route_tracks = [t for t in tracks if t.get("route_id") in routes]
    yard_tracks = [t for t in tracks if t.get("facility_id")]
    if len(route_tracks) != 11 or len(yard_tracks) != 20:
        raise ValueError("Eleven route and twenty yard track IDs required")
    yard_miles = sum(t["length_miles"] for t in yard_tracks)
    if not math.isclose(yard_miles, 4.18, abs_tol=1e-8):
        raise ValueError("Separate yard-track mileage differs")
    yard_counts = Counter(t["facility_id"] for t in yard_tracks)
    old_sites = {row["facility_id"]: row for row in old_screen["site_interfaces"]}
    if len(old_sites) != 12:
        raise ValueError("Predecessor site-interface population differs")
    lead_map = {
        "FAC-TAY-TERMINAL": "LEAD-TAY-TERMINAL",
        "FAC-TAY-WAREHOUSE": "LEAD-TAY-WAREHOUSE",
    }
    proposed_alignments = {row["id"]: row for row in candidate["candidate_alignments"]}
    if len(proposed_alignments) != 8 or not set(lead_map.values()) <= set(proposed_alignments):
        raise ValueError("Eight proposed branch/lead/ladder curves required")
    site_rows = []
    for facility in facilities:
        fid = facility["id"]
        feature = facilities_by_id[fid]
        if (
            feature["properties"]["owner"] != facility["owner"]
            or yard_counts[fid] != facility["track_count"]
        ):
            raise ValueError(f"Facility owner/track count differs: {fid}")
        envelope = transform(TO_UTM, shape(feature["geometry"]))
        nearest_distance, nearest_route = min(
            (envelope.distance(line), rid) for rid, line in routes.items()
        )
        site_tracks = [t for t in yard_tracks if t["facility_id"] == fid]
        gaps = [
            min(
                transform(TO_UTM, shape(tracks_by_id[t["id"]]["geometry"])).distance(line)
                for line in routes.values()
            )
            for t in site_tracks
        ]
        yard_gap = min(gaps) if gaps else None
        geometry_state = (
            "NO_RAIL_TRACK_IN_SOURCE"
            if yard_gap is None
            else "CORRECTED_ROUTE_GEOMETRY_TOUCHES_YARD"
            if yard_gap <= 1
            else "CORRECTED_ROUTE_REQUIRES_LOCAL_LEAD"
        )
        lead = proposed_alignments.get(lead_map.get(fid))
        if (lead is None) != (fid not in lead_map):
            raise ValueError("Local lead/facility assignment differs")
        if lead is not None and lead["joins_source_yard_track_id"] not in {
            t["id"] for t in site_tracks
        }:
            raise ValueError("Proposed lead does not join selected site track")
        site_rows.append(
            {
                "facility_id": fid,
                "source_owner_label": facility["owner"],
                "case_operating_state": facility["case_status"],
                "source_footprint_basis": facility["footprint_basis"],
                "source_footprint_precision": feature["properties"]["precision_class"],
                "source_yard_track_ids": [t["id"] for t in site_tracks],
                "nearest_corrected_route_id": nearest_route,
                "envelope_to_corrected_route_m": round(nearest_distance, 3),
                "minimum_yard_to_corrected_route_m": round(yard_gap, 3)
                if yard_gap is not None
                else None,
                "corrected_geometry_state": geometry_state,
                "predecessor_geometry_state": old_sites[fid]["mapped_route_join_state"],
                "proposed_local_lead_id": lead["id"] if lead else None,
                "proposed_local_lead_length_m": lead["candidate_projected_length_m"]
                if lead
                else None,
                "proposed_lead_outside_synthetic_envelope_m": lead[
                    "outside_synthetic_site_envelope_m"
                ]
                if lead
                else None,
                "proposed_lead_in_service": False,
                "real_deed_lease_easement_or_interchange_id": None,
                "real_property_or_access_verified": False,
            }
        )
    if Counter(r["corrected_geometry_state"] for r in site_rows) != {
        "CORRECTED_ROUTE_GEOMETRY_TOUCHES_YARD": 4,
        "CORRECTED_ROUTE_REQUIRES_LOCAL_LEAD": 2,
        "NO_RAIL_TRACK_IN_SOURCE": 6,
    }:
        raise ValueError("Corrected route/site join population differs")
    design_rows = []
    candidate_lines = {
        f["properties"].get("source_route_id")
        or f["properties"].get("source_yard_track_id"): transform(TO_UTM, shape(f["geometry"]))
        for f in candidate_geo["features"]
    }
    turnout_rows = []
    for aid, row in proposed_alignments.items():
        profile = row["profile"]
        stations = profile["stations"]
        if (
            len(stations) != profile["station_count"]
            or stations[0]["chainage_m"] != 0
            or any(
                left["chainage_m"] >= right["chainage_m"]
                for left, right in zip(stations, stations[1:])
            )
            or abs(stations[0]["formation_m"] - profile["start_elevation_m"]) > 0.001
            or abs(stations[-1]["formation_m"] - profile["end_elevation_m"]) > 0.001
        ):
            raise ValueError(f"Proposed continuous-grade profile population differs: {aid}")
        if (
            profile["maximum_grade_pct"] > 1.8 + 1e-9
            or max(profile["maximum_cut_m"], profile["maximum_fill_m"]) > 12 + 1e-9
        ):
            raise ValueError(f"Proposed screening profile exceeds case bound: {aid}")
        design_rows.append(
            {
                "alignment_id": aid,
                "role": row["role"],
                "minimum_sampled_plan_radius_m": row["minimum_sampled_radius_m"],
                "maximum_sampled_grade_pct": profile["maximum_grade_pct"],
                "maximum_screened_cut_m": profile["maximum_cut_m"],
                "maximum_screened_fill_m": profile["maximum_fill_m"],
                "profile_station_count": profile["station_count"],
                "proposed_length_m": row.get("candidate_projected_length_m"),
                "outside_synthetic_envelope_m": row.get("outside_synthetic_site_envelope_m"),
                "in_service": False,
                "construction_clearance_and_turnout_design_verified": False,
                "real_land_access_verified": False,
            }
        )
        line_id = row.get("joins_source_yard_track_id", aid)
        line = candidate_lines[line_id]
        if abs(stations[-1]["chainage_m"] - line.length) > 0.02:
            raise ValueError(f"Profile/plan chainage differs: {aid}")
        lead_parent_id = row.get("branches_from_lead_id")
        if lead_parent_id:
            parent_id = proposed_alignments[lead_parent_id]["joins_source_yard_track_id"]
        else:
            parent_id = "BST-MAIN"
        parent = candidate_lines[parent_id]
        junction = Point(line.coords[0])
        parent_chainage = parent.project(junction)
        start_gap = junction.distance(parent)
        if start_gap > 0.05:
            raise ValueError(f"Proposed turnout leaves parent line: {aid}")
        expected_chainage = row.get("compensated_main_junction_chainage_m") or row.get(
            "main_junction_chainage_m"
        )
        if expected_chainage is not None and abs(parent_chainage - expected_chainage) > 0.05:
            raise ValueError(f"Proposed turnout chainage differs: {aid}")
        target_id = row.get("joins_source_yard_track_id")
        target_gap = (
            Point(line.coords[-1]).distance(
                transform(TO_UTM, shape(tracks_by_id[target_id]["geometry"]))
            )
            if target_id
            else None
        )
        if target_gap is not None and target_gap > 0.05:
            raise ValueError(f"Proposed turnout does not join yard track: {aid}")
        turnout_rows.append(
            {
                "alignment_id": aid,
                "parent_alignment_id": lead_parent_id or "BST-MAIN",
                "parent_projected_chainage_m": round(parent_chainage, 3),
                "junction_gap_m": round(start_gap, 5),
                "sampled_five_metre_plan_tangent_angle_deg": tangent_angle_deg(
                    parent, line, parent_chainage
                ),
                "target_yard_track_id": target_id,
                "target_yard_gap_m": round(target_gap, 5) if target_gap is not None else None,
                "hardware_number_or_frog_angle": None,
                "flangeway_and_vehicle_swept_envelope_verified": False,
                "state": "PROPOSED_SYNTHETIC_CENTERLINE_CONNECTION_NOT_CONSTRUCTION_TURNOUT",
            }
        )
    candidate_structures = candidate["source_structure_reconciliation"]
    if len(candidate_structures) != 26 or {s["id"] for s in candidate_structures} != {
        s["id"] for s in structures
    }:
        raise ValueError("Twenty-six structure IDs do not crosswalk")
    if any(s["geometry_offset_m"] > 0.05 for s in candidate_structures):
        raise ValueError("Structure moved off corrected route")
    structure_by_id = {s["id"]: s for s in candidate_structures}
    structure_rows = []
    for structure in structures:
        crossing = structure_by_id[structure["id"]]
        structure_rows.append(
            {
                "structure_id": structure["id"],
                "kind": structure["kind"],
                "route_id": structure["route_id"],
                "source_milepost": structure["milepost"],
                "corrected_projected_chainage_m": crossing["candidate_projected_chainage_m"],
                "fixed_coordinate_offset_m": crossing["geometry_offset_m"],
                "source_span_m": structure["span_m"],
                "source_condition": structure["condition"],
                "source_inspection_date": structure.get("inspection_date"),
                "source_restriction": structure["restriction"],
                "waterway_label": structure.get("waterway"),
                "source_catchup_usd": structure.get("catchup_usd"),
                "hydrologic_catchment_and_design_flow": None,
                "hydraulic_capacity_verified": False,
                "field_clearance_or_load_rating_verified": False,
            }
        )
    if Counter(s["kind"] for s in structure_rows) != {
        "culvert": 20,
        "rail_bridge": 4,
        "third_party_highway_overbridge": 2,
    }:
        raise ValueError("Structure-kind population differs")
    external_endpoint_rows = []
    for route_id in ("BST-EAST", "BST-MINERAL"):
        feature = next(
            f
            for f in candidate_geo["features"]
            if f["properties"].get("source_route_id") == route_id
        )
        external_endpoint_rows.append(
            {
                "route_id": route_id,
                "synthetic_line_end_lon_lat": feature["geometry"]["coordinates"][-1],
                "external_client_parcel_or_footprint_id": None,
                "external_client_access_instrument_id": None,
                "precision_state": "ROUTE_ENDPOINT_ONLY_CLIENT_FOOTPRINT_UNKNOWN",
            }
        )
    return {
        "record_id": source["record_id"],
        "state": source["state"],
        "source_sha256": digest(HERE / "source.json"),
        "input_sha256": source["input_sha256"],
        "corrected_route_miles": {**expected_miles, "total": sum(expected_miles.values())},
        "separate_yard_track_miles": yard_miles,
        "population": {
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
        },
        "site_interfaces": site_rows,
        "proposed_design_screens": design_rows,
        "proposed_turnout_interfaces": turnout_rows,
        "structure_design_boundaries": structure_rows,
        "external_client_endpoints": external_endpoint_rows,
        "structure_crosswalk_ids": sorted(s["id"] for s in candidate_structures),
        "no_mine_spur": True,
        "finished_uranium_custody_authorized": False,
        "operating_route_or_finance_delta_from_this_register": 0,
        "limits": [
            "A corrected geometric touch is not a surveyed switch or executed access right.",
            "Two local leads and four terminal ladders remain proposed and out of service; their outside-envelope lengths are not parcel acquisitions.",
            "Vertical/plan screens lack turnout hardware, clearance, load, geotechnical, drainage, earthwork quantity and construction verification.",
            "Owner labels, synthetic acreage envelopes and the empty rights layer do not prove real title, lease, easement, UP interchange agreement or external customer footprint.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raw = (json.dumps(build(), indent=2, sort_keys=True) + "\n").encode()
    path = HERE / "register.json"
    if args.check:
        if path.read_bytes() != raw:
            raise ValueError("Stale corrected rail/site interface register")
    else:
        path.write_bytes(raw)
    print("PASS corrected 12-site/31-track interface register")


if __name__ == "__main__":
    main()
