from decimal import Decimal as D

import pytest

from enterprise.closeout.finance import CloseoutAdjustment
from enterprise.closeout.state_minimum import StateMinimum
from industrial.planning.enterprise import Books


def test_entity_minimum_first_year_and_unpaid_history():
    tax = StateMinimum()
    assert not any(r["entity"] == "PS" and r["year"] == 2025 for r in tax.rows)
    assert len([r for r in tax.rows if r["entity"] == "SHIH" and r["year"] == 2025]) == 1
    books = Books(
        "base",
        {"segment_mapping": {}, "knowledge_cutoff": "2026-09-15", "created_on": "2026-09-15"},
        CloseoutAdjustment.account_types | {"3100": "equity"},
    )
    tax.post_opening(books)
    for month in range(1, 9):
        tax.post_month(books, 2026, month)
    assert books.balances["SHIH"]["CO_STATE_MIN_PAY"] == -1600
    assert books.balances["PS"]["CO_STATE_MIN_PAY"] == -800
    assert sum(D(r["signed_usd"]) for r in books.rows) == 0
    assert not any(r["account"] == "1000" for r in books.rows)
    with pytest.raises(ValueError):
        tax.post_month(books, 2026, 1)
