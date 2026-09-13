"""Verify a fixed, source-bound editorial adjudication; never approve new text by rule."""

from collections import Counter
import csv
import gzip
import hashlib
import json
import re
import subprocess

from geospatial.finalization.screen import BASE, ROOT
from tools.evidence.inventory import fingerprints, tree


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def review():
    packet = json.loads(
        gzip.decompress((BASE / "GROUP_DECISIONS.json.gz").read_bytes())
    )
    extracted = json.loads(
        gzip.decompress((BASE / "EXTRACTED_RESIDUAL.json.gz").read_bytes())
    )
    expected = list(
        csv.DictReader(
            gzip.open(ROOT / "geospatial/completion/REMAINING_OCCURRENCES.csv.gz", "rt")
        )
    )
    by_id = {r["occurrence_id"]: r for r in extracted}
    if len(by_id) != len(extracted) or set(by_id) != {
        r["occurrence_id"] for r in expected
    }:
        raise ValueError(
            "Adjudication extraction population differs from residual census"
        )
    for row in expected:
        if any(by_id[row["occurrence_id"]][k] != v for k, v in row.items()):
            raise ValueError("Exact census carrier changed")
    source_tree = tree(ROOT, packet["baseline"])
    paths = {r["source_path"] for r in extracted}
    hashes = fingerprints(ROOT, [source_tree[p] for p in paths])
    objects = {
        r["object_id"]
        for r in json.loads((ROOT / "geospatial/sources/catalog.json").read_text())[
            "objects"
        ]
    }
    output = []
    seen = set()
    counterpart_text = {}
    for group in packet["groups"]:
        if digest(group["text"].encode()) != group["text_sha256"]:
            raise ValueError("Reviewed wording changed")
        if not set(group["related_object_ids"]) <= objects:
            raise ValueError("Unknown subject crosswalk")
        for counterpart in group["counterparts"]:
            path = counterpart["path"]
            if path not in counterpart_text:
                raw = subprocess.check_output(
                    ["git", "show", packet["baseline"] + ":" + path], cwd=ROOT
                )
                if digest(raw) != counterpart["sha256"]:
                    raise ValueError("Text counterpart source hash differs")
                from geospatial.scripts.census import extract

                units, _ = extract(raw, path, BASE, False)
                counterpart_text[path] = re.sub(
                    r"[^a-z0-9]", "", " ".join(t for _, t in units).lower()
                )
            if (
                re.sub(r"[^a-z0-9]", "", group["text"].lower())
                not in counterpart_text[path]
            ):
                raise ValueError("Claimed text counterpart does not match")
        for oid in group["occurrence_ids"]:
            row = by_id[oid]
            if (
                oid in seen
                or " ".join(row["exact_source_wording"].split()) != group["text"]
            ):
                raise ValueError("Duplicate carrier or text-group mismatch")
            if hashes[source_tree[row["source_path"]]][1] != row["source_sha256"]:
                raise ValueError("Archived source hash differs")
            seen.add(oid)
            output.append(
                dict(
                    **row,
                    **{
                        k: group[k]
                        for k in (
                            "group_id",
                            "disposition",
                            "review_method",
                            "related_object_ids",
                            "interpretation_rules",
                            "counterparts",
                            "limit",
                        )
                    },
                )
            )
    if seen != set(by_id):
        raise ValueError("Missing editorial disposition")
    earlier = json.loads(
        (ROOT / "geospatial/completion/SOURCE_REVIEW.json").read_text()
    )
    summary = dict(
        baseline_revision=packet["baseline"],
        source_files=len(paths),
        grouped_wordings=len(packet["groups"]),
        reviewed_carriers=len(output),
        prior_reviewed_carriers=earlier["cumulative_reviewed_carriers"],
        cumulative_reviewed_carriers=earlier["cumulative_reviewed_carriers"]
        + len(output),
        remaining_baseline_carriers=0,
        dispositions=dict(sorted(Counter(r["disposition"] for r in output).items())),
        group_decisions_sha256=digest((BASE / "GROUP_DECISIONS.json.gz").read_bytes()),
        extraction_sha256=digest((BASE / "EXTRACTED_RESIDUAL.json.gz").read_bytes()),
        baseline_carrier_adjudication_complete=True,
        subsequent_source_review_separate=True,
        semantic_census_complete=False,
        issue_108_complete=False,
        scope="All remaining baseline discovery carriers have an exact fixed editorial disposition. "
        "This does not treat every carrier as a geographic claim or every source claim as current canon. "
        "Subsequent source review, visual evidence, geography and delivery have separate acceptance checks.",
    )
    return summary, sorted(output, key=lambda r: r["occurrence_id"])


def write(output):
    output.mkdir(parents=True, exist_ok=True)
    summary, rows = review()
    (output / "SOURCE_ADJUDICATION.json.gz").write_bytes(
        gzip.compress(json.dumps(rows, ensure_ascii=False).encode(), mtime=0)
    )
    (output / "SOURCE_REVIEW.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary, rows


if __name__ == "__main__":
    print(json.dumps(write(BASE)[0], indent=2))
