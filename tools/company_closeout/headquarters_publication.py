"""Publish the exact approved HQ PNG alongside the pinned general PDF renderer."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import fitz

from tools.documents import build_controlled_publications as predecessor

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "docs/canon/HEADQUARTERS_IMAGE_SUCCESSOR_2026-09-22.md"
PUBLICATION = "docs/governance/publications/SH-CORP-HQ-IMAGE-20260922_v1.0.0.pdf"
ARTWORK = "assets/headquarters/exterior/2026-09-22/sacramento-hq-exterior.png"
STRUCTURED = "docs/structured/corporate_headquarters_image_successor_2026-09-22.json"
MANIFEST = "docs/governance/publication_manifest.json"
IMAGE_LINE = re.compile(
    r"^!\[Current Sable Harbor Sacramento headquarters exterior\]"
    r"\(\.\./\.\./assets/headquarters/exterior/2026-09-22/sacramento-hq-exterior\.png\)$",
    re.M,
)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked_artwork() -> tuple[Path, str]:
    identity = json.loads((ROOT / STRUCTURED).read_text())
    if identity["current_source_png"] != ARTWORK:
        raise ValueError("structured HQ image path differs from publication source")
    art = ROOT / ARTWORK
    digest = sha256(art)
    if digest != identity["current_source_sha256"]:
        raise ValueError("HQ source artwork differs from controlling structured hash")
    if digest not in (ROOT / SOURCE).read_text():
        raise ValueError("HQ source artwork hash is absent from the controlling decision")
    png = fitz.Pixmap(str(art))
    if [png.width, png.height] != identity["current_dimensions_px"]:
        raise ValueError("HQ image dimensions differ from controlling source")
    if art.stat().st_size != identity["current_source_bytes"]:
        raise ValueError("HQ image size differs from controlling source")
    return art, digest


def render_with_artwork(render_pdf):
    """Return a scoped render hook; the existing renderer's bytes stay pinned."""

    def render(**kwargs):
        if kwargs["src_rel"] != SOURCE:
            return render_pdf(**kwargs)
        art, _digest = checked_artwork()
        source = (ROOT / SOURCE).read_text()
        if len(IMAGE_LINE.findall(source)) != 1:
            raise ValueError("HQ decision must contain one exact source-image reference")
        original_body = predecessor.body

        def body_with_plate_note(markdown: str, source_url: str = "") -> str:
            filtered = IMAGE_LINE.sub(
                "The approved exterior is reproduced in the final image plate.",
                markdown,
            )
            return original_body(filtered, source_url)

        try:
            predecessor.body = body_with_plate_note
            render_pdf(**kwargs)
        finally:
            predecessor.body = original_body

        path = ROOT / kwargs["out_rel"]
        document = fitz.open(path)
        page = document.new_page(width=612, height=792)
        page.insert_text(
            (42, 107), "SABLE HARBOR  /  HEADQUARTERS", fontsize=18, color=(0.08, 0.24, 0.19)
        )
        page.insert_image(fitz.Rect(42, 165, 570, 462), filename=str(art), keep_proportion=True)
        page.insert_text(
            (42, 486), "Current Sacramento headquarters exterior • September 22, 2026", fontsize=10
        )
        page.insert_text(
            (42, 735),
            "SH-CORP-HQ-IMAGE-20260922  |  Source artwork is versioned in Git",
            fontsize=8,
        )
        temporary = path.with_suffix(".artwork.tmp.pdf")
        document.save(temporary, garbage=4, deflate=True, no_new_id=True)
        document.close()
        qpdf = shutil.which("qpdf")
        if not qpdf:
            raise RuntimeError("qpdf is required to normalize the HQ visual publication")
        subprocess.run(
            [
                qpdf,
                "--empty",
                "--pages",
                str(temporary),
                "1-z",
                "--",
                str(path),
                "--remove-info",
                "--remove-metadata",
                "--deterministic-id",
            ],
            check=True,
        )
        temporary.unlink()
        verify_embedded_image(path, art)

    return render


def verify_embedded_image(pdf: Path, art: Path) -> None:
    document = fitz.open(pdf)
    page = document[-1]
    images = page.get_images(full=True)
    if len(images) != 1:
        raise ValueError("HQ publication must contain exactly one image on its visual plate")
    published = fitz.Pixmap(document, images[0][0])
    source = fitz.Pixmap(str(art))
    if (published.width, published.height, published.n, published.samples) != (
        source.width,
        source.height,
        source.n,
        source.samples,
    ):
        raise ValueError("HQ publication pixels differ from approved source artwork")


def bind_artwork() -> None:
    art, digest = checked_artwork()
    manifest_path = ROOT / MANIFEST
    manifest = json.loads(manifest_path.read_text())
    entries = [item for item in manifest["artifacts"] if item["source"] == SOURCE]
    if len(entries) != 1 or entries[0]["publication"] != PUBLICATION:
        raise ValueError("HQ controlled publication pair is absent or duplicated")
    verify_embedded_image(ROOT / PUBLICATION, art)
    entries[0]["source_assets"] = [{"path": ARTWORK, "sha256": digest}]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
