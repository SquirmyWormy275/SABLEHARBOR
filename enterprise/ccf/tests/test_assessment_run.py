"""Reference preparation must preserve baseline duties and isolate fictional execution."""

from copy import deepcopy

import pytest

from enterprise.ccf.assurance import assessment_run as run
from enterprise.ccf.tests.test_substantive import native, sources  # noqa: F401


def test_computed_cases_preserve_boundary_failures_and_history():
    cases = run.synthetic_cases()
    results = {r["case_id"]: r for r in run.evaluate_cases(cases)}
    assert results["DEMO-LEAVER-RENO"]["result"] == "PASS"
    assert results["DEMO-LEAVER-BOISE"]["result"] == "FAIL"
    assert results["DEMO-AI-LATE-IMPACT"]["result"] == "FAIL"
    assert results["DEMO-AI-PROSPECTIVE"]["result"] == "PASS"
    changed = deepcopy(cases)
    changed[0]["end"] = "2026-09-09T11:00:00+00:00"
    assert run.evaluate_cases(changed)[0]["result"] == "FAIL"
    assert run.evaluate_cases(changed)[0]["raw_sha256"] != results[cases[0]["id"]]["raw_sha256"]


@pytest.mark.parametrize("mutation", ["duplicate", "namespace", "timezone", "unknown"])
def test_invalid_synthetic_inputs_rejected(mutation):
    cases = run.synthetic_cases()
    if mutation == "duplicate":
        cases.append(deepcopy(cases[0]))
    elif mutation == "namespace":
        cases[0]["source_record"] = "ACTUAL-RECORD"
    elif mutation == "timezone":
        cases[0]["start"] = "2026-09-09T10:00:00"
    else:
        cases[0]["rule"] = "always_pass"
    with pytest.raises(ValueError):
        run.evaluate_cases(cases)


def test_delta_rejects_lost_duties_or_changed_baseline_semantics():
    base = dict(
        controls=[dict(control_id="C")],
        actions=[
            dict(
                id="A",
                requirement_ids=["R"],
                procedure="P",
                acceptance_test="T",
                work_type="ENHANCE",
                control_ids=["C"],
            )
        ],
        targets=[],
        capability_candidates=[],
    )
    for field, value in [
        ("requirement_ids", []),
        ("procedure", "weaker"),
        ("acceptance_test", "automatic pass"),
    ]:
        changed = deepcopy(base)
        changed["actions"][0][field] = value
        with pytest.raises(ValueError):
            run.delta(base, changed)
    changed = deepcopy(base)
    changed["actions"].append(deepcopy(changed["actions"][0]))
    with pytest.raises(ValueError):
        run.delta(base, changed)


def test_integrated_reference_and_resealed_tamper(monkeypatch, native, sources, tmp_path):  # noqa: F811
    monkeypatch.setattr(run.actions.substantive, "validate_source_inventory", lambda *args: None)
    result = run.run(native, sources)
    assert result["summary"]["combined_equals_union"]
    assert result["summary"]["checklist_rows"] == 210
    assert not result["source_backed_reference"]["assessment"]["evidence"]
    assert not result["source_backed_reference"]["assessment"]["tests"]
    assert all(
        r["test_result"] == "UNTESTED" and r["review"] is None and r["population_count"] is None
        for r in result["evidence_checklist"]
    )
    assert len({r["id"] for r in result["canonical_actions"]}) == len(result["canonical_actions"])
    # Reuse this computed result for packaging checks; production verification recomputes sources.
    monkeypatch.setattr(run, "run", lambda *args: deepcopy(result))
    out = tmp_path / "assessment"
    run.build(out, native, sources)
    assert run.verify(out, native, sources)["verified"]
    altered = run.read_json(out / "ASSESSMENT_RUN.json")
    altered["evidence_checklist"][0]["test_result"] = "PASS"
    run.write_json(out / "ASSESSMENT_RUN.json", altered)
    run.write_json(out / "REVIEW_MANIFEST.json", dict(files=run.substantive.members(out)))
    with pytest.raises(ValueError, match="re-performance"):
        run.verify(out, native, sources)
