"""Verify the actual approved PNG is present in the controlled PDF and catalog."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets/headquarters/exterior/2026-09-22/sacramento-hq-exterior.png"
DECISION = ROOT / "docs/canon/HEADQUARTERS_IMAGE_SUCCESSOR_2026-09-22.md"
PDF = ROOT / "docs/governance/publications/SH-CORP-HQ-IMAGE-20260922_v1.0.0.pdf"
MANIFEST = ROOT / "docs/governance/publication_manifest.json"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def test_current_headquarters_image_is_published_as_exact_pixels() -> None:
    expected = "3296663d8c7be71bca8aee5fad953a6a96b1ecf03a4b021a8dce48f9295afaf3"
    assert digest(SOURCE) == expected
    assert SOURCE.stat().st_size == 2730619
    document = fitz.open(PDF)
    image_objects = [image for page in document for image in page.get_images(full=True)]
    assert len(image_objects) == 1
    source = fitz.Pixmap(str(SOURCE))
    published = fitz.Pixmap(document, image_objects[0][0])
    assert (published.width, published.height, published.n, published.samples) == (
        source.width,
        source.height,
        source.n,
        source.samples,
    )


def test_manifest_binds_visual_source_and_historical_hash_is_distinct() -> None:
    source = "docs/canon/HEADQUARTERS_IMAGE_SUCCESSOR_2026-09-22.md"
    publication = "docs/governance/publications/SH-CORP-HQ-IMAGE-20260922_v1.0.0.pdf"
    manifest = json.loads(MANIFEST.read_text())
    rows = [item for item in manifest["artifacts"] if item["source"] == source]
    assert len(rows) == 1
    assert rows[0]["publication"] == publication
    assert rows[0]["source_sha256"] == digest(DECISION)
    assert rows[0]["sha256"] == digest(PDF)
    assert rows[0]["source_assets"] == [
        {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": digest(SOURCE),
        }
    ]
    old = "2bf5a1209b9c3ece435271f2fbf5a3c827bbbccf242ea4ee60535749ccee9d92"
    assert old in DECISION.read_text()
    assert old != digest(SOURCE)
