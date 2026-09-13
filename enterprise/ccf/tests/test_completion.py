"""Draft coverage routing must not become unsupported assurance or conceal missing designs."""

import hashlib

import pytest

from enterprise.ccf.assurance import completion
from enterprise.ccf.registry import compile_registry


@pytest.fixture(scope="module")
def native():
    return compile_registry()


def test_every_selected_attribute_and_control_has_review_work(native):
    c, a = completion.iso_inputs(native, completion.TARGETS)
    p = completion.review_packet(native)
    selected = {x.requirement_id for x in a.applicability}
    expected = {(r.id, x.id) for r in c.requirements if r.id in selected for x in r.attributes}
    actual = [(r["requirement_id"], r["attribute_id"]) for r in p["coverage_workpapers"]]
    assert len(actual) == len(set(actual)) and set(actual) == expected
    assert {r["control_id"] for r in p["controls"]} == {i.control_id for i in a.implementations}
    assert len(p["controls"]) == 86
    assert all(r["review"] is None for r in p["controls"] + p["coverage_workpapers"])
    assert p["summary"]["accepted_coverage"] == 0
    assert all(
        d["applicability"] == "UNRESOLVED"
        for r in p["coverage_workpapers"]
        for d in r["boundary_decisions"]
    )


def test_missing_or_duplicate_extension_procedure_fails(native, monkeypatch):
    original = completion.read_json

    def changed(path):
        rows = original(path)
        if path == completion.DATA / "control_procedures.json":
            return rows[:-1]
        return rows

    monkeypatch.setattr(completion, "read_json", changed)
    with pytest.raises(ValueError, match="population"):
        completion.review_packet(native)

    def duplicated(path):
        rows = original(path)
        return rows + rows[:1] if path == completion.DATA / "control_procedures.json" else rows

    monkeypatch.setattr(completion, "read_json", duplicated)
    with pytest.raises(ValueError, match="Duplicate"):
        completion.review_packet(native)


def test_design_change_invalidates_linked_workpapers(native, monkeypatch):
    before = completion.review_packet(native)
    original = completion.read_json

    def changed(path):
        rows = original(path)
        if path == completion.DATA / "control_procedures.json":
            rows[0]["procedure"] += " Revised local design."
        return rows

    monkeypatch.setattr(completion, "read_json", changed)
    after = completion.review_packet(native)
    cid = original(completion.DATA / "control_procedures.json")[0]["control_id"]
    linked = [
        (a, b)
        for a, b in zip(before["coverage_workpapers"], after["coverage_workpapers"])
        if cid in a["candidate_control_ids"]
    ]
    assert linked
    assert all(
        a["candidate_design_digests"][cid] != b["candidate_design_digests"][cid] for a, b in linked
    )
    assert all(b["review"] is None for a, b in linked)


def test_assessment_work_is_not_counted_as_a_missing_control(native):
    p = completion.review_packet(native)
    context = next(
        r
        for r in p["coverage_workpapers"]
        if r["workpaper_id"] == "ISO42001:A.6.2.4:IMPLEMENTATION_GUIDANCE"
    )
    assert context["attribute_kind"] == "ASSESSMENT"
    assert context["routing"] == "NO_CONTROL_ROUTE_REVIEW_REQUIRED"
    assert not context["candidate_control_ids"]
    masking = next(
        r for r in p["coverage_workpapers"] if r["workpaper_id"] == "ISO27001:A.8.11:OBJECTIVE"
    )
    assert masking["proposed_measure_ids"] == ["MASKING"]
    assert masking["reviewer_decision"] == "PENDING"


def test_reperformance_rejects_resealed_tamper_and_symlink(tmp_path, native, monkeypatch):
    # Only source byte inspection is substituted here; production build validates real originals.
    monkeypatch.setattr(completion, "validate_source_inventory", lambda *args: None)
    root = tmp_path / "bundle"
    completion.build_completion(root, native, tmp_path)
    assert completion.verify_completion(root, native, tmp_path) == {"verified": True}
    target = root / "CONTROL_LIBRARY.csv"
    target.write_text(target.read_text() + "invented accepted control\n")
    manifest = completion.read_json(root / "MANIFEST.json")
    manifest["files"]["CONTROL_LIBRARY.csv"] = hashlib.sha256(target.read_bytes()).hexdigest()
    completion.write_json(root / "MANIFEST.json", manifest)
    with pytest.raises(ValueError, match="re-performance"):
        completion.verify_completion(root, native, tmp_path)
    target.unlink()
    target.symlink_to(tmp_path / "external")
    with pytest.raises(ValueError, match="symlinks"):
        completion.verify_completion(root, native, tmp_path)


def test_source_validation_failure_leaves_no_bundle(tmp_path, native, monkeypatch):
    def fail(*args):
        raise ValueError("Source bytes differ")

    monkeypatch.setattr(completion, "validate_source_inventory", fail)
    with pytest.raises(ValueError, match="Source bytes"):
        completion.build_completion(tmp_path / "bundle", native, tmp_path)
    assert not (tmp_path / "bundle").exists()
