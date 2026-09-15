"""Reconcile incident facts, distinct cost concepts and synthetic reporting dates."""

import calendar
import json
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

SOURCE = Path(__file__).with_name("rail_reporting_successor.json")


def validate(data):
    base = json.loads(SOURCE.with_name("obligation_census.json").read_text())
    original = {
        r["id"]: r["source_record"] for r in base["records"] if r["id"].startswith("BST-EVT")
    }
    if len(data["cases"]) != 14 or {r["event_id"] for r in data["cases"]} != set(original):
        raise ValueError("Rail event population omitted or duplicated")
    if data["available_on"] < data["authored_on"] or data["available_on"] != "2026-09-15":
        raise ValueError("Retrospective evidence availability")
    for row in data["cases"]:
        s = original[row["event_id"]]
        if s != row["source_record"]:
            raise ValueError("Accepted historical fact changed")
        if D(row["repair_cost_usd"]) + D(row["other_claim_clearing_or_indirect_usd"]) != D(
            s["case_claim_or_damage_usd"]
        ):
            raise ValueError("Claim/repair decomposition changed original total")
        day = date.fromisoformat(s["date"])
        groups = []
        threshold = data["thresholds"].get(str(day.year), {}).get("usd")
        if row["crossing"]:
            groups.append("I")
        if threshold is not None and D(row["repair_cost_usd"]) > threshold:
            groups.append("II")
        if row["reportable_injury"]:
            groups.append("III")
        if row["groups"] != groups or bool(s["recordable_persons"]) != row["reportable_injury"]:
            raise ValueError("Reporting groups disagree with incident facts")
        if "grade crossing" == s["category"] and not row["crossing"]:
            raise ValueError("Crossing omitted on private-status pretext")
        if groups:
            due = date(
                day.year, day.month, calendar.monthrange(day.year, day.month)[1]
            ) + timedelta(days=30)
            filed = date.fromisoformat(row["modeled_submitted_on"])
            expected = "MODELED_SUBMITTED_LATE" if filed > due else "MODELED_SUBMITTED"
            if str(due) != row["monthly_due_on"] or row["filing_state"] != expected or filed < day:
                raise ValueError("Monthly due or late filing state wrong")
            if row["form_families"] != [
                {"I": "F6180.57", "II": "F6180.54", "III": "F6180.55a"}[g] for g in groups
            ]:
                raise ValueError("Wrong incident form family")
        elif (
            row["modeled_submitted_on"]
            or row["filing_state"] != "NO_PART225_GROUP_TRIGGER_IN_AUTHORED_FACTS"
        ):
            raise ValueError("Unsupported filing state")
        if row["acknowledgement_state"] != "NOT_ASSERTED":
            raise ValueError("Invented regulator acknowledgment")
    late = next(r for r in data["cases"] if r["event_id"] == "BST-EVT-006")
    claim = next(r for r in data["cases"] if r["event_id"] == "BST-EVT-009")
    if (
        late["filing_state"] != "MODELED_SUBMITTED_LATE"
        or claim["source_record"]["status"] != "open claim"
    ):
        raise ValueError("Adverse historical case erased")
    return {
        "cases": 14,
        "states": dict(Counter(r["filing_state"] for r in data["cases"])),
        "incident_form_records": sum(len(r["groups"]) for r in data["cases"]),
        "open_liability_claims": 1,
        "scope": "SELECTED_CASES; EVENT_DAY_AUTHORITY_RESIDUAL_RETAINED",
    }


if __name__ == "__main__":
    print(json.dumps(validate(json.loads(SOURCE.read_text())), indent=2))
