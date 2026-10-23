#!/usr/bin/env python3
"""Verify exact historical Git blob copies without network or source worktrees."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

repo = Path(__file__).resolve().parents[4]
manifest = json.loads((Path(__file__).resolve().parent / 'MANIFEST.json').read_text())
assert manifest['unique_git_blob_count'] == 18
assert len(manifest['entries']) == 18
count = 0
for entry in manifest['entries']:
    for rel in entry['destination_paths']:
        path = repo / rel
        data = path.read_bytes()
        assert len(data) == entry['source_bytes'], rel
        assert hashlib.sha256(data).hexdigest() == entry['source_sha256'], rel
        oid = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
        assert oid == entry['source_git_blob_oid'], rel
        count += 1
assert count == manifest['preserved_file_count'] == 19
print(f'PASS: {len(manifest["entries"])} unique historical blobs, {count} byte-exact files')
