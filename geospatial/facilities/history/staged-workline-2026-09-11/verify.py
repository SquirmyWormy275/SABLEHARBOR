#!/usr/bin/env python3
"""Verify exact historical facility recovery ZIPs without extracting them."""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "SOURCE_MANIFEST.json").read_text())
BLOCK = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(BLOCK), b""):
            digest.update(block)
    return digest.hexdigest()


def archive_members(path: Path, expected: list[dict]) -> dict[str, dict]:
    declared = {row["path"]: row for row in expected}
    if len(declared) != len(expected):
        raise ValueError("Duplicate manifest path")
    observed = {}
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            name = member.filename
            parts = PurePosixPath(name).parts
            if name.startswith("/") or ".." in parts or name in observed:
                raise ValueError(f"Unsafe or duplicate ZIP member: {name}")
            row = declared.get(name)
            if row is None or member.file_size != row["bytes"]:
                raise ValueError(f"Unknown or wrong-sized ZIP member: {name}")
            sha = hashlib.sha256()
            git = hashlib.sha1()
            git.update(f"blob {member.file_size}\0".encode())
            size, crc = 0, 0
            with archive.open(member) as stream:
                for block in iter(lambda: stream.read(BLOCK), b""):
                    sha.update(block)
                    git.update(block)
                    size += len(block)
                    crc = binascii.crc32(block, crc)
            if (
                size != row["bytes"]
                or sha.hexdigest() != row["sha256"]
                or git.hexdigest() != row["git_blob_oid"]
                or f"{crc & 0xFFFFFFFF:08x}" != row["zip_crc32"]
            ):
                raise ValueError(f"ZIP member bytes differ: {name}")
            observed[name] = row
        if set(observed) != set(declared):
            raise ValueError("ZIP member set differs from tracked manifest")
        if path.name.startswith("SABLE_HARBOR_COMPLETE_"):
            verify_outer_manifest(archive, observed)
        else:
            verify_inner_manifest(archive, observed)
    return observed


def verify_outer_manifest(archive: zipfile.ZipFile, rows: dict[str, dict]) -> None:
    text = archive.read("MANIFEST.sha256").decode("utf-8")
    declared = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        if name in declared:
            raise ValueError("Duplicate outer checksum entry")
        declared[name] = digest
    if len(declared) != 10 or set(declared) != set(rows) - {"MANIFEST.sha256"}:
        raise ValueError("Outer checksum member set differs")
    for name, digest in declared.items():
        if rows[name]["sha256"] != digest:
            raise ValueError(f"Outer checksum differs: {name}")


def verify_inner_manifest(archive: zipfile.ZipFile, rows: dict[str, dict]) -> None:
    source = json.loads(archive.read("RECOVERY_MANIFEST.json"))
    files = source["files"]
    if source["file_count"] != 483 or len(files) != 483 or source["deleted_paths"]:
        raise ValueError("Staged overlay census differs")
    if source["staged_tree"] != MANIFEST["source_staged_tree_reported"]:
        raise ValueError("Staged tree identity differs")
    for item in files:
        name = "repository-overlay/" + item["path"]
        row = rows.get(name)
        if row is None or (
            row["bytes"] != item["bytes"]
            or row["sha256"] != item["sha256"]
            or row["git_blob_oid"] != item["git_sha"]
        ):
            raise ValueError(f"Declared overlay source differs: {name}")


def verify(directory: Path) -> dict:
    result = {}
    for package in MANIFEST["packages"]:
        path = directory / package["asset_name"]
        if path.stat().st_size != package["bytes"] or sha256_file(path) != package["sha256"]:
            raise ValueError(f"Package bytes differ: {path.name}")
        members = archive_members(path, package["members"])
        result[path.name] = {"sha256": package["sha256"], "members_verified": len(members)}
    inner = MANIFEST["packages"][1]
    outer = MANIFEST["packages"][0]
    nested = next(row for row in outer["members"] if row["path"] == inner["asset_name"])
    if nested["sha256"] != inner["sha256"] or nested["bytes"] != inner["bytes"]:
        raise ValueError("Nested and standalone recovery ZIPs differ")
    return {"status": "PASS", "packages": result, "declared_overlay_files": 483}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_directory", type=Path)
    print(json.dumps(verify(parser.parse_args().asset_directory), indent=2))
