"""V6 exact-route successor keeps authored duties and active tasks frozen."""

import copy
import json
from collections import Counter
from pathlib import Path

import pytest

from enterprise.audit_suite.documentary_283_route_reconciliation_v6 import (
    IAM_SOURCE,
    SEC_SOURCE,
    V6ReconciliationError,
    _selected_sec_routes,
    build,
    markdown,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V6_2026-09-30"
V5 = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V5_2026-09-30.json"
SEC_RECEIPT = (
    PRIVATE
    / "enterprise/generated/audit-suite/company-sec003-selected-vulnerability-2026-09-30"
    / "main-run-v1/RECEIPT.json"
)


@pytest.fixture(scope="module")
def result():
    return build(REPOSITORY, PRIVATE)


def test_exact_successor_and_frozen_task_pair(result):
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert markdown(result) == STEM.with_suffix(".md").read_text()
    assert result["reviewed_source_roster"] == {
        "cohorts": 28,
        "native_versions": 529,
        "source_complete": False,
        "registry": "REVIEWED_MAIN_V7_PARTIAL_PORTFOLIO_AND_CANDIDATE",
    }
    assert result["active_p1_tasks"] == {
        side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"} for side in "AB"
    }
    assert result["p1_freeze"]["file_count"] == 538
    assert result["audit_task_credit"] is False
    assert result["active_pair_mutated"] is False
    old = json.loads(V5.read_text())
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
            "SOURCE_CANDIDATE_PARTIAL": 129,
            "DESIGN_CONTEXT_ONLY": 33,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        for row in rows:
            previous = old_rows[side, row["task_id"]]
            assert all(row[key] == previous[key] for key in immutable)
            if row["classification"] != previous["classification"]:
                assert row["control_id"] == "SH-SEC-003"
                assert row["authored_test_clause"] is None
                assert previous["classification"] == "DESIGN_CONTEXT_ONLY"
                assert row["classification"] == "SOURCE_CANDIDATE_PARTIAL"


def test_selected_source_routes_and_authored_clauses(result):
    for side in "AB":
        rows = [row for row in result["rows"] if row["side"] == side]
        iam = [row for row in rows if row["v6_reviewed_source_ids"] == [IAM_SOURCE]]
        sec = [row for row in rows if row["v6_reviewed_source_ids"] == [SEC_SOURCE]]
        assert len(iam) == len(sec) == 5
        assert {row["control_id"] for row in iam} == {"SH-IAM-005"}
        assert Counter(row["classification"] for row in iam) == {
            "SOURCE_CANDIDATE_PARTIAL": 3,
            "UNSUPPORTED_EXACT_CLAUSE": 2,
        }
        assert Counter(row["classification"] for row in sec) == {
            "SOURCE_CANDIDATE_PARTIAL": 3,
            "UNSUPPORTED_EXACT_CLAUSE": 2,
        }
        authored = [row for row in sec if row["authored_test_clause"]]
        assert {row["task_id"].split(":")[-1] for row in authored} == {"CC7.1", "CC5.2"}
        assert all(row["classification"] == "UNSUPPORTED_EXACT_CLAUSE" for row in authored)


def test_sec003_route_clause_or_id_drift_is_rejected():
    old = json.loads(V5.read_text())
    receipt = json.loads(SEC_RECEIPT.read_text())
    changed = copy.deepcopy(receipt)
    changed["selected_routes"]["A"][0]["authored_test_clause"] = "invented credit"
    with pytest.raises(V6ReconciliationError, match="clause/gate"):
        _selected_sec_routes(changed, old)
    changed = copy.deepcopy(receipt)
    changed["selected_routes"]["B"][0]["task_id"] = "other task"
    with pytest.raises(V6ReconciliationError, match="route IDs"):
        _selected_sec_routes(changed, old)
