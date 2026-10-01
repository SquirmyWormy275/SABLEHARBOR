"""Reviewed route V6 adds selected leads without accepting unsupported clauses."""

import json
from collections import Counter
from pathlib import Path

import pytest

from enterprise.audit_suite import unsupported_121_pbc_plan as pinned
from enterprise.audit_suite import unsupported_121_pbc_plan_v6 as plan

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
STEM = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V6_2026-09-30"
V5 = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V5_2026-09-30.json"


@pytest.fixture(scope="module")
def result():
    return plan.build(REPOSITORY, PRIVATE)


def test_exact_successor_preserves_all_historical_rows_groups_and_requests(result):
    old = json.loads(V5.read_text())
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert plan.markdown(result) == STEM.with_suffix(".md").read_text()
    assert result["p1_freeze"] == plan.P1_FREEZE
    assert result["external_messages_sent"] == result["accepted_na_determinations"] == 0
    assert result["fresh_pair_created"] is result["active_pair_mutated"] is False
    assert result["audit_task_credit"] is False
    assert result["active_p1_tasks"] == {
        side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"} for side in "AB"
    }
    assert len(result["rows"]) == len(old["rows"]) == 242
    assert len(result["request_groups"]) == len(result["group_delta"]) == 30
    for before, after in zip(old["rows"], result["rows"], strict=True):
        assert all(after[key] == value for key, value in before.items())
        assert after["pbc_request_status"] == "DRAFT_NOT_SENT"
        assert after["current_task_status"] == "NOT_STARTED"
        assert after["current_task_conclusion"] == "NOT_RUN"
        assert after["task_credit"] is False
    for name in ("request_groups", "group_delta"):
        for before, after in zip(old[name], result[name], strict=True):
            assert all(after[key] == value for key, value in before.items())
    assert result["candidate_owner_source_queues"] == old["candidate_owner_source_queues"]
    assert result["nonoccurrence_acceptance_protocol"] == old["nonoccurrence_acceptance_protocol"]


def test_only_four_selected_clauses_and_three_groups_gain_v6_leads(result):
    for side in "AB":
        rows = [row for row in result["rows"] if row["side"] == side]
        assert len(rows) == len({row["task_id"] for row in rows}) == 121
        assert len({row["control_id"] for row in rows}) == 28
        assert {row["task_id"] for row in rows if row["v6_reviewed_source_ids"]} == set(
            plan.NEW_SOURCE_TASKS
        )
        for row in rows:
            lead = plan.NEW_SOURCE_TASKS.get(row["task_id"])
            assert row["v6_reviewed_source_ids"] == ([lead] if lead else [])
            assert set(row["v6_source_limits"]) == ({lead} if lead else set())
            assert row["v6_next_action_changed_from_v5"] == (
                row["request_group_id"] in plan.NEW_SOURCE_GROUPS
            )
            assert row["accepted_nonoccurrence_status"] != "ACCEPTED"
        assert all(
            row["authored_test_clause"] and row["task_credit"] is False
            for row in rows
            if row["v6_reviewed_source_ids"]
        )
        assert sum(row["possible_nonoccurrence_review_candidate"] for row in rows) == 53
        assert all(
            row["accepted_nonoccurrence_status"] == "NOT_ESTABLISHED"
            for row in rows
            if row["possible_nonoccurrence_review_candidate"]
        )
        assert Counter(
            row["request_group_id"] for row in rows if row["control_id"] == "SH-LEG-001"
        ) == {"SH-LEG-001/PROVISION": 16, "SH-LEG-001/CONTEXT": 4, "SH-LEG-001/MATTER": 46}
        assert result["counts"][side]["source_affected_unsupported_clauses"] == 13
        assert result["counts"][side]["v6_new_source_affected_unsupported_clauses"] == 4
        assert result["counts"][side]["v6_cumulative_source_affected_unsupported_clauses"] == 17
        assert result["counts"][side]["next_action_changes"] == 6
        assert result["counts"][side]["v6_next_action_changes_from_v5"] == 3
    assert {
        g["request_group_id"] for g in result["request_groups"] if g["v6_reviewed_source_ids"]
    } == set(plan.NEW_SOURCE_GROUPS)
    assert sum(g["v5_next_action_changed"] for g in result["request_groups"]) == 6
    assert sum(g["v6_next_action_changed_from_v5"] for g in result["request_groups"]) == 3
    for group in result["request_groups"]:
        assert group["request_status"] == "DRAFT_NOT_SENT"
        assert group["task_credit"] is False
        if group["request_group_id"] not in plan.NEW_SOURCE_GROUPS:
            assert group["v6_next_action"] == group["v5_next_action"]


def test_main_route_review_pin_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(plan.PINS, plan.V6_REVIEW, "0" * 64)
    with pytest.raises(pinned.SourceRequestError, match="Pinned input differs"):
        plan.build(REPOSITORY, PRIVATE)
