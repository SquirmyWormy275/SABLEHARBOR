"""Reconcile Taylor track/site interfaces without manufacturing property rights."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name("TRACK_SITE_INTERFACE_SCREEN.json")
TO_UTM = Transformer.from_crs(4326, 26913, always_xy=True).transform
SOURCES = {
    "operations": "industrial/source/operations.json",
    "routes": "industrial/source/geography/network.geojson",
    "tracks": "geospatial/geojson/industrial_tracks.geojson",
    "facilities": "geospatial/geojson/industrial_facilities.geojson",
    "trackage_rights": "geospatial/geojson/rail_trackage_rights.geojson",
}


def _load(name):
    return json.loads((ROOT / SOURCES[name]).read_text())


def build() -> dict:
    operations = _load("operations")
    routes = {
        f["id"]: transform(TO_UTM, shape(f["geometry"]))
        for f in _load("routes")["features"]
        if f["id"].startswith("BST-")
    }
    if set(routes) != {"BST-MAIN", "BST-EAST", "BST-MINERAL"}:
        raise ValueError("Railway route population changed")
    track_features = {f["id"].removeprefix("IND-"): f for f in _load("tracks")["features"]}
    facility_features = {f["id"].removeprefix("IND-"): f for f in _load("facilities")["features"]}
    facilities = operations["facilities"]
    tracks = operations["track_segments"]
    structures = operations["structures"]
    if (len(facilities), len(tracks), len(structures)) != (12, 31, 26):
        raise ValueError("Accepted facility/track/structure population changed")
    if {f["id"] for f in facilities} != set(facility_features):
        raise ValueError("Facility geometry/source IDs do not reconcile")
    if {t["id"] for t in tracks} != set(track_features):
        raise ValueError("Track geometry/source IDs do not reconcile")
    if _load("trackage_rights")["features"]:
        raise ValueError("New trackage-rights geometry requires instrument review")
    route_track = [t for t in tracks if t.get("route_id") in routes]
    yard_track = [t for t in tracks if t.get("facility_id")]
    if len(route_track) != 11 or len(yard_track) != 20:
        raise ValueError("Track register route/yard classification changed")
    route_lengths = {
        route: sum(t["length_miles"] for t in route_track if t["route_id"] == route)
        for route in routes
    }
    if not math.isclose(sum(route_lengths.values()), 40, abs_tol=1e-8):
        raise ValueError("Route track register does not total 40 unique route-miles")
    for structure in structures:
        if structure["route_id"] not in routes or not (
            0 <= structure["milepost"] <= route_lengths[structure["route_id"]]
        ):
            raise ValueError(f"Structure outside registered route: {structure['id']}")
    yard_counts = Counter(t["facility_id"] for t in yard_track)
    site_rows = []
    for facility in facilities:
        facility_id = facility["id"]
        source_feature = facility_features[facility_id]
        if source_feature["properties"]["owner"] != facility["owner"]:
            raise ValueError(f"Facility owner/geometry mismatch: {facility_id}")
        if yard_counts[facility_id] != facility["track_count"]:
            raise ValueError(f"Facility track count mismatch: {facility_id}")
        envelope = transform(TO_UTM, shape(source_feature["geometry"]))
        site_tracks = [t for t in yard_track if t["facility_id"] == facility_id]
        nearest = sorted((envelope.distance(line), route) for route, line in routes.items())
        yard_separations = [
            min(
                transform(TO_UTM, shape(track_features[t["id"]]["geometry"])).distance(line)
                for line in routes.values()
            )
            for t in site_tracks
        ]
        minimum_yard_gap = min(yard_separations) if yard_separations else None
        site_rows.append(
            {
                "facility_id": facility_id,
                "source_owner_label": facility["owner"],
                "case_status": facility["case_status"],
                "source_footprint_basis": facility["footprint_basis"],
                "geometry_precision": source_feature["properties"]["precision_class"],
                "site_acreage_source": facility["acreage"],
                "source_yard_track_count": facility["track_count"],
                "yard_track_ids": [t["id"] for t in site_tracks],
                "nearest_route_id": nearest[0][1],
                "envelope_to_nearest_route_m": nearest[0][0],
                "minimum_yard_track_to_route_m": minimum_yard_gap,
                "mapped_route_join_state": (
                    "NO_RAIL_TRACK_IN_SOURCE"
                    if minimum_yard_gap is None
                    else "CASE_GEOMETRY_TOUCHES_ROUTE"
                    if minimum_yard_gap <= 1
                    else "LOCAL_LEAD_NOT_GEOMETRICALLY_CONNECTED"
                ),
                "real_title_or_access_instrument_id": None,
                "real_instrument_review_state": "NOT_SUPPLIED_BY_SYNTHETIC_SOURCE",
            }
        )
    return {
        "schema": "rail-track-site-interface-screen-v1",
        "source_paths": SOURCES,
        "source_sha256": {
            name: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for name, path in SOURCES.items()
        },
        "projection": "EPSG:26913",
        "route_miles_from_11_register_segments": route_lengths,
        "yard_track_count": len(yard_track),
        "yard_track_miles_not_route_miles": sum(t["length_miles"] for t in yard_track),
        "structure_count": len(structures),
        "facility_count": len(facilities),
        "trackage_rights_geometry_count": 0,
        "site_interfaces": site_rows,
        "limits": [
            "Footprints are synthetic acreage envelopes, not cadastral parcels or surveyed track plans.",
            "Nearest geometry separation is a gap screen, not a designed rail lead or proof of operational disconnection.",
            "A fictional owner label and operating case do not establish a real deed, lease, easement, UP interchange instrument or construction right.",
            "No rail spur to Red Wash is authorized; ore/product moves by the accepted truck interface subject to its own custody gate.",
        ],
    }


def main() -> None:
    OUTPUT.write_text(json.dumps(build(), indent=2) + "\n")


if __name__ == "__main__":
    main()
