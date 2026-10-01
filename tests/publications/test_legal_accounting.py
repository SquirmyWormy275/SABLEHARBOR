"""Exercise accounting boundaries, selection and deterministic derivatives."""

import copy
import importlib.util
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "legal_accounting", ROOT / "tools/legal_gaps/accounting.py"
)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def source():
    return json.loads((ROOT / a.HERE / "source.json").read_text())


def test_complete_native_reconciliation():
    result = a.validate(ROOT, source())
    assert len(result) == 23
    checks = a.reconciliations(ROOT)
    assert len(checks) == 15
    assert (
        next(c for c in checks if c["check"] == "FF economic claim bridge")["left"] == "971500.0000"
    )


@pytest.mark.parametrize(
    "mutation", ["gap", "hash", "heading", "posting", "population", "selector"]
)
def test_reject_broken_or_misleading_link(mutation):
    data = copy.deepcopy(source())
    link = data["links"][0]
    if mutation == "gap":
        data["coverage"].pop()
    elif mutation == "hash":
        data["sources"][link["source_path"]] = "0" * 64
    elif mutation == "heading":
        link["clause_heading"] = "Invented clause"
    elif mutation == "posting":
        link["new_posting_authorized"] = True
    elif mutation == "population":
        link["population"] = "ARU-2026-MODEL"
    elif mutation == "selector":
        link["selector"] = {"pointer": "/missing"}
    with pytest.raises((ValueError, KeyError)):
        a.validate(ROOT, data)


def test_deterministic_derivatives(tmp_path):
    one, two = tmp_path / "one", tmp_path / "two"
    a.build(output=one)
    a.build(output=two)
    for name in ("LINKS.md", "links.json", "links.xlsx", "links.sqlite3"):
        assert (one / name).read_bytes() == (two / name).read_bytes()


def test_no_entry_has_no_posting_value():
    links = a.validate(ROOT, source())
    for link in links:
        if link["evidence_kind"] == "NO_ENTRY":
            assert link["native_value"]["posting"] is None


@pytest.mark.parametrize("mutation", ["value", "schema", "missing_row", "user_version"])
def test_database_logical_mutations_rejected(tmp_path, mutation):
    original = ROOT / a.HERE / "links.sqlite3"
    changed = tmp_path / "changed.sqlite3"
    shutil.copyfile(original, changed)
    with sqlite3.connect(changed) as con:
        if mutation == "value":
            con.execute("UPDATE coverage SET disposition='INVENTED'")
        elif mutation == "schema":
            con.execute("CREATE INDEX unauthorized_index ON coverage(disposition)")
        elif mutation == "missing_row":
            con.execute("DELETE FROM reconciliation WHERE rowid=1")
        else:
            con.execute("PRAGMA user_version=1")
    with pytest.raises(ValueError, match="schema or contents"):
        a.compare_databases(original, changed)


def test_database_header_variation_permitted_without_rewriting(tmp_path):
    original = ROOT / a.HERE / "links.sqlite3"
    changed = tmp_path / "other_engine.sqlite3"
    raw = bytearray(original.read_bytes())
    # SQLite header bytes 96-99 identify the last writing library version.
    raw[96:100] = (3045000).to_bytes(4, "big")
    changed.write_bytes(raw)
    before = changed.read_bytes()
    a.compare_databases(original, changed)
    assert changed.read_bytes() == before


def test_database_corruption_rejected(tmp_path):
    bad = tmp_path / "corrupt.sqlite3"
    bad.write_bytes(b"not a SQLite database")
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        a.compare_databases(ROOT / a.HERE / "links.sqlite3", bad)
