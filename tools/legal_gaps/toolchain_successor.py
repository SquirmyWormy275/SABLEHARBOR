"""Verify an exact historical build-environment successor without resealing artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

RECORD = "docs/legal/gap-instruments/dependency-successors/PR168-toolchain.json"
RECORD_SHA256 = "c8d81197607675076ee4a117c03b292eb8875e382cc321d6b7f8b0b6ebf112ea"
PATCHED_RECORD = "docs/legal/gap-instruments/dependency-successors/PR211-toolchain.json"
PATCHED_RECORD_SHA256 = "50be5c8ad83d62368a03736b461ea257f230ec8f4090c4d45a1f21e9cf862fed"
DEPENDENCY = "tools/legal_gaps/requirements.txt"


def historical_toolchain_successor(root: Path, item: dict) -> str | None:
    """Only for manifest inputs; never applies to publications or company sources."""
    if item.get("path") != DEPENDENCY:
        return None
    try:
        raw = (root / RECORD).read_bytes()
        if hashlib.sha256(raw).hexdigest() != RECORD_SHA256:
            return None
        record = json.loads(raw)
        before = (root / record["baseline_snapshot"]).read_bytes()
        after = (root / DEPENDENCY).read_bytes()
        if item.get("sha256") != record["before_sha256"]:
            return None
        if hashlib.sha256(before).hexdigest() != record["before_sha256"]:
            return None
        predecessor = before.replace(b"PyMuPDF==1.26.6", b"PyMuPDF==1.26.7").replace(
            b"pytest==8.4.2", b"pytest==9.0.3"
        )
        if hashlib.sha256(predecessor).hexdigest() != record["after_sha256"]:
            return None
        if after == predecessor:
            return record["id"]
        patched_raw = (root / PATCHED_RECORD).read_bytes()
        if hashlib.sha256(patched_raw).hexdigest() != PATCHED_RECORD_SHA256:
            return None
        patched = json.loads(patched_raw)
        patched_before = (root / patched["baseline_snapshot"]).read_bytes()
        if (patched["path"] != DEPENDENCY
                or patched["prior_successor_id"] != record["id"]
                or patched_before != predecessor
                or hashlib.sha256(patched_before).hexdigest() != patched["before_sha256"]
                or patched_before.count(b"Pillow==12.3.0") != 1):
            return None
        expected = patched_before.replace(b"Pillow==12.3.0", b"Pillow==13.0.0")
        if after != expected or hashlib.sha256(after).hexdigest() != patched["after_sha256"]:
            return None
        return patched["id"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
