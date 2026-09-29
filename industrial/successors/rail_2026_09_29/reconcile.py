#!/usr/bin/env python3
"""Separate exact regeneration/comparison for the dated rail case."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from industrial.planning import forecast, operating_model  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = ROOT / "industrial/generated/successors/rail_2026_09_29"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def without_availability(value: object) -> object:
    if isinstance(value, dict):
        return {k: without_availability(v) for k, v in value.items() if k != "available_at"}
    if isinstance(value, list):
        return [without_availability(v) for v in value]
    return value


def compare(output: Path = OUT) -> dict:
    old = operating_model.calculate(operating_model.load_source())
    new_source = json.loads((output / "planning_source.json").read_text())
    new = operating_model.calculate(new_source)
    exported = json.loads((output / "planning_operations/operating_rows.json").read_text())
    if new != exported or len(old) != 180 or len(new) != 180:
        raise ValueError("Successor operating export is stale or has wrong population")
    changes = []
    for a, b in zip(old, new, strict=True):
        key = (a["scenario"], a["period"])
        if key != (b["scenario"], b["period"]):
            raise ValueError("Scenario-period population changed")
        left = without_availability(a)
        right = without_availability(b)
        old_hours = left["capacity"]["rail"].pop("train_hours_daily")
        new_hours = right["capacity"]["rail"].pop("train_hours_daily")
        if left != right:
            raise ValueError(f"Operating economics/capacity changed beyond train hours: {key}")
        if old_hours == new_hours:
            raise ValueError(f"Expected a train-hour consequence: {key}")
        changes.append({"scenario": key[0], "period": key[1],
                        "old_hours": old_hours, "new_hours": new_hours})
    if new_source["available_at"] <= operating_model.load_source()["available_at"]:
        raise ValueError("Successor availability did not advance")
    finance_source = json.loads((output / "financial_source.json").read_text())
    with tempfile.TemporaryDirectory(prefix="rail-successor-reperform-") as temp:
        a = forecast.build(Path(temp) / "old", operating_rows=old)
        b = forecast.build(Path(temp) / "new", operating_rows=new, source=finance_source)
        datasets = {}
        for name, old_rows in a["datasets"].items():
            new_rows = b["datasets"].get(name)
            if new_rows is None or without_availability(old_rows) != without_availability(new_rows):
                raise ValueError(f"Material finance row drift: {name}")
            exported_path = output / "planning_forecast" / f"{name}.csv"
            if sha(exported_path) != sha(Path(temp) / "new" / f"{name}.csv"):
                raise ValueError(f"Stale successor finance export: {name}")
            datasets[name] = {"rows": len(old_rows), "economic_rows_equal": True,
                              "successor_export_sha256": sha(exported_path)}
        if set(datasets) != set(b["datasets"]):
            raise ValueError("Forecast dataset set changed")
        if without_availability(a["summary"]["scenarios"]) != without_availability(b["summary"]["scenarios"]):
            raise ValueError("Scenario finance summary changed")
    result = {
        "status": "SEPARATE_REGENERATION_COMPARISON_PASSED",
        "source_selector_sha256": sha(HERE / "source.json"),
        "candidate_report_sha256": sha(ROOT / "geospatial/engineering_review/COMPENSATED_40_MILE_CANDIDATE.json"),
        "candidate_geojson_sha256": sha(ROOT / "geospatial/engineering_review/COMPENSATED_40_MILE_CANDIDATE.geojson"),
        "planning_months": len(changes),
        "only_operating_differences": ["available_at", "capacity.rail.train_hours_daily"],
        "downside_2027_03_conditional_capacity_cars": next(
            r["capacity"]["conditional_total_rail_capacity_cars"]
            for r in new if r["scenario"] == "downside" and r["period"] == "2027-03"
        ),
        "base_2027_01_train_hours_before_after": [changes[0]["old_hours"], changes[0]["new_hours"]],
        "forecast_datasets": datasets,
        "modeled_journal_cash_tax_delta_usd": 0,
        "scope": "Complete three-route geometry with inherited branch switching; no proposed leads or new rights/costs placed in service. Metadata availability advances to successor date.",
    }
    if result["downside_2027_03_conditional_capacity_cars"] != 1008:
        raise ValueError("Complete-route conditional capacity threshold changed")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = compare()
    if args.write:
        (HERE / "reperform-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
