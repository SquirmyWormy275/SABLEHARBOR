"""Mine taxpayer cash inventory, cost-recovery and depletion tax bridges."""

import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

from enterprise.closeout.rwh_history import build as history_build

Q = D(".0001")


def build(result, book, assets, forecast_result):
    history = history_build()
    s = history["source"]
    logistics = json.loads(
        Path(__file__).with_name("source").joinpath("mine_tax_logistics.json").read_text()
    )
    h = {r["jurisdiction"]: r for r in history["rows"]}
    account = defaultdict(lambda: defaultdict(D))
    seen = set()
    for r in result["journal_rows"]:
        if int(r["month"]) <= 0:
            continue
        if r["entity"] in {"PS", "RWH"} or (
            r["entity"] == "ELIM" and r["source_id"].startswith("CO-RWH-BOOK-SERVICE-")
        ):
            identity = tuple(
                str(r.get(k, ""))
                for k in ("scenario", "entity", "year", "month", "journal_id", "account", "line_no")
            )
            if identity in seen:
                raise ValueError("Duplicate mine legal-book leg")
            seen.add(identity)
            key = r["scenario"], int(r["year"])
            account[key][r["account"]] += D(r["signed_usd"])
            if r["account_type"] in {"revenue", "expense"}:
                account[key]["_NET"] -= D(r["signed_usd"])
    by_period = {(r["scenario"], r["year"], r["month"]): r for r in book.rows}
    expected_periods = {
        (s, y, m)
        for s in ("base", "downside", "expansion")
        for y in range(2026, 2032)
        for m in range(1, 13)
    }
    if len(by_period) != len(book.rows) or set(by_period) != expected_periods:
        raise ValueError("Incomplete or duplicate mine inventory period population")
    if set(account) != {(s, y) for s, y, _ in expected_periods}:
        raise ValueError("Incomplete mine income population")
    result_rows = []
    for scenario in ("base", "downside", "expansion"):
        for jurisdiction in ("US", "CA", "IL", "WV"):
            historical_dda = assets["totals"][scenario, "PS", jurisdiction, 2025][
                "tax_depreciation_usd"
            ]
            idle_dda = historical_dda * D(s["whole_pool_idle_days"]) / D(s["owned_days"])
            tax_dda_inventory = (historical_dda - idle_dda) * D(125000) / D(s["produced_lb"])
            tax_cash_inventory = D(history["cash_inventory_usd"]) + sum(
                D(v) for v in s["production_indirect_allocations"].values()
            ) * D(125000) / D(s["produced_lb"])
            mineral = D(h["US"]["initial_mineral_basis_usd"]) - D(
                h["US"]["deduction_depletion_usd"]
            )
            depletion_units = D(7820000) + D(125000)
            initial_loss = max(
                -(
                    D(h["US"]["cash_cost_income_before_dda_usd"])
                    - (historical_dda - tax_dda_inventory)
                    - D(h["US"]["cost_depletion_usd"])
                ),
                D(0),
            )
            previous_book_cash = D(history["cash_inventory_usd"]) + D(
                s["book_normal_production_indirect_usd"]
            ) * D(125000) / D(s["produced_lb"])
            previous_tax_cash = tax_cash_inventory
            previous_difference = previous_tax_cash - previous_book_cash
            previous_stock_units = D(125000)
            for year in range(2026, 2032):
                a = account[scenario, year]
                months = [by_period[scenario, year, m] for m in range(1, 13)]
                produced = sum(D(r["production_lb"]) for r in months)
                sold = sum(D(r["sales_lb"]) for r in months)
                ending = previous_stock_units + produced - sold
                if ending < 0 or sold > depletion_units:
                    raise ValueError(
                        "Mine tax unit/depletion population exceeds available property"
                    )
                cash_cost = sum(
                    D(r["production_cash_cost_usd"]) + D(r["production_mineral_tax_usd"])
                    for r in months
                )
                support = sum(D(r["group_support_production_cost_usd"]) for r in months)
                allowance = assets["totals"][scenario, "PS", jurisdiction, year][
                    "tax_depreciation_usd"
                ]
                # Whole-month shutdown allocation is a modeled cost-recovery
                # method, separate from normal interruptions or low utilization.
                # Zero output alone does not establish that every asset was idle.
                # No future whole-pool idle cost-recovery exclusion is claimed.
                current_idle = D(0)
                active_allowance = allowance - current_idle
                additional = sum(
                    D(r["signed_usd"])
                    for r in forecast_result["journal_rows"]
                    if r["scenario"] == scenario
                    and r["entity"] == "RWH_PS"
                    and int(r["year"]) == year
                    and r["account"] == "5100"
                    and r.get("source_type") in {"PRODUCTION_COST", "MINE_DISRUPTION"}
                )
                inbound = a["5200"] + sum(
                    D(r["signed_usd"])
                    for r in result["journal_rows"]
                    if r["scenario"] == scenario
                    and int(r["year"]) == year
                    and int(r["month"]) > 0
                    and r["entity"] == "RWH"
                    and r["account"] == "5150"
                    and not r["source_id"].startswith("CO-RWH-BOOK-")
                )
                freight_assay = (
                    D(logistics["current_2026_freight_assay_handling_usd"])
                    if year == 2026
                    else sum(
                        D(r["signed_usd"])
                        for r in forecast_result["journal_rows"]
                        if r["scenario"] == scenario
                        and int(r["year"]) == year
                        and r["entity"] == "RWH_PS"
                        and r["account"] == "5100"
                        and r.get("source_type") == "MINE_FREIGHT_ASSAY"
                    )
                )
                freight_assay = D(freight_assay)
                assay = freight_assay * D(logistics["ordinary_assay_fraction"])
                transport = freight_assay - assay
                additional += inbound + assay
                available = previous_stock_units + produced
                if available <= 0:
                    raise ValueError("Annual mine tax pool has no allocable production")
                opening_tax_cash = tax_cash_inventory
                incurred_tax_cash = cash_cost + support + additional
                tax_cash_inventory = (
                    (tax_cash_inventory + cash_cost + support + additional) * ending / available
                )
                dda_cogs = (tax_dda_inventory + active_allowance) * sold / available
                tax_dda_inventory += active_allowance - dda_cogs
                closing_book_cash = D(months[-1]["corrected_cash_inventory_usd"]) + D(
                    months[-1]["consolidated_service_cost_inventory_usd"]
                )
                difference = tax_cash_inventory - closing_book_cash
                inventory_income_adjustment = difference - previous_difference
                native_income_tax = a["5500"] + a["5501"] + a["CO_STATE_MIN_EXP"]
                unpaid_transaction_tax = a["CO_RWH_ROT_EXP"]
                common = (
                    a["_NET"]
                    + native_income_tax
                    + a["5300"]
                    + a["5600"]
                    + unpaid_transaction_tax
                    + inventory_income_adjustment
                )
                before_depletion = common - dda_cogs - current_idle
                cost_depletion = (
                    min(mineral, mineral * sold / depletion_units) if depletion_units else D(0)
                )
                # The mine's existing external delivered-sales freight is a
                # separately disclosed mine-gate netback estimate, not revenue.
                mining_gross = max(-a["4000"] - transport, D(0))
                percentage = min(mining_gross * D(".22"), max(before_depletion, D(0)) * D(".5"))
                deduction = max(cost_depletion, percentage)
                basis_reduction = min(mineral, deduction)
                mineral -= basis_reduction
                depletion_units -= sold
                taxable = before_depletion - deduction
                result_rows.append(
                    dict(
                        scenario=scenario,
                        year=year,
                        taxpayer="PS",
                        jurisdiction=jurisdiction,
                        book_income_before_native_tax_usd=str(
                            (a["_NET"] + native_income_tax).quantize(Q)
                        ),
                        book_dda_expense_added_back_usd=str(a["5300"]),
                        aro_accretion_added_back_usd=str(a["5600"]),
                        unpaid_rot_added_back_usd=str(unpaid_transaction_tax),
                        cash_inventory_income_adjustment_usd=str(
                            inventory_income_adjustment.quantize(Q)
                        ),
                        tax_depreciation_allowance_usd=str(allowance),
                        idle_depreciation_deduction_usd=str(current_idle.quantize(Q)),
                        tax_dda_cogs_usd=str(dda_cogs.quantize(Q)),
                        tax_cash_inventory_usd=str(tax_cash_inventory.quantize(Q)),
                        opening_tax_cash_inventory_usd=str(opening_tax_cash.quantize(Q)),
                        tax_cash_cost_incurred_usd=str(incurred_tax_cash.quantize(Q)),
                        tax_cash_cost_cogs_usd=str(
                            (opening_tax_cash + incurred_tax_cash - tax_cash_inventory).quantize(Q)
                        ),
                        tax_dda_inventory_usd=str(tax_dda_inventory.quantize(Q)),
                        tax_mineral_basis_usd=str(mineral.quantize(Q)),
                        cost_depletion_usd=str(cost_depletion.quantize(Q)),
                        percentage_depletion_usd=str(percentage.quantize(Q)),
                        depletion_deduction_usd=str(deduction.quantize(Q)),
                        income_before_nol_usd=str(taxable.quantize(Q)),
                        opening_2026_loss_before_state_apportionment_usd=str(
                            initial_loss.quantize(Q)
                        ),
                        source_taxpayer_boundary="PS includes disregarded RWH; state loss not a filed member NOL",
                        production_support_incurred_usd=str(support.quantize(Q)),
                        additional_idle_production_cash_capitalized_pool_usd=str(
                            additional.quantize(Q)
                        ),
                        tax_inventory_method="ANNUAL_WEIGHTED_AVERAGE; book normal-capacity and monthly layers separately reconciled",
                        mining_gross_income_netback_usd=str(mining_gross.quantize(Q)),
                        inbound_production_logistics_capitalized_pool_usd=str(inbound.quantize(Q)),
                        ordinary_assay_capitalized_pool_usd=str(assay.quantize(Q)),
                        outbound_transport_netback_usd=str(transport.quantize(Q)),
                        netback_estimate_zero_to_full_freight_usd=str(freight_assay.quantize(Q)),
                    )
                )
                previous_difference = difference
                previous_book_cash = closing_book_cash
                previous_tax_cash = tax_cash_inventory
                previous_stock_units = ending
    return result_rows
