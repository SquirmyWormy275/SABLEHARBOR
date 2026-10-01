"""ETH001 route preparation stays closed until V11 main-local acceptance."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import documentary_283_route_reconciliation_v10 as route
from enterprise.audit_suite.documentary_283_route_reconciliation_v10 import V10ReconciliationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


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


def test_no_integrated_delta_without_main_local_v11_acceptance(previous, receipt):
    assert route.V11_ACCEPTED is None
    assert route.PROSPECTIVE_V11["isolated_commit"] == ("d41d73470d2ae9610b67dcf3abac244710295971")
    with pytest.raises(
        V10ReconciliationError, match="main-local review and output pins are pending"
    ):
        route.build(REPOSITORY, PRIVATE)
    with pytest.raises(V10ReconciliationError, match="accepted candidate verification required"):
        route._extend(previous, receipt, route.P1_FREEZE, qualification=None)
    assert not (
        REPOSITORY
        / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V10_2026-09-30.json"
    ).exists()
