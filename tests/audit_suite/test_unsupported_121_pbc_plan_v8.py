"""Conditional LEG001 matter leads change one draft PBC group, without credit."""

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import unsupported_121_pbc_plan_v8 as plan

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def inputs():
    old_path = REPOSITORY / plan.V7_PLAN
    route_path = REPOSITORY / plan.V8_LEDGER
    assert hashlib.sha256(old_path.read_bytes()).hexdigest() == plan.PINS[plan.V7_PLAN]
    assert hashlib.sha256(route_path.read_bytes()).hexdigest() == plan.PINS[plan.V8_LEDGER]
    return json.loads(old_path.read_text()), json.loads(route_path.read_text())


@pytest.fixture(scope="module")
def draft(inputs):
    return plan._extend(*inputs, plan.P1_FREEZE)


@pytest.fixture(scope="module")
def reviewed():
    return plan.build(REPOSITORY, PRIVATE)


def test_reviewed_main_joins_reproduce_exact_isolated_draft(reviewed, draft):
    stem = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V8_2026-09-30"
    assert reviewed == draft == json.loads(stem.with_suffix(".json").read_text())
    assert plan.markdown(reviewed) == stem.with_suffix(".md").read_text()
    assert reviewed["source_pins"][plan.V8_REVIEW] == plan.PINS[plan.V8_REVIEW]


def test_main_review_gate_fails_closed_if_pin_is_removed(monkeypatch):
    assert plan.PINS[plan.V8_REVIEW] == (
        "3587f7ec4fe0082a8f93d6e0565f6758a1f7b4bc0d6e43c8bd47cb7b012f86ea"
    )
    monkeypatch.setitem(plan.PINS, plan.V8_REVIEW, "PENDING_INDEPENDENT_MAIN_REVIEW")
    with pytest.raises(plan.V8SourceRequestError, match="review pin is pending"):
        plan.build(REPOSITORY, PRIVATE)


def test_draft_preserves_all_v7_rows_groups_contacts_and_original_requests(inputs, draft):
    old, _ = inputs
    assert len(draft["rows"]) == len(old["rows"]) == 242
    assert len(draft["request_groups"]) == len(draft["group_delta"]) == 30
    for before, after in zip(old["rows"], draft["rows"], strict=True):
        assert all(after[key] == value for key, value in before.items())
        assert after["pbc_request_status"] == "DRAFT_NOT_SENT"
        assert after["current_task_status"] == "NOT_STARTED"
        assert after["current_task_conclusion"] == "NOT_RUN"
        assert after["task_credit"] is False
    for name in ("request_groups", "group_delta"):
        for before, after in zip(old[name], draft[name], strict=True):
            assert all(after[key] == value for key, value in before.items())
    assert draft["candidate_owner_source_queues"] == old["candidate_owner_source_queues"]
    assert draft["nonoccurrence_acceptance_protocol"] == old["nonoccurrence_acceptance_protocol"]
    assert draft["external_messages_sent"] == draft["accepted_na_determinations"] == 0
    assert draft["audit_task_credit"] is draft["active_pair_mutated"] is False


def test_only_two_conditional_matter_clauses_and_one_group_gain_v8_leads(draft):
    assert draft["counts"]["A"] == draft["counts"]["B"]
    for side in "AB":
        rows = [row for row in draft["rows"] if row["side"] == side]
        assert len(rows) == len({row["task_id"] for row in rows}) == 121
        assert {row["task_id"] for row in rows if row["v8_reviewed_source_ids"]} == (
            plan.NEW_SOURCE_TASKS
        )
        assert Counter(
            row["request_group_id"] for row in rows if row["control_id"] == "SH-LEG-001"
        ) == {"SH-LEG-001/PROVISION": 16, "SH-LEG-001/CONTEXT": 4, "SH-LEG-001/MATTER": 46}
        assert sum(row["possible_nonoccurrence_review_candidate"] for row in rows) == 53
        assert all(
            row["accepted_nonoccurrence_status"] == "NOT_ESTABLISHED"
            for row in rows
            if row["possible_nonoccurrence_review_candidate"]
        )
        for row in rows:
            selected = row["task_id"] in plan.NEW_SOURCE_TASKS
            assert row["v8_reviewed_source_ids"] == ([plan.SOURCE] if selected else [])
            assert set(row["v8_source_limits"]) == ({plan.SOURCE} if selected else set())
            assert row["v8_next_action_changed_from_v7"] == (
                row["request_group_id"] == plan.NEW_SOURCE_GROUP
            )
            if selected:
                assert row["authored_test_clause"]
                assert row["possible_nonoccurrence_review_candidate"] is True
                assert row["accepted_nonoccurrence_status"] == "NOT_ESTABLISHED"
                assert len(row["v8_source_record_refs"][plan.SOURCE]) == 2
        counts = draft["counts"][side]
        assert counts["v8_new_legal_source_affected_unsupported_clauses"] == 2
        assert counts["v8_cumulative_reviewed_source_affected_unsupported_clauses"] == 21
        assert counts["v8_cumulative_targeted_unsupported_clauses"] == 33
        assert counts["v8_next_action_changes_from_v7"] == 1
    assert {
        group["request_group_id"]
        for group in draft["request_groups"]
        if group["v8_reviewed_source_ids"]
    } == {plan.NEW_SOURCE_GROUP}
    assert sum(group["v8_next_action_changed_from_v7"] for group in draft["request_groups"]) == 1
    for group in draft["request_groups"]:
        assert group["request_status"] == "DRAFT_NOT_SENT"
        assert group["task_credit"] is False
        if group["request_group_id"] == plan.NEW_SOURCE_GROUP:
            assert "all-company or outside-matter population" in group["v8_next_action"]
            assert "independent challenge" in group["v8_next_action"]
        else:
            assert group["v8_next_action"] == group["v7_next_action"]


def test_extra_unsupported_lead_fails_closed(inputs):
    old, ledger = inputs
    changed = deepcopy(ledger)
    row = next(
        row
        for row in changed["rows"]
        if row["side"] == "A" and row["task_id"] == "TASK-SH-LEG-001-corporate-CHECK-HIPAA:160.308"
    )
    row["v8_reviewed_source_ids"] = [plan.SOURCE]
    row["v8_source_limits"] = {plan.SOURCE: plan.routes_v8.LIMIT}
    row["v8_source_record_refs"] = {plan.SOURCE: []}
    with pytest.raises(plan.V8SourceRequestError, match="Unsupported V8 clause/source drift"):
        plan._extend(old, changed, plan.P1_FREEZE)


def test_false_no_matter_acceptance_and_wrong_native_lead_fail_closed(inputs):
    old, ledger = inputs
    accepted = deepcopy(old)
    row = next(
        row
        for row in accepted["rows"]
        if row["side"] == "A" and row["task_id"] in plan.NEW_SOURCE_TASKS
    )
    row["accepted_nonoccurrence_status"] = "ACCEPTED"
    with pytest.raises(plan.V8SourceRequestError, match="Unsupported V8 clause/source drift"):
        plan._extend(accepted, ledger, plan.P1_FREEZE)
    wrong = deepcopy(ledger)
    row = next(
        row
        for row in wrong["rows"]
        if row["side"] == "B" and row["task_id"] == "TASK-SH-LEG-001-corporate-CHECK-HIPAA:160.504"
    )
    row["v8_source_record_refs"][plan.SOURCE][0]["record"] = "PROVISION-07"
    with pytest.raises(plan.V8SourceRequestError, match="Selected conditional matter native lead"):
        plan._extend(old, wrong, plan.P1_FREEZE)


def test_markdown_keeps_draft_and_conditional_boundary(draft):
    text = plan.markdown(draft)
    assert "121 unsupported" in text
    assert "160.306" in text and "160.504" in text
    assert "other 44 matter clauses" in text
    assert "DRAFT_NOT_SENT" in text
    assert draft["accepted_na_determinations"] == 0
