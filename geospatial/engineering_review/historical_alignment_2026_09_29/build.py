#!/usr/bin/env python3
"""Reproduce a visibly fictional historical railway alignment alternative."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pyproj import Geod, Transformer
from shapely.geometry import LineString, Point, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
METRES_PER_MILE = 1609.344
GEOD = Geod(ellps="WGS84")
PROJECT = Transformer.from_crs(4326, 26913, always_xy=True)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def geodesic_miles(coords: list[list[float]]) -> float:
    return sum(
        GEOD.inv(*a, *b)[2] for a, b in zip(coords, coords[1:], strict=False)
    ) / METRES_PER_MILE


def build() -> dict:
    source = json.loads((HERE / "source.json").read_text())
    for relative, sha in source["accepted_sources"].items():
        if digest(ROOT / relative) != sha:
            raise ValueError(f"Accepted historical or modern source changed: {relative}")
    lower = source["lower_authority_narrative_source"]
    if digest(ROOT / lower["path"]) != lower["sha256"]:
        raise ValueError("Lower-authority historical narrative bytes changed")
    accepted = json.loads((ROOT / "industrial/source/operations.json").read_text())
    epochs = {r["epoch"]: r for r in accepted["geography"]["historical_route_epochs"]}
    if (
        epochs["1898"]["route_miles"] is not None
        or epochs["1954"]["route_miles"] is not None
        or [epochs["1954"]["surviving_route_miles_low"], epochs["1954"]["surviving_route_miles_high"]]
        != source["accepted_history_preserved"]["1954_surviving_miles_interval"]
        or epochs["1968"]["effective_date"] != source["accepted_history_preserved"]["1968_main_completion"]
        or epochs["1972"]["effective_date"] != source["accepted_history_preserved"]["1972_east_branch_completion"]
        or epochs["1986"]["effective_date"] != source["accepted_history_preserved"]["1986_mineral_branch_completion"]
    ):
        raise ValueError("Accepted historical chronology or uncertainty changed")
    candidate = source["hypothesis"]
    survivor = candidate["surviving_1954_centerline_lon_lat"]
    abandoned = candidate["abandoned_mine_only_centerline_lon_lat"]
    if survivor[0] != accepted["geography"]["wamsutter_junction_lon_lat"]:
        raise ValueError("Later Wamsutter anchor changed")
    if abandoned[0] not in survivor or survivor[-1] != candidate["fictional_west_service_point_lon_lat"] or abandoned[-1] != candidate["fictional_coal_works_lon_lat"]:
        raise ValueError("Fictional historical topology is disconnected")
    survivor_miles = geodesic_miles(survivor)
    abandoned_miles = geodesic_miles(abandoned)
    if not 14 <= survivor_miles <= 16:
        raise ValueError("Candidate 1954 survivor violates accepted interval")
    if not 20 <= survivor_miles + abandoned_miles <= 24:
        raise ValueError("Candidate pre-failure estate is not roughly 22 miles")
    if candidate["current_operating_right_or_asset"] or candidate["real_title_or_survey_evidence"]:
        raise ValueError("Historical hypothesis cannot grant current rights or survey authority")
    counties = json.loads((ROOT / "industrial/source/geography/wyoming_counties.geojson").read_text())
    sweetwater = next(f for f in counties["features"] if f["properties"].get("GEOID") == "56037")
    county = shape(sweetwater["geometry"])
    if not all(county.covers(Point(*p)) for p in survivor + abandoned):
        raise ValueError("A fictional anchor leaves the named county")
    modern = json.loads(
        (ROOT / "geospatial/engineering_review/COMPENSATED_40_MILE_CANDIDATE.geojson").read_text()
    )
    current_lines = [
        transform(PROJECT.transform, shape(f["geometry"]))
        for f in modern["features"]
        if f["properties"].get("source_route_id") in {"BST-MAIN", "BST-EAST", "BST-MINERAL"}
    ]
    old_lines = [transform(PROJECT.transform, LineString(coords)) for coords in (survivor, abandoned)]
    overlap = sum(old.intersection(now.buffer(0.05)).length for old in old_lines for now in current_lines)
    if overlap > 10:
        raise ValueError("Historical candidate back-projects a modern active alignment")
    features = [
        {
            "type": "Feature", "id": "HYP-BST-1954-SURVIVOR",
            "geometry": {"type": "LineString", "coordinates": survivor},
            "properties": {
                "scenario_id": candidate["scenario_id"],
                "record_id": source["record_id"],
                "classification": source["status"],
                "historical_role": "1954-survivor-placement-hypothesis",
                "candidate_miles": survivor_miles,
                "accepted_extent_low_miles": 14,
                "accepted_extent_high_miles": 16,
                "accepted_geometry": None,
                "not_current_asset_or_right": True,
            },
        },
        {
            "type": "Feature", "id": "HYP-BST-MINE-ONLY-ABANDONED",
            "geometry": {"type": "LineString", "coordinates": abandoned},
            "properties": {
                "scenario_id": candidate["scenario_id"],
                "record_id": source["record_id"],
                "classification": source["status"],
                "historical_role": "mine-only-trackage-abandonment-hypothesis",
                "candidate_miles": abandoned_miles,
                "accepted_geometry": None,
                "date_precision": "interval-only",
                "not_current_asset_or_right": True,
            },
        },
    ]
    geojson = {"type": "FeatureCollection", "features": features}
    write(HERE / "candidate.geojson", geojson)
    report = {
        "record_id": source["record_id"],
        "recorded_date_utc": source["recorded_date_utc"],
        "status": source["status"],
        "source_sha256": digest(HERE / "source.json"),
        "candidate_geojson_sha256": digest(HERE / "candidate.geojson"),
        "accepted_1898_original_extent_miles": None,
        "accepted_1898_geometry": None,
        "accepted_1954_surviving_interval_miles": [14, 16],
        "accepted_1954_geometry": None,
        "candidate_1954_survivor_miles": survivor_miles,
        "candidate_abandoned_mine_only_miles": abandoned_miles,
        "candidate_prefailure_total_miles": survivor_miles + abandoned_miles,
        "current_route_overlap_screen_m": overlap,
        "source_fixed_modern_structure_or_asset_ids_reused": 0,
        "scope": "One newly authored alternative, not recovered original history, accepted linework, property title, historical terrain proof, or current operating asset; 1898 extent remains unknown.",
    }
    write(HERE / "report.json", report)
    return report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
