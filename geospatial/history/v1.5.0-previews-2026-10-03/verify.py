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

    equivalence = json.loads((ROOT / "CACHE_EQUIVALENCE.json").read_text())
    for name, expected in source["cache_archives"].items():
        path = ROOT / expected["tracked_path"]
        if (
            path.stat().st_size != expected["manifest_bytes"]
            or sha256_file(path) != expected["manifest_sha256"]
        ):
            raise ValueError(f"cache provenance manifest hash mismatch: {name}")
        manifest = json.loads(path.read_text())
        counts = {kind: 0 for kind in ("file", "directory", "symlink")}
        members_by_path = {}
        file_bytes = 0
        for member in manifest["members"]:
            counts[member["kind"]] += 1
            members_by_path[member["path"]] = member
            if member["kind"] == "file":
                file_bytes += member["size"]
            if member["kind"] == "symlink" and not member["path"].startswith(".venv/"):
                raise ValueError(f"cache has non-environment symlink: {name}")
        if (
            len(manifest["members"]) != expected["member_count"]
            or counts["file"] != expected["file_count"]
            or counts["directory"] != expected["directory_count"]
            or counts["symlink"] != expected["symlink_count"]
            or file_bytes != expected["logical_file_bytes"]
        ):
            raise ValueError(f"cache member manifest count mismatch: {name}")
        family = equivalence["families"][name]
        if (
            family["manifest_sha256"] != expected["manifest_sha256"]
            or family["archive_sha256"] != expected["archive_sha256"]
            or sum(family["disposition_counts"].values()) != counts["file"]
            or family["unresolved_file_members"] != 0
        ):
            raise ValueError(f"cache equivalence receipt mismatch: {name}")
        if name == "C18":
            for preview in source["previews"].values():
                outer_path = preview["outer_member_path"].removeprefix("TREE/")
                member = members_by_path[outer_path]
                if member["sha256"] != preview["sha256"] or member["size"] != preview["bytes"]:
                    raise ValueError("C18 preview archive member mismatch")
        else:
            accepted = source["accepted_package"]
            for outer_path in (
                "var/geographic/sable-harbor-geographic-evidence-v1.5.0.zip",
                "var/geographic/retrieval-check/sable-harbor-geographic-evidence-v1.5.0.zip",
            ):
                member = members_by_path[outer_path]
                if member["sha256"] != accepted["sha256"] or member["size"] != accepted["bytes"]:
                    raise ValueError("C19 accepted release member mismatch")

    result: dict[str, object] = {
        "tracked_originals": len(source["tracked_originals"]),
        "cache_manifests": len(source["cache_archives"]),
    }
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
