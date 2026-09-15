from collections import defaultdict
from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from enterprise.closeout.rwh_tax_workpapers import build


def inputs():
    rows, monthly = [], []
    totals = defaultdict(lambda: {"tax_depreciation_usd": D(0)})
    for scenario in ("base", "downside", "expansion"):
        for year in range(2026, 2032):
            rows.append(
                dict(
                    scenario=scenario,
                    year=year,
                    month=1,
                    entity="RWH",
                    account="4000",
                    account_type="revenue",
                    signed_usd="-1000000",
                    source_id="SALE",
                    journal_id=f"SALE-{year}",
                )
            )
            for month in range(1, 13):
                monthly.append(
                    dict(
                        scenario=scenario,
                        year=year,
                        month=month,
                        production_lb="100",
                        sales_lb="100",
                        production_cash_cost_usd="1000",
                        production_mineral_tax_usd="100",
                        group_support_production_cost_usd="100",
                        corrected_cash_inventory_usd="100000",
                        consolidated_service_cost_inventory_usd="0",
                    )
                )
    return (
        {"journal_rows": rows},
        SimpleNamespace(rows=monthly),
        {"totals": totals},
        {"journal_rows": []},
    )


def test_annual_pool_conservation_and_realization_boundary():
    rows = build(*inputs())
    assert len(rows) == 72
    for row in rows:
        assert abs(
            D(row["opening_tax_cash_inventory_usd"])
            + D(row["tax_cash_cost_incurred_usd"])
            - D(row["tax_cash_cost_cogs_usd"])
            - D(row["tax_cash_inventory_usd"])
        ) <= D(".0001")
        assert D(row["idle_depreciation_deduction_usd"]) == 0
        assert D(row["depletion_deduction_usd"]) >= D(row["cost_depletion_usd"])


def test_duplicate_sale_is_not_more_taxable_income():
    result, book, assets, forecast = inputs()
    result["journal_rows"].append(result["journal_rows"][0].copy())
    with pytest.raises(ValueError, match="Duplicate mine"):
        build(result, book, assets, forecast)


def test_missing_scenario_or_month_fails_before_tax_calculation():
    result, book, assets, forecast = inputs()
    book.rows.pop()
    with pytest.raises(ValueError, match="period population"):
        build(result, book, assets, forecast)
    result, book, assets, forecast = inputs()
    result["journal_rows"] = [r for r in result["journal_rows"] if r["scenario"] != "downside"]
    with pytest.raises(ValueError, match="income population"):
        build(result, book, assets, forecast)
