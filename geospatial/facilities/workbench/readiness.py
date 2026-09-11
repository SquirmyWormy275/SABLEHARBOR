"""Read-only architectural concept checks; no code or engineering certification."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

EPS = 1e-6  # Numeric comparison tolerance in metres, never a design/code threshold.


def _inside(point, rect):
    x, y = point
    a, b, w, h = rect
    return a - EPS <= x <= a + w + EPS and b - EPS <= y <= b + h + EPS


def _boundary(point, rect):
    x, y = point
    a, b, w, h = rect
    return (
        _inside(point, rect) and min(abs(x - a), abs(x - a - w), abs(y - b), abs(y - b - h)) <= EPS
    )


def _overlap(a, b):
    return (
        min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]) > EPS
        and min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]) > EPS
    )


def _cross(a, b, c, d):
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    values = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    if values[0] * values[1] < -EPS and values[2] * values[3] < -EPS:
        return True
    return any(
        abs(v) <= EPS
        and min(p[0], q[0]) - EPS <= r[0] <= max(p[0], q[0]) + EPS
        and min(p[1], q[1]) - EPS <= r[1] <= max(p[1], q[1]) + EPS
        for v, p, q, r in [
            (values[0], a, b, c),
            (values[1], a, b, d),
            (values[2], c, d, a),
            (values[3], c, d, b),
        ]
    )


def build_readiness(root: Path) -> dict:
    """Return deterministic evidence checks from sources; never mutate publications."""
    root = Path(root)
    paths = sorted((root / "geospatial/facilities/source").glob("*.json"))
    runtime = root / "geospatial/facilities/RUNTIME_BRIDGE.json"
    if runtime.exists():
        paths.append(runtime)
    checks, source_hashes = [], {}

    def emit(scope, rule, outcome, basis, evidence, next_action):
        checks.append(
            {
                "id": f"SH-READY:{scope}:{rule}",
                "scope": scope,
                "severity": {
                    "PASS": "INFO",
                    "NOT_ASSESSED": "INFO",
                    "REVIEW": "WARNING",
                    "FAIL": "ERROR",
                }[outcome],
                "outcome": outcome,
                "basis": basis,
                "evidence": evidence,
                "next_action": next_action,
            }
        )

    for path in paths:
        relative = str(path.relative_to(root))
        source_hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        data = json.loads(path.read_text())
        for site in data.get("sites", [data]):
            sid = site["site_id"]
            buildings = site.get("buildings", [])
            base = {
                "source": relative,
                "site_id": sid,
                "status": site.get("status"),
                "geometry_status": site.get("geometry_status"),
            }
            adjacency = site.get("adjacency", [])
            emit(
                sid,
                "adjacency-intent",
                "PASS" if adjacency else "NOT_ASSESSED",
                "Presence of explicit functional adjacency/separation intent only; relationships are not inferred from proximity.",
                {**base, "relationships": adjacency},
                "Review declared relationships against operating and access workflows."
                if adjacency
                else "Record intended adjacency and separation relationships before assessing them.",
            )
            pairs = [
                [a["id"], b["id"]]
                for i, a in enumerate(buildings)
                for b in buildings[i + 1 :]
                if a.get("rect_m") and b.get("rect_m") and _overlap(a["rect_m"], b["rect_m"])
            ]
            complete = bool(buildings) and all(b.get("rect_m") for b in buildings)
            emit(
                sid,
                "building-separation",
                "FAIL" if pairs else "PASS" if complete else "NOT_ASSESSED",
                "Concept footprints must not overlap in a common local coordinate frame; no minimum separation distance is asserted.",
                {**base, "overlapping_buildings": pairs},
                "Resolve overlapping footprints."
                if pairs
                else "Engineering separation distances and fire exposure remain unassessed.",
            )
            access = site.get("access", {})
            service = access.get("service_arrival_m", [])
            public = {
                k: v
                for k, v in access.items()
                if k
                in (
                    "public_arrival_m",
                    "pedestrian_spine_m",
                    "education_entry_m",
                    "residential_arrival_m",
                    "east_west_walk_m",
                )
                and v
            }
            crossings = [
                name
                for name, points in public.items()
                if any(
                    _cross(a, b, c, d)
                    for a, b in zip(service, service[1:])
                    for c, d in zip(points, points[1:])
                )
            ]
            supported = len(service) > 1 and any(len(p) > 1 for p in public.values())
            emit(
                sid,
                "service-pedestrian-crossings",
                "REVIEW" if crossings else "PASS" if supported else "NOT_ASSESSED",
                "Intersection of drawn route centre-lines is a coordination trigger; grade, widths, timing and controls are unknown.",
                {**base, "crossing_routes": crossings, "service_route": service},
                "Review crossing controls, loading manoeuvres and grade."
                if crossings
                else "Confirm swept paths, loading geometry and pedestrian controls; unrecorded routes are not assumed clear.",
            )
            for building in buildings:
                bid = building["id"]
                floors = building.get("floors", [])
                cores = building.get("core_zones", [])
                mismatch = [
                    f["id"] for f in floors if "core_zones" in f and f["core_zones"] != cores
                ]
                emit(
                    bid,
                    "fixed-core-stacking",
                    "FAIL" if mismatch else "PASS" if cores else "NOT_ASSESSED",
                    "A building-level core template is inherited by every floor; explicit floor overrides must match. Implicit renderer cores are not source evidence.",
                    {
                        **base,
                        "building_id": bid,
                        "core_template": cores,
                        "mismatched_floors": mismatch,
                        "core_basis": building.get("core_basis"),
                    },
                    "Reconcile floor overrides with the fixed template."
                    if mismatch
                    else "Confirm structural, shaft and service continuity in engineering design.",
                )
                for floor in floors:
                    fid = floor["id"]
                    rooms = floor.get("rooms", [])
                    corridors = floor.get("circulation_zones", [])
                    missing, invalid, disconnected = [], [], []
                    for room in rooms:
                        rid = room.get("id", room.get("name"))
                        doors = [d for d in floor.get("doors", []) if d.get("room_id") == rid]
                        if room.get("door"):
                            doors.append(room["door"])
                        if not doors:
                            missing.append(rid)
                            continue
                        valid = [
                            d
                            for d in doors
                            if d.get("x_m") is not None
                            and d.get("y_m") is not None
                            and room.get("rect_m")
                            and _boundary((d["x_m"], d["y_m"]), room["rect_m"])
                            and d.get("width_m", 0) > 0
                        ]
                        if len(valid) != len(doors):
                            invalid.append(rid)
                        if corridors and not any(
                            _boundary((d["x_m"], d["y_m"]), z["rect_m"])
                            for d in valid
                            for z in corridors
                        ):
                            disconnected.append(rid)
                    outcome = (
                        "FAIL"
                        if invalid
                        else "NOT_ASSESSED"
                        if not corridors or not rooms
                        else "REVIEW"
                        if missing or disconnected
                        else "PASS"
                    )
                    emit(
                        fid,
                        "door-circulation-access",
                        outcome,
                        "Positive-width room door anchors must lie on their room boundary and a recorded circulation boundary. Indirect room-to-room access requires explicit review, not an invented route.",
                        {
                            **base,
                            "floor_id": fid,
                            "missing_doors": missing,
                            "invalid_doors": invalid,
                            "no_direct_circulation": disconnected,
                        },
                        "Record missing routes and resolve invalid doors; review indirect access and full opening/swing clearances.",
                    )
                    lift = [c["name"] for c in cores if c.get("type") == "lift"]
                    accessible = [
                        r.get("id", r.get("name"))
                        for r in rooms
                        if "accessible" in str(r.get("name", "")).lower()
                        or r.get("accessible") is True
                    ]
                    emit(
                        fid,
                        "accessibility-evidence",
                        "NOT_ASSESSED",
                        "Lift and accessible-room labels are evidence inventory only; no complete step-free route, turning-space or accessible-facility assessment is encoded.",
                        {
                            **base,
                            "floor_id": fid,
                            "lift_labels": lift,
                            "accessible_room_labels": accessible,
                        },
                        "Provide coordinated step-free routes, levels, clearances and accessible facility details for qualified review.",
                    )
                    stairs = [c["name"] for c in cores if c.get("type") == "stair"]
                    exits = [d for d in floor.get("doors", []) if d.get("exterior")]
                    emit(
                        fid,
                        "egress-engineering",
                        "NOT_ASSESSED",
                        "Concept stairs/exterior doors do not establish exit capacity, travel distance, protection, discharge or emergency operation.",
                        {
                            **base,
                            "floor_id": fid,
                            "stair_labels": stairs,
                            "exterior_door_count": len(exits),
                            "planned_peak": floor.get("planned_peak"),
                            "core_basis": building.get("core_basis"),
                        },
                        "Commission occupancy-specific egress and emergency-access review; no legal thresholds are applied here.",
                    )
            if not buildings:
                emit(
                    sid,
                    "interior-readiness",
                    "NOT_ASSESSED",
                    "No owned/modelled interior geometry is supplied; external providers and unresolved sites are not fabricated.",
                    {**base, "exemption": site.get("floor_exemption")},
                    "Retain the context-only boundary until an authorized interior source exists.",
                )
    checks.sort(key=lambda c: c["id"])
    counts = Counter(c["outcome"] for c in checks)
    return {
        "schema_version": "1.0.0",
        "assessment": "ARCHITECTURAL_CONCEPT_READINESS_NOT_CODE_CERTIFICATION",
        "source_sha256": source_hashes,
        "checks": checks,
        "summary": {
            "check_count": len(checks),
            "outcomes": {key: counts[key] for key in ("PASS", "REVIEW", "FAIL", "NOT_ASSESSED")},
            "status": "ACTION_REQUIRED"
            if counts["FAIL"]
            else "REVIEW_REQUIRED"
            if counts["REVIEW"]
            else "PARTIAL_EVIDENCE",
            "engineering_certified": False,
        },
    }
