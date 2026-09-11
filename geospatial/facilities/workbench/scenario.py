"""Capacity experiments; no employee census or authority mutation."""

import math

FIELDS = (
    "assigned_workers",
    "shared_workers",
    "attendance_percent",
    "sharing_ratio",
    "touchdown_visitors",
    "other_attendees",
)


def baseline(data):
    return {
        "scenario_id": "SCENARIO-BASELINE",
        "horizon": 2026,
        "assumption": "Source capacity comparison, not observed staff or attendance.",
        "source_sha256": data["source_sha256"],
        "floors": [{"id": f["id"], **f["defaults"]} for f in data["floors"]],
        "campus": {
            "trainees": data["campus"]["trainee_peak"],
            "resident_trainees": data["campus"]["default_resident_trainees"],
            "resident_other": data["campus"]["resident_capacity"]
            - data["campus"]["default_resident_trainees"],
        },
    }


def evaluate(data, scenario):
    if not isinstance(scenario, dict):
        return {"status": "INVALID", "errors": ["Scenario must be an object."]}
    errors = []
    if not isinstance(scenario.get("scenario_id"), str) or not scenario["scenario_id"].strip():
        errors.append("A scenario ID is required.")
    if scenario.get("source_sha256") != data["source_sha256"]:
        errors.append("Scenario baseline is stale or missing; rebase and review assumptions.")
    if not isinstance(scenario.get("assumption"), str) or not scenario["assumption"].strip():
        errors.append("A planning assumption is required.")
    if scenario.get("horizon") not in (2026, 2031, 2036):
        errors.append("Horizon must be 2026, 2031 or 2036; no automatic growth is assumed.")
    sources = {f["id"]: f for f in data["floors"]}
    rows = scenario.get("floors", [])
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        return {"status": "INVALID", "errors": errors + ["floors must be records"]}
    ids = [r.get("id") for r in rows]
    if any(not isinstance(i, str) for i in ids):
        return {"status": "INVALID", "errors": errors + ["Floor IDs must be strings."]}
    if len(ids) != len(set(ids)) or set(ids) != set(sources):
        errors.append(
            "Supply each known floor exactly once; unknown or missing floors are rejected."
        )
    for row in rows:
        for key in FIELDS:
            value = row.get(key)
            source = sources.get(row.get("id"), {})
            if value is None and source.get("assigned_desks") is None:
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                errors.append(f"{row.get('id')} invalid {key}")
            elif key == "attendance_percent" and value > 100:
                errors.append("Attendance must be between 0 and 100 percent.")
            elif key == "sharing_ratio" and value < 1:
                errors.append("Sharing ratio must be at least one worker per shared desk.")
            elif key not in ("attendance_percent", "sharing_ratio") and value != int(value):
                errors.append("People must be whole numbers.")
    campus = scenario.get("campus", {})
    if not isinstance(campus, dict):
        errors.append("campus must be a record")
        campus = {}
    for key in ("trainees", "resident_trainees", "resident_other"):
        v = campus.get(key)
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            errors.append(f"Invalid campus {key}")
    if errors:
        return {"status": "INVALID", "errors": errors}
    if campus["resident_trainees"] > campus["trainees"]:
        return {
            "status": "INVALID",
            "errors": ["Resident trainees must be a subset of day trainees."],
        }
    results = []
    buildings = {}
    sites = {}
    for row in rows:
        source = sources[row["id"]]
        if any(row.get(k) is None for k in FIELDS) or source["assigned_desks"] is None:
            result = {
                "id": row["id"],
                "status": "UNKNOWN",
                "day_attendees": None,
                "reason": "Fitted capacity or scenario demand unestablished; unknown is not zero.",
            }
        else:
            shared = max(
                math.ceil(row["shared_workers"] / row["sharing_ratio"]),
                math.ceil(row["shared_workers"] * row["attendance_percent"] / 100),
            )
            assigned = row["assigned_workers"]
            learners = campus["trainees"] if row["id"] == data["campus"]["training_floor_id"] else 0
            day = (
                math.ceil(assigned * row["attendance_percent"] / 100)
                + math.ceil(row["shared_workers"] * row["attendance_percent"] / 100)
                + row["touchdown_visitors"]
                + row["other_attendees"]
                + learners
            )
            constraints = []
            for label, demand, capacity in [
                ("assigned_desks", assigned, source["assigned_desks"]),
                ("shared_desks", shared, source["shared_desks"]),
                ("touchdown_seats", row["touchdown_visitors"], source["touchdown_seats"]),
            ]:
                if demand > capacity:
                    constraints.append(
                        {
                            "category": label,
                            "demand": demand,
                            "capacity": capacity,
                            "excess": demand - capacity,
                        }
                    )
            if source["planned_peak"] is not None and day > source["planned_peak"]:
                constraints.append(
                    {
                        "category": "modelled_day_peak",
                        "demand": day,
                        "capacity": source["planned_peak"],
                        "excess": day - source["planned_peak"],
                    }
                )
            result = {
                "id": row["id"],
                "status": "CONSTRAINT" if constraints else "WITHIN_MODEL",
                "day_attendees": day,
                "required_assigned_desks": assigned,
                "required_shared_desks": shared,
                "constraints": constraints,
            }
        result.update({"building_id": source["building_id"], "site_id": source["site_id"]})
        results.append(result)
        for grouped, key in [(buildings, source["building_id"]), (sites, source["site_id"])]:
            group = grouped.setdefault(
                key, {"known_day_attendees": 0, "unknown_floors": [], "constraint_floors": []}
            )
            if result["day_attendees"] is None:
                group["unknown_floors"].append(row["id"])
            else:
                group["known_day_attendees"] += result["day_attendees"]
            if result["status"] == "CONSTRAINT":
                group["constraint_floors"].append(row["id"])
    night = campus["resident_trainees"] + campus["resident_other"]
    capacity = data["campus"]
    campus_constraints = []
    if campus["trainees"] > capacity["trainee_peak"]:
        campus_constraints.append("Day cohort exceeds the single simultaneous training envelope.")
    if night > capacity["resident_capacity"]:
        campus_constraints.append("Night residence exceeds single-room capacity.")
    return {
        "status": "CONSTRAINT"
        if campus_constraints or any(r["status"] == "CONSTRAINT" for r in results)
        else "WITHIN_KNOWN_MODEL",
        "authority": "EXPERIMENT_ONLY_NOT_CANON_OR_COMPLIANCE",
        "errors": [],
        "floors": results,
        "buildings": buildings,
        "sites": sites,
        "campus": {
            "day_people": sites[capacity["site_id"]]["known_day_attendees"],
            "night_residents": night,
            "resident_trainees_subset": campus["resident_trainees"],
            "constraints": campus_constraints,
        },
        "limits": [
            "No enterprise total is inferred from unknown floors.",
            "Day and night populations are separate; residents do not add to day trainees.",
            "Desk sharing never reduces simultaneous people.",
            "Assigned desks remain reserved even when their assigned users are absent.",
            "Within model is not safety, code or engineering approval.",
        ],
    }
