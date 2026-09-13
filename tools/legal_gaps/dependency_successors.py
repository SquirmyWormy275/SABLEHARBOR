"""Exact, audited compatibility of one historical dependency with accepted main.

This does not validate the original whole-file pin against new bytes. It records
why one identified instrument can remain unchanged across one accepted transition.
No general allowlist, Git/network dependency, or transitive successor acceptance.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

RECORD = "docs/legal/gap-instruments/dependency-successors/PR162.json"
RECORD_SHA256 = "8b13014537e5c1ca36d68a28e4db6c4e14b8991f4e8c11205797046c4864e804"
DOCUMENT_ID = "SH-LEGAL-DRAFT-HOST-RIGHTS"
DEPENDENCY = "geospatial/registers/SITE_REGISTER.csv"
BEFORE_SHA256 = "df07fc9b2225114deafbad5536c625982c73730ed486cbef15b5fd7a34a86fa8"
AFTER_SHA256 = "d9d445d6ebab15bad40186a7de742ddd881b3971119ae7da3ae95cb1886f6720"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rows(data):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
    result = {}
    for row in reader:
        identity = row["object_id"]
        if identity in result or None in row or None in row.values():
            raise ValueError("Malformed or duplicate site row")
        result[identity] = row
    return reader.fieldnames, result


def accepted_dependency_successor(root: Path, document_id: str, item: dict) -> str | None:
    """Return the audited disposition ID only for the exact dependency transition.

    Call this only for package dependencies, never sources or generated artifacts.
    Missing evidence, any byte drift, different instruments and changed source
    pins fail closed. A future accepted change needs its own reviewed successor.
    """
    if (document_id, item.get("path"), item.get("sha256")) != (
        DOCUMENT_ID,
        DEPENDENCY,
        BEFORE_SHA256,
    ):
        return None
    try:
        root = Path(root)
        raw = (root / RECORD).read_bytes()
        if sha(raw) != RECORD_SHA256:
            return None
        record = json.loads(raw)
        before = (root / record["baseline_snapshot"]).read_bytes()
        after = (root / DEPENDENCY).read_bytes()
        if sha(before) != BEFORE_SHA256 or sha(after) != AFTER_SHA256:
            return None
        if sha((root / record["canon_path"]).read_bytes()) != record["canon_sha256"]:
            return None
        before_fields, a = rows(before)
        after_fields, b = rows(after)
        if before_fields != after_fields or a.keys() != b.keys() or len(a) != record["row_count"]:
            return None
        actual_changes = [
            {"object_id": key, "before": a[key], "after": b[key]} for key in a if a[key] != b[key]
        ]
        if actual_changes != record["changed_rows"]:
            return None
        if {r["object_id"] for r in actual_changes} != {"SH-SITE-0002", "SH-SITE-0003"}:
            return None
        if any(
            a[key] != row or b[key] != row for key, row in record["unchanged_relevant_rows"].items()
        ):
            return None
        return record["id"]
    except (OSError, ValueError, KeyError, TypeError, csv.Error):
        return None
