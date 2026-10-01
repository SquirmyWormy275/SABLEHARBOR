"""Selected LEG/DAT PBC draft actions preserve V14 requests and no-credit gates."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import unsupported_121_pbc_plan_v15 as plan

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
STEM = REPOSITORY / "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V15_2026-10-01"


@pytest.fixture(scope="module")
def inputs() -> tuple[dict, dict, dict, dict, dict, dict]:
    paths = (
        REPOSITORY / plan.V14_PLAN,
        REPOSITORY / plan.ROUTE_LEDGER,
        REPOSITORY / plan.V16_LEDGER,
        REPOSITORY / plan.LEG_GAP,
        PRIVATE / plan.LEG_RECEIPT,
        PRIVATE / plan.DAT_RECEIPT,
    )
    for path in paths:
        rel = str(path.relative_to(REPOSITORY if path.is_relative_to(REPOSITORY) else PRIVATE))
        assert hashlib.sha256(path.read_bytes()).hexdigest() == plan.PINS[rel]
    return tuple(json.loads(path.read_bytes()) for path in paths)


@pytest.fixture(scope="module")
def draft(inputs: tuple[dict, dict, dict, dict, dict, dict]) -> dict:
    return plan._extend(*inputs, plan.P1_FREEZE)


def test_reviewed_main_pins_and_exact_unchanged_prefix(
    inputs: tuple[dict, dict, dict, dict, dict, dict], draft: dict
) -> None:
    old = inputs[0]
    for rel, digest in plan.PINS.items():
        path = (
            REPOSITORY
            if rel in {plan.V14_PLAN, plan.ROUTE_LEDGER, plan.V16_LEDGER, plan.LEG_GAP}
            else PRIVATE
        ) / rel
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    assert draft["v17_route_ledger_sha256"] == plan.PINS[plan.ROUTE_LEDGER]
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


def test_only_16_leg_and_two_dat_authored_actions_per_side(
    inputs: tuple[dict, dict, dict, dict, dict, dict], draft: dict
) -> None:
    old, ledger, v16, gap, leg_receipt, dat_receipt = inputs
    refs, selected = plan._selected_refs(old, ledger, v16, gap, leg_receipt, dat_receipt)
    for side in "AB":
        rows = [row for row in draft["rows"] if row["side"] == side]
        assert {row["task_id"] for row in rows if row["v15_reviewed_source_ids"]} == (
            selected["leg"] | selected["dat"]
        )
        assert len(selected["leg"]) == 16
        assert len(selected["dat"]) == 2
        assert sum(row["v15_next_action_changed_from_v14"] for row in rows) == 18
        for row in rows:
            task = row["task_id"]
            route_row = next(
                r for r in ledger["rows"] if r["side"] == side and r["task_id"] == task
            )
            assert row["v15_targeted_source_ids"] == route_row["targeted_integrated_source_ids"]
            assert row["v15_source_record_refs"] == route_row["v17_source_record_refs"]
            assert row["v15_source_limits"] == route_row["v17_source_limits"]
            assert row["current_task_status"] == "NOT_STARTED"
            assert row["current_task_conclusion"] == "NOT_RUN"
            assert row["task_credit"] is False
            if task in selected["leg"]:
                assert row["request_group_id"] == plan.LEG_GROUP
                assert row["v15_source_record_refs"] == {plan.LEG_SOURCE: refs[side]["leg"][task]}
                assert row["v15_next_action"].startswith(row["v14_next_action"] + " ")
            elif task in selected["dat"]:
                assert row["request_group_id"] == plan.DAT_GROUP
                assert row["v15_source_record_refs"] == {plan.DAT_SOURCE: refs[side]["dat"]}
                assert row["v15_next_action"].startswith(row["v14_next_action"] + " ")
            else:
                assert row["v15_reviewed_source_ids"] == []
                assert row["v15_next_action"] == row["v14_next_action"]
    assert {ref["branch"] for row in refs["A"]["leg"].values() for ref in row} == {"LEGOV-CLEAN"}
    assert {ref["branch"] for row in refs["B"]["leg"].values() for ref in row} == {"LEGOV-MESSY"}
    assert {ref["branch"] for ref in refs["A"]["dat"]} == {plan.route.dat.BRANCHES["CLEAN"]}
    assert {ref["branch"] for ref in refs["B"]["dat"]} == {plan.route.dat.BRANCHES["MESSY"]}


def test_only_two_groups_change_draft_next_action_and_scope(draft: dict) -> None:
    for collection in ("request_groups", "group_delta"):
        changed = [row for row in draft[collection] if row["v15_next_action_changed_from_v14"]]
        assert {row["request_group_id"] for row in changed} == {plan.LEG_GROUP, plan.DAT_GROUP}
        for row in changed:
            source = (
                plan.LEG_SOURCE if row["request_group_id"] == plan.LEG_GROUP else plan.DAT_SOURCE
            )
            assert row["v15_reviewed_source_ids"] == [source]
            assert row["v15_next_action"].startswith(row["v14_next_action"] + " ")
            assert len(row["v15_source_record_refs_by_side"]["A"]) == (
                16 if source == plan.LEG_SOURCE else 2
            )
            assert len(row["v15_source_record_refs_by_side"]["B"]) == (
                16 if source == plan.LEG_SOURCE else 2
            )
    assert all(group["request_status"] == "DRAFT_NOT_SENT" for group in draft["request_groups"])


def test_denominators_no_event_and_p1_remain_unrun(draft: dict) -> None:
    assert draft["counts"]["A"] == draft["counts"]["B"]
    for side in "AB":
        counts = draft["counts"][side]
        assert counts["unsupported_exact_clauses"] == 121
        assert counts["possible_nonoccurrence_review_candidates"] == 53
        assert counts["v15_new_reviewed_source_leads"] == 18
        assert counts["v15_cumulative_reviewed_source_affected_unsupported_clauses"] == 47
        assert counts["v15_cumulative_targeted_unsupported_clauses"] == 55
        assert counts["v15_cumulative_changed_request_groups"] == 19
        assert draft["active_p1_tasks"][side] == {
            "task_count": 409,
            "status": "NOT_STARTED",
            "conclusion": "NOT_RUN",
        }
    assert draft["external_messages_sent"] == draft["accepted_na_determinations"] == 0
    assert draft["fresh_pair_created"] is draft["source_complete"] is False
    assert draft["audit_task_credit"] is draft["active_pair_mutated"] is False


def test_tampered_route_branch_and_no_event_fail_closed(
    inputs: tuple[dict, dict, dict, dict, dict, dict],
) -> None:
    old, ledger, v16, gap, leg_receipt, dat_receipt = inputs
    changed = deepcopy(ledger)
    next(
        row
        for row in changed["rows"]
        if row["side"] == "A" and row["task_id"] == plan.route.DAT_TASKS[0]
    )["classification"] = "SOURCE_CANDIDATE_PARTIAL"
    with pytest.raises(plan.V15SourceRequestError, match="route/native lead"):
        plan._extend(old, changed, v16, gap, leg_receipt, dat_receipt, plan.P1_FREEZE)
    changed = deepcopy(leg_receipt)
    changed["records"]["CLEAN"][0]["branch"] = changed["branches"]["MESSY"]
    with pytest.raises(plan.route.V17ReconciliationError, match="native branch refs"):
        plan._extend(old, ledger, v16, gap, changed, dat_receipt, plan.P1_FREEZE)
    changed = deepcopy(dat_receipt)
    changed["records"]["MESSY"][0]["branch"] = plan.route.dat.BRANCHES["CLEAN"]
    with pytest.raises(plan.route.V17ReconciliationError, match="native branch refs"):
        plan._extend(old, ledger, v16, gap, leg_receipt, changed, plan.P1_FREEZE)
    changed = deepcopy(old)
    next(
        row
        for row in changed["rows"]
        if row["side"] == "B" and row["possible_nonoccurrence_review_candidate"]
    )["accepted_nonoccurrence_status"] = "ACCEPTED"
    with pytest.raises(plan.V15SourceRequestError, match="task, draft request"):
        plan._extend(changed, ledger, v16, gap, leg_receipt, dat_receipt, plan.P1_FREEZE)


@pytest.mark.parametrize("rel", [plan.V14_PLAN, plan.V14_REVIEW, plan.ROUTE_REVIEW])
def test_disposable_tampered_prior_or_review_byte_fails_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rel: str
) -> None:
    origin = REPOSITORY / rel if rel == plan.V14_PLAN else PRIVATE / rel
    disposable = tmp_path / origin.name
    disposable.write_bytes(origin.read_bytes() + b"\n")
    disposable.chmod(0o600)
    replacement = str(disposable)
    attr = (
        "V14_PLAN"
        if rel == plan.V14_PLAN
        else "V14_REVIEW"
        if rel == plan.V14_REVIEW
        else "ROUTE_REVIEW"
    )
    monkeypatch.setattr(plan, attr, replacement)
    monkeypatch.setitem(plan.PINS, replacement, plan.PINS[rel])
    with pytest.raises(plan.pinned.SourceRequestError, match="Pinned input differs"):
        plan.build(REPOSITORY, PRIVATE)


def test_full_bounded_build_without_recursive_prior_or_route_replay(
    draft: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert draft == json.loads(STEM.with_suffix(".json").read_bytes())
    assert plan.markdown(draft) == STEM.with_suffix(".md").read_text()

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Recursive prior/route build forbidden")

    monkeypatch.setattr(plan.prior, "build", forbidden)
    monkeypatch.setattr(plan.route, "build", forbidden)
    built = plan.build(REPOSITORY, PRIVATE)
    assert built == draft
    assert plan._p1_inventory(PRIVATE) == plan.P1_FREEZE
