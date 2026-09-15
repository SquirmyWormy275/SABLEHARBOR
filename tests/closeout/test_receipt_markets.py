from decimal import Decimal as D

import pytest

from enterprise.closeout.receipt_markets import allocate


def row(account="LEG_4000", amount="-11075500", month="8", **changes):
    return dict(
        scenario="base",
        entity="SHI",
        year="2026",
        month=month,
        journal_id="J1",
        line_no="1",
        account=account,
        account_type="revenue",
        signed_usd=amount,
        source_id="SOURCE1",
        **changes,
    )


def test_august_material_destination_is_inside_aggregate():
    result = allocate([row()])
    assert {(x["market_state"], D(x["receipts_usd"])) for x in result} == {
        ("CA", D("11015500")),
        ("WV", D("60000")),
    }


def test_shared_service_and_annual_close_are_not_external_sales():
    result = allocate([row("SHARED_REV", "-25000"), row(month="0")])
    assert len(result) == 1 and result[0]["population"] == "INTERCOMPANY_ALLOCATION"


@pytest.mark.parametrize("rows", [[row(), row()], [row("NEW_REVENUE")], [row(amount="-11075501")]])
def test_changed_or_duplicate_population_requires_review(rows):
    with pytest.raises(ValueError):
        allocate(rows)


def test_service_credit_keeps_its_market_and_revenue_sign():
    credit = row("BIZ_REVENUE", "1000", month="9", unit="foundry-field")
    credit["year"] = "2027"
    result = allocate([credit])
    assert result[0]["receipts_usd"] == "-1000" and result[0]["market_state"] == "CA"


@pytest.mark.parametrize(
    "year,month,account",
    [
        (2032, 1, "LEG_4000"),
        (2015, 1, "LEG_4000"),
        (2026, 13, "LEG_4000"),
        (2025, 9, "LEG_4050"),
        (2026, 9, "BIZ_REVENUE"),
    ],
)
def test_uncovered_periods_require_new_market_facts(year, month, account):
    record = row(account, month=str(month))
    record["year"] = str(year)
    with pytest.raises(ValueError):
        allocate([record])


def test_balanced_market_reallocation_cannot_change_current_operations():
    import json

    from enterprise.closeout.receipt_markets import SOURCE

    source = json.loads(SOURCE.read_text())
    source["august_2026"]["ca_services_usd"] = "11014500.00"
    source["august_2026"]["wv_cradle_materials_usd"] = "61000.00"
    with pytest.raises(ValueError, match="current operating source"):
        allocate([row()], source)
