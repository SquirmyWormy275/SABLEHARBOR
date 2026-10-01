"""The exact ETH001 route delta requires reviewed V11 candidate targeting."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import documentary_283_route_reconciliation_v10 as route
from enterprise.audit_suite.documentary_283_route_reconciliation_v10 import V10ReconciliationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V10_2026-09-30"


@pytest.fixture(scope="module")
def previous():
    path = REPOSITORY / route.V9_LEDGER
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["v9_ledger"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def receipt():
    path = PRIVATE / route.ETH_RUN / "SOURCE_RECEIPT.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == route.PINS["eth_receipt"]["sha256"]
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def result():
    return route.build(REPOSITORY, PRIVATE)


def test_v9_prefix_exact_generic_and_authored_eth001_boundaries(previous):
    assert len(previous["rows"]) == 566
    for side in "AB":
        rows = [row for row in previous["rows"] if row["side"] == side]
        generic = [row for row in rows if row["task_id"] in route.GENERIC]
        sanctions = next(row for row in rows if row["task_id"] == route.SANCTIONS)
        assert len(rows) == 283
        assert len(generic) == 3
        assert all(row["classification"] == "DESIGN_CONTEXT_ONLY" for row in generic)
        assert all(row["authored_test_clause"] is None for row in generic)
        assert all(row["targeted_integrated_source_ids"] == [] for row in generic)
        assert sanctions["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
        assert sanctions["remaining_test_gate"] == sanctions["authored_test_clause"]
        assert sanctions["targeted_integrated_source_ids"] == []
        assert previous["counts"][side]["classifications"] == {
            "DESIGN_CONTEXT_ONLY": 30,
            "SOURCE_CANDIDATE_PARTIAL": 132,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        assert previous["counts"][side]["targeted_integrated_route_count"] == 170


def test_selected_native_refs_are_exact_and_keep_messy_history(receipt):
    refs = route._selected_refs(receipt)
    assert [len(refs[s]["TOE"]) for s in "AB"] == [8, 11]
    for side, branch in (("A", "ETH001-CLEAN"), ("B", "ETH001-MESSY")):
        assert {
            ref["branch"]
            for suffix in ("IMPLEMENTATION", "TOD", "TOE")
            for ref in refs[side][suffix]
        } == {branch}
        assert [ref["record"] for ref in refs[side]["IMPLEMENTATION"]] == [
            "FICTIONAL-LOCAL-APPROVAL",
            "SELECTED-ROSTER",
        ]
        assert [ref["record"] for ref in refs[side]["TOD"]] == [
            "DRAFT",
            "FICTIONAL-LOCAL-APPROVAL",
            "SELECTED-ROSTER",
        ]
        assert all(set(ref) == set(route.IDENTITY) for ref in refs[side]["TOE"])
    assert [ref["record"] for ref in refs["B"]["TOE"]][-5:] == [
        "FALSE-CLEAN",
        "MISSING-DISCOVERY",
        "LATE-ACK-AS-P013",
        "CORRECTION",
        "FINAL",
    ]


def test_source_authority_drift_fails_closed(receipt):
    changed = deepcopy(receipt)
    changed["messy_historical_false_clean_exception_open"] = False
    with pytest.raises(V10ReconciliationError, match="Selected conduct authority boundary"):
        route._selected_refs(changed)
    changed = deepcopy(receipt)
    changed["native_originals"][0]["record"] = "UNREVIEWED"
    with pytest.raises(V10ReconciliationError, match="Selected conduct native roster"):
        route._selected_refs(changed)


def test_build_reproduces_tracked_json_markdown_and_frozen_p1(result):
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route.markdown(result) == STEM.with_suffix(".md").read_text()
    assert result["p1_freeze"] == route.P1_FREEZE
    assert result["audit_task_credit"] is result["active_pair_mutated"] is False
    assert result["active_p1_tasks"] == {
        side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"} for side in "AB"
    }
    assert result["source_pins"]["v11_review"]["sha256"] == (
        "559cbd325ce84e736417576ece134c4f0959d849bd775af0761ad5bd6881b615"
    )
    assert result["reviewed_source_roster"]["additional_selected_eth001_cohort_versions"] == 19


def test_only_three_generic_rows_promote_and_every_prior_field_is_retained(previous, result):
    assert len(previous["rows"]) == len(result["rows"]) == 566
    permitted = {
        "classification",
        "candidate_or_design_source_ids",
        "targeted_integrated_source_ids",
    }
    for before, after in zip(previous["rows"], result["rows"], strict=True):
        assert all(after[key] == value for key, value in before.items() if key not in permitted)
        selected = before["task_id"] in route.GENERIC
        for key in permitted:
            if not selected:
                assert after[key] == before[key]
        if selected:
            assert before["classification"] == "DESIGN_CONTEXT_ONLY"
            assert after["classification"] == "SOURCE_CANDIDATE_PARTIAL"
            assert after["candidate_or_design_source_ids"] == [route.SOURCE]
            assert after["targeted_integrated_source_ids"] == [route.SOURCE]
            assert after["v10_reviewed_source_ids"] == [route.SOURCE]
            assert after["v10_source_limits"][route.SOURCE] == route.LIMIT
        else:
            assert after["v10_reviewed_source_ids"] == []
            assert after["v10_source_limits"] == {}
            assert after["v10_source_record_refs"] == {}
    for side in "AB":
        assert result["counts"][side]["classifications"] == {
            "DESIGN_CONTEXT_ONLY": 27,
            "SOURCE_CANDIDATE_PARTIAL": 135,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        assert result["counts"][side]["targeted_integrated_route_count"] == 173
        assert result["counts"][side]["authored_clause_count"] == 154
        assert result["counts"][side]["inferred_gate_count"] == 129
        sanctions = next(
            row
            for row in result["rows"]
            if row["side"] == side and row["task_id"] == route.SANCTIONS
        )
        assert sanctions["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
        assert sanctions["remaining_test_gate"] == sanctions["authored_test_clause"]
        assert sanctions["targeted_integrated_source_ids"] == []
        assert sanctions["v10_reviewed_source_ids"] == []


def test_exact_native_refs_on_only_selected_rows(result, receipt):
    selected = route._selected_refs(receipt)
    for side in "AB":
        rows = [row for row in result["rows"] if row["side"] == side]
        leads = [row for row in rows if row["v10_reviewed_source_ids"]]
        assert {row["task_id"] for row in leads} == set(route.GENERIC)
        for row in leads:
            suffix = route.GENERIC[row["task_id"]]
            assert row["v10_source_record_refs"][route.SOURCE] == selected[side][suffix]
        assert all(row["authored_test_clause"] is None for row in leads)
        assert all(row["audit_task_credit"] is False for row in leads)


def test_review_pins_and_unqualified_delta_fail_closed(previous, receipt, monkeypatch):
    assert route.V11_ACCEPTED["pins"]["v11_review"]["sha256"] == (
        "559cbd325ce84e736417576ece134c4f0959d849bd775af0761ad5bd6881b615"
    )
    for label, pin in (
        ("portfolio_report", "v11_portfolio"),
        ("candidate_A", "v11_candidate_a"),
        ("candidate_B", "v11_candidate_b"),
        ("candidate_report", "v11_candidate_report"),
    ):
        assert route.PROSPECTIVE_V11[label] == route.V11_ACCEPTED["pins"][pin]["sha256"]
    with pytest.raises(V10ReconciliationError, match="accepted candidate verification required"):
        route._extend(previous, receipt, route.P1_FREEZE, qualification=None)
    monkeypatch.setitem(route.V11_ACCEPTED["pins"]["v11_review"], "sha256", "0" * 64)
    with pytest.raises(route.pinned.V3ReconciliationError, match="Pinned input differs"):
        route._accepted_v11(REPOSITORY, PRIVATE, route.P1_FREEZE)


def test_changed_generic_or_sanctions_boundary_fails_closed(previous, receipt):
    damaged = deepcopy(previous)
    for row in damaged["rows"]:
        if row["task_id"] == "TASK-SH-ETH-001-corporate-TOE":
            row["classification"] = "SOURCE_CANDIDATE_PARTIAL"
    with pytest.raises(V10ReconciliationError, match="Generic ETH001 route boundary"):
        route._extend(damaged, receipt, route.P1_FREEZE, qualification=route._ACCEPTED_TOKEN)
    damaged = deepcopy(previous)
    for row in damaged["rows"]:
        if row["task_id"] == route.SANCTIONS:
            row["targeted_integrated_source_ids"] = [route.SOURCE]
    with pytest.raises(V10ReconciliationError, match="Authored sanctions route boundary"):
        route._extend(damaged, receipt, route.P1_FREEZE, qualification=route._ACCEPTED_TOKEN)
