"""Validate privately authored lifecycle/other-scope sources without inventing them."""

from copy import deepcopy
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


def demonstration_time(scope: dict) -> str:
    """Explicit scheduled observation; never pretend it occurred on a request."""
    zone = ZoneInfo(scope.get("timezone", "UTC"))
    supplied = scope.get("fieldwork_start")
    if supplied:
        value = datetime.fromisoformat(supplied.replace("Z", "+00:00"))
        if len(supplied) == 10:
            value = datetime.combine(value.date(), time(9), zone)
        if value.tzinfo is None:
            raise ValueError("Scheduled demonstration time requires a timezone")
        return value.isoformat()
    cutoff = datetime.fromisoformat(scope["period_end"].replace("Z", "+00:00"))
    day = cutoff.astimezone(zone).date() if cutoff.tzinfo else cutoff.date()
    holidays = set(scope.get("holidays", []))
    day += timedelta(days=1)
    while day.weekday() >= 5 or day.isoformat() in holidays:
        day += timedelta(days=1)
    return datetime.combine(day, time(9), zone).isoformat()


def requests(definitions: list, *, control_id: str, boundary_id: str) -> list[dict]:
    """Return reviewable supporting requests from already bound private definitions."""
    if not isinstance(definitions, list) or len(definitions) > 100:
        raise ValueError("Invalid authored supporting source collection")
    result, identities = [], set()
    for source in definitions:
        required = {"source_identity", "source_role", "artifact_kind", "available_by", "recipe"}
        if not isinstance(source, dict) or not required <= source.keys():
            raise ValueError("Supporting source lacks explicit provenance")
        identity = source["source_identity"]
        if not isinstance(identity, str) or not identity or identity in identities:
            raise ValueError("Supporting source identities must be distinct")
        identities.add(identity)
        role = source["source_role"]
        recipe = source["recipe"]
        rows = recipe.get("rows", [])
        columns = recipe.get("columns", [])
        if not rows or not isinstance(rows, list) or not columns:
            raise ValueError("Supporting source requires actual native rows")
        if any(set(row) != set(columns) for row in rows):
            raise ValueError("Supporting source fields must match its native schema")
        available = datetime.fromisoformat(source["available_by"].replace("Z", "+00:00"))
        if available.tzinfo is None:
            raise ValueError("Supporting source availability requires a timezone")
        seen = set()
        for row in rows:
            if not row.get("id") or row["id"] in seen:
                raise ValueError("Supporting records require unique original identities")
            seen.add(row["id"])
            if row.get("record_origin") != "AUTHORED_TRAINING_SOURCE":
                raise ValueError("Supporting sources must disclose their authored origin")
            if role in {"DRAFT_PREDECESSOR", "SUPERSEDED_VERSION"}:
                expected = "DRAFT" if role == "DRAFT_PREDECESSOR" else "SUPERSEDED"
                if row.get("lifecycle_state") != expected:
                    raise ValueError("Lifecycle source does not satisfy its declared role")
            elif role == "INDEPENDENT_OTHER_SCOPE":
                if not row.get("boundary_id") or row["boundary_id"] == boundary_id:
                    raise ValueError("Alternate source must preserve a different actual scope")
            elif role != "CURRENT_ACTION_DEMONSTRATION":
                raise ValueError("Unsupported authored source role")
            occurred = datetime.fromisoformat(row["occurred_at"].replace("Z", "+00:00"))
            if occurred.tzinfo is None or occurred > available:
                raise ValueError("Supporting source cannot precede its actual occurrence")
        result.append(
            {
                "id": control_id + "-SUPPORT-" + identity,
                "title": source["title"],
                "purpose": source["purpose"],
                "available_by": source["available_by"],
                "artifact_recipes": [deepcopy(source)],
                "coverage": {
                    "control_id": control_id,
                    "source_role": role,
                    "purpose": "Inspect explicitly labeled supporting history or alternate scope",
                    "professional_sufficiency": "NOT_ASSERTED",
                },
            }
        )
    return result
