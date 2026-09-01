#!/usr/bin/env python3
"""Validate Sable Harbor's canon-derived rendered organization-map package."""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ORG_DIR = ROOT / "docs" / "organization"
REGISTER_PATH = ORG_DIR / "ORGANIZATION_MAP_REGISTER.json"
DECISION_REGISTER_PATH = ROOT / "docs" / "canon" / "DECISION_REGISTER.md"

REQUIRED_PAGE_METADATA = (
    "**Chart ID:**",
    "**Canonical date:**",
    "**Status:**",
    "**Purpose:**",
)
REQUIRED_INTERPRETATION_PHRASES = (
    "does **not** invent final legal entities",
    "person-to-person reporting lines",
)


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot parse {path.relative_to(ROOT)}: {exc}")
        return {}


def main() -> int:
    errors: list[str] = []
    if not REGISTER_PATH.exists():
        errors.append(f"missing register: {REGISTER_PATH.relative_to(ROOT)}")
        register: dict[str, Any] = {}
    else:
        register = load_json(REGISTER_PATH, errors)

    if not DECISION_REGISTER_PATH.exists():
        errors.append(f"missing decision register: {DECISION_REGISTER_PATH.relative_to(ROOT)}")

    canonical_date = register.get("canonicalDate")
    if canonical_date != "2026-08-31":
        errors.append("register canonicalDate must be 2026-08-31")

    charts = register.get("charts", []) if isinstance(register, dict) else []
    if not isinstance(charts, list) or not charts:
        errors.append("organization register must contain a nonempty charts list")
        charts = []

    seen_ids: set[str] = set()
    seen_pages: set[str] = set()
    seen_assets: set[str] = set()

    for chart in charts:
        if not isinstance(chart, dict):
            errors.append(f"chart entry must be an object: {chart!r}")
            continue
        chart_id = chart.get("id")
        page_relative = chart.get("page")
        asset_relative = chart.get("asset")
        if not chart_id or not page_relative or not asset_relative:
            errors.append(f"chart entry missing id, page, or asset: {chart!r}")
            continue

        if chart_id in seen_ids:
            errors.append(f"duplicate chart id: {chart_id}")
        if page_relative in seen_pages:
            errors.append(f"duplicate chart page: {page_relative}")
        if asset_relative in seen_assets:
            errors.append(f"duplicate chart asset: {asset_relative}")
        seen_ids.add(str(chart_id))
        seen_pages.add(str(page_relative))
        seen_assets.add(str(asset_relative))

        if chart.get("canonicalDate") != canonical_date:
            errors.append(f"{chart_id}: canonical date differs from register")
        if not str(chart.get("purpose", "")).strip():
            errors.append(f"{chart_id}: missing purpose")
        if not str(chart.get("relationshipSemantics", "")).strip():
            errors.append(f"{chart_id}: missing relationship semantics")

        page_path = ROOT / str(page_relative)
        asset_path = ROOT / str(asset_relative)
        if not page_path.exists():
            errors.append(f"{chart_id}: missing page {page_relative}")
        else:
            page_text = page_path.read_text(encoding="utf-8")
            if f"`{chart_id}`" not in page_text:
                errors.append(f"{chart_id}: page does not declare matching Chart ID")
            for marker in REQUIRED_PAGE_METADATA:
                if marker not in page_text:
                    errors.append(f"{chart_id}: page missing metadata marker {marker}")
            for phrase in REQUIRED_INTERPRETATION_PHRASES:
                if phrase not in page_text:
                    errors.append(f"{chart_id}: page missing interpretation guardrail {phrase!r}")
            if Path(str(asset_relative)).name not in page_text:
                errors.append(f"{chart_id}: page does not embed registered SVG asset")
            for required_source in (
                "SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md",
                "DECISION_REGISTER.md",
                "CHART_GOVERNANCE.md",
            ):
                if required_source not in page_text:
                    errors.append(f"{chart_id}: page missing controlling-source link {required_source}")

        if not asset_path.exists():
            errors.append(f"{chart_id}: missing SVG asset {asset_relative}")
        else:
            try:
                root = ET.parse(asset_path).getroot()
            except Exception as exc:  # pragma: no cover - diagnostic path
                errors.append(f"{chart_id}: malformed SVG {asset_relative}: {exc}")
            else:
                if root.tag.split("}")[-1] != "svg":
                    errors.append(f"{chart_id}: registered asset is not an SVG root")
                title = root.find("{http://www.w3.org/2000/svg}title")
                description = root.find("{http://www.w3.org/2000/svg}desc")
                if title is None or not (title.text or "").strip():
                    errors.append(f"{chart_id}: SVG missing accessible title")
                if description is None or not (description.text or "").strip():
                    errors.append(f"{chart_id}: SVG missing accessible description")
                if root.get("role") != "img":
                    errors.append(f"{chart_id}: SVG role must be img")
                if not root.get("aria-labelledby"):
                    errors.append(f"{chart_id}: SVG missing aria-labelledby")
                svg_text = asset_path.read_text(encoding="utf-8")
                if "NOT AN HR REPORTING TREE" not in svg_text:
                    errors.append(f"{chart_id}: SVG missing reporting-tree disclaimer")

    expected_ids = {f"SH-ORG-{number:03d}" for number in range(1, len(charts) + 1)}
    if seen_ids != expected_ids:
        missing = sorted(expected_ids - seen_ids)
        extra = sorted(seen_ids - expected_ids)
        if missing:
            errors.append(f"register missing contiguous chart IDs: {', '.join(missing)}")
        if extra:
            errors.append(f"register has unexpected chart IDs: {', '.join(extra)}")

    readme_path = ORG_DIR / "README.md"
    if not readme_path.exists():
        errors.append("missing docs/organization/README.md")
    else:
        readme_text = readme_path.read_text(encoding="utf-8")
        for page_relative in seen_pages:
            filename = Path(page_relative).name
            if filename not in readme_text:
                errors.append(f"organization README does not link {filename}")

    for artifact in register.get("supportingArtifacts", []):
        relative = artifact.get("path") if isinstance(artifact, dict) else artifact
        if not relative:
            errors.append(f"supporting artifact entry missing path: {artifact!r}")
            continue
        if not (ROOT / str(relative)).exists():
            errors.append(f"missing supporting artifact: {relative}")

    if errors:
        print("Organization-map validation FAILED:", file=sys.stderr)
        for error in sorted(set(errors)):
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        f"Organization-map validation passed: {len(charts)} registered pages and SVG assets; "
        "metadata, accessibility, source links, and non-HR guardrails verified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
