"""Exact unsupported clauses remain open in the read-only source-request plan."""

import json
from collections import Counter
from pathlib import Path

import pytest

from enterprise.audit_suite import unsupported_121_pbc_plan as plan

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_2026-09-29"


def test_exact_unsupported_population_reproduces_without_credit():
    result = plan.build(REPOSITORY, PRIVATE)
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert plan.markdown(result) == STEM.with_suffix(".md").read_text()
    assert len(result["rows"]) == 242
    assert len(result["request_groups"]) == 30
    assert result["counts"]["A"] == result["counts"]["B"]
    assert result["external_messages_sent"] == 0
    assert result["fresh_pair_created"] is False
    assert result["active_pair_mutated"] is False
    assert result["audit_task_credit"] is False
    for side in "AB":
        rows = [row for row in result["rows"] if row["side"] == side]
        assert len(rows) == 121
        assert len({row["task_id"] for row in rows}) == 121
        assert len({row["control_id"] for row in rows}) == 28
        assert all(
            row["authored_test_clause"]
            and row["pbc_request_status"] == "DRAFT_NOT_SENT"
            and row["current_task_status"] == "NOT_STARTED"
            and row["current_task_conclusion"] == "NOT_RUN"
            and row["task_credit"] is False
            and row["actual_operation_eligibility_as_of_packet"] is False
            and row["contact_status"] == "PROPOSED_NOT_ACCEPTED_DECISION_AUTHORITY"
            and row["system_status"] == "DESIGN_LOCATOR_ONLY_NOT_VERIFIED_DEPLOYED"
            for row in rows
        )


def test_legal_case_split_and_nonoccurrence_are_pending():
    result = plan.build(REPOSITORY, PRIVATE)
    side_a = [row for row in result["rows"] if row["side"] == "A"]
    legal = [row for row in side_a if row["control_id"] == "SH-LEG-001"]
    assert Counter(row["request_group_id"] for row in legal) == {
        "SH-LEG-001/PROVISION": 16,
        "SH-LEG-001/CONTEXT": 4,
        "SH-LEG-001/MATTER": 46,
    }
    assert result["counts"]["A"]["possible_nonoccurrence_review_candidates"] == 53
    assert result["counts"]["A"]["accepted_nonoccurrence_determinations"] == 0
    assert all(
        row["accepted_nonoccurrence_status"] == "NOT_ESTABLISHED"
        for row in side_a
        if row["possible_nonoccurrence_review_candidate"]
    )
    assert all(
        "EXTERNAL_AUTHORITY_RESPONSE_IF_TRIGGERED" in row["source_request_lanes"]
        for row in legal
        if row["request_group_id"] == "SH-LEG-001/MATTER"
    )
    assert all(
        row["source_request_lanes"] == ["QUALIFIED_LEGAL_APPLICABILITY_DECISION"]
        for row in legal
        if row["request_group_id"] == "SH-LEG-001/CONTEXT"
    )
    assert all(
        "QUALIFIED_LEGAL_APPLICABILITY_DECISION" in row["source_request_lanes"]
        for row in legal
        if row["request_group_id"] == "SH-LEG-001/PROVISION"
    )
    reserved = next(row for row in legal if row["task_id"].endswith("CHECK-HIPAA:160.302"))
    assert reserved["request_group_id"] == "SH-LEG-001/CONTEXT"
    assert reserved["possible_nonoccurrence_review_candidate"] is False


def test_external_customer_and_regulator_lanes_do_not_claim_responses():
    result = plan.build(REPOSITORY, PRIVATE)
    side_a = {row["task_id"]: row for row in result["rows"] if row["side"] == "A"}
    for control in ("SH-PRD-002", "SH-PRD-003", "SH-PRD-004"):
        row = side_a[f"TASK-{control}-corporate-ACTION-S-COMMUNICATION"]
        assert "EXTERNAL_COUNTERPARTY_RESPONSE" in row["source_request_lanes"]
        assert row["external_request_status"] == "NOT_SENT_OR_RECEIVED_BY_THIS_PACKET"
        assert row["task_credit"] is False
    regulator = side_a["TASK-SH-REC-002-corporate-ACTION-H-REGULATOR"]
    assert regulator["accepted_nonoccurrence_status"] == "NOT_ESTABLISHED"
    assert regulator["qualified_decision_status"] == "NOT_SUPPLIED_TO_THIS_PACKET"


def test_pinned_review_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(plan.PINS, plan.REVIEW, "0" * 64)
    with pytest.raises(plan.SourceRequestError, match="Pinned input differs"):
        plan.build(REPOSITORY, PRIVATE)
