"""Offline delivery must reject missing, extra and altered evidence."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "tools/legal_gaps/package.py"
SPEC = importlib.util.spec_from_file_location("legal_package", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def fixture_package(folder):
    data = b"original evidence"
    (folder / "evidence.md").write_bytes(data)
    rows = [{"path": "evidence.md", "sha256": module.digest(data), "bytes": len(data)}]
    manifest = {"files": rows}
    (folder / "MANIFEST.json").write_text(json.dumps(manifest))
    (folder / "SHA256SUMS.txt").write_text(
        module.digest(data)
        + "  evidence.md\n"
        + module.digest((folder / "MANIFEST.json").read_bytes())
        + "  MANIFEST.json\n"
    )


@pytest.mark.parametrize("mutation", ["alter", "delete", "extra", "checksums"])
def test_package_mutations_rejected(tmp_path, mutation):
    fixture_package(tmp_path)
    module.verify(tmp_path)
    if mutation == "alter":
        (tmp_path / "evidence.md").write_text("changed evidence")
    elif mutation == "delete":
        (tmp_path / "evidence.md").unlink()
    elif mutation == "extra":
        (tmp_path / "unmanifested.md").write_text("extra")
    else:
        (tmp_path / "SHA256SUMS.txt").write_text("forged inventory")
    with pytest.raises(AssertionError):
        module.verify(tmp_path)


def test_missing_html_anchor_rejected(tmp_path):
    data = b'<html><a href="#missing">clause</a></html>'
    (tmp_path / "index.html").write_bytes(data)
    rows = [{"path": "index.html", "sha256": module.digest(data), "bytes": len(data)}]
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"files": rows}))
    (tmp_path / "SHA256SUMS.txt").write_text(
        module.digest(data)
        + "  index.html\n"
        + module.digest((tmp_path / "MANIFEST.json").read_bytes())
        + "  MANIFEST.json\n"
    )
    with pytest.raises(AssertionError, match="Missing anchor"):
        module.verify(tmp_path)


def test_seed_symlink_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    folder = tmp_path / module.PREFIX
    folder.mkdir(parents=True)
    outside = tmp_path / "unselected.md"
    outside.write_text("not a selected instrument")
    (folder / "redirect.md").symlink_to(outside)
    with pytest.raises(ValueError, match="Symlink"):
        module.collect()
