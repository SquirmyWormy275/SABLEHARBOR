from copy import deepcopy
from decimal import Decimal as D

import pytest

from enterprise.closeout.aru_tax_workpapers import build as release_build
from enterprise.closeout.aru_tax_workpapers import financing_components


def build(rows, forecast):
    return release_build(
        rows, forecast, expected_groups={("base", e, 2026) for e in ("ARU", "BST")}
    )


def fixture():
    forecast = {"datasets": {"assets": [], "debt": []}}
    debt = financing_components(forecast)
    rows = []
    for month in range(1, 13):
        for entity, share in (("ARU", D(".92")), ("BST", D(".08"))):
            accounts = [
                ("4000", "revenue", -D(1000)),
                ("5100", "expense", D(100)),
                ("5300", "expense", D(30)),
                ("5500", "expense", D(10)),
                ("5900", "expense", D(5)),
                ("5400", "expense", sum(debt["base", 2026, month].values()) * share),
            ]
            for index, (account, kind, value) in enumerate(accounts):
                rows.append(
                    dict(
                        scenario="base",
                        entity=entity,
                        year=2026,
                        month=month,
                        account=account,
                        account_type=kind,
                        signed_usd=str(value),
                        source_id="TEST_SOURCE",
                        journal_id=f"J-{entity}-{month}",
                        line_no=index,
                    )
                )
    return rows, forecast


def test_new_target_operating_day_and_noninterest_fee_are_separate():
    rows, forecast = fixture()
    result = build(rows, forecast)
    assert len(result["rows"]) == 8
    for row in result["rows"]:
        assert D(row["excluded_old_target_operating_profit_usd"]) == 36
        assert D(row["book_dda_addback_usd"]) == 360
        assert D(row["native_planning_tax_addback_usd"]) == 120
        assert D(row["book_only_shared_allocation_addback_usd"]) == 60
        assert D(row["unused_commitment_fee_deduction_usd"]) > 0
        assert D(row["tax_goodwill_amortization_usd"]) == (
            D("866666.6667") if row["taxpayer"] == "ARU" else 0
        )
    january = [r for r in result["financing_components"] if r["month"] == 1]
    assert all(r["old_target_day_excluded"] for r in january)


@pytest.mark.parametrize(
    "fault", ["duplicate", "omitted_month", "financing_change", "recursive_tax"]
)
def test_independent_source_population_changes_fail(fault):
    rows, forecast = fixture()
    if fault == "duplicate":
        rows.append(rows[0])
    elif fault == "omitted_month":
        rows = [r for r in rows if not (r["entity"] == "ARU" and r["month"] == 12)]
    elif fault == "financing_change":
        row = next(r for r in rows if r["account"] == "5400")
        row["signed_usd"] = "1"
    else:
        rows[1]["account"] = "CO_TAX_CURRENT"
    with pytest.raises(ValueError):
        build(rows, forecast)


def test_unpaid_employer_levy_not_deducted_and_no_automatic_goodwill_tax_for_bst():
    rows, forecast = fixture()
    base = build(rows, forecast)
    levy = deepcopy(rows[0])
    levy.update(
        month=7,
        account="5000",
        account_type="expense",
        signed_usd="16065",
        journal_id="LEVY",
        source_id="CO-RETENTION-EMP-TAX-ARU-202607",
    )
    changed = build(rows + [levy], forecast)
    for a, b in zip(base["rows"], changed["rows"], strict=True):
        assert a["income_before_interest_limit_usd"] == b["income_before_interest_limit_usd"]


def test_employee_retention_timing_reverses_unfixed_accrual():
    rows, forecast = fixture()
    result = build(rows, forecast)
    selected = [r for r in result["rows"] if r["jurisdiction"] == "US"]
    assert sum(D(r["retention_book_accrual_usd"]) for r in selected) == 491781
    assert sum(D(r["retention_fixed_paid_deduction_usd"]) for r in selected) == 250000
    old = sum(D(r["retention_old_target_accrual_usd"]) for r in selected)
    assert old > 0
    assert (
        sum(D(r["retention_employee_timing_adjustment_usd"]) for r in selected)
        == 491781 - old - 250000
    )


def test_native_forecast_retention_schema_without_line_number():
    from enterprise.closeout.aru_tax_workpapers import retention_components

    row = dict(
        scenario="base",
        entity="ARU_GROUP",
        year=2027,
        month=1,
        journal_id="RETENTION-CASH",
        account="1000",
        signed_usd="-250000",
        source_id="FINAL-RETENTION-PAYMENT",
    )
    forecast = {"datasets": {"debt": [], "journal": [row]}}
    assert retention_components(forecast)["base", 2027]["paid"] == 250000
    forecast["datasets"]["journal"].append(row)
    with pytest.raises(ValueError, match="Duplicate forecast"):
        retention_components(forecast)


def test_default_release_scope_rejects_entire_missing_scenarios_and_years():
    rows, forecast = fixture()
    # This formerly succeeded because groups were inferred only from supplied rows.
    with pytest.raises(ValueError, match="source-scope groups"):
        release_build(rows, forecast)
    partial = build(rows, forecast)
    assert partial["source_scope"] == "EXPLICIT_PARTIAL_WORKPAPER"
    only_aru = [r for r in rows if r["entity"] == "ARU"]
    with pytest.raises(ValueError, match="source-scope groups"):
        build(only_aru, forecast)


@pytest.mark.parametrize(
    "account", ["CO_SUB_TAX_CURRENT", "CO_SUB_TAX_DEFERRED", "CO_SUB_TAX_VA_EXP"]
)
def test_final_subsidiary_income_tax_accounts_rejected(account):
    rows, forecast = fixture()
    rows[1]["account"] = account
    with pytest.raises(ValueError, match="before income-tax"):
        build(rows, forecast)


def test_current_debt_schedule_has_no_generated_tree_dependency(tmp_path, monkeypatch):
    from enterprise.closeout import aru_tax_workpapers as workpapers

    # ROOT points at an empty tree: the helper must invoke the source-owned
    # native builder into its own temporary output, never read ROOT/generated.
    monkeypatch.setattr(workpapers, "ROOT", tmp_path)
    rows = workpapers.current_debt_schedule()
    assert len(rows) == 12
    assert {int(r["month"]) for r in rows} == set(range(1, 13))
    january = next(r for r in rows if int(r["month"]) == 1)
    assert D(january["term_interest_usd"]) == 104024
    assert not (tmp_path / "industrial/generated").exists()
