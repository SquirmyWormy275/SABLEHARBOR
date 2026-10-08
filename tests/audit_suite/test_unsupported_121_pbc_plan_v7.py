"""Selected physical-site leads update one request group without audit credit."""

import json
from collections import Counter
from pathlib import Path

import pytest

from enterprise.audit_suite import unsupported_121_pbc_plan as pinned
from enterprise.audit_suite import unsupported_121_pbc_plan_v7 as plan

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V7_2026-09-30"
V6 = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V6_2026-09-30.json"


@pytest.fixture(scope="module")
def result():
    return plan.build(REPOSITORY, PRIVATE)


def test_exact_successor_preserves_every_prior_row_group_and_request(result):
    old = json.loads(V6.read_text())
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


def test_only_two_physical_clauses_and_one_group_gain_v7_leads(result):
    for side in "AB":
        rows = [row for row in result["rows"] if row["side"] == side]
        assert len(rows) == len({row["task_id"] for row in rows}) == 121
        assert len({row["control_id"] for row in rows}) == 28
        assert {row["task_id"] for row in rows if row["v7_reviewed_source_ids"]} == (
            plan.NEW_SOURCE_TASKS
        )
        for row in rows:
            selected = row["task_id"] in plan.NEW_SOURCE_TASKS
            assert row["v7_reviewed_source_ids"] == ([plan.SOURCE] if selected else [])
            assert set(row["v7_source_limits"]) == ({plan.SOURCE} if selected else set())
            assert row["v7_next_action_changed_from_v6"] == (
                row["request_group_id"] == plan.NEW_SOURCE_GROUP
            )
            assert row["accepted_nonoccurrence_status"] != "ACCEPTED"
        assert all(
            row["authored_test_clause"] and row["task_credit"] is False
            for row in rows
            if row["v7_reviewed_source_ids"]
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
        counts = result["counts"][side]
        assert counts["unsupported_exact_clauses"] == 121
        assert counts["v7_new_physical_source_affected_unsupported_clauses"] == 2
        assert counts["v7_cumulative_reviewed_source_affected_unsupported_clauses"] == 19
        assert counts["v7_cumulative_targeted_unsupported_clauses"] == 31
        assert counts["next_action_changes"] == 6
        assert counts["v6_next_action_changes_from_v5"] == 3
        assert counts["v7_next_action_changes_from_v6"] == 1
    assert {
        g["request_group_id"] for g in result["request_groups"] if g["v7_reviewed_source_ids"]
    } == {plan.NEW_SOURCE_GROUP}
    assert sum(g["v5_next_action_changed"] for g in result["request_groups"]) == 6
    assert sum(g["v6_next_action_changed_from_v5"] for g in result["request_groups"]) == 3
    assert sum(g["v7_next_action_changed_from_v6"] for g in result["request_groups"]) == 1
    for group in result["request_groups"]:
        assert group["request_status"] == "DRAFT_NOT_SENT"
        assert group["task_credit"] is False
        if group["request_group_id"] == plan.NEW_SOURCE_GROUP:
            assert "Reno, Boise and provider" in group["v7_next_action"]
            assert "environmental populations" in group["v7_next_action"]
            assert "recovery proof" in group["v7_next_action"]
            assert "qualified independent challenge" in group["v7_next_action"]
        else:
            assert group["v7_next_action"] == group["v6_next_action"]


def test_main_route_review_pin_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(plan.PINS, plan.V7_REVIEW, "0" * 64)
    with pytest.raises(pinned.SourceRequestError, match="Pinned input differs"):
        plan.build(REPOSITORY, PRIVATE)
