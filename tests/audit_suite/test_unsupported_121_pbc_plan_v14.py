"""Selected GOV CC1.2 discovery leads preserve every V13 draft request boundary."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import unsupported_121_pbc_plan_v14 as plan

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V14_2026-10-01"


@pytest.fixture(scope="module")
def inputs():
    return (
        json.loads((REPOSITORY / plan.V13_PLAN).read_bytes()),
        json.loads((REPOSITORY / plan.ROUTE_LEDGER).read_bytes()),
        json.loads((PRIVATE / plan.SOURCE_RECEIPT).read_bytes()),
    )


@pytest.fixture(scope="module")
def draft(inputs):
    return plan._extend(*inputs, plan.P1_FREEZE)


def test_v13_row_group_contact_locator_and_request_prefix_remains(inputs, draft):
    old, _, _ = inputs
    for collection, count in (("rows", 242), ("request_groups", 30), ("group_delta", 30)):
        assert len(old[collection]) == len(draft[collection]) == count
        for previous, current in zip(old[collection], draft[collection], strict=True):
            assert all(current[key] == value for key, value in previous.items())
    for key in (
        "candidate_owner_source_queues",
        "nonoccurrence_acceptance_protocol",
        "reviewed_route_roster",
    ):
        assert draft[key] == old[key]
    assert draft["as_of"] == "2026-10-01"
    assert all(group["request_status"] == "DRAFT_NOT_SENT" for group in draft["request_groups"])


def test_only_two_authored_gov_leads_match_branch_native_refs_and_route(inputs, draft):
    old, ledger, receipt = inputs
    for side, scenario, count in (("A", "CLEAN", 9), ("B", "MESSY", 14)):
        rows = [row for row in draft["rows"] if row["side"] == side]
        assert {row["task_id"] for row in rows if row["v14_reviewed_source_ids"]} == set(plan.TASKS)
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
            assert row["v14_reviewed_source_ids"] == [plan.SOURCE]
            assert row["v14_targeted_source_ids"] == [plan.SOURCE]
            assert old_row["v13_targeted_source_ids"] == []
            assert row["v14_targeted_source_ids"] == route_row["targeted_integrated_source_ids"]
            assert row["v14_source_limits"] == {plan.SOURCE: plan.SOURCE_LIMIT}
            assert row["v14_source_record_refs"] == {plan.SOURCE: refs}
            assert route_row["v16_source_record_refs"] == {plan.SOURCE: refs}
            assert row["authored_test_clause"] == plan.route.CLAUSE
            assert row["current_task_status"] == "NOT_STARTED"
            assert row["current_task_conclusion"] == "NOT_RUN"
            assert row["task_credit"] is False
            assert route_row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
            assert route_row["audit_task_credit"] is False
    assert {
        group["request_group_id"]
        for group in draft["request_groups"]
        if group["v14_next_action_changed_from_v13"]
    } == set(plan.GROUPS)
    for name in plan.GROUPS:
        old_group = next(g for g in old["request_groups"] if g["request_group_id"] == name)
        group = next(g for g in draft["request_groups"] if g["request_group_id"] == name)
        assert group["v14_next_action"].startswith(old_group["v13_next_action"] + " ")
        assert group["candidate_contact_person_id"] == old_group["candidate_contact_person_id"]
        assert (
            group["requested_originals_or_decision"] == old_group["requested_originals_or_decision"]
        )


def test_exact_denominators_and_no_send_or_credit(draft):
    assert draft["counts"]["A"] == draft["counts"]["B"]
    for side in "AB":
        counts = draft["counts"][side]
        assert counts["unsupported_exact_clauses"] == 121
        assert counts["possible_nonoccurrence_review_candidates"] == 53
        assert counts["v14_new_reviewed_source_leads"] == 2
        assert counts["v14_cumulative_reviewed_source_affected_unsupported_clauses"] == 29
        assert counts["v14_cumulative_targeted_unsupported_clauses"] == 37
        assert counts["v14_cumulative_changed_request_groups"] == 17
        assert draft["active_p1_tasks"][side] == {
            "task_count": 409,
            "status": "NOT_STARTED",
            "conclusion": "NOT_RUN",
        }
    assert len(draft["request_groups"]) == 30
    assert draft["external_messages_sent"] == draft["accepted_na_determinations"] == 0
    assert draft["fresh_pair_created"] is draft["source_complete"] is False
    assert draft["audit_task_credit"] is draft["active_pair_mutated"] is False


def test_selected_source_route_or_no_event_drift_fails_closed(inputs):
    old, ledger, receipt = inputs
    changed = deepcopy(receipt)
    changed["records"]["CLEAN"][0]["branch"] = plan.source.BRANCHES["MESSY"]
    with pytest.raises(plan.V14SourceRequestError, match="roster differs"):
        plan._extend(old, ledger, changed, plan.P1_FREEZE)
    changed = deepcopy(ledger)
    next(row for row in changed["rows"] if row["side"] == "B" and row["task_id"] == plan.TASKS[1])[
        "classification"
    ] = "SOURCE_CANDIDATE_PARTIAL"
    with pytest.raises(plan.V14SourceRequestError, match="authored route"):
        plan._extend(old, changed, receipt, plan.P1_FREEZE)
    changed_old = deepcopy(old)
    next(
        row
        for row in changed_old["rows"]
        if row["side"] == "A" and row["possible_nonoccurrence_review_candidate"]
    )["accepted_nonoccurrence_status"] = "ACCEPTED"
    with pytest.raises(plan.V14SourceRequestError, match="task/request"):
        plan._extend(changed_old, ledger, receipt, plan.P1_FREEZE)


@pytest.mark.parametrize("rel", [plan.V13_PLAN, plan.V13_REVIEW])
def test_disposable_tampered_prior_byte_or_review_fails_pin(tmp_path, monkeypatch, rel):
    origin = REPOSITORY / rel if rel == plan.V13_PLAN else PRIVATE / rel
    disposable = tmp_path / origin.name
    disposable.write_bytes(origin.read_bytes() + b"\n")
    disposable.chmod(0o600)
    replacement = str(disposable)
    if rel == plan.V13_PLAN:
        monkeypatch.setattr(plan, "V13_PLAN", replacement)
    else:
        monkeypatch.setattr(plan, "V13_REVIEW", replacement)
    monkeypatch.setitem(plan.PINS, replacement, plan.PINS[rel])
    with pytest.raises(plan.pinned.SourceRequestError, match="Pinned input differs"):
        plan.build(REPOSITORY, PRIVATE)


def test_build_uses_reviewed_bytes_without_recursive_prior_or_route_build(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Recursive full-chain build forbidden")

    monkeypatch.setattr(plan.prior, "build", forbidden)
    monkeypatch.setattr(plan.route, "build", forbidden)
    built = plan.build(REPOSITORY, PRIVATE)
    assert built == json.loads(STEM.with_suffix(".json").read_bytes())
    assert plan.markdown(built) == STEM.with_suffix(".md").read_text()
    assert built["source_pins"][plan.V13_REVIEW] == plan.PINS[plan.V13_REVIEW]
    assert built["source_pins"][plan.ROUTE_REVIEW] == plan.PINS[plan.ROUTE_REVIEW]
    assert built["source_pins"][plan.SOURCE_REVIEW] == plan.PINS[plan.SOURCE_REVIEW]
