"""Reperform newly authored permit condition populations and dated risk mappings."""

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

from enterprise.ccf.operations.testing import ADAPTERS
from enterprise.ccf.registry import compile_registry
from enterprise.operations.controls import _registry, _scope

DIRECTORY = Path(__file__).parent
ROOT = DIRECTORY.parents[2]


def read(name):
    return json.loads((DIRECTORY / name).read_text())


def validate_instruments(data):
    if data["authored_on"] != "2026-09-15" or data["available_on"] < data["authored_on"]:
        raise ValueError("Retrospective instrument availability")
    conditions = data["conditions"]
    if len(conditions) != 14 or {c["permit_id"] for c in conditions} != {
        f"RW-PER-{i:03}" for i in range(1, 15)
    }:
        raise ValueError("Permit condition population")
    if [c["id"] for c in conditions] != [f"RW-AUG-COND-{i:03}" for i in range(1, 15)]:
        raise ValueError("Condition identities/order changed")
    if conditions[7]["expected_dates"] != [f"2026-08-{i:02}" for i in range(1, 32)]:
        raise ValueError("Daily Cell 1 population omission")
    expected = {
        (c["id"], day, member)
        for c in conditions
        for day in c["expected_dates"]
        for member in c["population_members"]
    }
    actual = [(r["condition_id"], r["event_on"], r["member"]) for r in data["evidence"]]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError("Missing or duplicate expected occurrence")
    for c in conditions:
        if c["expected_occurrences"] != len(c["expected_dates"]) * len(c["population_members"]):
            raise ValueError("Wrong condition denominator")
        if c["term_origin"] != "NEWLY_AUTHORED_SYNTHETIC_INSTRUMENT_DETAIL":
            raise ValueError("Synthetic instrument origin promoted")
    for r in data["evidence"]:
        if (
            not "2026-08-01" <= r["event_on"] <= "2026-08-31"
            or r["available_on"] < data["authored_on"]
        ):
            raise ValueError("Wrong period or premature evidence")
        if not r["preparer_id"] or r["preparer_id"] == r["reviewer_id"]:
            raise ValueError("Missing or self review")
        if r["state"] not in {
            "PERFORMED",
            "FAILED_CORRECTED",
            "MISSING_EVIDENCE",
            "PERFORMED_WITH_EXCEPTION",
            "BLOCKED",
        }:
            raise ValueError("Unsupported performance state")
        if (
            r["state"] == "FAILED_CORRECTED"
            and not r["event_on"] <= r["action"]["corrected_on"] <= "2026-08-31"
        ):
            raise ValueError("Correction timing")
        if (
            r["state"] in {"MISSING_EVIDENCE", "PERFORMED_WITH_EXCEPTION", "BLOCKED"}
            and r["action"]["state"] != "OPEN"
        ):
            raise ValueError("Unresolved exception erased")
    wells = {"MW-04", "MW-09", "MW-12", "MW-17", "MW-21", "TAIL-UD-1"}
    if set(conditions[6]["population_members"]) != wells:
        raise ValueError("Station identities differ from source monitoring population")
    if set(conditions[3]["population_members"]) != {f"RW-{i:04}" for i in range(13, 141)}:
        raise ValueError("RWH badge population differs from declared employees")
    workplace = read("workplace_examinations.json")
    if set(conditions[8]["population_members"]) != {
        r["place"] + " / " + r["shift"] for r in workplace["expected_population"]
    }:
        raise ValueError("Workplace evidence join changed")
    rows = {(r["condition_id"], r["member"]): r for r in data["evidence"]}
    if rows[("RW-AUG-COND-007", "MW-17")]["state"] != "PERFORMED_WITH_EXCEPTION":
        raise ValueError("MW17 unresolved trend cleared")
    if (
        rows[("RW-AUG-COND-011", "C07 selected yellowcake shipment authority gate")]["state"]
        != "BLOCKED"
    ):
        raise ValueError("Uranium transport authority invented")
    dates = [
        date.fromisoformat(x)
        for x in ["2026-07-31", *conditions[9]["expected_dates"], "2026-09-04"]
    ]
    if any((b - a).days > 7 for a, b in zip(dates, dates[1:], strict=False)):
        raise ValueError("Magazine seven-day boundary gap")
    if any(
        r["due_on"] <= "2026-08-31" or r["state"] != "FUTURE_DUE" for r in data["future_duties"]
    ):
        raise ValueError("Future duty improperly classified")
    zero = data["zero_occurrence_register"]
    if (
        len(zero) != 1
        or zero[0]["permit_id"] != "RW-PER-002"
        or zero[0]["count"] != 0
        or conditions[1]["expected_occurrences"] != 0
    ):
        raise ValueError("No-occurrence scope changed")
    return {
        "conditions": 14,
        "occurrences": len(actual),
        "outcomes": dict(Counter(r["state"] for r in data["evidence"])),
        "future_due": len(data["future_duties"]),
        "no_occurrence_populations": 1,
        "workplace_joins_not_additional_exams": 4,
    }


def validate_risks(data, native=None):
    native = native or compile_registry()
    controls = {r["id"]: r for r in native["records"] if r["kind"] == "control"}
    risks = {r["id"] for r in native["records"] if r["kind"] == "risk"}
    missing = {cid for cid, r in controls.items() if not r["data"]["risk_ids"]}
    mappings = data["mappings"]
    if len(mappings) != len(missing) or {m["control_id"] for m in mappings} != missing:
        raise ValueError("Supplement no longer matches unmapped native controls; review successor")
    if any(m["risk_id"] not in risks or not m["rationale"] for m in mappings):
        raise ValueError("Unsupported risk mapping")
    return {
        "native_controls": len(controls),
        "native_unmapped": len(missing),
        "supplemental_mappings": len(mappings),
        "combined_unmapped": 0,
        "applicability_rows": sum(r["kind"] == "applicability" for r in native["records"]),
        "applicability_states": dict(
            Counter(
                r["data"]["decision_state"]
                for r in native["records"]
                if r["kind"] == "applicability"
            )
        ),
        "automated_adapters": len(ADAPTERS),
        "forecast_control_unit_combinations": sum(len(_scope(r)) for r in _registry()),
        "forecast_expected_occurrences": sum(len(_scope(r)) for r in _registry()) * 3 * 60,
    }


def report():
    return {
        "permit_performance": validate_instruments(
            read("synthetic_permit_instruments_august.json")
        ),
        "ccf_denominators": validate_risks(read("risk_mapping_supplement.json")),
        "source_hashes": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                DIRECTORY / "synthetic_permit_instruments_august.json",
                DIRECTORY / "risk_mapping_supplement.json",
                ROOT / "docs/controls/CCF_RISK_CONTROL_TRACEABILITY_MATRIX_v0.1.md",
                ROOT / "docs/structured/business-lines/interfaces.json",
            ]
        },
    }


if __name__ == "__main__":
    print(json.dumps(report(), indent=2))
