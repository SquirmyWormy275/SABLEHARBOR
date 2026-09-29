"""Decision-specific tests for the dated railway source successor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("pyproj")
pytest.importorskip("shapely")

from industrial.planning import operating_model  # noqa: E402
from industrial.successors.rail_2026_09_29 import build, reconcile  # noqa: E402


def test_pinned_candidate_rejects_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corrupted = tmp_path / "candidate.json"
    corrupted.write_bytes(build.CANDIDATE.read_bytes() + b" ")
    monkeypatch.setattr(build, "CANDIDATE", corrupted)
    with pytest.raises(ValueError, match="Pinned railway input changed"):
        build.checked_inputs()


def test_dated_source_preserves_population_and_finance(tmp_path: Path) -> None:
    original_sha = build.digest(build.SOURCE / "operations.json")
    network_sha = build.digest(build.SOURCE / "geography/network.geojson")
    result = build.build(tmp_path)
    source = tmp_path / "source"
    ops = json.loads((source / "operations.json").read_text())
    network = json.loads((source / "geography/network.geojson").read_text())
    crosswalk = json.loads((tmp_path / "asset_crosswalk.json").read_text())
    assert build.digest(build.SOURCE / "operations.json") == original_sha
    assert build.digest(build.SOURCE / "geography/network.geojson") == network_sha
    assert result["counts"]["route_segments"] == 11
    assert result["counts"]["structures"] == 26
    assert {f["id"] for f in network["features"]} == {*build.ROUTES, "ROAD-RW-01"}
    assert sum(result["route_miles"].values()) == 40
    assert ops["geography"]["historical_route_epochs"][0]["route_miles"] is None
    assert ops["geography"]["historical_route_epochs"][1]["surviving_route_miles_low"] == 14
    assert ops["geography"]["historical_route_epochs"][1]["surviving_route_miles_high"] == 16
    assert ops["interface"]["direct_uranium_custody"] == "OPEN_GATED"
    for route in build.ROUTES:
        segments = [r for r in ops["track_segments"] if r.get("route_id") == route]
        assert sum(r["length_miles"] for r in segments) == pytest.approx(result["route_miles"][route])
        assert segments[0]["mp_start"] == 0
        assert segments[-1]["mp_end"] == result["route_miles"][route]
        for left, right in zip(segments, segments[1:]):
            assert left["mp_end"] == right["mp_start"]
            assert left["boundary_end_lon_lat"] == right["boundary_start_lon_lat"]
    assert {r["id"] for r in crosswalk["track_segments"]} == {
        r["id"] for r in ops["track_segments"] if r.get("route_id") in build.ROUTES
    }
    assert {r["id"] for r in crosswalk["structures"]} == {
        r["id"] for r in ops["structures"]
    }
    assert max(r["offset_m"] for r in crosswalk["structures"]) <= 0.02
    old_ops = json.loads((build.SOURCE / "operations.json").read_text())
    assert {r["id"] for r in old_ops["structures"]} == {r["id"] for r in ops["structures"]}
    assert {r["id"] for r in old_ops["track_segments"]} == {r["id"] for r in ops["track_segments"]}
    new_plan = json.loads((tmp_path / "planning_source.json").read_text())
    exported = json.loads((tmp_path / "planning_operations/operating_rows.json").read_text())
    assert operating_model.calculate(new_plan) == exported  # source map order is substantive
    proof = reconcile.compare(tmp_path)
    assert proof["planning_months"] == 180
    assert proof["downside_2027_03_conditional_capacity_cars"] == 1008
    assert proof["modeled_journal_cash_tax_delta_usd"] == 0
    assert proof["forecast_datasets"]["journal"]["rows"] == 123716
    assert len(proof["forecast_datasets"]) == 13
