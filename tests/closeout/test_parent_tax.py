from decimal import Decimal as D

import pytest

from enterprise.closeout.finance import CloseoutAdjustment
from enterprise.closeout.parent_tax import ParentTax
from industrial.planning.enterprise import Books


def tax():
    result = {"monthly_rows": [], "journal_rows": [], "legal_trial_balance_rows": []}
    for case in ["base", "downside", "expansion"]:
        for year in range(2026, 2032):
            for month in range(1, 13):
                result["monthly_rows"].append(
                    dict(entity="SHI", scenario=case, year=year, month=month, net_income_usd="-100")
                )
    legacy = {
        "rows": [
            dict(
                entity="SHI",
                book="PRIMARY_USD",
                entry_date=f"{year}-12-31",
                account_type="expense",
                signed_usd="100",
            )
            for year in [2023, 2024, 2025]
        ]
    }
    return ParentTax(
        result,
        legacy,
        history=dict(
            federal_nol=D(0),
            california_nol=D(0),
            research_2022=D(0),
            research_remaining_2026=D(0),
            historical_tax_cash=D(7200),
        ),
    )


def test_adopted_history_and_full_allowance_no_goodwill_tax():
    t = tax()
    assert t.source["corporate_effective_date"] == t.source["formation_date"] == "2016-04-12"
    assert t.opening_nol == 300
    for row in t.rows:
        assert D(row["federal_current_usd"]) == 0 and D(row["california_current_usd"]) == 800
        assert row["gross_dta_usd"] == row["valuation_allowance_usd"]
        assert D(row["net_deferred_expense_usd"]) == 0
        assert D(row["book_depreciation_usd"]) == 0


def test_provision_payment_and_deferred_legs_balance():
    t = tax()
    b = Books(
        "base",
        {"segment_mapping": {}, "knowledge_cutoff": "2026-09-15", "created_on": "2026-09-15"},
        CloseoutAdjustment.account_types | {"1000": "asset", "3100": "equity"},
    )
    t.post_opening(b)
    for month in range(1, 13):
        t.post_month(b, 2026, month)
    assert sum(D(r["signed_usd"]) for r in b.rows) == 0
    assert b.balances["SHI"]["CO_TAX_PAY_CA"] == 0
    assert b.balances["SHI"]["CO_TAX_PAY_FED"] == 0
    assert b.balances["SHI"]["CO_TAX_DTA"] + b.balances["SHI"]["CO_TAX_VA"] == 0
    assert b.balances["SHI"]["1000"] == -8000


def test_duplicate_provision_rejected():
    t = tax()
    b = Books(
        "base",
        {"segment_mapping": {}, "knowledge_cutoff": "2026-09-15", "created_on": "2026-09-15"},
        CloseoutAdjustment.account_types | {"1000": "asset", "3100": "equity"},
    )
    t.post_month(b, 2026, 1)
    with pytest.raises(ValueError):
        t.post_month(b, 2026, 1)


def test_unpaid_transaction_tax_deduction_waits_for_payment():
    result = {"monthly_rows": [], "journal_rows": [], "legal_trial_balance_rows": []}
    for case in ["base", "downside", "expansion"]:
        for year in range(2026, 2032):
            for month in range(1, 13):
                result["monthly_rows"].append(
                    dict(entity="SHI", scenario=case, year=year, month=month, net_income_usd="-100")
                )
        result["journal_rows"] += [
            dict(
                entity="SHI",
                scenario=case,
                year=y,
                month=1,
                account="CO_SOFTWARE_TAX_PAY",
                signed_usd=v,
                source_id=f"fixture-{y}",
                journal_id=f"fixture-{y}",
            )
            for y, v in [(2027, "-90"), (2028, "90")]
        ]
    legacy = {
        "rows": [
            dict(
                entity="SHI",
                book="PRIMARY_USD",
                entry_date=f"{y}-12-31",
                account_type="expense",
                signed_usd="100",
            )
            for y in [2023, 2024, 2025]
        ]
    }
    t = ParentTax(
        result,
        legacy,
        history=dict(
            federal_nol=D(0),
            california_nol=D(0),
            research_2022=D(0),
            research_remaining_2026=D(0),
            historical_tax_cash=D(7200),
        ),
    )
    rows = {r["year"]: r for r in t.rows if r["scenario"] == "base"}
    assert D(rows[2027]["unpaid_transaction_tax_addback_usd"]) == 90
    assert D(rows[2028]["unpaid_transaction_tax_addback_usd"]) == -90
    assert rows[2027]["gross_dta_usd"] == rows[2027]["valuation_allowance_usd"]
