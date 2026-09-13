"""Evidence and temporal boundaries for the geographic requirements package."""

import copy
import csv
import gzip
import io
import json
import pytest
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform
from geospatial.chronology.build import ROOT, build as history
from geospatial.completion import source_review, site_options, dossier, raster_review
from geospatial.completion.atlas import frames
from tools.evidence.closeout import residual_geography


@pytest.fixture(scope="module")
def reviewed():
    return source_review.review()


@pytest.fixture(scope="module")
def options():
    return site_options.build()


def test_review_population_preserves_every_carrier_and_reconciles(reviewed):
    rows, remaining, summary = reviewed
    old, _ = residual_geography()
    before = {
        r["occurrence_id"]: r
        for r in old
        if r["source_path"] != "industrial/source/operations.json"
    }
    assert len(rows) == 1770 and summary["source_files"] == 147
    ids = {r["occurrence_id"] for r in rows}
    left = {r["occurrence_id"] for r in remaining}
    assert not ids & left and ids | left == set(before)
    for row in rows:
        assert all(row[k] == v for k, v in before[row["occurrence_id"]].items())
    assert summary["cumulative_reviewed_carriers"] + len(remaining) == 78145
    assert not summary["semantic_census_complete"]
    committed = list(
        csv.DictReader(
            io.StringIO(
                gzip.decompress(
                    (ROOT / "geospatial/completion/SOURCE_REVIEW.csv.gz").read_bytes()
                ).decode()
            )
        )
    )
    assert {r["occurrence_id"] for r in committed} == ids


def test_retained_financial_allocations_do_not_collapse_names(reviewed):
    rows, _, _ = reviewed
    allocations = [r for r in rows if r["disposition"] == "WORKFORCE_ALLOCATION_RECORD"]
    assert len(allocations) == 90
    assert len({r["occurrence_id"] for r in allocations}) == 90
    assert all(
        r["containing_record"] and r["containing_locator"].startswith("/employees/")
        for r in allocations
    )


def test_exact_source_binding_rejects_fabricated_line_and_pointer():
    with pytest.raises(ValueError, match="mismatch"):
        source_review.context(
            b"first\nactual\n",
            dict(
                source_path="x.py",
                source_locator="line:2",
                exact_source_wording="invented",
                occurrence_id="bad",
            ),
        )
    with pytest.raises(ValueError, match="mismatch"):
        source_review.context(
            b'{"items":[{"name":"actual"}]}',
            dict(
                source_path="x.json",
                source_locator="/items/0/name",
                exact_source_wording="invented",
                occurrence_id="bad",
            ),
        )
    loc, record, owner = source_review.context(
        b'def fixture():\n    location = "a"\n',
        dict(
            source_path="x.py",
            source_locator="line:2",
            exact_source_wording='    location = "a"',
            occurrence_id="good",
        ),
    )
    assert owner == "FunctionDef:fixture" and "location" in record


def test_site_designs_fit_scale_and_keep_geometry_separate_from_title(options):
    sites, access, reports = options
    assert len(sites["features"]) == len(access["features"]) == 9
    studies = {
        r["id"]: shape(r["geometry"])
        for r in json.loads((ROOT / "geospatial/geojson/locked_search_areas.geojson").read_text())[
            "features"
        ]
    }
    for row in sites["features"]:
        p = row["properties"]
        spec = next(s for s in site_options.SPECS if s["object_id"] == p["object_id"])
        project = Transformer.from_crs(4326, p["projected_epsg"], always_xy=True).transform
        geom = transform(project, shape(row["geometry"]))
        assert geom.is_valid and studies[p["study_id"]].covers(shape(row["geometry"]))
        assert spec["min_acres"] < geom.area / 4046.8564224 < spec["max_acres"]
        assert abs(geom.area - p["width_m"] * p["depth_m"]) < 0.01
        assert all(
            p[k] is None
            for k in ("owner_entity", "occupancy_start", "occupancy_end", "valid_from", "valid_to")
        )
        line = next(a for a in access["features"] if a["properties"]["option_id"] == row["id"])
        g = transform(project, shape(line["geometry"]))
        assert abs(g.length - p["reference_access_gap_m"]) < 0.001
        assert geom.boundary.distance(shape({"type": "Point", "coordinates": g.coords[0]})) < 0.001
    assert all(r["reference_clear_candidates"] >= 3 for r in reports)


def test_historical_frames_do_not_backdate_modern_routes():
    data = history()
    rows = {r["year"]: r for r in frames(data)}
    for year in ["1898", "1907", "1954", "1958"]:
        assert rows[year]["route_feature_ids"] == []
    assert len(rows["1968"]["route_feature_ids"]) == 3
    assert len(rows["1972"]["route_feature_ids"]) == 4
    assert len(rows["1986"]["route_feature_ids"]) == 5
    assert rows["2026"]["as_of"] == "2026-09-13"
    assert "MOVE-KLEIN-FORT-2024" in rows["2024"]["event_ids"]
    assert "MOVE-KLEIN-FORT-2024" not in rows["2023"]["event_ids"]


def test_all_site_requirements_keep_observations_distinct_from_intervals():
    data = dossier.build()
    records = {r["object_id"]: r for r in data["records"]}
    assert len(records) == 34 and len(data["observations"]) == 17
    assert all(
        o["occupancy_start"] is None and o["occupancy_end"] is None for o in data["observations"]
    )
    for oid in ("SH-SITE-0011", "SH-SITE-0012", "SH-SITE-0013"):
        assert records[oid]["disposition"] == "AUTHORED_SHARED_LEASED_OFFICE"
    assert records["SH-SITE-0027"]["disposition"] == "EXTERNAL_OPERATING_HOST_REGIONAL_PRECISION_ACCEPTED"
    assert records["SH-SITE-0002"]["occupancy_bounds"]["latest_end"] == "2025-01-01"
    assert all(r["issue_106_complete"] for r in records.values())


def test_visual_role_review_is_complete_and_preserves_superseded_maps():
    rows = raster_review.review()
    assert len(rows) == 97
    obsolete = [r for r in rows if r["disposition"] == "SUPERSEDED_GEOGRAPHIC_ILLUSTRATION"]
    assert len(obsolete) == 2 and all(
        "42.3127" in r["finding"] and "GEO-C001" in r["finding"] for r in obsolete
    )
    assert all(not r["geographic_claim_promoted"] and not r["occupancy_established"] for r in rows)


def test_reader_keeps_source_text_in_inert_data(tmp_path, reviewed):
    from geospatial.completion.readers import write

    rows, _, summary = reviewed
    sample = copy.deepcopy(rows[:1])
    sample[0]["exact_source_wording"] = "</script><script>window.injected=true</script>"
    write(tmp_path, dossier.build(), sample, summary)
    html = (tmp_path / "source-review.html").read_text()
    assert "</script><script>window.injected=true" not in html
    assert "<\\/script>" in html
    assert "textContent=r.exact_source_wording" in html
