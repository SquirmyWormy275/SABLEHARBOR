from decimal import Decimal as D

import pytest

from enterprise.closeout.treasury import build, spread
from industrial.planning.enterprise import read_csv, write_csv


def fixture(tmp_path):
    root = tmp_path / "enterprise"
    root.mkdir()
    rows = []
    statements = []
    for entity in ["SHI", "CONSOLIDATED"]:
        for month in [8, 9, 10, 11]:
            statements.append(
                dict(
                    scenario="base",
                    entity=entity,
                    year=2026,
                    month=month,
                    ending_cash_usd=str(10 + 300 * (month - 8)),
                )
            )
    for month in [9, 10, 11]:
        rows.append(
            dict(
                scenario="base",
                entity="SHI",
                year=2026,
                month=month,
                account="1000",
                journal_id=f"J{month}",
                line_no=month,
                source_id=f"M{month}",
                source_type="MEMBER_EQUITY",
                cash_flow="FINANCING",
                signed_usd="300",
                available_at="2026-09-15",
                fact_state="CONDITIONAL_FORECAST",
            )
        )
    write_csv(root / "enterprise_journal.csv", rows)
    write_csv(root / "enterprise_monthly_statements.csv", statements)
    return rows


def test_rounding_is_conservative_and_exact():
    for value in ["100.0001", "-100.0001", "0.0001"]:
        values = spread(value, 31)
        assert len(values) == 31 and sum(values) == D(value)
        assert all(v == v.quantize(D(".0001")) for v in values)


def test_thirteen_weeks_bridge_and_no_available_funding(tmp_path):
    fixture(tmp_path)
    result = build(tmp_path)
    assert result["weeks"] == 13 and result["rows"] == 52 and result["monthly_checks"] == 12
    rows = read_csv(tmp_path / "treasury_13week.csv")
    assert all(D(r["arithmetic_difference_usd"]) == 0 for r in rows)
    missing = [r for r in rows if r["timing_case"] == "MEMBER_CASH_UNAVAILABLE"]
    assert all(D(r["closing_cash_usd"]) == 10 for r in missing)
    assert sum(D(r["unavailable_member_cash_usd"]) for r in missing if r["entity"] == "SHI") == 900
    assert max(r["week_end"] for r in rows) == "2026-11-30"


@pytest.mark.parametrize("corruption", ["duplicate", "omit"])
def test_cash_population_errors_rejected(tmp_path, corruption):
    rows = fixture(tmp_path)
    if corruption == "duplicate":
        rows.append(rows[0])
    else:
        rows.pop()
    write_csv(tmp_path / "enterprise/enterprise_journal.csv", rows)
    with pytest.raises(ValueError):
        build(tmp_path)
