#!/usr/bin/env python3
"""Validate Sable Harbor's current canon-derived organization publication package.

The accepted package uses Markdown source pages plus rendered SVG assets. Older
validation logic expected Mermaid source and a legacy register schema; this
validator follows ORGANIZATION_MAP_REGISTER.json v0.2 instead.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORG_DIR = ROOT / "docs" / "organization"
REGISTER_PATH = ORG_DIR / "ORGANIZATION_MAP_REGISTER.json"
DECISION_REGISTER_PATH = ROOT / "docs" / "canon" / "DECISION_REGISTER.md"

DECISION_ID_RE = re.compile(r"\|\s*([A-Z]{2,8}-\d{3})\s*\|")
EXPECTED_CHART_IDS = {f"SH-ORG-{number:03d}" for number in range(1, 10)}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []

    try:
        register = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"missing register: {REGISTER_PATH.relative_to(ROOT)}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"cannot parse register: {exc}", file=sys.stderr)
        return 1

    decision_ids: set[str] = set()
    if DECISION_REGISTER_PATH.exists():
        decision_ids = set(
            DECISION_ID_RE.findall(DECISION_REGISTER_PATH.read_text(encoding="utf-8"))
        )
    else:
        fail(errors, f"missing decision register: {DECISION_REGISTER_PATH.relative_to(ROOT)}")

    if register.get("schemaVersion") != "0.2.0":
        fail(errors, "register schemaVersion must be 0.2.0")
    if register.get("canonicalDate") != "2026-08-31":
        fail(errors, "register canonicalDate must be 2026-08-31")

    for source in register.get("controllingSources", []):
        if not (ROOT / source).exists():
            fail(errors, f"missing controlling source: {source}")

    charts = register.get("charts", [])
    if not isinstance(charts, list):
        fail(errors, "register charts must be a list")
        charts = []

    seen_ids: set[str] = set()
    seen_pages: set[str] = set()
    seen_assets: set[str] = set()

    for chart in charts:
        if not isinstance(chart, dict):
            fail(errors, f"invalid chart entry: {chart!r}")
            continue

        chart_id = chart.get("id")
        page_rel = chart.get("page")
        asset_rel = chart.get("asset")
        title = chart.get("title")
        purpose = chart.get("purpose")

        if not all((chart_id, page_rel, asset_rel, title, purpose)):
            fail(errors, f"chart entry missing id/page/asset/title/purpose: {chart!r}")
            continue

        if chart_id in seen_ids:
            fail(errors, f"duplicate chart id: {chart_id}")
        if page_rel in seen_pages:
            fail(errors, f"duplicate chart page: {page_rel}")
        if asset_rel in seen_assets:
            fail(errors, f"duplicate chart asset: {asset_rel}")
        seen_ids.add(chart_id)
        seen_pages.add(page_rel)
        seen_assets.add(asset_rel)

        if chart.get("canonicalDate") != register.get("canonicalDate"):
            fail(errors, f"{chart_id}: canonicalDate differs from register")
        if not chart.get("relationshipSemantics"):
            fail(errors, f"{chart_id}: missing relationshipSemantics")

        page = ROOT / page_rel
        asset = ROOT / asset_rel
        if not page.exists():
            fail(errors, f"{chart_id}: missing page {page_rel}")
            continue
        if not asset.exists():
            fail(errors, f"{chart_id}: missing asset {asset_rel}")
            continue

        page_text = page.read_text(encoding="utf-8")
        if f"`{chart_id}`" not in page_text:
            fail(errors, f"{chart_id}: page does not declare matching chart ID")
        if "**Chart ID:**" not in page_text and "**Map ID:**" not in page_text:
            fail(errors, f"{chart_id}: page lacks Chart ID/Map ID metadata")
        if "**Canonical date:**" not in page_text:
            fail(errors, f"{chart_id}: page lacks canonical-date metadata")
        if Path(asset_rel).name not in page_text:
            fail(errors, f"{chart_id}: page does not link rendered asset")
        if "Controlling sources" not in page_text:
            fail(errors, f"{chart_id}: page lacks controlling-sources section")

        asset_text = asset.read_text(encoding="utf-8")
        lowered = asset_text.lower()
        if "<svg" not in lowered or "<title" not in lowered or "<desc" not in lowered:
            fail(errors, f"{chart_id}: SVG lacks svg/title/desc structure")
        if "<script" in lowered or "javascript:" in lowered:
            fail(errors, f"{chart_id}: SVG contains executable content")

        for decision_id in chart.get("sourceDecisionIds", []):
            if decision_ids and decision_id not in decision_ids:
                fail(errors, f"{chart_id}: unknown decision ID {decision_id}")

    if seen_ids != EXPECTED_CHART_IDS:
        missing = sorted(EXPECTED_CHART_IDS - seen_ids)
        extra = sorted(seen_ids - EXPECTED_CHART_IDS)
        if missing:
            fail(errors, f"register missing chart IDs: {', '.join(missing)}")
        if extra:
            fail(errors, f"register has unexpected chart IDs: {', '.join(extra)}")

    readme = ORG_DIR / "README.md"
    if not readme.exists():
        fail(errors, "missing docs/organization/README.md")
    else:
        readme_text = readme.read_text(encoding="utf-8")
        for page_rel in seen_pages:
            if Path(page_rel).name not in readme_text:
                fail(errors, f"organization README does not link {Path(page_rel).name}")
        for required in (
            "SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md",
            "DECISION_REGISTER.md",
            "CHART_GOVERNANCE.md",
            "build_organization_charts.py",
        ):
            if required not in readme_text:
                fail(errors, f"organization README does not link {required}")

    if errors:
        print("Organization-map validation FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        f"Organization-map validation passed: {len(charts)} rendered charts, "
        f"{len(decision_ids)} decision IDs available."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
