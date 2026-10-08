"""Exact V14 prefix and held PRD concern route boundaries."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import documentary_283_route_reconciliation_v15 as route

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V15_2026-09-30"


@pytest.fixture(scope="module")
def previous() -> dict:
    path = REPOSITORY / route.V14_LEDGER
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["v14_ledger"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def receipt() -> dict:
    path = PRIVATE / route.SOURCE_RUN / "RECEIPT.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["prd_receipt"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def result(previous: dict, receipt: dict) -> dict:
    return route._extend(previous, receipt, route.P1_FREEZE)


def test_exact_source_pins_and_no_delivery(receipt: dict, previous: dict) -> None:
    for pin in route.PINS.values():
        path = (REPOSITORY if pin["scope"] == "repo" else PRIVATE) / pin["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin["sha256"]
    assert receipt["selected_claimant_verified"] is False
    assert receipt["real_external_messages_sent"] == 0
    assert receipt["fictional_accepted_deliveries"] == 0
    assert receipt["customer_acknowledgments"] == 0
    assert receipt["internal_draft_status"] == {
        "CLEAN": "HELD",
        "MESSY": "HELD_AFTER_CORRECTION",
    }
    refs = route._selected_refs(receipt, previous)
    assert [len(refs[side]) for side in "AB"] == [8, 13]
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        assert tuple((row["system"], row["record"]) for row in refs[side]) == route.ROSTER[scenario]
        assert {row["branch"] for row in refs[side]} == {route.source.BRANCHES[scenario]}
        assert all(set(row) == set(route.IDENTITY) for row in refs[side])


def test_only_existing_prd_rows_extend_without_promotion(
    previous: dict, receipt: dict, result: dict
) -> None:
    assert len(result["rows"]) == len(previous["rows"]) == 566
    assert result["v14_prefix_sha256"] == route.PINS["v14_ledger"]["sha256"]
    assert result["active_p1_tasks"] == previous["active_p1_tasks"]
    refs = route._selected_refs(receipt, previous)
    for old, new in zip(previous["rows"], result["rows"], strict=True):
        selected = old["task_id"] in route.TARGETS
        generic = old["task_id"] in route.GENERIC
        allowed = {"targeted_integrated_source_ids"} if selected else set()
        if generic:
            allowed.add("candidate_or_design_source_ids")
        assert all(new[key] == value for key, value in old.items() if key not in allowed)
        assert new["targeted_integrated_source_ids"] == (
            [*old["targeted_integrated_source_ids"], route.SOURCE]
            if selected
            else old["targeted_integrated_source_ids"]
        )
        assert new["candidate_or_design_source_ids"] == (
            [*old["candidate_or_design_source_ids"], route.SOURCE]
            if generic
            else old["candidate_or_design_source_ids"]
        )
        assert new["v15_reviewed_source_ids"] == ([route.SOURCE] if selected else [])
        assert new["v15_source_record_refs"] == (
            {route.SOURCE: refs[old["side"]]} if selected else {}
        )
        assert new["classification"] == old["classification"]
        assert new["remaining_test_gate"] == old["remaining_test_gate"]
        assert new["current_status"] == "NOT_STARTED"
        assert new["current_conclusion"] == "NOT_RUN"
        assert new["audit_task_credit"] is False
    assert result["audit_task_credit"] is result["active_pair_mutated"] is False


def test_counts_and_authored_limits_persist(result: dict) -> None:
    for side in "AB":
        count = result["counts"][side]
        assert count["targeted_integrated_route_count"] == 175
        assert count["classifications"] == {
            "DESIGN_CONTEXT_ONLY": 27,
            "SOURCE_CANDIDATE_PARTIAL": 135,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        assert count["v15_new_selected_prd_authored_leads"] == 3
        assert count["v15_new_selected_prd_generic_leads"] == 9
        assert count["v15_new_distinct_targeted_routes"] == 0
        assert count["v15_new_classification_promotions"] == 0
        for task_id in route.AUTHORED:
            row = next(
                row for row in result["rows"] if row["side"] == side and row["task_id"] == task_id
            )
            assert row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
            assert row["authored_test_clause"] == route.CLAUSE
            assert len(row["v15_source_record_refs"][route.SOURCE]) == (8 if side == "A" else 13)


def test_tampered_held_boundary_roster_or_clause_fails(previous: dict, receipt: dict) -> None:
    for key, value in (
        ("selected_claimant_verified", True),
        ("fictional_accepted_deliveries", 1),
        ("customer_acknowledgments", 1),
        ("source_complete", True),
    ):
        changed = deepcopy(receipt)
        changed[key] = value
        with pytest.raises(route.V15ReconciliationError, match="source scope or held gate"):
            route._selected_refs(changed, previous)
    changed = deepcopy(receipt)
    changed["records"]["MESSY"][-1]["record"] = "DELIVERED"
    with pytest.raises(route.V15ReconciliationError, match="native original roster"):
        route._selected_refs(changed, previous)
    changed = deepcopy(previous)
    row = next(
        row for row in changed["rows"] if row["side"] == "A" and row["task_id"] == route.AUTHORED[0]
    )
    row["remaining_test_gate"] = "partial receipt is enough"
    with pytest.raises(route.V15ReconciliationError, match="authored/generic route gate"):
        route._extend(changed, receipt, route.P1_FREEZE)
    changed = deepcopy(previous)
    row = next(
        row for row in changed["rows"] if row["side"] == "B" and row["task_id"] == route.GENERIC[0]
    )
    row["targeted_integrated_source_ids"] = []
    with pytest.raises(route.V15ReconciliationError, match="authored/generic route gate"):
        route._extend(changed, receipt, route.P1_FREEZE)


def test_exact_generated_ledger_and_markdown(result: dict) -> None:
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route.markdown(result) == STEM.with_suffix(".md").read_text()


def test_full_reviewed_v14_and_company_native_replay() -> None:
    result = route.build(REPOSITORY, PRIVATE)
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route._p1_inventory(PRIVATE) == route.P1_FREEZE
