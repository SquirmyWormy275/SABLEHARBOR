"""Verify source-backed activity boundaries independently of rendering."""

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).with_name("activity_applicability.json")


def validate(data, root=ROOT):
    rows = data["records"]
    if len(rows) != len({r["id"] for r in rows}) or {r["id"] for r in rows} != set(
        data["required_boundary_ids"]
    ):
        raise ValueError("Omitted or duplicate activity boundary")
    if {r["business_unit"] for r in rows} != set(data["required_units"]):
        raise ValueError("Omitted business unit/corporate boundary")
    legal = {
        e["entity_id"]
        for e in json.loads((root / "industrial/source/entities.json").read_text())["entities"]
        if e["entity_id"] != "NMI"
    }
    for row in rows:
        if not set(row["legal_entities"]) <= legal:
            raise ValueError("Capability/external party incorrectly promoted to legal entity")
        if row["available_on"] < data["authored_on"]:
            raise ValueError("Review promoted into earlier availability")
        if row["performance"] == "PASS":
            raise ValueError("Applicability review is not operating effectiveness")
        if not row["accountable_role"] or not row["duty"] or not row["population_definition"]:
            raise ValueError("Unscoped duty")
        source = root / row["source_path"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != row["source_sha256"]:
            raise ValueError("Stale controlling source")
        selector = row["selector"]
        if selector:
            values = json.loads(source.read_text())
            if "unit" in selector:
                values = [r for r in values if r["unit"] == selector["unit"]]
            elif "key" in selector:
                values = values[selector["key"]]
            elif "site_id" in selector:
                values = [r for r in values["sites"] if r["id"] == selector["site_id"]]
                if any(
                    r["operating"]
                    or (row["id"] != "APP-OWNED-SITE-ACTIVATION" and r["contract_executed"])
                    for r in values
                ):
                    raise ValueError("Planned site boundary needs current activity review")
            if len(values) != row["population_count"]:
                raise ValueError("Declared source population does not reconcile")
        if row["performance"] == "FUTURE_DUE" and row["scenario"] == "CURRENT_SOURCE_REVIEW":
            raise ValueError("Future occurrence requires explicit scenario/period")
    return {
        "activity_boundaries": len(rows),
        "unit_boundaries": len(data["required_units"]),
        "performance_states": dict(Counter(r["performance"] for r in rows)),
        "scope": "APPLICABILITY_REVIEW_NOT_FULL_STATUTORY_OCCURRENCE_POPULATION",
    }


if __name__ == "__main__":
    print(json.dumps(validate(json.loads(SOURCE.read_text())), indent=2, sort_keys=True))
