"""Custody chronology, ownership, population and source-cost regression guards."""

import copy

import pytest

from enterprise.operations.completed_period import read
from enterprise.operations.september_custody import (
    SEPTEMBER_SOURCE,
    as_of,
    build,
    verify_source_expense,
)


@pytest.fixture(scope="module")
def result():
    return build()


def test_original_hold_then_separate_known_on_receipt(result):
    assert (
        as_of(result, effective_at="2026-08-31T23:59:59-06:00", known_on="2026-09-15T00:00:00Z")
        is None
    )
    assert (
        as_of(result, effective_at="2026-09-14T23:59:59-06:00", known_on="2026-09-14T23:59:59Z")
        is None
    )
    received = as_of(
        result, effective_at="2026-09-14T23:59:59-06:00", known_on="2026-09-15T00:00:00Z"
    )
    assert received["event"] == "CONVERTER_CUSTODIAL_RECEIPT"
    roll = result["lot_rollforward"]
    assert roll["closing_converter_custody_lb_u3o8"] == "200.00"
    assert roll["rejected_mine_quarantine_lb_u3o8"] == "200.00"
    assert roll["title_owner"] == "RWH"
    assert roll["new_revenue_usd"] == "0.00"


@pytest.mark.parametrize(
    "field,value",
    [
        ("released_at", "2026-09-06T08:00:00-06:00"),
        ("received_at", "2026-09-12T08:00:00-06:00"),
        ("carrier_id", "BST"),
        ("legal_owner", "PS"),
        ("quantity_lb_u3o8", "201"),
        ("freight_amount_usd", "50001"),
    ],
)
def test_source_mutations_fail(result, field, value):
    source = read(SEPTEMBER_SOURCE)
    source[field] = value
    with pytest.raises(ValueError):
        build(source=source)


@pytest.mark.parametrize("field,value", [("outcome", "FAIL"), ("evidence_id", "")])
def test_failed_or_missing_qualification_blocks_shipment(result, field, value):
    q = copy.deepcopy(result["qualification"])
    q["checks"][0][field] = value
    with pytest.raises(ValueError, match="[Qq]ualification"):
        build(qualification=q)


def test_independent_retained_cost_not_second_expense(result):
    from industrial.planning.enterprise import load_anchor

    rows = load_anchor()
    receipt = verify_source_expense(result, rows)
    assert receipt["reconciled_parent_usd"] == "50000.00"
    assert receipt["additional_journal_usd"] == "0.00"
    broken = copy.deepcopy(result)
    broken["expense_bridge"]["parent"]["amount_usd"] = "50001.00"
    with pytest.raises(ValueError, match="independent journal"):
        verify_source_expense(broken, rows)
