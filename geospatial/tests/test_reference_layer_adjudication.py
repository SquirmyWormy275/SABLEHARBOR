"""Fail closed on changed reference evidence and preserve source-local identity."""

import copy
import csv
import gzip
import io
import json

import pytest

from geospatial.adjudication import review_reference_layers as review


def fixture():
    config = json.loads((review.HERE / "REFERENCE_LAYER_RULES.json").read_text())
    source = config["sources"][0]
    document = json.loads(review.archived(config["source_commit"], source["path"]))
    hit = {
        "occurrence_id": "test",
        "source_path": source["path"],
        "source_locator": "/features/0/id",
        "exact_source_wording": document["features"][0]["id"],
    }
    return hit, document, source, config["reviewed_names"]


def test_reference_properties_and_geometry_are_preserved():
    hit, document, source, names = fixture()
    row = review.classify(hit, document, source, names)
    assert json.loads(row["source_properties_json"]) == document["features"][0]["properties"]
    assert row["disposition"] == "REFERENCE_FEATURE_IDENTIFIER"
    assert row["geometry_type"] == "LineString"
    hit.update(
        source_locator="/features/0/properties/source_id",
        exact_source_wording=source["source_id"],
    )
    provenance = review.classify(hit, document, source, names)
    assert provenance["reference_key"] == row["reference_key"]
    assert provenance["disposition"] == "REFERENCE_SOURCE_LINK"


def test_changed_wording_locator_and_canon_flags_fail():
    hit, document, source, names = fixture()
    bad = dict(hit, exact_source_wording="different")
    with pytest.raises(ValueError, match="wording differs"):
        review.classify(bad, document, source, names)
    with pytest.raises(ValueError, match="locator"):
        review.classify(dict(hit, source_locator="/features/0/geometry"), document, source, names)
    document = copy.deepcopy(document)
    document["features"][0]["properties"]["canon_status"] = "OWNED"
    with pytest.raises(ValueError, match="reference-only"):
        review.classify(hit, document, source, names)


def test_archived_batch_reproduces_without_claiming_census_completion():
    payload, summary = review.review()
    assert payload == (review.HERE / "REFERENCE_LAYER_REVIEW.csv.gz").read_bytes()
    assert summary == (review.HERE / "REFERENCE_LAYER_REVIEW.json").read_bytes()
    rows = list(csv.DictReader(io.StringIO(gzip.decompress(payload).decode())))
    assert len(rows) == len({r["occurrence_id"] for r in rows}) == 7844
    assert len({r["reference_key"] for r in rows}) == 3912
    report = json.loads(summary)
    assert (
        report["cumulative_reviewed_occurrences"] + report["remaining_unreviewed_occurrences"]
        == 78145
    )
    assert not report["geometry_or_occupancy_promoted"]
    assert not report["semantic_census_complete"]


def test_source_hash_tampering_fails(monkeypatch):
    monkeypatch.setattr(review, "archived", lambda *args: b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        review.review()
