from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import fitz
import pytest

ROOT = Path(__file__).resolve().parents[2]
ORG = ROOT / "docs/organization"


def source():
    return json.loads((ORG / "source/chartbook.json").read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exporter():
    spec = importlib.util.spec_from_file_location(
        "export_charts", ROOT / "tools/organization/export_charts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_export_is_idempotent_and_preserves_master_history_and_readme():
    paths = [
        *sorted((ORG / "assets/current").iterdir()),
        *sorted((ORG / "charts").glob("*.md")),
        *sorted(p for p in (ORG / "history").rglob("*") if p.is_file()),
        ORG / "ORGANIZATION_MAP_REGISTER.json",
        ORG / "DISPLAY_INVENTORY.md",
        ORG / "UNRESOLVED_AND_EXCLUDED.md",
        ROOT / "README.md",
    ]
    before = {path: digest(path) for path in paths}
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_organization_charts.py")],
        cwd=ROOT,
        check=True,
    )
    assert {path: digest(path) for path in paths} == before


def test_complete_publication_validates():
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_organization_maps.py")],
        cwd=ROOT,
        check=True,
    )


def test_person_card_rejects_extra_prose_and_does_not_invent_year():
    module = exporter()
    data = source()
    nodes = {n["id"]: n for n in data["nodes"]}
    unknown = next(n for n in nodes.values() if n.get("person_id") and n["joined_year"] is None)
    assert module.display_fields(unknown)["joined_year"] == "Year not recorded"
    occurrence = next(
        p
        for c in data["charts"]
        for p in c["pages"]
        if any(card["node_id"] == unknown["id"] for card in p["cards"])
    )
    card = next(c for c in occurrence["cards"] if c["node_id"] == unknown["id"])
    pdf = fitz.open(ROOT / data["visual_master"])
    page = pdf[occurrence["page"] - 1]
    rect = fitz.Rect(card["bounds"])
    assert module.card_fields(page, rect, True) == module.display_fields(unknown)
    page.insert_text((rect.x0 + 20, rect.y1 - 10), "Unrequested biography", fontsize=9)
    with pytest.raises(ValueError, match="Extra card text"):
        module.card_fields(page, rect, True)


def test_company_coverage_logos_and_board_capacity():
    data = source()
    nodes = {n["id"]: n for n in data["nodes"]}
    charts = {c["slug"]: c for c in data["charts"]}
    assert len(data["charts"]) == 40
    assert sum(len(c["pages"]) for c in data["charts"]) == 57
    assert len(nodes) == 208
    people = [n for n in nodes.values() if n["type"] == "person"]
    assert len({n["person_id"] for n in people if n["status"].startswith("current_")}) == 51
    assert sum(n["joined_year"] is None for n in people if n["status"].startswith("current_")) == 18
    assert set(charts["business-lines"]["node_ids"]) == {
        "SHI",
        "foundry-field",
        "willow",
        "atlas-meridian",
        "PS",
        "project-cradle",
        "ARU",
        "advisory",
    }
    for node_id in charts["business-lines"]["node_ids"]:
        node = nodes[node_id]
        assert digest(ROOT / node["logo"]) == node["logo_sha256"]
    board = json.loads((ROOT / "docs/governance/structured/board_and_committees.json").read_text())
    assert len(charts["people-board"]["node_ids"]) == len(board["directors"]) + 1
    assert nodes["P001-BOARD"]["person_id"] == nodes["P001"]["person_id"]
    assert nodes["P001-BOARD"]["title"] != nodes["P001"]["title"]


def test_industrial_ownership_workforce_and_transport_boundaries_remain_canonical():
    entities = {
        n["entity_id"]: n
        for n in json.loads((ROOT / "industrial/source/entities.json").read_text())["entities"]
    }
    finance = json.loads((ROOT / "industrial/source/finance.json").read_text())
    chart = next(c for c in source()["charts"] if c["slug"] == "industrial-ownership")
    assert {(e["from"], e["to"]) for e in chart["edges"]} == {
        ("SHI", "SHIH"),
        ("SHIH", "PS"),
        ("PS", "RWH"),
        ("SHIH", "ARU"),
        ("ARU", "BST"),
    }
    for edge in chart["edges"]:
        assert entities[edge["to"]]["owner_entity_id"] == edge["from"]
    assert sum(e["fte"] for e in finance["employees"]) == 131
    assert entities["ARU"]["selected_fte"] + entities["BST"]["selected_fte"] == 131
    assert entities["PS"]["selected_fte"] + entities["RWH"]["selected_fte"] == 140
    narrative = (ORG / "PALE_SUN_AND_RED_WASH.md").read_text()
    for required in (
        "no pre-existing commercial relationship",
        "$15 million preliminary screen is unbooked",
        "$28.0 million cash consideration",
        "RW-017`–`RW-025",
        "ARU/BS&T uranium custody remains OPEN_GATED",
        "October 17, 2025",
    ):
        assert required in narrative


def test_retired_artwork_preserved_but_cannot_be_regenerated():
    for version in ("v0.3.0", "v0.4.0"):
        archive = json.loads((ORG / f"history/{version}/manifest.json").read_text())
        for artifact in archive["artifacts"]:
            assert digest(ROOT / artifact["preserved_path"]) == artifact["sha256"]
    before = {p: digest(p) for p in (ORG / "assets").rglob("*") if p.is_file()}
    for name in ("build_j2_charts.py", "postbuild_org_briefing.py"):
        subprocess.run([sys.executable, str(ROOT / "tools/organization" / name)], check=True)
    after = {p: digest(p) for p in (ORG / "assets").rglob("*") if p.is_file()}
    assert after == before
