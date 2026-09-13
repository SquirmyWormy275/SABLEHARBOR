#!/usr/bin/env python3
"""Bind archived reference-layer discovery hits to their existing features."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
from collections import Counter

from geospatial.adjudication.review_blackridge import HERE, REGISTERS, archived, digest


def classify(hit, document, source, names):
    match = re.fullmatch(
        r"/features/(0|[1-9][0-9]*)/(id|properties/source_id|properties/name)",
        hit["source_locator"],
    )
    if not match:
        raise ValueError("Unreviewed locator")
    feature = document["features"][int(match[1])]
    props = feature["properties"]
    if any(
        props.get(k) != v
        for k, v in {
            "canon_status": "REAL_REFERENCE",
            "fictionality": "REAL",
            "real_world_relation": "REFERENCE_ONLY",
        }.items()
    ):
        raise ValueError("Feature is not explicitly reference-only")
    field = match[2]
    value = feature["id"] if field == "id" else props[field.split("/")[1]]
    if value != hit["exact_source_wording"]:
        raise ValueError("Discovery wording differs from archived feature")
    if (
        props["source_id"] != source["source_id"]
        or feature["id"] != f"{source['source_id']}-{int(match[1]) + 1}"
    ):
        raise ValueError("Unexpected source/feature identity")
    if field == "properties/name" and value not in names:
        raise ValueError("Unreviewed feature name")
    disposition = {
        "id": "REFERENCE_FEATURE_IDENTIFIER",
        "properties/source_id": "REFERENCE_SOURCE_LINK",
        "properties/name": "REFERENCE_FEATURE_NAME",
    }[field]
    return {
        "occurrence_id": hit["occurrence_id"],
        "source_path": hit["source_path"],
        "source_locator": hit["source_locator"],
        "exact_source_wording": value,
        "disposition": disposition,
        "reference_key": feature["id"],
        "geometry_type": feature["geometry"]["type"],
        "geometry_sha256": digest(
            json.dumps(feature["geometry"], sort_keys=True, separators=(",", ":")).encode()
        ),
        "source_properties_json": json.dumps(props, sort_keys=True, separators=(",", ":")),
    }


def review():
    rules = (HERE / "REFERENCE_LAYER_RULES.json").read_bytes()
    config = json.loads(rules)
    manifest = json.loads((REGISTERS / "CENSUS_MANIFEST.json").read_text())
    if config["source_commit"] != manifest["source_commit"]:
        raise ValueError("Baseline differs")
    archive = (REGISTERS / "GEOGRAPHIC_CANDIDATE_OCCURRENCES.csv.gz").read_bytes()
    if digest(archive) != config["occurrences_sha256"]:
        raise ValueError("Occurrence hash mismatch")
    hits = list(csv.DictReader(io.StringIO(gzip.decompress(archive).decode())))
    if len(hits) != manifest["candidate_occurrences"] or len(
        {h["occurrence_id"] for h in hits}
    ) != len(hits):
        raise ValueError("Discovery coverage differs")
    with (REGISTERS / "SOURCE_COVERAGE.csv").open() as handle:
        coverage = {r["source_path"]: r["file_sha256"] for r in csv.DictReader(handle)}
    output = []
    for source in config["sources"]:
        data = archived(config["source_commit"], source["path"])
        if digest(data) != source["sha256"] or coverage[source["path"]] != source["sha256"]:
            raise ValueError("Source hash mismatch")
        document = json.loads(data)
        features = document["features"]
        if (
            document["type"] != "FeatureCollection"
            or len(features) != source["features"]
            or len({f["id"] for f in features}) != len(features)
        ):
            raise ValueError("Feature inventory differs")
        selected = [h for h in hits if h["source_path"] == source["path"]]
        if len(selected) != source["occurrences"] or any(
            h["source_commit"] != config["source_commit"] for h in selected
        ):
            raise ValueError("Source occurrence coverage differs")
        output.extend(classify(h, document, source, config["reviewed_names"]) for h in selected)
    with gzip.open(HERE / "BLACKRIDGE_REVIEW.csv.gz", "rt") as handle:
        prior = {r["occurrence_id"] for r in csv.DictReader(handle)}
    if prior & {r["occurrence_id"] for r in output}:
        raise ValueError("Review batches overlap")
    stream = io.StringIO()
    writer = csv.DictWriter(stream, list(output[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(sorted(output, key=lambda r: r["occurrence_id"]))
    payload = gzip.compress(stream.getvalue().encode(), mtime=0)
    summary = {
        "source_commit": config["source_commit"],
        "rules_sha256": digest(rules),
        "review_output_sha256": digest(payload),
        "reviewed_occurrences": len(output),
        "reference_features": sum(s["features"] for s in config["sources"]),
        "disposition_counts": dict(sorted(Counter(r["disposition"] for r in output).items())),
        "cumulative_reviewed_occurrences": len(prior) + len(output),
        "remaining_unreviewed_occurrences": len(hits) - len(prior) - len(output),
        "semantic_census_complete": False,
        "geometry_or_occupancy_promoted": False,
        "limits": "Archived real-world context layers only. Feature IDs and provider metadata establish neither Sable Harbor ownership nor occupancy. Geometry is hash-bound source context, not promoted canon. OCR and later canon deltas remain outside these batches.",
    }
    return payload, (json.dumps(summary, indent=2) + "\n").encode()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, data in zip(
        ("REFERENCE_LAYER_REVIEW.csv.gz", "REFERENCE_LAYER_REVIEW.json"), review()
    ):
        path = HERE / name
        if args.check:
            if path.read_bytes() != data:
                raise SystemExit(f"Review output drift: {name}")
        else:
            path.write_bytes(data)
    print("PASS pinned reference-layer review")
