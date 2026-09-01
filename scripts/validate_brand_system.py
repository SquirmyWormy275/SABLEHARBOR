#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOGOS = ROOT / "assets/brand/logos"
MANIFEST = ROOT / "assets/brand/manifest.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    errors: list[str] = []
    manifest = load_json(MANIFEST)
    legacy_path = ROOT / manifest["legacy_full_build_manifest"]
    legacy = load_json(legacy_path)

    svg_files = sorted(LOGOS.glob("*.svg"))
    png_files = sorted(LOGOS.glob("*.png"))
    svg_stems = {path.stem for path in svg_files}
    png_stems = {path.stem for path in png_files}

    if svg_stems != png_stems:
        errors.append(f"SVG/PNG stem mismatch: {sorted(svg_stems ^ png_stems)}")

    expected_stems = {
        f"{identity['slug']}__{variant}"
        for identity in manifest["identities"]
        for variant in identity["variants"]
    }
    if svg_stems != expected_stems:
        errors.append(
            "identity matrix mismatch: "
            f"missing={sorted(expected_stems - svg_stems)} "
            f"unexpected={sorted(svg_stems - expected_stems)}"
        )

    counts = manifest["counts"]
    if len(manifest["identities"]) != counts["identities"]:
        errors.append("manifest identity count is incorrect")
    if len(svg_files) != counts["svg_files"] or len(png_files) != counts["png_files"]:
        errors.append(
            f"logo count mismatch: svg={len(svg_files)} png={len(png_files)} expected={counts}"
        )

    for path in svg_files:
        try:
            root = ET.parse(path).getroot()
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(f"{path}: malformed SVG: {exc}")
            continue
        tags = [element.tag.split("}")[-1] for element in root.iter()]
        for forbidden in ("text", "script", "image"):
            if forbidden in tags:
                errors.append(f"{path}: forbidden <{forbidden}> in production logo")
        title = root.find("{http://www.w3.org/2000/svg}title")
        if title is None or not (title.text or "").strip():
            errors.append(f"{path}: missing accessible title")

    for path in LOGOS.iterdir():
        lowered = path.name.lower()
        if any(token in lowered for token in ("board", "contact-sheet", "mockup", "concept")):
            errors.append(f"{path}: forbidden board/mockup filename in production directory")

    # The legacy build manifest also recorded generated dossier/wiki files. Those
    # hashes are historical after the portal reorganization; only its immutable
    # brand-package records remain in the current validation scope.
    for record in legacy.get("files", []):
        relative = record["path"]
        if not relative.startswith("assets/brand/"):
            continue
        if relative == "assets/brand/manifest.json":
            continue
        path = ROOT / relative
        if not path.exists():
            errors.append(f"legacy brand-manifest path missing: {relative}")
            continue
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != record["sha256"]:
            errors.append(f"legacy brand-manifest hash mismatch: {relative}")

    required = [
        "assets/brand/README.md",
        "assets/brand/BRAND_STANDARDS.md",
        "assets/brand/FONT_PROVENANCE.md",
        "assets/brand/VALIDATION.md",
        "assets/brand/MANIFEST_SCOPE.md",
        "assets/brand/collateral/letterhead/sable-harbor-letterhead-us-letter.docx",
        "assets/brand/collateral/letterhead/sable-harbor-letterhead-a4.docx",
        "assets/brand/collateral/presentation/sable-harbor-presentation-template-16x9.pptx",
        "assets/brand/packages/README.md",
    ]
    for relative in required:
        path = ROOT / relative
        if not path.exists() or path.stat().st_size == 0:
            errors.append(f"missing or empty required brand artifact: {relative}")

    if errors:
        print("\n".join(errors))
        raise SystemExit(1)

    print(
        "PASS: "
        f"{len(manifest['identities'])} identities, {len(svg_files)} SVG, "
        f"{len(png_files)} PNG; current scope and legacy brand hashes verified."
    )


if __name__ == "__main__":
    main()
