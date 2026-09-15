"""Finite H2 mine cash, quantity, book carrying and tax-opening reconstruction."""

import json
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name("source") / "rwh_tax_history.json"
Q = D(".0001")


def build():
    s = json.loads(SOURCE.read_text())
    native = json.loads((ROOT / "red_wash/source/core_operating_data.json").read_text())
    t = native["transaction"]
    classes = {k: D(v) for k, v in s["operating_asset_classes"].items()}
    if sum(classes.values()) != D(t["operating_assets_usd"]):
        raise ValueError("RWH asset classes change accepted42m purchase allocation")
    if sum(D(v) for v in s["acquired_current_assets"].values()) != D(t["current_assets_usd"]):
        raise ValueError("RWH current asset allocation differs")
    produced = D(s["produced_lb"])
    sold = D(s["sold_lb"])
    ending = produced - sold
    if ending != 125000:
        raise ValueError("H2 units do not reach accepted opening finished inventory")
    production = sum(D(v) for v in s["production_cash_costs"].values())
    other = sum(D(v) for v in s["nonproduction_cash_costs"].values())
    repair = D(s["repair_cost_usd"])
    rehab = D(s["rehabilitation_usd"])
    if (repair, rehab) != (
        D(t["repair_stabilization_expense_usd"]),
        D(t["capitalized_rehabilitation_usd"]),
    ):
        raise ValueError("Stabilization source changed")
    cash_inventory = production * ending / produced
    cash_cogs = production - cash_inventory
    contributions = D("44312500")
    closing_cash = (
        contributions
        - D(t["cash_consideration_usd"])
        - rehab
        + D(s["sales_usd"])
        - production
        - other
        - repair
        + D(s["closing_trade_payables_usd"])
    )
    if closing_cash != D("2000000") or cash_inventory != D("5625000"):
        raise ValueError("Authored H2cash/cost events do not reach source cash/inventory")
    implied_tpd = produced / (D(2000) * D(".0017") * D(".92")) / D(167)
    if implied_tpd > D(native["mine_2026"]["nameplate_tpd"]):
        raise ValueError("Authored H2 production exceeds retained plant nameplate")
    reserve = D(native["resource_basis"]["recoverable_lb"]) + produced
    productive = classes["mineral_interest"] + classes["production_plant"]
    book_dda = productive * produced / reserve
    book_dda_inventory = book_dda * ending / produced
    original_dda_inventory = D("687500")
    book_inventory_delta = book_dda_inventory - original_dda_inventory
    opening_equity_correction = book_dda - book_inventory_delta
    initial_tax_cost = (
        D(t["cash_consideration_usd"]) + D(t["other_liabilities_usd"]) - D(t["current_assets_usd"])
    )
    tax_classes = {k: initial_tax_cost * v / sum(classes.values()) for k, v in classes.items()}
    cost_depletion = tax_classes["mineral_interest"] * sold / reserve
    plant_federal = tax_classes["production_plant"]
    plant_ca = plant_federal / D(10) * D(167) / D(365)
    results = []
    cash_profit = D(s["sales_usd"]) - cash_cogs - other - repair
    for jurisdiction, plant_dda in [("US", plant_federal), ("CA", plant_ca)]:
        dda_inventory = plant_dda * ending / produced
        deducted_dda = plant_dda - dda_inventory
        predepletion = cash_profit - deducted_dda
        percentage = min(D(s["sales_usd"]) * D(".22"), max(predepletion, D(0)) * D(".5"))
        depletion = max(cost_depletion, percentage)
        income = predepletion - depletion
        results.append(
            dict(
                jurisdiction=jurisdiction,
                taxpayer="PS",
                legal_operator="RWH",
                period="2025-H2",
                cash_cost_income_before_dda_usd=str(cash_profit.quantize(Q)),
                initial_operating_tax_cost_usd=str(initial_tax_cost),
                initial_land_basis_usd=str(tax_classes["surface_land"].quantize(Q)),
                initial_mineral_basis_usd=str(tax_classes["mineral_interest"].quantize(Q)),
                initial_plant_basis_usd=str(plant_federal.quantize(Q)),
                production_depreciation_usd=str(plant_dda.quantize(Q)),
                depreciation_in_closing_inventory_usd=str(dda_inventory.quantize(Q)),
                depreciation_released_to_cogs_usd=str(deducted_dda.quantize(Q)),
                cost_depletion_usd=str(cost_depletion.quantize(Q)),
                percentage_depletion_usd=str(percentage.quantize(Q)),
                deduction_depletion_usd=str(depletion.quantize(Q)),
                taxable_income_usd=str(income.quantize(Q)),
                loss_before_state_apportionment_usd=str(max(-income, D(0)).quantize(Q)),
                closing_inventory_tax_basis_usd=str((cash_inventory + dda_inventory).quantize(Q)),
                closing_operating_tax_basis_usd=str(
                    (initial_tax_cost - plant_dda - depletion + rehab).quantize(Q)
                ),
                aro_basis_included_usd="0",
                remittance_usd="0",
                state_loss_boundary="CA amount is pre-apportionment; do not treat as filedmemberNOL",
                fact_state="NEWLY_AUTHORED_CONSTRAINED_SYNTHETIC_HISTORY",
            )
        )
    return dict(
        source=s,
        rows=results,
        closing_cash_usd=str(closing_cash),
        ending_inventory_lb=str(ending),
        book_dda_usd=str(book_dda.quantize(Q)),
        book_inventory_delta_usd=str(book_inventory_delta.quantize(Q)),
        opening_equity_correction_usd=str(opening_equity_correction.quantize(Q)),
        cash_inventory_usd=str(cash_inventory),
        source_contributed_cash_usd=str(contributions),
        adopted_initial_goodwill_usd="0",
        book_correction_posting_state="PREPARED_NOT_POSTED_PENDING_FORWARD_INVENTORY_CARRYING_COMPOSITION",
    )
