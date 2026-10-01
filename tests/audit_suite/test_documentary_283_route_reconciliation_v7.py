"""Physical-site leads do not alter authored tasks or the frozen engagement."""

import copy
import json
from collections import Counter
from pathlib import Path

import pytest

from enterprise.audit_suite.documentary_283_route_reconciliation_v7 import (
    IMMUTABLE,
    SOURCE,
    V7ReconciliationError,
    _selected_routes,
    build,
    markdown,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V7_2026-09-30"
V6 = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V6_2026-09-30.json"
RECEIPT = (
    PRIVATE
    / "enterprise/generated/audit-suite/company-physical-site-selected-2026-09-30"
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
    previous = json.loads(V6.read_text())
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
        assert sum(bool(row["targeted_integrated_source_ids"]) for row in rows) == 167
        for row in rows:
            prior = old[side, row["task_id"]]
            assert all(row[key] == prior[key] for key in IMMUTABLE)
            if row["classification"] != prior["classification"]:
                assert row["control_id"] == "SH-SEC-001"
                assert row["authored_test_clause"] is None
                assert prior["classification"] == "DESIGN_CONTEXT_ONLY"
                assert row["classification"] == "SOURCE_CANDIDATE_PARTIAL"


def test_exact_selected_leads_keep_physical_authored_clauses_unsupported(result):
    for side in "AB":
        rows = [
            row
            for row in result["rows"]
            if row["side"] == side and row["v7_reviewed_source_ids"] == [SOURCE]
        ]
        assert len(rows) == 9
        assert Counter(row["control_id"] for row in rows) == {"SH-SEC-001": 5, "SH-BCM-004": 4}
        assert Counter(row["classification"] for row in rows) == {
            "SOURCE_CANDIDATE_PARTIAL": 7,
            "UNSUPPORTED_EXACT_CLAUSE": 2,
        }
        unsupported = [row for row in rows if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"]
        assert {row["task_id"].split(":")[-1] for row in unsupported} == {"CC6.4", "A1.2"}
        assert all(SOURCE not in row["candidate_or_design_source_ids"] for row in unsupported)


def test_physical_route_drift_is_rejected_without_mutating_source():
    prior = json.loads(V6.read_text())
    receipt = json.loads(RECEIPT.read_text())
    changed = copy.deepcopy(receipt)
    changed["selected_routes"]["A"][0]["authored_test_clause"] = "invented satisfaction"
    with pytest.raises(V7ReconciliationError, match="clause or classification"):
        _selected_routes(changed, prior)
    changed = copy.deepcopy(receipt)
    changed["selected_routes"]["B"][0]["task_id"] = "invented task"
    with pytest.raises(V7ReconciliationError, match="route IDs"):
        _selected_routes(changed, prior)
