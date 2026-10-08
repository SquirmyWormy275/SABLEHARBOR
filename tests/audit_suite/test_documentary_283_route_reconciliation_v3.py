"""The 21-source route successor is candidate-only and exact-clause bounded."""

import copy
import json
from collections import Counter
from pathlib import Path

import pytest

from enterprise.audit_suite import documentary_283_route_reconciliation as prior
from enterprise.audit_suite.documentary_283_route_reconciliation_v3 import (
    PINS,
    V3ReconciliationError,
    _check_source,
    build,
    markdown,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
PORTFOLIO = PRIVATE
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V3_2026-09-29"


def test_exact_paired_routes_and_no_credit():
    result = build(REPOSITORY, PRIVATE, PORTFOLIO)
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert markdown(result) == STEM.with_suffix(".md").read_text()
    assert result["reviewed_source_roster"] == {
        "cohorts": 21,
        "native_versions": 358,
        "source_complete": False,
    }
    assert len(result["rows"]) == 566
    assert result["counts"]["A"] == result["counts"]["B"]
    for side in "AB":
        rows = [row for row in result["rows"] if row["side"] == side]
        assert len(rows) == 283
        assert len({row["task_id"] for row in rows}) == 283
        assert len({row["control_id"] for row in rows}) == 43
        assert Counter(row["classification"] for row in rows) == {
            "SOURCE_CANDIDATE_PARTIAL": 108,
            "DESIGN_CONTEXT_ONLY": 54,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        assert all(
            row["current_status"] == "NOT_STARTED"
            and row["current_conclusion"] == "NOT_RUN"
            and row["actual_operation_eligibility_as_of_packet"] is False
            and row["audit_task_credit"] is False
            for row in rows
        )
    assert result["audit_task_credit"] is False
    assert result["active_pair_mutated"] is False


def test_newly_targeted_authored_clauses_remain_unsupported():
    result = build(REPOSITORY, PRIVATE, PORTFOLIO)
    old = prior.build(REPOSITORY, PRIVATE)
    old_rows = {(row["side"], row["task_id"]): row for row in old["rows"]}
    changed = [
        row
        for row in result["rows"]
        if row["classification"] != old_rows[row["side"], row["task_id"]]["classification"]
    ]
    assert len(changed) == 48
    assert all(
        row["authored_test_clause"] is None
        and old_rows[row["side"], row["task_id"]]["classification"] == "DESIGN_CONTEXT_ONLY"
        and row["classification"] == "SOURCE_CANDIDATE_PARTIAL"
        for row in changed
    )
    for side in "AB":
        authored = [
            row
            for row in result["rows"]
            if row["side"] == side
            and row["control_id"]
            in {
                "SH-ENG-005",
                "SH-PRD-002",
                "SH-PRD-003",
                "SH-PRD-004",
                "SH-ETH-003",
                "SH-ETH-004",
                "SH-IAM-005",
            }
            and row["authored_test_clause"] is not None
        ]
        assert len(authored) == 9
        assert all(row["classification"] == "UNSUPPORTED_EXACT_CLAUSE" for row in authored)


def test_source_join_rejects_task_credit_or_clause_drift():
    pins = json.loads((REPOSITORY / PINS).read_text())
    old = prior.build(REPOSITORY, PRIVATE)
    source_root = PRIVATE / "enterprise/generated/audit-suite"
    prd = json.loads(
        (source_root / "company-prd-internal-customer-2026-09-29/run-v2/RECEIPT.json").read_text()
    )
    review = json.loads(
        (
            source_root
            / "company-prd-internal-customer-2026-09-29/independent-review-v2/REVIEW.json"
        ).read_text()
    )
    loaded = {"prd_receipt": prd, "prd_review": review}
    changed = copy.deepcopy(loaded)
    changed["prd_receipt"]["audit_task_credit"] = True
    with pytest.raises(V3ReconciliationError, match="grants credit"):
        _check_source("prd", changed, pins, old)
    changed = copy.deepcopy(loaded)
    changed["prd_receipt"]["selected_route_authority"]["A"]["task_ids"][0] = "TASK-OTHER"
    with pytest.raises(V3ReconciliationError, match="Exact selected task IDs"):
        _check_source("prd", changed, pins, old)
