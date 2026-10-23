"""Verify direct historical Git blobs from the local operations/repository intake."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MANIFEST = Path(__file__).with_name("MANIFEST.json")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["item_count"] == len(manifest["items"]) == 2
    for item in manifest["items"]:
        path = (ROOT / item["destination"]).resolve()
        assert path.is_relative_to(ROOT) and path.is_file() and not path.is_symlink()
        data = path.read_bytes()
        assert len(data) == item["bytes"]
        assert hashlib.sha256(data).hexdigest() == item["sha256"]
        git_blob = hashlib.sha1(
            f"blob {len(data)}\0".encode() + data, usedforsecurity=False
        ).hexdigest()
        assert git_blob == item["git_blob_oid"]
    print(json.dumps({"status": "PASS", "item_count": 2}, sort_keys=True))


if __name__ == "__main__":
    main()
