from decimal import Decimal as D

import pytest

from enterprise.closeout.rot_penalties import TYPES, RotPenalties
from industrial.planning.enterprise import Books


def test_current_cutoff_and_opening_roll_forward_without_cash():
    p = RotPenalties()
    b = Books(
        "base",
        {"segment_mapping": {}, "created_on": "2026-09-22", "knowledge_cutoff": "2026-09-22"},
        TYPES | {"3100": "equity"},
    )
    p.post_opening(b)
    for m in range(1, 9):
        p.post_month(b, 2026, m)
    assert -b.balances["RWH"]["CO_ROT_PENALTY_PAY"] - b.balances["RWH"]["CO_ROT_INTEREST_PAY"] == D(
        "69137.56"
    )
    assert sum(p.amounts(p.cutoff)) == D("70322.54")
    assert not any(r["account"] == "1000" for r in b.rows)
    with pytest.raises(ValueError, match="Duplicate"):
        p.post_month(b, 2026, 8)


def test_unpaid_future_interest_is_visible_conditional_cost():
    p = RotPenalties()
    future = [r for r in p.rows if r["year"] == 2031]
    assert all(r["interest_rate_state"] == "HELD_7_PERCENT_PLANNING_ASSUMPTION" for r in future)
    assert sum(D(r["interest_activity_usd"]) for r in future) > 30000
    assert all(r["cash_paid_usd"] == "0" for r in future)
