"""Trace archived catalog/search occurrences to hash-verified source documents."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import sqlite3
import tempfile
from collections import Counter

from geospatial.adjudication.review_blackridge import HERE, REGISTERS, archived, digest

FIELDS = {"id", "title", "owner", "category", "source", "publication", "search_text"}
SQL_FIELDS = {
    "institutional_object": {
        "id": "id",
        "title": "title",
        "owner": "owner",
        "category": "category",
        "source_path": "source",
        "publication_path": "publication",
        "search_text": "search_text",
    },
    "institutional_search": {
        "id": "id",
        "title": "title",
        "owner": "owner",
        "category": "category",
        "body": "search_text",
    },
    "institutional_search_content": {
        "c0": "id",
        "c1": "title",
        "c2": "owner",
        "c3": "category",
        "c4": "search_text",
    },
    "relationship": {"source_id": "id"},
}


def classify(hit, record, field, value, context):
    if field not in FIELDS or value != record[field] or value != hit["exact_source_wording"]:
        raise ValueError("Occurrence differs from canonical catalog field")
    return {
        "occurrence_id": hit["occurrence_id"],
        "source_path": hit["source_path"],
        "source_locator": hit["source_locator"],
        "exact_source_wording": value,
        "catalog_object_id": record["id"],
        "canonical_field": field,
        "disposition": "DERIVED_SEARCH_COPY"
        if field == "search_text"
        else "CATALOG_METADATA_REFERENCE",
        "referenced_source": record["source"],
        "referenced_source_sha256": record["source_sha256"],
        "source_context_json": json.dumps(context, sort_keys=True, separators=(",", ":")),
    }


def review():
    config_bytes = (HERE / "CATALOG_RULES.json").read_bytes()
    config = json.loads(config_bytes)
    manifest = json.loads((REGISTERS / "CENSUS_MANIFEST.json").read_text())
    if config["source_commit"] != manifest["source_commit"]:
        raise ValueError("Baseline differs")
    compressed = (REGISTERS / "GEOGRAPHIC_CANDIDATE_OCCURRENCES.csv.gz").read_bytes()
    if digest(compressed) != config["occurrences_sha256"]:
        raise ValueError("Occurrence hash mismatch")
    hits = list(csv.DictReader(io.StringIO(gzip.decompress(compressed).decode())))
    with (REGISTERS / "SOURCE_COVERAGE.csv").open() as handle:
        coverage = {r["source_path"]: r["file_sha256"] for r in csv.DictReader(handle)}
    data = {}
    for source in config["sources"]:
        payload = archived(config["source_commit"], source["path"])
        if digest(payload) != source["sha256"] or coverage[source["path"]] != source["sha256"]:
            raise ValueError("Source hash mismatch")
        data[source["path"]] = payload
    catalog = json.loads(data["docs/internal/institutional_catalog.json"])
    records = {r["id"]: r for r in catalog["objects"]}
    if len(records) != len(catalog["objects"]):
        raise ValueError("Duplicate catalog identity")
    for record in records.values():
        payload = archived(config["source_commit"], record["source"])
        if digest(payload) != record["source_sha256"]:
            raise ValueError("Referenced document hash mismatch")
        expected_search = " ".join((record["title"], record["source"], payload.decode())).lower()
        if record["search_text"] != expected_search:
            raise ValueError("Search text does not reproduce from referenced source")
    output = []
    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as file:
        file.write(data["docs/internal/institutional_catalog.sqlite3"])
        file.flush()
        db = sqlite3.connect(f"file:{file.name}?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        tables = {
            name: [dict(row) for row in db.execute(f'SELECT * FROM "{name}"')]
            for name in SQL_FIELDS
        }
        db.close()
        for source in config["sources"]:
            selected = [h for h in hits if h["source_path"] == source["path"]]
            if len(selected) != source["occurrences"]:
                raise ValueError("Occurrence coverage differs")
            for hit in selected:
                if hit["source_commit"] != config["source_commit"]:
                    raise ValueError("Occurrence baseline differs")
                if source["path"].endswith(".json"):
                    m = re.fullmatch(r"/objects/(0|[1-9][0-9]*)/([a-z_]+)", hit["source_locator"])
                    if not m:
                        raise ValueError("Unreviewed JSON locator")
                    record = catalog["objects"][int(m[1])]
                    field = m[2]
                    value = record[field]
                    context = {k: v for k, v in record.items() if k != "search_text"}
                else:
                    m = re.fullmatch(
                        r"table:([a-z_]+):row:([1-9][0-9]*):column:([a-z0-9_]+)",
                        hit["source_locator"],
                    )
                    if not m or m[1] not in SQL_FIELDS or m[3] not in SQL_FIELDS[m[1]]:
                        raise ValueError("Unreviewed SQL locator")
                    context = tables[m[1]][int(m[2]) - 1]
                    key = (
                        context["c0"]
                        if m[1] == "institutional_search_content"
                        else context["source_id"]
                        if m[1] == "relationship"
                        else context["id"]
                    )
                    record = records[key]
                    field = SQL_FIELDS[m[1]][m[3]]
                    value = context[m[3]]
                    context = {
                        k: v for k, v in context.items() if k not in ("search_text", "body", "c4")
                    }
                output.append(classify(hit, record, field, value, context))
    prior = set()
    for name in ("BLACKRIDGE", "REFERENCE_LAYER"):
        with gzip.open(HERE / f"{name}_REVIEW.csv.gz", "rt") as handle:
            prior.update(r["occurrence_id"] for r in csv.DictReader(handle))
    ids = {r["occurrence_id"] for r in output}
    if len(ids) != len(output) or ids & prior:
        raise ValueError("Review batches duplicate occurrences")
    stream = io.StringIO()
    writer = csv.DictWriter(stream, list(output[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(sorted(output, key=lambda r: r["occurrence_id"]))
    payload = gzip.compress(stream.getvalue().encode(), mtime=0)
    summary = {
        "source_commit": config["source_commit"],
        "rules_sha256": digest(config_bytes),
        "review_output_sha256": digest(payload),
        "reviewed_occurrences": len(output),
        "hash_verified_source_documents": len(records),
        "disposition_counts": dict(Counter(r["disposition"] for r in output)),
        "cumulative_reviewed_occurrences": len(prior) + len(output),
        "remaining_unreviewed_occurrences": len(hits) - len(prior) - len(output),
        "semantic_census_complete": False,
        "geometry_or_occupancy_promoted": False,
        "limits": "Index carriers are traced to their archived sources. This does not adjudicate geographic claims within those documents or promote catalog metadata to canon. Search text copies are retained, not counted as independent corroboration.",
    }
    return payload, (json.dumps(summary, indent=2) + "\n").encode()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, data in zip(("CATALOG_REVIEW.csv.gz", "CATALOG_REVIEW.json"), review()):
        path = HERE / name
        if args.check:
            if path.read_bytes() != data:
                raise SystemExit(f"Review drift: {name}")
        else:
            path.write_bytes(data)
    print("PASS archived catalog derivation review")
