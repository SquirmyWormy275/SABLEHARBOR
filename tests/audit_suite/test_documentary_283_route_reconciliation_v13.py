"""Exact V12 prefix and no-credit tests for the selected emergency replay lead."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import documentary_283_route_reconciliation_v13 as route

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V13_2026-09-30"


@pytest.fixture(scope="module")
def previous() -> dict:
    path = REPOSITORY / route.V12_LEDGER
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["v12_ledger"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def receipt() -> dict:
    path = PRIVATE / route.REPLAY_RUN / "RECEIPT.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["replay_receipt"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def result(previous: dict, receipt: dict) -> dict:
    return route._extend(previous, receipt, route.P1_FREEZE)


def test_reviewed_pins_and_selected_original_chains(previous: dict, receipt: dict) -> None:
    for pin in route.PINS.values():
        path = (REPOSITORY if pin["scope"] == "repo" else PRIVATE) / pin["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin["sha256"]
    refs = route._selected_refs(receipt, previous)
    assert [len(refs[side]) for side in "AB"] == [8, 15]
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        assert [(r["system"], r["record"]) for r in refs[side]] == [
            (system, record) for _, system, record, _, _, _ in route.replay._plan(scenario)
        ]
        assert {r["branch"] for r in refs[side]} == {route.replay.BRANCHES[scenario]}
        assert all(set(r) == set(route.IDENTITY) for r in refs[side])
    assert receipt["actual_phi_processing"] is False
    assert receipt["external_bytes_or_packets"] == 0
    assert receipt["messy_upstream_gates_remain_open"] is True


def test_only_one_named_unsupported_route_gains_a_lead(previous: dict, result: dict) -> None:
    assert len(result["rows"]) == len(previous["rows"]) == 566
    assert result["v12_prefix_sha256"] == route.PINS["v12_ledger"]["sha256"]
    assert result["active_p1_tasks"] == previous["active_p1_tasks"]
    for old, new in zip(previous["rows"], result["rows"], strict=True):
        selected = old["task_id"] == route.TASK
        assert all(
            new[key] == value
            for key, value in old.items()
            if key != "targeted_integrated_source_ids" or not selected
        )
        assert new["targeted_integrated_source_ids"] == (
            [*old["targeted_integrated_source_ids"], route.SOURCE]
            if selected
            else old["targeted_integrated_source_ids"]
        )
        assert new["v13_reviewed_source_ids"] == ([route.SOURCE] if selected else [])
        assert new["classification"] == old["classification"]
        assert new["remaining_test_gate"] == old["remaining_test_gate"]
        assert new["current_status"] == "NOT_STARTED"
        assert new["current_conclusion"] == "NOT_RUN"
        assert new["audit_task_credit"] is False
    assert result["audit_task_credit"] is result["active_pair_mutated"] is False


def test_counts_and_unsupported_clause_persist(result: dict) -> None:
    for side in "AB":
        count = result["counts"][side]
        assert count["targeted_integrated_route_count"] == 175
        assert count["classifications"] == {
            "DESIGN_CONTEXT_ONLY": 27,
            "SOURCE_CANDIDATE_PARTIAL": 135,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        assert count["v13_new_selected_emergency_replay_authored_leads"] == 1
        assert count["v13_new_distinct_targeted_routes"] == 0
        selected = next(
            r for r in result["rows"] if r["side"] == side and r["task_id"] == route.TASK
        )
        assert selected["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
        assert selected["authored_test_clause"] == route.CLAUSE
        assert len(selected["v13_source_record_refs"][route.SOURCE]) == (8 if side == "A" else 15)


def test_changed_replay_scope_or_authored_clause_fails(previous: dict, receipt: dict) -> None:
    for key, value in (
        ("messy_upstream_gates_remain_open", False),
        ("actual_phi_processing", True),
        ("source_complete", True),
    ):
        changed = deepcopy(receipt)
        changed[key] = value
        with pytest.raises(route.V13ReconciliationError, match="scope or open exceptions"):
            route._selected_refs(changed, previous)
    changed = deepcopy(receipt)
    changed["records"]["MESSY"][-1]["record"] = "CLOSED"
    with pytest.raises(route.V13ReconciliationError, match="native roster"):
        route._selected_refs(changed, previous)
    changed = deepcopy(previous)
    selected = next(r for r in changed["rows"] if r["side"] == "A" and r["task_id"] == route.TASK)
    selected["remaining_test_gate"] = "truncated"
    with pytest.raises(route.V13ReconciliationError, match="unsupported IAM005"):
        route._extend(changed, receipt, route.P1_FREEZE)


def test_exact_generated_ledger_and_markdown(result: dict) -> None:
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route.markdown(result) == STEM.with_suffix(".md").read_text()


def test_full_reviewed_source_and_v12_replay() -> None:
    result = route.build(REPOSITORY, PRIVATE)
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route._p1_inventory(PRIVATE) == route.P1_FREEZE
