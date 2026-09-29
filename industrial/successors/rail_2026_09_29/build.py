#!/usr/bin/env python3
"""Materialize the dated 40-mile railway geometry successor without editing locked inputs."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from pyproj import Geod, Transformer
from shapely.geometry import LineString, Point, shape
from shapely.ops import substring, transform, unary_union

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from industrial.planning import forecast, operating_model  # noqa: E402
from industrial.tools import build_operations  # noqa: E402

HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "industrial/source"
CANDIDATE = ROOT / "geospatial/engineering_review/COMPENSATED_40_MILE_CANDIDATE.json"
CANDIDATE_GEO = CANDIDATE.with_suffix(".geojson")
OUT = ROOT / "industrial/generated/successors/rail_2026_09_29"
ROUTES = ("BST-MAIN", "BST-EAST", "BST-MINERAL")
GEOD = Geod(ellps="WGS84")
FWD = Transformer.from_crs(4326, 26913, always_xy=True)
BACK = Transformer.from_crs(26913, 4326, always_xy=True)
MAP_FWD = Transformer.from_crs(4326, 26912, always_xy=True)
METRES_PER_MILE = 1609.344


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # The planning allocator uses source map insertion order for deterministic
    # largest-remainder tie breaks. Preserve it in the durable selector outputs.
    path.write_text(json.dumps(data, indent=2) + "\n")


def checked_inputs() -> tuple[dict, dict, dict, dict]:
    spec = json.loads((HERE / "source.json").read_text())
    paths = {
        "original_operations_sha256": SOURCE / "operations.json",
        "original_network_sha256": SOURCE / "geography/network.geojson",
        "candidate_report_sha256": CANDIDATE,
        "candidate_geojson_sha256": CANDIDATE_GEO,
    }
    for key, path in paths.items():
        if digest(path) != spec[key]:
            raise ValueError(f"Pinned railway input changed: {key}")
    for key in ("candidate_report_sha256", "candidate_geojson_sha256"):
        path = paths[key]
        accepted = subprocess.check_output(
            ["git", "show", f"{spec['candidate_acceptance_commit']}:{path.relative_to(ROOT)}"],
            cwd=ROOT,
        )
        if hashlib.sha256(accepted).hexdigest() != spec[key]:
            raise ValueError(f"Accepted candidate commit does not contain {key}")
    report = json.loads(CANDIDATE.read_text())
    if report["candidate_route_miles"] != {**spec["route_miles"], "total": 40.0}:
        raise ValueError("Candidate route split differs from the dated selector")
    candidate = json.loads(CANDIDATE_GEO.read_text())
    features = {
        f["properties"]["source_route_id"]: f
        for f in candidate["features"]
        if f["properties"].get("source_route_id") in ROUTES
    }
    if set(features) != set(ROUTES):
        raise ValueError("A proposed route is missing or duplicated")
    return spec, report, features, json.loads((SOURCE / "operations.json").read_text())


def station(coords: list, target_mile: float, route_miles: float) -> list[float]:
    """Locate a newly authored district boundary on the candidate centerline."""
    lengths = [GEOD.inv(*a, *b)[2] for a, b in zip(coords, coords[1:], strict=False)]
    remaining = target_mile / route_miles * sum(lengths)
    for (a, b), length in zip(zip(coords, coords[1:], strict=False), lengths, strict=True):
        if remaining <= length:
            azimuth = GEOD.inv(*a, *b)[0]
            lon, lat, _ = GEOD.fwd(*a, azimuth, remaining)
            return [round(lon, 10), round(lat, 10)]
        remaining -= length
    if abs(remaining) < 0.001:
        return coords[-1]
    raise ValueError("Maintenance station exceeds route")


def rechain(coords: list, point: list) -> tuple[float, float]:
    projected = LineString([FWD.transform(*xy) for xy in coords])
    anchor = Point(FWD.transform(*point))
    chain = projected.project(anchor)
    portion = substring(projected, 0, chain)
    geographic = LineString([BACK.transform(*xy) for xy in portion.coords])
    return GEOD.geometry_length(geographic) / METRES_PER_MILE, projected.distance(anchor)


def network_successor(old_network: dict, features: dict, spec: dict) -> dict:
    network = copy.deepcopy(old_network)
    for feature in network["features"]:
        route = feature["id"]
        if route not in ROUTES:
            continue
        feature["geometry"] = copy.deepcopy(features[route]["geometry"])
        props = feature["properties"]
        props["route_miles"] = spec["route_miles"][route]
        props["fact_state"] = "NEWLY_AUTHORED_SYNTHETIC_GEOMETRY_SUCCESSOR"
        props["provenance"] = spec["record_id"]
        props["survey_status"] = "NOT_SURVEYED"
        props["terrain_profile_ref"] = str(CANDIDATE.relative_to(ROOT))
        if route != "BST-MAIN":
            main = features["BST-MAIN"]["geometry"]["coordinates"]
            junction, offset = rechain(main, feature["geometry"]["coordinates"][0])
            if offset > 0.02:
                raise ValueError(f"{route} junction leaves corrected mainline")
            props["junction_main_mile"] = round(junction, 9)
            props["history"] = "Synthetic branch rechain; 1954 survivor alignment remains unlocated"
        else:
            props["history"] = (
                "Fictional 1968 completion; 1898 extent and 1954 survivor position remain unknown"
            )
    miles = sum(
        build_operations.line_miles(f["geometry"]["coordinates"])
        for f in network["features"]
        if f["id"] in ROUTES
    )
    if abs(miles - 40) > 0.000001:
        raise ValueError(f"Revised network is not 40 route-miles: {miles}")
    return network


def spatial_screen(network: dict, old_screen: dict, spec: dict) -> dict:
    water = json.loads((SOURCE / "geography/wyoming_waterbodies.geojson").read_text())
    polygons = unary_union(
        [transform(MAP_FWD.transform, shape(f["geometry"])) for f in water["features"]]
    )
    overlaps = []
    for feature in network["features"]:
        line = transform(MAP_FWD.transform, shape(feature["geometry"]))
        overlap = line.intersection(polygons).length
        overlaps.append({"route_id": feature["id"], "overlap_metres": round(overlap, 6)})
        if overlap >= 0.001:
            raise ValueError(f"Revised {feature['id']} introduces a waterbody crossing")
    screen = copy.deepcopy(old_screen)
    screen["method"] += "; recomputed for the September 29 dated synthetic successor"
    screen["source_successor"] = spec["record_id"]
    screen["waterbody_overlaps"] = overlaps
    main = next(f for f in network["features"] if f["id"] == "BST-MAIN")
    for crossing in screen["i80_crossings"]:
        mile, offset = rechain(main["geometry"]["coordinates"], crossing["lon_lat"])
        if offset > 0.02:
            raise ValueError("An inherited highway crossing leaves corrected mainline")
        crossing["projected_milepost"] = mile
    return screen


def operations_successor(old: dict, network: dict, spec: dict) -> tuple[dict, dict]:
    data = copy.deepcopy(old)
    data["schema_version"] = "1.1"
    data["document_id"] = "SH-IND-OPS-001-RAIL-20260929"
    data["successor_known_on_utc"] = spec["known_on_utc"]
    data["supersedes_scope"] = "Rail geometry, route/asset mileposts, and dependent train hours only"
    data["source_observed_utc"] = spec["known_on_utc"]
    data["geography"]["mainline_route_miles"] = spec["route_miles"]["BST-MAIN"]
    data["geography"]["branch_route_miles"] = sum(
        spec["route_miles"][r] for r in ROUTES[1:]
    )
    data["geography"]["network_geodesic_route_miles"] = sum(
        build_operations.line_miles(f["geometry"]["coordinates"])
        for f in network["features"] if f["id"] in ROUTES
    )
    data["geography"]["selection_reason"] = (
        "September 29 fixed-control, exact-40-mile synthetic successor; "
        "no new mine spur or land right; prior selected-candidate values retained as history"
    )
    data["geography"]["current_alignment_source"] = {
        "report": str(CANDIDATE.relative_to(ROOT)),
        "report_sha256": spec["candidate_report_sha256"],
        "geojson": str(CANDIDATE_GEO.relative_to(ROOT)),
        "geojson_sha256": spec["candidate_geojson_sha256"],
        "acceptance_commit": spec["candidate_acceptance_commit"],
        "classification": "NEWLY_AUTHORED_SYNTHETIC_DESIGN; NOT_SURVEYED",
    }
    data["geography"]["historical_only_screening_inputs"] = [
        "geography/selected_mainline.geojson",
        "geography/derived_ground_profiles.json",
        "geography/candidate_comparison.json",
    ]
    for branch in data["geography"]["branches"]:
        route = branch["id"]
        feature = next(f for f in network["features"] if f["id"] == route)
        branch["miles"] = spec["route_miles"][route]
        branch["junction"] = feature["geometry"]["coordinates"][0]
        branch["end"] = feature["geometry"]["coordinates"][-1]
    epochs = {r["epoch"]: r for r in data["geography"]["historical_route_epochs"]}
    main_miles = spec["route_miles"]["BST-MAIN"]
    east_miles = spec["route_miles"]["BST-EAST"]
    mineral_miles = spec["route_miles"]["BST-MINERAL"]
    epochs["1968"].update(
        route_miles=main_miles,
        net_route_growth_from_1954_low=main_miles - 16,
        net_route_growth_from_1954_high=main_miles - 14,
    )
    epochs["1972"].update(route_miles=main_miles + east_miles, added_route_miles=east_miles)
    epochs["1986"].update(route_miles=40, added_route_miles=mineral_miles)
    epochs["2026"]["known_on_utc"] = spec["known_on_utc"]
    epochs["2026"]["note"] = (
        "Retrospective synthetic geometry correction known September 29; underlying "
        "September 5 operating and forecast populations were not known-on restated. "
        "No Red Wash rail spur; yard tracks excluded."
    )
    old_segments = {r["id"]: copy.deepcopy(r) for r in old["track_segments"]}
    route_segments = [r for r in old["track_segments"] if r.get("route_id") in ROUTES]
    new_segments = []
    crosswalk = {"track_segments": [], "structures": []}
    for route in ROUTES:
        boundaries = spec["track_boundary_miles"][route]
        route_rows = [r for r in route_segments if r["route_id"] == route]
        if len(route_rows) != len(boundaries) - 1:
            raise ValueError(f"Track asset population changed for {route}")
        feature = next(f for f in network["features"] if f["id"] == route)
        coords = feature["geometry"]["coordinates"]
        for old_row, start, end in zip(route_rows, boundaries[:-1], boundaries[1:], strict=True):
            row = copy.deepcopy(old_row)
            row.update(
                mp_start=start,
                mp_end=end,
                length_miles=end - start,
                fact_state="NEWLY_AUTHORED_SYNTHETIC_MAINTENANCE_BOUNDARY",
                provenance=spec["record_id"],
                boundary_start_lon_lat=station(coords, start, spec["route_miles"][route]),
                boundary_end_lon_lat=station(coords, end, spec["route_miles"][route]),
                boundary_basis=spec["boundary_basis"],
            )
            new_segments.append(row)
            crosswalk["track_segments"].append(
                {"id": row["id"], "route_id": route,
                 "old_mp": [old_row["mp_start"], old_row["mp_end"]],
                 "new_mp": [start, end],
                 "new_boundary_lon_lat": [row["boundary_start_lon_lat"], row["boundary_end_lon_lat"]]}
            )
    data["track_segments"] = new_segments + [
        old_segments[r["id"]] for r in old["track_segments"] if r.get("route_id") not in ROUTES
    ]
    for structure in data["structures"]:
        feature = next(f for f in network["features"] if f["id"] == structure["route_id"])
        old_mp = structure["milepost"]
        actual_miles = build_operations.line_miles(feature["geometry"]["coordinates"])
        mile, offset = rechain(feature["geometry"]["coordinates"], structure["lon_lat"])
        if offset > 0.02:
            raise ValueError(f"Structure {structure['id']} leaves corrected route")
        structure["milepost"] = round(mile / actual_miles * spec["route_miles"][structure["route_id"]], 9)
        structure["fact_state"] = "SOURCE_FIXED_COORDINATE_SUCCESSOR_RECHAIN"
        structure["provenance"] = spec["record_id"]
        crosswalk["structures"].append(
            {"id": structure["id"], "route_id": structure["route_id"],
             "old_milepost": old_mp, "new_milepost": structure["milepost"],
             "fixed_coordinate_lon_lat": structure["lon_lat"], "offset_m": round(offset, 4)}
        )
    if len(crosswalk["track_segments"]) != 11 or len(crosswalk["structures"]) != 26:
        raise ValueError("Asset crosswalk population changed")
    cap = data["capacity_model"]
    branch_miles = east_miles + mineral_miles
    old_branch_miles = sum(r["miles"] for r in old["geography"]["branches"])
    switching = cap["daily_branch_running_and_switching_hours"] - 2 * old_branch_miles / spec["branch_speed_mph"]
    branch_hours = switching + 2 * branch_miles / spec["branch_speed_mph"]
    cap["round_trip_running_hours"] = 2 * main_miles / cap["road_average_mph"]
    cap["daily_branch_running_and_switching_hours"] = branch_hours
    cap["daily_branch_basis"] = (
        f"One daily round trip of each branch at {spec['branch_speed_mph']} mph plus "
        f"{switching:.9f} hours inherited local switching; extra workload requires protected extra-board duty."
    )
    cap["base_daily_train_hours"] = cap["base_round_trips_daily"] * (
        cap["round_trip_running_hours"] + cap["round_trip_switching_hours"]
    )
    cap["base_daily_train_hours_including_branches"] = cap["base_daily_train_hours"] + branch_hours
    headroom = cap["headroom_scenario"]
    headroom["daily_train_hours"] = headroom["round_trips_daily"] * (
        cap["round_trip_running_hours"] + cap["round_trip_switching_hours"]
    )
    headroom["daily_train_hours_including_branches"] = headroom["daily_train_hours"] + branch_hours
    return data, crosswalk


def build(output: Path = OUT) -> dict:
    spec, report, features, original = checked_inputs()
    output = Path(output)
    source_dir = output / "source"
    geo_dir = source_dir / "geography"
    geo_dir.mkdir(parents=True, exist_ok=True)
    for path in SOURCE.iterdir():
        if path.is_file() and path.name != "operations.json":
            target = source_dir / path.name
            if not target.exists():
                target.symlink_to(path)
    for path in (SOURCE / "geography").iterdir():
        if path.is_file() and path.name not in {"network.geojson", "spatial_screen.json"}:
            target = geo_dir / path.name
            if not target.exists():
                target.symlink_to(path)
    old_network = json.loads((SOURCE / "geography/network.geojson").read_text())
    network = network_successor(old_network, features, spec)
    write(geo_dir / "network.geojson", network)
    screen = spatial_screen(
        network, json.loads((SOURCE / "geography/spatial_screen.json").read_text()), spec
    )
    screen["input_sha256"]["network.geojson"] = digest(geo_dir / "network.geojson")
    write(geo_dir / "spatial_screen.json", screen)
    operations, crosswalk = operations_successor(original, network, spec)
    operations["geography"]["source_file_sha256"]["geography/network.geojson"] = digest(geo_dir / "network.geojson")
    operations["geography"]["source_file_sha256"]["geography/spatial_screen.json"] = digest(geo_dir / "spatial_screen.json")
    write(source_dir / "operations.json", operations)
    write(output / "asset_crosswalk.json", crosswalk)
    ops_result = build_operations.build(output / "operations", source_dir=source_dir)
    ops_result["output"] = "operations"
    planning = copy.deepcopy(operating_model.load_source())
    planning.update(
        schema_version="1.1", record_id="SH-PLAN-OPS-RAIL-20260929-001",
        cutoff=spec["known_on_utc"], available_at=spec["known_on_utc"],
        baseline_reference=str((OUT / "source/operations.json").relative_to(ROOT)),
        baseline_sha256=digest(source_dir / "operations.json"),
    )
    planning["source_policy"] += " Geometry successor known September 29; original September 6 forecast remains frozen."
    planning["rail"]["mainline_miles"] = spec["route_miles"]["BST-MAIN"]
    planning["rail"]["branch_hours_daily"] = operations["capacity_model"]["daily_branch_running_and_switching_hours"]
    write(output / "planning_source.json", planning)
    rows = operating_model.build(output / "planning_operations", source=planning)
    financial_source = forecast.source_data()
    financial_source["record_id"] = "SH-PLAN-FIN-RAIL-20260929-001"
    financial_source["available_at"] = spec["known_on_utc"]
    write(output / "financial_source.json", financial_source)
    finance = forecast.build(
        output / "planning_forecast", operating_rows=rows["operating_rows"], source=financial_source
    )
    manifest = {
        "record_id": spec["record_id"], "status": spec["status"],
        "known_on_utc": spec["known_on_utc"],
        "original_cutoff": spec["original_operating_cutoff"],
        "source_sha256": {"selector": digest(HERE / "source.json"),
                           "operations": digest(source_dir / "operations.json"),
                           "network": digest(geo_dir / "network.geojson"),
                           "spatial_screen": digest(geo_dir / "spatial_screen.json"),
                           "planning": digest(output / "planning_source.json"),
                           "financial": digest(output / "financial_source.json")},
        "counts": {"route_segments": len(crosswalk["track_segments"]),
                   "structures": len(crosswalk["structures"]),
                   "planning_months": len(rows["operating_rows"]),
                   "forecast_datasets": {k: len(v) for k, v in finance["datasets"].items()}},
        "route_miles": spec["route_miles"],
        "excluded": spec["proposed_leads_and_ladders"],
        "operations_build": ops_result,
        "candidate_status_at_source": report["status"],
    }
    write(output / "successor_manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
