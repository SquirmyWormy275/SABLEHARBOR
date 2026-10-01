"""Validate declared synthetic performance without asserting external compliance."""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from .environmental_review import review

DIRECTORY = Path(__file__).parent


def available_records(data, known_on):
    return data["examinations"] if known_on >= data["available_on"] else []


def validate_workplace(data):
    def instant(value):
        return datetime.fromisoformat(value)

    if data["available_on"] < data["authored_on"]:
        raise ValueError("Retrospective authorship cannot become earlier available evidence")
    expected = {(r["date"], r["shift"], r["place"]) for r in data["expected_population"]}
    actual = [(r["date"], r["shift"], r["place"]) for r in data["examinations"]]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError("Examination population omission or duplicate")
    qualifications = {r["id"]: r for r in data["qualification_records"]}
    for record in data["examinations"]:
        q = qualifications[record["designation_id"]]
        if q["person_id"] != record["examiner"] or record["place"] not in q["scope"]:
            raise ValueError("Examiner identity or scope not authorized")
        if not q["effective_on"] <= record["date"] <= q["expires_on"]:
            raise ValueError("Unqualified assignment")
        if q["legal_entity"] != record["legal_entity"]:
            raise ValueError("Wrong legal employer")
        if (
            not instant(record["examined_at"])
            <= instant(record["released_at"])
            <= instant(record["work_started_at"])
        ):
            raise ValueError("Work released before examination")
        if (
            not instant(record["examined_at"])
            <= instant(record["recorded_at"])
            < instant(record["shift_end"])
        ):
            raise ValueError("Missing or late shift record")
        if record["corrective_action"]:
            if not (
                instant(record["examined_at"])
                <= instant(record["miners_notified_at"])
                <= instant(record["corrected_at"])
                <= instant(record["released_at"])
            ):
                raise ValueError("Hazard released before notification and correction")
    if data["review"]["preparer_id"] == data["review"]["reviewer_id"]:
        raise ValueError("Self review")
    for attempt in data["attempts"]:
        if attempt["state"] == "BLOCKED_EXPIRED_DESIGNATION" and attempt["authorized_release"]:
            raise ValueError("Blocked assignment cannot release work")
    return {"examinations": len(actual), "blocked_assignments": len(data["attempts"])}


def validate_environment(data):
    if data["environmental_review"]["result"] != review():
        raise ValueError("Stale environmental review")
    r = data["environmental_review"]["reviewer_reperformance"]
    total = sum(map(Decimal, r["mw17_2019_uranium_mg_l"]))
    if total != Decimal(r["sum_mg_l"]) or total / 4 != Decimal(r["mean_mg_l"]):
        raise ValueError("Independent arithmetic does not reconcile")
    if Decimal("0.0232") - total / 4 != Decimal(r["latest_minus_mean_mg_l"]):
        raise ValueError("Independent latest comparison does not reconcile")
    permits = {f"RW-PER-{i:03}" for i in range(1, 15)}
    if (
        len(data["conditions"]) != len(permits)
        or {r["permit_id"] for r in data["conditions"]} != permits
    ):
        raise ValueError("Permit condition population incomplete")
    return {
        "conditions": len(permits),
        "monitoring_rows": data["environmental_review"]["result"]["population_count"],
    }


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "workplace": validate_workplace(
                    json.loads((DIRECTORY / "workplace_examinations.json").read_text())
                ),
                "environment": validate_environment(
                    json.loads((DIRECTORY / "permit_condition_performance.json").read_text())
                ),
            },
            sort_keys=True,
        )
    )
