from copy import deepcopy
from decimal import Decimal as D

import pytest

from enterprise.closeout.finance import CloseoutAdjustment
from enterprise.closeout.industrial_tax import IndustrialTax
from industrial.planning.enterprise import Books


def provider():
    return IndustrialTax(
        {
            "journal_rows": [
                dict(
                    entity="RWH",
                    year=2026,
                    month=m,
                    account="4000",
                    signed_usd="-3039583",
                    scenario=s,
                    source_id=f"RWH-{m}",
                )
                for s in ["base", "downside", "expansion"]
                for m in range(1, 13)
            ]
        }
    )


def test_august_independent_population_and_non_cash_carryforward():
    t = provider()
    b = Books(
        "base",
        {"segment_mapping": {}, "knowledge_cutoff": "2026-09-15", "created_on": "2026-09-15"},
        CloseoutAdjustment.account_types,
    )
    for m in range(1, 13):
        t.post_month(b, 2026, m)
    assert sum(
        D(r["tax_expense_usd"]) for r in t.rows if r["scenario"] == "base" and r["month"] == 8
    ) == D("180947.89")
    assert sum(D(r["signed_usd"]) for r in b.rows) == 0
    assert not any(r["account"] == "1000" for r in b.rows)
    assert b.balances["RWH"]["CO_RWH_ROT_PAY"] < -D("180947.89")
    with pytest.raises(ValueError):
        t.post_month(b, 2026, 8)


def test_reversed_or_wrong_period_balanced_overlay_rejected():
    t = provider()
    rows = []
    for s in ["base", "downside", "expansion"]:
        b = Books(
            s,
            {"segment_mapping": {}, "knowledge_cutoff": "2026-09-15", "created_on": "2026-09-15"},
            CloseoutAdjustment.account_types,
        )
        for m in range(1, 13):
            t.post_month(b, 2026, m)
        rows.extend(b.rows)
    assert t.verify(rows)["invoice_accruals"] == 108
    for mutation in ["reverse", "period", "duplicate", "omit"]:
        changed = deepcopy(rows)
        if mutation == "reverse":
            for r in changed[:2]:
                r["signed_usd"] = str(-D(r["signed_usd"]))
        elif mutation == "period":
            for r in changed[:2]:
                r["month"] = 2
        elif mutation == "duplicate":
            changed += deepcopy(changed[:2])
        else:
            changed = changed[2:]
        with pytest.raises(ValueError):
            t.verify(changed)


def test_receipt_tax_uses_sale_period_not_august_invoice_accrual():
    from enterprise.closeout.industrial_tax import august_receipt_workpaper
    from enterprise.operations.completed_period import build

    edition = build()
    rows, bridge = august_receipt_workpaper(edition)
    assert D(bridge[0]["collected_tax_cents_usd"]) == D("167698.94")
    assert all(D(r["collected_tax_usd"]) == 0 for r in rows if r["sale_period"] == "2026-08")
    assert all(r["additional_book_expense_usd"] == "0" for r in rows)
    assert bridge[0]["ordinary_return_due"] == "2026-09-21"
    changed = deepcopy(edition)
    invoice = next(
        r
        for r in changed["tables"]["current_customer_invoice_ledger"]
        if r.get("source_contract_id") == "UCA-2019-04"
    )
    invoice["sale_period"] = "2025-12"
    with pytest.raises(ValueError):
        august_receipt_workpaper(changed)
