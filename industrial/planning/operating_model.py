#!/usr/bin/env python3
"""Constrained monthly physical forecasts. All future events are conditional cases."""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DEFAULT_OUT = ROOT / "industrial/generated/planning/operations"
SEGMENTS = ("BST", "TERMINALS", "TRUCKING", "WAREHOUSE")


def load_source() -> dict:
    return json.loads((BASE / "source/operating_plan.json").read_text())


def load_capital() -> dict:
    return json.loads((BASE / "source/capital_options.json").read_text())


def legacy_operations() -> dict:
    return json.loads((ROOT / "industrial/source/operations.json").read_text())


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v
                    for k, v in row.items()
                }
            )


def monthly_allocation(annual_units: int, weights: list[int]) -> list[int]:
    """Largest-remainder allocation preserves exact annual integer quantities."""
    exact = [annual_units * weight / sum(weights) for weight in weights]
    allocated = [math.floor(number) for number in exact]
    order = sorted(range(len(weights)), key=lambda i: (-(exact[i] - allocated[i]), i))
    for index in order[: annual_units - sum(allocated)]:
        allocated[index] += 1
    return allocated


def active_events(source: dict, scenario: str, period: str) -> list[dict]:
    return [
        event
        for event in source["events"]
        if event["scenario"] == scenario
        and (
            period in event.get("months", [])
            or event.get("start_month", "9999") <= period <= event.get("end_month", "0000")
        )
    ]


def train_limit(effort_lb: float, locomotive_tons: float, rail: dict) -> int:
    resistance = 20 * rail["ruling_grade_pct"] + rail["rolling_resistance_lb_per_ton"]
    return max(0, math.floor((effort_lb / resistance - locomotive_tons) / rail["gross_car_tons"]))


def rail_capacity(
    source: dict, service_days: int, winter: bool, failure: int, expanded: bool
) -> dict:
    rail = source["rail"]
    effort = rail["failure_tractive_effort_lb"] if failure else rail["normal_tractive_effort_lb"]
    tons = rail["failure_locomotive_tons"] if failure else rail["normal_locomotive_tons"]
    if failure >= 2:
        effort = rail["reserve_tractive_effort_lb"] if failure == 2 else 0
        tons = rail["reserve_locomotive_tons"] if failure == 2 else 0
    if winter:
        effort *= rail["winter_tractive_factor"]
    limit = min(rail["normal_train_limit"], train_limit(effort, tons, rail))
    mph = rail["failure_average_mph"] if failure else rail["normal_average_mph"]
    if failure >= 2:
        mph = rail["single_average_mph"]
    round_trip = 2 * rail["mainline_miles"] / mph + rail["switch_hours_round_trip"]
    crew_hours = (
        rail["expanded_crew_duty_hours_daily"] if expanded else rail["normal_crew_duty_hours_daily"]
    )
    trips = min(
        rail["conditional_maximum_round_trips_daily"]
        if expanded
        else rail["normal_round_trips_daily"],
        max(0, math.floor((crew_hours - rail["branch_hours_daily"]) / round_trip)),
    )
    return {
        "loaded_cars_per_train": limit,
        "round_trips_daily": trips,
        "service_days": service_days,
        "capacity_cars": service_days * trips * limit,
        "train_hours_daily": trips * round_trip + rail["branch_hours_daily"],
        "crew_duty_hours_daily": crew_hours,
        "tractive_effort_lb": effort,
    }


def _capital_month(
    source: dict, options: dict, case: dict, strategy: str, period: str, cost_index: float
) -> tuple[dict, dict, dict]:
    capacities = dict(source["capacity"])
    capacities.update(
        {
            "daily_nameplate_tons": source["mine"]["daily_nameplate_tons"],
            "rail_round_trips_daily": 3,
        }
    )
    fte = dict(source["baseline_fte"])
    output = {
        "aru_growth_usd": 0.0,
        "mine_growth_usd": 0.0,
        "aru_replacement_usd": 0.0,
        "mine_replacement_usd": 0.0,
        "conditional_in_service_events": [],
        "growth_by_segment": {},
        "active_growth_by_segment": {},
        "incremental_fixed_opex_by_segment": {s: 0.0 for s in (*SEGMENTS, "RWH")},
    }
    active_aru_cost = 0.0
    for project in options["growth_projects"]:
        enabled = case["mine_growth"] if project["owner"] == "RWH" else strategy == "owned"
        if not enabled:
            continue
        key = "mine_growth_usd" if project["owner"] == "RWH" else "aru_growth_usd"
        if period in project["spend_months"]:
            amount = project["growth_cost_usd"] / len(project["spend_months"])
            output[key] += amount
            output["growth_by_segment"][project["segment"]] = amount
        if period >= project["conditional_service_month"]:
            capacities.update(project["capacity_changes"])
            fte[project["segment"]] = fte.get(project["segment"], 128) + project["fte_added"]
            output["active_growth_by_segment"][project["segment"]] = project["growth_cost_usd"]
            output["incremental_fixed_opex_by_segment"][project["segment"]] += (
                project["incremental_fixed_opex_year_usd"]
                / 12
                * cost_index
                / source["external_2026_cost_index"]
            )
            if project["owner"] == "ARU":
                active_aru_cost += project["growth_cost_usd"]
        if period == project["conditional_service_month"]:
            output["conditional_in_service_events"].append(
                {
                    "project_id": project["id"],
                    "period": period,
                    "status": "CONDITIONAL_CAPACITY_ASSUMPTION_NOT_COMMISSIONING",
                    "authority_granted": False,
                }
            )
    year = int(period[:4])
    replacements = source["replacements"]
    inflation = cost_index / source["external_2026_cost_index"]
    output["aru_replacement_usd"] = (
        (
            replacements["aru_2026_base_usd"]
            + active_aru_cost * replacements["incremental_installed_asset_replacement_fraction"]
        )
        / 12
        * inflation
    )
    output["mine_replacement_usd"] = (
        replacements["mine_2026_sustaining_usd"] / 12 * inflation
        + replacements["mine_remaining_rehab_by_year"][str(year)] / 12
    )
    return output, capacities, fte


def calculate(
    source: dict | None = None,
    strategy_overrides: dict | None = None,
    capital_source: dict | None = None,
) -> list[dict]:
    """Return 180 records, with optional capital strategy overrides for comparison.

    served_units includes externally subcontracted fulfillment; owned_served_units
    alone drives ordinary ARU procurement. Subcontractor cost is charged once in
    additional_cash_cost_usd. Inbound outside carriers are paid by Red Wash and
    excluded from ARU revenues. No mine or rail authority is conferred by a case.
    """
    source = source or load_source()
    options = capital_source or load_capital()
    legacy = legacy_operations()
    rates = {r["commodity"]: r for r in legacy["interface"]["rates"]}
    dray_hours = {
        name: v["dray"]["cycle_hours"]
        for name, v in legacy["interface"]["unit_cost_components"].items()
    }
    rows = []
    for scenario, case in source["scenarios"].items():
        strategy = (strategy_overrides or {}).get(scenario, case["strategy"])
        if strategy not in {"current", "outsource", "owned"}:
            raise ValueError("Unknown capital strategy")
        override = scenario in (strategy_overrides or {})
        outsource_fraction = (
            (0 if strategy == "current" else 1)
            if override
            else case["ordinary_external_outsource_fraction"]
        )
        stock_acid = source["mine"]["opening_acid_tons"]
        stock_binder = source["mine"]["opening_binder_tons"]
        stock_product = source["mine"]["opening_product_inventory_lb"]
        for year in source["years"]:
            for month in range(1, 13):
                period = f"{year}-{month:02d}"
                days = calendar.monthrange(year, month)[1]
                weekdays = sum(calendar.weekday(year, month, day) < 5 for day in range(1, days + 1))
                weight = source["monthly_weights"][month - 1] / sum(source["monthly_weights"])
                events = active_events(source, scenario, period)
                winter = month in {1, 2, 12}
                winter_event = next((e for e in events if e["type"] == "winter"), None)
                failed_units = max((e.get("failed_units", 0) for e in events), default=0)
                failure_days = max((e.get("downtime_service_days", 0) for e in events), default=0)
                lost_days = sum(e.get("rail_lost_service_days", 0) for e in events) + (
                    1 if winter and not winter_event else 0
                )
                service_days = max(0, weekdays - lost_days)
                price_index = source["external_2026_price_index"] * (
                    1 + source["annual_price_growth"]
                ) ** (year - 2026)
                cost_index = source["external_2026_cost_index"] * (
                    1 + source["annual_cost_growth"]
                ) ** (year - 2026)
                capital, capacity, fte = _capital_month(
                    source, options, case, strategy, period, cost_index
                )
                expanded = capacity["rail_round_trips_daily"] == 4
                rail = rail_capacity(source, service_days, winter, failed_units, expanded)
                outside_rail = rail_capacity(source, service_days, winter, failed_units, True)
                if failed_units:
                    degraded_days = min(service_days, failure_days)
                    normal = rail_capacity(
                        source, service_days - degraded_days, winter, 0, expanded
                    )
                    rail["capacity_cars"] = (
                        normal["capacity_cars"]
                        + rail["round_trips_daily"] * rail["loaded_cars_per_train"] * degraded_days
                    )
                    normal_outside = rail_capacity(
                        source, service_days - degraded_days, winter, 0, True
                    )
                    outside_rail["capacity_cars"] = (
                        normal_outside["capacity_cars"]
                        + outside_rail["round_trips_daily"]
                        * outside_rail["loaded_cars_per_train"]
                        * degraded_days
                    )
                    rail["degraded_service_days"] = degraded_days
                    rail["failed_units"] = failed_units
                truck_cycle = (
                    winter_event["truck_cycle_multiplier"]
                    if winter_event
                    else (capacity["winter_truck_cycle_multiplier"] if winter else 1)
                )
                available_driver_hours = (
                    capacity["drivers"] * capacity["driver_productive_hours_year"] / 12
                )
                available_tractor_hours = (
                    capacity["tractors"] * capacity["tractor_available_hours_year"] / 12
                )
                truck_hours = min(available_driver_hours, available_tractor_hours)
                unit_capacities = {
                    "BST": rail["capacity_cars"],
                    "TERMINALS": capacity["terminal_tons_year"] / 12,
                    "TRUCKING": math.floor(
                        truck_hours / (capacity["external_truck_hours_per_dispatch"] * truck_cycle)
                    ),
                    "WAREHOUSE": capacity["warehouse_slots"],
                }
                segments = {}
                for segment in SEGMENTS:
                    baseline = source["annual_2025_units"][segment] * weight
                    starting_units = source["annual_2025_units"][segment]
                    annual_demand = round(
                        starting_units
                        + case.get("incremental_external_demand_scale", 1)
                        * (
                            starting_units
                            * (1 + case["external_demand_growth"][segment]) ** (year - 2026)
                            - starting_units
                        )
                    )
                    demand = monthly_allocation(annual_demand, source["monthly_weights"])[month - 1]
                    loss_fraction = max(
                        (e.get("loss_fraction_by_segment", {}).get(segment, 0) for e in events),
                        default=0,
                    )
                    revenue_loss_fraction = max(
                        (
                            e.get("loss_revenue_fraction_by_segment", {}).get(segment, 0)
                            for e in events
                        ),
                        default=0,
                    )
                    eligible = max(0, demand - round(demand * loss_fraction))
                    owned = min(eligible, math.floor(unit_capacities[segment]))
                    extra_capacity = source["outside_capacity"][segment]["annual_units"] / 12
                    if segment == "BST":
                        extra_capacity = min(
                            extra_capacity, max(0, outside_rail["capacity_cars"] - owned)
                        )
                    outsourced = min(
                        math.floor((eligible - owned) * outsource_fraction),
                        math.floor(extra_capacity),
                    )
                    outside_cost = (
                        outsourced
                        * source["outside_capacity"][segment]["unit_cost_2026_usd"]
                        * cost_index
                        / source["external_2026_cost_index"]
                    )
                    event_cost = sum(
                        e.get("additional_cost_by_segment", {}).get(segment, 0) for e in events
                    )
                    fixed = capital["incremental_fixed_opex_by_segment"][segment]
                    if strategy == "outsource" and period == "2027-01":
                        event_cost += options.get("outsourcing_setup_cost_by_segment", {}).get(
                            segment, 0
                        )
                    revenue_factor = (
                        demand
                        / baseline
                        * (1 - revenue_loss_fraction)
                        * ((owned + outsourced) / eligible if eligible else 0)
                    )
                    segments[segment] = {
                        "unit": {
                            "BST": "loaded_revenue_car",
                            "TERMINALS": "handled_short_ton",
                            "TRUCKING": "billable_truck_dispatch",
                            "WAREHOUSE": "reserved_pallet_month",
                        }[segment],
                        "baseline_2025_month_units": baseline,
                        "demand_units": demand,
                        "eligible_demand_units": eligible,
                        "customer_loss_units": demand - eligible,
                        "customer_loss_revenue_fraction": revenue_loss_fraction,
                        "served_units": owned + outsourced,
                        "owned_served_units": owned,
                        "outsourced_units": outsourced,
                        "lost_units": demand - owned - outsourced,
                        "capacity_owned_units": unit_capacities[segment],
                        "revenue_volume_factor": revenue_factor,
                        "cost_volume_factor": owned / baseline,
                        "additional_cash_cost_usd": outside_cost + event_cost + fixed,
                        "outside_provider_cash_usd": outside_cost,
                        "disruption_cash_usd": event_cost,
                        "incremental_fixed_cash_usd": fixed,
                        "fte": fte[segment],
                    }
                # Mine feed can be curtailed independently by equipment, acid or product storage.
                mine = source["mine"]
                processing_days = (
                    mine["annual_processing_days"] * days / (366 if calendar.isleap(year) else 365)
                )
                lost_mine_days = sum(e.get("unavailable_calendar_days", 0) for e in events)
                operable_tons = (
                    capacity["daily_nameplate_tons"]
                    * processing_days
                    * mine["normal_availability"]
                    * max(0, days - lost_mine_days)
                    / days
                )
                requested_tons = (
                    case["annual_ore_targets"][year - source["years"][0]]
                    * days
                    / (366 if calendar.isleap(year) else 365)
                )
                sales_growth = case.get("sales_growth", mine["sales_growth"])
                requested_sales = monthly_allocation(
                    round(mine["sales_demand_2027_lb"] * (1 + sales_growth) ** (year - 2027)),
                    source["monthly_weights"],
                )[month - 1]
                yield_lb = 2000 * mine["grade_fraction"] * mine["recovery_fraction"]
                product_capacity_tons = max(
                    0,
                    (
                        mine.get("maximum_product_inventory_lb", 250000)
                        + requested_sales
                        - stock_product
                    )
                    / yield_lb,
                )
                before_inventory_tons = min(requested_tons, operable_tons, product_capacity_tons)
                planned_acid_cars = max(
                    0,
                    math.ceil(
                        (
                            before_inventory_tons * mine["acid_tons_per_ore_ton"]
                            + mine["acid_minimum_tons"]
                            - stock_acid
                        )
                        / 100
                        - 1e-10
                    ),
                )
                acid_fraction = min((e.get("acid_delivery_fraction", 1) for e in events), default=1)
                acid_cars = math.floor(planned_acid_cars * acid_fraction)
                acid_available_feed = max(
                    0,
                    (stock_acid + acid_cars * 100 - mine["acid_minimum_tons"])
                    / mine["acid_tons_per_ore_ton"],
                )
                ore = min(before_inventory_tons, acid_available_feed)
                binder_cars = max(
                    0,
                    math.ceil(
                        (
                            ore * mine["binder_tons_per_ore_ton"]
                            + mine["binder_minimum_tons"]
                            - stock_binder
                        )
                        / 100
                        - 1e-10
                    ),
                )
                opening_acid, opening_binder, opening_product = (
                    stock_acid,
                    stock_binder,
                    stock_product,
                )
                stock_acid += 100 * acid_cars - ore * mine["acid_tons_per_ore_ton"]
                stock_binder += 100 * binder_cars - ore * mine["binder_tons_per_ore_ton"]
                production = ore * yield_lb
                sales = min(
                    requested_sales,
                    max(0, stock_product + production - mine["minimum_product_inventory_lb"]),
                )
                stock_product += production - sales
                cars = {"acid": acid_cars, "binder": binder_cars}
                for commodity, annual in mine["ordinary_annual_cars_at_225000_ore_tons"].items():
                    cars[commodity] = max(0, round(annual * ore / 225000))
                cars["project"] = monthly_allocation(
                    mine["annual_project_cars"], [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0]
                )[month - 1]
                rail_remaining = max(
                    0, rail["capacity_cars"] - segments["BST"]["owned_served_units"]
                )
                terminal_remaining = max(
                    0, unit_capacities["TERMINALS"] - segments["TERMINALS"]["owned_served_units"]
                )
                truck_hours_remaining = max(
                    0,
                    truck_hours
                    - segments["TRUCKING"]["owned_served_units"]
                    * capacity["external_truck_hours_per_dispatch"]
                    * truck_cycle,
                )
                aru_cars, outside_cars = {}, {}
                interface_tons = interface_trips = interface_hours = 0.0
                interface_limit_remaining = legacy["interface"]["design_capacity_cars"] / 12
                for commodity, count in cars.items():
                    rate = rates[commodity]
                    per_car_hours = rate["truck_legs_per_car"] * dray_hours[commodity] * truck_cycle
                    accepted = min(
                        count,
                        int(rail_remaining),
                        int(terminal_remaining / rate["car_payload_short_tons"]),
                        int(truck_hours_remaining / per_car_hours),
                        int(interface_limit_remaining),
                    )
                    aru_cars[commodity] = accepted
                    outside_cars[commodity] = count - accepted
                    rail_remaining -= accepted
                    terminal_remaining -= accepted * rate["car_payload_short_tons"]
                    truck_hours_remaining -= accepted * per_car_hours
                    interface_limit_remaining -= accepted
                    interface_tons += accepted * rate["car_payload_short_tons"]
                    interface_trips += accepted * rate["truck_legs_per_car"]
                    interface_hours += accepted * per_car_hours
                linehaul = (
                    sum(cars[c] * rates[c]["external_linehaul_per_car"] for c in cars)
                    * cost_index
                    / source["external_2026_cost_index"]
                )
                outside_inbound = (
                    sum(
                        outside_cars[c] * source["outside_inbound_service_per_car_2026_usd"][c]
                        for c in cars
                    )
                    * cost_index
                    / source["external_2026_cost_index"]
                )
                constraints = []
                if ore + 1e-6 < requested_tons:
                    constraints.append("MINE_FEED_CURTAILED")
                if sales + 1e-6 < requested_sales:
                    constraints.append("PRODUCT_SALES_UNSERVED")
                if sum(outside_cars.values()):
                    constraints.append("INBOUND_OUTSIDE_CARRIER_SUBSTITUTION")
                if any(s["lost_units"] for s in segments.values()):
                    constraints.append("EXTERNAL_CUSTOMER_VOLUME_LOST")
                if any(s["outsourced_units"] for s in segments.values()):
                    constraints.append("EXTERNAL_CUSTOMER_VOLUME_SUBCONTRACTED")
                mine_cash = (
                    sum(e.get("mine_repair_cash_usd", 0) for e in events)
                    + capital["incremental_fixed_opex_by_segment"]["RWH"]
                )
                rows.append(
                    {
                        "available_at": "2026-09-06T00:00:00-07:00",
                        "record_origin": "PUBLIC_SYNTHETIC_PLANNING_MODEL",
                        "fact_state": "FORECAST",
                        "schema_version": "1.0",
                        "scenario": scenario,
                        "strategy": strategy,
                        "year": year,
                        "month": month,
                        "period": period,
                        "period_role": "CONDITIONAL_FORECAST",
                        "authority_granted": False,
                        "segments": segments,
                        "mine": {
                            "ore_tons": ore,
                            "requested_ore_tons": requested_tons,
                            "production_u3o8_lb": production,
                            "sales_u3o8_lb": sales,
                            "requested_sales_u3o8_lb": requested_sales,
                            "lost_sales_u3o8_lb": requested_sales - sales,
                            "opening_product_inventory_lb": opening_product,
                            "ending_product_inventory_lb": stock_product,
                            "operating_capacity_tons": operable_tons,
                            "lost_production_tons": requested_tons - ore,
                            "inventory_constrained_tons": before_inventory_tons - ore,
                            "opening_acid_tons": opening_acid,
                            "acid_received_tons": acid_cars * 100,
                            "acid_consumed_tons": ore * mine["acid_tons_per_ore_ton"],
                            "ending_acid_tons": stock_acid,
                            "opening_binder_tons": opening_binder,
                            "binder_received_tons": binder_cars * 100,
                            "binder_consumed_tons": ore * mine["binder_tons_per_ore_ton"],
                            "ending_binder_tons": stock_binder,
                            "uranium_price_usd_lb": mine["uranium_price_2026_usd_lb"]
                            * price_index
                            / source["external_2026_price_index"]
                            * case["uranium_price_multiplier"],
                            "production_cash_cost_index": cost_index,
                            "additional_cash_cost_usd": mine_cash,
                            "site_fte": 128,
                            "platform_fte": 12,
                            "direct_uranium_custody": "OPEN_GATED",
                        },
                        "interface": {
                            "cars_by_commodity": cars,
                            "aru_served_cars_by_commodity": aru_cars,
                            "outside_cars_by_commodity": outside_cars,
                            "external_linehaul_usd": linehaul,
                            "outside_service_cash_usd": outside_inbound,
                            "aru_handled_tons": interface_tons,
                            "aru_truck_dispatches": interface_trips,
                            "aru_truck_hours": interface_hours,
                        },
                        "capital": capital,
                        "assumptions": {
                            "external_price_index": price_index,
                            "cash_cost_index": cost_index,
                            "interface_price_index": price_index
                            / source["external_2026_price_index"],
                            "interface_cost_index": cost_index / source["external_2026_cost_index"],
                        },
                        "capacity": {
                            "rail": rail,
                            "conditional_total_rail_capacity_cars": outside_rail["capacity_cars"],
                            "truck_driver_hours": available_driver_hours,
                            "truck_tractor_hours": available_tractor_hours,
                            "truck_total_owned_required_hours": truck_hours - truck_hours_remaining,
                            "truck_cycle_multiplier": truck_cycle,
                            "terminal_owned_used_tons": segments["TERMINALS"]["owned_served_units"]
                            + interface_tons,
                            "terminal_owned_capacity_tons": unit_capacities["TERMINALS"],
                            "warehouse_owned_slots": capacity["warehouse_slots"],
                            "rail_owned_used_cars": segments["BST"]["owned_served_units"]
                            + sum(aru_cars.values()),
                        },
                        "lost_customer_ids": [
                            e["customer_id"] for e in events if e["type"] == "customer_loss"
                        ],
                        "events": [e["id"] for e in events],
                        "constraints": constraints,
                    }
                )
    return rows


def validate(rows: list[dict], source: dict | None = None) -> dict:
    source = source or load_source()
    checks = 0

    def check(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            raise ValueError(message)

    keys = [(r["scenario"], r["year"], r["month"]) for r in rows]
    check(len(set(keys)) == len(keys), "Duplicate scenario-month")
    for row in rows:
        key = f"{row['scenario']} {row['year']}-{row['month']:02d}"
        check(
            row["period_role"] == "CONDITIONAL_FORECAST" and row["authority_granted"] is False,
            f"{key}: forecast cannot grant authority",
        )
        check(row["available_at"] == source["available_at"], f"{key}: availability mismatch")
        cap, mine = row["capacity"], row["mine"]
        check(cap["rail_owned_used_cars"] <= cap["rail"]["capacity_cars"], f"{key}: rail capacity")
        check(
            cap["rail"]["train_hours_daily"] <= cap["rail"]["crew_duty_hours_daily"],
            f"{key}: crew hours",
        )
        check(
            cap["terminal_owned_used_tons"] <= cap["terminal_owned_capacity_tons"] + 1e-6,
            f"{key}: terminal capacity",
        )
        check(
            cap["truck_total_owned_required_hours"]
            <= min(cap["truck_driver_hours"], cap["truck_tractor_hours"]) + 1e-6,
            f"{key}: driver or tractor hours",
        )
        check(
            row["segments"]["WAREHOUSE"]["owned_served_units"] <= cap["warehouse_owned_slots"],
            f"{key}: warehouse capacity",
        )
        check(mine["ore_tons"] <= mine["operating_capacity_tons"] + 1e-6, f"{key}: mine capacity")
        for name in ("acid", "binder"):
            check(
                abs(
                    mine[f"opening_{name}_tons"]
                    + mine[f"{name}_received_tons"]
                    - mine[f"{name}_consumed_tons"]
                    - mine[f"ending_{name}_tons"]
                )
                < 1e-6,
                f"{key}: {name} mass balance",
            )
            check(
                source["mine"][f"{name}_minimum_tons"] - 1e-6
                <= mine[f"ending_{name}_tons"]
                <= source["mine"][f"{name}_maximum_tons"] + 1e-6,
                f"{key}: {name} inventory bounds",
            )
        check(
            abs(
                mine["opening_product_inventory_lb"]
                + mine["production_u3o8_lb"]
                - mine["sales_u3o8_lb"]
                - mine["ending_product_inventory_lb"]
            )
            < 1e-6,
            f"{key}: product mass balance",
        )
        check(
            source["mine"]["minimum_product_inventory_lb"] - 1e-6
            <= mine["ending_product_inventory_lb"]
            <= source["mine"].get("maximum_product_inventory_lb", 250000) + 1e-6,
            f"{key}: product inventory bounds",
        )
        for segment, values in row["segments"].items():
            check(
                values["served_units"] + values["lost_units"] == values["demand_units"],
                f"{key}: {segment} demand balance",
            )
            check(
                values["served_units"] == values["owned_served_units"] + values["outsourced_units"],
                f"{key}: {segment} fulfillment balance",
            )
            check(
                min(
                    values[k]
                    for k in (
                        "served_units",
                        "lost_units",
                        "owned_served_units",
                        "outsourced_units",
                    )
                )
                >= 0,
                f"{key}: {segment} negative volume",
            )
        for commodity, count in row["interface"]["cars_by_commodity"].items():
            check(
                count
                == row["interface"]["aru_served_cars_by_commodity"][commodity]
                + row["interface"]["outside_cars_by_commodity"][commodity],
                f"{key}: {commodity} carrier balance",
            )
    return {
        "passed": True,
        "checks": checks,
        "scenario_months": len(rows),
        "scope": "Conditional physical case validation, not operating authorization",
    }


def write_manifest(
    output: Path, dependencies: list[Path], effective_inputs: dict, artifact_names: list[str]
) -> None:
    """Pin disk provenance separately from optional in-memory scenario overrides."""
    write_json(
        output / "manifest.json",
        {
            "available_at": "2026-09-06T00:00:00-07:00",
            "record_origin": "PUBLIC_SYNTHETIC_PLANNING_MODEL",
            "dependency_sha256": {
                str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(dependencies)
            },
            "effective_input_sha256": {
                name: hashlib.sha256(
                    json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                for name, value in effective_inputs.items()
            },
            "artifacts": {
                name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                for name in sorted(artifact_names)
            },
            "policy": (
                "Disk dependency hashes identify provenance; canonical effective-input hashes "
                "identify in-memory overrides. Only named outputs from this build are "
                "inventoried; stale unrelated files are excluded."
            ),
        },
    )


def build(output: Path = DEFAULT_OUT, source: dict | None = None) -> dict:
    source = source or load_source()
    rows = calculate(source)
    validation = validate(rows, source)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "operating_rows.json", rows)
    write_json(output / "validation.json", validation)
    flat = []
    for r in rows:
        flat.append(
            {
                "scenario": r["scenario"],
                "year": r["year"],
                "month": r["month"],
                "period_role": r["period_role"],
                **{f"{s.lower()}_served_units": r["segments"][s]["served_units"] for s in SEGMENTS},
                "ore_tons": r["mine"]["ore_tons"],
                "production_u3o8_lb": r["mine"]["production_u3o8_lb"],
                "sales_u3o8_lb": r["mine"]["sales_u3o8_lb"],
                "mine_lost_production_tons": r["mine"]["lost_production_tons"],
                "interface_cars": sum(r["interface"]["cars_by_commodity"].values()),
                "outside_inbound_cars": sum(r["interface"]["outside_cars_by_commodity"].values()),
                "aru_growth_usd": r["capital"]["aru_growth_usd"],
                "mine_growth_usd": r["capital"]["mine_growth_usd"],
                "aru_replacement_usd": r["capital"]["aru_replacement_usd"],
                "mine_replacement_usd": r["capital"]["mine_replacement_usd"],
                "events": r["events"],
                "constraints": r["constraints"],
            }
        )
    write_csv(output / "monthly_operating_summary.csv", flat)
    write_manifest(
        output,
        [
            BASE / "operating_model.py",
            BASE / "source/operating_plan.json",
            BASE / "source/capital_options.json",
            ROOT / "industrial/source/operations.json",
        ],
        {"operating_plan": source, "capital_options": load_capital()},
        ["operating_rows.json", "monthly_operating_summary.csv", "validation.json"],
    )
    return {"schema_version": "1.0", "operating_rows": rows, "summary": validation}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(build(args.out)["summary"], sort_keys=True))
