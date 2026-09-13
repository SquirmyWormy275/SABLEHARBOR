"""Exercise accounting boundaries, selection and deterministic derivatives."""

import copy
import importlib.util
import json
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
