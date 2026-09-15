from decimal import Decimal as D

import pytest

from enterprise.closeout.historical_rot import HistoricalRot
from industrial.planning.enterprise import Books


def test_historical_utility_tax_is_unpaid_equity_correction_not_acquisition_basis():
    provider = HistoricalRot()
    books = Books(
        "base",
        {"segment_mapping": {}, "knowledge_cutoff": "2026-09-15", "created_on": "2026-09-15"},
        {"3100": "equity", "CO_RWH_ROT_PAY": "liability"},
    )
    provider.post_opening(books)
    assert len(books.rows) == 36
    assert books.balances["RWH"]["3100"] == D("646624.38")
    assert books.balances["RWH"]["CO_RWH_ROT_PAY"] == -D("646624.38")
    assert {r["account"] for r in books.rows} == {"3100", "CO_RWH_ROT_PAY"}
    assert all(int(r["year"]) == 2026 and int(r["month"]) == 0 for r in books.rows)
    assert len([r for r in provider.rows if not r["utility_own_use"]]) == 6
    with pytest.raises(ValueError, match="Duplicate"):
        provider.post_opening(books)
