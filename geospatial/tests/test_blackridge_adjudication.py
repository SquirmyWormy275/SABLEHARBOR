"""Verify the review's evidence binding and preservation of distinct temporal records."""

import copy
import csv
import gzip
import io
import json

import pytest

from geospatial.adjudication import review_blackridge as review


def assignment_hit(number=1):
    return {
        "occurrence_id": f"OCC-test-{number}",
        "source_locator": f"table:exclusive_assignment:row:{number}:column:location_id",
        "exact_source_wording": "BLACKRIDGE-PIT",
    }


def test_repeated_location_does_not_deduplicate_assignments_or_intervals():
    config = json.loads((review.HERE / "BLACKRIDGE_RULES.json").read_text())
    first = {
        "id": 1,
        "assignment_id": "ASN-1",
        "resource_id": "TRUCK-1",
        "location_id": "BLACKRIDGE-PIT",
        "starts_at": "2015-01-01T00:00:00+00:00",
        "ends_at": "2015-01-01T12:00:00+00:00",
    }
    second = dict(first, id=2, assignment_id="ASN-2", resource_id="TRUCK-2")
    a = review.classify(assignment_hit(), first, config["rules"])
    b = review.classify(assignment_hit(2), second, config["rules"])
    assert a["reference_key"] == b["reference_key"]
    assert a["occurrence_id"] != b["occurrence_id"]
    assert json.loads(a["source_context_json"]) == first
    assert json.loads(b["source_context_json"]) == second


def test_changed_wording_and_unknown_location_fail_closed():
    config = json.loads((review.HERE / "BLACKRIDGE_RULES.json").read_text())
    hit = assignment_hit()
    with pytest.raises(ValueError, match="differs"):
        review.classify(hit, {"location_id": "ANOTHER-PIT"}, config["rules"])
    hit["exact_source_wording"] = "ANOTHER-PIT"
    with pytest.raises(ValueError, match="no exact"):
        review.classify(hit, {"location_id": "ANOTHER-PIT"}, config["rules"])
    duplicate = copy.deepcopy(config["rules"])
    duplicate.append(duplicate[0])
    with pytest.raises(ValueError, match="no exact"):
        review.classify(assignment_hit(), {"location_id": "BLACKRIDGE-PIT"}, duplicate)


def test_archived_review_reproduces_and_every_assignment_survives():
    payload, summary_bytes = review.review()
    assert payload == (review.HERE / "BLACKRIDGE_REVIEW.csv.gz").read_bytes()
    assert summary_bytes == (review.HERE / "BLACKRIDGE_REVIEW.json").read_bytes()
    summary = json.loads(summary_bytes)
    rows = list(csv.DictReader(io.StringIO(gzip.decompress(payload).decode())))
    assignments = [
        json.loads(r["source_context_json"])
        for r in rows
        if r["disposition"] == "REPEATED_LOCATION_REFERENCE"
    ]
    assert len(assignments) == 365 * 2 * (27 + 54)
    assert len({r["assignment_id"] for r in assignments}) == len(assignments)
    assert {r["resource_type"] for r in assignments} == {"TRUCK", "OPERATOR"}
    assert all(r["starts_at"] < r["ends_at"] for r in assignments)
    assert len({r["occurrence_id"] for r in rows}) == len(rows)
    assert summary["reviewed_occurrences"] + summary["remaining_unreviewed_occurrences"] == 78145
    assert not summary["semantic_census_complete"]
    assert not summary["geometry_or_occupancy_promoted"]
    assert summary["disposition_counts"]["UNLOCATED_COMPONENT_REFERENCE"] == 11


def test_source_hash_tampering_fails(monkeypatch):
    monkeypatch.setattr(review, "archived", lambda *args: b"unrelated source")
    with pytest.raises(ValueError, match="hash mismatch"):
        review.review()
