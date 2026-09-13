#!/usr/bin/env python3
"""Reproduce the bounded semantic review of pinned Blackridge discovery occurrences."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import pathlib
import re
import sqlite3
import subprocess
import tempfile
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
REGISTERS = ROOT / "geospatial/registers"
FIELDS = [
    "occurrence_id",
    "source_locator",
    "exact_source_wording",
    "rule_id",
    "disposition",
    "reference_key",
    "source_context_json",
]
LOCATOR = re.compile(r"table:([a-z_]+):row:([1-9][0-9]*):column:([a-z_]+)")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def archived(commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def classify(hit, context, rules):
    match = LOCATOR.fullmatch(hit["source_locator"])
    if not match:
        raise ValueError("Unsupported locator")
    table, _, column = match.groups()
    value = hit["exact_source_wording"]
    if context.get(column) != value:
        raise ValueError("Discovery wording differs from archived source row")
    matches = [r for r in rules if r["table"] == table and r["column"] == column]
    if len(matches) != 1 or value not in matches[0]["values"]:
        raise ValueError("Occurrence has no exact reviewed rule")
    rule = matches[0]
    if table == "exclusive_assignment":
        # Group ONLY the location token. Distinct assignments and intervals remain distinct.
        key = f"{table}:{column}:{value}"
    elif table == "event_ledger":
        key = f"{table}:{column}:{value}"
    else:
        key = f"{table}:canonical_id:{context['canonical_id']}"
    return {
        "occurrence_id": hit["occurrence_id"],
        "source_locator": hit["source_locator"],
        "exact_source_wording": value,
        "rule_id": rule["id"],
        "disposition": rule["disposition"],
        "reference_key": key,
        "source_context_json": json.dumps(context, sort_keys=True, separators=(",", ":")),
    }


def review():
    rules_bytes = (HERE / "BLACKRIDGE_RULES.json").read_bytes()
    config = json.loads(rules_bytes)
    manifest = json.loads((REGISTERS / "CENSUS_MANIFEST.json").read_text())
    if config["source_commit"] != manifest["source_commit"]:
        raise ValueError("Review and census baselines differ")
    for source in config["sources"]:
        data = archived(config["source_commit"], source["path"])
        if digest(data) != source["sha256"]:
            raise ValueError("Archived source hash mismatch")
    source = config["sources"][0]
    coverage = list(csv.DictReader((REGISTERS / "SOURCE_COVERAGE.csv").open()))
    entry = next(r for r in coverage if r["source_path"] == source["path"])
    if entry["file_sha256"] != source["sha256"]:
        raise ValueError("Source coverage hash mismatch")
    compressed = (REGISTERS / "GEOGRAPHIC_CANDIDATE_OCCURRENCES.csv.gz").read_bytes()
    if digest(compressed) != config["occurrences_sha256"]:
        raise ValueError("Discovery input changed; review must be revised explicitly")
    occurrences = list(csv.DictReader(io.StringIO(gzip.decompress(compressed).decode())))
    if len({r["occurrence_id"] for r in occurrences}) != len(occurrences):
        raise ValueError("Duplicate occurrence IDs")
    if len(occurrences) != manifest["candidate_occurrences"]:
        raise ValueError("Census occurrence count mismatch")
    selected = [r for r in occurrences if r["source_path"] == source["path"]]
    if any(r["source_commit"] != config["source_commit"] for r in selected):
        raise ValueError("Occurrence baseline differs")
    output = []
    with tempfile.TemporaryDirectory(prefix="sh-blackridge-review-") as temp:
        path = pathlib.Path(temp) / "archived.sqlite3"
        path.write_bytes(archived(config["source_commit"], source["path"]))
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            # Match the original census extraction's SELECT * row ordinals. Store the
            # primary/source keys too; ordinals are never interpreted as entity IDs.
            tables = {}
            for rule in config["rules"]:
                table = rule["table"]
                if not re.fullmatch(r"[a-z_]+", table):
                    raise ValueError("Invalid reviewed table")
                if table not in tables:
                    tables[table] = [dict(row) for row in db.execute(f'SELECT * FROM "{table}"')]
            for hit in selected:
                match = LOCATOR.fullmatch(hit["source_locator"])
                if not match or match[1] not in tables:
                    raise ValueError("Unreviewed table/locator")
                index = int(match[2]) - 1
                if index >= len(tables[match[1]]):
                    raise ValueError("Source row ordinal out of range")
                output.append(classify(hit, tables[match[1]][index], config["rules"]))
    counts = Counter(row["rule_id"] for row in output)
    if counts != Counter({r["id"]: r["expected_occurrences"] for r in config["rules"]}):
        raise ValueError("Reviewed rule counts differ")
    text = io.StringIO()
    writer = csv.DictWriter(text, FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(sorted(output, key=lambda row: row["occurrence_id"]))
    payload = gzip.compress(text.getvalue().encode(), mtime=0)
    summary = {
        "source_commit": config["source_commit"],
        "source_path": source["path"],
        "source_sha256": source["sha256"],
        "rules_sha256": digest(rules_bytes),
        "discovery_sha256": digest(compressed),
        "review_output_sha256": digest(payload),
        "baseline_occurrences": len(occurrences),
        "reviewed_occurrences": len(output),
        "remaining_unreviewed_occurrences": len(occurrences) - len(output),
        "rule_counts": dict(sorted(counts.items())),
        "disposition_counts": dict(sorted(Counter(r["disposition"] for r in output).items())),
        "repeated_location_token_count": 1,
        "distinct_assignments_preserved": len(
            {
                json.loads(r["source_context_json"])["assignment_id"]
                for r in output
                if r["disposition"] == "REPEATED_LOCATION_REFERENCE"
            }
        ),
        "semantic_census_complete": False,
        "geometry_or_occupancy_promoted": False,
        "limits": "One pinned source reviewed. Repeated tokens are not duplicate events. "
        "Source-local IDs do not establish joins, geometry, ownership or occupancy. "
        "Unlocated components remain unresolved. OCR and later canon deltas are outside this batch.",
    }
    return payload, (json.dumps(summary, indent=2) + "\n").encode()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = zip(("BLACKRIDGE_REVIEW.csv.gz", "BLACKRIDGE_REVIEW.json"), review())
    for name, data in outputs:
        path = HERE / name
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit(f"Review output drift: {name}")
        else:
            path.write_bytes(data)
    print(
        "PASS pinned Blackridge semantic review"
        if args.check
        else "Built Blackridge semantic review"
    )
