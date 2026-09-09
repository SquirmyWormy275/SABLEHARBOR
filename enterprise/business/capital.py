"""Standalone mine-upgrade and closure support sensitivities, separate from logistics."""

from decimal import Decimal as D

from .model import money


def calculate(source):
    mine = source["mine_upgrade"]
    rows = []
    for scenario, case in mine["cases"].items():
        capital = D(mine["capital_usd"]) * D(case["capital_factor"])
        volume = D(mine["annual_incremental_payable_lb"]) * D(case["volume_factor"])
        price = D(mine["price_usd_per_lb"]) * D(case["price_factor"])
        margin = volume * (price - D(mine["incremental_cash_cost_usd_per_lb"]))
        depreciation = capital / mine["operating_years"]
        tax = max(margin - depreciation, D(0)) * D(mine["tax_rate"])
        cash = (
            margin - D(mine["annual_sustaining_usd"]) - D(mine["annual_closure_funding_usd"]) - tax
        )
        npv = -capital
        for year in range(1, mine["operating_years"] + 1):
            npv += cash / (1 + D(mine["discount_rate"])) ** year
        rows.append(
            {
                "scenario": scenario,
                "initial_capital_usd": money(capital),
                "incremental_payable_lb": money(volume),
                "annual_sales_usd": money(volume * price),
                "annual_cash_margin_usd": money(margin),
                "annual_cash_tax_usd": money(tax),
                "annual_free_cash_usd": money(cash),
                "npv_usd": money(npv),
                "discount_rate": mine["discount_rate"],
                "fact_state": "CONDITIONAL_INVESTMENT_CASE",
                "scope": "STANDALONE_MINE_UPGRADE; common capital excluded from prior differential logistics comparison",
                "decision_state": "NO_ENGINEERING_APPROVAL_OR_COMMITTED_FUNDING",
            }
        )
    closure = source["closure_sensitivity"]
    stress = []
    for factor in closure["cost_factors"]:
        obligation = D(closure["base_cash_obligation_usd"]) * D(factor)
        funded = D(closure["funded_cash_usd"])
        stress.append(
            {
                "cost_factor": factor,
                "cash_obligation_usd": money(obligation),
                "funded_support_assumption_usd": money(funded),
                "unfunded_nominal_usd": money(max(obligation - funded, 0)),
                "present_value_usd": money(
                    obligation / (1 + D(closure["discount_rate"])) ** closure["years_to_settlement"]
                ),
                "fact_state": "CONDITIONAL_SUPPORT_SENSITIVITY",
                "boundary": closure["boundary"],
            }
        )
    return rows, stress
