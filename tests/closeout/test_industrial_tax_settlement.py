from copy import deepcopy
from decimal import Decimal as D

import pytest

from enterprise.closeout.industrial_tax_settlement import build


def inputs(monkeypatch):
    anchor, forecast_rows, legal = [], [], []
    for year in range(2026, 2032):
        for scenario in ["base"] if year == 2026 else ["base", "downside", "expansion"]:
            for group in ("ARU_GROUP", "RWH_PS"):
                for month in range(1, 13):
                    native = []
                    direct = year == 2026 and group == "RWH_PS"

                    def pair(
                        identifier,
                        debit,
                        credit,
                        value,
                        native=native,
                        scenario=scenario,
                        group=group,
                        year=year,
                        month=month,
                    ):
                        for account, signed in ((debit, value), (credit, -value)):
                            native.append(
                                dict(
                                    scenario=scenario,
                                    entity=group,
                                    year=year,
                                    month=month,
                                    journal_id=f"{group}-{year}-{month}-{identifier}",
                                    source_id=identifier,
                                    account=account,
                                    signed_usd=str(signed),
                                )
                            )

                    pair(
                        "RW-TAX" if direct else "CURRENT", "5500", "1000" if direct else "2700", 10
                    )
                    pair("DEFERRED", "5501", "2250", 1)
                    if month % 3 == 0 and not direct:
                        pair(
                            "TAX26-PAYMENT" if year == 2026 else f"TAX-CASH-{year}{month:02}",
                            "2700",
                            "1000",
                            30,
                        )
                    (anchor if year == 2026 else forecast_rows).extend(native)
                    for s in ["base", "downside", "expansion"] if year == 2026 else [scenario]:
                        owner, other = ("ARU", "BST") if group == "ARU_GROUP" else ("RWH", "PS")
                        for entity in (owner, other):
                            for index, account in enumerate(("5500", "5501", "2700")):
                                total = (
                                    sum(
                                        D(r["signed_usd"])
                                        for r in native
                                        if r["account"] == account
                                    )
                                    if entity == owner
                                    else D(0)
                                )
                                legal.append(
                                    dict(
                                        scenario=s,
                                        entity=entity,
                                        year=year,
                                        month=month,
                                        source_id=f"LEGAL-{entity}-{year}-{month}",
                                        journal_id=f"J-{entity}-{year}-{month}",
                                        line_no=index,
                                        account=account,
                                        signed_usd=str(total),
                                    )
                                )
    monkeypatch.setattr("industrial.planning.enterprise.load_anchor", lambda: anchor)
    return legal, {"datasets": {"journal": forecast_rows}}, anchor


def test_complete_payment_population_preserves_payer_and_no_new_cash(monkeypatch):
    legal, forecast, _ = inputs(monkeypatch)
    result = build(legal, forecast)
    assert len(result["rows"]) == 432
    assert len(result["payments"]) == 168
    assert all(r["additional_cash_usd"] == "0.0000" for r in result["rows"])
    assert all(
        r["taxpayer"] == "PS" and r["legal_cash_book_owner"] == "RWH"
        for r in result["payments"]
        if r["source_group"] == "RWH_PS"
    )
    assert all(
        "ALLOCATION_PENDING" in r["taxpayer"]
        for r in result["payments"]
        if r["source_group"] == "ARU_GROUP"
    )
    assert all(r["available_at"] >= "2026-09-21T00:00:00Z" for r in result["rows"])
    january = next(
        r for r in result["rows"] if r["source_group"] == "ARU_GROUP" and r["month"] == 1
    )
    assert january["native_closing_tax_payable_usd"] == "10.0000"
    assert january["native_closing_tax_prepayment_usd"] == "0.0000"


@pytest.mark.parametrize(
    "fault",
    ["omit_group", "duplicate_payment", "reverse_payment", "legal_changed", "omit_legal_entity"],
)
def test_source_and_legal_population_errors_fail(monkeypatch, fault):
    legal, forecast, _ = inputs(monkeypatch)
    rows = forecast["datasets"]["journal"]
    if fault == "omit_group":
        forecast["datasets"]["journal"] = [
            r for r in rows if not (r["scenario"] == "downside" and r["year"] == 2029)
        ]
    elif fault == "duplicate_payment":
        rows.append(deepcopy(next(r for r in rows if r["source_id"].startswith("TAX-CASH"))))
    elif fault == "reverse_payment":
        selected = next(r for r in rows if r["source_id"].startswith("TAX-CASH"))
        for r in rows:
            if (r["scenario"], r["entity"], r["journal_id"]) == (
                selected["scenario"],
                selected["entity"],
                selected["journal_id"],
            ):
                r["signed_usd"] = str(-D(r["signed_usd"]))
    elif fault == "legal_changed":
        legal[0]["signed_usd"] = "11"
    else:
        legal = [r for r in legal if r["entity"] != "PS"]
    with pytest.raises(ValueError):
        build(legal, forecast)


def test_native_overpayment_stays_asset_without_refund(monkeypatch):
    legal, forecast, anchor = inputs(monkeypatch)
    for r in anchor:
        if r["entity"] == "ARU_GROUP" and r["month"] == 2 and r["source_id"] == "CURRENT":
            r["signed_usd"] = "-20" if r["account"] == "5500" else "20"
    for r in legal:
        if r["entity"] == "ARU" and r["year"] == 2026 and r["month"] == 2:
            if r["account"] in {"5500", "2700"}:
                r["signed_usd"] = "-20" if r["account"] == "5500" else "20"
    result = build(legal, forecast)
    row = next(
        r
        for r in result["rows"]
        if r["scenario"] == "base"
        and r["source_group"] == "ARU_GROUP"
        and r["year"] == 2026
        and r["month"] == 2
    )
    assert row["native_closing_tax_prepayment_usd"] == "10.0000"
    assert row["native_closing_tax_payable_usd"] == "0.0000"
    assert row["gross_source_tax_cash_paid_usd"] == "0.0000"
