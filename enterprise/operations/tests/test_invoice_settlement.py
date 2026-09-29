import copy
from collections import defaultdict
from decimal import Decimal as D

import pytest

from enterprise.operations.completed_period import build
from enterprise.operations.invoice_settlement import validate


@pytest.fixture(scope="module")
def tables():
    return build()["tables"]


def test_dated_ledger_aging_and_source_collection_totals(tables):
    ledger = tables["current_customer_invoice_ledger"]
    assert len(ledger) == 117
    assert len(tables["current_customer_cash_allocations"]) == 33
    assert sum(D(r["closing_allowance_usd"]) for r in ledger) == 80000
    totals = defaultdict(D)
    for r in tables["current_customer_cash_allocations"]:
        totals[r["financial_group"]] += D(r["amount_usd"])
    assert dict(totals) == {"ARU_GROUP": D("3829683"), "RWH_PS": D("2993750")}
    assert all(r["paid_on"] == "2026-08-28" for r in tables["current_customer_cash_allocations"])
    current = {r["invoice_id"]: r for r in tables["current_invoices"]}
    for r in ledger:
        if D(r["august_billed_usd"]):
            assert D(r["august_billed_usd"]) == D(current[r["invoice_id"]]["principal_usd"])
            assert r["legal_issuer"] == current[r["invoice_id"]]["legal_entity"]


@pytest.mark.parametrize(
    "table,field,value",
    [
        ("current_customer_cash_allocations", "paid_on", "2026-06-01"),
        ("current_customer_cash_allocations", "customer_id", "MISSING"),
        ("current_customer_cash_allocations", "amount_usd", "1"),
        ("current_customer_invoice_ledger", "due_on", "2026-01-01"),
        ("current_customer_invoice_aging", "bucket", "OVER_90"),
        ("current_customer_invoice_aging", "days_past_due", 999),
    ],
)
def test_invoice_receipt_and_aging_mutations_fail(tables, table, field, value):
    broken = copy.deepcopy(tables)
    broken[table][0][field] = value
    with pytest.raises(ValueError):
        validate(broken)


@pytest.mark.parametrize(
    "table",
    [
        "current_customer_invoice_ledger",
        "current_customer_cash_allocations",
        "current_customer_invoice_aging",
    ],
)
def test_duplicate_or_omitted_evidence_fails(tables, table):
    for duplicate in (False, True):
        broken = copy.deepcopy(tables)
        if duplicate:
            broken[table].append(broken[table][0])
        else:
            broken[table].pop()
        with pytest.raises(ValueError):
            validate(broken)


def test_rwh_opening_sales_split_cannot_exceed_native_monthly_revenue(tables):
    rows = [
        r for r in tables["current_customer_invoice_ledger"] if r["financial_group"] == "RWH_PS"
    ]
    assert len(rows) == 12
    cash = defaultdict(D)
    for row in rows:
        cash[row["sale_period"]] += D(row["paid_august_usd"])
        assert D(row["opening_outstanding_usd"]) <= D(row["invoice_face_usd"])
    assert dict(cash) == {"2026-06": D("1281252"), "2026-07": D("1712498"), "2026-08": D("0")}
    for field, value in [
        ("sale_period", "2026-07"),
        ("invoice_face_usd", "99999999"),
        ("collected_before_august_usd", "0"),
    ]:
        broken = copy.deepcopy(tables)
        next(
            r
            for r in broken["current_customer_invoice_ledger"]
            if r.get("sale_period") == "2026-06"
        )[field] = value
        with pytest.raises(ValueError):
            validate(broken)
