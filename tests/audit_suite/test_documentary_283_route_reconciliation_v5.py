"""V5 joins exact reviewed native sources without changing frozen audit tasks."""

import copy
import json
from collections import Counter
from pathlib import Path

import pytest

from enterprise.audit_suite import documentary_283_route_reconciliation_v3 as prior
from enterprise.audit_suite.documentary_283_route_reconciliation_v5 import (
    V5ReconciliationError,
    _source_routes,
    build,
    markdown,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V5_2026-09-30"


def test_exact_successor_and_frozen_active_pair():
    result = build(REPOSITORY, PRIVATE)
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert markdown(result) == STEM.with_suffix(".md").read_text()
    assert result["reviewed_source_roster"] == {
        "cohorts": 26,
        "native_versions": 475,
        "source_complete": False,
    }
    assert result["active_p1_tasks"] == {
        side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"} for side in "AB"
    }
    assert len(result["rows"]) == 566
    assert result["audit_task_credit"] is False
    assert result["active_pair_mutated"] is False
    old = prior.build(REPOSITORY, PRIVATE, PRIVATE)
    old_rows = {(row["side"], row["task_id"]): row for row in old["rows"]}
    immutable = (
        "family",
        "control_id",
        "procedure_type",
        "authored_test_clause",
        "test_gate_basis",
        "requirement_ids",
        "screen_row_sha256",
        "remaining_test_gate",
        "current_status",
        "current_conclusion",
        "actual_operation_eligibility_as_of_packet",
        "audit_task_credit",
    )
    for side in "AB":
        rows = [row for row in result["rows"] if row["side"] == side]
        assert len(rows) == len({row["task_id"] for row in rows}) == 283
        assert len({row["control_id"] for row in rows}) == 43
        assert Counter(row["classification"] for row in rows) == {
            "SOURCE_CANDIDATE_PARTIAL": 126,
            "DESIGN_CONTEXT_ONLY": 36,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        assert sum(bool(row["targeted_integrated_source_ids"]) for row in rows) == 157
        for row in rows:
            prior_row = old_rows[side, row["task_id"]]
            assert all(row[key] == prior_row[key] for key in immutable)
            if row["classification"] != prior_row["classification"]:
                assert prior_row["classification"] == "DESIGN_CONTEXT_ONLY"
                assert row["classification"] == "SOURCE_CANDIDATE_PARTIAL"
                assert row["authored_test_clause"] is None


def test_sec005_overlap_and_rec003_existing_source_are_not_double_counted():
    rows = [row for row in build(REPOSITORY, PRIVATE)["rows"] if row["side"] == "A"]
    newly_selected = [
        row
        for row in rows
        if row["control_id"]
        in {"SH-SEC-005", "SH-ASS-001", "SH-ASS-002", "SH-GOV-003", "SH-POL-002", "SH-ERM-002"}
        and row["authored_test_clause"] is not None
    ]
    assert len(newly_selected) == 13
    assert all(row["classification"] == "UNSUPPORTED_EXACT_CLAUSE" for row in newly_selected)
    sec = [row for row in rows if row["control_id"] == "SH-SEC-005"]
    assert len(sec) == 5
    assert all(
        row["v5_reviewed_source_ids"]
        == ["SEC005_SYMBOLIC_LOCAL_V1", "SEC005_SELECTED_OPERATIONS_V2"]
        for row in sec
    )
    assert [row["classification"] for row in sec].count("UNSUPPORTED_EXACT_CLAUSE") == 2
    assert [row["classification"] for row in sec].count("SOURCE_CANDIDATE_PARTIAL") == 3
    rec = [row for row in rows if row["control_id"] == "SH-REC-003"]
    assert len(rec) == 4
    assert all(row["v5_reviewed_source_ids"] == ["REC003_EXISTING_SNAPSHOT_V1"] for row in rec)
    assert [row["classification"] for row in rec].count("DESIGN_CONTEXT_ONLY") == 1
    assert [row["classification"] for row in rec].count("SOURCE_CANDIDATE_PARTIAL") == 3


def test_selected_route_drift_is_rejected():
    old = prior.build(REPOSITORY, PRIVATE, PRIVATE)
    path = (
        PRIVATE
        / "enterprise/generated/audit-suite/company-gov-appetite-2026-09-30"
        / "main-run-v1/RECEIPT.json"
    )
    receipt = json.loads(path.read_text())
    changed = copy.deepcopy(receipt)
    changed["selected_routes"]["A"][0]["authored_test_clause"] = "invented credit"
    with pytest.raises(V5ReconciliationError, match="Exact selected clause/gate"):
        _source_routes("gov_appetite", changed, old)
    changed = copy.deepcopy(receipt)
    changed["selected_routes"]["B"].append(changed["selected_routes"]["B"][0])
    with pytest.raises(V5ReconciliationError, match="Duplicate selected route"):
        _source_routes("gov_appetite", changed, old)
