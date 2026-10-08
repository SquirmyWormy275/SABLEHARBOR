"""Emergency replay changes one draft action and reconciles exact V13 route targets."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import unsupported_121_pbc_plan_v11 as plan

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V11_2026-09-30"


@pytest.fixture(scope="module")
def inputs():
    return (
        json.loads((REPOSITORY / plan.V10_PLAN).read_bytes()),
        json.loads((PRIVATE / plan.ROUTE_LEDGER).read_bytes()),
        json.loads((PRIVATE / plan.SOURCE_RECEIPT).read_bytes()),
    )


@pytest.fixture(scope="module")
def draft(inputs):
    return plan._extend(*inputs, plan.P1_FREEZE)


@pytest.fixture(scope="module")
def built():
    return plan.build(REPOSITORY, PRIVATE)


def test_every_v10_row_group_contact_and_original_request_field_remains(inputs, draft):
    old, _, _ = inputs
    assert len(old["rows"]) == len(draft["rows"]) == 242
    assert len(old["request_groups"]) == len(draft["request_groups"]) == 30
    assert len(old["group_delta"]) == len(draft["group_delta"]) == 30
    for collection in ("rows", "request_groups", "group_delta"):
        for previous, current in zip(old[collection], draft[collection], strict=True):
            assert all(current[key] == value for key, value in previous.items())
    assert draft["candidate_owner_source_queues"] == old["candidate_owner_source_queues"]
    assert draft["nonoccurrence_acceptance_protocol"] == old["nonoccurrence_acceptance_protocol"]
    assert draft["reviewed_route_roster"] == old["reviewed_route_roster"]
    assert all(group["request_status"] == "DRAFT_NOT_SENT" for group in draft["request_groups"])


def test_exact_emergency_originals_route_and_one_draft_action(inputs, draft):
    old, ledger, receipt = inputs
    for side, scenario, branch, count in (
        ("A", "CLEAN", "EMERGENCY-REPLAY-CLEAN", 8),
        ("B", "MESSY", "EMERGENCY-REPLAY-MESSY", 15),
    ):
        rows = [row for row in draft["rows"] if row["side"] == side]
        assert {row["task_id"] for row in rows if row["v11_reviewed_source_ids"]} == {plan.TASK}
        row = next(row for row in rows if row["task_id"] == plan.TASK)
        old_row = next(
            row for row in old["rows"] if row["side"] == side and row["task_id"] == plan.TASK
        )
        route_row = next(
            row for row in ledger["rows"] if row["side"] == side and row["task_id"] == plan.TASK
        )
        assert row["v11_reviewed_source_ids"] == [plan.SOURCE]
        assert row["v11_targeted_source_ids"] == route_row["targeted_integrated_source_ids"]
        assert row["v11_targeted_source_ids"] == [*old_row["v10_targeted_source_ids"], plan.SOURCE]
        assert row["v11_source_limits"] == {plan.SOURCE: plan.SOURCE_LIMIT}
        assert row["v11_source_record_refs"][plan.SOURCE] == [
            {key: native[key] for key in plan.REF_FIELDS} for native in receipt["records"][scenario]
        ]
        assert len(row["v11_source_record_refs"][plan.SOURCE]) == count
        assert all(ref["branch"] == branch for ref in row["v11_source_record_refs"][plan.SOURCE])
        assert row["authored_test_clause"] == plan.route.CLAUSE
        assert row["current_task_status"] == "NOT_STARTED"
        assert row["current_task_conclusion"] == "NOT_RUN"
        assert row["task_credit"] is False
        assert route_row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
        pol = next(row for row in rows if row["task_id"] == plan.POL004_TASK)
        assert pol["v10_targeted_source_ids"] == []
        assert pol["v11_targeted_source_ids"] == [plan.POL004_SOURCE]
        assert pol["v11_reviewed_source_ids"] == []
    old_group = next(g for g in old["request_groups"] if g["request_group_id"] == plan.GROUP)
    group = next(g for g in draft["request_groups"] if g["request_group_id"] == plan.GROUP)
    assert group["candidate_contact_person_id"] == old_group["candidate_contact_person_id"]
    assert group["requested_originals_or_decision"] == old_group["requested_originals_or_decision"]
    assert group["v11_next_action"].startswith(old_group["v10_next_action"] + " ")
    assert "BA-flowdown, BCM capacity/BIA, IAM and SEC005" in group["v11_next_action"]
    assert {
        g["request_group_id"]
        for g in draft["request_groups"]
        if g["v11_next_action_changed_from_v10"]
    } == {plan.GROUP}


def test_denominators_and_no_credit(inputs, draft):
    old, ledger, receipt = inputs
    assert ledger["counts"]["A"]["targeted_integrated_route_count"] == 175
    assert receipt["local_open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert draft["counts"]["A"] == draft["counts"]["B"]
    for side in "AB":
        previous = old["counts"][side]
        counts = draft["counts"][side]
        assert previous["v10_cumulative_reviewed_source_affected_unsupported_clauses"] == 23
        assert previous["v10_cumulative_targeted_unsupported_clauses"] == 34
        assert counts["v11_new_reviewed_source_leads"] == 1
        assert counts["v11_newly_source_affected_unsupported_clauses"] == 0
        assert counts["v11_newly_route_targeted_unsupported_clauses"] == 1
        assert counts["v11_cumulative_reviewed_source_affected_unsupported_clauses"] == 23
        assert counts["v11_cumulative_targeted_unsupported_clauses"] == 35
        assert counts["v11_cumulative_changed_request_groups"] == 11
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
    changed["messy_upstream_gates_remain_open"] = False
    with pytest.raises(plan.V11SourceRequestError, match="scope differs"):
        plan._extend(old, ledger, changed, plan.P1_FREEZE)
    changed = deepcopy(ledger)
    next(row for row in changed["rows"] if row["side"] == "B" and row["task_id"] == plan.TASK)[
        "classification"
    ] = "SOURCE_CANDIDATE_PARTIAL"
    with pytest.raises(plan.V11SourceRequestError, match="authored route"):
        plan._extend(old, changed, receipt, plan.P1_FREEZE)
    changed = deepcopy(ledger)
    next(
        row for row in changed["rows"] if row["side"] == "A" and row["task_id"] == plan.POL004_TASK
    )["targeted_integrated_source_ids"] = []
    with pytest.raises(plan.V11SourceRequestError, match="POL004 route target"):
        plan._extend(old, changed, receipt, plan.P1_FREEZE)
    changed_old = deepcopy(old)
    next(
        row
        for row in changed_old["rows"]
        if row["side"] == "A" and row["possible_nonoccurrence_review_candidate"]
    )["accepted_nonoccurrence_status"] = "ACCEPTED"
    with pytest.raises(plan.V11SourceRequestError, match="task/request"):
        plan._extend(changed_old, ledger, receipt, plan.P1_FREEZE)


def test_review_pin_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(plan.PINS, plan.ROUTE_REVIEW, "0" * 64)
    with pytest.raises(plan.pinned.SourceRequestError, match="Pinned input differs"):
        plan.build(REPOSITORY, PRIVATE)


def test_build_reproduces_tracked_artifacts_and_review_pins(built):
    assert built == json.loads(STEM.with_suffix(".json").read_bytes())
    assert plan.markdown(built) == STEM.with_suffix(".md").read_text()
    assert built["source_pins"][plan.V10_REVIEW] == plan.PINS[plan.V10_REVIEW]
    assert built["source_pins"][plan.ROUTE_REVIEW] == plan.PINS[plan.ROUTE_REVIEW]
    assert built["source_pins"][plan.SOURCE_REVIEW] == plan.PINS[plan.SOURCE_REVIEW]
