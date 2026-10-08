"""Reviewed V5 sources adjust only six next actions in the unsupported plan."""

import json
from collections import Counter
from pathlib import Path

import pytest

from enterprise.audit_suite import unsupported_121_pbc_plan as prior
from enterprise.audit_suite import unsupported_121_pbc_plan_v5 as plan

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V5_2026-09-30"


def test_v5_reproduces_exact_unsupported_population_without_request_or_credit():
    result = plan.build(REPOSITORY, PRIVATE)
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert plan.markdown(result) == STEM.with_suffix(".md").read_text()
    assert result["reviewed_route_roster"] == {
        "cohorts": 26,
        "native_versions": 475,
        "source_complete": False,
    }
    assert len(result["rows"]) == 242
    assert len(result["request_groups"]) == len(result["group_delta"]) == 30
    assert result["external_messages_sent"] == 0
    assert result["accepted_na_determinations"] == 0
    assert result["fresh_pair_created"] is False
    assert result["active_pair_mutated"] is False
    assert result["audit_task_credit"] is False
    for side in "AB":
        rows = [row for row in result["rows"] if row["side"] == side]
        assert len(rows) == len({row["task_id"] for row in rows}) == 121
        assert len({row["control_id"] for row in rows}) == 28
        assert sum(row["possible_nonoccurrence_review_candidate"] for row in rows) == 53
        assert sum(bool(row["v5_reviewed_source_ids"]) for row in rows) == 13
        assert all(
            row["authored_test_clause"]
            and row["pbc_request_status"] == "DRAFT_NOT_SENT"
            and row["current_task_status"] == "NOT_STARTED"
            and row["current_task_conclusion"] == "NOT_RUN"
            and row["task_credit"] is False
            and row["accepted_nonoccurrence_status"] != "ACCEPTED"
            for row in rows
        )
        legal = [row for row in rows if row["control_id"] == "SH-LEG-001"]
        assert Counter(row["request_group_id"] for row in legal) == {
            "SH-LEG-001/PROVISION": 16,
            "SH-LEG-001/CONTEXT": 4,
            "SH-LEG-001/MATTER": 46,
        }


def test_every_group_owner_locator_and_request_are_explicitly_reconciled():
    old = prior.build(REPOSITORY, PRIVATE)
    result = plan.build(REPOSITORY, PRIVATE)
    old_groups = {row["request_group_id"]: row for row in old["request_groups"]}
    assert {row["request_group_id"] for row in result["group_delta"]} == set(old_groups)
    changed = [row for row in result["group_delta"] if row["next_action_changed"]]
    assert {row["request_group_id"] for row in changed} == set(plan.NEW_SOURCE_GROUPS)
    assert len(changed) == 6
    assert all(
        not row["grouping_changed"]
        and not row["candidate_contact_changed"]
        and not row["source_locator_changed"]
        and not row["requested_originals_changed"]
        for row in result["group_delta"]
    )
    for group in result["request_groups"]:
        old_group = old_groups[group["request_group_id"]]
        assert all(group[key] == old_group[key] for key in old_group)
        assert group["request_status"] == "DRAFT_NOT_SENT"
        assert group["task_credit"] is False
        if group["request_group_id"] in plan.NEW_SOURCE_GROUPS:
            assert group["v5_next_action"] != old_group["requested_originals_or_decision"]
        else:
            assert group["v5_next_action"] == old_group["requested_originals_or_decision"]


def test_review_pin_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(plan.PINS, plan.V5_REVIEW, "0" * 64)
    with pytest.raises(prior.SourceRequestError, match="Pinned input differs"):
        plan.build(REPOSITORY, PRIVATE)
