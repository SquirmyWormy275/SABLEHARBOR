from decimal import Decimal as D

import pytest

from enterprise.closeout.sovereignty import attribute, core_purpose, runtime_sustaining_share
from enterprise.runtime import model


def cash(*args):
    return attribute(*(D(x) for x in args))


def test_member_money_is_not_internal_generation():
    available, internal, external, residual = cash(-20, 10, 5, 0, 40, 100, 0)
    assert (available, internal, external, residual) == (-35, 0, 40, 0)


def test_unpaid_bills_cannot_improve_internal_growth_attribution():
    # Cash CFO improved by20 only because due expenses remained unpaid.
    ordinary = cash(30, 10, 5, 0, 40, 20, 0)
    overdue = cash(50, 10, 5, 20, 40, 20, 0)
    assert ordinary == overdue


def test_released_prior_requirement_is_not_current_internal_generation():
    # Prior cash origins may be member financing, borrowing or unpaid-bill timing.
    assert cash(0, 0, 0, -100, 100, 0, 0) == (0, 0, 0, 100)


def test_unavailable_funding_remains_explicit():
    assert cash(-20, 10, 5, 0, 40, 0, 0) == (-35, 0, 0, 40)


def test_tax_and_interest_already_in_operating_cash_not_subtracted_again():
    assert cash(80, 20, 10, 0, 25, 0, 0) == (50, 25, 0, 0)


def test_new_unknown_asset_cannot_silently_inherit_growth_class():
    with pytest.raises(ValueError, match="Unclassified Core"):
        core_purpose("NEW-UNREVIEWED-PROJECT", "base", 2027, model.load())


def test_refresh_preserves_source_cycle_and_splits_new_capacity():
    data = model.load()
    assert (
        runtime_sustaining_share("RT-FORECAST-hardware_cash_request-2027-1", "base", 2027, data)
        == 0
    )
    assert (
        runtime_sustaining_share("RT-FORECAST-hardware_cash_request-2028-1", "base", 2028, data)
        == 0
    )
    assert (
        0
        < runtime_sustaining_share("RT-FORECAST-hardware_cash_request-2031-1", "base", 2031, data)
        <= 1
    )
