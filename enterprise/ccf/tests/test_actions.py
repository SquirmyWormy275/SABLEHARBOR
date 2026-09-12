"""Selectable design deltas must preserve source limits and reject invented acceptance."""

from copy import deepcopy

import pytest

from enterprise.ccf.assurance import actions
from enterprise.ccf.tests.test_substantive import native, sources  # noqa: F401


@pytest.fixture
def prepared(monkeypatch, native, sources):  # noqa: F811
    monkeypatch.setattr(actions.substantive, "validate_source_inventory", lambda *args: None)
    return native, sources


def test_baseline_selection_preserves_roles_without_extension_leakage(prepared):
    result = actions.plan(*prepared, [])
    assert result["baseline"] == ["SOC2", "HIPAA"]
    assert result["summary"]["baseline_checks"] == 116
    assert result["summary"]["source_context_checks"] == 0
    assert not result["capability_candidates"] and not result["c5_criterion_workpapers"]
    assert all(
        rid.split(":")[0] in {"SOC2", "HIPAA"}
        for r in result["actions"]
        for rid in r["requirement_ids"]
    )
    hearing = next(r for r in result["actions"] if r["id"] == "CHECK-HIPAA:160.504")
    assert hearing["work_type"] == "ASSESSMENT_ONLY"
    assert "90 days" in hearing["problem"]
    notice = next(r for r in result["actions"] if r["id"] == "ACTION-H-NOTICE-CLOCK")
    control = next(r for r in result["controls"] if r["control_id"] == "SH-INC-001")
    assert notice["id"] in {r["action_id"] for r in control["proposed_steps"]}
    assert all(
        r["review"] is None and r["implementation"] == "NOT_ASSERTED" for r in result["controls"]
    )


def test_extensions_preserve_child_kind_and_pending_comparisons(prepared):
    result = actions.plan(*prepared, ["ISO27001", "ISO42001", "C5"])
    assert result["summary"]["source_context_checks"] == 3
    assert len(result["c5_criterion_workpapers"]) == 623
    c5 = {r["requirement_id"]: r for r in result["c5_criterion_workpapers"]}
    assert (
        c5["C5:AM-02.01B"]["comparison_depth"] == "AUTHOR_CHILD_CONDITION_COMPARISON_NOT_ACCEPTANCE"
    )
    assert "SH-CFG-001" in c5["C5:AM-02.01B"]["individually_proposed_procedures"]
    assert c5["C5:AM-02.01B"]["author_child_comparison"]["work_type"] == "REUSE_VALIDATION"
    assert c5["C5:AM-02.01B"]["domain_candidate_procedures"]
    assert {r["kind"] for r in c5.values()} == {
        "basic",
        "additional_sharpen",
        "additional_complement",
    }
    assert all(r["review"] is None for r in c5.values())
    assert (
        result["summary"]["accepted_coverage"] == result["summary"]["actual_implementations"] == 0
    )
    cap = next(r for r in result["capability_candidates"] if r["id"] == "CAP-SELECTED-REDUNDANCY")
    assert cap["classification"] == "NEW_CAPABILITY_CANDIDATE_NOT_CONFIRMED_ABSENT"
    assert "when the exact criterion is selected" in cap["activation"]
    assert (
        "GATE-C5-SELECTION"
        in next(r for r in result["actions"] if r["id"] == cap["action_id"])["dependencies"]
    )


def test_changed_procedure_analysis_requires_reconsideration(prepared, monkeypatch):
    original = actions.read_json

    def changed(path):
        result = original(path)
        if path == actions.DATA / "baseline_checks.json":
            result = deepcopy(result)
            result[0]["procedure_and_test"] = "Changed interpretation"
        return result

    monkeypatch.setattr(actions, "read_json", changed)
    with pytest.raises(ValueError, match="stale"):
        actions.plan(*prepared, [])


def test_invalid_target_rejected(prepared):
    for selected in [["ISO27001", "ISO27001"], ["UNKNOWN"]]:
        with pytest.raises(ValueError, match="distinct supported"):
            actions.plan(*prepared, selected)


def test_resealed_action_edits_cannot_forge_acceptance(prepared, tmp_path):
    output = tmp_path / "delivery"
    actions.build(output, *prepared, [])
    assert actions.verify(output, *prepared)["verified"]
    report = actions.read_json(output / "ACTION_PLAN.json")
    report["controls"][0]["implementation"] = "DEPLOYED"
    actions.write_json(output / "ACTION_PLAN.json", report)
    manifest = actions.read_json(output / "REVIEW_MANIFEST.json")
    manifest["files"] = actions.substantive.members(output)
    actions.write_json(output / "REVIEW_MANIFEST.json", manifest)
    with pytest.raises(ValueError, match="re-performance"):
        actions.verify(output, *prepared)


@pytest.mark.parametrize("target,other", [("ISO27001", "ISO42001"), ("ISO42001", "ISO27001")])
def test_single_iso_selection_excludes_other_frameworks(prepared, target, other):
    result = actions.plan(*prepared, [target])
    assert not result["c5_criterion_workpapers"]
    assert not any(
        rid.startswith((other + ":", "C5:"))
        for r in result["actions"]
        for rid in r["requirement_ids"]
    )
    assert result["summary"]["source_context_checks"] == (2 if target == "ISO27001" else 1)
