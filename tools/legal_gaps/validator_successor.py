"""Exact maintenance successor for two historically reviewed validators."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

RECORD = "docs/legal/gap-instruments/dependency-successors/PR168-validators.json"
RECORD_SHA256 = "85dd75a29a8f14566945b91562a0f5e57e6119dc26224fffe444932ea2e28ea3"
PATHS = {"tools/legal_gaps/validate.py", "tools/legal_gaps/validate_close_review_v43.py"}


def verified_validator_successor(root: Path, relative: str, original_digest: str) -> bool:
    if relative not in PATHS:
        return False
    try:
        raw = (root / RECORD).read_bytes()
        if hashlib.sha256(raw).hexdigest() != RECORD_SHA256:
            return False
        record = json.loads(raw)
        entries = record["entries"]
        if len(entries) != 2 or {e["path"] for e in entries} != PATHS:
            return False
        for entry in entries:
            before = (root / entry["baseline_snapshot"]).read_bytes()
            after = (root / entry["path"]).read_bytes()
            if hashlib.sha256(before).hexdigest() != entry["before_sha256"]:
                return False
            if hashlib.sha256(after).hexdigest() != entry["after_sha256"]:
                return False
        return next(e for e in entries if e["path"] == relative)["before_sha256"] == original_digest
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        return False
