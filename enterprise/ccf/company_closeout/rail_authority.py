"""Validate recovered primary notices and the finite event-day authority review."""

import hashlib
import json
from datetime import date
from pathlib import Path

DIRECTORY = Path(__file__).parent
SOURCE = DIRECTORY / "rail_authority_review.json"


def threshold_on(day, reporting):
    day = date.fromisoformat(day) if isinstance(day, str) else day
    rule = reporting["thresholds"].get(str(day.year))
    if rule is None:
        return None
    if rule.get("effective_from") and day < date.fromisoformat(rule["effective_from"]):
        return rule["prior_usd"]
    return rule["usd"]


def validate(data, reporting):
    notices = {r["year"]: r for r in data["annual_notices"]}
    if len(data["annual_notices"]) != 3 or set(notices) != {2021, 2023, 2025}:
        raise ValueError("Original annual notice population")
    for year, amount, effective in [
        (2021, 11200, "2021-01-08"),
        (2023, 11500, "2023-01-01"),
        (2025, 12400, "2025-01-01"),
    ]:
        n = notices[year]
        if n["threshold_usd"] != amount or n["effective_from"] != effective:
            raise ValueError("Recovered threshold or effective date changed")
        if reporting["thresholds"][str(year)]["usd"] != amount:
            raise ValueError("Case threshold differs from recovered notice")
    for row in data["annual_notices"] + data["annual_cross_checks"]:
        path = DIRECTORY / row["snapshot"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Changed primary authority snapshot")
    if threshold_on("2021-01-07", reporting) != 10700 or threshold_on(
        "2021-01-08", reporting
    ) != 11200:
        raise ValueError("January 2021 transition erased")
    rules = data["rule_index"]["records"]
    by_id = {r["document_number"]: r for r in rules}
    if len(rules) != 33 or len(by_id) != 33:
        raise ValueError("Amendment index population changed")
    for ident in ["2025-12177", "2025-12179", "2025-12194"]:
        if by_id[ident]["type"] != "Proposed Rule" or by_id[ident]["effective_on"]:
            raise ValueError("Proposal promoted into effective law")
    for ident in ["2026-17790", "2026-17791"]:
        row = by_id[ident]
        if row["effective_on"] != "2026-09-30" or row["disposition"] != "PUBLISHED_FUTURE_EFFECTIVE":
            raise ValueError("Future rule promoted into completed period")
    cases = {r["event_id"]: r for r in reporting["cases"]}
    if len(data["events"]) != 14 or {r["event_id"] for r in data["events"]} != set(cases):
        raise ValueError("Event-day review population omitted or duplicated")
    for row in data["events"]:
        case = cases[row["event_id"]]
        if row["event_date"] != case["source_record"]["date"] or row["reporting_groups"] != case["groups"]:
            raise ValueError("Event-day source facts differ")
        if row["threshold_usd"] != threshold_on(row["event_date"], reporting):
            raise ValueError("Wrong event-day threshold")
    return {"primary_notices": 3, "rule_index_records": 33, "selected_events": 14,
            "future_effective_rules_preserved": 2, "unrecovered_original_notices": 0}


if __name__ == "__main__":
    print(json.dumps(validate(json.loads(SOURCE.read_text()), json.loads(
        (DIRECTORY / "rail_reporting_successor.json").read_text())), indent=2))
