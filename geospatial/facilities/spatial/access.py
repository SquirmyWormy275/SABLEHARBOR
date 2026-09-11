"""Explicit, source-locked room and campus access route review."""

from __future__ import annotations
import hashlib
import json
from pathlib import Path

EPS = 1e-6


def _hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _inside(point, rect):
    x, y, w, h = rect
    return x - EPS <= point[0] <= x + w + EPS and y - EPS <= point[1] <= y + h + EPS


def _boundary(point, rect):
    x, y, w, h = rect
    return (
        _inside(point, rect)
        and min(abs(point[0] - x), abs(point[0] - x - w), abs(point[1] - y), abs(point[1] - y - h))
        <= EPS
    )


def _point(door):
    return [door["x_m"], door["y_m"]]


def build_access(root: Path) -> dict:
    root = Path(root)
    policy_path = root / "geospatial/facilities/spatial/ACCESS_POLICY.json"
    policy = json.loads(policy_path.read_text())
    source_path = root / policy["source"]
    site = json.loads(source_path.read_text())
    floors = {f["id"]: f for b in site["buildings"] for f in b["floors"]}
    routes = []
    for rule in policy["routes"]:
        result = {
            **rule,
            "site_id": site["site_id"],
            "outcome": "FAIL",
            "errors": [],
            "waypoints_m": [],
            "room_ids": [rule["room_id"], rule["via_room_id"]],
            "door_ids": [],
            "segments": [],
            "coordinate_frame": "floor_local_metres",
            "egress_certified": False,
        }
        floor = floors.get(rule["floor_id"])
        rooms = {r["id"]: r for r in floor["rooms"]} if floor else {}
        origin = rooms.get(rule["room_id"])
        via = rooms.get(rule["via_room_id"])
        if not origin or not via:
            result["errors"].append("Missing floor, origin or intermediate room")
            routes.append(result)
            continue
        payload = {
            "rooms": [origin, via],
            "floor_doors": floor.get("doors", []),
            "circulation": floor.get("circulation_zones", []),
        }
        if _hash(payload) != rule["geometry_security_sha256"]:
            result["errors"].append(
                "Reviewed room, door, circulation or access-class facts changed; substantive re-review required"
            )
        door = origin.get("door")
        exit_door = via.get("door")
        if not door or not exit_door:
            result["errors"].append("Required source door missing")
            routes.append(result)
            continue
        p, q = _point(door), _point(exit_door)
        for room, d in [(origin, door), (via, exit_door)]:
            if d.get("width_m", 0) <= 0 or not _boundary(_point(d), room["rect_m"]):
                result["errors"].append("Invalid source door boundary or width: " + room["id"])
            matching = [
                d2
                for d2 in floor.get("doors", [])
                if d2.get("room_id") == room["id"]
                and all(d2.get(k) == d.get(k) for k in ("x_m", "y_m", "width_m", "wall"))
            ]
            if not matching:
                result["errors"].append("Room door lacks matching floor door: " + room["id"])
        if not _boundary(p, via["rect_m"]):
            result["errors"].append("Origin door does not open into reviewed intermediate room")
        corridor = next(
            (z for z in floor.get("circulation_zones", []) if _boundary(q, z["rect_m"])), None
        )
        if not corridor:
            result["errors"].append("Intermediate room has no source door to circulation")
        if via.get("access") in ("audit", "residential", "private"):
            result["errors"].append(
                "Private or independent-assurance space cannot serve as intermediate passage"
            )
        if via.get("access") == "restricted" and rule["classification"] != "J2":
            result["errors"].append("Restricted intermediate requires J2-authorized route class")
        if rule["classification"] == "public" and via.get("access") != "public":
            result["errors"].append("Public route crosses nonpublic intermediate")
        x, y, w, h = origin["rect_m"]
        start = [x + w / 2, y + h / 2]
        points = [start, p, q]
        zones = [origin["rect_m"], via["rect_m"]]
        if corridor:
            x, y, w, h = corridor["rect_m"]
            points.append([x + w / 2, y + h / 2])
            zones.append(corridor["rect_m"])
        for i, (a, b, rect) in enumerate(zip(points, points[1:], zones)):
            verified = _inside(a, rect) and _inside(b, rect)
            result["segments"].append(
                {
                    "index": i,
                    "from_m": a,
                    "to_m": b,
                    "containing_rect_m": rect,
                    "verified": verified,
                    "basis": "Straight segment contained in convex source rectangle; furniture and clear width unassessed",
                }
            )
            if not verified:
                result["errors"].append("Route segment leaves verified source zone")
        result.update(
            waypoints_m=points,
            door_ids=[origin["id"] + ":door", via["id"] + ":door"],
            corridor_name=corridor["name"] if corridor else None,
            outcome="PASS" if not result["errors"] else "FAIL",
        )
        routes.append(result)
    campus = []
    classes = {
        "public_arrival_m": "public",
        "education_entry_m": "public",
        "pedestrian_spine_m": "staff",
        "east_west_walk_m": "staff",
        "j2_controlled_entry_m": "J2",
        "residential_arrival_m": "residential",
        "service_arrival_m": "service",
        "fire_service_loop_m": "service",
    }
    envelope = [0, 0, *site["envelope_m"]]
    for key, classification in classes.items():
        points = site.get("access", {}).get(key, [])
        if not points:
            continue
        verified = all(_inside(p, envelope) for p in points)
        campus.append(
            {
                "id": "SH-ACCESS:" + site["site_id"] + ":" + key,
                "site_id": site["site_id"],
                "classification": classification,
                "coordinate_frame": "site_local_metres",
                "waypoints_m": points,
                "outcome": "PASS" if verified else "FAIL",
                "segments": [
                    {
                        "from_m": a,
                        "to_m": b,
                        "verified": _inside(a, envelope) and _inside(b, envelope),
                    }
                    for a, b in zip(points, points[1:])
                ],
                "basis": "Source centre-line within modelled envelope; width, grades, barriers and crossing operations not assessed",
                "egress_certified": False,
            }
        )
    return {
        "schema_version": "1.0.0",
        "source_sha256": {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [policy_path, source_path]
        },
        "routes": routes,
        "campus_routes": campus,
        "summary": {
            "reviewed_rooms": len(routes),
            "reviewed_floors": len({r["floor_id"] for r in routes}),
            "verified_routes": sum(r["outcome"] == "PASS" for r in routes),
            "failures": sum(r["outcome"] == "FAIL" for r in routes + campus),
            "status": "FAIL" if any(r["outcome"] == "FAIL" for r in routes + campus) else "PASS",
            "engineering_certified": False,
        },
    }
