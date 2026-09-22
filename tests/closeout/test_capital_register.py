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


def test_founder_opening_zero_requires_complete_formation_facts():
    from enterprise.closeout.capital_register import validate_formation

    register = build_register()
    assert register["founder_monetary_basis_complete"]
    founders = [
        r
        for r in register["unit_history"]
        if r["holder_id"] in {"SH-HOLDER-DM", "SH-HOLDER-PR", "SH-HOLDER-JB"}
    ]
    assert len(founders) == 3
    assert all(
        r["effective_date"] == "2016-04-12" and r["recorded_subscription_cash_usd"] == "0.00"
        for r in founders
    )
    for field, value in (
        ("company_owned_preexisting_ip", True),
        ("binding_customer_commitments", True),
        ("cash_contributed_usd", "1"),
        ("unvested_units", 1),
        ("effective_date", "2016-01-01"),
    ):
        source = deepcopy(register["source"])
        source["founder_formation"][field] = value
        with pytest.raises(ValueError):
            validate_formation(source)
    source = deepcopy(register["source"])
    source["founder_formation"]["valuation"]["aggregate_fair_value_usd"] = "1000"
    with pytest.raises(ValueError, match="fair value"):
        validate_formation(source)
    result = build(journal())
    assert (
        sum(D(r["historical_monetary_opening_usd"]) for r in result["holder_rollforward"])
        == 227312500
    )
    assert sum(D(r["closing_paid_in_capital_usd"]) for r in result["holder_rollforward"]) == D(
        "227312623.46"
    )


def test_industrial_history_five_holder_cash_and_no_duplicate_units():
    register = build_register()
    history = register["historical_industrial_contribution"]
    assert register["verified_subscription_receipts_usd"] == "183000000.00"
    assert register["total_historical_paid_in_usd"] == "227312500.00"
    assert sum(D(r["received_usd"]) for r in history["holder_rows"]) == 44312500
    assert all(r["units_before"] == r["units_after"] for r in history["holder_rows"])
    assert all(r["rights_before"] == r["rights_after"] for r in history["holder_rows"])
    assert history["available_at"] >= history["repository_source_available_at"]
    assert history["authored_day"] == "2026-09-22"
    assert history["additional_2026_postings_usd"] == "0.00"


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_cash",
        "duplicate_holder",
        "new_units",
        "compulsory",
        "before_acceptance",
        "before_control",
        "duplicate_receipt",
        "wrong_split",
    ],
)
def test_industrial_history_adverse_states_rejected(mutation):
    from enterprise.closeout.capital_register import historical_industrial_contribution

    register = build_register()
    source = deepcopy(register["source"])
    event = source["historical_industrial_contribution"]
    if mutation == "extra_cash":
        event["amount_usd"] = "44312501"
    elif mutation == "duplicate_holder":
        event["holders"].append(dict(event["holders"][0]))
    elif mutation == "new_units":
        event["holders"][0]["new_units"] = 1
    elif mutation == "compulsory":
        event["compulsory_call"] = True
    elif mutation == "before_acceptance":
        event["receipt_date"] = "2025-07-08"
    elif mutation == "before_control":
        event["downstream"][-1]["effective_date"] = "2025-07-17"
    elif mutation == "duplicate_receipt":
        event["holders"][1]["receipt_id"] = event["holders"][0]["receipt_id"]
    else:
        event["downstream"][-1]["amount_usd"] = "16312501"
    with pytest.raises(ValueError):
        historical_industrial_contribution(source, register["holders"])
