"""Exact public original transport within the pinned CompanyStore byte bounds."""

from __future__ import annotations

import hashlib

from .edition import EditionError, encoded, sha

MAX_BYTES = 25 * 1024 * 1024


def prepare(path, content, limit=MAX_BYTES):
    """Keep ordinary originals intact; explicitly describe empty or multipart originals."""
    if not 0 < limit <= MAX_BYTES:
        raise EditionError("Transport cannot exceed the existing store limit")
    record = "DOC-" + sha(path.encode())[:40]
    if 0 < len(content) <= limit:
        return [dict(record=record, content=content, kind="EXACT_ORIGINAL")]
    parts = [
        dict(
            record=f"{record}-P{index:06d}",
            content=content[start : start + limit],
            kind="BYTE_PART",
        )
        for index, start in enumerate(range(0, len(content), limit), 1)
    ]
    manifest = {
        "transport_format": "SH-EXACT-BYTE-PARTS-1",
        "source_path": path,
        "source_bytes": len(content),
        "source_sha256": sha(content),
        "parts": [
            {"record": p["record"], "bytes": len(p["content"]), "sha256": sha(p["content"])}
            for p in parts
        ],
        "qualification": "Transport metadata; not a business event or an original source document",
    }
    marker = encoded(manifest)
    if len(marker) > MAX_BYTES:
        raise EditionError("Transport manifest exceeds the existing store limit")
    return [dict(record=record, content=marker, kind="TRANSPORT_MANIFEST"), *parts]


def verify_original(path, expected_sha, expected_bytes, prepared, read):
    """Independently reconstruct ordered store bytes, including zero-byte originals."""
    import json

    record = "DOC-" + sha(path.encode())[:40]
    if not prepared or not isinstance(prepared[0], dict):
        raise EditionError("Missing transport original identity")
    first = prepared[0]
    if first.get("record") != record or first.get("kind") not in {
        "EXACT_ORIGINAL",
        "TRANSPORT_MANIFEST",
    }:
        raise EditionError("Transport record identity or kind differs from original path")
    if first["kind"] == "EXACT_ORIGINAL":
        content = read(first["record"])
        if (
            len(prepared) != 1
            or not 0 < len(content) <= MAX_BYTES
            or len(content) != expected_bytes
            or sha(content) != expected_sha
        ):
            raise EditionError("Original readback changed")
        return
    for index, part in enumerate(prepared[1:], 1):
        if part.get("kind") != "BYTE_PART" or part.get("record") != f"{record}-P{index:06d}":
            raise EditionError("Transport part identity or kind differs from original path")
    marker = read(first["record"])
    if not 0 < len(marker) <= MAX_BYTES:
        raise EditionError("Transport manifest violates store byte bound")
    manifest = json.loads(marker)
    if (
        manifest.get("transport_format") != "SH-EXACT-BYTE-PARTS-1"
        or manifest.get("source_path") != path
        or manifest.get("source_sha256") != expected_sha
        or manifest.get("source_bytes") != expected_bytes
    ):
        raise EditionError("Transport manifest changed source identity")
    identifiers = [p["record"] for p in manifest["parts"]]
    if len(set(identifiers)) != len(identifiers) or identifiers != [
        p["record"] for p in prepared[1:]
    ]:
        raise EditionError("Missing, duplicate or reordered transport part")
    digest, size = hashlib.sha256(), 0
    for part in manifest["parts"]:
        content = read(part["record"])
        if (
            not 0 < len(content) <= MAX_BYTES
            or len(content) != part["bytes"]
            or sha(content) != part["sha256"]
        ):
            raise EditionError("Transport part changed")
        digest.update(content)
        size += len(content)
    if size != expected_bytes or digest.hexdigest() != expected_sha:
        raise EditionError("Reassembled original changed")
