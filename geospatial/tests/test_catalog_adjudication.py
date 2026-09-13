import json

import pytest

from geospatial.adjudication import review_catalog as review


def test_catalog_derivation_reproduces():
    payload, report = review.review()
    assert payload == (review.HERE / "CATALOG_REVIEW.csv.gz").read_bytes()
    assert report == (review.HERE / "CATALOG_REVIEW.json").read_bytes()
    data = json.loads(report)
    assert data["disposition_counts"] == {
        "DERIVED_SEARCH_COPY": 336,
        "CATALOG_METADATA_REFERENCE": 108,
    }
    assert data["hash_verified_source_documents"] == 84
    assert data["remaining_unreviewed_occurrences"] == 8961
    assert not data["semantic_census_complete"]


def test_mutated_source_hash_fails(monkeypatch):
    monkeypatch.setattr(review, "archived", lambda *args: b"changed")
    with pytest.raises(ValueError, match="Source hash"):
        review.review()


def test_wrong_canonical_field_or_wording_fails():
    with pytest.raises(ValueError, match="canonical catalog field"):
        review.classify(
            {"exact_source_wording": "wrong"}, {"title": "original"}, "title", "wrong", {}
        )
    with pytest.raises(ValueError, match="canonical catalog field"):
        review.classify({}, {}, "not_reviewed", "anything", {})
