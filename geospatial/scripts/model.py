"""Shared temporal and network rules. Unknown facts never become timeless facts."""
from __future__ import annotations
from collections import defaultdict, deque
from datetime import date
from pyproj import Geod
from shapely.geometry import shape, Point

GEOD = Geod(ellps="WGS84")
CANON_STATUSES = {"CANON_LOCKED", "CANON_SITED", "CANON_CONSTRAINED", "ENGINEERED", "ILLUSTRATIVE", "REAL_REFERENCE", "HISTORICAL", "PROPOSED", "CONFLICTING", "UNKNOWN"}


def temporal_membership(record, as_of):
    """Return CERTAIN, POSSIBLE, ABSENT, or UNKNOWN at an ISO calendar date.

    Intervals are half-open. A snapshot establishes only its own date. A year
    establishes bounds on an event; it never silently becomes January 1.
    """
    date.fromisoformat(as_of)
    start, end = record.get("valid_from"), record.get("valid_to")
    if (start and as_of < start) or (end and as_of >= end):
        return "ABSENT"
    if record.get("disposed_on") and as_of >= record["disposed_on"]:
        return "ABSENT"
    if record.get("snapshot_as_of") == as_of:
        return "CERTAIN"
    earliest, latest = record.get("earliest_start"), record.get("latest_start")
    first_end, last_end = record.get("earliest_end"), record.get("latest_end")
    if earliest and as_of < earliest or last_end and as_of >= last_end:
        return "ABSENT"
    if earliest and latest and earliest <= as_of < latest:
        return "POSSIBLE"
    if first_end and last_end and first_end <= as_of < last_end:
        return "POSSIBLE"
    if start or latest and as_of >= latest:
        return "CERTAIN"
    return "UNKNOWN"


def state_filter(records, as_of, owner=None, include_possible=False):
    accepted = {"CERTAIN", "POSSIBLE"} if include_possible else {"CERTAIN"}
    return [r for r in records if temporal_membership(r, as_of) in accepted and (owner is None or r.get("owner_entity") == owner)]


def meters_between(a, b):
    return GEOD.inv(a[0], a[1], b[0], b[1])[2]


def network_errors(nodes, segments, routes, tolerance_m=2.0):
    """Check declared endpoints, ownership, duplicate edges and route graph.

    Tests may use isolated fixtures. They are not BS&T geographic canon.
    """
    errors=[]
    node_map={n["properties"]["feature_id"]:n for n in nodes}
    edge_map={s["properties"]["feature_id"]:s for s in segments}
    seen={}
    for segment in segments:
        p=segment["properties"]; name=p["feature_id"]; g=shape(segment["geometry"])
        if g.geom_type != "LineString":
            errors.append(f"{name}: network edge must be an intentional contiguous LineString")
            continue
        if not p.get("owner_entity") or not p.get("operator_entity"):
            errors.append(f"{name}: missing owner/operator")
        for key,xy in [("from_node_id",g.coords[0]),("to_node_id",g.coords[-1])]:
            n=node_map.get(p.get(key))
            if n is None:
                errors.append(f"{name}: unknown {key}")
            elif meters_between(xy,shape(n["geometry"]).coords[0])>tolerance_m:
                errors.append(f"{name}: endpoint exceeds {tolerance_m} m tolerance")
        key=g.normalize().wkb_hex
        if key in seen:
            errors.append(f"{name}: duplicate geometry with {seen[key]}")
        seen[key]=name
        if p.get("geometry_miles") is not None and abs(p["geometry_miles"]-GEOD.geometry_length(g)/1609.344)>.001:
            errors.append(f"{name}: incorrect calculated mileage")
    for route in routes:
        graph=defaultdict(set); ids=route.get("segment_ids",[])
        if not ids:
            errors.append(f"{route['route_id']}: empty route")
            continue
        for sid in ids:
            if sid not in edge_map:
                errors.append(f"{route['route_id']}: missing segment {sid}")
                continue
            p=edge_map[sid]["properties"];a=p.get("from_node_id");b=p.get("to_node_id")
            graph[a].add(b);graph[b].add(a)
        if graph:
            start=next(iter(graph)); reached={start};q=deque([start])
            while q:
                for nxt in graph[q.popleft()]-reached:
                    reached.add(nxt);q.append(nxt)
            if len(reached)!=len(graph):errors.append(f"{route['route_id']}: disconnected route")
            if route.get("origin_node") not in graph or route.get("destination_node") not in graph:
                errors.append(f"{route['route_id']}: undeclared route endpoint")
    return errors
