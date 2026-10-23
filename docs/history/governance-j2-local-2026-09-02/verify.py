"""Verify the exact September 2 local-branch historical source package."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath


def digest_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def verify(archive: Path, manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text())
    assert archive.name == manifest["archive_filename"]
    assert archive.stat().st_size == manifest["archive_bytes"]
    assert digest_file(archive) == manifest["archive_sha256"]
    items = manifest["items"]
    assert len(items) == manifest["item_count"] == 13
    expected = {item["member"]: item for item in items}
    assert len(expected) == len(items)
    total = 0
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        assert len(names) == len(set(names)) and set(names) == set(expected)
        for name in names:
            path = PurePosixPath(name)
            assert not path.is_absolute() and ".." not in path.parts
            item = expected[name]
            assert package.getinfo(name).file_size == item["bytes"]
            sha256 = hashlib.sha256()
            git_sha1 = hashlib.sha1(
                f"blob {item['bytes']}\0".encode(), usedforsecurity=False
            )
            observed = 0
            with package.open(name) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    observed += len(chunk)
                    sha256.update(chunk)
                    git_sha1.update(chunk)
            assert observed == item["bytes"]
            assert sha256.hexdigest() == item["sha256"]
            assert git_sha1.hexdigest() == item["git_blob_oid"]
            total += observed
    assert total == manifest["member_bytes"]
    return {
        "status": "PASS",
        "archive_sha256": manifest["archive_sha256"],
        "member_count": len(items),
        "member_bytes": total,
        "authority": manifest["authority"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument(
        "--manifest", type=Path, default=Path(__file__).with_name("MANIFEST.json")
    )
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.manifest), sort_keys=True))


if __name__ == "__main__":
    main()
