from collections import defaultdict
from decimal import Decimal as D

from enterprise.closeout.historical_tax import build, federal_rate_tax


def test_authored_history_reconciles_cash_without_new_capital_or_asset_plug():
    result = build()
    changes = defaultdict(D)
    for row in result["events"]:
        changes[row["year"]] += D(row["cash_usd"])
    for row in result["annual"]:
        assert D(row["opening_cash_usd"]) + changes[row["year"]] == D(row["closing_cash_usd"])
    assert sum(D(r["contribution_usd"]) for r in result["annual"]) == 183000000
    assert sum(D(r["existing_debt_draw_usd"]) for r in result["annual"]) == 35000000
    assert sum(D(r["equipment_usd"]) for r in result["annual"]) == 9000000
    assert sum(D(r["book_pretax_usd"]) for r in result["annual"]) == -174200000
    assert result["historical_tax_cash"] == D("1037879.0800")
    assert result["federal_nol"] == D("141801600")  # §174 and CA deduction differ from book loss.
    assert result["research_remaining_2026"] == 12000000


def test_historical_rate_boundary_is_period_specific():
    assert federal_rate_tax(D(100000), 2017) == 22250
    assert federal_rate_tax(D(100000), 2018) == 21000
