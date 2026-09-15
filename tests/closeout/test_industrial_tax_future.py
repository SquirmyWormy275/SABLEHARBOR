from copy import deepcopy
from decimal import Decimal as D

import pytest

from enterprise.closeout.industrial_tax_future import FutureIndustrialTax


def inputs():
    return {"journal_rows": [dict(entity="RWH", account="4000", scenario=s, year=y, month=m,
                                 journal_id=f"{y}-{m}", source_id="MINE_SALES", signed_usd="-3647500.01")
                            for s in ["base", "downside", "expansion"] for y in range(2027, 2032) for m in range(1, 13)]}


def posted(provider):
    return [dict(scenario=r["scenario"], source_id=r["source_id"], entity="RWH", year=r["year"], month=r["month"],
                 account=a, signed_usd=str(D(r["tax_expense_usd"]) * sign))
            for r in provider.rows for a, sign in [("CO_RWH_ROT_EXP", 1), ("CO_RWH_ROT_PAY", -1)]]


def test_complete_allocations_and_tax():
    p = FutureIndustrialTax(inputs())
    assert len(p.rows) == 540 and len(p.allocation_rows) == 720
    first = p.allocation_rows[:4]
    assert sum(D(r["principal_usd"]) for r in first) == D("3647500.01")
    assert sum(D(r["tax_expense_usd"]) for r in p.rows[:3]) == D("217137.50")
    assert all(r["tax_cash_paid_usd"] == "0" for r in p.rows)
    assert p.verify(posted(p))["invoice_accruals"] == 540


@pytest.mark.parametrize("mutation", ["duplicate", "omitted", "entity", "period", "scenario"])
def test_native_reject(mutation):
    source = inputs()
    if mutation == "duplicate":
        source["journal_rows"].append(deepcopy(source["journal_rows"][0]))
    elif mutation == "omitted":
        source["journal_rows"].pop()
    else:
        source["journal_rows"][0][{"entity": "entity", "period": "year", "scenario": "scenario"}[mutation]] = {
            "entity": "PS", "period": 2032, "scenario": "stress"}[mutation]
    with pytest.raises(ValueError):
        FutureIndustrialTax(source)


@pytest.mark.parametrize("mutation", ["duplicate", "reverse", "entity", "period", "scenario"])
def test_balanced_overlay_reject(mutation):
    p = FutureIndustrialTax(inputs())
    rows = posted(p)
    if mutation == "duplicate":
        rows.extend(deepcopy(rows[:2]))
    elif mutation == "reverse":
        for row in rows[:2]:
            row["signed_usd"] = str(-D(row["signed_usd"]))
    else:
        for row in rows[:2]:
            row[{"entity": "entity", "period": "year", "scenario": "scenario"}[mutation]] = {
                "entity": "PS", "period": 2026, "scenario": "stress"}[mutation]
    with pytest.raises(ValueError):
        p.verify(rows)


def test_opening_carryforward_is_not_new_sale():
    source = inputs()
    opening = deepcopy(source["journal_rows"][0])
    opening.update(month=0, journal_id="OPENING", signed_usd="-99999999")
    source["journal_rows"].append(opening)
    assert FutureIndustrialTax(source).rows == FutureIndustrialTax(inputs()).rows
