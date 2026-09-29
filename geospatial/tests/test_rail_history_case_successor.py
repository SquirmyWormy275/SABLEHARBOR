"""Fictional 1954 placement remains distinct from recovered history and modern rail."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geospatial.successors.rail_history_2026_09_29 import build as history

HERE = Path(__file__).resolve().parents[1] / "successors/rail_history_2026_09_29"


def test_exact_separate_outputs_and_preserved_history():
    outputs = history.build()
    assert set(outputs) == {"case.geojson", "report.json", "case.svg"}
    assert all((HERE / name).read_bytes() == content for name, content in outputs.items())
    report = json.loads(outputs["report.json"])
    case = json.loads(outputs["case.geojson"])
    source = json.loads((HERE / "source.json").read_text())
    assert source["schema_version"] == report["source_schema_version"] == "1.1"
    assert source["supersedes_source_sha256"] == report["supersedes_source_sha256"]
    assert source["prior_source_accepted_commit"] == report["prior_source_accepted_commit"]
    assert source["prior_source_repository_available_at_utc"] == report[
        "prior_source_repository_available_at_utc"
    ]
    assert source["repository_available_at"] is None
    assert "#107B" in source["authority"] and "#108B" not in source["authority"]
    assert 14 <= report["lengths_miles"]["survivor"] <= 16
    assert 20 <= report["illustrative_prefailure_total_miles"] <= 24
    assert report["accepted_history_preserved"]["1898_extent_miles"] is None
    assert report["accepted_history_preserved"]["1954_recovered_geometry"] is None
    assert report["accepted_history_preserved"]["real_title_or_right_of_way_instrument"] is None
    assert report["snapshot_dispositions"] == [
        {"date": "1898-04-06", "recovered_linework": 0, "illustrative_linework": 0},
        {"date": "1954-07-01", "recovered_linework": 0, "illustrative_linework": 1},
        {
            "date": "1968-10-14",
            "recovered_linework": 0,
            "illustrative_linework": 0,
            "modern_route_source_separate": True,
        },
    ]
    assert report["current_operating_asset_count_added"] == 0
    assert report["finance_tax_cash_delta_usd"] == 0
    assert report["real_property_instrument_count_added"] == 0
    assert len(case["features"]) == 2
    assert all(f["properties"]["current_asset_id"] is None for f in case["features"])
    assert all(f["properties"]["real_title_or_right_of_way"] is None for f in case["features"])
    assert all(f["properties"]["continuous_operating_interval"] is None for f in case["features"])
    assert b"not a recovered map" in outputs["case.svg"]


@pytest.mark.parametrize(
    "field,value,error",
    [
        (("selection", "historical_evidence_state"), "RECOVERED_SURVEY", "authority"),
        (("selection", "current_operating_network_effect"), "NEW_TRACK", "authority"),
        (("selection", "finance_tax_cash_effect"), "CAPEX", "authority"),
        (("selection", "property_right_effect"), "REAL_RIGHT_OF_WAY", "authority"),
        (("historical_time_interpretation", "abandonment_date"), "1954-07-01", "uncertainty"),
        (
            ("historical_time_interpretation", "survivor_retirement_date"),
            "1968-10-14",
            "uncertainty",
        ),
        (("accepted_history_preserved", "1898_extent_miles"), 22.132, "uncertainty"),
        (("accepted_history_preserved", "1954_recovered_geometry"), "case.geojson", "uncertainty"),
        (("input_sha256", "industrial/source/operations.json"), "0" * 64, "Changed pinned"),
        (("authority",), "Owner #107B/#108B approved", "authority"),
    ],
)
def test_unsupported_evidence_right_or_economic_promotion_rejected(
    tmp_path, monkeypatch, field, value, error
):
    source = json.loads((HERE / "source.json").read_text())
    if len(field) == 1:
        source[field[0]] = value
    else:
        source[field[0]][field[1]] = value
    (tmp_path / "source.json").write_text(json.dumps(source))
    monkeypatch.setattr(history, "HERE", tmp_path)
    with pytest.raises(ValueError, match=error):
        history.build()
