from copy import deepcopy
from decimal import Decimal

import pytest

from enterprise.closeout.capital_export import opening_bridge
from enterprise.closeout.capital_register import build_register


def opening():
    rows = []
    for scenario in ("base", "downside", "expansion"):
        for index, (source, account, amount) in enumerate(
            [
                ("LEGACY-OPEN-2026", "LEG_3000", "-38800000"),
                ("SH-VOICE-GW-01", "LEG_3000", "30000000"),
                ("LEGACY-OPEN-2026", "3100", "27200000"),
                ("OPEN-MEMBER-BASIS", "3000", "-44312500"),
                ("CO-TAX-HISTORICAL-PAYMENTS", "3100", "1037879.08"),
            ]
        ):
            rows.append(
                dict(
                    scenario=scenario,
                    entity="SHI",
                    year=2026,
                    month=0,
                    journal_id=source,
                    line_no=index,
                    source_id=source,
                    account=account,
                    account_type="equity",
                    signed_usd=amount,
                )
            )
        rows.append(
            dict(
                scenario=scenario,
                entity="PS",
                year=2026,
                month=0,
                journal_id="LEGAL-PS-2026-00",
                line_no=1,
                source_id="LEGAL-PS-2026-00",
                account="3000",
                account_type="equity",
                signed_usd="-44312500",
            )
        )
    return rows


def test_round_cash_is_distinct_from_initialization_and_industrial_reconstruction():
    journal = opening()
    preserved = deepcopy(journal)
    summary, details = opening_bridge(journal, build_register())
    assert journal == preserved
    assert len(summary) == 3 and len(details) == 15
    for row in summary:
        assert Decimal(row["historical_subscription_paid_in_usd"]) == 183000000
        assert Decimal(row["historical_industrial_contribution_paid_in_usd"]) == 44312500
        assert Decimal(row["total_historical_paid_in_usd"]) == 227312500
        assert Decimal(row["historical_2016_2022_pretax_result_usd"]) == -174200000
        assert Decimal(row["corrected_core_initialization_equity_usd"]) == 8800000
        assert Decimal(row["industrial_noncash_reconstruction_usd"]) == 44312500
        assert Decimal(row["total_parent_opening_equity_usd"]) == Decimal("24874620.92")
        assert row["additional_ledger_cash_or_equity_posted_usd"] == "0"


def test_duplicate_omitted_and_changed_opening_rejected():
    rows = opening()
    with pytest.raises(ValueError, match="Duplicate"):
        opening_bridge(rows + [rows[0]], build_register())
    with pytest.raises(ValueError, match="Incomplete"):
        opening_bridge([r for r in rows if r["scenario"] != "base"], build_register())
    rows[0]["signed_usd"] = "-40000000"
    with pytest.raises(ValueError, match="do not explain"):
        opening_bridge(rows, build_register())


def test_missing_noncash_capital_cannot_be_hidden_in_a_new_round():
    rows = [r for r in opening() if r["source_id"] != "OPEN-MEMBER-BASIS"]
    with pytest.raises(ValueError, match="noncash reconstruction"):
        opening_bridge(rows, build_register())


def test_historical_receipt_must_match_existing_reconstruction():
    register = build_register()
    register["historical_contribution_receipts_usd"] = "44312501"
    with pytest.raises(ValueError, match="historical contribution"):
        opening_bridge(opening(), register)
