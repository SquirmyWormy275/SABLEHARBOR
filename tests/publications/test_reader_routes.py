"""Reader routes must reject broken evidence instead of silently resealing it."""

import importlib.util
import json
import shutil
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "reader_route_validator", ROOT / "tools/reader/validate_routes.py"
)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


@pytest.fixture
def route_copy(tmp_path):
    register = json.loads((ROOT / validator.REGISTER).read_text())
    paths = {validator.REGISTER, Path("docs/reader/exercises/README.md")}
    for route in register["routes"]:
        paths.add(Path(route["guide"]))
        paths.update(Path(item["path"]) for item in route["evidence"])
    guides = [ROOT / "docs/reader/exercises/README.md"] + [
        ROOT / route["guide"] for route in register["routes"]
    ]
    for guide in guides:
        for token in MarkdownIt().parse(guide.read_text()):
            for child in token.children or []:
                if child.type != "link_open":
                    continue
                url = urlsplit(child.attrGet("href") or "")
                if url.scheme or url.netloc or not url.path:
                    continue
                paths.add((guide.parent / unquote(url.path)).resolve().relative_to(ROOT))
    for path in paths:
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, destination)
    assert validator.validate(tmp_path) == []
    return tmp_path, register


def save(root, register):
    (root / validator.REGISTER).write_text(json.dumps(register))


def test_current_routes():
    assert validator.validate(ROOT) == []


def test_rejects_changed_evidence_bytes(route_copy):
    root, register = route_copy
    path = root / register["routes"][0]["evidence"][0]["path"]
    path.write_bytes(path.read_bytes() + b"\nChanged evidence.\n")
    assert any("hash mismatch" in error for error in validator.validate(root))


def test_rejects_wrong_workbook_sheet(route_copy):
    root, register = route_copy
    workbook = next(
        item for route in register["routes"] for item in route["evidence"] if "sheets" in item
    )
    workbook["sheets"][0] = "Made-up worksheet"
    save(root, register)
    assert any("workbook sheets differ" in error for error in validator.validate(root))


def test_rejects_missing_guide(route_copy):
    root, register = route_copy
    (root / register["routes"][0]["guide"]).unlink()
    assert any("missing guide" in error for error in validator.validate(root))


def test_rejects_inconsistent_steps(route_copy):
    root, register = route_copy
    register["routes"][0]["steps"][0] = "A different task."
    save(root, register)
    assert any("steps differ" in error for error in validator.validate(root))


def test_rejects_duplicate_stable_id(route_copy):
    root, register = route_copy
    register["routes"][1]["id"] = register["routes"][0]["id"]
    save(root, register)
    assert any("three stable IDs" in error for error in validator.validate(root))


def test_rejects_broken_guide_link(route_copy):
    root, register = route_copy
    guide = root / register["routes"][0]["guide"]
    guide.write_text(guide.read_text() + "\n[Missing evidence](missing.csv)\n")
    assert any("broken local link" in error for error in validator.validate(root))
