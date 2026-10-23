#!/usr/bin/env python3
"""Verify exact historical geographic preview sources and optional release assets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parent


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def members(path: Path) -> dict[str, dict[str, object]]:
    actual: dict[str, dict[str, object]] = {}
    with ZipFile(path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            if member.filename in actual:
                raise ValueError(f"duplicate ZIP member: {member.filename}")
            digest = hashlib.sha256()
            count = 0
            with archive.open(member) as stream:
                for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                    digest.update(chunk)
                    count += len(chunk)
            actual[member.filename] = {
                "bytes": count,
                "sha256": digest.hexdigest(),
                "crc32": f"{member.CRC:08x}",
            }
    return actual


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-dir", type=Path)
    parser.add_argument("--accepted-package", type=Path)
    args = parser.parse_args()
    if args.accepted_package and not args.asset_dir:
        parser.error("--accepted-package requires --asset-dir")

    source = json.loads((ROOT / "SOURCE_MANIFEST.json").read_text())
    for relative, expected in source["tracked_originals"].items():
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size != expected["bytes"]:
            raise ValueError(f"tracked original missing or size mismatch: {relative}")
        if sha256_file(path) != expected["sha256"]:
            raise ValueError(f"tracked original hash mismatch: {relative}")

    result: dict[str, object] = {"tracked_originals": len(source["tracked_originals"])}
    if args.asset_dir:
        accepted = None
        if args.accepted_package:
            expected = source["accepted_package"]
            if (
                args.accepted_package.stat().st_size != expected["bytes"]
                or sha256_file(args.accepted_package) != expected["sha256"]
            ):
                raise ValueError("accepted v1.5.0 package hash mismatch")
            accepted = members(args.accepted_package)

        for name, expected in source["previews"].items():
            path = args.asset_dir / expected["asset"]
            if path.stat().st_size != expected["bytes"] or sha256_file(path) != expected["sha256"]:
                raise ValueError(f"historical preview ZIP hash mismatch: {name}")
            actual = members(path)
            if actual != expected["members"]:
                raise ValueError(f"historical preview ZIP member mismatch: {name}")
            if accepted is not None:
                same = {
                    key
                    for key in actual.keys() & accepted.keys()
                    if actual[key]["sha256"] == accepted[key]["sha256"]
                    and actual[key]["bytes"] == accepted[key]["bytes"]
                }
                comparison = expected["accepted_member_comparison"]
                if (
                    len(same) != comparison["equal_count"]
                    or sorted(actual.keys() & accepted.keys() - same) != comparison["differing"]
                    or sorted(accepted.keys() - actual.keys()) != comparison["missing"]
                    or sorted(actual.keys() - accepted.keys()) != comparison["extra"]
                ):
                    raise ValueError(f"accepted-member comparison mismatch: {name}")
        result["release_assets"] = len(source["previews"])
        if accepted is not None:
            result["accepted_package_comparison"] = "passed"
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
