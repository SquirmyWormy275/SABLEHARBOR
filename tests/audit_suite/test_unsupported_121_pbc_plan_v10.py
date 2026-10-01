"""POL004 source adds only one draft discovery lead to the V9 PBC plan."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import unsupported_121_pbc_plan_v10 as plan

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
STEM = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V10_2026-09-30"


@pytest.fixture(scope="module")
def inputs():
    return (
        json.loads((REPOSITORY / plan.V9_PLAN).read_bytes()),
        json.loads((PRIVATE / plan.SOURCE_RECEIPT).read_bytes()),
    )


@pytest.fixture(scope="module")
def draft(inputs):
    return plan._extend(*inputs, plan.P1_FREEZE)


@pytest.fixture(scope="module")
def built():
    return plan.build(REPOSITORY, PRIVATE)


def test_exact_v9_rows_groups_contacts_and_original_requests_remain(inputs, draft):
    old, _ = inputs
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


def test_exact_pol004_lead_and_single_draft_action(inputs, draft):
    old, source = inputs
    for side, branch, count in (
        ("A", "POL004-PROCEDURE-CLEAN", 7),
        ("B", "POL004-PROCEDURE-MESSY", 9),
    ):
        rows = [row for row in draft["rows"] if row["side"] == side]
        assert {row["task_id"] for row in rows if row["v10_reviewed_source_ids"]} == {plan.TASK}
        row = next(row for row in rows if row["task_id"] == plan.TASK)
        old_row = next(
            row for row in old["rows"] if row["side"] == side and row["task_id"] == plan.TASK
        )
        assert row["v10_reviewed_source_ids"] == [plan.SOURCE]
        assert row["v10_targeted_source_ids"] == old_row["v9_targeted_source_ids"] == []
        assert row["v10_source_limits"] == {plan.SOURCE: plan.SOURCE_LIMIT}
        assert row["v10_source_record_refs"][plan.SOURCE] == [
            {key: native[key] for key in plan.REF_FIELDS}
            for native in source["native_originals"]
            if native["branch"] == branch
        ]
        assert len(row["v10_source_record_refs"][plan.SOURCE]) == count
        assert row["authored_test_clause"] == plan.procedure.CLAUSE
        assert row["current_task_status"] == "NOT_STARTED"
        assert row["current_task_conclusion"] == "NOT_RUN"
        assert row["task_credit"] is False
        assert source["route_disposition"][side]["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    old_group = next(g for g in old["request_groups"] if g["request_group_id"] == plan.GROUP)
    group = next(g for g in draft["request_groups"] if g["request_group_id"] == plan.GROUP)
    assert group["candidate_contact_person_id"] == old_group["candidate_contact_person_id"]
    assert group["requested_originals_or_decision"] == old_group["requested_originals_or_decision"]
    assert group["v10_next_action"].startswith(old_group["v9_next_action"] + " ")
    assert "broader policy remains OPEN" in group["v10_next_action"]
    assert "fictional v0.2 procedure approval is pending" in group["v10_next_action"]
    assert {
        g["request_group_id"]
        for g in draft["request_groups"]
        if g["v10_next_action_changed_from_v9"]
    } == {plan.GROUP}


def test_unique_affected_denominators_and_no_credit(inputs, draft):
    old, source = inputs
    assert source["enterprise_policy_status_2026"] == "OPEN"
    assert source["design_standard_approved_only"] is True
    assert source["procedure_authority"] == "PENDING_AUTHORIZED_DECISION"
    assert source["messy_false_close_corrected"] is True
    assert source["messy_missed_interval_retained"] is True
    assert source["messy_exception_open"] is True
    assert draft["counts"]["A"] == draft["counts"]["B"]
    for side in "AB":
        previous = old["counts"][side]
        counts = draft["counts"][side]
        assert previous["v9_cumulative_reviewed_source_affected_unsupported_clauses"] == 22
        assert previous["v9_cumulative_targeted_unsupported_clauses"] == 34
        assert counts["v10_new_reviewed_source_leads"] == 1
        assert counts["v10_newly_source_affected_unsupported_clauses"] == 1
        assert counts["v10_cumulative_reviewed_source_affected_unsupported_clauses"] == 23
        assert counts["v10_cumulative_targeted_unsupported_clauses"] == 34
        assert counts["v10_cumulative_changed_request_groups"] == 11
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


def test_authority_route_or_no_event_drift_fails_closed(inputs):
    old, source = inputs
    changed = deepcopy(source)
    changed["procedure_authority"] = "APPROVED"
    with pytest.raises(plan.V10SourceRequestError, match="authority or scope"):
        plan._extend(old, changed, plan.P1_FREEZE)
    changed = deepcopy(source)
    changed["route_disposition"]["B"]["classification"] = "PARTIAL_SOURCE"
    with pytest.raises(plan.V10SourceRequestError, match="route join differs"):
        plan._extend(old, changed, plan.P1_FREEZE)
    changed_old = deepcopy(old)
    next(
        row
        for row in changed_old["rows"]
        if row["side"] == "A" and row["possible_nonoccurrence_review_candidate"]
    )["accepted_nonoccurrence_status"] = "ACCEPTED"
    with pytest.raises(plan.V10SourceRequestError, match="task/request"):
        plan._extend(changed_old, source, plan.P1_FREEZE)


def test_review_pin_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(plan.PINS, plan.SOURCE_REVIEW, "0" * 64)
    with pytest.raises(plan.pinned.SourceRequestError, match="Pinned input differs"):
        plan.build(REPOSITORY, PRIVATE)


def test_build_reproduces_tracked_artifacts_and_review_pins(built):
    assert built == json.loads(STEM.with_suffix(".json").read_bytes())
    assert plan.markdown(built) == STEM.with_suffix(".md").read_text()
    assert built["source_pins"][plan.V9_REVIEW] == plan.PINS[plan.V9_REVIEW]
    assert built["source_pins"][plan.SOURCE_REVIEW] == plan.PINS[plan.SOURCE_REVIEW]
    assert built["source_pins"][plan.SOURCE_DB] == plan.PINS[plan.SOURCE_DB]
