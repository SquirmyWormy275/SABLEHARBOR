"""Verify exact September 9 organization draft originals and local duplicates."""

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(downloads: Path | None) -> dict:
    manifest = json.loads((HERE / "SOURCE_MANIFEST.json").read_text())
    expected = {row["name"]: row for row in manifest["files"]}
    actual = {path.name for path in (HERE / "original").iterdir() if path.is_file()}
    if actual != set(expected) or len(expected) != manifest["original_file_count"]:
        raise ValueError("historical original file census mismatch")
    for name, row in expected.items():
        source = HERE / "original" / name
        if source.stat().st_size != row["bytes"] or sha256(source) != row["sha256"]:
            raise ValueError(f"historical original mismatch: {name}")
        if downloads is not None:
            for local_name in (name, row["duplicate_local_basename"]):
                candidate = downloads / local_name
                if candidate.stat().st_size != row["bytes"] or sha256(candidate) != row["sha256"]:
                    raise ValueError(f"local candidate mismatch: {local_name}")
    return {
        "result": "PASS",
        "originals": len(expected),
        "local_download_candidates_verified": len(expected) * 2 if downloads else 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--downloads", type=Path)
    print(json.dumps(verify(parser.parse_args().downloads), sort_keys=True))
