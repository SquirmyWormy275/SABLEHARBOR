"""SEC001 source leads only revise one unsent group; unsupported work stays open."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import unsupported_121_pbc_plan_v9 as plan

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V9_2026-09-30"


@pytest.fixture(scope="module")
def inputs():
    paths = (
        (REPOSITORY / plan.V8_PLAN, plan.V8_PLAN),
        (REPOSITORY / plan.V11_LEDGER, plan.V11_LEDGER),
        (PRIVATE / plan.COMP_RECEIPT, plan.COMP_RECEIPT),
        (PRIVATE / plan.TRANSFER_RECEIPT, plan.TRANSFER_RECEIPT),
    )
    for path, key in paths:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == plan.PINS[key]
    return tuple(json.loads(path.read_bytes()) for path, _ in paths)


@pytest.fixture(scope="module")
def draft(inputs):
    return plan._extend(*inputs, plan.P1_FREEZE)


@pytest.fixture(scope="module")
def built():
    return plan.build(REPOSITORY, PRIVATE)


def test_exact_v8_rows_groups_contacts_and_original_requests_remain(inputs, draft):
    old, _, _, _ = inputs
    assert len(old["rows"]) == len(draft["rows"]) == 242
    assert len(old["request_groups"]) == len(draft["request_groups"]) == 30
    assert len(old["group_delta"]) == len(draft["group_delta"]) == 30
    for previous, current in zip(old["rows"], draft["rows"], strict=True):
        assert all(current[key] == value for key, value in previous.items())
        assert current["pbc_request_status"] == "DRAFT_NOT_SENT"
        assert (current["current_task_status"], current["current_task_conclusion"]) == (
            "NOT_STARTED",
            "NOT_RUN",
        )
        assert current["task_credit"] is False
    for name in ("request_groups", "group_delta"):
        for previous, current in zip(old[name], draft[name], strict=True):
            assert all(current[key] == value for key, value in previous.items())
    assert draft["candidate_owner_source_queues"] == old["candidate_owner_source_queues"]
    assert draft["nonoccurrence_acceptance_protocol"] == old["nonoccurrence_acceptance_protocol"]
    assert draft["external_messages_sent"] == draft["accepted_na_determinations"] == 0
    assert draft["fresh_pair_created"] is draft["audit_task_credit"] is False


def test_only_cc52_cc67_receive_bounded_leads_and_one_group_action(inputs, draft):
    old, ledger, comp, transfer = inputs
    for side, comp_branch, transfer_branch in (
        ("A", "SEC001-COMPONENT-CLEAN", "SEC001-XFER-CLEAN"),
        ("B", "SEC001-COMPONENT-MESSY", "SEC001-XFER-MESSY"),
    ):
        rows = [row for row in draft["rows"] if row["side"] == side]
        assert {row["task_id"] for row in rows if row["v9_reviewed_source_ids"]} == {
            plan.CC52_TASK,
            plan.CC67_TASK,
        }
        cc52 = next(row for row in rows if row["task_id"] == plan.CC52_TASK)
        cc67 = next(row for row in rows if row["task_id"] == plan.CC67_TASK)
        assert (
            cc52["v8_targeted_source_ids"]
            == cc52["v9_targeted_source_ids"]
            == ["SEC003_SELECTED_VULNERABILITY_V1"]
        )
        assert cc52["v9_reviewed_source_ids"] == [plan.COMP_SOURCE]
        assert cc67["v8_targeted_source_ids"] == []
        assert (
            cc67["v9_targeted_source_ids"]
            == cc67["v9_reviewed_source_ids"]
            == [plan.TRANSFER_SOURCE]
        )
        for row, source, receipt, branch, count in (
            (cc52, plan.COMP_SOURCE, comp, comp_branch, 10 if side == "A" else 15),
            (cc67, plan.TRANSFER_SOURCE, transfer, transfer_branch, 10 if side == "A" else 16),
        ):
            assert len(row["v9_source_record_refs"][source]) == count
            assert row["v9_source_record_refs"][source] == [
                {key: native[key] for key in plan.REF_FIELDS}
                for native in receipt["native_originals"]
                if native["branch"] == branch
            ]
            assert row["v9_source_limits"][source]
            assert row["authored_test_clause"] == row["remaining_test_gate"]
            assert row["accepted_nonoccurrence_status"] != "ACCEPTED"
        routed = {row["task_id"]: row for row in ledger["rows"] if row["side"] == side}
        assert (
            cc52["v9_targeted_source_ids"]
            == routed[plan.CC52_TASK]["targeted_integrated_source_ids"]
        )
        assert (
            cc67["v9_targeted_source_ids"]
            == routed[plan.CC67_TASK]["targeted_integrated_source_ids"]
        )
        assert sum(row["possible_nonoccurrence_review_candidate"] for row in rows) == 53
        assert all(
            row["accepted_nonoccurrence_status"] == "NOT_ESTABLISHED"
            for row in rows
            if row["possible_nonoccurrence_review_candidate"]
        )
    group = next(g for g in draft["request_groups"] if g["request_group_id"] == plan.GROUP)
    old_group = next(g for g in old["request_groups"] if g["request_group_id"] == plan.GROUP)
    assert group["candidate_contact_person_id"] == old_group["candidate_contact_person_id"]
    assert group["requested_originals_or_decision"] == old_group["requested_originals_or_decision"]
    assert group["v9_next_action"].startswith(old_group["v8_next_action"] + " ")
    assert "third-party landscape is undesigned" in group["v9_next_action"]
    assert "actual transfer population" in group["v9_next_action"]
    assert group["v9_reviewed_source_ids"] == sorted((plan.COMP_SOURCE, plan.TRANSFER_SOURCE))
    assert group["request_status"] == "DRAFT_NOT_SENT"
    assert {
        g["request_group_id"] for g in draft["request_groups"] if g["v9_reviewed_source_ids"]
    } == {plan.GROUP}
    assert sum(g["v9_next_action_changed_from_v8"] for g in draft["request_groups"]) == 1


def test_unique_affected_denominators_and_no_credit(inputs, draft):
    old, _, _, _ = inputs
    assert draft["counts"]["A"] == draft["counts"]["B"]
    for side in "AB":
        previous = old["counts"][side]
        counts = draft["counts"][side]
        assert previous["v8_cumulative_reviewed_source_affected_unsupported_clauses"] == 21
        assert previous["v8_cumulative_targeted_unsupported_clauses"] == 33
        assert counts["v9_new_reviewed_source_leads"] == 2
        assert counts["v9_newly_source_affected_unsupported_clauses"] == 1
        assert counts["v9_cumulative_reviewed_source_affected_unsupported_clauses"] == 22
        assert counts["v9_cumulative_targeted_unsupported_clauses"] == 34
        assert counts["v9_cumulative_changed_request_groups"] == 10
        assert counts["unsupported_exact_clauses"] == 121
        assert counts["possible_nonoccurrence_review_candidates"] == 53
        assert draft["active_p1_tasks"][side] == {
            "task_count": 409,
            "status": "NOT_STARTED",
            "conclusion": "NOT_RUN",
        }
    assert draft["p1_freeze"] == plan.P1_FREEZE
    assert draft["external_messages_sent"] == draft["accepted_na_determinations"] == 0
    assert draft["fresh_pair_created"] is draft["audit_task_credit"] is False


def test_wrong_route_or_claim_drift_fails_closed(inputs):
    old, ledger, comp, transfer = inputs
    changed_route = deepcopy(ledger)
    next(
        row
        for row in changed_route["rows"]
        if row["side"] == "A" and row["task_id"] == plan.CC52_TASK
    )["targeted_integrated_source_ids"] = [plan.COMP_SOURCE]
    with pytest.raises(plan.V9SourceRequestError, match="Unsupported V9 clause/route drift"):
        plan._extend(old, changed_route, comp, transfer, plan.P1_FREEZE)
    changed_component = deepcopy(comp)
    changed_component["actual_supplier_selected_or_contracted"] = True
    with pytest.raises(plan.V9SourceRequestError, match="component authority or scope"):
        plan._extend(old, ledger, changed_component, transfer, plan.P1_FREEZE)
    changed_transfer = deepcopy(transfer)
    changed_transfer["actual_network_transmission"] = True
    with pytest.raises(plan.routes_v11.V11ReconciliationError, match="authority or route boundary"):
        plan._extend(old, ledger, comp, changed_transfer, plan.P1_FREEZE)


def test_review_pin_drift_and_false_no_event_acceptance_fail_closed(inputs, monkeypatch):
    old, ledger, comp, transfer = inputs
    changed = deepcopy(old)
    next(
        row
        for row in changed["rows"]
        if row["side"] == "B" and row["possible_nonoccurrence_review_candidate"]
    )["accepted_nonoccurrence_status"] = "ACCEPTED"
    with pytest.raises(plan.V9SourceRequestError, match="Unsupported V9 clause/route drift"):
        plan._extend(changed, ledger, comp, transfer, plan.P1_FREEZE)
    monkeypatch.setitem(plan.PINS, plan.V11_REVIEW, "0" * 64)
    with pytest.raises(plan.pinned.SourceRequestError, match="Pinned input differs"):
        plan.build(REPOSITORY, PRIVATE)


def test_build_reproduces_tracked_artifacts_and_pins(built):
    assert built == json.loads(STEM.with_suffix(".json").read_bytes())
    assert plan.markdown(built) == STEM.with_suffix(".md").read_text()
    assert built["source_pins"][plan.V8_REVIEW] == plan.PINS[plan.V8_REVIEW]
    assert built["source_pins"][plan.V11_REVIEW] == plan.PINS[plan.V11_REVIEW]
    assert built["source_pins"][plan.COMP_REVIEW] == plan.PINS[plan.COMP_REVIEW]
    assert built["source_pins"][plan.COMP_DB] == plan.PINS[plan.COMP_DB]
