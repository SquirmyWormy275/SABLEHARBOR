"""Real reader routes fail on broken links and misleading workbook promises."""

import json
import shutil
from pathlib import Path

import pytest

from tools.reader.usability import HERE, ROOT, inspect


@pytest.fixture
def corpus(tmp_path):
    spec = json.loads((ROOT / HERE / "tasks.json").read_text())
    paths = {HERE / "tasks.json"}
    paths.update(Path(p) for task in spec["tasks"] for p in task["route"])
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, target)
    return tmp_path


def test_current_routes():
    assert len(inspect()["tasks"]) == 6


def test_missing_visible_link(corpus):
    (corpus / "README.md").write_text("# Empty entry page\n")
    with pytest.raises(AssertionError, match="Missing reader link"):
        inspect(corpus)


def test_incorrect_sheet_promise(corpus):
    path = corpus / HERE / "tasks.json"
    spec = json.loads(path.read_text())
    spec["tasks"][1]["expected_sheets"].append("Bank confirmation")
    path.write_text(json.dumps(spec))
    with pytest.raises(AssertionError, match="Promised workbook sheets"):
        inspect(corpus)


def test_missing_evidence(corpus):
    (corpus / "industrial/publications/SH-IND-ARU-CLOSE-001_v1.0.0.pdf").unlink()
    with pytest.raises(AssertionError):
        inspect(corpus)
