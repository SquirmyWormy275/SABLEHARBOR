"""Reproducible railway geometry successor at synthetic worldbuilding precision.

The accepted industrial route, operating mileposts, track register and releases
are inputs. Candidate curves and formation are separate proposals. A candidate
does not establish a surveyed alignment, title, a railroad permit or service.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Geod, Transformer
from scipy.ndimage import map_coordinates
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
from shapely.geometry import LineString, Point, shape
from shapely.ops import substring, transform, unary_union

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name("WORLD_BUILDING_DESIGN.json")
GEOMETRY_OUTPUT = Path(__file__).with_name("WORLD_BUILDING_DESIGN.geojson")
TO_UTM = Transformer.from_crs(4326, 26913, always_xy=True).transform
TO_WGS84 = Transformer.from_crs(26913, 4326, always_xy=True).transform
GEOD = Geod(ellps="WGS84")
SOURCES = {
    "operations": "industrial/source/operations.json",
    "network": "industrial/source/geography/network.geojson",
    "main_profile": "industrial/source/geography/candidate_comparison.json",
    "tracks": "geospatial/geojson/industrial_tracks.geojson",
    "facilities": "geospatial/geojson/industrial_facilities.geojson",
    "waterbodies": "industrial/source/geography/wyoming_waterbodies.geojson",
    "local_roads": "industrial/source/geography/wyoming_local_roads.geojson",
    "dem": "industrial/source/geography/wyoming_screening_dem.tif",
}

# These are authored preliminary case parameters, in projected metres. A branch
# replaces its first source runout with a C1 cubic; the remaining source route is
# retained. Leads join source mainline to source yard-track end points. They are
# additional local-track candidates, not part of the accepted 40 route-miles.
CASES = {
    "BST-EAST": {"runout_m": 1200, "entry_handle_m": 600, "exit_handle_m": 250},
    "BST-MINERAL": {"runout_m": 800, "entry_handle_m": 350, "exit_handle_m": 250},
    "LEAD-TAY-TERMINAL": {
        "main_start_back_m": 300,
        "yard_track_id": "YARD-FAC-TAY-TERMINAL-legacygeneral",
        "entry_handle_m": 200,
        "exit_handle_m": 200,
    },
    "LEAD-TAY-WAREHOUSE": {
        "main_start_back_m": 0,
        "yard_track_id": "YARD-FAC-TAY-WAREHOUSE-warehouse",
        "entry_handle_m": 200,
        "exit_handle_m": 200,
    },
}
LADDER = (
    ("legacyteam", 60, 20),
    ("phase1generalA", 80, 30),
    ("phase1generalB", 100, 30),
    ("phase1liquid", 140, 90),
)


def _read(name: str):
    return json.loads((ROOT / SOURCES[name]).read_text())


def _report(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


def _geojson_line(line: LineString):
    geographic = transform(TO_WGS84, line)
    return {
        "type": "LineString",
        "coordinates": [[_report(lon, 9), _report(lat, 9)] for lon, lat in geographic.coords],
    }


def _unit(vector):
    value = np.asarray(vector, dtype=float)
    norm = np.linalg.norm(value)
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError("Zero or invalid tangent")
    return value / norm


def _xy(line: LineString, distance: float):
    return np.asarray(line.interpolate(distance).coords[0])


def _tangent(line: LineString, distance: float, step: float = 20):
    return _unit(_xy(line, min(line.length, distance + step)) - _xy(line, max(0, distance - step)))


def _bezier(start, entry_tangent, end, exit_tangent, entry_handle, exit_handle):
    p0 = np.asarray(start)
    p1 = p0 + _unit(entry_tangent) * entry_handle
    p3 = np.asarray(end)
    p2 = p3 - _unit(exit_tangent) * exit_handle
    u = np.linspace(0, 1, 301)[:, None]
    points = (1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u * u * p2 + u**3 * p3
    derivative = 3 * (1 - u) ** 2 * (p1 - p0) + 6 * (1 - u) * u * (p2 - p1) + 3 * u * u * (p3 - p2)
    second = 6 * (1 - u) * (p2 - 2 * p1 + p0) + 6 * u * (p3 - 2 * p2 + p1)
    cross = abs(derivative[:, 0] * second[:, 1] - derivative[:, 1] * second[:, 0])
    radius = (derivative[:, 0] ** 2 + derivative[:, 1] ** 2) ** 1.5 / np.maximum(cross, 1e-12)
    line = LineString([tuple(point) for point in points])
    return line, float(np.min(radius))


def solve_continuous_profile(
    chainage,
    ground,
    start_elevation,
    end_elevation,
    start_grade=None,
    end_grade=None,
    vertical_radius_proxy_m=10000,
    grade_limit=0.018,
    cut_fill_limit_m=12,
):
    """L1 formation optimum with C1 piecewise-quadratic elevation.

    The derivative (grade) interpolates linearly between node grades; its
    integral exactly equals each station elevation difference. This is a
    continuous-grade preliminary profile, not a rail-design certification.
    """
    x = np.asarray(chainage, dtype=float)
    g = np.asarray(ground, dtype=float)
    n = len(x)
    if n < 3 or len(g) != n or not np.isfinite(x).all() or not np.isfinite(g).all():
        raise ValueError("Invalid profile stations")
    if abs(x[0]) > 1e-8 or (np.diff(x) <= 0).any():
        raise ValueError("Profile chainage must increase from zero")
    rows = lil_matrix((2 * n + 2 * (n - 1), 3 * n))
    limits = np.zeros(rows.shape[0])
    equalities = lil_matrix((n - 1, 3 * n))
    index = 0
    for i, elevation in enumerate(g):
        rows[index, i] = 1
        rows[index, 2 * n + i] = -1
        limits[index] = elevation
        index += 1
        rows[index, i] = -1
        rows[index, 2 * n + i] = -1
        limits[index] = -elevation
        index += 1
    for i, interval in enumerate(np.diff(x)):
        for sign in (1, -1):
            rows[index, n + i + 1] = sign
            rows[index, n + i] = -sign
            limits[index] = interval / vertical_radius_proxy_m
            index += 1
        equalities[i, i + 1] = 1
        equalities[i, i] = -1
        equalities[i, n + i] = -interval / 2
        equalities[i, n + i + 1] = -interval / 2
    bounds = [(float(v - cut_fill_limit_m), float(v + cut_fill_limit_m)) for v in g]
    bounds += [(-grade_limit, grade_limit)] * n + [(0, None)] * n
    bounds[0] = (float(start_elevation), float(start_elevation))
    if end_elevation is not None:
        bounds[n - 1] = (float(end_elevation), float(end_elevation))
    if start_grade is not None:
        bounds[n] = (float(start_grade), float(start_grade))
    if end_grade is not None:
        bounds[2 * n - 1] = (float(end_grade), float(end_grade))
    objective = np.r_[np.zeros(2 * n), np.ones(n)]
    result = linprog(
        objective,
        A_ub=rows.tocsr(),
        b_ub=limits,
        A_eq=equalities.tocsr(),
        b_eq=np.zeros(n - 1),
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        raise ValueError(f"Continuous-grade profile infeasible: {result.message}")
    elevation = result.x[:n]
    grade = result.x[n : 2 * n]
    integral_error = np.diff(elevation) - (grade[:-1] + grade[1:]) * np.diff(x) / 2
    if (
        max(abs(integral_error)) > 1e-7
        or max(abs(grade)) > grade_limit + 1e-8
        or max(abs(np.diff(grade) / np.diff(x))) > 1 / vertical_radius_proxy_m + 1e-8
        or max(abs(elevation - g)) > cut_fill_limit_m + 1e-8
    ):
        raise ValueError("Continuous-grade solution violates its declared constraints")
    return elevation, grade


def _profile_at(x, elevation, grade, station):
    i = max(0, min(len(x) - 2, int(np.searchsorted(x, station) - 1)))
    fraction = (station - x[i]) / (x[i + 1] - x[i])
    interval = x[i + 1] - x[i]
    z = elevation[i] + interval * (
        grade[i] * fraction + (grade[i + 1] - grade[i]) * fraction * fraction / 2
    )
    s = grade[i] + (grade[i + 1] - grade[i]) * fraction
    return float(z), float(s)


def _ground_at(line, dem, step_m):
    x = np.r_[np.arange(0, line.length, step_m), line.length]
    coordinates = [_xy(line, station) for station in x]
    pixel = [(~dem.transform) @ (float(p[0]), float(p[1])) for p in coordinates]
    # Inverse affine values are column/row at the pixel corner. Bilinear
    # screen samples are shifted to pixel centers, matching the pinned DEM.
    col = np.asarray([v[0] for v in pixel]) - 0.5
    row = np.asarray([v[1] for v in pixel]) - 0.5
    if (
        (row < 0).any()
        or (col < 0).any()
        or (row >= dem.height - 1).any()
        or (col >= dem.width - 1).any()
    ):
        raise ValueError("Candidate leaves the pinned DEM footprint")
    g = map_coordinates(dem.read(1), [row, col], order=1, mode="nearest")
    return x, g


def _profile_record(
    line, dem, start_elevation, end_elevation, start_grade, end_grade, radius, step_m=None
):
    x, ground = _ground_at(line, dem, step_m or (20 if line.length < 1000 else 80))
    elevation, grade = solve_continuous_profile(
        x, ground, start_elevation, end_elevation, start_grade, end_grade, radius
    )
    return {
        "station_count": len(x),
        "maximum_grade_pct": _report(max(abs(grade)) * 100),
        "maximum_cut_m": _report(max(ground - elevation)),
        "maximum_fill_m": _report(max(elevation - ground)),
        "start_elevation_m": _report(elevation[0]),
        "end_elevation_m": _report(elevation[-1]),
        "end_formation_minus_screen_ground_m": _report(elevation[-1] - ground[-1]),
        "start_grade_pct": _report(grade[0] * 100),
        "end_grade_pct": _report(grade[-1] * 100),
        "stations": [
            {
                "chainage_m": _report(a),
                "screen_ground_m": _report(b),
                "formation_m": _report(c),
                "grade_pct": _report(d * 100),
            }
            for a, b, c, d in zip(x, ground, elevation, grade)
        ],
        "continuous_grade_method": "C1 piecewise-quadratic elevation with linearly interpolated grade at nodes; L1 ground deviation minimum",
        "vertical_radius_proxy_m": radius,
    }


def build():
    operations = _read("operations")
    network = {
        f["id"]: transform(TO_UTM, shape(f["geometry"])) for f in _read("network")["features"]
    }
    tracks = {
        f["id"].removeprefix("IND-"): transform(TO_UTM, shape(f["geometry"]))
        for f in _read("tracks")["features"]
    }
    facilities = {
        f["id"].removeprefix("IND-"): transform(TO_UTM, shape(f["geometry"]))
        for f in _read("facilities")["features"]
    }
    if set(network) != {"BST-MAIN", "BST-EAST", "BST-MINERAL", "ROAD-RW-01"}:
        raise ValueError("Accepted network population changed")
    if (len(tracks), len(facilities), len(operations["structures"])) != (31, 12, 26):
        raise ValueError("Accepted track/site/structure population changed")
    water = unary_union(
        [transform(TO_UTM, shape(f["geometry"])) for f in _read("waterbodies")["features"]]
    )
    roads = {
        f["id"]: transform(TO_UTM, shape(f["geometry"])) for f in _read("local_roads")["features"]
    }
    main = network["BST-MAIN"]
    source_profile = next(
        c for c in _read("main_profile")["candidates"] if c["candidate_id"] == "TAYLOR-A"
    )["legacy_corridor"]
    stations = source_profile["ground_profile"]
    main_x = np.asarray([s["chainage_m"] for s in stations])
    main_g = np.asarray([s["elevation_m"] for s in stations])
    source_z = source_profile["vertical_design"]["track_elevations_m"]
    if abs(main.length - main_x[-1]) > 0.1:
        raise ValueError("Mainline geometry/profile chainage mismatch")
    main_z, main_s = solve_continuous_profile(main_x, main_g, source_z[0], source_z[-1])
    main_record = {
        "station_count": len(main_x),
        "maximum_grade_pct": _report(max(abs(main_s)) * 100),
        "maximum_cut_m": _report(max(main_g - main_z)),
        "maximum_fill_m": _report(max(main_z - main_g)),
        "maximum_source_formation_change_m": _report(max(abs(main_z - source_z))),
        "start_elevation_m": _report(main_z[0]),
        "end_elevation_m": _report(main_z[-1]),
        "vertical_radius_proxy_m": 10000,
        "continuous_grade_method": "C1 piecewise-quadratic elevation with linearly interpolated grade at nodes; L1 ground deviation minimum",
        "stations": [
            {
                "chainage_m": _report(a),
                "screen_ground_m": _report(b),
                "formation_m": _report(c),
                "grade_pct": _report(d * 100),
            }
            for a, b, c, d in zip(main_x, main_g, main_z, main_s)
        ],
    }
    features = []
    rows = []
    candidates = {}
    projected_source_branch_m = 0.0
    projected_candidate_branch_m = 0.0
    geodesic_source_branch_m = 0.0
    geodesic_candidate_branch_m = 0.0
    source_branch_chord_slack_m = 0.0
    with rasterio.open(ROOT / SOURCES["dem"]) as dem:
        if str(dem.crs) != "EPSG:26913":
            raise ValueError("Pinned DEM projection changed")
        for route in ("BST-EAST", "BST-MINERAL"):
            source_line = network[route]
            case = CASES[route]
            start = np.asarray(source_line.coords[0])
            junction = main.project(Point(start))
            if Point(start).distance(main) > 0.01:
                raise ValueError(f"{route} no longer meets mainline")
            runout = case["runout_m"]
            curve, radius = _bezier(
                start,
                _tangent(main, junction),
                _xy(source_line, runout),
                _tangent(source_line, runout),
                case["entry_handle_m"],
                case["exit_handle_m"],
            )
            remaining = substring(source_line, runout, source_line.length)
            line = LineString(list(curve.coords) + list(remaining.coords)[1:])
            if radius < 150 or curve.intersection(water).length > 1e-6 or not line.is_simple:
                raise ValueError(f"{route} violates horizontal or waterbody screen")
            start_z, start_s = _profile_at(main_x, main_z, main_s, junction)
            x, ground = _ground_at(line, dem, 80)
            profile = _profile_record(line, dem, start_z, float(ground[-1]), start_s, None, 10000)
            source_road_ids = sorted(
                id for id, road in roads.items() if not source_line.intersection(road).is_empty
            )
            candidate_road_ids = sorted(
                id for id, road in roads.items() if not line.intersection(road).is_empty
            )
            if candidate_road_ids != source_road_ids:
                raise ValueError(f"{route} changes pinned local-road crossing population")
            projected_source_branch_m += source_line.length
            projected_candidate_branch_m += line.length
            geodesic_source_branch_m += GEOD.geometry_length(transform(TO_WGS84, source_line))
            geodesic_candidate_branch_m += GEOD.geometry_length(transform(TO_WGS84, line))
            source_chord_m = Point(source_line.coords[0]).distance(Point(source_line.coords[-1]))
            source_slack_m = source_line.length - source_chord_m
            source_branch_chord_slack_m += source_slack_m
            row = {
                "id": route,
                "role": "PROPOSED_HORIZONTAL_AND_VERTICAL_ROUTE_SUCCESSOR",
                "source_projected_length_m": _report(source_line.length),
                "candidate_projected_length_m": _report(line.length),
                "candidate_minus_source_projected_m": _report(line.length - source_line.length),
                "source_endpoint_chord_m": _report(source_chord_m),
                "source_plan_tortuosity_slack_m": _report(source_slack_m),
                "main_junction_chainage_m": _report(junction),
                "curve_runout_source_m": runout,
                "curve_minimum_sampled_radius_m": _report(radius),
                "curve_waterbody_overlap_m": 0,
                "local_road_crossing_ids_preserved": candidate_road_ids,
                "profile": profile,
                "milepost_state": "SOURCE_MILEPOSTS_REQUIRE_RECHAINING_IF_ADOPTED",
                "real_land_access_state": "UNESTABLISHED",
            }
            rows.append(row)
            candidates[route] = line
            features.append(
                {
                    "type": "Feature",
                    "id": route + "-CANDIDATE",
                    "geometry": _geojson_line(line),
                    "properties": {
                        "source_route_id": route,
                        "case_status": row["role"],
                        "survey_status": "NOT_SURVEYED",
                    },
                }
            )
        for lead_id in ("LEAD-TAY-TERMINAL", "LEAD-TAY-WAREHOUSE"):
            case = CASES[lead_id]
            target_id = case["yard_track_id"]
            track = tracks[target_id]
            station = main.length - case["main_start_back_m"]
            end = np.asarray(track.coords[-1])
            yard_tangent = _unit(np.asarray(track.coords[0]) - end)
            line, radius = _bezier(
                _xy(main, station),
                _tangent(main, station),
                end,
                yard_tangent,
                case["entry_handle_m"],
                case["exit_handle_m"],
            )
            if radius < 100 or line.intersection(water).length > 1e-6 or not line.is_simple:
                raise ValueError(f"{lead_id} violates horizontal or waterbody screen")
            if line.intersection(main).length > 1e-6:
                raise ValueError(f"{lead_id} overlaps mainline away from its switch")
            start_z, start_s = _profile_at(main_x, main_z, main_s, station)
            x, ground = _ground_at(line, dem, 20)
            profile = _profile_record(line, dem, start_z, float(ground[-1]), start_s, 0, 2000)
            target_facility = target_id.split("YARD-")[1].rsplit("-", 1)[0]
            envelope = facilities[target_facility]
            row = {
                "id": lead_id,
                "role": "PROPOSED_ADDITIONAL_LOCAL_LEAD_NOT_ROUTE_MILES",
                "joins_source_yard_track_id": target_id,
                "main_junction_chainage_m": _report(station),
                "candidate_projected_length_m": _report(line.length),
                "minimum_sampled_radius_m": _report(radius),
                "outside_synthetic_site_envelope_m": _report(line.difference(envelope).length),
                "source_yard_track_end_gap_m": _report(Point(end).distance(main)),
                "waterbody_overlap_m": 0,
                "local_road_crossing_ids": sorted(
                    id for id, road in roads.items() if not line.intersection(road).is_empty
                ),
                "profile": profile,
                "real_land_access_state": "UNESTABLISHED_FOR_OUTSIDE_ENVELOPE",
                "internal_yard_ladder_state": "SOURCE_PARALLEL_TRACKS_LACK_SWITCH_GEOMETRY",
            }
            rows.append(row)
            candidates[lead_id] = line
            features.append(
                {
                    "type": "Feature",
                    "id": lead_id,
                    "geometry": _geojson_line(line),
                    "properties": {
                        "source_yard_track_id": target_id,
                        "case_status": row["role"],
                        "survey_status": "NOT_SURVEYED",
                    },
                }
            )
        terminal_lead = candidates["LEAD-TAY-TERMINAL"]
        lead_x, lead_ground = _ground_at(terminal_lead, dem, 20)
        main_station = main.length - CASES["LEAD-TAY-TERMINAL"]["main_start_back_m"]
        lead_start_z, lead_start_s = _profile_at(main_x, main_z, main_s, main_station)
        lead_z, lead_s = solve_continuous_profile(
            lead_x, lead_ground, lead_start_z, float(lead_ground[-1]), lead_start_s, 0, 2000
        )
        ladder_lines = []
        for name, back_m, handle_m in LADDER:
            target_id = f"YARD-FAC-TAY-TERMINAL-{name}"
            target = tracks[target_id]
            end = np.asarray(target.coords[-1])
            lead_station = terminal_lead.length - back_m
            ladder, radius = _bezier(
                _xy(terminal_lead, lead_station),
                _tangent(terminal_lead, lead_station),
                end,
                np.asarray(target.coords[0]) - end,
                handle_m,
                handle_m,
            )
            if radius < 30 or not ladder.is_simple or not ladder.intersection(water).is_empty:
                raise ValueError(f"{target_id} ladder curve fails horizontal screen")
            if any(not ladder.intersection(previous).is_empty for previous in ladder_lines):
                raise ValueError(f"{target_id} crosses an earlier ladder candidate")
            intersection = ladder.intersection(terminal_lead)
            if intersection.length > 1e-6 or ladder.distance(terminal_lead) > 1e-6:
                raise ValueError(f"{target_id} rejoins or overlaps the terminal lead")
            ladder_lines.append(ladder)
            start_z, start_s = _profile_at(lead_x, lead_z, lead_s, lead_station)
            profile = _profile_record(ladder, dem, start_z, None, start_s, 0, 1000, 10)
            row = {
                "id": f"LADDER-TAY-TERMINAL-{name}",
                "role": "PROPOSED_INTERNAL_YARD_LADDER_NOT_ROUTE_MILES",
                "joins_source_yard_track_id": target_id,
                "branches_from_lead_id": "LEAD-TAY-TERMINAL",
                "lead_branch_chainage_m": _report(lead_station),
                "candidate_projected_length_m": _report(ladder.length),
                "minimum_sampled_radius_m": _report(radius),
                "outside_synthetic_site_envelope_m": _report(
                    ladder.difference(facilities["FAC-TAY-TERMINAL"]).length
                ),
                "local_road_crossing_ids": sorted(
                    id for id, road in roads.items() if not ladder.intersection(road).is_empty
                ),
                "profile": profile,
                "real_land_access_state": "UNESTABLISHED_FOR_OUTSIDE_ENVELOPE",
                "source_track_formation_state": "NOT_RECORDED; PROPOSED LEVEL ENTRY",
            }
            rows.append(row)
            candidates[row["id"]] = ladder
            features.append(
                {
                    "type": "Feature",
                    "id": row["id"],
                    "geometry": _geojson_line(ladder),
                    "properties": {
                        "source_yard_track_id": target_id,
                        "case_status": row["role"],
                        "survey_status": "NOT_SURVEYED",
                    },
                }
            )
    structures = []
    route_miles = {"BST-MAIN": 33.34847676361104, "BST-EAST": 4, "BST-MINERAL": 2.65152323638896}
    for item in operations["structures"]:
        route = network[item["route_id"]]
        point = transform(TO_UTM, Point(item["lon_lat"]))
        station = route.project(point)
        derived_mp = station / route.length * route_miles[item["route_id"]]
        offset = point.distance(route)
        if offset > 0.1 or abs(derived_mp - item["milepost"]) > 0.001:
            raise ValueError(f"Source structure location/milepost mismatch: {item['id']}")
        candidate = candidates.get(item["route_id"], route)
        candidate_station = candidate.project(point)
        candidate_mp = candidate_station / candidate.length * route_miles[item["route_id"]]
        structures.append(
            {
                "id": item["id"],
                "route_id": item["route_id"],
                "kind": item["kind"],
                "source_milepost": _report(item["milepost"], 6),
                "source_geometry_offset_m": _report(offset),
                "source_milepost_difference": _report(derived_mp - item["milepost"], 6),
                "candidate_geometry_offset_m": _report(point.distance(candidate)),
                "candidate_milepost_if_original_route_extent_held": _report(candidate_mp, 6),
                "candidate_minus_source_milepost_if_extent_held": _report(
                    candidate_mp - item["milepost"], 6
                ),
                "new_route_design_state": "RECHAIN_AND_REDESIGN_IF_BRANCH_CANDIDATE_ADOPTED"
                if item["route_id"] != "BST-MAIN"
                else "SOURCE_LOCATION_RETAINED",
            }
        )
    if any(x["id"].startswith("LEAD") for x in structures):
        raise ValueError("Lead should not be represented as an accepted source structure")
    report = {
        "schema": "rail-worldbuilding-design-candidate-v1",
        "source_paths": SOURCES,
        "source_sha256": {
            name: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for name, path in SOURCES.items()
        },
        "projection": "EPSG:26913",
        "status": "PROPOSED_DERIVED_SYNTHETIC_ENGINEERING_NOT_ACCEPTED_OPERATING_SOURCE",
        "authored_case_parameters": CASES,
        "authored_terminal_ladder_parameters": [
            {
                "target_track_suffix": name,
                "switch_back_from_terminal_lead_end_m": back,
                "both_bezier_handles_m": handle,
            }
            for name, back, handle in LADDER
        ],
        "accepted_source_population": {
            "route_miles": 40,
            "route_tracks": 11,
            "yard_tracks": 20,
            "facilities": 12,
            "structures": 26,
        },
        "candidate_measurement_bridge": {
            "accepted_geodesic_route_miles": 40,
            "source_branch_projected_length_m": _report(projected_source_branch_m),
            "candidate_branch_projected_length_m": _report(projected_candidate_branch_m),
            "projected_branch_length_increase_m": _report(
                projected_candidate_branch_m - projected_source_branch_m
            ),
            "source_branch_plan_tortuosity_slack_m": _report(source_branch_chord_slack_m),
            "candidate_increase_beyond_all_source_chord_slack_m": _report(
                projected_candidate_branch_m
                - projected_source_branch_m
                - source_branch_chord_slack_m
            ),
            "candidate_geodesic_route_miles": _report(
                40 + (geodesic_candidate_branch_m - geodesic_source_branch_m) / 1609.344, 6
            ),
            "geodesic_route_mile_increase": _report(
                (geodesic_candidate_branch_m - geodesic_source_branch_m) / 1609.344, 6
            ),
            "source_40_mile_status": "UNCHANGED_ACCEPTED_OPERATING_SOURCE; CANDIDATE_REQUIRES_ROUTE_SOURCE_DISPOSITION",
        },
        "mainline_continuous_grade_candidate": main_record,
        "candidate_alignments": rows,
        "source_structure_reconciliation": structures,
        "historical_alignment_disposition": [
            {
                "epoch": "1898",
                "geometry": None,
                "classification": "SOURCE_EVENT_UNLOCATED; NO SURVEY OR CONTEMPORANEOUS LINEWORK",
            },
            {
                "epoch": "1954",
                "geometry": None,
                "surviving_route_miles_interval": [14, 16],
                "classification": "SOURCE_EXTENT_INTERVAL_UNLOCATED; CURRENT 15-MILE SEGMENT NOT BACK-PROJECTED",
            },
            {
                "epoch": "abandoned",
                "geometry": None,
                "classification": "NO_ACCEPTED ABANDONED ALIGNMENT LINEWORK",
            },
        ],
        "decision_effects": [
            "Branch candidate lengths differ from accepted route lengths; operating route-mile, milepost, structure and scenario source cannot silently adopt them.",
            "The source branch endpoint chords leave less than 47 projected metres of total plan-length slack; straightening both source branches cannot absorb the candidate's 310.775-metre increase while their current endpoints stay fixed.",
            "Two proposed leads and four terminal ladder curves join source tracks; source 31-track register has no lead or ladder geometry and is not amended by this screen.",
            "Synthetic facility envelopes are not parcels. Exterior lead portions have no real title, easement, lease, construction or interchange instrument.",
            "Pinned DEM and waterbody intersection screens do not establish subsurface, flood, wetlands, drainage, utilities, road clearances, earthwork volume or structural design.",
            "C1 grade and sampled plan radius are worldbuilding checks, not civil/rail professional certification or authority to operate.",
        ],
    }
    geometry = {"type": "FeatureCollection", "features": features}
    return report, geometry


def main():
    report, geometry = build()
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    GEOMETRY_OUTPUT.write_text(json.dumps(geometry, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
