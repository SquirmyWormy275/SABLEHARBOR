"""Exact source-target IDs cannot be mistaken for completed task clauses."""

import json
from collections import Counter
from pathlib import Path

import pytest

from enterprise.audit_suite.documentary_283_route_reconciliation import (
    ReconciliationError,
    _require_review_receipt_join,
    _reviewed_receipt_sha,
    build,
    markdown,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_2026-09-29"


def test_exact_paired_denominator_and_reviewed_input_reproduction():
    result = build(REPOSITORY, PRIVATE)
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert markdown(result) == STEM.with_suffix(".md").read_text()
    assert result["audit_task_credit"] is False
    assert result["active_pair_mutated"] is False
    assert len(result["rows"]) == 566
    assert result["counts"]["A"] == result["counts"]["B"]
    assert result["counts"]["A"]["classifications"] == {
        "DESIGN_CONTEXT_ONLY": 78,
        "SOURCE_CANDIDATE_PARTIAL": 84,
        "UNSUPPORTED_EXACT_CLAUSE": 121,
    }
    assert result["counts"]["A"]["targeted_integrated_route_count"] == 93
    cross = result["counts"]["A"]["target_vs_classification"]
    assert [
        cross["TARGETED"][name]["count"]
        for name in (
            "SOURCE_CANDIDATE_PARTIAL",
            "DESIGN_CONTEXT_ONLY",
            "UNSUPPORTED_EXACT_CLAUSE",
        )
    ] == [78, 10, 5]
    assert [
        cross["UNTARGETED"][name]["count"]
        for name in (
            "SOURCE_CANDIDATE_PARTIAL",
            "DESIGN_CONTEXT_ONLY",
            "UNSUPPORTED_EXACT_CLAUSE",
        )
    ] == [6, 68, 116]
    assert set(cross["UNTARGETED"]["SOURCE_CANDIDATE_PARTIAL"]["task_ids"]) == {
        "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.302",
        "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.500",
        "TASK-SH-DAT-002-corporate-CHECK-SOC2:C1.1",
        "TASK-SH-DAT-002-corporate-CHECK-SOC2:CC6.7",
        "TASK-SH-DAT-002-corporate-IMPLEMENTATION",
        "TASK-SH-DAT-002-corporate-TOE",
    }
    assert result["counts"]["A"]["authored_clause_count"] == 154
    assert result["counts"]["A"]["inferred_gate_count"] == 129
    for side in "AB":
        selected = [row for row in result["rows"] if row["side"] == side]
        assert len(selected) == 283
        assert len({row["control_id"] for row in selected}) == 43
        assert len({row["task_id"] for row in selected}) == 283
        assert all(
            row["current_status"] == "NOT_STARTED"
            and row["current_conclusion"] == "NOT_RUN"
            and row["audit_task_credit"] is False
            and row["actual_operation_eligibility_as_of_packet"] is False
            for row in selected
        )


def test_targeted_routes_can_still_lack_the_exact_activity():
    result = build(REPOSITORY, PRIVATE)
    a = {row["task_id"]: row for row in result["rows"] if row["side"] == "A"}
    unsupported_targeted = {
        row["task_id"]
        for row in a.values()
        if row["targeted_integrated_source_ids"]
        and row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    }
    assert unsupported_targeted == {
        "TASK-SH-BCM-004-corporate-ACTION-H-EMERGENCY",
        "TASK-SH-DAT-003-corporate-CHECK-SOC2:CC6.5",
        "TASK-SH-REC-002-corporate-ACTION-H-REGULATOR",
        "TASK-SH-REC-004-corporate-ACTION-H-PHYSICAL-MOVEMENT",
        "TASK-SH-REC-004-corporate-CHECK-SOC2:CC6.5",
    }
    assert a["TASK-SH-DAT-002-corporate-ACTION-H-RIGHTS-ASSISTANCE"]["classification"] == (
        "UNSUPPORTED_EXACT_CLAUSE"
    )
    assert a["TASK-SH-POL-003-corporate-ACTION-H-ADDRESSABLE"]["classification"] == (
        "DESIGN_CONTEXT_ONLY"
    )
    provider = [row for row in a.values() if row["family"] == "provider_and_ba_contracts"]
    assert Counter(row["classification"] for row in provider) == {
        "SOURCE_CANDIDATE_PARTIAL": 16,
        "DESIGN_CONTEXT_ONLY": 3,
        "UNSUPPORTED_EXACT_CLAUSE": 66,
    }


def test_reviewed_receipt_join_rejects_missing_ambiguous_or_malformed_hash():
    digest = "a" * 64
    assert _reviewed_receipt_sha({"run_sha256": {"RECEIPT.json": digest}}) == digest
    assert _reviewed_receipt_sha({"run_receipt_sha256": digest}) == digest
    for review in (
        {},
        {"run_sha256": {"MANIFEST.json": digest}},
        {"run_receipt_sha256": "not-a-sha"},
        {"run_receipt_sha256": digest, "run_sha256": {"RECEIPT.json": digest}},
    ):
        with pytest.raises(ReconciliationError):
            _reviewed_receipt_sha(review)
    with pytest.raises(ReconciliationError, match="Review/receipt join differs"):
        _require_review_receipt_join({"run_receipt_sha256": digest}, "b" * 64, "sample")
