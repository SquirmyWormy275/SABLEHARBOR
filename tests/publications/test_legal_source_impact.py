"""Mutation tests for bounded, read-only source impact reporting."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "source_impact", ROOT / "tools/legal_gaps/source_impact.py"
)
impact = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(impact)


def graph():
    return {
        "baseline_revision": "test",
        "baseline_problems": [],
        "uncovered_scope": ["Bounded test"],
        "nodes": [
            {"id": "source.json", "path": "source.json", "kind": "file", "sha256": "old"},
            {"id": "book.xlsx", "path": "book.xlsx", "kind": "file", "sha256": "book"},
            {"id": "case", "kind": "calculation"},
            {"id": "release", "kind": "retained_release", "action": "REVIEW_SUCCESSOR"},
        ],
        "edges": [
            {"source": "source.json", "target": "case", "basis": "register/selector"},
            {"source": "case", "target": "book.xlsx", "basis": "register/calculation"},
            {"source": "book.xlsx", "target": "release", "basis": "manifest/original_files"},
        ],
    }


def test_unchanged_is_only_bounded_clean():
    r = impact.analyze(graph(), {"source.json": "old", "book.xlsx": "book"})
    assert r["status"] == "NO_CHANGE_IN_BOUNDED_GRAPH"
    assert r["uncovered_scope"] and not r["impacted"]


def test_changed_source_propagates_transitively_to_retained_release():
    r = impact.analyze(graph(), {"source.json": "new", "book.xlsx": "book"})
    assert {i["node"]["id"] for i in r["impacted"]} == {"case", "book.xlsx", "release"}
    assert all(i["changed_inputs"] == ["source.json"] for i in r["impacted"])
    assert all(i["dependency_edges"][0]["basis"] for i in r["impacted"])


def test_deleted_source_still_invalidates_dependents():
    r = impact.analyze(graph(), {"book.xlsx": "book"})
    assert r["changes"][0]["change"] == "MISSING"
    assert len(r["impacted"]) == 3


def test_added_formerly_missing_input_requires_review():
    g = graph()
    g["nodes"][0]["sha256"] = None
    r = impact.analyze(g, {"source.json": "new", "book.xlsx": "book"})
    assert r["changes"][0]["change"] == "ADDED"


def test_outside_graph_not_silently_clean():
    r = impact.analyze(graph(), {"source.json": "old", "book.xlsx": "book"}, ["unknown.json"])
    assert r["status"] == "REVIEW_REQUIRED"
    assert r["unclassified_changes"] == ["unknown.json"]


def test_dependency_cycle_rejected():
    g = graph()
    g["edges"].append({"source": "release", "target": "source.json", "basis": "bad"})
    with pytest.raises(ValueError, match="cycle"):
        impact.analyze(g, {})


def test_unknown_manifest_endpoint_rejected():
    g = graph()
    g["nodes"] = g["nodes"][1:]
    with pytest.raises(ValueError, match="Unknown edge"):
        impact.analyze(g, {})


def test_duplicate_node_rejected():
    g = graph()
    g["nodes"].append(copy.deepcopy(g["nodes"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        impact.analyze(g, {})


def test_report_does_not_mutate_source_and_retains_sqlite(tmp_path):
    source = tmp_path / "source.json"
    source.write_text("original bytes")
    result = impact.analyze(graph(), {"source.json": "changed", "book.xlsx": "book"})
    impact.write_report(result, tmp_path / "report")
    assert source.read_text() == "original bytes"
    assert (tmp_path / "report/report.sqlite3").is_file()
    assert json.loads((tmp_path / "report/report.json").read_text()) == result
    with pytest.raises(FileExistsError):
        impact.write_report(result, tmp_path / "report")


def test_real_graph_rebuild_matches_persisted_baseline():
    saved = json.loads((impact.DEST / "graph.json").read_text())
    assert impact.build_graph(revision=saved["baseline_revision"]) == saved
    assert saved["baseline_problems"] == []


def test_real_invoice_change_reaches_billing_practice_accounting_and_release():
    saved = json.loads((impact.DEST / "graph.json").read_text())
    hashes = {n["path"]: n["sha256"] for n in saved["nodes"] if n["kind"] == "file"}
    hashes["docs/finance/evidence/SH-FIN-HUMAN-001/source.json"] = "mutation"
    result = impact.analyze(saved, hashes)
    ids = {i["node"]["id"] for i in result["impacted"]}
    for path in [
        "editions/billing.pdf",
        "accounting/links.xlsx",
        "practice/revenue-dispute/worked.xlsx",
        "walkthroughs/walkthroughs.xlsx",
    ]:
        assert impact.PREFIX + "/" + path in ids
    assert any(i.startswith("release:") for i in ids)
    assert any("#calculation/" in i for i in ids)


def test_changed_register_is_itself_an_input_even_if_it_removes_entries():
    saved = json.loads((impact.DEST / "graph.json").read_text())
    hashes = {n["path"]: n["sha256"] for n in saved["nodes"] if n["kind"] == "file"}
    hashes[impact.PREFIX + "/manifest.json"] = impact.digest(b'{"packages": []}')
    result = impact.analyze(saved, hashes)
    ids = {i["node"]["id"] for i in result["impacted"]}
    assert impact.PREFIX + "/editions/billing.pdf" in ids
    assert result["status"] == "REVIEW_REQUIRED"


def test_integrated_period_source_reaches_close_tracker_and_briefs():
    saved = json.loads((impact.DEST / "graph.json").read_text())
    path = impact.PREFIX + "/period-close/source/journal.csv"
    hashes = {n["path"]: n["sha256"] for n in saved["nodes"] if n["kind"] == "file"}
    assert path in hashes, "Integrated baseline must include period close"
    hashes[path] = "changed journal"
    result = impact.analyze(saved, hashes)
    ids = {i["node"]["id"] for i in result["impacted"]}
    for target in ["period-close/worked.xlsx", "evidence-tracking/tracker.xlsx"]:
        assert impact.PREFIX + "/" + target in ids
    assert any("/case-briefs/" in i and i.endswith(".pdf") for i in ids)
    assert any(i["node"]["kind"] == "calculation" for i in result["impacted"])


def test_brief_generator_change_requires_exact_pdf_review():
    saved = json.loads((impact.DEST / "graph.json").read_text())
    hashes = {n["path"]: n["sha256"] for n in saved["nodes"] if n["kind"] == "file"}
    path = "tools/legal_gaps/case_briefs.py"
    assert path in hashes
    hashes[path] = "changed layout"
    result = impact.analyze(saved, hashes)
    assert any(i["node"]["id"].endswith(".pdf") for i in result["impacted"])


def test_deleted_tracking_register_still_reaches_workbook():
    saved = json.loads((impact.DEST / "graph.json").read_text())
    hashes = {n["path"]: n["sha256"] for n in saved["nodes"] if n["kind"] == "file"}
    del hashes[impact.PREFIX + "/evidence-tracking/tracker.json"]
    result = impact.analyze(saved, hashes)
    assert any(i["node"]["id"].endswith("/tracker.xlsx") for i in result["impacted"])
    assert result["status"] == "REVIEW_REQUIRED"
