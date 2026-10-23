"""Check exact historical company closeout and owner-decision sources."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "SOURCE_MANIFEST.json").read_text())
    assert len(manifest["files"]) == 4
    seen = set()
    for entry in manifest["files"]:
        name = entry["file"]
        assert Path(name).name == name and name not in seen
        seen.add(name)
        data = (root / name).read_bytes()
        assert len(data) == entry["bytes"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    print("PASS: four September 14–15 original closeout/voice sources")


if __name__ == "__main__":
    main()
