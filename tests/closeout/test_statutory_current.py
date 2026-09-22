from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from enterprise.closeout.statutory_current import MEMBERS, build


def source():
    parent = []
    aru = []
    mine = []
    factors = []
    for s in ("base", "downside", "expansion"):
        for y in range(2026, 2032):
            p = dict(scenario=s, year=y)
            for field in (
                "book_pretax_usd",
                "book_depreciation_usd",
                "allowance_addback_usd",
                "inventory_addback_usd",
                "unpaid_transaction_tax_addback_usd",
                "book_only_service_fee_reversal_usd",
                "california_depreciation_usd",
                "federal_depreciation_usd",
                "historical_research_amortization_usd",
                "interest_usd",
                "interest_deducted_usd",
            ):
                p[field] = "0"
            parent.append(p)
            for j in ("US", "CA", "IL", "WV"):
                mine.append(
                    dict(
                        scenario=s,
                        jurisdiction=j,
                        year=y,
                        income_before_nol_usd="-1000000",
                        opening_2026_loss_before_state_apportionment_usd="2000000",
                    )
                )
                for e in ("ARU", "BST"):
                    aru.append(
                        dict(
                            scenario=s,
                            taxpayer=e,
                            jurisdiction=j,
                            year=y,
                            income_before_interest_limit_usd="100000000" if e == "ARU" else "0",
                            eligible_interest_expense_usd="50000000" if e == "ARU" else "0",
                            tax_depreciation_allowance_usd="0",
                            tax_goodwill_amortization_usd="0",
                        )
                    )
            for j in ("CA", "IL", "WV"):
                for e in MEMBERS:
                    factors.append(
                        dict(
                            scenario=s,
                            jurisdiction=j,
                            member=e,
                            year=y,
                            member_factor=".5"
                            if (j, e) == ("CA", "SHI")
                            else ".2"
                            if (j, e) == ("IL", "PS")
                            else "0",
                        )
                    )
            factors.append(
                dict(scenario=s, jurisdiction="PA", member="SHI", year=y, member_factor="0")
            )
    return (
        SimpleNamespace(
            rows=parent,
            asset_rows=[],
            historical_income={"2025": "-9100000"},
            opening_state_nol=D(100000000),
        ),
        {"rows": aru},
        mine,
        factors,
        [
            dict(
                scenario=s,
                entity="SHIH",
                year=2026,
                month=1,
                account="5800",
                account_type="expense",
                signed_usd="900000",
            )
            for s in ("base", "downside", "expansion")
        ],
    )


def test_separate_federal_taxpayers_do_not_pool_mine_losses():
    r = build(*source())
    a = next(
        x
        for x in r["federal"]
        if x["scenario"] == "base" and x["taxpayer"] == "ARU" and x["year"] == 2026
    )
    assert D(a["interest_deducted_usd"]) == D(30000000)
    assert D(a["interest_carryforward_usd"]) == D(20000000)
    assert D(a["current_tax_usd"]) == D(14687400)
    m = next(
        x
        for x in r["federal"]
        if x["scenario"] == "base" and x["taxpayer"] == "PS" and x["year"] == 2026
    )
    assert D(m["closing_nol_usd"]) == D(3000000)
    assert D(m["current_tax_usd"]) == 0


def test_combined_state_group_keeps_member_losses_and_suspension():
    r = build(*source())
    ca = next(
        x
        for x in r["states"]
        if x["scenario"] == "base"
        and x["taxpayer"] == "SHI"
        and x["jurisdiction"] == "CA"
        and x["year"] == 2026
    )
    assert D(ca["opening_member_nol_usd"]) > 0
    assert D(ca["member_nol_used_usd"]) == 0
    il = next(
        x
        for x in r["states"]
        if x["scenario"] == "base"
        and x["taxpayer"] == "PS"
        and x["jurisdiction"] == "IL"
        and x["year"] == 2026
    )
    assert D(il["member_nol_used_usd"]) <= 500000


def test_missing_or_duplicate_source_workpaper_rejected():
    p, a, m, f, j = source()
    a["rows"].pop()
    with pytest.raises(ValueError, match="Incomplete"):
        build(p, a, m, f, j)
    p, a, m, f, j = source()
    a["rows"].append(a["rows"][0].copy())
    with pytest.raises(ValueError, match="Duplicate"):
        build(p, a, m, f, j)
