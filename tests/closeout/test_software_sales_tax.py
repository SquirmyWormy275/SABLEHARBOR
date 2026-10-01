import copy
import json
from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from enterprise.closeout.finance import CloseoutAdjustment
from enterprise.closeout.software_sales_tax import SOURCE, SoftwareTax
from industrial.planning.enterprise import Books


def population():
    source = json.loads(SOURCE.read_text())
    source["contracts"] = [
        r for r in source["contracts"] if r["contract_id"] in {"FF-001", "FF-003"}
    ]
    invoices = [
        dict(
            invoice_id="INV-base-FF-003-TERM-0",
            source_id="FF-003-TERM-0",
            customer_id="SYN-CUSTOMER-003",
            scenario="base",
            unit="foundry-field",
            issue_month=1,
            amount_usd="1740000",
        ),
        dict(
            invoice_id="INV-base-FF-001-TERM-0",
            source_id="FF-001-TERM-0",
            customer_id="SYN-CUSTOMER-001",
            scenario="base",
            unit="foundry-field",
            issue_month=1,
            amount_usd="1200",
        ),
    ]
    return SimpleNamespace(
        inputs={"contracts": source["contracts"]}, tables={"invoices": invoices}
    ), source


def test_ff003_protected_while_new_tax_posts_once_and_settles_separately():
    op, source = population()
    tax = SoftwareTax(op, source)
    b = Books(
        "base",
        {
            "segment_mapping": {"FOUNDRY_FIELD": "foundry-field"},
            "knowledge_cutoff": "2026-09-15",
            "created_on": "2026-09-15",
        },
        CloseoutAdjustment.account_types | {"1000": "asset"},
    )
    tax.post_month(b, 2027, 1)
    assert b.balances["SHI"]["CO_SOFTWARE_TAX_PAY"] == -105
    assert all(r["unit"] == "foundry-field" for r in b.rows)
    assert all(r["source_id"] != "FF-003-TAX" for r in b.rows)
    with pytest.raises(ValueError, match="Duplicate"):
        tax.post_month(b, 2027, 1)
    tax.post_month(b, 2027, 2)
    with pytest.raises(ValueError, match="Duplicate"):
        tax.post_month(b, 2027, 2)
    tax.verify(b.rows)
    reversed_rows = copy.deepcopy(b.rows)
    for row in reversed_rows:
        row["signed_usd"] = str(-D(row["signed_usd"]))
    with pytest.raises(ValueError, match="population"):
        tax.verify(reversed_rows)
    assert b.balances["SHI"]["1000"] == -105 and b.balances["SHI"]["CO_SOFTWARE_TAX_PAY"] == 0
    assert sum(D(r["signed_usd"]) for r in b.rows) == 0
    assert next(r for r in tax.rows if r["source_id"] == "FF-003-TAX")["planned_cash_date"] == ""


@pytest.mark.parametrize("mutation", ["customer", "duplicate", "threshold", "omitted"])
def test_tax_population_guards(mutation):
    op, source = population()
    if mutation == "customer":
        op.tables["invoices"][1]["customer_id"] = "WRONG"
    if mutation == "duplicate":
        op.tables["invoices"].append(copy.deepcopy(op.tables["invoices"][1]))
    if mutation == "threshold":
        op.tables["invoices"][1]["amount_usd"] = "5000001"
    if mutation == "omitted":
        op.inputs = {"contracts": op.inputs["contracts"][:1]}
    with pytest.raises(ValueError):
        SoftwareTax(op, source)


def test_payment_plan_precedes_bank_holidays():
    from datetime import date

    from enterprise.closeout.software_sales_tax import planning_payment_date

    assert planning_payment_date(2027, 5) == date(2027, 5, 28)
    assert planning_payment_date(2027, 12) == date(2027, 12, 30)
