from decimal import Decimal as D

import pytest

from enterprise.closeout.cost_recovery import quarterly_test, schedule


def test_seven_year_half_year_switch_and_basis_conservation():
    rows = schedule(100000, 2026, 1, 7, last_year=2033)
    assert D(rows[0]["tax_depreciation_usd"]) == D("14285.7143")
    assert D(rows[-1]["closing_tax_basis_usd"]) == 0
    assert abs(sum(D(r["tax_depreciation_usd"]) for r in rows) - 100000) <= D(".0004")
    for row in rows:
        assert abs(
            D(row["opening_tax_basis_usd"])
            - D(row["tax_depreciation_usd"])
            - D(row["closing_tax_basis_usd"])
        ) <= D(".0001")


def test_bonus_basis_not_deducted_again_and_buildings_excluded():
    rows = schedule(100000, 2026, 7, 7, bonus=True)
    assert D(rows[0]["tax_depreciation_usd"]) == 100000
    assert all(D(r["tax_depreciation_usd"]) == 0 for r in rows[1:])
    with pytest.raises(ValueError):
        schedule(100000, 2026, 1, 39, bonus=True, building=True)


def test_midmonth_and_quarter_population_not_arbitrary_election():
    rows = schedule(390000, 2026, 7, 39, building=True)
    assert D(rows[0]["tax_depreciation_usd"]) == D("4583.3333")
    cohorts = [
        dict(cost_usd=60, life_years=7, service_month=1),
        dict(cost_usd=40, life_years=7, service_month=10),
        dict(cost_usd=900, life_years=39, service_month=1, building=True),
    ]
    assert not quarterly_test(cohorts)
    cohorts[1]["cost_usd"] = 41
    assert quarterly_test(cohorts)
