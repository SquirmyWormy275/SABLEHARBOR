"""Verify the September 11 office-work recovery ZIP without extraction."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def verify(archive: Path, source_manifest: Path, originals: Path) -> None:
    manifest = json.loads(source_manifest.read_text())
    raw = archive.read_bytes()
    if (
        len(raw) != manifest["original_archive_bytes"]
        or hashlib.sha256(raw).hexdigest() != manifest["original_archive_sha256"]
    ):
        raise ValueError("archive size or SHA-256 mismatch")

    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise ValueError("ZIP CRC mismatch")
        expected = {row["member"]: row for row in manifest["entries"]}
        actual = {member.filename for member in package.infolist() if not member.is_dir()}
        if actual != set(expected):
            raise ValueError("archive member census mismatch")
        for name, row in expected.items():
            data = package.read(name)
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ValueError(f"member mismatch: {name}")
            if f"{package.getinfo(name).CRC:08x}" != row["crc32"]:
                raise ValueError(f"CRC mismatch: {name}")
            if (originals / name).read_bytes() != data:
                raise ValueError(f"tracked original mismatch: {name}")

        original = json.loads(package.read("RECOVERY-MANIFEST.json"))
        if sorted(original["missing_draft_companions"]) != sorted(manifest["missing_companions"]):
            raise ValueError("missing-companion declaration mismatch")
        for row in original["original_files"]:
            member = expected[row["path"]]
            if member["bytes"] != row["bytes"] or member["sha256"] != row["sha256"]:
                raise ValueError(f"original draft declaration mismatch: {row['path']}")
    print(
        json.dumps(
            {
                "result": "PASS",
                "members": len(expected),
                "declared_originals": len(original["original_files"]),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("SOURCE_MANIFEST.json"),
    )
    parser.add_argument(
        "--originals",
        type=Path,
        default=Path(__file__).with_name("original"),
    )
    args = parser.parse_args()
    verify(args.archive, args.manifest, args.originals)
