#!/usr/bin/env python3
"""Validate Sable Harbor's canon-derived organization-map package.

The script uses only the Python standard library. It checks package structure,
chart metadata, register consistency, decision-ID references, and a small set
of high-risk visual shortcuts that would blur locked canonical distinctions.
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

REQUIRED_METADATA = (
    "**Map ID:**",
    "**Canonical date:**",
    "**Map type:**",
    "**Edge meaning:**",
)

FORBIDDEN_MERMAID_PHRASES = (
    "Foundry / Foundry Field",
    "Pale Sun / Red Wash",
    "ARU / BS&T",
    "reports to",
    "Chief Executive Officer",
    "Chief Technology Officer",
    "Chief Financial Officer",
)

MERMAID_RE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
DECISION_ID_RE = re.compile(r"\|\s*([A-Z]{2,8}-\d{3})\s*\|")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []

    if not REGISTER_PATH.exists():
        fail(errors, f"missing register: {REGISTER_PATH.relative_to(ROOT)}")
    else:
        try:
            register = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            fail(errors, f"cannot parse register: {exc}")
            register = {}

    decision_ids: set[str] = set()
    if DECISION_REGISTER_PATH.exists():
        decision_ids = set(
            DECISION_ID_RE.findall(DECISION_REGISTER_PATH.read_text(encoding="utf-8"))
        )
    else:
        fail(errors, f"missing decision register: {DECISION_REGISTER_PATH.relative_to(ROOT)}")

    charts = register.get("charts", []) if isinstance(register, dict) else []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()

    if register.get("canonicalDate") != "2026-08-31":
        fail(errors, "register canonicalDate must be 2026-08-31")

    for chart in charts:
        chart_id = chart.get("id")
        # v0.2 rendered-chart registers distinguish the narrative page from
        # its SVG asset; earlier registers used a single path field.
        rel_path = chart.get("path") or chart.get("page")

        if not chart_id or not rel_path:
            fail(errors, f"chart entry missing id or path: {chart!r}")
            continue

        if chart_id in seen_ids:
            fail(errors, f"duplicate chart id: {chart_id}")
        seen_ids.add(chart_id)

        if rel_path in seen_paths:
            fail(errors, f"duplicate chart path: {rel_path}")
        seen_paths.add(rel_path)

        path = ROOT / rel_path
        if not path.exists():
            fail(errors, f"{chart_id}: missing file {rel_path}")
            continue

        text = path.read_text(encoding="utf-8")

        # Current rendered-chart registers carry metadata in JSON and point to
        # both a narrative page and a separately generated SVG asset.
        if chart.get("page") and chart.get("asset"):
            asset = ROOT / chart["asset"]
            if not asset.exists():
                fail(errors, f"{chart_id}: missing asset {chart['asset']}")
            for field in ("title", "purpose", "canonicalDate", "relationshipSemantics"):
                if not chart.get(field):
                    fail(errors, f"{chart_id}: missing register field {field}")
            continue

        if f"`{chart_id}`" not in text:
            fail(errors, f"{chart_id}: file does not declare matching Map ID")

        for marker in REQUIRED_METADATA:
            if marker not in text:
                fail(errors, f"{chart_id}: missing metadata marker {marker}")

        blocks = MERMAID_RE.findall(text)
        if not blocks:
            fail(errors, f"{chart_id}: no Mermaid block found")

        for block_index, block in enumerate(blocks, start=1):
            for phrase in FORBIDDEN_MERMAID_PHRASES:
                if phrase.lower() in block.lower():
                    fail(
                        errors,
                        f"{chart_id} Mermaid block {block_index}: forbidden phrase {phrase!r}",
                    )

        for decision_id in chart.get("sourceDecisionIds", []):
            if decision_ids and decision_id not in decision_ids:
                fail(errors, f"{chart_id}: unknown decision ID {decision_id}")

    expected_chart_ids = {f"SH-ORG-{number:03d}" for number in range(1, 10)}
    if seen_ids != expected_chart_ids:
        missing = sorted(expected_chart_ids - seen_ids)
        extra = sorted(seen_ids - expected_chart_ids)
        if missing:
            fail(errors, f"register missing chart IDs: {', '.join(missing)}")
        if extra:
            fail(errors, f"register has unexpected chart IDs: {', '.join(extra)}")

    readme = ORG_DIR / "README.md"
    if readme.exists():
        readme_text = readme.read_text(encoding="utf-8")
        for rel_path in seen_paths:
            name = Path(rel_path).name
            if name not in readme_text:
                fail(errors, f"organization README does not link {name}")

        for artifact in register.get("supportingArtifacts", []):
            rel_path = artifact.get("path") if isinstance(artifact, dict) else artifact
            if not rel_path:
                fail(errors, f"supporting artifact entry missing path: {artifact!r}")
                continue
            path = ROOT / rel_path
            if not path.exists():
                fail(errors, f"missing supporting artifact: {rel_path}")
            if path != readme and Path(rel_path).name not in readme_text:
                fail(errors, f"organization README does not link supporting artifact {Path(rel_path).name}")
    else:
        fail(errors, "missing docs/organization/README.md")

    if errors:
        print("Organization-map validation FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        f"Organization-map validation passed: {len(charts)} charts, "
        f"{len(decision_ids)} decision IDs available."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
