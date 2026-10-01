"""Exact-row and native-authority tests for the selected POL004 route lead."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import documentary_283_route_reconciliation_v12 as route

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V12_2026-09-30"


@pytest.fixture(scope="module")
def previous() -> dict:
    path = REPOSITORY / route.V11_LEDGER
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["v11_ledger"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def receipt() -> dict:
    path = PRIVATE / route.POL_RUN / "SOURCE_RECEIPT.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["pol_receipt"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def result(previous: dict, receipt: dict) -> dict:
    return route._extend(previous, receipt, route.P1_FREEZE)


def test_accepted_pin_roster_and_open_policy_status(previous: dict, receipt: dict) -> None:
    assert route.PINS["v11_review"]["sha256"] == (
        "5db6205b1afcbd578562345a7ff0af6a212b8cbf1c39139cb71a22590fd394a2"
    )
    assert route.PINS["pol_review"]["sha256"] == (
        "2c0e96babf915c42d7d056de9ec87c30bc8966ddab126343ec444a1bad715143"
    )
    for pin in route.PINS.values():
        path = (REPOSITORY if pin["scope"] == "repo" else PRIVATE) / pin["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin["sha256"]
    assert previous["active_p1_tasks"] == {
        side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"} for side in "AB"
    }
    assert receipt["enterprise_policy_status_2026"] == "OPEN"
    assert receipt["design_standard_approved_only"] is True
    assert receipt["procedure_authority"] == "PENDING_AUTHORIZED_DECISION"
    assert receipt["messy_exception_open"] is True
    assert receipt["actual_operation"] is False


def test_complete_native_chains_and_three_clocks(previous: dict, receipt: dict) -> None:
    refs = route._selected_refs(receipt, previous)
    assert [len(refs[side]) for side in "AB"] == [7, 9]
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        assert [(row["system"], row["record"]) for row in refs[side]] == [
            (system, record) for system, record, _, _ in route.procedure.PLAN[scenario]
        ]
        assert {row["branch"] for row in refs[side]} == {route.procedure.BRANCHES[scenario]}
        assert all(set(row) == set(route.IDENTITY) for row in refs[side])
    assert [row["record"] for row in refs["B"]][-5:] == [
        "FALSE-CLOSE",
        "CHALLENGE",
        "CORRECTION",
        "EXPIRY-REVIEW",
        "FINAL",
    ]


def test_adverse_history_authority_or_native_drift_fails(previous: dict, receipt: dict) -> None:
    for key, value in (
        ("messy_exception_open", False),
        ("procedure_authority", "APPROVED"),
        ("actual_operation", True),
    ):
        changed = deepcopy(receipt)
        changed[key] = value
        with pytest.raises(route.V12ReconciliationError, match="authority or scope"):
            route._selected_refs(changed, previous)
    changed = deepcopy(receipt)
    changed["native_originals"][-1]["record"] = "UNREVIEWED"
    with pytest.raises(route.V12ReconciliationError, match="native roster"):
        route._selected_refs(changed, previous)
    changed = deepcopy(receipt)
    changed["native_originals"][-1]["available_at"] = ""
    with pytest.raises(route.V12ReconciliationError, match="native roster or clocks"):
        route._selected_refs(changed, previous)


def test_every_v11_field_and_only_cc53_target_changes(
    previous: dict, receipt: dict, result: dict
) -> None:
    assert len(result["rows"]) == len(previous["rows"]) == 566
    assert result["v11_prefix_sha256"] == route.PINS["v11_ledger"]["sha256"]
    assert result["active_p1_tasks"] == previous["active_p1_tasks"]
    refs = route._selected_refs(receipt, previous)
    for old, new in zip(previous["rows"], result["rows"], strict=True):
        selected = old["task_id"] == route.TASK
        assert all(
            new[key] == value
            for key, value in old.items()
            if key != "targeted_integrated_source_ids" or not selected
        )
        assert new["targeted_integrated_source_ids"] == (
            [route.SOURCE] if selected else old["targeted_integrated_source_ids"]
        )
        assert new["v12_reviewed_source_ids"] == ([route.SOURCE] if selected else [])
        assert new["v12_source_limits"] == ({route.SOURCE: route.LIMIT} if selected else {})
        assert new["v12_source_record_refs"] == (
            {route.SOURCE: refs[old["side"]]} if selected else {}
        )
        assert new["classification"] == old["classification"]
        assert new["current_status"] == "NOT_STARTED"
        assert new["current_conclusion"] == "NOT_RUN"
        assert new["audit_task_credit"] is False
    assert result["audit_task_credit"] is result["active_pair_mutated"] is False


def test_counts_and_selected_clause_remain_unsupported(result: dict) -> None:
    for side in "AB":
        counts = result["counts"][side]
        assert counts["targeted_integrated_route_count"] == 175
        assert counts["classifications"] == {
            "DESIGN_CONTEXT_ONLY": 27,
            "SOURCE_CANDIDATE_PARTIAL": 135,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        assert counts["v12_new_selected_pol004_authored_leads"] == 1
        assert counts["v12_new_generic_promotions"] == 0
        selected = next(
            row for row in result["rows"] if row["side"] == side and row["task_id"] == route.TASK
        )
        assert selected["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
        assert selected["authored_test_clause"] == route.CLAUSE
        assert selected["remaining_test_gate"] == route.CLAUSE
        assert len(selected["v12_source_record_refs"][route.SOURCE]) == (7 if side == "A" else 9)


def test_changed_cc53_authored_clause_fails(previous: dict, receipt: dict) -> None:
    changed = deepcopy(previous)
    row = next(
        row for row in changed["rows"] if row["side"] == "A" and row["task_id"] == route.TASK
    )
    row["remaining_test_gate"] = "truncated"
    with pytest.raises(route.V12ReconciliationError, match="Exact authored POL004"):
        route._extend(changed, receipt, route.P1_FREEZE)


def test_replay_matches_tracked_ledger_and_markdown(result: dict) -> None:
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route.markdown(result) == STEM.with_suffix(".md").read_text()


def test_full_reviewed_source_and_prefix_replay() -> None:
    result = route.build(REPOSITORY, PRIVATE)
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route.markdown(result) == STEM.with_suffix(".md").read_text()
    assert route._p1_inventory(PRIVATE) == route.P1_FREEZE
