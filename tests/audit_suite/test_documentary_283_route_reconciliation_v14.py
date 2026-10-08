"""Exact V13 prefix and no-credit tests for reviewed ENG005 operation lead."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import documentary_283_route_reconciliation_v14 as route

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V14_2026-09-30"


@pytest.fixture(scope="module")
def previous() -> dict:
    path = REPOSITORY / route.V13_LEDGER
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["v13_ledger"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def receipt() -> dict:
    path = PRIVATE / route.SOURCE_RUN / "RECEIPT.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["eng005_receipt"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def result(previous: dict, receipt: dict) -> dict:
    return route._extend(previous, receipt, route.P1_FREEZE)


def test_reviewed_pins_and_exact_native_roster(previous: dict, receipt: dict) -> None:
    for pin in route.PINS.values():
        path = (REPOSITORY if pin["scope"] == "repo" else PRIVATE) / pin["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin["sha256"]
    refs = route._selected_refs(receipt, previous)
    assert [len(refs[side]) for side in "AB"] == [12, 22]
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        assert tuple(row["record"] for row in refs[side]) == route.ROSTER[scenario]
        assert {row["branch"] for row in refs[side]} == {route.source.BRANCHES[scenario]}
        assert all(set(row) == set(route.IDENTITY) for row in refs[side])
    assert receipt["corporate_emergency_authority_status"] == "NOT_EVIDENCED_OPEN"
    assert receipt["open_exception_counts"] == {"CLEAN": 0, "MESSY": 2}


def test_only_four_eng005_routes_extend_without_promotion(previous: dict, result: dict) -> None:
    assert len(result["rows"]) == len(previous["rows"]) == 566
    assert result["v13_prefix_sha256"] == route.PINS["v13_ledger"]["sha256"]
    assert result["active_p1_tasks"] == previous["active_p1_tasks"]
    for old, new in zip(previous["rows"], result["rows"], strict=True):
        selected = old["task_id"] in route.TARGETS
        generic = old["task_id"] in route.GENERIC
        assert all(
            new[key] == value
            for key, value in old.items()
            if key
            not in (
                {"targeted_integrated_source_ids", "candidate_or_design_source_ids"}
                if selected
                else set()
            )
        )
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
        assert new["v14_reviewed_source_ids"] == ([route.SOURCE] if selected else [])
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
        assert count["v14_new_selected_eng005_authored_leads"] == 1
        assert count["v14_new_selected_eng005_generic_leads"] == 3
        assert count["v14_new_distinct_targeted_routes"] == 0
        assert count["v14_new_classification_promotions"] == 0
        authored = next(
            row
            for row in result["rows"]
            if row["side"] == side and row["task_id"] == route.AUTHORED
        )
        assert authored["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
        assert authored["authored_test_clause"] == route.CLAUSE
        assert len(authored["v14_source_record_refs"][route.SOURCE]) == (12 if side == "A" else 22)


def test_changed_authority_native_roster_or_clause_fails(previous: dict, receipt: dict) -> None:
    for key, value in (
        ("corporate_emergency_authority_status", "APPROVED"),
        ("source_complete", True),
        ("real_deployment", True),
    ):
        changed = deepcopy(receipt)
        changed[key] = value
        with pytest.raises(route.V14ReconciliationError, match="scope or open gates"):
            route._selected_refs(changed, previous)
    changed = deepcopy(receipt)
    changed["records"]["MESSY"][-1]["record"] = "CLOSED"
    with pytest.raises(route.V14ReconciliationError, match="native original roster"):
        route._selected_refs(changed, previous)
    changed = deepcopy(receipt)
    changed["records"]["CLEAN"][0]["system"] = "change_approval"
    with pytest.raises(route.V14ReconciliationError, match="native original roster"):
        route._selected_refs(changed, previous)
    changed = deepcopy(previous)
    authored = next(
        row for row in changed["rows"] if row["side"] == "A" and row["task_id"] == route.AUTHORED
    )
    authored["remaining_test_gate"] = "shortened"
    with pytest.raises(route.V14ReconciliationError, match="authored/generic route gate"):
        route._extend(changed, receipt, route.P1_FREEZE)


def test_exact_generated_ledger_and_markdown(result: dict) -> None:
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route.markdown(result) == STEM.with_suffix(".md").read_text()


def test_full_reviewed_v13_and_company_native_replay() -> None:
    result = route.build(REPOSITORY, PRIVATE)
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route._p1_inventory(PRIVATE) == route.P1_FREEZE
