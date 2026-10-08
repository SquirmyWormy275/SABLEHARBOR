"""Exact V15 prefix and selected governance route boundaries."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import documentary_283_route_reconciliation_v16 as route

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V16_2026-10-01"


@pytest.fixture(scope="module")
def previous() -> dict:
    path = REPOSITORY / route.V15_LEDGER
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["v15_ledger"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def receipt() -> dict:
    path = PRIVATE / route.SOURCE_RUN / "RECEIPT.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["gov_receipt"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def result(previous: dict, receipt: dict) -> dict:
    return route._extend(previous, receipt, route.P1_FREEZE)


def test_reviewed_pins_and_exact_branch_roster(previous: dict, receipt: dict) -> None:
    for pin in route.PINS.values():
        path = (REPOSITORY if pin["scope"] == "repo" else PRIVATE) / pin["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin["sha256"]
    assert receipt["actual_board_meeting"] is False
    assert receipt["legal_quorum_established"] is False
    assert receipt["adopted_minutes"] is False
    assert receipt["authored_cc12_clause_satisfied"] is False
    assert receipt["messy_historical_governance_exception_status"] == "OPEN"
    refs = route._selected_refs(receipt, previous)
    assert [len(refs[side]) for side in "AB"] == [9, 14]
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        assert tuple((row["system"], row["record"]) for row in refs[side]) == route.ROSTER[scenario]
        assert {row["branch"] for row in refs[side]} == {route.source.BRANCHES[scenario]}
        assert {item["branch"] for item in receipt["upstream_original_refs"][scenario]} == {
            route.source.sec3.BRANCHES[scenario]
        }
        assert all(set(row) == set(route.IDENTITY) for row in refs[side])


def test_only_eight_gov_routes_extend_and_six_generic_promote(previous: dict, result: dict) -> None:
    assert len(result["rows"]) == len(previous["rows"]) == 566
    assert previous["as_of"] == "2026-09-30"
    assert result["as_of"] == "2026-10-01"
    assert result["v15_prefix_sha256"] == route.PINS["v15_ledger"]["sha256"]
    assert result["active_p1_tasks"] == previous["active_p1_tasks"]
    for old, new in zip(previous["rows"], result["rows"], strict=True):
        selected = old["task_id"] in route.TARGETS
        generic = old["task_id"] in route.GENERIC
        allowed = {"targeted_integrated_source_ids"} if selected else set()
        if generic:
            allowed.update(("candidate_or_design_source_ids", "classification"))
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
        assert new["classification"] == (
            "SOURCE_CANDIDATE_PARTIAL" if generic else old["classification"]
        )
        assert new["v16_reviewed_source_ids"] == ([route.SOURCE] if selected else [])
        assert new["v16_source_record_refs"] == (
            {
                route.SOURCE: [
                    {key: ref[key] for key in route.IDENTITY}
                    for ref in json.loads(
                        (PRIVATE / route.SOURCE_RUN / "RECEIPT.json").read_text()
                    )["records"]["CLEAN" if old["side"] == "A" else "MESSY"]
                ]
            }
            if selected
            else {}
        )
        assert new["current_status"] == "NOT_STARTED"
        assert new["current_conclusion"] == "NOT_RUN"
        assert new["audit_task_credit"] is False
    assert result["audit_task_credit"] is result["active_pair_mutated"] is False


def test_counts_and_authored_limits_persist(result: dict) -> None:
    for side in "AB":
        count = result["counts"][side]
        assert count["targeted_integrated_route_count"] == 183
        assert count["classifications"] == {
            "DESIGN_CONTEXT_ONLY": 21,
            "SOURCE_CANDIDATE_PARTIAL": 141,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        assert count["v16_new_selected_gov_authored_leads"] == 2
        assert count["v16_new_selected_gov_generic_leads"] == 6
        assert count["v16_new_distinct_targeted_routes"] == 8
        assert count["v16_new_classification_promotions"] == 6
        for task_id in route.AUTHORED:
            row = next(
                row for row in result["rows"] if row["side"] == side and row["task_id"] == task_id
            )
            assert row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
            assert row["authored_test_clause"] == route.CLAUSE
            assert len(row["v16_source_record_refs"][route.SOURCE]) == (9 if side == "A" else 14)


def test_tampered_authority_branch_roster_or_gate_fails(previous: dict, receipt: dict) -> None:
    changed = deepcopy(previous)
    changed["as_of"] = "2026-10-01"
    with pytest.raises(route.V16ReconciliationError, match="Reviewed V15 route prefix"):
        route._extend(changed, receipt, route.P1_FREEZE)
    for key, value in (
        ("actual_board_meeting", True),
        ("adopted_minutes", True),
        ("authored_cc12_clause_satisfied", True),
        ("source_complete", True),
    ):
        changed = deepcopy(receipt)
        changed[key] = value
        with pytest.raises(route.V16ReconciliationError, match="scope or authority"):
            route._selected_refs(changed, previous)
    changed = deepcopy(receipt)
    changed["upstream_original_refs"]["CLEAN"][0]["branch"] = route.source.sec3.BRANCHES["MESSY"]
    with pytest.raises(route.V16ReconciliationError, match="branch native roster"):
        route._selected_refs(changed, previous)
    changed = deepcopy(receipt)
    changed["records"]["MESSY"][-1]["record"] = "ADOPTED-MINUTES"
    with pytest.raises(route.V16ReconciliationError, match="branch native roster"):
        route._selected_refs(changed, previous)
    changed = deepcopy(previous)
    authored = next(
        row for row in changed["rows"] if row["side"] == "A" and row["task_id"] == route.AUTHORED[0]
    )
    authored["remaining_test_gate"] = "calendar is sufficient"
    with pytest.raises(route.V16ReconciliationError, match="authored/generic route gate"):
        route._extend(changed, receipt, route.P1_FREEZE)
    changed = deepcopy(previous)
    generic = next(
        row for row in changed["rows"] if row["side"] == "B" and row["task_id"] == route.GENERIC[0]
    )
    generic["classification"] = "SOURCE_CANDIDATE_PARTIAL"
    with pytest.raises(route.V16ReconciliationError, match="authored/generic route gate"):
        route._extend(changed, receipt, route.P1_FREEZE)


def test_exact_generated_ledger_and_markdown(result: dict) -> None:
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route.markdown(result) == STEM.with_suffix(".md").read_text()


def test_full_reviewed_v15_and_company_native_replay() -> None:
    result = route.build(REPOSITORY, PRIVATE)
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route._p1_inventory(PRIVATE) == route.P1_FREEZE
