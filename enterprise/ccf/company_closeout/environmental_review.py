"""Reperform a bounded environmental review from the existing Red Wash generator."""

import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def review(root=ROOT):
    source = root / "red_wash/generated/environmental_monitoring.csv"
    if not source.exists():
        raise ValueError("Run red_wash/tools/validate_red_wash_record.py --generate first")
    rows = list(csv.DictReader(source.open()))
    expected = {
        (f"{year}-Q{quarter}", station)
        for year in range(2019, 2027)
        for quarter in range(1, 3 if year == 2026 else 5)
        for station in ("MW-04", "MW-09", "MW-12", "MW-17", "MW-21", "TAIL-UD-1")
    }
    actual = [(r["period"], r["station"]) for r in rows]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError("Environmental period/station population omitted or duplicated")
    observations = []
    for station in ("MW-04", "MW-09", "MW-12", "MW-17", "MW-21", "TAIL-UD-1"):
        values = {(r["period"], r["station"]): r for r in rows}
        baseline = [r for r in rows if r["station"] == station and r["period"].startswith("2019-")]
        latest = values[("2026-Q2", station)]
        mean = sum(Decimal(r["uranium_mg_l"]) for r in baseline) / 4
        delta = Decimal(latest["uranium_mg_l"]) - mean
        observations.append(
            {
                "station": station,
                "baseline_2019_mean_uranium_mg_l": str(mean),
                "latest_period": "2026-Q2",
                "latest_uranium_mg_l": latest["uranium_mg_l"],
                "delta_mg_l": str(delta),
                "internal_trend_flag": delta > Decimal("0.005"),
            }
        )
    return {
        "source_path": str(source.relative_to(root)),
        "generator_source_hashes": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in (
                "red_wash/tools/build_red_wash_package.py",
                "red_wash/source/core_operating_data.json",
                "red_wash/source/aru_bst_bridge.json",
                "red_wash/source/external_source_register.csv",
            )
        },
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "population_count": len(rows),
        "period_station_units": len(expected),
        "period_start": "2019-Q1",
        "period_end": "2026-Q2",
        "quarter_2026_q3_status": "FUTURE_DUE_NOT_COMPLETE_AT_AUGUST_CUTOFF",
        "observations": observations,
        "threshold_basis": "New synthetic internal investigation trigger: latest minus 2019 annual mean > 0.005 mg/L. Not a statutory limit, background finding or permit exceedance.",
        "outcome": "INVESTIGATION_REQUIRED",
        "liability_conclusion": "NOT_DETERMINED",
    }


if __name__ == "__main__":
    print(json.dumps(review(), indent=2, sort_keys=True))
