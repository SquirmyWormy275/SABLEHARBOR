from decimal import Decimal as D

import pytest

from enterprise.closeout.tax_limits import illinois_nol_used


@pytest.mark.parametrize(
    "year,expected",
    [
        (2026, "500000"),
        (2027, "1500000"),
        (2028, "3000000"),
        (2029, "5000000"),
        (2030, "6500000"),
        (2031, "8000000"),
    ],
)
def test_enacted_illinois_year_limits(year, expected):
    assert illinois_nol_used(year, "10000000", "20000000") == D(expected)


def test_floor_never_creates_loss_or_exceeds_available_carryover():
    assert illinois_nol_used(2027, "200000", "1000000") == D(200000)
    assert illinois_nol_used(2027, "10000000", "100") == D(100)
    assert illinois_nol_used(2027, "-100", "1000000") == 0


@pytest.mark.parametrize(
    "year,income,loss", [(2032, "1", "1"), (True, "1", "1"), (2026, "NaN", "1"), (2026, "1", "-1")]
)
def test_reject_unscoped_or_invalid_populations(year, income, loss):
    with pytest.raises(ValueError):
        illinois_nol_used(year, income, loss)
