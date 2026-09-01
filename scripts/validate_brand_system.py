#!/usr/bin/env python3
"""Validate the production logo manifest and recovered collateral package."""

from __future__ import annotations

import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGOS = ROOT / "assets/brand/logos"
MANIFEST_PATH = ROOT / "assets/brand/manifest.json"

CURRENT_UNITS = (
    "foundry-field",
    "willow",
    "atlas-meridian",
    "pale-sun",
    "project-cradle",
    "american-resource-utility",
    "advisory",
)


def main() -> int:
    errors: list[str] = []
    svg_files = sorted(LOGOS.glob("*.svg"))
    png_files = sorted(LOGOS.glob("*.png"))
    svg_stems = {path.stem for path in svg_files}
    png_stems = {path.stem for path in png_files}

    if svg_stems != png_stems:
        errors.append(f"SVG/PNG stem mismatch: {sorted(svg_stems ^ png_stems)}")

    for path in svg_files:
        try:
            root = ET.parse(path).getroot()
        except Exception as exc:  # noqa: BLE001 - report malformed publication input
            errors.append(f"{path.relative_to(ROOT)}: malformed SVG: {exc}")
            continue
        tags = [element.tag.split("}")[-1] for element in root.iter()]
        for forbidden in ("text", "script", "image"):
            if forbidden in tags:
                errors.append(
                    f"{path.relative_to(ROOT)}: forbidden <{forbidden}> in production logo"
                )
        if tags.count("svg") != 1:
            errors.append(f"{path.relative_to(ROOT)}: expected exactly one SVG root")
        title = root.find("{http://www.w3.org/2000/svg}title")
        if title is None or not (title.text or "").strip():
            errors.append(f"{path.relative_to(ROOT)}: missing/nontextual title")

    for path in LOGOS.iterdir():
        lowered = path.name.lower()
        if any(token in lowered for token in ("board", "contact-sheet", "mockup", "concept")):
            errors.append(
                f"{path.relative_to(ROOT)}: production directory contains board/mockup filename"
            )

    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        errors.append(f"cannot load production manifest: {exc}")
        manifest = {}

    records = manifest.get("assets")
    if records is None:
        records = manifest.get("files")
    if not isinstance(records, list):
        errors.append("manifest must contain an assets array (or legacy files array)")
        records = []

    manifest_paths: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            errors.append(f"invalid manifest record: {record!r}")
            continue
        rel = record.get("path")
        expected_hash = record.get("sha256")
        if not rel or not expected_hash:
            errors.append(f"manifest record missing path/sha256: {record!r}")
            continue
        if rel in manifest_paths:
            errors.append(f"duplicate manifest path: {rel}")
        manifest_paths.add(rel)
        path = ROOT / rel
        if not path.exists():
            errors.append(f"manifest path missing: {rel}")
            continue
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            errors.append(f"manifest hash mismatch: {rel}")

    if manifest.get("asset_count") not in (None, len(records)):
        errors.append(
            f"manifest asset_count={manifest.get('asset_count')} does not equal {len(records)} records"
        )
    if manifest.get("one_logo_per_file") is not True:
        errors.append("manifest must declare one_logo_per_file=true")
    if set(manifest.get("formats", [])) != {"svg", "png"}:
        errors.append("manifest formats must be exactly svg and png")

    required = [
        "assets/brand/README.md",
        "assets/brand/BRAND_STANDARDS.md",
        "assets/brand/FONT_PROVENANCE.md",
        "assets/brand/VALIDATION.md",
        "assets/brand/collateral/README.md",
        "assets/brand/collateral/letterhead/sable-harbor-letterhead-us-letter.docx",
        "assets/brand/collateral/letterhead/sable-harbor-letterhead-a4.docx",
        "assets/brand/collateral/presentation/sable-harbor-presentation-template-16x9.pptx",
        "docs/business-lines/README.md",
        "docs/legal/PRELIMINARY_NAME_AND_MARK_SCREEN.md",
        "docs/wiki/Home.md",
    ]
    required.extend(
        f"assets/brand/collateral/letterhead/business-lines/{slug}-letterhead-us-letter.svg"
        for slug in CURRENT_UNITS
    )
    for rel in required:
        path = ROOT / rel
        if not path.exists() or path.stat().st_size == 0:
            errors.append(f"missing/empty: {rel}")

    if errors:
        print("Brand-system validation FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        f"Brand-system validation passed: {len(svg_stems)} lockups, "
        f"{len(svg_files)} SVG, {len(png_files)} PNG, {len(records)} manifest assets, "
        f"and {len(CURRENT_UNITS)} unit letterheads."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
