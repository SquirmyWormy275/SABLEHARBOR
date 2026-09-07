#!/usr/bin/env python3
"""Derive Geo representations from accepted industrial inputs, with source drift rejection.

Industrial inputs retain their identity and bytes. GIS does not own a second railway
model. Re-run before the GeoPackage builder; output is deterministic and offline.
"""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

from shapely.geometry import Point, mapping, shape
from shapely.ops import substring
from model import GEOD

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
MAP = {
    "SHI": "SH-ENT-001",
    "SHIH": "SH-ENT-SHIH",
    "PS": "SH-ENT-006",
    "RWH": "SH-ENT-007",
    "ARU": "SH-ENT-008",
    "BST": "SH-ENT-009",
    "NMI": "SH-ENT-015",
}
DID = "GEO-D018"


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sync():
    c = json.loads((BASE / "sources/catalog.json").read_text())
    pins = [s for s in c["sources"] if s["source_id"].startswith("SRC-CURRENT-")]
    for s in pins:
        p = ROOT / s["url_or_repo_path"]
        if hashlib.sha256(p.read_bytes()).hexdigest() != s["file_sha256"]:
            raise ValueError("Current canon source changed; reconcile before build: " + str(p))
    ops = json.loads((ROOT / "industrial/source/operations.json").read_text())
    entities = json.loads((ROOT / "industrial/source/entities.json").read_text())["entities"]
    spec = importlib.util.spec_from_file_location(
        "industrial_geo_source", ROOT / "industrial/tools/build_operations.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as td:
        module.geography_outputs(Path(td), ops)
        derived = {
            p.stem: json.loads(p.read_text())["features"] for p in Path(td).glob("*.geojson")
        }
    existing = {e["entity_id"]: e for e in c["entities"]}
    names = {e["legal_name"]: MAP[e["entity_id"]] for e in entities}
    for e in entities:
        eid = MAP[e["entity_id"]]
        row = dict(
            entity_id=eid,
            canonical_name=e["legal_name"],
            entity_type="EXTERNAL_OPERATOR" if e["entity_id"] == "NMI" else "LEGAL_ENTITY",
            parent_entity_id=MAP.get(e["owner_entity_id"]),
            valid_from=None,
            valid_to=None,
            legal_status=e["jurisdiction"] + " " + e["legal_form"] + "; accepted fictional case",
            canon_status="CANON_LOCKED",
            source_id="SRC-CURRENT-ENTITIES",
            notes="Current ownership snapshot at "
            + c["world_state_date"]
            + ". Formation and parent ownership dates are distinct; see industrial/source/entities.json. Stable industrial ID: "
            + e["entity_id"],
        )
        existing[eid] = row
    # Parents must precede children in the foreign-key insertion order.
    ordered = []
    pending = list(existing.values())
    while pending:
        available = [
            e
            for e in pending
            if not e["parent_entity_id"]
            or e["parent_entity_id"] in {x["entity_id"] for x in ordered}
        ]
        if not available:
            raise ValueError("Cyclic entity parent chain")
        ordered.extend(available)
        pending = [e for e in pending if e not in available]
    c["entities"] = ordered
    c["objects"] = [o for o in c["objects"] if not o["object_id"].startswith("SH-IND-")]
    c["claims"] = [o for o in c["claims"] if not o["claim_id"].startswith("CLM-IND-")]
    c["relationships"] = [
        o for o in c["relationships"] if not o["relationship_id"].startswith("REL-IND-")
    ]
    objs = {o["object_id"]: o for o in c["objects"]}

    def obj(oid, name, typ, raw, loc, place="Wyoming", entity="SH-ENT-009"):
        row = dict(
            object_id=oid,
            canonical_name=name,
            object_type=typ,
            entity_id=entity,
            place=place,
            granularity="DERIVED_CASE_GEOMETRY",
            census_status="LOCKED_DERIVED_IMPLEMENTATION",
            canon_status="ENGINEERED",
            fictionality="FICTIONAL_IN_REAL_GEOGRAPHY",
            source_id="SRC-CURRENT-OPS",
            source_path="industrial/source/operations.json",
            source_commit=c["source_commit"],
            source_locator=loc,
            exact_source_wording=json.dumps(raw, ensure_ascii=False, sort_keys=True),
            relevant_date=str(raw.get("opened", raw.get("date", "2026"))),
            date_precision="DAY"
            if len(str(raw.get("opened", raw.get("date", "")))) == 10
            else "YEAR_OR_RANGE",
            conflict_id="",
            next_action="Maintain industrial source identity; further precision requires supported source revision.",
            notes="Accepted synthetic case implementation; not survey, land title or regulatory qualification.",
            decision_id=DID,
        )
        c["objects"].append(row)
        objs[oid] = row
        return oid

    def normalize(f, oid, sid="SRC-CURRENT-OPS", prefix="IND-"):
        p = copy.deepcopy(f["properties"])
        fid = prefix + str(f["id"])
        owner = names.get(p.get("owner"))
        p.update(
            feature_id=fid,
            object_id=oid,
            canonical_name=p.get("name", p.get("id", fid)),
            fictionality="FICTIONAL_IN_REAL_GEOGRAPHY",
            real_world_relation="SYNTHETIC_CASE_NOT_REAL_PROPERTY",
            canon_status="ENGINEERED",
            geometry_status="LOCKED_DERIVED_IMPLEMENTATION",
            location_method="DERIVED_FROM_ACCEPTED_SOURCE",
            precision_class="CASE_ENGINEERING_NOT_SURVEY",
            horizontal_accuracy_m=None,
            vertical_accuracy_m=None,
            public_precision="SYNTHETIC_CASE",
            source_id=sid,
            decision_id=DID,
            recorded_at=c["recorded_at"],
            world_state_date=c["world_state_date"],
            owner_entity=owner,
            operator_entity=owner,
            valid_from=None,
            valid_to=None,
            construction_method="Geo adapter of industrial source; geometry and original attributes retained.",
            notes="Owner/operator identify the current synthetic case, not a timeless real-property right. Source opening date is not automatically the current owner acquisition date.",
        )
        return dict(type="Feature", id=fid, geometry=copy.deepcopy(f["geometry"]), properties=p)

    out = {
        k: []
        for k in [
            "rail_nodes",
            "rail_network",
            "roads",
            "rail_yards",
            "rail_interchanges",
            "rail_bridges",
            "rail_crossings",
            "rail_tunnels",
            "rail_mileposts",
            "rail_industries",
            "rail_trackage_rights",
            "industrial_facilities",
            "industrial_tracks",
        ]
    }
    facilities = []
    for i, f in enumerate(derived["facilities"]):
        p = f["properties"]
        oid = obj(
            "SH-IND-" + f["id"],
            p["name"],
            "FACILITY",
            ops["facilities"][i],
            "/facilities/" + str(i),
            entity=names.get(p["owner"]),
        )
        n = normalize(f, oid)
        facilities.append(n)
        c["relationships"].append(
            dict(
                relationship_id="REL-IND-" + f["id"],
                subject_id=oid,
                predicate="CURRENT_CASE_OWNER",
                object_id=names[p["owner"]],
                valid_from=None,
                valid_to=None,
                date_text=c["world_state_date"],
                canon_status="ENGINEERED",
                source_id="SRC-CURRENT-OPS",
                decision_id=DID,
                notes="Current modeled owner; original facility opening does not backdate ownership.",
            )
        )
    out["industrial_facilities"] = facilities
    for i, f in enumerate(derived["structure_points"]):
        p = f["properties"]
        oid = obj(
            "SH-IND-" + f["id"],
            f["id"] + " " + p["kind"],
            "RAIL_STRUCTURE",
            p,
            "/structures/" + str(i),
        )
        n = normalize(f, oid)
        n["properties"].update(
            canonical_name=f["id"] + " " + p["kind"],
            owner_entity="SH-ENT-009",
            operator_entity="SH-ENT-009",
        )
        out["rail_bridges" if p["kind"] == "rail_bridge" else "rail_crossings"].append(n)
    for i, f in enumerate(derived["track_segments"]):
        p = f["properties"]
        oid = obj(
            "SH-IND-" + f["id"],
            p.get("name", f["id"]),
            "TRACK_REGISTER_SEGMENT",
            ops["track_segments"][i],
            "/track_segments/" + str(i),
        )
        out["industrial_tracks"].append(normalize(f, oid))
    network = {f["id"]: f for f in derived["network"]}
    main = shape(network["BST-MAIN"]["geometry"])
    # Split the same centerline at actual branch junctions for explicit graph connectivity.
    east = network["BST-EAST"]["geometry"]["coordinates"][0]
    mineral = network["BST-MINERAL"]["geometry"]["coordinates"][0]
    cuts = [0, main.project(Point(east)), main.project(Point(mineral)), main.length]
    node_points = {
        "WAM": list(main.coords[0]),
        "EAST-J": east,
        "MINERAL-J": mineral,
        "TAY": list(main.coords[-1]),
        "EAST-END": network["BST-EAST"]["geometry"]["coordinates"][-1],
        "MINERAL-END": network["BST-MINERAL"]["geometry"]["coordinates"][-1],
    }
    node_seq = ["WAM", "EAST-J", "MINERAL-J", "TAY"]
    for key, xy in node_points.items():
        f = dict(
            id="NODE-" + key,
            geometry=mapping(Point(xy)),
            properties=dict(name="BS&T " + key, owner="Blood, Sweat & Tears Railway Company"),
        )
        out["rail_nodes"].append(normalize(f, "SH-RAIL-0001", "SRC-CURRENT-NETWORK"))
    routeids = {}
    for i in range(3):
        f = copy.deepcopy(network["BST-MAIN"])
        f["id"] = "BST-MAIN-" + str(i + 1)
        f["geometry"] = mapping(substring(main, cuts[i], cuts[i + 1]))
        n = normalize(f, "SH-RAIL-0001", "SRC-CURRENT-NETWORK")
        n["properties"].update(
            from_node_id="IND-NODE-" + node_seq[i],
            to_node_id="IND-NODE-" + node_seq[i + 1],
            route_id="BST-MAIN",
            route_miles=GEOD.geometry_length(shape(f["geometry"])) / 1609.344,
            geometry_miles=GEOD.geometry_length(shape(f["geometry"])) / 1609.344,
            valid_from="1968-10-14",
        )
        out["rail_network"].append(n)
    routeids["BST-MAIN"] = [n["id"] for n in out["rail_network"]]
    for key, junction, end in [
        ("BST-EAST", "EAST-J", "EAST-END"),
        ("BST-MINERAL", "MINERAL-J", "MINERAL-END"),
    ]:
        f = network[key]
        oid = obj(
            "SH-IND-" + key,
            f["properties"]["name"],
            "RAIL_BRANCH",
            f["properties"],
            "/geography/branches",
            entity="SH-ENT-009",
        )
        n = normalize(f, oid, "SRC-CURRENT-NETWORK")
        n["properties"].update(
            from_node_id="IND-NODE-" + junction,
            to_node_id="IND-NODE-" + end,
            route_id=key,
            geometry_miles=GEOD.geometry_length(shape(f["geometry"])) / 1609.344,
            valid_from=f["properties"]["open_date"],
        )
        out["rail_network"].append(n)
        routeids[key] = [n["id"]]
    road = normalize(network["ROAD-RW-01"], "SH-RAIL-0002", "SRC-CURRENT-NETWORK")
    road["properties"].update(
        owner_entity="SH-ENT-007",
        operator_entity="SH-ENT-008",
        route_id="ROAD-RW-01",
        notes="Truck-only synthetic access; RWH easement interests and ARU drayage do not confer uranium custody authority.",
    )
    out["roads"] = [road]
    c["rail_routes"] = []
    for key, start, end in [
        ("BST-MAIN", "WAM", "TAY"),
        ("BST-EAST", "EAST-J", "EAST-END"),
        ("BST-MINERAL", "MINERAL-J", "MINERAL-END"),
    ]:
        c["rail_routes"].append(
            dict(
                route_id=key,
                canonical_name=network[key]["properties"]["name"],
                railroad="SH-ENT-009",
                route_type="CURRENT_DERIVED_CASE",
                origin_node="IND-NODE-" + start,
                destination_node="IND-NODE-" + end,
                segment_ids=routeids[key],
                valid_from=network[key]["properties"]["open_date"],
                valid_to=None,
                status="LOCKED_DERIVED_IMPLEMENTATION",
                canon_status="ENGINEERED",
                decision_id=DID,
                notes="Accepted synthetic chronology; early 1898/1954 alignment not spatialized.",
            )
        )
    for i, event in enumerate(ops["history"]):
        obj(
            "SH-IND-" + event["id"],
            event["event"],
            "EVENT",
            event,
            "/history/" + str(i),
            place="Wyoming; exact early event sites unlocated",
        )
    for oid, name, quote, loc in [
        (
            "SH-SITE-0007",
            "Taylor — BS&T industrial town and operating hub",
            ops["geography"],
            "/geography",
        ),
        ("SH-SITE-0008", "Wamsutter fictional interchange", ops["facilities"][0], "/facilities/0"),
        (
            "SH-SITE-0020",
            "ARU terminal, warehouse and trucking estate",
            ops["facilities"],
            "/facilities",
        ),
        (
            "SH-SITE-0021",
            "ARU external customer delivery interfaces",
            ops["contract_facility_assignments"],
            "/contract_facility_assignments",
        ),
        ("SH-RAIL-0001", "BS&T 40-mile operating network", ops["geography"], "/geography"),
        (
            "SH-RAIL-0002",
            "Taylor–Red Wash truck-only access and transload interface",
            ops["geography"],
            "/geography",
        ),
        (
            "SH-EVT-0008",
            "Sable Harbor Industrial Holdings acquisition of ARU",
            {"date": "2026-01-07"},
            "industrial/source/entities.json#/entities/4",
        ),
    ]:
        o = objs[oid]
        o.update(
            canonical_name=name,
            source_id="SRC-CURRENT-OPS",
            source_path="industrial/source/operations.json",
            source_commit=c["source_commit"],
            source_locator=loc,
            exact_source_wording=json.dumps(quote, ensure_ascii=False, sort_keys=True),
            census_status="LOCKED_DERIVED_IMPLEMENTATION",
            canon_status="ENGINEERED",
            decision_id=DID,
            conflict_id="",
            next_action="Reconcile with accepted industrial model; precise surveying/land rights remain separate.",
            notes="Current case source replaces old unresolved/proposed scope. Taylor is fictional; municipal incorporation is not asserted.",
            place="Wyoming; Taylor, Wamsutter and Rawlins operating estate"
            if oid in {"SH-SITE-0020", "SH-SITE-0021"}
            else o["place"],
        )
    objs["SH-SITE-0007"]["place"] = "42.12 N, 108.10 W; Sweetwater County, Wyoming"
    objs["SH-RAIL-0003"].update(
        next_action="Early coal-era and abandoned alignments remain unlocated; current mainline/branches and opening epochs are already modeled.",
        notes="1898 and 1954 geometry must not be backfilled from current track; industrial history controls known chronology.",
    )
    # Replace stale C exports and old study-yard polygons with source-controlled inputs.
    oldsites = json.loads((BASE / "geojson/sites.geojson").read_text())["features"]
    oldsites = [f for f in oldsites if f["id"].startswith("SITE-RW")]
    write(BASE / "geojson/sites.geojson", dict(type="FeatureCollection", features=oldsites))
    for stem, features in out.items():
        write(
            BASE / "geojson" / (stem + ".geojson"),
            dict(type="FeatureCollection", features=features),
        )
    write(
        BASE / "geojson/bst_alignment_current.geojson",
        dict(type="FeatureCollection", features=out["rail_network"]),
    )
    hub = dict(
        id="TAYLOR-CURRENT",
        geometry=mapping(Point(ops["geography"]["taylor_lon_lat"])),
        properties=dict(name="Taylor industrial hub", owner="Blood, Sweat & Tears Railway Company"),
    )
    write(
        BASE / "geojson/taylor_hub.geojson",
        dict(
            type="FeatureCollection", features=[normalize(hub, "SH-SITE-0007", "SRC-CURRENT-OPS")]
        ),
    )
    c["geometry_layers"].update(
        industrial_facilities="industrial_facilities",
        industrial_tracks="industrial_tracks",
        taylor_hub="taylor_hub",
    )
    write(BASE / "sources/catalog.json", c)
    report = dict(
        source_commit=c["source_commit"],
        source_pins={s["url_or_repo_path"]: s["file_sha256"] for s in pins},
        selected_candidate=ops["geography"]["selected_candidate"],
        network_route_miles=sum(
            GEOD.geometry_length(shape(f["geometry"])) / 1609.344 for f in out["rail_network"]
        ),
        road_miles=GEOD.geometry_length(shape(road["geometry"])) / 1609.344,
        facilities=len(facilities),
        track_register_segments=len(out["industrial_tracks"]),
        structures=len(ops["structures"]),
        history_events=len(ops["history"]),
        old_pr96_candidate="TAYLOR-C_SUPERSEDED",
        preserves_source_geometries=True,
    )
    write(BASE / "reports/INDUSTRIAL_RECONCILIATION.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "source_pins"}, indent=2))


if __name__ == "__main__":
    sync()
