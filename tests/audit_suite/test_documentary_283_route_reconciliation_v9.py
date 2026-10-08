"""A pending addressable inventory supplies only one design-context route lead."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import documentary_283_route_reconciliation_v9 as route
from enterprise.audit_suite.documentary_283_route_reconciliation_v9 import V9ReconciliationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V9_2026-09-30"


@pytest.fixture(scope="module")
def previous():
    path = REPOSITORY / route.V8_LEDGER
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["v8_ledger"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def receipt():
    path = PRIVATE / route.ADDR_RUN / "RECEIPT.json"
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["addressable_receipt"]["sha256"]
    )
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def result():
    return route.build(REPOSITORY, PRIVATE)


def test_reviewed_builder_reproduces_exact_isolated_json_and_markdown(result):
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route.markdown(result) == STEM.with_suffix(".md").read_text()
    assert result["p1_freeze"] == route.P1_FREEZE
    assert result["audit_task_credit"] is result["active_pair_mutated"] is False
    assert result["active_p1_tasks"] == {
        side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"} for side in "AB"
    }


def test_every_v8_row_field_and_class_is_preserved(previous, result):
    assert len(previous["rows"]) == len(result["rows"]) == 566
    for before, after in zip(previous["rows"], result["rows"], strict=True):
        assert all(
            after[key] == value
            for key, value in before.items()
            if key != "targeted_integrated_source_ids"
        )
        assert after["classification"] == before["classification"]
        if before["task_id"] != route.ACTION:
            assert (
                after["targeted_integrated_source_ids"] == before["targeted_integrated_source_ids"]
            )
    for side in "AB":
        assert result["counts"][side]["classifications"] == {
            "DESIGN_CONTEXT_ONLY": 30,
            "SOURCE_CANDIDATE_PARTIAL": 132,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        assert result["counts"][side]["targeted_integrated_route_count"] == 170


def test_only_action_h_receives_pending_design_context(result):
    for side in "AB":
        rows = [row for row in result["rows"] if row["side"] == side]
        leads = [row for row in rows if row["v9_reviewed_source_ids"]]
        assert len(leads) == 1
        assert leads[0]["task_id"] == route.ACTION
        assert leads[0]["classification"] == "DESIGN_CONTEXT_ONLY"
        assert leads[0]["remaining_test_gate"] == leads[0]["authored_test_clause"]
        assert leads[0]["current_status"] == "NOT_STARTED"
        assert leads[0]["current_conclusion"] == "NOT_RUN"
        assert leads[0]["audit_task_credit"] is False
        assert len(leads[0]["v9_source_record_refs"][route.SOURCE]) == 23
        assert {ref["record"] for ref in leads[0]["v9_source_record_refs"][route.SOURCE]} == {
            *(f"SPEC-{index:02d}" for index in range(1, 23)),
            "GATE-02" if side == "A" else "GATE-04",
        }
        generic = [row for row in rows if row["task_id"] in route.GENERIC]
        assert len(generic) == 3
        assert all(row["v9_reviewed_source_ids"] == [] for row in generic)
        assert all(row["v9_source_limits"] == {} for row in generic)
        assert all(row["v9_source_record_refs"] == {} for row in generic)


def test_pending_cases_and_messy_waiver_are_not_promoted(receipt):
    refs = route._selected_refs(receipt, PRIVATE / route.ADDR_RUN / "company.sqlite3")
    assert {side: len(rows) for side, rows in refs.items()} == {"A": 23, "B": 23}
    assert receipt["final_states"] == {"CLEAN": "PENDING_REVIEW", "MESSY": "QUARANTINED"}
    assert receipt["open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert receipt["related_sh_pol003_gap"] == "OPEN_INSUFFICIENT_SOURCE_UNCHANGED"
    changed = deepcopy(receipt)
    changed["final_states"]["CLEAN"] = "APPROVED"
    with pytest.raises(V9ReconciliationError, match="Pending addressable docket boundary"):
        route._selected_refs(changed, PRIVATE / route.ADDR_RUN / "company.sqlite3")
    damaged = deepcopy(receipt)
    next(ref for ref in damaged["records"]["MESSY"] if ref["record"] == "SPEC-22")["sha256"] = (
        "0" * 64
    )
    with pytest.raises(V9ReconciliationError, match="Selected addressable native tuple"):
        route._selected_refs(damaged, PRIVATE / route.ADDR_RUN / "company.sqlite3")


def test_changed_action_class_and_review_pin_fail_closed(previous, receipt, monkeypatch):
    damaged = deepcopy(previous)
    for row in damaged["rows"]:
        if row["task_id"] == route.ACTION:
            row["classification"] = "SOURCE_CANDIDATE_PARTIAL"
    with pytest.raises(V9ReconciliationError, match="Addressable authored action boundary"):
        route._extend(
            damaged, receipt, PRIVATE / route.ADDR_RUN / "company.sqlite3", route.P1_FREEZE
        )
    monkeypatch.setitem(route.PINS["v10_review"], "sha256", "0" * 64)
    with pytest.raises(route.pinned.V3ReconciliationError, match="Pinned input differs"):
        route.build(REPOSITORY, PRIVATE)
