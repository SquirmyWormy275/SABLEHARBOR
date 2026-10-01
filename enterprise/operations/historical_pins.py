"""Verify frozen source pins after additive organization successors.

The September 22 J2 records cite the then-current chart and facility register.
Their exact bytes now live in dated history paths. Current successors may add
people, but cannot change the earlier J2 or person population.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PREDECESSORS = {
    "docs/organization/source/chartbook.json": (
        "6471a6362517f97574c775b73b94ac48d6060d81cee605eb661811425ed75866",
        "docs/organization/history/v1.1.0/chartbook.json",
    ),
    "geospatial/facilities/population/REGISTER.json": (
        "203f71aaf75128f0aa3b0b649e9400173fe366fc9a3e6dd528a6a1b176d013d7",
        "geospatial/facilities/population/history/v1.1.0/REGISTER.json",
    ),
}


def _rows(records, key, failure):
    rows = {row[key]: row for row in records}
    if len(rows) != len(records):
        raise ValueError(failure)
    return rows


def verify(root: Path, path: str, expected: str, *, failure: str) -> str:
    """Return the exact current or preserved path for a historical source pin."""
    current = (root / path).read_bytes()
    if hashlib.sha256(current).hexdigest() == expected:
        return path
    if path not in PREDECESSORS or expected != PREDECESSORS[path][0]:
        raise ValueError(failure + path)
    preserved_path = PREDECESSORS[path][1]
    preserved = (root / preserved_path).read_bytes()
    if hashlib.sha256(preserved).hexdigest() != expected:
        raise ValueError(failure + path)

    earlier, successor = json.loads(preserved), json.loads(current)
    if path == "docs/organization/source/chartbook.json":
        prior_rows = _rows(earlier["nodes"], "id", failure + path)
        next_rows = _rows(successor["nodes"], "id", failure + path)
    else:
        if earlier["j2"] != successor["j2"]:
            raise ValueError(failure + path)
        prior_rows = _rows(earlier["people"], "person_id", failure + path)
        next_rows = _rows(successor["people"], "person_id", failure + path)
    if any(next_rows.get(identifier) != row for identifier, row in prior_rows.items()):
        raise ValueError(failure + path)
    return preserved_path
