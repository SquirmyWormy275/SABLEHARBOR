from __future__ import annotations

import hashlib
import json
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
        "ARU/BS&T uranium custody remains OPEN_GATED",
        "October 17, 2025",
    ):
        assert required in narrative

    assert "ARU-010" not in narrative
    assert "ARU-016" not in narrative

    addendum = "DECISION_REGISTER_ADDENDUM_2026-09-05_RED_WASH_R2.md"
    assert addendum in pale_sun_wrapper
    assert addendum in aru_wrapper
    assert "RW-017" in pale_sun_wrapper and "RW-025" in pale_sun_wrapper
    assert "RW-017" in aru_wrapper and "RW-025" in aru_wrapper


def test_industrial_chart_authority_and_census_match_current_sources() -> None:
    sources = json.loads((ROOT / "industrial/source/entities.json").read_text())
    entities = {row["entity_id"]: row for row in sources["entities"]}
    finance = json.loads((ROOT / "industrial/source/finance.json").read_text())
    aru = (ORG / "assets/aru-bst-organization-2026.svg").read_text()
    ps = (ORG / "assets/pale-sun-red-wash-organization-2026.svg").read_text()
    assert sum(employee["fte"] for employee in finance["employees"]) == 131
    assert entities["ARU"]["selected_fte"] + entities["BST"]["selected_fte"] == 131
    assert entities["PS"]["selected_fte"] + entities["RWH"]["selected_fte"] == 140
    assert entities["ARU"]["owner_entity_id"] == "SHIH"
    assert entities["PS"]["owner_entity_id"] == "SHIH"
    assert entities["RWH"]["owner_entity_id"] == "PS"
    assert entities["BST"]["owner_entity_id"] == "ARU"
    for expected in ("Nora Ashcombe", "Seth Kettering", "131 FTE", "OPEN GATES / NO CUSTODY"):
        assert expected in aru
    for expected in ("EVAN VILANDER", "MARI VARELA", "Pale Sun Inc.", "Red Wash Mining, LLC"):
        assert expected in ps
    assert "Identity and exact title unresolved" not in aru
    assert "ARU OPERATING LEADER" not in aru


def test_historical_artwork_bytes_and_mixed_effective_dates_are_preserved() -> None:
    archive = json.loads((ORG / "history/v0.3.0/manifest.json").read_text())
    for artifact in archive["artifacts"]:
        assert _digest(ROOT / artifact["preserved_path"]) == artifact["sha256"]
    register = json.loads((ORG / "ORGANIZATION_MAP_REGISTER.json").read_text())
    dates = {chart["id"]: chart["canonicalDate"] for chart in register["charts"]}
    for chart_id in ("SH-ORG-001", "SH-ORG-002", "SH-ORG-006", "SH-ORG-008"):
        assert dates[chart_id] == "2026-09-05"
    assert dates["SH-ORG-004"] == "2026-08-31"
