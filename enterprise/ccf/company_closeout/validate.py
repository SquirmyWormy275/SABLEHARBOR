"""Validate exact source coverage and temporal boundaries of the review census."""

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).with_name("obligation_census.json")


def validate(data, root=ROOT):
    populations = {
        "red_wash_permit_register": (
            "red_wash/source/core_operating_data.json",
            "permit_register",
            "permit_id",
        ),
        "rail_safety_events": ("industrial/source/operations.json", "safety_events", "id"),
    }
    if data["available_on"] < data["authored_on"]:
        raise ValueError("New review cannot be available before authorship")
    if len({r["id"] for r in data["records"]}) != len(data["records"]):
        raise ValueError("Duplicate population member")
    for population, (path, key, id_key) in populations.items():
        raw = (root / path).read_bytes()
        sources = {r[id_key]: r for r in json.loads(raw)[key]}
        records = [r for r in data["records"] if r["population"] == population]
        if {r["id"] for r in records} != set(sources):
            raise ValueError("Omitted or unexpected population member")
        for row in records:
            if (
                row["source_path"] != path
                or row["source_sha256"] != hashlib.sha256(raw).hexdigest()
            ):
                raise ValueError("Changed source with stale review")
            if row["source_record"] != sources[row["id"]]:
                raise ValueError("Source facts changed in review")
            if row["performance"] != "MISSING_EVIDENCE":
                raise ValueError(
                    "This review has no performance evidence; successor review required"
                )
            if row["due_date"] is not None:
                raise ValueError("No due date established by this review")
            for evidence in row["evidence"]:
                if (
                    hashlib.sha256((root / evidence["path"]).read_bytes()).hexdigest()
                    != evidence["sha256"]
                ):
                    raise ValueError("Stale evidence relationship")
    if any(r["population"] not in populations for r in data["records"]):
        raise ValueError("Unknown population")
    return dict(Counter(r["population"] for r in data["records"]))


if __name__ == "__main__":
    print(json.dumps(validate(json.loads(SOURCE.read_text())), sort_keys=True))
