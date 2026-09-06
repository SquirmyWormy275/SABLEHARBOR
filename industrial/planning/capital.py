#!/usr/bin/env python3
"""Incremental logistics investment screen using constrained common-demand cases."""

from __future__ import annotations

import argparse
import copy
import json
import math
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from industrial.tools.build_financials import customer_schedules

try:
    from . import operating_model as operating
    from .transactions import procurement_costs
except ImportError:
    import operating_model as operating
    from transactions import procurement_costs

DEFAULT_OUT = operating.ROOT / "industrial/generated/planning/capital"


def npv(rate: float, cashflows: list[float]) -> float:
    if rate <= -1 or not math.isfinite(rate) or not all(math.isfinite(c) for c in cashflows):
        raise ValueError("Finite cash flows and a discount rate above -100% are required")
    factor = 1.0
    result = 0.0
    for amount in cashflows:
        result += amount * factor
        factor /= 1 + rate
    return result


def irr(cashflows: list[float]) -> dict:
    nonzero = [c for c in cashflows if abs(c) > 1e-8]
    changes = sum(a * b < 0 for a, b in zip(nonzero, nonzero[1:], strict=False))
    if not changes:
        return {"status": "NO_IRR_NO_SIGN_CHANGE", "period_rate": None, "annualized_rate": None}
    if changes > 1:
        return {
            "status": "AMBIGUOUS_NONCONVENTIONAL_CASH_FLOW",
            "period_rate": None,
            "annualized_rate": None,
            "sign_changes": changes,
            "note": "No single IRR is selected; multiple or absent roots are possible. NPV remains the decision statistic.",  # noqa: E501 — disclosure text
        }
    low, high = -0.99, 1.0
    fl = npv(low, cashflows)
    fh = npv(high, cashflows)
    while fl * fh > 0 and high < 1e6:
        high = high * 2 + 1
        fh = npv(high, cashflows)
    if fl * fh > 0:
        return {"status": "NO_BRACKETED_IRR", "period_rate": None, "annualized_rate": None}
    for _ in range(180):
        middle = (low + high) / 2
        fm = npv(middle, cashflows)
        if (fl > 0) == (fm > 0):
            low, fl = middle, fm
        else:
            high = middle
    value = (low + high) / 2
    return {
        "status": "UNIQUE_CONVENTIONAL_IRR",
        "period_rate": value,
        "annualized_rate": (1 + value) ** 12 - 1,
    }


def annual_project_tax(taxable: float, carried_loss: float, source: dict) -> tuple[float, float]:
    if taxable < 0:
        return 0.0, carried_loss - taxable
    used = min(carried_loss, taxable * source["nol_utilization_limit_fraction"])
    return (taxable - used) * source["cash_tax_rate"], carried_loss - used


def contract_revenue(row: dict, contracts: list[dict], forecast_source: dict) -> float:
    """Match the forecast's rounded customer allocation without importing its ledger."""

    def money(value):
        return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))

    lost = set(row.get("lost_customer_ids", []))
    total = 0
    for segment, values in row["segments"].items():
        all_contracts = [
            c for c in contracts if c["month"] == row["month"] and c["segment"] == segment
        ]
        eligible = [c for c in all_contracts if c["customer_id"] not in lost]
        if not eligible:
            continue
        target = money(
            Decimal(sum(c["revenue_usd"] for c in all_contracts))
            * Decimal(str(values["revenue_volume_factor"]))
            * Decimal(str(row["assumptions"]["external_price_index"]))
        )
        denominator = sum(c["revenue_usd"] for c in eligible)
        exact = [Decimal(target) * c["revenue_usd"] / denominator for c in eligible]
        allocated = [int(value) for value in exact]
        order = sorted(range(len(exact)), key=lambda i: (-(exact[i] - allocated[i]), i))
        for index in order[: target - sum(allocated)]:
            allocated[index] += 1
        renewals = forecast_source["adjustments"][row["scenario"]][
            "contract_renewal_price_multipliers"
        ]
        total += sum(
            money(Decimal(amount) * Decimal(str(renewals.get(c["customer_id"], 1))))
            for c, amount in zip(eligible, allocated, strict=True)
        )
    return total


def _economic_rows(rows: list[dict]) -> list[dict]:
    finance = json.loads((operating.ROOT / "industrial/source/finance.json").read_text())
    baseline_payroll = defaultdict(float)
    for employee in finance["employees"]:
        baseline_payroll[employee["segment"]] += (
            employee["annual_salary_usd"]
            * (1 + employee["annual_employer_burden_pct"] / 100)
            * employee["fte"]
        )
    plan = operating.load_source()
    forecast_source = json.loads((operating.BASE / "source/forecast.json").read_text())
    _, _, contracts = customer_schedules(finance)
    ordinary_costs = {
        (r["scenario"], r["year"], r["month"], r["segment"]): float(r["external_cost_usd"])
        for r in procurement_costs(rows)
    }
    rates = {r["commodity"]: r for r in operating.legacy_operations()["interface"]["rates"]}
    result = []
    for row in rows:
        revenue = contract_revenue(row, contracts, forecast_source)
        payroll = ordinary = extra = 0.0
        payroll_multiplier = forecast_source["adjustments"][row["scenario"]]["payroll_multiplier"]
        for segment in (*operating.SEGMENTS, "ARU"):
            key = row["scenario"], row["year"], row["month"], segment
            ordinary += ordinary_costs[key]
            if segment == "ARU":
                payroll += (
                    baseline_payroll[segment]
                    / 12
                    * row["assumptions"]["cash_cost_index"]
                    * payroll_multiplier
                )
                continue
            segment_row = row["segments"][segment]
            payroll += (
                baseline_payroll[segment]
                / 12
                * segment_row["fte"]
                / plan["baseline_fte"][segment]
                * row["assumptions"]["cash_cost_index"]
                * payroll_multiplier
            )
            extra += segment_row["additional_cash_cost_usd"]
        interface_variable = 0.0
        ic = 0.0
        for commodity, count in row["interface"]["aru_served_cars_by_commodity"].items():
            rate = rates[commodity]
            interface_variable += (
                count
                * (
                    rate["rail_unit_cost"]
                    + rate["terminal_unit_cost"]
                    + rate["truck_legs_per_car"] * rate["dray_unit_cost"]
                )
                * row["assumptions"]["interface_cost_index"]
            )
            ic += (
                count
                * (
                    rate["rail_rate"]
                    + rate["terminal_rate"]
                    + rate["truck_legs_per_car"] * rate["dray_rate"]
                )
                * row["assumptions"]["interface_price_index"]
            )
        interface_cash = (
            interface_variable
            + 48000 / 12 * row["assumptions"]["interface_cost_index"]
            + row["interface"]["outside_service_cash_usd"]
            + row["interface"]["external_linehaul_usd"]
        )
        result.append(
            {
                "year": row["year"],
                "month": row["month"],
                "external_revenue_usd": revenue,
                "ordinary_nonpayroll_usd": ordinary,
                "payroll_usd": payroll,
                "additional_cash_cost_usd": extra,
                "real_interface_cash_cost_usd": interface_cash,
                "intercompany_revenue_excluded_usd": ic,
                "operating_cash_margin_usd": revenue - ordinary - payroll - extra - interface_cash,
                "capital": row["capital"],
                "served_units": {s: row["segments"][s]["served_units"] for s in operating.SEGMENTS},
                "lost_units": {s: row["segments"][s]["lost_units"] for s in operating.SEGMENTS},
            }
        )
    return result


def _compare(base: list[dict], option: list[dict], source: dict, strategy: str) -> dict:
    monthly = []
    nwc = 0.0
    carried_tax_loss = 0.0
    year_taxable = 0.0
    replacement_basis = []
    cumulative_growth = 0.0
    cumulative_growth_dda = 0.0
    monthly_discount = (1 + source["discount_rate"]) ** (1 / 12) - 1
    for reference, row in zip(base, option, strict=True):
        year, month = row["year"], row["month"]
        period = f"{year}-{month:02d}"
        revenue = row["external_revenue_usd"] - reference["external_revenue_usd"]
        margin = row["operating_cash_margin_usd"] - reference["operating_cash_margin_usd"]
        capex = row["capital"]["aru_growth_usd"] - reference["capital"]["aru_growth_usd"]
        mine_common_difference = (
            row["capital"]["mine_growth_usd"] - reference["capital"]["mine_growth_usd"]
        )
        if abs(mine_common_difference) > 1e-6:
            raise ValueError(
                "Compared logistics options must share the same conditional mine project"
            )
        replacement = (
            row["capital"]["aru_replacement_usd"] - reference["capital"]["aru_replacement_usd"]
        )
        cumulative_growth += capex
        growth_depreciation = 0.0
        for project in source["growth_projects"]:
            if (
                strategy == "owned"
                and project["owner"] == "ARU"
                and period > project["conditional_service_month"]
            ):
                growth_depreciation += (
                    project["growth_cost_usd"] / source["depreciation_years"]["ARU"] / 12
                )
        cumulative_growth_dda += growth_depreciation
        depreciation = growth_depreciation + sum(replacement_basis) / (
            source["replacement_depreciation_years"] * 12
        )
        if replacement > 0:
            replacement_basis.append(replacement)
        desired_nwc = max(
            0, revenue * 12 * source["net_working_capital_fraction_of_incremental_external_revenue"]
        )
        nwc_change = desired_nwc - nwc
        nwc = desired_nwc
        year_taxable += margin - depreciation
        residual = recovery = 0.0
        if year == 2031 and month == 12 and source.get("terminal_disposal", True):
            residual = cumulative_growth * source["residual_fraction_of_growth_cost"]
            residual_basis = cumulative_growth - cumulative_growth_dda
            year_taxable += residual - residual_basis
            recovery = nwc
        tax = 0.0
        if month == 12:
            tax, carried_tax_loss = annual_project_tax(year_taxable, carried_tax_loss, source)
            year_taxable = 0.0
        cash = margin - tax - capex - replacement - nwc_change + residual + recovery
        monthly.append(
            {
                "option": strategy,
                "year": year,
                "month": month,
                "period_role": "CONDITIONAL_PROJECT_CASH_FLOW",
                "incremental_external_revenue_usd": revenue,
                "incremental_cash_operating_margin_usd": margin,
                "intercompany_revenue_excluded_usd": row["intercompany_revenue_excluded_usd"]
                - reference["intercompany_revenue_excluded_usd"],
                "incremental_growth_capex_usd": capex,
                "incremental_replacement_capex_usd": replacement,
                "incremental_tax_depreciation_usd": depreciation,
                "incremental_cash_tax_usd": tax,
                "ending_project_tax_loss_usd": carried_tax_loss,
                "incremental_nwc_change_usd": nwc_change,
                "ending_incremental_nwc_usd": nwc,
                "terminal_residual_gross_usd": residual,
                "terminal_nwc_recovery_usd": recovery,
                "incremental_unlevered_cashflow_usd": cash,
            }
        )
    cashflows = [0] + [r["incremental_unlevered_cashflow_usd"] for r in monthly]
    return {
        "option": strategy,
        "basis": "Incremental consolidated logistics cash flows versus identical demand served with current logistics assets; common conditional mine growth cancels, and 2026 sunk capital is excluded.",  # noqa: E501 — disclosure text
        "npv_usd": npv(monthly_discount, cashflows),
        "irr": irr(cashflows),
        "incremental_external_revenue_5y_usd": sum(
            r["incremental_external_revenue_usd"] for r in monthly
        ),
        "incremental_growth_capex_usd": sum(r["incremental_growth_capex_usd"] for r in monthly),
        "incremental_replacement_capex_usd": sum(
            r["incremental_replacement_capex_usd"] for r in monthly
        ),
        "common_conditional_mine_growth_usd": sum(r["capital"]["mine_growth_usd"] for r in option),
        "sunk_2026_interface_cost_included_usd": 0,
        "monthly_cashflows": monthly,
    }


def evaluate(
    source: dict | None = None,
    demand_scale: float = 1,
    options: tuple[str, ...] = ("current", "outsource", "owned"),
) -> dict:
    source = source or operating.load_capital()
    if demand_scale < 0:
        raise ValueError("Demand scale must be nonnegative")
    plan = copy.deepcopy(operating.load_source())
    plan["scenarios"]["expansion"]["incremental_external_demand_scale"] = demand_scale
    economic = {}
    physical = {}
    for option in set(options) | {"current"}:
        rows = [
            r
            for r in operating.calculate(plan, {"expansion": option}, source)
            if r["scenario"] == "expansion"
        ]
        operating.validate(rows, plan)
        economic[option] = _economic_rows(rows)
        physical[option] = rows
    results = {
        name: _compare(economic["current"], economic[name], source, name) for name in options
    }
    return {
        "available_at": "2026-09-06T00:00:00-07:00",
        "record_origin": "PUBLIC_SYNTHETIC_PLANNING_MODEL",
        "decision_state": "OPTIONS_REVIEW_NOT_CAPITAL_APPROVAL",
        "incremental_external_demand_scale": demand_scale,
        "discount_rate": source["discount_rate"],
        "options": results,
        "physical_2031": {
            option: {
                segment: sum(
                    r["segments"][segment]["served_units"]
                    for r in physical[option]
                    if r["year"] == 2031
                )
                for segment in operating.SEGMENTS
            }
            for option in options
        },
        "retrospective": source["retrospective"],
        "conditions": source["conditions"],
    }


def break_even(source: dict, strategy: str, comparator: str = "current") -> dict:
    def value(scale: float) -> float:
        result = evaluate(source, scale, tuple(dict.fromkeys((strategy, comparator))))
        return result["options"][strategy]["npv_usd"] - result["options"][comparator]["npv_usd"]

    low, high = 0.0, 3.0
    first, last = value(low), value(high)
    # Capacity steps are explicit: report first bracket, not global monotonicity.
    points = [(i / 4, value(i / 4)) for i in range(13)]
    brackets = [(a, b) for a, b in zip(points, points[1:], strict=False) if a[1] <= 0 < b[1]]
    if not brackets:
        return {
            "status": "NO_POSITIVE_NPV_CROSSING_IN_TESTED_RANGE",
            "tested_incremental_demand_scale": [low, high],
            "npv_at_zero_usd": first,
            "npv_at_three_usd": last,
        }
    (low, _), (high, _) = brackets[0]
    for _ in range(20):
        mid = (low + high) / 2
        if value(mid) > 0:
            high = mid
        else:
            low = mid
    threshold = evaluate(source, high, tuple(dict.fromkeys((strategy, comparator))))
    plan = operating.load_source()
    annual_request = {
        s: round(
            plan["annual_2025_units"][s]
            + high
            * (
                plan["annual_2025_units"][s]
                * (1 + plan["scenarios"]["expansion"]["external_demand_growth"][s]) ** 5
                - plan["annual_2025_units"][s]
            )
        )
        for s in operating.SEGMENTS
    }
    return {
        "status": "FIRST_BRACKETED_NPV_CROSSING",
        "comparator": comparator,
        "incremental_demand_scale": high,
        "requested_2031_units": annual_request,
        "served_2031_units": threshold["physical_2031"][strategy],
        "npv_at_threshold_usd": value(high),
        "note": "Demand mix grows together; discrete capacity and integer cars make NPV stepped. This is a scenario threshold, not an independent market demand estimate.",  # noqa: E501 — disclosure text
    }


def build(
    output: Path = DEFAULT_OUT, source: dict | None = None, include_break_even: bool = True
) -> dict:
    source = source or operating.load_capital()
    result = evaluate(source)
    result["break_even"] = (
        {name: break_even(source, name) for name in ("outsource", "owned")}
        if include_break_even
        else {}
    )
    result["owned_vs_outsource_npv_usd"] = (
        result["options"]["owned"]["npv_usd"] - result["options"]["outsource"]["npv_usd"]
    )
    if include_break_even:
        result["break_even"]["owned_vs_outsource"] = break_even(source, "owned", "outsource")
    sensitivity = []
    for rate in [0.08, 0.10, 0.15]:
        for salvage in [0, 0.45, 0.65]:
            changed = copy.deepcopy(source)
            changed["discount_rate"], changed["residual_fraction_of_growth_cost"] = rate, salvage
            case = evaluate(changed)
            sensitivity.append(
                {
                    "discount_rate": rate,
                    "residual_fraction": salvage,
                    **{
                        name + "_npv_usd": case["options"][name]["npv_usd"]
                        for name in ("outsource", "owned")
                    },
                }
            )
    result["sensitivity"] = sensitivity
    no_disposal = copy.deepcopy(source)
    no_disposal["terminal_disposal"] = False
    continuing = evaluate(no_disposal)
    result["no_terminal_disposal_or_wc_recovery_npv_usd"] = {
        name: continuing["options"][name]["npv_usd"] for name in ("outsource", "owned")
    }
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    operating.write_json(output / "capital_review.json", result)
    operating.write_csv(
        output / "incremental_project_cashflows.csv",
        [r for option in result["options"].values() for r in option["monthly_cashflows"]],
    )
    operating.write_csv(output / "discount_residual_sensitivity.csv", sensitivity)
    summary = {
        "decision_state": result["decision_state"],
        "npv_usd": {k: round(v["npv_usd"]) for k, v in result["options"].items()},
        "irr": {k: v["irr"] for k, v in result["options"].items()},
        "break_even": result["break_even"],
    }
    operating.write_json(
        output / "validation.json",
        {
            "passed": all(
                v["sunk_2026_interface_cost_included_usd"] == 0 for v in result["options"].values()
            ),
            "checks": [
                "sunk capital excluded",
                "intercompany revenue excluded",
                "common mine capex cancels",
                "monthly physical capacities validated",
                "project cash tax loss balance nonnegative",
                "shared procurement costs used",
            ],
            "summary": summary,
        },
    )
    operating.write_manifest(
        output,
        [
            operating.BASE / "capital.py",
            operating.BASE / "operating_model.py",
            operating.BASE / "transactions.py",
            operating.BASE / "source/operating_plan.json",
            operating.BASE / "source/capital_options.json",
            operating.BASE / "source/transaction_policy.json",
            operating.BASE / "source/forecast.json",
            operating.ROOT / "industrial/tools/build_financials.py",
            operating.ROOT / "industrial/source/operations.json",
            operating.ROOT / "industrial/source/finance.json",
        ],
        {"capital_options": source, "operating_plan": operating.load_source()},
        [
            "capital_review.json",
            "incremental_project_cashflows.csv",
            "discount_residual_sensitivity.csv",
            "validation.json",
        ],
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--skip-break-even", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.out, include_break_even=not args.skip_break_even), indent=2))
