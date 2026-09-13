import copy
import json

import pytest

from geospatial.closeout.sites import ROOT, bind_source, review


def test_every_site_has_a_source_binding_and_separate_occupancy_disposition():
    result, sources = review()
    assert result["verified_site_records"] == 34
    assert len(sources) == 16
    assert all(
        row["occupancy_valid_from"] is None and row["occupancy_valid_to"] is None
        for row in result["rows"]
    )
    assert all(row["source"]["sha256"] in sources for row in result["rows"])
    assert not result["issue_106_complete"]
    by_id = {row["object_id"]: row for row in result["rows"]}
    assert by_id["SH-SITE-0016"]["hosting_dependency_ids"] == [
        "SH-SITE-0028",
        "SH-SITE-0029",
        "SH-SITE-0030",
    ]
    assert by_id["SH-SITE-0002"]["conflict_ids"] == ["GEO-C002"]
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
