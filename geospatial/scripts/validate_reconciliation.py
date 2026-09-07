"""Cross-domain acceptance checks: regressions must fail even if GIS files are valid."""

import json
from pathlib import Path
from shapely.geometry import shape
from model import GEOD, meters_between

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent


def reconciliation_errors(c, layers):
    errors = []

    def check(ok, message):
        if not ok:
            errors.append(message)

    ops = json.loads((ROOT / "industrial/source/operations.json").read_text())
    original = json.loads((ROOT / "industrial/source/geography/network.geojson").read_text())[
        "features"
    ]
    features = {f["id"]: f for f in original}
    entities = {e["entity_id"]: e for e in c["entities"]}
    objects = {o["object_id"]: o for o in c["objects"]}
    check(
        entities["SH-ENT-001"]["canonical_name"] == "Sable Harbor, LLC",
        "Parent legal identity drift",
    )
    for child, parent in [
        ("SH-ENT-006", "SH-ENT-SHIH"),
        ("SH-ENT-007", "SH-ENT-006"),
        ("SH-ENT-008", "SH-ENT-SHIH"),
        ("SH-ENT-009", "SH-ENT-008"),
    ]:
        check(entities[child]["parent_entity_id"] == parent, "Industrial ownership drift: " + child)
    check(entities["SH-ENT-003"]["canonical_name"] == "Klein", "Klein identity drift")
    check(
        entities["SH-ENT-015"]["canonical_name"] == "Northstar Minerals, Inc.",
        "Northstar seller identity drift",
    )
    check(
        "Bedford" in objects["SH-SITE-0005"]["canonical_name"]
        and "Fairmont" in objects["SH-SITE-0005"]["place"],
        "Bedford/Fairmont geography drift",
    )
    check(
        "Kelly Gang Mining" in objects["SH-SITE-0023"]["canonical_name"]
        and "Tasmania" in objects["SH-SITE-0023"]["place"],
        "Stream 17 identity/region drift",
    )
    check("Demotte" in objects["SH-SITE-0027"]["canonical_name"], "Demotte identity drift")
    for suffix in ["BIG", "SMALL", "WHITE", "MUSEUM"]:
        check("SH-FAC-FORT-" + suffix in objects, "Fort component missing: " + suffix)
    check(
        all("Evalon" not in e["canonical_name"] for e in c["entities"]),
        "Obsolete current entity name",
    )
    check(
        all("Belle" not in f["properties"]["canonical_name"] for f in layers["search_areas"]),
        "Superseded Belle in active search layer",
    )
    check(
        any(
            "Belle" in f["properties"]["canonical_name"]
            and f["properties"]["canon_status"] == "HISTORICAL"
            for f in layers["historical_sites"]
        ),
        "Belle supersession provenance lost",
    )
    check(
        len(layers["taylor_hub"]) == 1
        and meters_between(
            shape(layers["taylor_hub"][0]["geometry"]).coords[0], ops["geography"]["taylor_lon_lat"]
        )
        < 0.01,
        "Taylor differs from industrial candidate A",
    )
    rails = layers["rail_segments"]
    total = sum(GEOD.geometry_length(shape(f["geometry"])) / 1609.344 for f in rails)
    check(
        abs(total - ops["geography"]["network_geodesic_route_miles"]) < 0.00001,
        "Rail route-mile reconciliation failed",
    )
    check(
        {f["properties"]["route_id"] for f in rails} == {"BST-MAIN", "BST-EAST", "BST-MINERAL"},
        "Missing external branch or forbidden mine spur",
    )
    for rid in ["BST-MAIN", "BST-EAST", "BST-MINERAL"]:
        selected = [f for f in rails if f["properties"]["route_id"] == rid]
        check(
            abs(
                sum(GEOD.geometry_length(shape(f["geometry"])) for f in selected)
                - GEOD.geometry_length(shape(features[rid]["geometry"]))
            )
            < 0.01,
            "Changed source rail length: " + rid,
        )
        for f in selected:
            check(
                shape(f["geometry"]).hausdorff_distance(shape(features[rid]["geometry"]))
                < 0.0000001
                if len(selected) == 1
                else shape(f["geometry"])
                .difference(shape(features[rid]["geometry"]).buffer(1e-10))
                .is_empty,
                "Changed source centerline: " + rid,
            )
    check(
        len(layers["roads"]) == 1
        and shape(layers["roads"][0]["geometry"]).equals_exact(
            shape(features["ROAD-RW-01"]["geometry"]), 0
        ),
        "Truck-only road differs from accepted source",
    )
    check(
        abs(GEOD.geometry_length(shape(layers["roads"][0]["geometry"])) / 1609.344 - 9) < 0.00001,
        "Truck road mileage drift",
    )
    check(
        len(layers["industrial_facilities"]) == len(ops["facilities"]),
        "Industrial facility census incomplete",
    )
    check(
        len(layers["industrial_tracks"]) == len(ops["track_segments"]),
        "Track-register census incomplete",
    )
    check(
        len(layers["rail_bridges"]) + len(layers["rail_crossings"]) == len(ops["structures"]),
        "Structures census incomplete",
    )
    # Operating-entity creation does not establish shop occupancy or parcel ownership.
    for state in c["asset_states"]:
        if state["asset_id"] in {"SH-SITE-0002", "SH-SITE-0003"}:
            check(
                not state.get("earliest_start") and not state.get("valid_from"),
                "Institutional founding backdated into physical occupancy",
            )
    return errors
