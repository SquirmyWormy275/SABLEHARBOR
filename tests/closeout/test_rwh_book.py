from decimal import Decimal as D

import pytest

from enterprise.closeout.rwh_book import current_inventory_bridge
from industrial.planning.enterprise import load_anchor


def test_current_inventory_opening_activity_closing_and_scope():
    rows = current_inventory_bridge(load_anchor())
    assert len(rows) == 12
    assert D(rows[7]["corrected_cash_inventory_usd"]) == D("8385238.1530")
    assert D(rows[7]["corrected_dda_inventory_usd"]) == D("867149.3725")
    for previous, current in zip(rows, rows[1:]):
        assert previous["corrected_cash_inventory_usd"] == current["opening_cash_inventory_usd"]
        assert previous["corrected_dda_inventory_usd"] == current["opening_dda_inventory_usd"]
    # Omission of a month is a population error, not a zero-cost month.
    with pytest.raises(ValueError, match="Missing current"):
        current_inventory_bridge([r for r in load_anchor() if int(r["month"]) != 8])
