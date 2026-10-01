"""Selected ENG005 originals add one unsent draft discovery lead, without task credit."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import unsupported_121_pbc_plan_v12 as plan

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
STEM = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V12_2026-09-30"


@pytest.fixture(scope="module")
def inputs():
    return (
        json.loads((REPOSITORY / plan.V11_PLAN).read_bytes()),
        json.loads((PRIVATE / plan.ROUTE_LEDGER).read_bytes()),
        json.loads((PRIVATE / plan.SOURCE_RECEIPT).read_bytes()),
    )


@pytest.fixture(scope="module")
def draft(inputs):
    return plan._extend(*inputs, plan.P1_FREEZE)


@pytest.fixture(scope="module")
def built():
    return plan.build(REPOSITORY, PRIVATE)


def test_every_v11_row_group_contact_and_original_request_field_remains(inputs, draft):
    old, _, _ = inputs
    for collection, count in (("rows", 242), ("request_groups", 30), ("group_delta", 30)):
        assert len(old[collection]) == len(draft[collection]) == count
        for previous, current in zip(old[collection], draft[collection], strict=True):
            assert all(current[key] == value for key, value in previous.items())
    assert draft["candidate_owner_source_queues"] == old["candidate_owner_source_queues"]
    assert draft["nonoccurrence_acceptance_protocol"] == old["nonoccurrence_acceptance_protocol"]
    assert draft["reviewed_route_roster"] == old["reviewed_route_roster"]
    assert all(group["request_status"] == "DRAFT_NOT_SENT" for group in draft["request_groups"])


def test_exact_eng005_originals_route_and_one_draft_action(inputs, draft):
    old, ledger, receipt = inputs
    for side, scenario, count in (("A", "CLEAN", 12), ("B", "MESSY", 22)):
        rows = [row for row in draft["rows"] if row["side"] == side]
        assert {row["task_id"] for row in rows if row["v12_reviewed_source_ids"]} == {plan.TASK}
        row = next(row for row in rows if row["task_id"] == plan.TASK)
        old_row = next(
            row for row in old["rows"] if row["side"] == side and row["task_id"] == plan.TASK
        )
        route_row = next(
            row for row in ledger["rows"] if row["side"] == side and row["task_id"] == plan.TASK
        )
        assert row["v12_reviewed_source_ids"] == [plan.SOURCE]
        assert row["v12_targeted_source_ids"] == [*old_row["v11_targeted_source_ids"], plan.SOURCE]
        assert row["v12_targeted_source_ids"] == route_row["targeted_integrated_source_ids"]
        assert row["v12_source_limits"] == {plan.SOURCE: plan.SOURCE_LIMIT}
        refs = [
            {key: native[key] for key in plan.REF_FIELDS}
            for native in receipt["records"][scenario]
        ]
        assert row["v12_source_record_refs"] == {plan.SOURCE: refs}
        assert route_row["v14_source_record_refs"] == {plan.SOURCE: refs}
        assert len(refs) == count
        assert row["authored_test_clause"] == plan.route.CLAUSE
        assert row["current_task_status"] == "NOT_STARTED"
        assert row["current_task_conclusion"] == "NOT_RUN"
        assert row["task_credit"] is False
        assert route_row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
        assert route_row["audit_task_credit"] is False
    old_group = next(g for g in old["request_groups"] if g["request_group_id"] == plan.GROUP)
    group = next(g for g in draft["request_groups"] if g["request_group_id"] == plan.GROUP)
    assert group["candidate_contact_person_id"] == old_group["candidate_contact_person_id"]
    assert group["requested_originals_or_decision"] == old_group["requested_originals_or_decision"]
    assert group["v12_next_action"].startswith(old_group["v11_next_action"] + " ")
    assert "two OPEN historical exceptions" in group["v12_next_action"]
    assert {
        g["request_group_id"]
        for g in draft["request_groups"]
        if g["v12_next_action_changed_from_v11"]
    } == {plan.GROUP}


def test_denominators_open_gates_and_no_credit(inputs, draft):
    old, ledger, receipt = inputs
    assert ledger["counts"]["A"]["targeted_integrated_route_count"] == 175
    assert receipt["open_exception_counts"] == {"CLEAN": 0, "MESSY": 2}
    assert receipt["corporate_emergency_authority_status"] == "NOT_EVIDENCED_OPEN"
    assert draft["counts"]["A"] == draft["counts"]["B"]
    for side in "AB":
        previous = old["counts"][side]
        counts = draft["counts"][side]
        assert previous["v11_cumulative_reviewed_source_affected_unsupported_clauses"] == 23
        assert previous["v11_cumulative_targeted_unsupported_clauses"] == 35
        assert counts["v12_new_reviewed_source_leads"] == 1
        assert counts["v12_newly_source_affected_unsupported_clauses"] == 1
        assert counts["v12_newly_route_targeted_unsupported_clauses"] == 0
        assert counts["v12_cumulative_reviewed_source_affected_unsupported_clauses"] == 24
        assert counts["v12_cumulative_targeted_unsupported_clauses"] == 35
        assert counts["v12_cumulative_changed_request_groups"] == 12
        assert counts["unsupported_exact_clauses"] == 121
        assert counts["possible_nonoccurrence_review_candidates"] == 53
        assert draft["active_p1_tasks"][side] == {
            "task_count": 409,
            "status": "NOT_STARTED",
            "conclusion": "NOT_RUN",
        }
    assert draft["p1_freeze"] == plan.P1_FREEZE
    assert draft["external_messages_sent"] == draft["accepted_na_determinations"] == 0
    assert (
        draft["fresh_pair_created"]
        is draft["audit_task_credit"]
        is draft["source_complete"]
        is False
    )


def test_source_route_no_event_or_target_drift_fails_closed(inputs):
    old, ledger, receipt = inputs
    changed = deepcopy(receipt)
    changed["corporate_emergency_authority_status"] = "EVIDENCED"
    with pytest.raises(plan.V12SourceRequestError, match="scope differs"):
        plan._extend(old, ledger, changed, plan.P1_FREEZE)
    changed = deepcopy(receipt)
    changed["open_exception_counts"]["MESSY"] = 0
    with pytest.raises(plan.V12SourceRequestError, match="scope differs"):
        plan._extend(old, ledger, changed, plan.P1_FREEZE)
    changed = deepcopy(ledger)
    next(row for row in changed["rows"] if row["side"] == "B" and row["task_id"] == plan.TASK)[
        "classification"
    ] = "SOURCE_CANDIDATE_PARTIAL"
    with pytest.raises(plan.V12SourceRequestError, match="authored route"):
        plan._extend(old, changed, receipt, plan.P1_FREEZE)
    changed = deepcopy(ledger)
    next(row for row in changed["rows"] if row["side"] == "A" and row["task_id"] == plan.TASK)[
        "targeted_integrated_source_ids"
    ] = ["ENG005_LOCAL_V1"]
    with pytest.raises(plan.V12SourceRequestError, match="authored route"):
        plan._extend(old, changed, receipt, plan.P1_FREEZE)
    changed_old = deepcopy(old)
    next(
        row
        for row in changed_old["rows"]
        if row["side"] == "A" and row["possible_nonoccurrence_review_candidate"]
    )["accepted_nonoccurrence_status"] = "ACCEPTED"
    with pytest.raises(plan.V12SourceRequestError, match="task/request"):
        plan._extend(changed_old, ledger, receipt, plan.P1_FREEZE)


def test_review_pin_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(plan.PINS, plan.ROUTE_REVIEW, "0" * 64)
    with pytest.raises(plan.pinned.SourceRequestError, match="Pinned input differs"):
        plan.build(REPOSITORY, PRIVATE)


def test_build_reproduces_tracked_artifacts_and_review_pins(built):
    assert built == json.loads(STEM.with_suffix(".json").read_bytes())
    assert plan.markdown(built) == STEM.with_suffix(".md").read_text()
    assert built["source_pins"][plan.V11_REVIEW] == plan.PINS[plan.V11_REVIEW]
    assert built["source_pins"][plan.ROUTE_REVIEW] == plan.PINS[plan.ROUTE_REVIEW]
    assert built["source_pins"][plan.SOURCE_REVIEW] == plan.PINS[plan.SOURCE_REVIEW]
