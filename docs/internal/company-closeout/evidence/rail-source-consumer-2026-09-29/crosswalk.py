#!/usr/bin/env python3
"""Project fixed asset points and old track bounds onto a proposed rail centerline.

Track bounds are only a screening projection. A successor must review the
physical asset boundaries before treating the proposed mileposts as current.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pyproj import Geod, Transformer
from shapely.geometry import LineString, Point
from shapely.ops import substring

ROOT = Path(__file__).resolve().parents[5]
GEOD = Geod(ellps="WGS84")
FWD = Transformer.from_crs(4326, 26913, always_xy=True)
BACK = Transformer.from_crs(26913, 4326, always_xy=True)
METRES_PER_MILE = 1609.344


def point_at_mile(coords: list[list[float]], mile: float) -> list[float]:
    remaining = mile * METRES_PER_MILE
    for a, b in zip(coords, coords[1:], strict=False):
        azimuth, _, distance = GEOD.inv(a[0], a[1], b[0], b[1])
        if remaining <= distance + 0.0001:
            lon, lat, _ = GEOD.fwd(a[0], a[1], azimuth, min(max(remaining, 0), distance))
            return [lon, lat]
        remaining -= distance
    if remaining < 0.001:
        return coords[-1]
    raise ValueError(f"Milepost {mile} exceeds source route")


def project_mile(coords: list[list[float]], point: list[float]) -> tuple[float, float]:
    line = LineString([FWD.transform(*xy) for xy in coords])
    projected_point = Point(FWD.transform(*point))
    chainage = line.project(projected_point)
    if chainage <= 1e-9:
        return 0.0, line.distance(projected_point)
    part = substring(line, 0, chainage)
    geographic = LineString([BACK.transform(*xy) for xy in part.coords])
    return GEOD.geometry_length(geographic) / METRES_PER_MILE, line.distance(projected_point)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "candidate_geojson",
        nargs="?",
        type=Path,
        default=ROOT / "geospatial/engineering_review/COMPENSATED_40_MILE_CANDIDATE.geojson",
    )
    args = parser.parse_args()
    original = json.loads((ROOT / "industrial/source/operations.json").read_text())
    old_geojson = json.loads((ROOT / "industrial/source/geography/network.geojson").read_text())
    raw = args.candidate_geojson.read_bytes()
    new_geojson = json.loads(raw)
    old = {f["id"]: f["geometry"]["coordinates"] for f in old_geojson["features"]}
    new = {
        f["properties"]["source_route_id"]: f["geometry"]["coordinates"]
        for f in new_geojson["features"]
        if f["properties"].get("source_route_id") in {"BST-MAIN", "BST-EAST", "BST-MINERAL"}
    }
    if set(new) != {"BST-MAIN", "BST-EAST", "BST-MINERAL"}:
        raise ValueError("Expected exactly three proposed routes")
    tracks = []
    for row in original["track_segments"]:
        route = row.get("route_id")
        if route not in new or row.get("excluded_from_route_miles"):
            continue
        start, start_offset = project_mile(new[route], point_at_mile(old[route], row["mp_start"]))
        end, end_offset = project_mile(new[route], point_at_mile(old[route], row["mp_end"]))
        tracks.append(
            {
                "id": row["id"],
                "route_id": route,
                "source_mp_start": row["mp_start"],
                "source_mp_end": row["mp_end"],
                "candidate_mp_start": round(start, 6),
                "candidate_mp_end": round(end, 6),
                "source_boundary_projection_offsets_m": [round(start_offset, 3), round(end_offset, 3)],
                "candidate_boundary_status": "PROPOSED_PROJECTION_NOT_ADOPTED_ASSET_BOUNDARY",
            }
        )
    structures = []
    for row in original["structures"]:
        route = row["route_id"]
        mile, offset = project_mile(new[route], row["lon_lat"])
        structures.append(
            {
                "id": row["id"],
                "route_id": route,
                "source_milepost": row["milepost"],
                "candidate_milepost": round(mile, 6),
                "candidate_offset_m": round(offset, 3),
                "coordinate_state": "SOURCE_FIXED_COORDINATE_PROPOSED_RECHAIN",
            }
        )
    if len(tracks) != 11 or len(structures) != 26:
        raise ValueError("Source asset population changed")
    result = {
        "status": "READ_ONLY_PROPOSED_CROSSWALK",
        "candidate_geojson_sha256": hashlib.sha256(raw).hexdigest(),
        "source_track_count": len(tracks),
        "source_structure_count": len(structures),
        "track_segments": tracks,
        "structures": structures,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
