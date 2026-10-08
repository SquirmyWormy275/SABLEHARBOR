"""SEC001 exact-clause route preparation fails closed until reviewed V12."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import documentary_283_route_reconciliation_v11 as route
from enterprise.audit_suite.documentary_283_route_reconciliation_v11 import V11ReconciliationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V11_2026-09-30"


@pytest.fixture(scope="module")
def previous():
    path = REPOSITORY / route.V10_LEDGER
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["v10_ledger"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def receipt():
    path = PRIVATE / route.SEC_RUN / "SOURCE_RECEIPT.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["sec_receipt"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def result():
    return route.build(REPOSITORY, PRIVATE)


def test_exact_v10_prefix_and_cc67_authored_gate(previous):
    assert len(previous["rows"]) == 566
    assert previous["p1_freeze"] == route.P1_FREEZE
    assert previous["active_p1_tasks"] == {
        side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"} for side in "AB"
    }
    for side in "AB":
        rows = [row for row in previous["rows"] if row["side"] == side]
        selected = [row for row in rows if row["task_id"] == route.TASK]
        assert len(rows) == 283 and len(selected) == 1
        assert selected[0]["authored_test_clause"] == route.CLAUSE
        assert selected[0]["remaining_test_gate"] == route.CLAUSE
        assert selected[0]["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
        assert selected[0]["targeted_integrated_source_ids"] == []
        assert previous["counts"][side]["classifications"] == {
            "DESIGN_CONTEXT_ONLY": 27,
            "SOURCE_CANDIDATE_PARTIAL": 135,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        assert previous["counts"][side]["targeted_integrated_route_count"] == 173


def test_selected_native_refs_cover_causal_and_adverse_chains(receipt):
    refs = route._selected_refs(receipt)
    assert [len(refs[side]) for side in "AB"] == [10, 16]
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        assert [ref["record"] for ref in refs[side]] == [
            record for _, record, _, _ in route.transfer.PLAN[scenario]
        ]
        assert {ref["branch"] for ref in refs[side]} == {route.transfer.BRANCHES[scenario]}
        assert all(set(ref) == set(route.IDENTITY) for ref in refs[side])
    assert [ref["record"] for ref in refs["B"]][-6:] == [
        "FALSE-CLOSE",
        "GAP-DISCOVERY",
        "RECEIPT",
        "HANDLING",
        "CORRECTION",
        "FINAL",
    ]


def test_source_authority_and_exact_native_roster_drift_fail_closed(receipt):
    changed = deepcopy(receipt)
    changed["actual_network_transmission"] = True
    with pytest.raises(V11ReconciliationError, match="authority or route boundary"):
        route._selected_refs(changed)
    changed = deepcopy(receipt)
    changed["messy_historical_exception_open"] = False
    with pytest.raises(V11ReconciliationError, match="authority or route boundary"):
        route._selected_refs(changed)
    changed = deepcopy(receipt)
    changed["native_originals"][0]["record"] = "UNREVIEWED"
    with pytest.raises(V11ReconciliationError, match="native roster"):
        route._selected_refs(changed)


def test_main_review_and_source_pins_are_specific():
    assert route.PINS["v10_review"]["sha256"] == (
        "b702667f9f480774c07d160c31939250c7ad76a65661a1f7c8c41f23e068b674"
    )
    assert route.PINS["sec_review"]["sha256"] == (
        "9cf4d438d7b191f227f87f3dcb5cf6d36bcb3e7e490415d16cff11e72a33c196"
    )
    for entry in route.PINS.values():
        path = (REPOSITORY if entry["scope"] == "repo" else PRIVATE) / entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
    source_review = json.loads((PRIVATE / route.SEC_REVIEW).read_text())
    assert source_review["selected_task_id"] == route.TASK
    assert source_review["selected_authored_clause"] == route.CLAUSE
    assert source_review["source_complete"] is source_review["audit_task_credit"] is False


def test_accepted_v12_main_local_pins_and_unqualified_delta(previous, receipt, monkeypatch):
    assert route.V12_ACCEPTED["pins"]["v12_review"]["sha256"] == (
        "053dca8df77c5fb990daf7844a62a792276b89100dfef8df1d564f04df841400"
    )
    for entry in route.V12_ACCEPTED["pins"].values():
        assert entry["scope"] == "private"
        assert hashlib.sha256((PRIVATE / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
    with pytest.raises(V11ReconciliationError, match="accepted candidate verification required"):
        route._extend(previous, receipt, route.P1_FREEZE, qualification=None)
    monkeypatch.setitem(route.V12_ACCEPTED["pins"]["v12_review"], "sha256", "0" * 64)
    with pytest.raises(route.pinned.V3ReconciliationError, match="Pinned input differs"):
        route._accepted_v12(REPOSITORY, PRIVATE, route.P1_FREEZE)


def test_build_fails_closed_without_accepted_v12(monkeypatch):
    monkeypatch.setattr(route, "V12_ACCEPTED", None)
    with pytest.raises(V11ReconciliationError, match="V12 main-local review"):
        route.build(REPOSITORY, PRIVATE)


def test_in_memory_delta_changes_only_cc67_targeting_after_qualification(previous, receipt):
    """Exercise exact row arithmetic after the accepted V12 review."""
    result = route._extend(previous, receipt, route.P1_FREEZE, qualification=route._ACCEPTED_TOKEN)
    assert len(result["rows"]) == 566
    assert result["active_p1_tasks"] == previous["active_p1_tasks"]
    assert result["reviewed_source_roster"] == {
        **previous["reviewed_source_roster"],
        "additional_selected_sec001_cohort_versions": 26,
    }
    for before, after in zip(previous["rows"], result["rows"], strict=True):
        assert all(after[key] == value for key, value in before.items()) or (
            before["task_id"] == route.TASK
            and all(
                after[key] == value
                for key, value in before.items()
                if key != "targeted_integrated_source_ids"
            )
        )
        if before["task_id"] == route.TASK:
            assert before["targeted_integrated_source_ids"] == []
            assert after["targeted_integrated_source_ids"] == [route.SOURCE]
            assert after["v11_reviewed_source_ids"] == [route.SOURCE]
            assert after["v11_source_limits"] == {route.SOURCE: route.LIMIT}
            assert len(after["v11_source_record_refs"][route.SOURCE]) == (
                10 if before["side"] == "A" else 16
            )
            assert after["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
            assert after["remaining_test_gate"] == route.CLAUSE
            assert after["audit_task_credit"] is False
        else:
            assert after["v11_reviewed_source_ids"] == []
            assert after["v11_source_limits"] == {}
            assert after["v11_source_record_refs"] == {}
    for side in "AB":
        assert (
            result["counts"][side]["classifications"] == previous["counts"][side]["classifications"]
        )
        assert result["counts"][side]["targeted_integrated_route_count"] == 174
        assert result["counts"][side]["v11_new_selected_sec001_authored_leads"] == 1
        assert result["counts"][side]["v11_new_generic_promotions"] == 0
    assert result["audit_task_credit"] is result["active_pair_mutated"] is False


def test_in_memory_delta_rejects_changed_authored_gate(previous, receipt):
    changed = deepcopy(previous)
    for row in changed["rows"]:
        if row["task_id"] == route.TASK and row["side"] == "A":
            row["remaining_test_gate"] = "truncated"
    with pytest.raises(V11ReconciliationError, match="Authored SEC001 route boundary"):
        route._extend(changed, receipt, route.P1_FREEZE, qualification=route._ACCEPTED_TOKEN)


def test_build_reproduces_tracked_json_markdown_and_frozen_p1(result):
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route.markdown(result) == STEM.with_suffix(".md").read_text()
    assert result["counts"]["A"] == result["counts"]["B"]
    assert result["p1_freeze"] == route.P1_FREEZE
    assert result["active_p1_tasks"] == {
        side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"} for side in "AB"
    }
    assert result["source_pins"]["v12_review"]["sha256"] == (
        "053dca8df77c5fb990daf7844a62a792276b89100dfef8df1d564f04df841400"
    )
    assert result["audit_task_credit"] is result["active_pair_mutated"] is False
