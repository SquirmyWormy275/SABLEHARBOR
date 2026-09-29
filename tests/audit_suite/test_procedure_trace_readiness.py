from copy import deepcopy

import pytest

from enterprise.audit_suite import procedure_trace_readiness as readiness
from enterprise.audit_suite import sample_execution as execution
from enterprise.audit_suite.audit_readiness import summarize
from enterprise.audit_suite.population_lifecycle import handle as population_command
from enterprise.audit_suite.store import digest
from tests.audit_suite.test_sample_execution import trace as trace


def recorded(fixture):
    state, artifacts, stamp, payload = fixture
    execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    return state, artifacts, stamp, payload


def task(state):
    return readiness.summarize(state)["by_task"]["TASK"]


def test_real_correction_one_current_leaf_preserves_old_status_and_historical_wp(trace):
    state, artifacts, stamp, payload = recorded(trace)
    first = deepcopy(state["sample_executions"][0])
    corrected = deepcopy(payload)
    corrected.update(
        predecessor_id=first["id"],
        predecessor_digest=digest(first),
        correction_rationale="Later retained support unavailable",
    )
    corrected["items"][0].update(status="SUPPORT_UNAVAILABLE", evidence=[])
    execution.handle(state, "sample.execution.correct", corrected, stamp, artifacts)
    before = deepcopy(state)
    result = task(state)
    assert result["status"] == "RECORDED_TRACE_LINKS"
    assert result["trace_count"] == 2 and result["current_leaf_count"] == 1
    assert result["lineages"][0]["historical_trace_ids"] == [first["id"]]
    assert result["traces"][0]["recorded_item_status_counts"]["OBSERVED"] == 1
    assert result["current_leaf_item_status_counts"] == {
        "SUPPORT_UNAVAILABLE": 1,
        "NOT_PERFORMED": 1,
    }
    refs = result["traces"][1]["exact_refs"]
    assert next(r for r in refs if r["kind"] == "workpaper")["version"] == 1
    assert not result["automatic_testing_credit"] and state == before
    state["revision"] = 3
    state.setdefault("requests", [])
    state.setdefault("reviews", [])
    report = summarize(state)
    assert report["controls"][0]["procedures"][0]["sample_trace_readiness"] == result


def test_new_population_assessment_does_not_relabel_original_selected_reliability(trace):
    state, artifacts, stamp, payload = recorded(trace)
    population_command(
        state,
        "population.assess",
        {
            "population_id": payload["population_id"],
            "status": "READY_FOR_PURPOSE",
            "purpose": "Narrow author decision",
            "rationale": "Recorded assessment only",
            "observable_artifact_ids": [state["artifacts"][0]["id"]],
        },
        stamp,
        artifacts,
    )
    report = task(state)
    assert report["status"] == "RECORDED_TRACE_LINKS"
    assert report["traces"][0]["population_reliability"]["recorded_status"] == "PROVISIONAL"
    assert report["traces"][0]["period_qualification"]["source_query"] == "all supplied rows"
    assert report["completeness_accuracy"] == "NOT_ESTABLISHED_BY_TRACE_REPORT"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s["tasks"][0].update(status="COMPLETE"),
        lambda s: s["artifacts"].clear(),
        lambda s: s["artifacts"][0].update(audience="INSTRUCTOR"),
        lambda s: s["workpapers"][0]["versions"][0].update(text="Changed original"),
        lambda s: s["sample_executions"][0]["items"][0].update(item_digest="f" * 64),
        lambda s: s["sample_executions"][0].update(workpaper_version=True),
        lambda s: s.update(company_source_binding={"branch": "another"}),
    ],
)
def test_changed_or_inaccessible_pins_never_show_link_or_zero_failure_count(trace, mutation):
    state, *_ = recorded(trace)
    mutation(state)
    report = task(state)
    assert report["status"] == "UNAVAILABLE"
    assert report["current_leaf_count"] is None
    assert report["current_leaf_item_status_counts"] is None
    assert "exact_refs" not in report["traces"][0]


def test_forked_correction_is_ambiguous_not_two_current_observations(trace):
    state, artifacts, stamp, payload = recorded(trace)
    first = state["sample_executions"][0]
    execution.handle(
        state,
        "sample.execution.correct",
        {
            **payload,
            "predecessor_id": first["id"],
            "predecessor_digest": digest(first),
            "correction_rationale": "Correction",
        },
        stamp,
        artifacts,
    )
    fork = deepcopy(state["sample_executions"][-1])
    fork["id"] = "FORK"
    state["sample_executions"].append(fork)
    report = task(state)
    assert report["status"] == "UNAVAILABLE" and report["current_leaf_count"] is None
    assert len(report["traces"]) == 3


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s["sample_executions"].append(deepcopy(s["sample_executions"][0])),
        lambda s: s["sample_executions"][0].update(predecessor_id="missing", revision=2),
        lambda s: s["sample_executions"][0].update(predecessor_id=s["sample_executions"][0]["id"]),
    ],
)
def test_duplicate_missing_and_cyclic_chains_unavailable(trace, change):
    state, *_ = recorded(trace)
    change(state)
    assert task(state)["current_leaf_count"] is None


def test_bounds_and_malformed_records_report_unknown_not_empty_success(trace, monkeypatch):
    state, *_ = recorded(trace)
    monkeypatch.setattr(readiness, "MAX_TRACES", 0)
    report = readiness.summarize(state)
    assert report["status"] == "INPUT_UNAVAILABLE"
    assert report["by_task"]["TASK"]["trace_count"] is None
    assert report["unavailable_count"] is None
    monkeypatch.setattr(readiness, "MAX_TRACES", 2000)
    state["sample_executions"] = [None]
    assert readiness.summarize(state)["status"] == "INPUT_UNAVAILABLE"


def test_unobserved_selection_items_explicit_and_not_completeness(trace):
    state, artifacts, stamp, payload = trace
    payload["items"] = payload["items"][:1]
    execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    row = task(state)["traces"][0]
    assert row["selected_item_count"] == 2 and row["items_with_no_recorded_observation_count"] == 1
    assert row["population_reliability"]["independent_denominator"] == "NOT_ESTABLISHED"


def test_scope_type_alias_and_duplicate_locator_are_not_valid_metadata(trace):
    state, *_ = recorded(trace)
    first = deepcopy(state)
    state["sample_executions"][0]["items"][0]["evidence"] *= 2
    assert task(state)["status"] == "UNAVAILABLE"
    state = first
    state["scope"]["version"] = 1
    row = state["sample_executions"][0]
    row["scope_digest"] = digest(state["scope"])
    row["scope"]["version"] = True
    assert task(state)["status"] == "UNAVAILABLE"


def test_unresolvable_task_reference_has_no_reference_details(trace):
    state, *_ = recorded(trace)
    state["sample_executions"][0]["task_id"] = "UNAVAILABLE-PRIVATE-TASK"
    report = readiness.summarize(state)
    assert report["status"] == "PARTIAL_UNAVAILABLE"
    assert report["unavailable_count"] == 1
    assert "UNAVAILABLE-PRIVATE-TASK" not in str(report)


def test_recorded_reliability_qualification_is_separate_from_current_pin(trace):
    state, *_ = recorded(trace)
    # A legacy author qualification can differ from the currently pinned source;
    # report both without pretending either is independent truth.
    state["sample_executions"][0]["population_status"] = "UNDER_RELIABILITY_EVALUATION"
    state["sample_executions"][0]["selection_provisional"] = False
    result = task(state)
    assert result["status"] == "RECORDED_TRACE_LINKS"
    reliability = result["traces"][0]["population_reliability"]
    assert reliability["recorded_status"] == "UNDER_RELIABILITY_EVALUATION"
    assert reliability["current_population_status"] == "PROVISIONAL"
    assert reliability["selection_provisional"] is False
    assert reliability["current_selection_provisional"] is True
    assert not reliability["recorded_qualifiers_match_current_pins"]
    assert not result["automatic_testing_credit"]
