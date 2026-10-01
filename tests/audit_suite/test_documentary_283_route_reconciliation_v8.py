"""Selected LEG001 leads keep the authored and frozen audit boundaries intact."""

import copy
import json
from collections import Counter
from pathlib import Path

import pytest

from enterprise.audit_suite.documentary_283_route_reconciliation_v8 import (
    IMMUTABLE,
    SOURCE,
    V8ReconciliationError,
    _selected_routes,
    build,
    markdown,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V8_2026-09-30"
V7 = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V7_2026-09-30.json"
RECEIPT = (
    PRIVATE
    / "enterprise/generated/audit-suite/company-leg001-operating-docket-2027-09-30"
    / "main-run-v1/RECEIPT.json"
)


@pytest.fixture(scope="module")
def result():
    return build(REPOSITORY, PRIVATE)


def test_exact_successor_retains_pair_and_every_task_clause(result):
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert markdown(result) == STEM.with_suffix(".md").read_text()
    assert result["p1_freeze"]["file_count"] == 538
    assert result["active_p1_tasks"] == {
        side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"} for side in "AB"
    }
    assert result["audit_task_credit"] is False
    assert result["active_pair_mutated"] is False
    previous = json.loads(V7.read_text())
    assert result["reviewed_source_roster"] == {
        **previous["reviewed_source_roster"],
        "additional_legal_docket_cohort_versions": 100,
    }
    old = {(row["side"], row["task_id"]): row for row in previous["rows"]}
    for side in "AB":
        rows = [row for row in result["rows"] if row["side"] == side]
        assert len(rows) == len({row["task_id"] for row in rows}) == 283
        assert len({row["control_id"] for row in rows}) == 43
        assert Counter(row["classification"] for row in rows) == {
            "SOURCE_CANDIDATE_PARTIAL": 132,
            "DESIGN_CONTEXT_ONLY": 30,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        assert sum(bool(row["targeted_integrated_source_ids"]) for row in rows) == 169
        for row in rows:
            prior = old[side, row["task_id"]]
            assert all(row[key] == prior[key] for key in IMMUTABLE)
            assert row["classification"] == prior["classification"]
            if SOURCE not in row["v8_reviewed_source_ids"]:
                assert (
                    row["targeted_integrated_source_ids"] == prior["targeted_integrated_source_ids"]
                )
                assert (
                    row["candidate_or_design_source_ids"] == prior["candidate_or_design_source_ids"]
                )


def test_eight_exact_leads_keep_authored_legal_clauses_open(result):
    previous = json.loads(V7.read_text())
    old = {(row["side"], row["task_id"]): row for row in previous["rows"]}
    for side in "AB":
        rows = [
            row
            for row in result["rows"]
            if row["side"] == side and row["v8_reviewed_source_ids"] == [SOURCE]
        ]
        assert len(rows) == 8
        assert {row["control_id"] for row in rows} == {"SH-LEG-001"}
        assert Counter(row["classification"] for row in rows) == {
            "SOURCE_CANDIDATE_PARTIAL": 3,
            "DESIGN_CONTEXT_ONLY": 3,
            "UNSUPPORTED_EXACT_CLAUSE": 2,
        }
        assert all(row["v8_source_record_refs"][SOURCE] for row in rows)
        for row in rows:
            prior = old[side, row["task_id"]]
            assert SOURCE in row["targeted_integrated_source_ids"]
            if row["authored_test_clause"] is not None:
                assert (
                    row["candidate_or_design_source_ids"] == prior["candidate_or_design_source_ids"]
                )
                assert row["remaining_test_gate"] == prior["remaining_test_gate"]
        status = [
            row
            for row in result["rows"]
            if row["side"] == side and row["task_id"].endswith("ACTION-H-LEGAL-STATUS")
        ]
        assert len(status) == 1
        assert status[0]["v8_reviewed_source_ids"] == []


def test_legal_source_scope_drift_is_rejected():
    previous = json.loads(V7.read_text())
    receipt = json.loads(RECEIPT.read_text())
    changed = copy.deepcopy(receipt)
    changed["real_hipaa_applicability"] = "ESTABLISHED"
    with pytest.raises(V8ReconciliationError, match="boundary"):
        _selected_routes(previous, changed)
    changed = copy.deepcopy(receipt)
    changed["records"]["MESSY"] = changed["records"]["MESSY"][1:]
    with pytest.raises(V8ReconciliationError, match="population"):
        _selected_routes(previous, changed)
