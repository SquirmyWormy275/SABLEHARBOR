"""Held PRD concern source changes only three unsent authored discovery actions."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import unsupported_121_pbc_plan_v13 as plan

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
STEM = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V13_2026-10-01"


@pytest.fixture(scope="module")
def inputs():
    return (
        json.loads((REPOSITORY / plan.V12_PLAN).read_bytes()),
        json.loads((PRIVATE / plan.ROUTE_LEDGER).read_bytes()),
        json.loads((PRIVATE / plan.SOURCE_RECEIPT).read_bytes()),
    )


@pytest.fixture(scope="module")
def draft(inputs):
    return plan._extend(*inputs, plan.P1_FREEZE)


@pytest.fixture(scope="module")
def built():
    return plan.build(REPOSITORY, PRIVATE)


def test_every_v12_row_group_contact_and_original_request_field_remains(inputs, draft):
    old, _, _ = inputs
    for collection, count in (("rows", 242), ("request_groups", 30), ("group_delta", 30)):
        assert len(old[collection]) == len(draft[collection]) == count
        for previous, current in zip(old[collection], draft[collection], strict=True):
            assert all(current[key] == value for key, value in previous.items())
    assert draft["candidate_owner_source_queues"] == old["candidate_owner_source_queues"]
    assert draft["nonoccurrence_acceptance_protocol"] == old["nonoccurrence_acceptance_protocol"]
    assert draft["reviewed_route_roster"] == old["reviewed_route_roster"]
    assert all(group["request_status"] == "DRAFT_NOT_SENT" for group in draft["request_groups"])


def test_exact_prd_originals_and_only_three_draft_actions(inputs, draft):
    old, ledger, receipt = inputs
    for side, scenario, count in (("A", "CLEAN", 8), ("B", "MESSY", 13)):
        rows = [row for row in draft["rows"] if row["side"] == side]
        assert {row["task_id"] for row in rows if row["v13_reviewed_source_ids"]} == set(plan.TASKS)
        refs = [
            {key: native[key] for key in plan.REF_FIELDS} for native in receipt["records"][scenario]
        ]
        assert len(refs) == count
        for group, task in zip(plan.GROUPS, plan.TASKS, strict=True):
            row = next(row for row in rows if row["task_id"] == task)
            old_row = next(
                row for row in old["rows"] if row["side"] == side and row["task_id"] == task
            )
            route_row = next(
                row for row in ledger["rows"] if row["side"] == side and row["task_id"] == task
            )
            assert row["control_id"] == row["request_group_id"] == group
            assert row["v13_reviewed_source_ids"] == [plan.SOURCE]
            assert row["v13_targeted_source_ids"] == [
                *old_row["v12_targeted_source_ids"],
                plan.SOURCE,
            ]
            assert row["v13_targeted_source_ids"] == route_row["targeted_integrated_source_ids"]
            assert row["v13_source_limits"] == {plan.SOURCE: plan.SOURCE_LIMIT}
            assert row["v13_source_record_refs"] == {plan.SOURCE: refs}
            assert route_row["v15_source_record_refs"] == {plan.SOURCE: refs}
            assert row["authored_test_clause"] == plan.route.CLAUSE
            assert row["current_task_status"] == "NOT_STARTED"
            assert row["current_task_conclusion"] == "NOT_RUN"
            assert row["task_credit"] is False
            assert route_row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
            assert route_row["audit_task_credit"] is False
    for name in plan.GROUPS:
        old_group = next(g for g in old["request_groups"] if g["request_group_id"] == name)
        group = next(g for g in draft["request_groups"] if g["request_group_id"] == name)
        assert group["candidate_contact_person_id"] == old_group["candidate_contact_person_id"]
        assert (
            group["requested_originals_or_decision"] == old_group["requested_originals_or_decision"]
        )
        assert group["v13_next_action"].startswith(old_group["v12_next_action"] + " ")
        assert "claimant" in group["v13_next_action"]
    assert {
        g["request_group_id"]
        for g in draft["request_groups"]
        if g["v13_next_action_changed_from_v12"]
    } == set(plan.GROUPS)


def test_denominators_held_gates_and_no_credit(inputs, draft):
    old, ledger, receipt = inputs
    assert ledger["counts"]["A"]["targeted_integrated_route_count"] == 175
    assert receipt["selected_claimant_verified"] is False
    assert receipt["fictional_accepted_deliveries"] == 0
    assert receipt["customer_acknowledgments"] == 0
    assert receipt["local_open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert draft["counts"]["A"] == draft["counts"]["B"]
    for side in "AB":
        previous = old["counts"][side]
        counts = draft["counts"][side]
        assert previous["v12_cumulative_reviewed_source_affected_unsupported_clauses"] == 24
        assert previous["v12_cumulative_targeted_unsupported_clauses"] == 35
        assert counts["v13_new_reviewed_source_leads"] == 3
        assert counts["v13_newly_source_affected_unsupported_clauses"] == 3
        assert counts["v13_newly_route_targeted_unsupported_clauses"] == 0
        assert counts["v13_cumulative_reviewed_source_affected_unsupported_clauses"] == 27
        assert counts["v13_cumulative_targeted_unsupported_clauses"] == 35
        assert counts["v13_cumulative_changed_request_groups"] == 15
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


def test_source_route_or_no_event_drift_fails_closed(inputs):
    old, ledger, receipt = inputs
    changed = deepcopy(receipt)
    changed["selected_claimant_verified"] = True
    with pytest.raises(plan.V13SourceRequestError, match="scope differs"):
        plan._extend(old, ledger, changed, plan.P1_FREEZE)
    changed = deepcopy(receipt)
    changed["fictional_accepted_deliveries"] = 1
    with pytest.raises(plan.V13SourceRequestError, match="scope differs"):
        plan._extend(old, ledger, changed, plan.P1_FREEZE)
    changed = deepcopy(ledger)
    next(row for row in changed["rows"] if row["side"] == "B" and row["task_id"] == plan.TASKS[1])[
        "classification"
    ] = "SOURCE_CANDIDATE_PARTIAL"
    with pytest.raises(plan.V13SourceRequestError, match="authored route"):
        plan._extend(old, changed, receipt, plan.P1_FREEZE)
    changed_old = deepcopy(old)
    next(
        row
        for row in changed_old["rows"]
        if row["side"] == "A" and row["possible_nonoccurrence_review_candidate"]
    )["accepted_nonoccurrence_status"] = "ACCEPTED"
    with pytest.raises(plan.V13SourceRequestError, match="task/request"):
        plan._extend(changed_old, ledger, receipt, plan.P1_FREEZE)


def test_review_pin_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(plan.PINS, plan.V12_PLAN, "0" * 64)
    with pytest.raises(plan.pinned.SourceRequestError, match="Pinned input differs"):
        plan.build(REPOSITORY, PRIVATE)


def test_build_reproduces_tracked_artifacts_and_review_pins(built):
    assert built == json.loads(STEM.with_suffix(".json").read_bytes())
    assert plan.markdown(built) == STEM.with_suffix(".md").read_text()
    assert built["source_pins"][plan.V12_REVIEW] == plan.PINS[plan.V12_REVIEW]
    assert built["source_pins"][plan.ROUTE_REVIEW] == plan.PINS[plan.ROUTE_REVIEW]
    assert built["source_pins"][plan.SOURCE_REVIEW] == plan.PINS[plan.SOURCE_REVIEW]
