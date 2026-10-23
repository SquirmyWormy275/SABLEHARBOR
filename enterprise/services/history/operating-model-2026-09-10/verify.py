"""Verify the exact September 10 service operating-model ZIP and originals."""

import argparse
import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def verify(archive: Path, repo: Path | None) -> dict:
    manifest = json.loads((HERE / "SOURCE_MANIFEST.json").read_text())
    raw = archive.read_bytes()
    if len(raw) != manifest["archive_bytes"] or sha256(raw) != manifest["archive_sha256"]:
        raise ValueError("Original ZIP size or SHA-256 mismatch")
    expected = {row["member"]: row for row in manifest["members"]}
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise ValueError("ZIP CRC mismatch")
        names = {member.filename for member in package.infolist() if not member.is_dir()}
        if names != set(expected) or len(names) != manifest["original_regular_members"]:
            raise ValueError("ZIP member census mismatch")
        internal = json.loads(package.read("manifest.json"))["files"]
        if len(internal) != manifest["original_internal_manifest_declared_members"]:
            raise ValueError("Internal manifest count mismatch")
        for name, row in expected.items():
            info = package.getinfo(name)
            data = package.read(info)
            if len(data) != row["bytes"] or sha256(data) != row["sha256"]:
                raise ValueError(f"ZIP member differs: {name}")
            if f"{info.CRC:08x}" != row["crc32"]:
                raise ValueError(f"ZIP CRC differs: {name}")
            if (HERE / "original" / name).read_bytes() != data:
                raise ValueError(f"Tracked original differs: {name}")
            if name in internal and internal[name] != row["sha256"]:
                raise ValueError(f"Internal manifest differs: {name}")
            current = row["accepted_current_exact_path"]
            if repo is not None and current and (repo / current).read_bytes() != data:
                raise ValueError(f"Accepted current Git member differs: {name}")
        if set(internal) != names - {"manifest.json", "services.sqlite3"}:
            raise ValueError("Internal manifest member set mismatch")
    database = HERE / "original" / "services.sqlite3"
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as db:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Historical SQLite quick_check failed")
    return {
        "result": "PASS",
        "archive_sha256": manifest["archive_sha256"],
        "members": len(expected),
        "internal_manifest_members": len(internal),
        "historical_sqlite_quick_check": "ok",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--repo", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.repo), sort_keys=True))
