#!/usr/bin/env python3
"""Verify downloaded historical ZIP assets against the accepted source index."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent


def digest_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def digest_file(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def verify(directory):
    manifest = json.loads((HERE / "SOURCE_MANIFEST.json").read_text())
    receipts = []
    for package in manifest["packages"]:
        path = directory / package["asset_name"]
        if path.stat().st_size != package["bytes"] or digest_file(path) != package["sha256"]:
            raise ValueError(f"Package hash/size differs: {path.name}")
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError(f"ZIP CRC failed: {path.name}")
            declared = {row["path"]: row for row in package["members"]}
            actual = {item.filename: item for item in archive.infolist() if not item.is_dir()}
            if set(actual) != set(declared):
                raise ValueError(f"ZIP member set differs: {path.name}")
            for name, item in actual.items():
                member = PurePosixPath(name)
                if member.is_absolute() or ".." in member.parts:
                    raise ValueError(f"Unsafe ZIP member path: {name}")
                row = declared[name]
                if item.file_size != row["bytes"]:
                    raise ValueError(f"ZIP member size differs: {name}")
                if digest_bytes(archive.read(item)) != row["sha256"]:
                    raise ValueError(f"ZIP member SHA-256 differs: {name}")
            internal = package["internal_manifest_member"]
            if digest_bytes(archive.read(internal)) != package["internal_manifest_sha256"]:
                raise ValueError(f"Internal manifest differs: {path.name}")
            declared_rows = json.loads(archive.read(internal))
            entries = declared_rows.get("files") or declared_rows.get("entries")
            if len(entries) != package["internal_manifest_declared_files_verified"]:
                raise ValueError(f"Internal manifest count differs: {path.name}")
        receipts.append({"asset": path.name, "sha256": package["sha256"],
                         "members_verified": len(actual), "zip_crc_pass": True})
    return receipts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.asset_directory), indent=2))
