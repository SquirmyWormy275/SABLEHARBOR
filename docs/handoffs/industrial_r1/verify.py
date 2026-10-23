#!/usr/bin/env python3
"""Verify the exact September 5 R1 handoff ZIP without extracting it."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(archive: Path, manifest_path: Path, repo: Path | None) -> None:
    manifest = json.loads(manifest_path.read_text())
    archive_bytes = archive.read_bytes()
    if (
        len(archive_bytes) != manifest["original_archive_bytes"]
        or sha256(archive_bytes) != manifest["original_archive_sha256"]
    ):
        raise ValueError("outer ZIP size or SHA-256 mismatch")

    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise ValueError("ZIP CRC mismatch")
        expected = {entry["zip_member"]: entry for entry in manifest["entries"]}
        actual = {member.filename for member in package.infolist() if not member.is_dir()}
        if actual != set(expected):
            raise ValueError(
                f"ZIP file census mismatch: expected {len(expected)}, found {len(actual)}"
            )
        for name, entry in expected.items():
            data = package.read(name)
            if len(data) != entry["bytes"] or sha256(data) != entry["sha256"]:
                raise ValueError(f"member mismatch: {name}")
            if repo is not None and (repo / entry["repository_path"]).read_bytes() != data:
                raise ValueError(f"accepted Git byte mismatch: {entry['repository_path']}")

        checksum_member = next(name for name in expected if name.endswith("/CHECKSUMS.sha256"))
        prefix = checksum_member.removesuffix("CHECKSUMS.sha256")
        checked = 0
        for line in package.read(checksum_member).decode().splitlines():
            digest, relative = line.split("  ", 1)
            if sha256(package.read(prefix + relative)) != digest:
                raise ValueError(f"internal checksum mismatch: {relative}")
            checked += 1
        if checked != manifest["internal_checksums_verified"]:
            raise ValueError("internal checksum count mismatch")
    print(
        json.dumps(
            {
                "result": "PASS",
                "members": len(expected),
                "internal_checksums": checked,
                "repository_bytes_checked": repo is not None,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument(
        "--manifest", type=Path, default=Path(__file__).with_name("SOURCE_MANIFEST.json")
    )
    parser.add_argument(
        "--repo", type=Path, help="optionally compare every member with its accepted Git path"
    )
    args = parser.parse_args()
    verify(args.archive, args.manifest, args.repo)
