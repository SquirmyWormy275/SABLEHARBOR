from copy import deepcopy
from decimal import Decimal as D

import pytest

from enterprise.closeout.capital_register import allocate_event, build, build_register


def event():
    return dict(
        event_id="E1",
        source_id="MEMBER-TEST",
        legal_entity="SHI",
        scenario="base",
        year=2027,
        month=1,
        source_amount_usd="1000000.0001",
    )


def test_exact_register_rational_prices_and_unchanged_rights():
    register = build_register()
    assert sum(r["units"] for r in register["holders"]) == 100000000
    assert sum(D(r["participation_share"]) for r in register["holders"]) == 1
    assert register["verified_subscription_receipts_usd"] == "183000000.00"
    result = allocate_event(event())
    assert result["source_to_cash_rounding_usd"] == "-0.0001"
    assert result["cash_facing_requested_usd"] == "1000000.00"
    assert result["received_usd"] == "0.00"
    assert all(
        r["rights_before"] == r["rights_after"] and r["interests_issued"] == "0"
        for r in result["rows"]
    )


def test_nonparticipation_never_reassigns_cash_or_dilutes():
    e = dict(event(), event_state="CONDITIONAL_FORECAST_MODELED_RECEIPT")
    result = allocate_event(e, {"SH-HOLDER-DM": "100.00"})
    assert D(result["received_usd"]) == 100
    assert D(result["shortfall_usd"]) == 999900
    assert (
        next(r for r in result["rows"] if r["holder_id"] == "SH-HOLDER-HV")["received_usd"]
        == "0.00"
    )
    for receipts in ({"OUTSIDER": "1"}, {"SH-HOLDER-DM": "999999"}):
        with pytest.raises(ValueError):
            allocate_event(e, receipts)
    with pytest.raises(ValueError, match="explicit"):
        allocate_event(event(), {"SH-HOLDER-DM": "1"})


def journal():
    common = dict(
        entity="SHI",
        scenario="base",
        year=2027,
        month=1,
        source_id="MEMBER-TEST",
        source_type="MEMBER_EQUITY",
    )
    return [
        dict(common, account="1000", signed_usd="123.4567"),
        dict(common, account="3000", signed_usd="-123.4567"),
    ]


def test_source_cash_allocates_once_without_posting_or_new_units():
    result = build(journal())
    assert len(result["events"]) == 1
    assert len(result["holder_rollforward"]) == 5
    assert sum(D(r["contribution_usd"]) for r in result["holder_rollforward"]) == D("123.46")
    assert result["events"][0]["source_to_cash_rounding_usd"] == "0.0033"
    assert all(r["units_before"] == r["units_after"] for r in result["holder_rollforward"])
    for bad in (
        journal() + journal(),
        [dict(r, signed_usd=str(-D(r["signed_usd"]))) for r in journal()],
    ):
        with pytest.raises(ValueError):
            build(bad)


@pytest.mark.parametrize(
    "field,value",
    [("legal_entity", "PS"), ("scenario", "actual"), ("month", 13), ("source_amount_usd", "NaN")],
)
def test_wrong_scope_and_invalid_amount_rejected(field, value):
    e = deepcopy(event())
    e[field] = value
    with pytest.raises(ValueError):
        allocate_event(e)
