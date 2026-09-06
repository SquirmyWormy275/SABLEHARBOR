from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORG = ROOT / "docs" / "organization"
BUILDER = ROOT / "scripts" / "build_organization_charts.py"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_organization_builder_is_idempotent_and_preserves_root_readme() -> None:
    generated = [
        *sorted(ORG.glob("*_ORGANIZATION.md")),
        ORG / "2026_LEADERSHIP_AND_AUTHORITY_MAP.md",
        ORG / "2026_OPERATING_TOPOLOGY.md",
        ORG / "ORGANIZATION_MAP_REGISTER.json",
        ORG / "ORIGINAL_EIGHT.md",
        ORG / "README.md",
        ORG / "WILLOW_ORGANIZATION.md",
        *sorted((ORG / "assets").glob("*.svg")),
    ]
    before = {path: _digest(path) for path in generated}
    root_readme_before = _digest(ROOT / "README.md")

    subprocess.run([sys.executable, str(BUILDER)], cwd=ROOT, check=True)

    assert {path: _digest(path) for path in generated} == before
    assert _digest(ROOT / "README.md") == root_readme_before


def test_red_wash_chart_preserves_workforce_and_transport_boundaries() -> None:
    svg = (ORG / "assets" / "pale-sun-red-wash-organization-2026.svg").read_text()
    narrative = (ORG / "PALE_SUN_AND_RED_WASH.md").read_text()
    pale_sun_wrapper = (ORG / "PALE_SUN_RED_WASH_ORGANIZATION.md").read_text()
    aru_wrapper = (ORG / "ARU_BST_ORGANIZATION.md").read_text()

    for required in (
        "12 FTE business layer",
        "128 FTE site",
        "QUALIFIED EXTERNAL CARRIERS",
        "All Red Wash transport throughout 2025",
        "OPEN GATES / NO CUSTODY",
    ):
        assert required in svg

    for required in (
        "no pre-existing commercial relationship",
        "$15 million preliminary screen is unbooked",
        "$28.0 million cash consideration",
        "RW-017`–`RW-025",
        "No exact route, terminal, fleet, workforce, management team",
    ):
        assert required in narrative

    assert "ARU-010" not in narrative
    assert "ARU-016" not in narrative

    addendum = "DECISION_REGISTER_ADDENDUM_2026-09-05_RED_WASH.md"
    assert addendum in pale_sun_wrapper
    assert addendum in aru_wrapper
    assert "RW-017" in pale_sun_wrapper and "RW-025" in pale_sun_wrapper
    assert "RW-017" in aru_wrapper and "RW-025" in aru_wrapper
