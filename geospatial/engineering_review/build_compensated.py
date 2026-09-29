"""Preserve exact 40 route-miles in a fixed-control synthetic rail candidate.

The source mainline is shortened between fixed structure/junction controls by
smoothly blending toward each interval chord. The reduction exactly offsets
the branch turnout candidates. This remains proposed: operating route-specific
lengths, mileposts, assets and rights still require source adoption.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.optimize import brentq
from shapely.geometry import LineString, Point, shape
from shapely.ops import substring, transform, unary_union

from geospatial.engineering_review import build_worldbuilding_design as d

OUTPUT = Path(__file__).with_name("COMPENSATED_40_MILE_CANDIDATE.json")
GEOMETRY_OUTPUT = Path(__file__).with_name("COMPENSATED_40_MILE_CANDIDATE.geojson")

# Smooth changes vanish in both displacement and first derivative at control
# points; they cannot move source structures, branch junctions or end points.
# Each weight was bounded by the pinned road/water screens. Root scaling below
# selects the unique reduction needed to retain the exact 40-mile total.
SPAN_WEIGHTS = {
    ("CUL-01", "CUL-02"): 0.65,
    ("CUL-02", "BR-01"): 0.80,
    ("CUL-03", "CUL-04"): 0.12,
    ("CUL-04", "CUL-05"): 0.67,
    ("CUL-05", "CUL-06"): 0.69,
    ("CUL-06", "CUL-07"): 0.41,
    ("CUL-07", "BST-EAST"): 0.90,
    ("CUL-10", "CUL-11"): 0.68,
    ("CUL-11", "CUL-12"): 0.67,
    ("CUL-16", "END"): 0.65,
}


def _controls(main: LineString, operations: dict, network: dict):
    controls = [(0.0, "START"), (main.length, "END")]
    for structure in operations["structures"]:
        if structure["route_id"] == "BST-MAIN":
            point = transform(d.TO_UTM, Point(structure["lon_lat"]))
            controls.append((main.project(point), structure["id"]))
    for branch_id in ("BST-EAST", "BST-MINERAL"):
        controls.append((main.project(Point(network[branch_id].coords[0])), branch_id))
    controls.sort()
    if len(controls) != 25 or len({name for _, name in controls}) != len(controls):
        raise ValueError("Fixed-control population changed")
    return controls


def _blend(segment: LineString, weight: float):
    if weight == 0:
        return segment
    points = np.asarray(segment.coords)
    distance = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    fraction = distance / distance[-1]
    chord = (1 - fraction[:, None]) * points[0] + fraction[:, None] * points[-1]
    taper = weight * np.sin(np.pi * fraction) ** 2
    candidate = points * (1 - taper[:, None]) + chord * taper[:, None]
    return LineString([tuple(point) for point in candidate])


def _mainline(main: LineString, controls, scale: float):
    coordinates = []
    for (start, left), (end, right) in zip(controls, controls[1:]):
        segment = substring(main, start, end)
        weight = SPAN_WEIGHTS.get((left, right), 0) * scale
        candidate = _blend(segment, weight)
        coordinates.extend(
            list(candidate.coords) if not coordinates else list(candidate.coords)[1:]
        )
    return LineString(coordinates)


def _minimum_sampled_radius(line: LineString):
    points = np.asarray(line.coords)
    a = points[1:-1] - points[:-2]
    b = points[2:] - points[1:-1]
    c = points[2:] - points[:-2]
    cross = abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0])
    radius = (
        np.linalg.norm(a, axis=1)
        * np.linalg.norm(b, axis=1)
        * np.linalg.norm(c, axis=1)
        / (2 * np.maximum(cross, 1e-12))
    )
    return float(np.min(radius))


def build():
    operations = d._read("operations")
    network = {
        f["id"]: transform(d.TO_UTM, shape(f["geometry"])) for f in d._read("network")["features"]
    }
    source_main = network["BST-MAIN"]
    controls = _controls(source_main, operations, network)
    prior_report, prior_geometry = d.build()
    if (
        json.loads(d.OUTPUT.read_text()) != prior_report
        or json.loads(d.GEOMETRY_OUTPUT.read_text()) != prior_geometry
    ):
        raise ValueError("Prior worldbuilding candidate derivative is stale")
    prior = {f["id"]: transform(d.TO_UTM, shape(f["geometry"])) for f in prior_geometry["features"]}
    branch_lines = {id: prior[id + "-CANDIDATE"] for id in ("BST-EAST", "BST-MINERAL")}
    source_branch_length = sum(
        d.GEOD.geometry_length(transform(d.TO_WGS84, network[id])) for id in branch_lines
    )
    candidate_branch_length = sum(
        d.GEOD.geometry_length(transform(d.TO_WGS84, line)) for line in branch_lines.values()
    )
    branch_extra_m = candidate_branch_length - source_branch_length
    source_main_length = d.GEOD.geometry_length(transform(d.TO_WGS84, source_main))

    def remainder(scale):
        line = _mainline(source_main, controls, scale)
        return (
            source_main_length
            - d.GEOD.geometry_length(transform(d.TO_WGS84, line))
            - branch_extra_m
        )

    if remainder(0) >= 0 or remainder(1) <= 0:
        raise ValueError("Fixed-control spans cannot offset candidate branch length")
    scale = brentq(remainder, 0, 1, xtol=1e-12)
    main = _mainline(source_main, controls, scale)
    if not main.is_simple or _minimum_sampled_radius(main) < 700:
        raise ValueError("Compensated mainline fails topology or radius screen")
    water = unary_union(
        [transform(d.TO_UTM, shape(f["geometry"])) for f in d._read("waterbodies")["features"]]
    )
    roads = {
        f["id"]: transform(d.TO_UTM, shape(f["geometry"]))
        for f in d._read("local_roads")["features"]
    }
    source_road_ids = sorted(
        id for id, road in roads.items() if not source_main.intersection(road).is_empty
    )
    candidate_road_ids = sorted(
        id for id, road in roads.items() if not main.intersection(road).is_empty
    )
    if main.intersection(water).length > 1e-6 or candidate_road_ids != source_road_ids:
        raise ValueError("Compensated mainline changes pinned water/road crossing screen")
    if (
        Point(main.coords[0]).distance(Point(source_main.coords[0])) > 1e-6
        or Point(main.coords[-1]).distance(Point(source_main.coords[-1])) > 1e-6
    ):
        raise ValueError("Compensated mainline moves a source end point")
    tracks = {
        f["id"].removeprefix("IND-"): transform(d.TO_UTM, shape(f["geometry"]))
        for f in d._read("tracks")["features"]
    }
    facilities = {
        f["id"].removeprefix("IND-"): transform(d.TO_UTM, shape(f["geometry"]))
        for f in d._read("facilities")["features"]
    }
    if len(tracks) != 31 or len(facilities) != 12:
        raise ValueError("Accepted site/track population changed")
    source_profile = next(
        c for c in d._read("main_profile")["candidates"] if c["candidate_id"] == "TAYLOR-A"
    )["legacy_corridor"]
    source_z = source_profile["vertical_design"]["track_elevations_m"]
    features = [
        {
            "type": "Feature",
            "id": "BST-MAIN-COMPENSATED",
            "geometry": d._geojson_line(main),
            "properties": {
                "source_route_id": "BST-MAIN",
                "case_status": "PROPOSED_FIXED_CONTROL_40_MILE_CASE",
                "survey_status": "NOT_SURVEYED",
            },
        }
    ]
    rows = []
    with rasterio.open(d.ROOT / d.SOURCES["dem"]) as dem:
        main_x, main_ground = d._ground_at(main, dem, 70)
        main_z, main_grade = d.solve_continuous_profile(
            main_x, main_ground, source_z[0], source_z[-1]
        )
        main_profile = d._profile_record(
            main, dem, source_z[0], source_z[-1], None, None, 10000, 70
        )
        for route_id, line in branch_lines.items():
            source_start = Point(network[route_id].coords[0])
            if source_start.distance(main) > 0.001:
                raise ValueError(f"{route_id} junction moved")
            station = main.project(source_start)
            start_z, start_grade = d._profile_at(main_x, main_z, main_grade, station)
            _, ground = d._ground_at(line, dem, 80)
            profile = d._profile_record(
                line, dem, start_z, float(ground[-1]), start_grade, None, 10000, 80
            )
            rows.append(
                {
                    "id": route_id,
                    "role": "PROPOSED_BRANCH_WITH_COMPENSATED_MAINLINE",
                    "candidate_geodesic_route_miles": d._report(
                        d.GEOD.geometry_length(transform(d.TO_WGS84, line)) / 1609.344, 9
                    ),
                    "compensated_main_junction_chainage_m": d._report(station),
                    "minimum_sampled_radius_m": next(
                        r["curve_minimum_sampled_radius_m"]
                        for r in prior_report["candidate_alignments"]
                        if r["id"] == route_id
                    ),
                    "profile": profile,
                    "real_land_access_state": "UNESTABLISHED",
                }
            )
            features.append(
                {
                    "type": "Feature",
                    "id": route_id + "-CANDIDATE",
                    "geometry": d._geojson_line(line),
                    "properties": {
                        "source_route_id": route_id,
                        "case_status": "PROPOSED_FIXED_CONTROL_40_MILE_CASE",
                        "survey_status": "NOT_SURVEYED",
                    },
                }
            )
        lead_lines = {}
        for lead_id in ("LEAD-TAY-TERMINAL", "LEAD-TAY-WAREHOUSE"):
            case = d.CASES[lead_id]
            target = tracks[case["yard_track_id"]]
            station = main.length - case["main_start_back_m"]
            end = np.asarray(target.coords[-1])
            line, radius = d._bezier(
                d._xy(main, station),
                d._tangent(main, station),
                end,
                np.asarray(target.coords[0]) - end,
                case["entry_handle_m"],
                case["exit_handle_m"],
            )
            if radius < 100 or line.intersection(water).length > 1e-6 or not line.is_simple:
                raise ValueError(f"{lead_id} plan screen failed after compensation")
            start_z, start_grade = d._profile_at(main_x, main_z, main_grade, station)
            _, ground = d._ground_at(line, dem, 20)
            profile = d._profile_record(
                line, dem, start_z, float(ground[-1]), start_grade, 0, 2000, 20
            )
            facility_id = case["yard_track_id"].split("YARD-")[1].rsplit("-", 1)[0]
            lead_lines[lead_id] = line
            rows.append(
                {
                    "id": lead_id,
                    "role": "PROPOSED_LOCAL_LEAD_NOT_ROUTE_MILES",
                    "joins_source_yard_track_id": case["yard_track_id"],
                    "main_junction_chainage_m": d._report(station),
                    "candidate_projected_length_m": d._report(line.length),
                    "minimum_sampled_radius_m": d._report(radius),
                    "outside_synthetic_site_envelope_m": d._report(
                        line.difference(facilities[facility_id]).length
                    ),
                    "local_road_crossing_ids": sorted(
                        id for id, road in roads.items() if not line.intersection(road).is_empty
                    ),
                    "profile": profile,
                    "real_land_access_state": "UNESTABLISHED_FOR_OUTSIDE_ENVELOPE",
                }
            )
            features.append(
                {
                    "type": "Feature",
                    "id": lead_id,
                    "geometry": d._geojson_line(line),
                    "properties": {
                        "source_yard_track_id": case["yard_track_id"],
                        "case_status": "PROPOSED_FIXED_CONTROL_40_MILE_CASE",
                        "survey_status": "NOT_SURVEYED",
                    },
                }
            )
        terminal_lead = lead_lines["LEAD-TAY-TERMINAL"]
        lead_x, lead_ground = d._ground_at(terminal_lead, dem, 20)
        lead_station = main.length - d.CASES["LEAD-TAY-TERMINAL"]["main_start_back_m"]
        lead_start_z, lead_start_grade = d._profile_at(main_x, main_z, main_grade, lead_station)
        lead_z, lead_grade = d.solve_continuous_profile(
            lead_x, lead_ground, lead_start_z, float(lead_ground[-1]), lead_start_grade, 0, 2000
        )
        prior_ladders = []
        for name, back, handle in d.LADDER:
            target_id = f"YARD-FAC-TAY-TERMINAL-{name}"
            target = tracks[target_id]
            end = np.asarray(target.coords[-1])
            station = terminal_lead.length - back
            line, radius = d._bezier(
                d._xy(terminal_lead, station),
                d._tangent(terminal_lead, station),
                end,
                np.asarray(target.coords[0]) - end,
                handle,
                handle,
            )
            if (
                radius < 30
                or line.intersection(water).length > 1e-6
                or any(not line.intersection(previous).is_empty for previous in prior_ladders)
            ):
                raise ValueError(f"{target_id} ladder screen failed after compensation")
            prior_ladders.append(line)
            start_z, start_grade = d._profile_at(lead_x, lead_z, lead_grade, station)
            profile = d._profile_record(line, dem, start_z, None, start_grade, 0, 1000, 10)
            row_id = f"LADDER-TAY-TERMINAL-{name}"
            rows.append(
                {
                    "id": row_id,
                    "role": "PROPOSED_INTERNAL_YARD_LADDER_NOT_ROUTE_MILES",
                    "joins_source_yard_track_id": target_id,
                    "branches_from_lead_id": "LEAD-TAY-TERMINAL",
                    "candidate_projected_length_m": d._report(line.length),
                    "minimum_sampled_radius_m": d._report(radius),
                    "outside_synthetic_site_envelope_m": d._report(
                        line.difference(facilities["FAC-TAY-TERMINAL"]).length
                    ),
                    "profile": profile,
                    "real_land_access_state": "UNESTABLISHED_FOR_OUTSIDE_ENVELOPE",
                }
            )
            features.append(
                {
                    "type": "Feature",
                    "id": row_id,
                    "geometry": d._geojson_line(line),
                    "properties": {
                        "source_yard_track_id": target_id,
                        "case_status": "PROPOSED_FIXED_CONTROL_40_MILE_CASE",
                        "survey_status": "NOT_SURVEYED",
                    },
                }
            )
    structures = []
    candidate_routes = {"BST-MAIN": main, **branch_lines}
    for structure in operations["structures"]:
        point = transform(d.TO_UTM, Point(structure["lon_lat"]))
        route = candidate_routes[structure["route_id"]]
        offset = point.distance(route)
        if offset > 0.001:
            raise ValueError(f"Structure moved off candidate route: {structure['id']}")
        structures.append(
            {
                "id": structure["id"],
                "route_id": structure["route_id"],
                "source_milepost": d._report(structure["milepost"], 6),
                "candidate_projected_chainage_m": d._report(route.project(point)),
                "candidate_geodesic_route_miles": d._report(
                    d.GEOD.geometry_length(transform(d.TO_WGS84, route)) / 1609.344, 9
                ),
                "geometry_offset_m": d._report(offset),
                "source_milepost_state": "RECHAIN_REQUIRED_ON_SOURCE_ADOPTION",
            }
        )
    candidate_lengths = {
        id: d.GEOD.geometry_length(transform(d.TO_WGS84, line)) / 1609.344
        for id, line in candidate_routes.items()
    }
    total_miles = sum(candidate_lengths.values())
    if abs(total_miles - 40) > 1e-8:
        raise ValueError(f"Compensated route total is not 40 miles: {total_miles}")
    report = {
        "schema": "rail-fixed-control-40-mile-candidate-v1",
        "status": "RECOMMENDED_PROPOSED_SYNTHETIC_SOURCE_PATH_NOT_OPERATING_CANON",
        "source_sha256": {
            name: hashlib.sha256((d.ROOT / path).read_bytes()).hexdigest()
            for name, path in d.SOURCES.items()
        },
        "prior_candidate_sha256": hashlib.sha256(d.OUTPUT.read_bytes()).hexdigest(),
        "projection": "EPSG:26913",
        "geojson_coordinate_decimal_places": 10,
        "fixed_control_count": len(controls),
        "fixed_control_ids": [name for _, name in controls],
        "authored_span_weights": [
            {"from": a, "to": b, "maximum_weight": w} for (a, b), w in SPAN_WEIGHTS.items()
        ],
        "exact_length_scale": d._report(scale, 9),
        "source_route_miles": {
            "BST-MAIN": 33.34847676361104,
            "BST-EAST": 4,
            "BST-MINERAL": 2.65152323638896,
            "total": 40,
        },
        "candidate_route_miles": {
            **{id: d._report(value, 9) for id, value in candidate_lengths.items()},
            "total": d._report(total_miles, 9),
        },
        "source_main_projected_length_m": d._report(source_main.length),
        "candidate_main_projected_length_m": d._report(main.length),
        "main_projected_shortening_m": d._report(source_main.length - main.length),
        "main_geodesic_shortening_m": d._report(
            source_main_length - d.GEOD.geometry_length(transform(d.TO_WGS84, main))
        ),
        "compensated_main_minimum_sampled_radius_m": d._report(_minimum_sampled_radius(main)),
        "source_main_minimum_sampled_radius_m": d._report(_minimum_sampled_radius(source_main)),
        "main_local_road_crossing_ids_preserved": candidate_road_ids,
        "main_waterbody_overlap_m": 0,
        "mainline_continuous_grade_candidate": main_profile,
        "candidate_alignments": rows,
        "source_structure_reconciliation": structures,
        "historical_alignment_disposition": prior_report["historical_alignment_disposition"],
        "source_adoption_boundary": [
            "Exact 40 total route-miles are preserved, but route-specific lengths and mileposts differ from the accepted source and require its own reviewed successor.",
            "All fixed site endpoints, branch junction coordinates and 26 source structure coordinates stay fixed; all original local-road crossing IDs remain and pinned waterbody-polygon overlap stays zero.",
            "Two new Taylor local leads and four terminal ladder curves require track-register, asset, interentity, capital and site-access treatment before operating use.",
            "The 1898/1954/abandoned linework and real title/survey/external customer footprints are not supplied by this synthetic design candidate.",
            "The terrain/geometry screen is not a construction, load-rating, drainage, utilities, parcel or professional design approval.",
        ],
    }
    return report, {"type": "FeatureCollection", "features": features}


def main():
    report, geometry = build()
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    GEOMETRY_OUTPUT.write_text(json.dumps(geometry, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
