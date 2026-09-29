"""Exact recorded test/finding links; no inferred performance."""

from copy import deepcopy

import pytest

from enterprise.audit_suite import sample_execution
from enterprise.audit_suite.instructor_assessments import references
from enterprise.audit_suite.instructor_work_links import index, selected
from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_sample_execution import trace as native_trace


@pytest.fixture
def trace(tmp_path):
    state, artifacts, stamp, payload = native_trace.__wrapped__(tmp_path)
    sample_execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    return state, artifacts, stamp, payload


def links(state, artifacts, tasks=()):
    return selected(
        index(state, artifacts),
        set(artifacts),
        {
            "authored_task_ids": list(tasks),
            "task_mapping_status": "EXPLICIT_AUTHORED_LINKS" if tasks else "UNMAPPED",
        },
    )


def test_actual_trace_exact_original_and_historical_workpaper(trace):
    state, _, _, _ = trace
    before = deepcopy(state)
    a = state["artifacts"][0]
    result = links(state, {a["id"]: a["sha256"]})["recorded_sample_executions"][0]
    original = state["sample_executions"][0]
    assert result["record_sha256"] == digest(original)
    assert result["version"] == 1
    assert result["workpaper_version"] == 1
    assert result["workpaper_digest"] == digest(state["workpapers"][0]["versions"][0])
    assert result["matched_items"][0]["item_id"] == "a"
    assert not result["automatic_testing_credit"]
    assert state == before
    assert links(state, {a["id"]: "0" * 64})["recorded_sample_executions"] == []


def test_task_only_trace_requires_explicit_author_and_exact_task_pin(trace):
    state, _, _, _ = trace
    assert links(state, {})["recorded_sample_executions"] == []
    row = links(state, {}, ["TASK"])["recorded_sample_executions"][0]
    assert row["authored_task_match"] and row["source_artifact_ids"] == []
    state["tasks"][0]["status"] = "CHANGED"
    assert links(state, {}, ["TASK"])["recorded_sample_executions"] == []


def test_real_correction_keeps_old_and_new_exact_trace_pins(trace):
    state, artifacts, stamp, payload = trace
    old = deepcopy(state["sample_executions"][0])
    correction = {
        **payload,
        "predecessor_id": old["id"],
        "predecessor_digest": digest(old),
        "correction_rationale": "Clarify explicit observation",
    }
    correction["items"] = deepcopy(payload["items"])
    correction["items"][0]["observation"] = "Corrected author interpretation"
    sample_execution.handle(state, "sample.execution.correct", correction, stamp, artifacts)
    a = state["artifacts"][0]
    rows = links(state, {a["id"]: a["sha256"]})["recorded_sample_executions"]
    assert rows[0]["trace_status"] == "HISTORICAL_CORRECTED"
    assert rows[0]["record_sha256"] == digest(old)
    assert rows[1]["predecessor_digest"] == digest(old)
    assert rows[1]["version"] == 2
    assert rows[1]["trace_status"] == "CURRENT_LEAF_IN_SELECTED_HISTORY"
    assert rows[0]["successor_id"] == rows[1]["id"]


@pytest.mark.parametrize("revision", [True, 1.0])
def test_trace_revision_type_not_numeric_equality(trace, revision):
    state, _, _, _ = trace
    state["sample_executions"][0]["revision"] = revision
    with pytest.raises(DomainError):
        links(state, {}, ["TASK"])


def test_finding_remediation_explicit_evidence_not_control_or_title(trace):
    state, _, _, _ = trace
    a = state["artifacts"][0]
    remediation = {"id": "R", "evidence_ids": [a["id"]], "status": "OPEN"}
    finding = {"id": "F", "evidence_ids": [], "remediations": [remediation]}
    unrelated = {"id": "NOT_LINKED", "control_id": "C", "title": a["id"], "evidence_ids": []}
    state["findings"] = [finding, unrelated]
    result = links(state, {a["id"]: a["sha256"]})
    assert result["recorded_findings"] == []
    assert result["recorded_remediations"][0]["record_sha256"] == digest(remediation)
    assert result["recorded_remediations"][0]["finding_id"] == "F"
    finding["evidence_ids"] = [a["id"]]
    result = links(state, {a["id"]: a["sha256"]})
    assert [r["id"] for r in result["recorded_findings"]] == ["F"]
    assert result["recorded_findings"][0]["record_sha256"] == digest(finding)


def test_assessment_reference_allowlist_preserves_new_exact_record_digests(trace):
    state, _, _, _ = trace
    a = state["artifacts"][0]
    state["findings"] = [
        {
            "id": "F",
            "evidence_ids": [a["id"]],
            "remediations": [{"id": "R", "evidence_ids": [a["id"]]}],
        }
    ]
    linked = links(state, {a["id"]: a["sha256"]})
    expectation = {
        "expectation_id": "E",
        "source_ids": [],
        "control_associated_records_only": {"tasks": [], "requests": []},
        "source_linked_populations": [],
        "population_linked_selections": [],
        "source_linked_workpaper_versions": [],
        "workpaper_version_reviews": [],
        **linked,
    }
    refs = references({"sources": [], "expectations": [expectation]})
    assert {r["kind"] for r in refs} == {"sample_execution", "finding", "remediation"}
    assert next(r for r in refs if r["kind"] == "sample_execution")["content_sha256"] == digest(
        state["sample_executions"][0]
    )
    assert next(r for r in refs if r["kind"] == "finding")["version"] is None


def test_actual_task_only_trace_survives_bound_assessment_and_later_revision(tmp_path):
    from enterprise.audit_suite.instructor_assessments import (
        InstructorAssessments,
        validate_archive,
    )
    from tests.audit_suite.test_explanation_binding import workspace
    from tests.audit_suite.test_instructor_assessments import payload as assessment_payload
    from tests.audit_suite.test_instructor_comparison import advance, bound

    local = tmp_path / "local"
    local.mkdir()
    state, artifacts, stamp, p = native_trace.__wrapped__(local)
    state["tasks"][0]["control_id"] = "CONTROL1"
    state["workpapers"][0]["control_id"] = "CONTROL1"
    state["controls"] = [{"id": "CONTROL1"}]
    p["task_digest"] = digest(state["tasks"][0])
    sample_execution.handle(state, "sample.execution.record", p, stamp, artifacts)
    engine, args = workspace.__wrapped__(tmp_path)
    advance(
        engine,
        args,
        lambda s: {
            **s,
            "tasks": state["tasks"],
            "scope": {**s["scope"], "boundaries": ["corporate"]},
            "workpapers": state["workpapers"],
            "sample_executions": state["sample_executions"],
        },
    )
    args["authored"]["expectations"][0]["task_ids"] = ["TASK"]
    engine, args, bindings = bound((engine, args))
    root = tmp_path / "private-assessments"
    root.mkdir(mode=0o700)
    core = InstructorAssessments(root, engine, bindings)
    opts = core.options(args["instructor_id"], args["engagement_id"], 1)
    ref = next(r for r in opts["references"] if r["kind"] == "sample_execution")
    assert ref["content_sha256"] == digest(state["sample_executions"][0])
    p = assessment_payload(core, args, 1)
    p["dimensions"][2]["reference_ids"] = [ref["id"]]
    saved = core.save(args["instructor_id"], args["engagement_id"], p)
    advance(engine, args, lambda s: {**s, "sample_executions": []})
    loaded = core.read(args["instructor_id"], args["engagement_id"], saved["id"])
    assert loaded["document"]["references"] == saved["document"]["references"]
    validate_archive(core.snapshot())


def test_bound_finding_and_remediation_references_save_exact_historical_records(tmp_path):
    from enterprise.audit_suite.instructor_assessments import validate_archive
    from tests.audit_suite.test_instructor_assessments import assessment, payload
    from tests.audit_suite.test_instructor_comparison import advance

    core, engine, args = assessment.__wrapped__(tmp_path)
    source = args["source_refs"][0]
    remediation = {"id": "R1", "evidence_ids": ["A1"], "status": "OPEN"}
    finding = {"id": "F1", "evidence_ids": ["A1"], "status": "DRAFT", "remediations": [remediation]}
    advance(
        engine,
        args,
        lambda s: {
            **s,
            "company_source_binding": {"company": "C", "branch": "B"},
            "artifacts": [
                {"id": "A1", "sha256": source["sha256"], "source": {"receipt": {"source": source}}}
            ],
            "findings": [finding],
        },
    )
    actor, eid = args["instructor_id"], args["engagement_id"]
    refs = [
        r
        for r in core.options(actor, eid, 1)["references"]
        if r["kind"] in {"finding", "remediation"}
    ]
    assert {r["content_sha256"] for r in refs} == {digest(finding), digest(remediation)}
    p = payload(core, args, 1)
    p["dimensions"][5]["reference_ids"] = [r["id"] for r in refs]
    saved = core.save(actor, eid, p)
    advance(engine, args, lambda s: {**s, "findings": [{**finding, "status": "CHANGED"}]})
    assert {r["id"]: r for r in core.read(actor, eid, saved["id"])["document"]["references"]} == {
        r["id"]: r for r in refs
    }
    validate_archive(core.snapshot())
