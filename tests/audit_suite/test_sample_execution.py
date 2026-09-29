from copy import deepcopy
from dataclasses import asdict

import pytest

from enterprise.audit_suite import sample_execution as execution
from enterprise.audit_suite.population_lifecycle import population
from enterprise.audit_suite.populations import select
from enterprise.audit_suite.store import DomainError, Store, digest
from tests.audit_suite.test_population_lifecycle import context as population_context


@pytest.fixture
def trace(tmp_path):
    state, artifacts, stamp = population_context.__wrapped__(tmp_path)
    pop = population(state["populations"][0])
    chosen = select(
        pop,
        selection_id="SEL-a",
        method="MANUAL",
        ids=["a"],
        targeted_ids=["b"],
        purpose="Local procedure",
        rationale="Explicit selection",
    )
    state["selections"] = [{"id": chosen.id, "immutable": asdict(chosen)}]
    task = {
        "id": "TASK",
        "control_id": "C",
        "boundary_id": "corporate",
        "status": "NOT_STARTED",
        "conclusion": "NOT_RUN",
    }
    wp = {
        "id": "WP",
        "control_id": "C",
        "versions": [
            {"version": 1, "task_ids": ["TASK"], "text": "Original procedure"},
            {"version": 2, "task_ids": [], "text": "Later distinct work"},
        ],
    }
    state.update(
        phase="ACTIVE",
        scope={
            "boundaries": ["corporate"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
        },
        controls=[{"id": "C"}],
        tasks=[task],
        workpapers=[wp],
    )
    ref = {
        "artifact_id": state["artifacts"][0]["id"],
        "sha256": state["artifacts"][0]["sha256"],
        "locator": "Author supplied CSV row a",
    }
    payload = {
        "task_id": "TASK",
        "task_digest": digest(task),
        "population_id": pop.id,
        "population_digest": pop.sha256,
        "selection_id": chosen.id,
        "selection_digest": chosen.sha256,
        "workpaper_id": "WP",
        "workpaper_version": 1,
        "workpaper_digest": digest(wp["versions"][0]),
        "purpose": "Inspect retained selected rows",
        "procedure": "Read the selected local CSV row and document observation.",
        "items": [
            {
                "item_id": "a",
                "status": "OBSERVED",
                "observation": "Value recorded as10 in supplied CSV.",
                "evidence": [ref],
            },
            {
                "item_id": "b",
                "status": "NOT_PERFORMED",
                "observation": "Targeted inspection not yet performed.",
                "evidence": [],
            },
        ],
    }
    return state, artifacts, stamp, payload


def test_actual_original_and_historical_wp_trace_do_not_change_other_work(trace):
    state, artifacts, stamp, payload = trace
    before = deepcopy(state)
    execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    row = state.pop("sample_executions")[0]
    assert state == before
    assert row["workpaper_version"] == 1
    assert row["population_status"] == "PROVISIONAL" and row["selection_provisional"]
    assert row["items"][0]["selection_basis"] == "SAMPLED"
    assert row["items"][1]["selection_basis"] == "TARGETED"
    assert row["items"][0]["item_digest"] == digest({"id": "a", "amount": 10})
    assert row["items"][0]["locator_validation"] == "AUTHOR_SUPPLIED_NOT_CONTENT_MATCH_VERIFIED"
    assert not row["automatic_testing_credit"] and row["independent_review"] == "NOT_PERFORMED"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s, p: p.update(selection_digest="0" * 64),
        lambda s, p: p.update(
            workpaper_version=2, workpaper_digest=digest(s["workpapers"][0]["versions"][1])
        ),
        lambda s, p: p["items"][0].update(item_id="invented"),
        lambda s, p: p["items"][0]["evidence"][0].update(sha256="0" * 64),
        lambda s, p: s["artifacts"][0].update(audience="REVIEWER"),
        lambda s, p: s["artifacts"][0].update(status="QUARANTINED"),
        lambda s, p: s["tasks"][0].update(applicability="HISTORICAL"),
        lambda s, p: s["tasks"][0].update(control_id="OTHER"),
        lambda s, p: s["populations"][0].update(scope_reassessment="REQUIRED_FOR_REUSE"),
        lambda s, p: s["scope"].update(boundaries=["other"]),
        lambda s, p: s["scope"].update(period_end="2027-01-02"),
        lambda s, p: p["items"][0].update(status="PASS"),
        lambda s, p: p["items"][0].update(evidence=[]),
        lambda s, p: p["items"].append(deepcopy(p["items"][0])),
    ],
)
def test_bad_references_fail_without_appending(trace, mutation):
    state, artifacts, stamp, payload = trace
    mutation(state, payload)
    before = deepcopy(state)
    with pytest.raises(DomainError):
        execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    assert state == before


def test_corrupt_actual_original_rejected(trace):
    state, artifacts, stamp, payload = trace
    (artifacts.root / state["artifacts"][0]["sha256"]).write_bytes(b"corrupted")
    before = deepcopy(state)
    with pytest.raises(DomainError):
        execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    assert state == before


def test_corrections_preserve_old_body_and_reject_fork_sample_or_context(trace):
    state, artifacts, stamp, payload = trace
    execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    first = deepcopy(state["sample_executions"][0])
    correction = {
        **payload,
        "predecessor_id": first["id"],
        "predecessor_digest": digest(first),
        "correction_rationale": "Correct transcription wording.",
    }
    correction["items"] = deepcopy(payload["items"])
    correction["items"][0]["observation"] = "Corrected author wording; no change to source."
    for changed in [
        {**correction, "items": correction["items"][:1]},
        {**correction, "predecessor_digest": "0" * 64},
    ]:
        with pytest.raises(DomainError):
            execution.handle(state, "sample.execution.correct", changed, stamp, artifacts)
    state["company_source_binding"] = {"branch": "changed"}
    with pytest.raises(DomainError, match="original scope"):
        execution.handle(state, "sample.execution.correct", correction, stamp, artifacts)
    state.pop("company_source_binding")
    execution.handle(state, "sample.execution.correct", correction, stamp, artifacts)
    assert state["sample_executions"][0] == first and state["sample_executions"][1]["revision"] == 2
    with pytest.raises(DomainError, match="latest"):
        execution.handle(state, "sample.execution.correct", correction, stamp, artifacts)


def test_store_cas_replay_and_roles_enforce_handler_boundary(trace, tmp_path):
    state, artifacts, stamp, payload = trace
    store = Store(tmp_path / "store")
    actor = store.provision("Learner", ["learner"])["id"]
    state["artifacts"][0].pop("engagement_id", None)  # legacy scoped manifest
    created = store.create(actor, state, "create")
    eid = created["id"]
    # Artifacts with no engagement_id use current fixture's authorized manifest;
    # actual Engine retains the engagement association at collection time.
    command = {
        "command_id": "trace",
        "expected_revision": created["revision"],
        "kind": "sample.execution.record",
        "payload": payload,
    }

    def reducer(current, envelope, current_actor):
        execution.handle(
            current, envelope["kind"], envelope["payload"], {**stamp, "actor": actor}, artifacts
        )
        return current

    result = store.command(actor, eid, command, reducer, permissions={"learn", "instruct"})
    assert store.command(actor, eid, command, reducer, permissions={"learn", "instruct"}) == result
    with pytest.raises(DomainError):
        store.command(
            actor,
            eid,
            {**command, "command_id": "stale"},
            reducer,
            permissions={"learn", "instruct"},
        )
    outsider = store.provision("Independent reviewer", ["reviewer"])["id"]
    store.grant(eid, outsider, "review")
    with pytest.raises(DomainError):
        store.command(
            outsider,
            eid,
            {**command, "command_id": "role", "expected_revision": result["revision"]},
            reducer,
            permissions={"learn", "instruct"},
        )
    assert len(store.get(actor, eid)["sample_executions"]) == 1


def test_nested_lineage_pins_original_parent_and_rejects_different_parent(trace):
    from enterprise.audit_suite.populations import create_population

    state, artifacts, stamp, payload = trace
    original = population(state["populations"][0])
    parent = create_population(
        "SITES",
        1,
        [{"id": "SITE-A"}, {"id": "SITE-B"}],
        scope=original.scope,
        source=original.source,
    )
    chosen_parent = select(
        parent,
        selection_id="SITE-SEL",
        method="MANUAL",
        ids=["SITE-A"],
        purpose="Local sites",
        rationale="One explicit site",
    )
    child = create_population(
        "CHILD",
        1,
        [{"id": "a", "site": "SITE-A"}, {"id": "b", "site": "SITE-A"}],
        scope=original.scope,
        source=original.source,
        parent_population=parent,
        parent_selection=chosen_parent,
        parent_key="site",
    )
    selected = select(
        child,
        selection_id="CHILD-SEL",
        method="MANUAL",
        ids=["a"],
        targeted_ids=["b"],
        purpose="Child sample",
        rationale="Exact selected site",
    )
    state["populations"] = [
        {"id": parent.id, "immutable": asdict(parent)},
        {"id": child.id, "immutable": asdict(child), "parent_selection_id": chosen_parent.id},
    ]
    state["selections"] = [
        {"id": chosen_parent.id, "immutable": asdict(chosen_parent)},
        {"id": selected.id, "immutable": asdict(selected)},
    ]
    payload.update(
        population_id=child.id,
        population_digest=child.sha256,
        selection_id=selected.id,
        selection_digest=selected.sha256,
    )
    execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    assert (
        state["sample_executions"][0]["parent_lineage"][0]["selection_digest"]
        == chosen_parent.sha256
    )
    state["populations"][1]["parent_selection_id"] = selected.id
    before = deepcopy(state)
    with pytest.raises(DomainError):
        execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    assert state == before


def test_unavailable_support_record_requires_no_population_acceptance_and_bounds_text(trace):
    state, artifacts, stamp, payload = trace
    for item in payload["items"]:
        item.update(
            status="SUPPORT_UNAVAILABLE",
            evidence=[],
            observation="Requested support not yet obtained.",
        )
    execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    assert state["sample_executions"][0]["population_status"] == "PROVISIONAL"
    before = deepcopy(state)
    payload["procedure"] = "x" * 12001
    with pytest.raises(DomainError):
        execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    assert state == before


def test_input_pins_use_python_exact_objects_without_mutation_and_preserve_historical_link(trace):
    state, artifacts, stamp, payload = trace
    state["tasks"][0]["neutral_numeric_value"] = 1.0
    state["workpapers"][0]["versions"][0]["neutral_numeric_value"] = 1e20
    before = deepcopy(state)
    pins = execution.input_pins(state)
    assert state == before
    assert pins["tasks"][0]["task_digest"] == digest(state["tasks"][0])
    assert pins["workpaper_versions"] == [
        {
            "workpaper_id": "WP",
            "workpaper_version": 1,
            "workpaper_digest": digest(state["workpapers"][0]["versions"][0]),
            "task_ids": ["TASK"],
            "control_id": "C",
        }
    ]
    assert pins["selections"][0]["selection_digest"] == payload["selection_digest"]
    assert pins["selections"][0]["selection_provisional"]
    assert pins["artifacts"][0]["sha256"] == state["artifacts"][0]["sha256"]
    assert "records_json" not in str(pins)


def test_input_pins_hide_private_ambiguous_and_stale_scope_records(trace):
    state, artifacts, stamp, payload = trace
    state["artifacts"][0]["audience"] = "REVIEWER"
    state["tasks"][0]["applicability"] = "HISTORICAL"
    state["populations"][0]["scope_reassessment"] = "REQUIRED_FOR_REUSE"
    pins = execution.input_pins(state)
    assert (
        pins["artifacts"] == pins["tasks"] == pins["workpaper_versions"] == pins["selections"] == []
    )
    state["artifacts"][0]["audience"] = "LEARNER"
    state["artifacts"].append(deepcopy(state["artifacts"][0]))
    assert execution.input_pins(state)["artifacts"] == []


def test_correction_input_pins_only_current_leaf_with_exact_server_digest(trace):
    state, artifacts, stamp, payload = trace
    execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    first = deepcopy(state["sample_executions"][0])
    assert execution.input_pins(state)["correctable_executions"] == [
        {"execution_id": first["id"], "predecessor_digest": digest(first)}
    ]
    correction = {
        **payload,
        "predecessor_id": first["id"],
        "predecessor_digest": digest(first),
        "correction_rationale": "Document clearer wording.",
    }
    execution.handle(state, "sample.execution.correct", correction, stamp, artifacts)
    latest = state["sample_executions"][-1]
    assert execution.input_pins(state)["correctable_executions"] == [
        {"execution_id": latest["id"], "predecessor_digest": digest(latest)}
    ]
    for field, value in [
        ("company_source_binding", {"branch": "new"}),
        ("evidence_acquisition", {"mode": "new"}),
        ("scope", {**state["scope"], "timezone": "America/Denver"}),
    ]:
        changed = deepcopy(state)
        changed[field] = value
        assert execution.input_pins(changed)["correctable_executions"] == []
    changed = deepcopy(state)
    changed["tasks"][0]["applicability"] = "HISTORICAL"
    assert execution.input_pins(changed)["correctable_executions"] == []
    assert state["sample_executions"][0] == first


@pytest.mark.parametrize("overflow", ["collection", "paper_versions", "eligible_versions"])
def test_input_projection_overflow_returns_no_partial_index_and_preserves_state(trace, overflow):
    state, artifacts, stamp, payload = trace
    if overflow == "collection":
        state["tasks"] = [{"id": f"T{i}"} for i in range(20001)]
    elif overflow == "paper_versions":
        state["workpapers"][0]["versions"] = [
            {"version": i, "task_ids": ["TASK"]} for i in range(10001)
        ]
    else:
        state["workpapers"] = [
            {
                "id": f"WP{i}",
                "control_id": "C",
                "versions": [{"version": v, "task_ids": ["TASK"]} for v in range(7000)],
            }
            for i in range(3)
        ]
    before = deepcopy(state)
    result = execution.input_pins(state)
    assert result["status"] == "INPUT_LIMIT_EXCEEDED"
    assert all(
        result[k] == []
        for k in [
            "tasks",
            "selections",
            "workpaper_versions",
            "artifacts",
            "correctable_executions",
        ]
    )
    assert state == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("tasks", None),
        ("tasks", [{"id": []}]),
        ("workpapers", [{"id": "OLD", "versions": None}]),
        ("workpapers", [{"id": "OLD", "versions": [{"version": 1, "task_ids": None}]}]),
        ("artifacts", [{"name": "Old manifest without ID"}]),
        ("sample_executions", [None]),
    ],
)
def test_malformed_legacy_projection_does_not_break_unrelated_read(trace, field, value):
    state, artifacts, stamp, payload = trace
    state[field] = value
    before = deepcopy(state)
    result = execution.input_pins(state)
    assert result["status"] == "INPUT_DATA_UNAVAILABLE"
    assert result["tasks"] == result["artifacts"] == result["workpaper_versions"] == []
    assert state == before
