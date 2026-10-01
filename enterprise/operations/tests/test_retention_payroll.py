import copy
from decimal import Decimal as D

import pytest

from enterprise.operations.completed_period import build
from enterprise.operations.retention_payroll import validate


@pytest.fixture(scope="module")
def tables():
    return build()["tables"]


def test_retention_cash_and_current_wage_caps(tables):
    result = validate(tables)
    assert result["retention_recipients"] == 8
    assert result["ytd_payment_events"] == 136
    assert result["gross_bonus_usd"] == "250000.00"
    assert result["employee_bonus_net_usd"] == "173951.75"
    assert result["employee_bonus_withholding_usd"] == "76048.25"
    assert result["employer_bonus_levy_usd"] == "24266.75"
    assert D(result["employee_bonus_net_usd"]) + D(result["employee_bonus_withholding_usd"]) == D(
        result["gross_bonus_usd"]
    )
    nora = [
        r
        for r in tables["retention_payroll_ytd"]
        if r["employee_name"] == "Nora Ashcombe" and r["event_period"] == "2026-08"
    ]
    assert all(D(r["tax_components"]["social_or_tier1"]) == 0 for r in nora)
    seth = [
        r
        for r in tables["retention_payroll_ytd"]
        if r["employee_name"] == "Seth Kettering" and r["event_period"] == "2026-08"
    ]
    assert all(D(r["tax_components"]["tier2"]) == 0 for r in seth)


@pytest.mark.parametrize(
    "mutation", ["omit", "duplicate", "bonus_amount", "old_ytd", "wrong_entity", "future_period"]
)
def test_omitted_bonus_and_changed_tax_history_fail(tables, mutation):
    broken = copy.deepcopy(tables)
    rows = broken["retention_payroll_ytd"]
    if mutation == "omit":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif mutation == "bonus_amount":
        next(r for r in rows if r["payment_kind"] == "RETENTION")["gross_usd"] = "0"
    elif mutation == "old_ytd":
        next(
            r
            for r in broken["payroll"]
            if r["person_id"] == "P029" and r["pay_date"] == "2026-08-14"
        )["opening_ytd_wages_usd"] = "144200.00"
    elif mutation == "wrong_entity":
        rows[0]["legal_entity"] = "SHI"
    else:
        rows[0]["effective_period"] = "2027-01"
    with pytest.raises(ValueError):
        validate(broken)
