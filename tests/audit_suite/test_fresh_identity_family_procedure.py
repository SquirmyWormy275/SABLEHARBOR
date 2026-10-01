"""Neutral mutation tests for new family admission and per-item performance."""

import json
from copy import deepcopy
from dataclasses import asdict

import pytest

from enterprise.audit_suite import populations
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.fresh_identity_family_procedure import (
    AS_OF,
    ProcedureError,
    analyze,
    check_links,
    immutable_schema,
    population_rows,
    projected,
    sample_items,
    sample_observation,
    task_evaluation,
    verify_sample_trace,
)
from enterprise.audit_suite.store import digest


def row(record, *, component="identity", system="hr", document=None, at="2027-01-01"):
    return {
        "component": component,
        "document": document or {},
        "content_bytes": 5,
        "source": {
            "company": "EXAMPLE",
            "branch": "scope",
            "system": system,
            "record": record,
            "version": 1,
            "sha256": "1" * 64,
            "event_at": at + "T00:00:00Z",
            "available_at": at + "T00:01:00Z",
            "imported_at": "2026-10-01T00:00:00Z",
        },
    }


def test_future_available_record_rejected_before_control_calculation():
    r = row("future", at="2028-02-01")
    with pytest.raises(ProcedureError, match="Future/invalid"):
        analyze([r], {"canonical_people": []}, as_of=AS_OF)


def test_duplicate_actual_source_version_is_not_a_larger_population():
    r = row("one")
    with pytest.raises(ProcedureError, match="Duplicate observed"):
        analyze([r, deepcopy(r)], {"canonical_people": []}, as_of=AS_OF)


def test_unmatched_hr_subject_is_not_admitted_by_count_only():
    r = row("hr", document={"person_id": "unknown"})
    with pytest.raises(ProcedureError, match="outside canonical"):
        analyze([r], {"canonical_people": [{"person_id": "employee"}]}, as_of=AS_OF)


def test_duplicate_canonical_member_is_not_hidden_by_dictionary_projection():
    with pytest.raises(ProcedureError, match="Duplicate canonical"):
        analyze([], {"canonical_people": [{"person_id": "employee"}] * 2}, as_of=AS_OF)


def test_declared_review_count_cannot_replace_hr_member_identity():
    hr = row("hr", document={"person_id": "employee"})
    review = row(
        "q1", system="review_population", document={"declared_employee_ids": ["different"]}
    )
    with pytest.raises(ProcedureError, match="cohort differs"):
        analyze([hr, review], {"canonical_people": [{"person_id": "employee"}]}, as_of=AS_OF)


def test_joined_source_hash_changed_is_rejected():
    target = row("target")
    ref = {
        k: target["source"][k]
        for k in ("company", "branch", "system", "record", "version", "sha256")
    }
    ref["sha256"] = "2" * 64
    caller = row("caller", document={"reference": ref}, at="2027-02-01")
    with pytest.raises(ProcedureError, match="join byte hash"):
        check_links([target, caller])


def test_future_native_join_is_rejected_despite_valid_hash():
    target = row("target", at="2027-03-01")
    caller = row("caller", document={"reference": target["source"]}, at="2027-02-01")
    with pytest.raises(ProcedureError, match="future source"):
        check_links([target, caller])


def test_absent_typed_join_stays_explicit_limitation():
    ref = row("missing")["source"]
    result = check_links([row("caller", document={"reference": ref}, at="2027-02-01")])
    assert len(result["unresolved"]) == 1
    assert result["checked"] == []


def test_missing_predecessor_in_full_history_fails_closed():
    r = row(
        "caller",
        document={"source_previous": {"record": "missing", "sha256": "1" * 64}},
        at="2027-02-01",
    )
    with pytest.raises(ProcedureError, match="predecessor"):
        check_links([r])


def test_distinct_physical_stores_can_share_one_exact_local_object_tuple():
    target = row("object", component="human", system="local_object")
    other = deepcopy(target)
    other["component"] = "service"
    caller = row(
        "caller", component="human", document={"reference": target["source"]}, at="2027-02-01"
    )
    result = check_links([target, other, caller])
    assert len(result["checked"]) == 1
    assert not result["unresolved"]


def test_observed_expiry_exception_is_not_marked_observed_only():
    r = row("CHECKPOINT", component="lifecycle", system="access_reconciliation")
    got = sample_observation(
        r, {"worker": {"checkpoint_active_channels": ["application_session"]}}, "task"
    )
    assert got["status"] == "EXCEPTION_RECORDED"
    assert "application_session" in got["observation"]


def test_current_correction_does_not_erase_initial_expiry_sample_exception():
    r = row("FINAL-PROBES", component="lifecycle", system="access_reconciliation")
    got = sample_observation(
        r,
        {
            "worker": {
                "checkpoint_active_channels": ["application_session"],
                "final_active_channels": [],
            }
        },
        "task",
    )
    assert got["status"] == "OBSERVED"
    assert "application_session" in got["observation"]


def test_fully_performed_implementation_failure_and_partial_toe_are_distinct():
    base = {
        "control_id": "SH-IAM-003",
        "id": "example",
        "title": "Mover rights",
        "kind": "IMPLEMENTATION",
    }
    result = {"movers": [{"exception": True}]}
    criteria = {"SH-IAM-003": {"procedure": "Remove obsolete rights"}}
    actual = task_evaluation(base, result, criteria)
    assert (actual["status"], actual["conclusion"]) == ("COMPLETE", "FAIL")
    base["kind"] = "TOE"
    actual = task_evaluation(base, result, criteria)
    assert (actual["status"], actual["conclusion"]) == ("IN_PROGRESS", "LIMITATION")
    assert actual["independent_review"] == "RESERVED_NOT_PERFORMED"


@pytest.mark.parametrize(
    "trigger",
    ["no_version_update", "no_version_delete", "no_collection_update", "no_collection_delete"],
)
def test_missing_immutable_trigger_rejected_even_if_db_hash_resealed(tmp_path, trigger):
    folder = tmp_path / "source"
    folder.mkdir(mode=0o700)
    store = CompanyStore(folder)
    immutable_schema(store.path)
    with store._db() as db:
        db.execute("DROP TRIGGER " + trigger)
    with pytest.raises(ProcedureError, match="immutable.*triggers"):
        immutable_schema(store.path)


def test_same_name_noop_immutable_trigger_is_rejected(tmp_path):
    folder = tmp_path / "source"
    folder.mkdir(mode=0o700)
    store = CompanyStore(folder)
    with store._db() as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "CREATE TRIGGER no_version_update BEFORE UPDATE ON versions BEGIN SELECT1; END".replace(
                "SELECT1", "SELECT 1"
            )
        )
    with pytest.raises(ProcedureError, match="immutable.*triggers"):
        immutable_schema(store.path)


def test_receipt_provenance_is_retained_without_repeating_it_as_sample_observation():
    r = row("CHECKPOINT", component="lifecycle")
    native = {**r["source"], "component": r["component"], "content": b"{}"}
    artifact = {
        "id": "artifact",
        "sha256": "1" * 64,
        "version": 1,
        "status": "AVAILABLE",
        "source": {"receipt": {"source": {**r["source"], "provenance": "x" * 600_000}}},
    }
    got = projected(native, artifact)
    assert got["receipt"]["source"]["provenance"] == "x" * 600_000
    trace = sample_observation(got, {"worker": {"checkpoint_active_channels": []}}, "task")
    assert "provenance" not in json.loads(trace["observation"])["native"]
    assert len(trace["observation"]) < 8000


def test_quarantined_source_remains_unavailable_even_when_byte_checks_succeed():
    r = row("CHECKPOINT", component="lifecycle")
    r.update(artifact_id="artifact", artifact_sha256="1" * 64, artifact_status="QUARANTINED")
    item = sample_items([r], {"worker": {"checkpoint_active_channels": []}}, "task")[0]
    assert item["status"] == "SUPPORT_UNAVAILABLE"
    assert item["evidence"] == []


def neutral_trace():
    evidence = [row("CHECKPOINT", component="lifecycle")]
    evidence[0].update(
        artifact_id="artifact", artifact_sha256="1" * 64, artifact_status="AVAILABLE"
    )
    result = {"worker": {"checkpoint_active_channels": ["application_session"]}}
    rows = population_rows(evidence)
    scope = {
        "boundary_id": "corporate",
        "unit": "SVC-identity",
        "timezone": "UTC",
        "period_start": "2027-01-01T00:00:00Z",
        "period_end": "2027-12-31T23:59:59.999999Z",
    }
    pop = populations.create_population(
        "population",
        2,
        rows,
        scope=scope,
        status="READY_FOR_PURPOSE",
        source={
            "source_id": "source",
            "query": "native version census",
            "original_sha256": "1" * 64,
            "completeness_representation": "selected scope",
            "excluded_ids": [],
            "reliability_purpose": "census",
            "reliability_rationale": "exact source membership",
            "reliability_actor": "performer",
            "observable_source_ref": "artifact",
        },
    )
    chosen = populations.select(
        pop, selection_id="selection", method="ENTIRE", purpose="census", rationale="all rows"
    )
    final = {
        "scope": {"period_start": "2027-01-01", "period_end": "2027-12-31"},
        "populations": [{"id": pop.id, "rows": rows, "immutable": asdict(pop)}],
        "selections": [{"id": chosen.id, "immutable": asdict(chosen)}],
    }
    paper = {"id": "workpaper", "versions": [{"version": 1, "text": "actual observation"}]}
    evaluation = {"performed_procedure": "Inspect actual channel state after expiry"}
    trace = {
        "task_id": "task",
        "population_id": pop.id,
        "population_digest": pop.sha256,
        "selection_id": chosen.id,
        "selection_digest": chosen.sha256,
        "task_digest": "2" * 64,
        "workpaper_id": paper["id"],
        "workpaper_version": 1,
        "workpaper_digest": digest(paper["versions"][0]),
        "procedure": evaluation["performed_procedure"],
        "scope": final["scope"],
        "scope_digest": digest(final["scope"]),
        "independent_review": "NOT_PERFORMED",
        "automatic_testing_credit": False,
        "predecessor_id": None,
        "revision": 1,
        "parent_lineage": [],
        "items": [
            {
                **sample_items(evidence, result, "task")[0],
                "item_digest": digest(rows[0]),
                "selection_basis": "SAMPLED",
                "locator_validation": "AUTHOR_SUPPLIED_NOT_CONTENT_MATCH_VERIFIED",
            }
        ],
    }
    return final, trace, paper, evidence, result, evaluation, "2" * 64


@pytest.mark.parametrize("mutation", ["omit", "observation", "status", "support", "row", "digest"])
def test_independent_sample_trace_rejects_resealed_item_and_population_changes(mutation):
    args = neutral_trace()
    verify_sample_trace(*args)
    final, trace, _, _, _, _, _ = args
    if mutation == "omit":
        trace["items"] = []
    elif mutation == "observation":
        trace["items"][0]["observation"] = "All channels removed"
    elif mutation == "status":
        trace["items"][0]["status"] = "OBSERVED"
    elif mutation == "support":
        trace["items"][0]["evidence"][0]["sha256"] = "3" * 64
    elif mutation == "row":
        final["populations"][0]["rows"] = []
    else:
        trace["workpaper_digest"] = "3" * 64
    with pytest.raises(ProcedureError, match="population|sampled|Pinned"):
        verify_sample_trace(*args)
