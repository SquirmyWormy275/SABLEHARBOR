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

    first = prepared[0]
    if first["kind"] == "EXACT_ORIGINAL":
        content = read(first["record"])
        if len(prepared) != 1 or len(content) != expected_bytes or sha(content) != expected_sha:
            raise EditionError("Original readback changed")
        return
    manifest = json.loads(read(first["record"]))
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
        if len(content) != part["bytes"] or sha(content) != part["sha256"]:
            raise EditionError("Transport part changed")
        digest.update(content)
        size += len(content)
    if size != expected_bytes or digest.hexdigest() != expected_sha:
        raise EditionError("Reassembled original changed")
