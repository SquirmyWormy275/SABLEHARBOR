"""Independent accounting, scope, funding and reproducibility tests for enterprise v2."""

from __future__ import annotations

import copy
import csv
import json
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from industrial.planning import enterprise
from industrial.planning.forecast import build as build_forecast
from industrial.planning.legacy_adapter import legacy_snapshot

D = Decimal


def test_growth_cip_cash_and_noncash_commissioning_are_distinct():
    types = {"1000": "asset", "1400": "asset", "1410": "asset", "3000": "equity"}
    opening = {"1000": D(1000), "3000": D(-1000)}
    paid = {"1000": D(900), "1410": D(100), "3000": D(-1000)}
    operating = {"1000": D(900), "1400": D(100), "3000": D(-1000)}
    flows, residual = enterprise.flow_components(opening, paid, types)
    assert flows == {"OPERATING": D(0), "INVESTING": D(-100), "FINANCING": D(0)}
    assert residual == 0
    flows, residual = enterprise.flow_components(paid, operating, types)
    assert not any(flows.values()) and residual == 0


@pytest.mark.parametrize("annual_limit,expected_unpaid", [(30000000, 0), (0, 100)])
def test_new_annual_funding_can_pay_existing_arrears_without_reposting(
    annual_limit, expected_unpaid
):
    source = json.loads(enterprise.SOURCE.read_text())
    source["scenarios"]["base"]["member_equity_annual_limit_usd"] = annual_limit
    books = enterprise.Books("base", source, enterprise.account_contract([], []))
    books.post(
        "SHI",
        2027,
        0,
        [("1000", 2000000), ("CORE_UNPAID", -100), ("3000", -1999900)],
        "OPEN",
        "Known prior unpaid bill",
    )
    rows = []
    enterprise.member_funding(books, 2027, 1, D(0), {"core": D(0), "subsidiary": D(0)}, D(0), rows)
    assert D(rows[0]["required_equity_usd"]) == 100
    assert D(rows[0]["new_payment_deferral_usd"]) == 0
    assert -books.balances["SHI"]["CORE_UNPAID"] == expected_unpaid
    assert books.balances["SHI"]["1000"] == 2000000


@pytest.fixture(scope="module")
def integrated(tmp_path_factory):
    directory = tmp_path_factory.mktemp("enterprise")
    forecast = build_forecast(output=directory / "forecast")
    legacy = legacy_snapshot()
    result = enterprise.build(
        output=directory / "enterprise", forecast_result=forecast, legacy_result=legacy
    )
    return directory, forecast, legacy, result


def grouped_total(rows, fields, value="signed_usd"):
    result = defaultdict(D)
    for row in rows:
        result[tuple(str(row[field]) for field in fields)] += D(str(row[value]))
    return dict(result)


def test_legacy_executes_governed_selection_and_removes_old_industrial(integrated):
    _, _, legacy, result = integrated
    assert legacy["metadata"]["validation_controls"] >= 10
    assert legacy["metadata"]["selected_rows"] == len(legacy["rows"])
    selected = set(legacy["metadata"]["included_run_ids"])
    assert selected and all(row["legacy_run_id"] in selected for row in legacy["rows"])
    bridge = enterprise.read_csv(result["paths"]["legacy_replacement_bridge"])
    assert len(bridge) == len(legacy["rows"])
    kept = [row for row in bridge if row["bridge_action"] == "RETAIN_CORE"]
    removed = [row for row in bridge if row["bridge_action"] != "RETAIN_CORE"]
    assert kept and removed
    assert all(row["entity"] == "SHI" and row["book"] == "PRIMARY_USD" for row in kept)
    assert {row["entity"] for row in removed} >= {"RWH", "ARU", "BST"}
    assert not result["summary"]["raw_legacy_database_included"]


def test_every_journal_and_legal_monthly_trial_balance_balances(integrated):
    result = integrated[3]
    assert not any(grouped_total(result["journal_rows"], ["scenario", "journal_id"]).values())
    assert not any(
        grouped_total(
            result["legal_trial_balance_rows"], ["scenario", "entity", "year", "month"]
        ).values()
    )
    for row in result["journal_rows"]:
        debit, credit, signed = (D(row[key]) for key in ("debit_usd", "credit_usd", "signed_usd"))
        assert debit >= 0 and credit >= 0 and not (debit and credit)
        assert debit - credit == signed
        assert len(row["signed_usd"].split(".")[1]) == 4


def test_ownership_and_reciprocal_balances_eliminate_every_month(integrated):
    result = integrated[3]
    periods = defaultdict(lambda: defaultdict(dict))
    for row in result["legal_trial_balance_rows"]:
        periods[row["scenario"], row["year"], row["month"]][row["entity"]][row["account"]] = D(
            row["signed_usd"]
        )
    owners = json.loads(enterprise.SOURCE.read_text())["owners"]
    for entities in periods.values():
        for child, parent in owners.items():
            assert entities[parent].get("INV_" + child, 0) == -entities[child].get("3000", 0)
            assert sum(book.get("INV_" + child, 0) for book in entities.values()) == 0
        for asset, liability in (("1150", "2150"), ("SHARED_AR", "SHARED_AP")):
            assert sum(
                book.get(asset, 0) for entity, book in entities.items() if entity != "ELIM"
            ) == -sum(
                book.get(liability, 0) for entity, book in entities.items() if entity != "ELIM"
            )
            assert sum(book.get(asset, 0) for book in entities.values()) == 0
            assert sum(book.get(liability, 0) for book in entities.values()) == 0
        assert sum(book.get("1180", 0) for book in entities.values()) == 0
        group_cip = entities["ARU"].get("1410", D(0)) + entities["BST"].get("1410", D(0))
        assert entities["BST"].get("1410", D(0)) == (group_cip * D("0.55")).quantize(
            D(1), rounding=ROUND_HALF_UP
        )


def test_unit_accounts_and_statement_lines_sum_exactly_to_consolidation(integrated):
    result = integrated[3]
    unit = grouped_total(result["unit_rows"], ["scenario", "year", "month", "account"])
    legal = grouped_total(
        result["legal_trial_balance_rows"], ["scenario", "year", "month", "account"]
    )
    assert {key: value for key, value in unit.items() if value} == {
        key: value for key, value in legal.items() if value
    }
    assert not any(
        grouped_total(result["unit_rows"], ["scenario", "unit", "year", "month"]).values()
    )
    consolidated = {
        (str(row["scenario"]), str(row["year"]), str(row["month"])): row
        for row in result["monthly_rows"]
        if row["entity"] == "CONSOLIDATED"
    }
    for field in next(iter(consolidated.values())):
        if not field.endswith("_usd"):
            continue
        totals = grouped_total(result["unit_monthly_rows"], ["scenario", "year", "month"], field)
        assert totals == {key: D(row[field]) for key, row in consolidated.items()}, field


def test_cash_flow_continuity_and_annual_rollup(integrated):
    result = integrated[3]
    sequences = defaultdict(list)
    for row in result["monthly_rows"]:
        assert D(row["assets_usd"]) == D(row["liabilities_usd"]) + D(row["equity_usd"])
        flow = sum(
            D(row[key])
            for key in (
                "operating_cash_flow_usd",
                "investing_cash_flow_usd",
                "financing_cash_flow_usd",
                "opening_or_noncash_cash_bridge_usd",
            )
        )
        assert D(row["opening_cash_usd"]) + flow == D(row["ending_cash_usd"])
        sequences[row["scenario"], row["entity"]].append(row)
    for rows in sequences.values():
        rows.sort(key=lambda row: (row["year"], row["month"]))
        for before, after in zip(rows, rows[1:], strict=False):
            assert before["ending_cash_usd"] == after["opening_cash_usd"]
    monthly_income = grouped_total(
        result["monthly_rows"], ["scenario", "entity", "year"], "net_income_usd"
    )
    assert monthly_income == grouped_total(
        result["annual_rows"], ["scenario", "entity", "year"], "net_income_usd"
    )


def test_industrial_allocated_cash_flows_equal_forecast(integrated):
    _, forecast, _, result = integrated
    expected = defaultdict(D)
    actual = defaultdict(D)
    for row in forecast["journal_rows"]:
        if row["account"] == "1000" and int(row["month"]) > 0:
            expected[
                row["scenario"],
                row["entity"],
                int(row["year"]),
                int(row["month"]),
                row["cash_flow"],
            ] += D(str(row["signed_usd"]))
    for row in result["journal_rows"]:
        if int(row["year"]) <= 2026 or row["account"] != "1000":
            continue
        if row["source_type"] in {"LEGAL_ALLOCATION", "CASH_FLOW_RECLASSIFICATION"}:
            group = "ARU_GROUP" if row["entity"] in {"ARU", "BST"} else "RWH_PS"
        elif row["source_id"] == "PS-RWH-FLOW":
            group = "RWH_PS"
        else:
            continue
        actual[row["scenario"], group, row["year"], row["month"], row["cash_flow"]] += D(
            row["signed_usd"]
        )
    assert {key: value for key, value in actual.items() if value} == {
        key: value for key, value in expected.items() if value
    }


def test_finite_funding_reports_unpaid_liabilities(integrated):
    result = integrated[3]
    parent = [row for row in result["funding_rows"] if row["entity"] == "SHI"]
    assert any(D(row["funding_gap_usd"]) > 0 for row in parent if row["scenario"] == "downside")
    for row in parent:
        assert D(row["member_draws_year_to_date_usd"]) <= D(row["member_annual_limit_usd"])
        assert D(row["funding_gap_usd"]) == D(row["required_equity_usd"]) - D(
            row["available_equity_usd"]
        )
        if D(row["unpaid_operating_obligations_usd"]):
            assert row["feasibility"] == "FUNDING_GAP"
    for row in result["monthly_rows"]:
        if row["entity"] == "SHI":
            assert D(row["ending_cash_usd"]) >= 2000000


def test_external_acquisition_is_not_eliminated_as_internal_funding(integrated):
    result = integrated[3]
    acquisition = [
        row for row in result["journal_rows"] if row["source_type"] == "EXTERNAL_ACQUISITION"
    ]
    assert {row["entity"] for row in acquisition} == {"SHIH"}
    for row in enterprise.read_csv(result["paths"]["acquisition_cashflow_bridge"]):
        assert D(row["stock_consideration_usd"]) == 48000000
        assert D(row["acquisition_investing_cash_usd"]) == -46000000
        assert D(row["net_external_financing_usd"]) == 8700000
        assert D(row["parent_acquisition_capital_usd"]) == 39300000


def test_opening_mismatch_fails_before_projection(integrated):
    _, forecast, legacy, _ = integrated
    modified = copy.deepcopy(forecast)
    modified["opening_rows"][0]["signed_usd"] += 1
    types = enterprise.account_contract(legacy["rows"], forecast["journal_rows"])
    with pytest.raises(ValueError, match="Forecast opening differs"):
        enterprise.snapshot_rows(modified, enterprise.load_anchor(), "base", types)


def test_csv_reload_reproduces_business_outputs(integrated):
    directory, _, legacy, first = integrated
    second = enterprise.build(
        output=directory / "reloaded", forecast_output=directory / "forecast", legacy_result=legacy
    )
    for key in (
        "enterprise_journal",
        "enterprise_monthly_statements",
        "legal_monthly_trial_balances",
        "unit_monthly_statements",
        "enterprise_tax_allocation_bridge",
    ):
        assert Path(first["paths"][key]).read_bytes() == Path(second["paths"][key]).read_bytes(), (
            key
        )
    assert (
        first["summary"]["identity"]["forecast_rows_sha256"]
        == second["summary"]["identity"]["forecast_rows_sha256"]
    )
    with Path(second["paths"]["enterprise_tax_allocation_bridge"]).open(newline="") as stream:
        for row in csv.DictReader(stream):
            assert D(row["preallocation_net_income_usd"]) - D(row["book_only_fee_expense_usd"]) + D(
                row["book_only_fee_revenue_usd"]
            ) == D(row["postallocation_net_income_usd"])
            assert D(row["current_tax_change_from_allocation_usd"]) == 0
