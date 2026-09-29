import copy
from decimal import Decimal as D

import pytest

from enterprise.closeout.retention_tax import PAYABLE, RetentionTax, source_bonus_rows
from industrial.planning.enterprise import Books


def books():
    return Books(
        "base",
        {"segment_mapping": {}, "knowledge_cutoff": "2026-09-15", "created_on": "2026-09-15"},
        RetentionTax.account_types,
    )


def test_additional_employer_levy_balances_without_new_cash_or_double_burden():
    provider = RetentionTax()
    ledger = books()
    ledger.balances["ARU"]["5000"] = D("1000000")
    for month in range(1, 13):
        provider.post_month(ledger, 2026, month)
    provider.post_month(ledger, 2027, 1)
    assert len(ledger.rows) == 4
    assert ledger.balances["ARU"]["5000"] == D("1016065")
    assert ledger.balances["ARU"][PAYABLE] == D("-16065")
    assert ledger.balances["BST"][PAYABLE] == D("-8201.75")
    assert sum(D(r["signed_usd"]) for r in ledger.rows) == 0
    assert all(
        r["account"] != "1000" and r["cash_flow"] == "NONCASH_OR_OPENING" for r in ledger.rows
    )
    assert provider.receipt()["total_usd"] == "24266.75"
    with pytest.raises(ValueError, match="Duplicate"):
        provider.post_month(ledger, 2026, 7)


@pytest.mark.parametrize(
    "mutation", ["omit", "duplicate", "entity", "period", "amount", "ytd", "employee_net"]
)
def test_balanced_but_wrong_retention_source_rejected(mutation):
    rows = copy.deepcopy(source_bonus_rows())
    if mutation == "omit":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif mutation == "entity":
        rows[0]["legal_entity"] = "SHI"
    elif mutation == "period":
        rows[0]["event_period"] = "2027-01"
    elif mutation == "amount":
        rows[0]["employer_known_taxes_usd"] = "0"
    elif mutation == "ytd":
        rows[0]["opening_ytd_usd"] = "0"
    else:
        rows[0]["employee_net_usd"] = rows[0]["gross_usd"]
    with pytest.raises(ValueError):
        RetentionTax(rows)


def test_payable_cannot_be_misclassified_as_asset():
    provider = RetentionTax()
    ledger = books()
    ledger.types[PAYABLE] = "asset"
    with pytest.raises(ValueError, match="classification"):
        provider.post_month(ledger, 2026, 7)
    assert not ledger.rows
