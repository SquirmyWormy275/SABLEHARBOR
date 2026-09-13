import copy
import json

import pytest

from geospatial.closeout.sites import ROOT, bind_source, review


def test_every_site_has_a_source_binding_and_separate_occupancy_disposition():
    result, sources = review()
    assert result["verified_site_records"] == 34
    assert len(sources) == 18
    assert all(
        row["occupancy_valid_from"] is None and row["occupancy_valid_to"] is None
        for row in result["rows"]
    )
    assert all(row["source"]["sha256"] in sources for row in result["rows"])
    assert result["issue_106_complete"]
    assert all(r["current_decision_evidence"]["sha256"] in sources for r in result["rows"])
    by_id = {row["object_id"]: row for row in result["rows"]}
    assert by_id["SH-SITE-0016"]["hosting_dependency_ids"] == [
        "SH-SITE-0028",
        "SH-SITE-0029",
        "SH-SITE-0030",
    ]
    assert by_id["SH-SITE-0002"]["conflict_ids"] == []
    assert by_id["SH-SITE-0023"]["access_disposition"] == "EXTERNAL_HOST_AUTHORITY"
    assert (
        by_id["SH-SITE-0030"]["geometry_features"][0]["geometry_status"] == "SYNTHETIC_UNSURVEYED"
    )


def test_source_binding_rejects_a_changed_quote_or_locator():
    catalog = json.loads((ROOT / "geospatial/sources/catalog.json").read_text())
    hq = next(r for r in catalog["objects"] if r["object_id"] == "SH-SITE-0001")
    for change in (
        {"source_locator": "line:1"},
        {"exact_source_wording": "A fabricated occupied parcel"},
    ):
        candidate = copy.deepcopy(hq)
        candidate.update(change)
        with pytest.raises(ValueError, match="Source line does not match"):
            bind_source(candidate)


def test_structured_source_binding_rejects_a_different_facility():
    catalog = json.loads((ROOT / "geospatial/sources/catalog.json").read_text())
    row = copy.deepcopy(next(r for r in catalog["objects"] if r["object_id"] == "SH-SITE-0008"))
    row["source_locator"] = "/facilities/1"
    with pytest.raises(ValueError, match="Structured source does not match"):
        bind_source(row)


def test_approved_site_bounds_are_separate_from_exact_dates():
    from geospatial.chronology.continuity import load, occupancy_at

    record = load()
    assert occupancy_at("2023-07-01") == {"SH-SITE-0002": "CERTAIN", "SH-SITE-0003": "ABSENT"}
    assert occupancy_at("2024-01-01") == {"SH-SITE-0002": "POSSIBLE", "SH-SITE-0003": "POSSIBLE"}
    assert occupancy_at("2024-12-31") == {"SH-SITE-0002": "POSSIBLE", "SH-SITE-0003": "POSSIBLE"}
    assert occupancy_at("2025-01-01") == {"SH-SITE-0002": "ABSENT", "SH-SITE-0003": "CERTAIN"}
    assert set(occupancy_at("2025-01-01", known_at="2026-09-12T00:00:00+00:00").values()) == {
        "UNKNOWN"
    }
    assert (
        occupancy_at("2025-01-01", known_at=record["states"][0]["recorded_at"])["SH-SITE-0003"]
        == "CERTAIN"
    )


def test_continuity_validation_rejects_unapproved_precision(tmp_path):
    from geospatial.chronology.continuity import load, PATH

    record = load()
    (tmp_path / record["canon_path"]).parent.mkdir(parents=True)
    (tmp_path / record["canon_path"]).write_bytes((ROOT / record["canon_path"]).read_bytes())
    (tmp_path / PATH).parent.mkdir(parents=True)
    for field, value in [
        ("valid_from", "2024-01-01"),
        ("owner_entity", "REAL-LANDLORD"),
        ("latest_start", "2023-01-01"),
    ]:
        changed = copy.deepcopy(record)
        changed["states"][1][field] = value
        (tmp_path / PATH).write_text(json.dumps(changed))
        with pytest.raises(ValueError):
            load(tmp_path)
    (tmp_path / PATH).write_text(json.dumps(record))
    (tmp_path / record["canon_path"]).write_text("Unapproved altered history")
    with pytest.raises(ValueError, match="source hash"):
        load(tmp_path)
