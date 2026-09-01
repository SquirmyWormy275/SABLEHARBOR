#!/usr/bin/env python3
"""Regenerate chart artifacts without overwriting curated navigation indexes.

`build_organization_charts.py` contains the deterministic chart/page renderer and
an older root-README updater. The enterprise information architecture now keeps
root and organization README files curated. This wrapper regenerates every
chart, chart page, and the machine-readable register, then restores the curated
organization index before CI compares generated artifacts with Git.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import build_organization_charts as charts


def main() -> None:
    organization_index = charts.ORG / "README.md"
    preserved_index = organization_index.read_text(encoding="utf-8")

    charts.build_enterprise()
    charts.build_leadership()
    charts.build_foundry()
    charts.build_willow()
    charts.build_atlas()
    charts.build_pale_sun()
    charts.build_cradle()
    charts.build_aru()
    charts.build_original_eight()
    charts.write_pages()
    charts.write_register()

    # `write_pages` also emits the legacy generated index. The index is now a
    # curated navigation layer and must not be owned by the chart renderer.
    organization_index.write_text(preserved_index, encoding="utf-8")

    rendered = sorted(charts.ASSETS.glob("*.svg"))
    for svg in rendered:
        ET.parse(svg)
    print(
        f"Rendered {len(rendered)} organization charts and preserved curated "
        "README navigation"
    )


if __name__ == "__main__":
    main()
