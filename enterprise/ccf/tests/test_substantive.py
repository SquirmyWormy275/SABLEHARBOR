"""Source comparisons must retain their limits, exact populations and reviewed versions."""

from pathlib import Path
from zipfile import ZipFile

import pytest
import yaml

from enterprise.ccf.assurance import substantive as review
from enterprise.ccf.registry import compile_registry


@pytest.fixture(scope="module")
def native():
    return compile_registry()


@pytest.fixture
def sources(tmp_path):
    # Public synthetic content exercises source navigation only, not normative interpretation.
    specs = review.read_json(review.DATA / "addressable_specifications.json")
    sections = {}
    for row in specs:
        sections.setdefault(row["requirement_id"].split(":")[1], []).append(row)
    xml = (
        "<ROOT>"
        + "".join(
            f'<DIV TYPE="SECTION" N="{sid}">'
            + "".join(
                "<P>" + row["source_label"] + " (Addressable). Synthetic safeguard.</P>"
                for row in rows
            )
            + "</DIV>"
            for sid, rows in sections.items()
        )
        + "</ROOT>"
    )
    (tmp_path / review.HIPAA_HASH).write_text(xml)
    inventory = review.read_json(
        Path(review.__file__).with_name("reference_data") / "c5_inventory.json"
    )
    groups = {}
    parents = {
        pid: dict(
            identifier=pid.split("-")[1],
            basic=[],
            additional_sharpen=[],
            additional_complement=[],
            information=[],
            corresponding=None,
        )
        for pid in inventory["parents"]
    }
    for cid, info in inventory["children"].items():
        pid, child = cid.split(".")
        parents[pid][info["kind"]].append(
            dict(
                identifier=child,
                criterion="If a synthetic capability exists:\\n1. Synthetic first duty.\\n2. Synthetic second duty.",
            )
        )
    first = parents["AM-01"]
    first["information"] = [
        dict(
            applicable_criteria=[first["basic"][0]["identifier"]],
            information_text="Synthetic parent guidance.",
        )
    ]
    first["corresponding"] = "Synthetic customer responsibility."
    for pid, parent in parents.items():
        groups.setdefault(pid.split("-")[0], []).append(parent)
    with ZipFile(tmp_path / review.C5_HASH, "w") as z:
        for domain, rows in groups.items():
            z.writestr(domain + ".yml", yaml.safe_dump(rows))
    return tmp_path


def test_all_source_children_preserve_context_and_kind(sources):
    result = review.source_details(sources)
    assert len(result["addressable_specifications"]) == 22
    assert len(result["c5_children"]) == 623 and len(result["c5_parents"]) == 168
    child = next(r for r in result["c5_children"] if r["requirement_id"] == "C5:AM-01.01B")
    assert child["information_ids"] == ["AM-01:INFO:1"]
    assert child["customer_corresponding_present"]
    assert len(child["source_units"]) == 3 and child["source_units"][0]["lexical_conditional"]
    assert {r["kind"] for r in result["c5_children"]} == {
        "basic",
        "additional_sharpen",
        "additional_complement",
    }
    assert all(r["review"] is None for r in result["addressable_specifications"])


def test_dropped_or_substituted_addressable_entry_is_rejected(sources, monkeypatch):
    original = review.read_json

    def changed(path):
        rows = original(path)
        if path == review.DATA / "addressable_specifications.json":
            rows[-1] = dict(rows[0], locator="164.312(fake)")
        return rows

    monkeypatch.setattr(review, "read_json", changed)
    with pytest.raises(ValueError, match="Duplicate addressable source"):
        review.source_details(sources)


def test_changed_analysis_cannot_silently_rebind(native, sources, monkeypatch):
    monkeypatch.setattr(review, "validate_source_inventory", lambda *args: None)
    original = review.read_json

    def changed(path):
        rows = original(path)
        if path == review.DATA / "findings.json":
            rows[0]["duties"] = ["Changed duty requiring fresh author consideration"]
        return rows

    monkeypatch.setattr(review, "read_json", changed)
    with pytest.raises(ValueError, match="stale"):
        review.analysis(native, sources)


def test_unknown_finding_route_is_rejected(native, monkeypatch):
    original = review.read_json

    def changed(path):
        rows = original(path)
        if path == review.DATA / "findings.json":
            rows[0]["requirement_ids"] = ["HIPAA:invented"]
        return rows

    monkeypatch.setattr(review, "read_json", changed)
    with pytest.raises(ValueError, match="Unknown finding"):
        review.finding_bindings(native)


def test_depth_is_not_accepted_coverage(native, sources, monkeypatch):
    monkeypatch.setattr(review, "validate_source_inventory", lambda *args: None)
    result = review.analysis(native, sources)
    assert result["summary"]["findings"] == 50
    assert result["summary"]["requirements"] == 970
    assert result["summary"]["independent_acceptances"] == 0
    assert all(r["review"] is None for r in result["findings"] + result["requirement_review"])
    assert any(
        r["review_depth"] == "PRIOR_SECTION_ANALYSIS_ONLY" for r in result["requirement_review"]
    )
    domain = next(r for r in result["requirement_review"] if r["requirement_id"] == "C5:AM-02.01B")
    assert domain["review_depth"] == "DOMAIN_CONDITION_COMPARISON"
    assert domain["conclusion"] == "NO_COVERAGE_CONCLUSION"
    assert "SH-CFG-001" in domain["proposed_domain_control_ids"]


def test_bundle_reperformance_rejects_resealed_edit(tmp_path, native, sources, monkeypatch):
    monkeypatch.setattr(review, "validate_source_inventory", lambda *args: None)

    # Nested draft bundle is outside this test's scope; its own tests reperform it separately.
    def nested(path, *args):
        path.mkdir()
        (path / "fixture.txt").write_text("Synthetic nested library")

    monkeypatch.setattr(review, "build_completion", nested)
    root = tmp_path / "delivery"
    review.build_review(root, native, sources)
    assert review.verify_review(root, native, sources) == {"verified": True}
    f = root / "FINDINGS.md"
    f.write_text(f.read_text() + "Invented acceptance\n")
    m = review.read_json(root / "REVIEW_MANIFEST.json")
    m["files"] = review.members(root)
    review.write_json(root / "REVIEW_MANIFEST.json", m)
    with pytest.raises(ValueError, match="re-performance"):
        review.verify_review(root, native, sources)
