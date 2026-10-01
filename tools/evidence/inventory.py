"""Reconcile source coverage against Git objects without promoting geographic claims."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path


def tree(root, revision):
    raw = subprocess.check_output(["git", "ls-tree", "-r", "-z", revision], cwd=root)
    result = {}
    for entry in raw.split(b"\0"):
        if entry:
            metadata, path = entry.split(b"\t", 1)
            _, kind, oid = metadata.decode().split()
            if kind != "blob":
                raise ValueError("Source inventory requires ordinary Git blobs")
            result[path.decode()] = oid
    return result


def fingerprints(root, oids):
    """Use one batch read and verify each returned object identity and byte count."""
    ordered = sorted(set(oids))
    raw = subprocess.check_output(
        ["git", "cat-file", "--batch"],
        cwd=root,
        input=("\n".join(ordered) + "\n").encode(),
    )
    offset = 0
    result = {}
    for expected in ordered:
        end = raw.index(b"\n", offset)
        oid, kind, size = raw[offset:end].decode().split()
        if oid != expected or kind != "blob":
            raise ValueError("Archived object mismatch")
        size = int(size)
        start = end + 1
        content = raw[start : start + size]
        if len(content) != size or raw[start + size : start + size + 1] != b"\n":
            raise ValueError("Truncated archived object")
        result[oid] = (size, hashlib.sha256(content).hexdigest())
        offset = start + size + 1
    if offset != len(raw):
        raise ValueError("Unexpected archived bytes")
    return result


def inventory(root: Path, revision: str, residual):
    manifest = json.loads(
        (root / "geospatial/registers/CENSUS_MANIFEST.json").read_text()
    )
    baseline = manifest["source_commit"]
    previous, current = tree(root, baseline), tree(root, revision)
    with (root / "geospatial/registers/SOURCE_COVERAGE.csv").open() as f:
        coverage = list(csv.DictReader(f))
    paths = [r["source_path"] for r in coverage]
    if len(paths) != len(set(paths)) or set(paths) != set(previous):
        raise ValueError(
            "Coverage does not account for every baseline file exactly once"
        )
    hashes = fingerprints(root, previous.values())
    counts = Counter(row["source_path"] for row in residual)
    if not set(counts) <= set(paths):
        raise ValueError("Residual occurrences reference unknown baseline files")
    rows = []
    for row in coverage:
        path = row["source_path"]
        size, digest = hashes[previous[path]]
        if (
            row["source_commit"] != baseline
            or int(row["bytes"]) != size
            or row["file_sha256"] != digest
        ):
            raise ValueError(f"Archived source fingerprint mismatch: {path}")
        status = (
            "REMOVED"
            if path not in current
            else ("UNCHANGED" if current[path] == previous[path] else "MODIFIED")
        )
        rows.append(
            {
                **row,
                "archive_verified": True,
                "current_status": status,
                "baseline_git_blob": previous[path],
                "current_git_blob": current.get(path, ""),
                "residual_occurrences": counts[path],
                "review_boundary": "VISUAL_OR_OCR_REVIEW_REQUIRED"
                if any(
                    x in row["extraction_method"]
                    for x in ("IMAGE_", "PDF_", "UNSUPPORTED_")
                )
                else "SEMANTIC_REVIEW_NOT_ESTABLISHED",
            }
        )
    deltas = [
        {
            "source_path": p,
            "change": "ADDED"
            if p not in previous
            else "REMOVED"
            if p not in current
            else "MODIFIED",
            "baseline_git_blob": previous.get(p, ""),
            "current_git_blob": current.get(p, ""),
        }
        for p in sorted(previous.keys() | current.keys())
        if previous.get(p) != current.get(p)
    ]
    site_register = root / "geospatial/registers/SITE_REGISTER_CURRENT.csv"
    if not site_register.exists():
        site_register = root / "geospatial/registers/SITE_REGISTER.csv"
    with site_register.open() as f:
        sites = list(csv.DictReader(f))
    if len({r["object_id"] for r in sites}) != len(sites):
        raise ValueError("Site identifiers must be unique")
    return {
        "baseline_revision": baseline,
        "current_revision": revision,
        "baseline_sources": rows,
        "subsequent_changes": deltas,
        "sites": sites,
        "site_register": str(site_register.relative_to(root)),
        "summary": {
            "baseline_files_verified": len(rows),
            "baseline_bytes_verified": sum(int(r["bytes"]) for r in rows),
            "current_files": len(current),
            "change_counts": dict(Counter(r["change"] for r in deltas)),
            "visual_or_ocr_review_required": sum(
                r["review_boundary"] == "VISUAL_OR_OCR_REVIEW_REQUIRED" for r in rows
            ),
            "site_records": len(sites),
            "semantic_census_complete": False,
        },
    }
