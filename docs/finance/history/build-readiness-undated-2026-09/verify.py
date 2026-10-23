"""Check the historical PDF's exact original bytes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "SOURCE_MANIFEST.json").read_text())
    pdf = root / manifest["file"]
    data = pdf.read_bytes()
    assert len(data) == manifest["bytes"]
    assert hashlib.sha256(data).hexdigest() == manifest["sha256"]
    assert data.startswith(b"%PDF-")
    print(f"PASS: {pdf.name}; {len(data)} bytes; SHA-256 {manifest['sha256']}")


if __name__ == "__main__":
    main()
