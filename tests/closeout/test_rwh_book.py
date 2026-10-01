from decimal import Decimal as D

import pytest

from enterprise.closeout.rwh_book import current_inventory_bridge
from industrial.planning.enterprise import load_anchor


def test_current_inventory_opening_activity_closing_and_scope():
    rows = current_inventory_bridge(load_anchor())
    assert len(rows) == 12
    assert D(rows[7]["corrected_cash_inventory_usd"]) == D("8693912.5497")
    assert D(rows[7]["corrected_dda_inventory_usd"]) == D("867149.3725")
    for previous, current in zip(rows[:-1], rows[1:], strict=True):
        assert previous["corrected_cash_inventory_usd"] == current["opening_cash_inventory_usd"]
        assert previous["corrected_dda_inventory_usd"] == current["opening_dda_inventory_usd"]
    # Omission of a month is a population error, not a zero-cost month.
    with pytest.raises(ValueError, match="Missing current"):
        current_inventory_bridge([r for r in load_anchor() if int(r["month"]) != 8])


def test_duplicate_anchor_is_not_a_second_production_event():
    anchor = load_anchor()
    leg = next(
        r
        for r in anchor
        if r["entity"] == "RWH_PS"
        and int(r["month"]) == 8
        and r["account"] == "1200"
        and D(r["signed_usd"]) > 0
    )
    with pytest.raises(ValueError, match="Duplicate native"):
        current_inventory_bridge(anchor + [leg])
