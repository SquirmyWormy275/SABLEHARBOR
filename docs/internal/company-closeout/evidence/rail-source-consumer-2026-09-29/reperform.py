#!/usr/bin/env python3
"""Reperform the geometry-only rail planning and finance sensitivity.

This reads a proposed candidate and accepted planning inputs. It writes only to
temporary directories and does not adopt the candidate or edit source records.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from industrial.planning.forecast import build as forecast_build  # noqa: E402
from industrial.planning.operating_model import calculate, load_source  # noqa: E402


def changed_paths(before: object, after: object, prefix: str = "") -> list[str]:
    if isinstance(before, dict) and isinstance(after, dict):
        if before.keys() != after.keys():
            raise ValueError(f"Comparison schema changed at {prefix}")
        return [
            path
            for key in before
            for path in changed_paths(before[key], after[key], f"{prefix}.{key}")
        ]
    if isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            raise ValueError(f"Comparison population changed at {prefix}")
        return [
            path
            for index, (left, right) in enumerate(zip(before, after, strict=True))
            for path in changed_paths(left, right, f"{prefix}[{index}]")
        ]
    return [prefix] if before != after else []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "candidate",
        nargs="?",
        type=Path,
        default=ROOT / "geospatial/engineering_review/COMPENSATED_40_MILE_CANDIDATE.json",
    )
    args = parser.parse_args()
    raw = args.candidate.read_bytes()
    candidate = json.loads(raw)
    if candidate["schema"] != "rail-fixed-control-40-mile-candidate-v1":
        raise ValueError("Unexpected candidate schema")
    routes = candidate["candidate_route_miles"]
    if abs(sum(routes[key] for key in ("BST-MAIN", "BST-EAST", "BST-MINERAL")) - 40) > 1e-8:
        raise ValueError("Candidate does not retain 40 route-miles")

    source = load_source()
    before_main = source["rail"]["mainline_miles"]
    successor = copy.deepcopy(source)
    successor["rail"]["mainline_miles"] = routes["BST-MAIN"]
    before = calculate(source)
    after = calculate(successor)
    if len(before) != len(after) or len(before) != 180:
        raise ValueError("Unexpected planning population")
    changes = []
    for left, right in zip(before, after, strict=True):
        if (left["scenario"], left["period"]) != (right["scenario"], right["period"]):
            raise ValueError("Scenario-period drift")
        paths = changed_paths(left, right)
        if paths:
            changes.append(
                {
                    "scenario": left["scenario"],
                    "period": left["period"],
                    "changed_paths": paths,
                    "conditional_capacity_before_cars": left["capacity"]["conditional_total_rail_capacity_cars"],
                    "conditional_capacity_after_cars": right["capacity"]["conditional_total_rail_capacity_cars"],
                }
            )

    with tempfile.TemporaryDirectory(prefix="rail-40-forecast-") as directory:
        old_forecast = forecast_build(Path(directory) / "before", operating_rows=before)
        new_forecast = forecast_build(Path(directory) / "after", operating_rows=after)
    datasets = {
        name: {
            "rows": len(rows),
            "equal": rows == new_forecast["datasets"][name],
        }
        for name, rows in old_forecast["datasets"].items()
    }
    if set(datasets) != set(new_forecast["datasets"]):
        raise ValueError("Forecast dataset population changed")
    result = {
        "candidate_sha256": hashlib.sha256(raw).hexdigest(),
        "candidate_status": candidate["status"],
        "source_mainline_miles": before_main,
        "candidate_route_miles": routes,
        "planning_months": len(before),
        "train_hours_changed_months": sum(
            ".capacity.rail.train_hours_daily" in row["changed_paths"] for row in changes
        ),
        "only_train_hours_changed_months": sum(
            row["changed_paths"] == [".capacity.rail.train_hours_daily"] for row in changes
        ),
        "other_changed_months": [
            row for row in changes if row["changed_paths"] != [".capacity.rail.train_hours_daily"]
        ],
        "forecast_datasets": datasets,
        "forecast_summary_equal": old_forecast["summary"]["scenarios"]
        == new_forecast["summary"]["scenarios"],
        "scope": "Proposed geometry-only mainline length sensitivity; no candidate lead placed in service, new asset, price, cost, cash or legal right authored",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if not all(row["equal"] for row in datasets.values()):
        raise ValueError("Forecast changed; analyze exact journal/statement differences")


if __name__ == "__main__":
    main()
