"""Verify an exact historical build-environment successor without resealing artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

RECORD = "docs/legal/gap-instruments/dependency-successors/PR168-toolchain.json"
RECORD_SHA256 = "c8d81197607675076ee4a117c03b292eb8875e382cc321d6b7f8b0b6ebf112ea"
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
        if hashlib.sha256(after).hexdigest() != record["after_sha256"]:
            return None
        expected = before.replace(b"PyMuPDF==1.26.6", b"PyMuPDF==1.26.7").replace(
            b"pytest==8.4.2", b"pytest==9.0.3"
        )
        if after != expected:
            return None
        return record["id"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
