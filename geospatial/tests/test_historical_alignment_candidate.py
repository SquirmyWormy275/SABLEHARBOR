"""Boundary tests for the fictional early-rail alignment alternative."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("pyproj")
pytest.importorskip("shapely")

from geospatial.engineering_review.historical_alignment_2026_09_29 import build  # noqa: E402


def test_candidate_reproduces_without_promoting_accepted_unknowns() -> None:
    result = build.build()
    geo_sha = build.digest(build.HERE / "candidate.geojson")
    report_sha = build.digest(build.HERE / "report.json")
    assert result["candidate_1954_survivor_miles"] == pytest.approx(15.0848576853)
    assert result["candidate_prefailure_total_miles"] == pytest.approx(22.1322554284)
    assert result["current_route_overlap_screen_m"] < 0.1
    assert result["accepted_1898_original_extent_miles"] is None
    assert result["accepted_1898_geometry"] is None
    assert result["accepted_1954_geometry"] is None
    assert result["accepted_1954_surviving_interval_miles"] == [14, 16]
    assert result["source_fixed_modern_structure_or_asset_ids_reused"] == 0
    assert build.build() == result
    assert build.digest(build.HERE / "candidate.geojson") == geo_sha
    assert build.digest(build.HERE / "report.json") == report_sha


def test_out_of_range_or_current_rights_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = json.loads((build.HERE / "source.json").read_text())
    source["hypothesis"]["surviving_1954_centerline_lon_lat"][-1] = [-108.06, 41.57]
    source["hypothesis"]["fictional_west_service_point_lon_lat"] = [-108.06, 41.57]
    (tmp_path / "source.json").write_text(json.dumps(source))
    monkeypatch.setattr(build, "HERE", tmp_path)
    with pytest.raises(ValueError, match="1954 survivor violates accepted interval"):
        build.build()
    source["hypothesis"]["surviving_1954_centerline_lon_lat"][-1] = [-108.14, 41.5]
    source["hypothesis"]["fictional_west_service_point_lon_lat"] = [-108.14, 41.5]
    source["hypothesis"]["current_operating_right_or_asset"] = True
    (tmp_path / "source.json").write_text(json.dumps(source))
    with pytest.raises(ValueError, match="cannot grant current rights"):
        build.build()
