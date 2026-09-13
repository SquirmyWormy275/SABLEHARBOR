import json
from pathlib import Path
import pytest
from geospatial.chronology.build import build, period, pointer
from geospatial.chronology.operations_review import review


def test_history_preserves_evidence_and_temporal_meaning():
    result = build()
    events = {r["event_id"]: r for r in result["events"]}
    assert len(events) == len(result["events"]) == 72
    assert len(result["sites"]) == 34
    assert not any(e["occupancy_interval_established"] for e in events.values())
    lease = events["OBS-KLEIN-LEASE-2021"]
    assert "## 7.4 The Klein shop — 2021" in lease["evidence"]["evidence"]
    assert "Klein leases" in lease["evidence"]["evidence"]
    assert lease["precision"] == "YEAR"
    assert lease["earliest"] == "2021-01-01" and lease["latest"] == "2021-12-31"
    assert (
        next(s for s in result["sites"] if s["object_id"] == "SH-SITE-0002")["occupancy_interval"]
        is None
    )
    assert events["SH-EVT-0008"]["evidence"]["evidence"]["ownership_effective_on"] == "2026-01-07"
    assert all(e["object_ids"] == [] for e in events.values() if e["kind"] == "SAFETY_EVENT")
    assert not any("2024 relocation" in e["title"].lower() for e in events.values())


def test_route_history_does_not_backfill_unknown_alignment():
    records = build()["route_features"]

    def active(day):
        return [
            r
            for r in records
            if r["valid_from"] <= day and (not r["valid_to"] or day < r["valid_to"])
        ]

    assert not active("1898-04-06") and not active("1954-07-01")
    assert not active("1968-10-13")
    assert len(active("1968-10-14")) == 3
    assert len(active("1972-05-08")) == 4
    assert len(active("1986-09-19")) == 5


def test_period_bounds_are_explicit_and_invalid_dates_rejected():
    assert period("2022–2025")["latest"] == "2025-12-31"
    assert period("2024-02-29")["precision"] == "DAY"
    for value in ["2023-02-29", "2025–2022", "around then", "2024-13-01"]:
        with pytest.raises(ValueError):
            period(value)
    assert pointer({"a/b": {"~key": [17]}}, "/a~1b/~0key/0") == 17


def test_operations_review_is_reproducible_and_disjoint():
    raw, summary, rows = review()
    root = Path(__file__).resolve().parents[1] / "chronology"
    assert raw == (root / "OPERATIONS_REVIEW.csv.gz").read_bytes()
    assert summary == json.loads((root / "OPERATIONS_REVIEW.json").read_text())
    assert len(rows) == len({r["occurrence_id"] for r in rows}) == 295
    assert summary["remaining_occurrences"] == 8666
    allocations = [
        r for r in rows if r["source_locator"].startswith("/contract_facility_assignments/")
    ]
    assert len(allocations) == 74
    assert len({r["containing_record_locator"] for r in allocations}) == 30
    assert all(r["source_sha256"] == summary["source_sha256"] for r in rows)
