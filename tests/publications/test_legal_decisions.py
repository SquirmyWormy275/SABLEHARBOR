"""Navigation must preserve exact questions and must not smuggle in decisions."""

import importlib.util
import shutil
from pathlib import Path

import pytest
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "legal_decisions", ROOT / "tools/legal_gaps/decisions.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_every_source_field_has_one_navigation_record():
    rows = m.records()
    assert len(rows) == 125
    assert len({r["id"] for r in rows}) == 125
    assert len({r["package"] for r in rows}) == 17
    assert len({r["group"] for r in rows}) == 8
    assert {r["status"] for r in rows} == {"PENDING_REVIEW_NOT_ACCEPTED"}


@pytest.mark.parametrize("mutation", ["question", "response", "link"])
def test_workbook_mutation_is_rejected(tmp_path, monkeypatch, mutation):
    for name in ("organization.json", "decisions.json", "decisions.xlsx", "review.sqlite3"):
        shutil.copyfile(m.OUT / name, tmp_path / name)
    monkeypatch.setattr(m, "OUT", tmp_path)
    wb = load_workbook(tmp_path / "decisions.xlsx")
    if mutation == "question":
        wb["Review"]["C2"] = "Different proposed obligation"
    elif mutation == "response":
        wb["Review"]["E2"] = "Accepted"
    else:
        wb["Review"]["D2"].hyperlink = "../wrong.md"
    wb.save(tmp_path / "decisions.xlsx")
    with pytest.raises(AssertionError):
        m.validate()


def test_rebuild_bytes_are_deterministic(tmp_path, monkeypatch):
    shutil.copyfile(m.OUT / "organization.json", tmp_path / "organization.json")
    monkeypatch.setattr(m, "OUT", tmp_path)
    m.build()
    before = (tmp_path / "decisions.xlsx").read_bytes()
    m.build()
    assert (tmp_path / "decisions.xlsx").read_bytes() == before
