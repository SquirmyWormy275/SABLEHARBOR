from decimal import Decimal as D

from enterprise.closeout.rwh_history import build


def test_historical_cash_units_and_source_purchase_reconcile():
    result = build()
    assert D(result["closing_cash_usd"]) == 2000000
    assert D(result["ending_inventory_lb"]) == 125000
    assert D(result["source_contributed_cash_usd"]) == 44312500
    assert result["adopted_initial_goodwill_usd"] == "0"
    assert D(result["book_dda_usd"]) - D(result["book_inventory_delta_usd"]) == D(
        result["opening_equity_correction_usd"]
    )


def test_bonus_inventory_and_cost_depletion_do_not_double_deduct():
    result = build()
    for row in result["rows"]:
        assert abs(
            D(row["production_depreciation_usd"])
            - D(row["idle_depreciation_current_expense_usd"])
            - D(row["depreciation_in_closing_inventory_usd"])
            - D(row["depreciation_released_to_cogs_usd"])
        ) <= D(".0001")
        assert D(row["percentage_depletion_usd"]) == 0
        assert D(row["cost_depletion_usd"]) == D(row["deduction_depletion_usd"])
        assert abs(
            D(row["cash_cost_income_before_dda_usd"])
            - D(row["depreciation_released_to_cogs_usd"])
            - D(row["idle_depreciation_current_expense_usd"])
            - D(row["deduction_depletion_usd"])
            - D(row["taxable_income_usd"])
        ) <= D(".0001")
        assert row["aro_basis_included_usd"] == "0"
    assert D(result["rows"][0]["idle_depreciation_current_expense_usd"]) > 0


def test_production_indirects_capitalize_and_building_is_not_bonus():
    result = build()
    fed = result["rows"][0]
    assert D(fed["production_indirect_costs_capitalized_usd"]) == D("2345625")
    assert D(fed["production_depreciation_usd"]) < D(fed["initial_plant_basis_usd"])
    assert D(result["book_inventory_delta_usd"]) < D(result["book_dda_usd"])
    assert result["source"]["book_abnormal_period_costs"]["repair_and_shakedown"] == "3000000"
