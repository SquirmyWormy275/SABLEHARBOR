"""Verify the transfer manifest against accepted source and release indexes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    repo = root.parents[2]
    manifest = json.loads((root / "SOURCE_MANIFEST.json").read_text())
    original_bytes = (root / "TRANSFER_MANIFEST.json").read_bytes()
    assert len(original_bytes) == manifest["source_manifest_bytes"]
    assert hashlib.sha256(original_bytes).hexdigest() == manifest["source_manifest_sha256"]
    original = json.loads(original_bytes)
    assert original["repository_execution_performed"] is False
    assert original["geographic_conflict_resolution_performed"] is False

    accepted = {entry["member"]: entry for entry in manifest["accepted_payload_members"]}
    assert len(accepted) == len(original["files"]) == 3
    for entry in original["files"]:
        target = accepted[entry["path"]]
        assert (entry["bytes"], entry["sha256"]) == (
            target["bytes"],
            target["sha256"],
        )
        data = (repo / target["accepted_path"]).read_bytes()
        assert len(data) == target["bytes"]
        assert hashlib.sha256(data).hexdigest() == target["sha256"]

    release_index = json.loads(
        (repo / "geospatial/history/foundation-addendum-2026-09-05/SOURCE_MANIFEST.json").read_text()
    )
    addendum = next(
        item for item in release_index["packages"] if "Addendum" in item["asset_name"]
    )
    release_members = {item["path"]: item for item in addendum["members"]}
    for entry in original["source_files"]:
        path = "repository/geospatial/history/mandates/" + entry["filename"]
        found = release_members[path]
        assert (found["bytes"], found["sha256"]) == (
            entry["bytes"],
            entry["sha256"],
        )
    print("PASS: original transfer provenance, three accepted Git payloads and two release sources")


if __name__ == "__main__":
    main()
