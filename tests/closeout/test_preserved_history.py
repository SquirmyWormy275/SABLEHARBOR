from copy import deepcopy
from decimal import Decimal as D

import pytest

from enterprise.closeout.preserved_history import (
    derived_row,
    verify,
    verify_closes,
    verify_eliminations,
)


def row(entity, year, month, account, kind, amount, source="LEGAL-ARU-2026-01"):
    return derived_row(
        "base", entity, year, month, account, kind, D(amount), source, "NATIVE", "Source entry"
    )


def fixture():
    ppa = row("ARU", 2026, 1, "1600", "asset", "14762500")
    expense = row("ARU", 2026, 7, "5000", "expense", "16065", "REVIEWED-RETENTION")
    closing = [
        derived_row(
            "base",
            "ARU",
            2027,
            0,
            account,
            kind,
            value,
            "CLOSE-2026-CORPORATE",
            "ANNUAL_CLOSE",
            "Close prior-year P&L to retained earnings within its operating segment",
        )
        for account, kind, value in [
            ("5000", "expense", D("-16065")),
            ("3100", "equity", D("16065")),
        ]
    ]
    successor = [ppa, expense] + closing
    settlement = dict(rows=[])
    for scenario in ("base", "downside", "expansion"):
        for month in range(1, 13):
            paid = D(10946 if month <= 3 else 10945)
            settlement["rows"].append(
                dict(
                    scenario=scenario,
                    source_group="RWH_PS",
                    year=2026,
                    month=month,
                    taxpayer="PS",
                    gross_source_tax_cash_paid_usd=str(paid),
                )
            )
            value = paid + (D(78125) if month == 8 else D(0))
            for entity, account, kind, signed in [
                ("RWH", "1150", "asset", value),
                ("PS", "2150", "liability", -value),
            ]:
                item = row(entity, 2026, month, account, kind, signed, "REVIEWED-PAYER")
                item["scenario"] = scenario
                successor.append(item)
                successor.append(
                    derived_row(
                        scenario,
                        "ELIM",
                        2026,
                        month,
                        account,
                        kind,
                        -signed,
                        "1150",
                        "BALANCE_ELIMINATION",
                        "Eliminate reciprocal ownership or intercompany balances",
                    )
                )
    return [deepcopy(ppa)], successor, settlement


def test_native_goodwill_closing_and_source_paid_eliminations():
    result = verify(*fixture())
    assert result["native_2026_preserved_legs"] == 1
    assert result["annual_close_legs"] == 2
    assert result["elimination_legs"] == 72
    assert (
        result["historical_payer_bridge"]["total_incremental_current_account_usd"] == "209468.0000"
    )
    assert result["forecast_native_scope"].startswith("NOT_RUN")


@pytest.mark.parametrize(
    "mutation", ["ppa", "duplicate", "wrong_entity", "wrong_period", "extra_native_leg"]
)
def test_original_native_population_cannot_change(mutation):
    old, new, settlement = fixture()
    if mutation == "ppa":
        new[0]["signed_usd"] = "14762501"
    elif mutation == "duplicate":
        new.append(dict(new[0]))
    elif mutation == "wrong_entity":
        new[0]["entity"] = "BST"
    elif mutation == "wrong_period":
        new[0]["month"] = 2
    else:
        new.append(row("ARU", 2026, 1, "1200", "asset", "1"))
    with pytest.raises(ValueError, match="native/PPA"):
        verify(old, new, settlement)


@pytest.mark.parametrize("mutation", ["balanced_reversal", "duplicate", "new_closing_source"])
def test_no_broad_annual_close_bypass(mutation):
    _, rows, _ = fixture()
    closing = [r for r in rows if r["source_type"] == "ANNUAL_CLOSE"]
    if mutation == "balanced_reversal":
        for r in closing:
            r["signed_usd"] = str(-D(r["signed_usd"]))
    elif mutation == "duplicate":
        rows.extend(deepcopy(closing))
    else:
        closing[0]["source_id"] = "CLOSE-2026-UNREVIEWED"
    with pytest.raises(ValueError, match="annual close"):
        verify_closes(rows)


def test_balanced_reversed_elimination_and_unmatched_payer_rejected():
    _, rows, _ = fixture()
    for r in rows:
        if r["entity"] == "ELIM":
            r["signed_usd"] = str(-D(r["signed_usd"]))
    with pytest.raises(ValueError, match="elimination"):
        verify_eliminations(rows)
    _, rows, _ = fixture()
    next(r for r in rows if r["entity"] == "PS")["signed_usd"] = "-1"
    with pytest.raises(ValueError, match="not reciprocal"):
        verify_eliminations(rows)


def test_wrong_settlement_population_cannot_authorize_balanced_delta():
    old, new, source = fixture()
    source["rows"].append(dict(source["rows"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        verify(old, new, source)
    old, new, source = fixture()
    source["rows"][0]["taxpayer"] = "ARU"
    with pytest.raises(ValueError, match="wrong-taxpayer"):
        verify(old, new, source)


def test_forecast_compares_explicit_revised_source_not_old_tax_cash_plan():
    old, new, source = fixture()
    reviewed = [row("ARU", 2027, 6, "1000", "asset", "123", "LEGAL-ARU-2027-06")]
    new.extend(deepcopy(reviewed))
    assert (
        verify(old, new, source, reviewed_native_rows=reviewed)["forecast_native_preserved_legs"]
        == 1
    )
    new[-1]["signed_usd"] = "124"
    with pytest.raises(ValueError, match="Reviewed native forecast"):
        verify(old, new, source, reviewed_native_rows=reviewed)
