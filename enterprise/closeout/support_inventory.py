"""Normal support-cost layer, with separate legal fee and consolidated cost."""

import json
from decimal import Decimal as D
from pathlib import Path

SOURCE = Path(__file__).with_name("source") / "mine_support_allocation.json"
Q = D(".0001")


def allocation(source_rows, year, month):
    policy = json.loads(SOURCE.read_text())
    share = D(policy["ps_production_share"])
    if share != D(policy["august_ps_production_cost_usd"]) / D(policy["august_ps_total_cost_usd"]):
        raise ValueError("Platform support share differs from current work allocation")
    ga = sum(
        D(r["signed_usd"])
        for r in source_rows
        if r["account"] == "5100"
        and (
            r.get("description") == "pale sun site g and a usd"
            or r.get("source_type") == "MINE_PLATFORM_SITE_GA"
        )
    )
    if ga <= 0:
        raise ValueError("Missing mine/platform G&A source population")
    fee = D(125000) if year == 2026 else ga * D(15) / 28
    ps_cost = fee + (D(78125) if (year, month) == (2026, 8) else D(0))
    site_cost = ga - ps_cost
    bond = min(site_cost, D(policy["bond_monthly_component_usd"]))
    site_production = bond + (site_cost - bond) * D(policy["rwh_site_other_production_share"])
    fee_production = fee * share
    ps_production = ps_cost * share
    if site_cost < 0 or min(site_production, fee_production, ps_production) < 0:
        raise ValueError("Production-support allocation exceeds source cost capacity")
    return dict(
        group_ga_cost=ga,
        ps_cost=ps_cost,
        site_cost=site_cost,
        legal_production_cost=fee_production + site_production,
        group_production_cost=ps_production + site_production,
        fee_production_cost=fee_production,
        site_production_cost=site_production,
    )


def step(
    previous_legal, previous_elimination, source_rows, year, month, available_units, sold_units
):
    if not 0 <= sold_units <= available_units or available_units <= 0:
        raise ValueError("Invalid support-cost inventory quantity population")
    a = allocation(source_rows, year, month)
    legal_cogs = (previous_legal + a["legal_production_cost"]) * sold_units / available_units
    elimination_cogs = (
        (previous_elimination + a["group_production_cost"] - a["legal_production_cost"])
        * sold_units
        / available_units
    )
    closing_legal = previous_legal + a["legal_production_cost"] - legal_cogs
    closing_elimination = (
        previous_elimination
        + a["group_production_cost"]
        - a["legal_production_cost"]
        - elimination_cogs
    )
    return a | dict(
        legal_cogs=legal_cogs,
        elimination_cogs=elimination_cogs,
        closing_legal=closing_legal,
        closing_elimination=closing_elimination,
    )
