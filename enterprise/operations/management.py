"""Reconciled nonposting consumption allocations and rebuilt forecast vintages."""

from __future__ import annotations

import copy
from collections import defaultdict
from decimal import Decimal as D

from enterprise.business.model import UNITS, amount, fingerprint, money, period

POOLS = ("technology", "finance", "people", "assurance")
METRICS = ("revenue_usd", "net_income_usd", "requested_cash_flow_usd")


def _allocate(value, weights):
    """Round each share once and give the final recipient the exact residual."""
    total = sum(weights.values(), D(0))
    if total <= 0 or any(v < 0 for v in weights.values()):
        raise ValueError("Service consumption must have a positive nonnegative population")
    remaining = value
    rows = list(weights.items())
    result = {}
    for index, (key, weight) in enumerate(rows):
        share = remaining if index == len(rows) - 1 else amount(value * weight / total)
        result[key] = share
        remaining -= share
    return result


def _services(model, result):
    config = model.operations_inputs["management"]
    if set(config["usage"]) != set(POOLS):
        raise ValueError("Expected four explicit service consumption pools")
    groups = defaultdict(lambda: defaultdict(D))
    demand = defaultdict(lambda: defaultdict(lambda: defaultdict(D)))
    for row in model.tables["workforce_assignments"]:
        key = row["scenario"], row["period"]
        groups[key][row["home_group"]] += D(row["loaded_cost_usd"])
        demand[key]["people"][row["unit"]] += D(row["assignment_fte"])
    support, fees = defaultdict(D), defaultdict(lambda: defaultdict(D))
    fee_revenue = defaultdict(D)
    for row in model.tables["journal"]:
        if row["unit"] == "corporate" and row["account"] == "BIZ_SUPPORT":
            support[row["scenario"], row["period"]] += D(row["signed_usd"])
    for row in result["journal_rows"]:
        if int(row["year"]) < 2027 or row["entity"] == "ELIM":
            continue
        key = (
            row["scenario"],
            period((int(row["year"]) - 2027) * 12 + int(row["month"]))[2],
        )
        if row["account"] == "SHARED_REV" and row["entity"] == "SHI":
            fee_revenue[key] -= D(row["signed_usd"])
        if row["account"] != "SHARED_EXP":
            continue
        unit = {"ARU": "american-resource-utility", "PS": "pale-sun"}.get(row["entity"])
        if unit is None:
            raise ValueError("Unknown statutory service-fee recipient")
        fees[key][unit] += D(row["signed_usd"])
    for row in model.tables["events"]:
        key = row["scenario"], row["period"]
        if row["kind"] in {
            "INVOICE",
            "COST",
            "COLLECTION",
            "CREDIT_RECOVERY",
            "PAYMENT_REQUEST",
        }:
            demand[key]["finance"][row["unit"]] += 1
        if row["kind"] in {
            "DEPLOYMENT_ACCEPTANCE",
            "SUBSCRIPTION_SERVICE",
            "SERVICE_INCIDENT",
        }:
            demand[key]["technology"][row["unit"]] += 1
        if row["kind"] in {
            "MATTER_ACCEPTANCE",
            "MATTER_DETERMINATION",
            "FOLLOW_ON_GATE",
            "OUTCOME_ACCEPTED",
            "RECOVERY_RUN",
        }:
            demand[key]["assurance"][row["unit"]] += 1
    corporate = {
        (r["scenario"], period((int(r["year"]) - 2027) * 12 + int(r["month"]))[2]): r
        for r in result["unit_monthly_rows"]
        if r["unit"] == "corporate" and int(r["year"]) >= 2027
    }
    for key, row in sorted(corporate.items()):
        ess, ia = groups[key]["ess"], groups[key]["internal-audit"]
        tech, finance = amount(ess * D("0.4")), amount(ess * D("0.3"))
        gross = {
            "technology": tech + support[key],
            "finance": finance,
            "people": ess - tech - finance,
            "assurance": ia,
        }
        gross_total = sum(gross.values(), D(0))
        fee_total = sum(fees[key].values(), D(0))
        if fee_total != fee_revenue[key]:
            raise ValueError("Statutory service-fee expense and revenue are not reciprocal")
        fee_split = {unit: _allocate(value, gross) for unit, value in fees[key].items()}
        allocated_total = D(0)
        for pool in POOLS:
            weights = {
                u: D(str(v)) + demand[key][pool][u] for u, v in config["usage"][pool].items()
            }
            if set(weights) != (set(UNITS) | {"pale-sun", "american-resource-utility"}):
                raise ValueError("Service demand must explicitly cover seven units plus corporate")
            shares = _allocate(gross[pool], weights)
            pool_credit = sum((r[pool] for r in fee_split.values()), D(0))
            model.tables["service_cost_pools"].append(
                {
                    "scenario": key[0],
                    "period": key[1],
                    "unit": "corporate",
                    "pool_id": pool,
                    "gross_pool_usd": money(gross[pool]),
                    "statutory_fee_credit_usd": money(pool_credit),
                    "residual_pool_usd": money(gross[pool] - pool_credit),
                    "posting_state": "NONPOSTING_MANAGEMENT_VIEW",
                    "source_basis": config["cost_pool_basis"],
                }
            )
            for unit, share in shares.items():
                credit = fee_split.get(unit, {}).get(pool, D(0))
                net = share - credit
                allocated_total += net
                model.tables["service_consumption_allocations"].append(
                    {
                        "scenario": key[0],
                        "period": key[1],
                        "unit": unit,
                        "pool_id": pool,
                        "consumption_units": money(weights[unit]),
                        "planned_consumption_units": money(config["usage"][pool][unit]),
                        "generated_consumption_units": money(demand[key][pool][unit]),
                        "gross_allocation_usd": money(share),
                        "statutory_fee_credit_usd": money(credit),
                        "allocation_usd": money(net),
                        "basis": "DECLARED_SERVICE_UNITS_PLUS_GENERATED_ACTIVITY",
                        "posting_state": "NONPOSTING; EXISTING_STATUTORY_FEES_CREDITED_ONCE",
                    }
                )
        expense, revenue = D(row["expense_usd"]), D(row["revenue_usd"])
        retained = expense - gross_total - revenue + fee_total
        net_cost = expense - revenue
        model.tables["management_cost_reconciliation"].append(
            {
                "scenario": key[0],
                "period": key[1],
                "unit": "corporate",
                "corporate_expense_usd": money(expense),
                "corporate_revenue_usd": money(revenue),
                "statutory_fee_revenue_usd": money(fee_total),
                "gross_service_pool_usd": money(gross_total),
                "statutory_fee_credit_usd": money(fee_total),
                "residual_service_allocation_usd": money(allocated_total),
                "retained_j2_mission_usd": money(groups[key]["j2"]),
                "retained_other_corporate_usd": money(retained - groups[key]["j2"]),
                "retained_corporate_cost_usd": money(retained),
                "corporate_net_cost_usd": money(net_cost),
                "difference_usd": money(net_cost - allocated_total - retained),
            }
        )


def _metrics(model):
    output = defaultdict(lambda: defaultdict(D))
    for row in model.tables["journal"]:
        key = row["scenario"], row["period"], row["unit"]
        value = D(row["signed_usd"])
        if row["account_type"] == "revenue":
            output[key]["revenue_usd"] -= value
            output[key]["net_income_usd"] -= value
        elif row["account_type"] == "expense":
            output[key]["net_income_usd"] -= value
        if row["account"] == "1000":
            output[key]["requested_cash_flow_usd"] += value
    return {
        key: {metric: amount(values[metric]) for metric in METRICS}
        for key, values in output.items()
    }


def _forecast(model, model_factory):
    config = model.operations_inputs["management"]["forecast"]
    freeze = config["frozen_through_month"]
    if freeze != 6:
        raise ValueError("This revision exercise explicitly freezes January–June 2027")
    business, operations = (
        copy.deepcopy(model.inputs),
        copy.deepcopy(model.operations_inputs),
    )
    snapshots = [_metrics(model)]
    hashes = [fingerprint({"business": business, "operations": operations})]
    for driver in ("price", "volume", "timing", "workforce"):
        if driver == "price":
            for contract in business["contracts"]:
                if contract["start_month"] > freeze:
                    for field in ("monthly_subscription_usd", "deployment_fee_usd"):
                        contract[field] = float(
                            amount(D(str(contract[field])) * D(config["price_factor"]))
                        )
        elif driver == "volume":
            for engagement in business["engagements"]:
                if engagement["start_month"] > freeze:
                    for field in ("fee_usd", "delivery_hours"):
                        engagement[field] = float(
                            amount(D(str(engagement[field])) * D(config["volume_factor"]))
                        )
        elif driver == "timing":
            delay = config["timing_delay_months"]
            if type(delay) is not int or delay < 0:
                raise ValueError("Forecast delay must be a nonnegative month count")
            for contract in business["contracts"]:
                if contract["start_month"] > freeze:
                    contract["start_month"] += delay
        else:
            change = copy.deepcopy(config["workforce_change"])
            if change["month"] <= freeze:
                raise ValueError("Forecast staffing change crosses the frozen period")
            operations["workforce"]["events"].append(change)
        rebuilt = model_factory(inputs=business, operations_inputs=operations).build()
        values = _metrics(rebuilt)
        if set(values) != set(snapshots[0]):
            raise ValueError("Forecast revision changed metric population identities")
        if any(values[key] != snapshots[0][key] for key in values if key[1] <= period(freeze)[2]):
            raise ValueError("Forecast revision rewrote the frozen first six months")
        snapshots.append(values)
        hashes.append(fingerprint({"business": business, "operations": operations}))
    for vintage, index, role in (
        ("budget", 0, "SELECTED_OPERATING_INPUTS"),
        ("revised", 2, "PRICE_AND_SERVICE_VOLUME_ALTERNATIVE"),
        ("synthetic_outturn", 4, "TIMING_AND_WORKFORCE_ALTERNATIVE_NOT_ACTUAL"),
    ):
        model.tables["forecast_vintage_register"].append(
            {
                "vintage_id": vintage,
                "input_sha256": hashes[index],
                "role": role,
                "frozen_through_period": period(freeze)[2],
                "rebuild_state": "MODEL_EXECUTED",
                "cash_basis": "CORE_REQUESTED_CASH_BEFORE_ENTERPRISE_TREASURY",
                "attribution_order": "price,volume,timing,workforce",
            }
        )
        for (scenario, date, unit), values in sorted(snapshots[index].items()):
            for metric in METRICS:
                model.tables["forecast_vintage_metrics"].append(
                    {
                        "scenario": scenario,
                        "period": date,
                        "unit": unit,
                        "vintage_id": vintage,
                        "metric": metric,
                        "amount_usd": money(values[metric]),
                    }
                )
    for vintage, prior, revised in (("revised", 0, 2), ("synthetic_outturn", 2, 4)):
        for (scenario, date, unit), values in sorted(snapshots[prior].items()):
            key = scenario, date, unit
            for metric in METRICS:
                contributions = {}
                for index, driver in enumerate(("price", "volume", "timing", "workforce"), 1):
                    contributions[f"{driver}_contribution_usd"] = money(
                        snapshots[index][key][metric] - snapshots[index - 1][key][metric]
                        if prior < index <= revised
                        else D(0)
                    )
                end = snapshots[revised][key][metric]
                model.tables["forecast_variance_contributions"].append(
                    {
                        "scenario": scenario,
                        "period": date,
                        "unit": unit,
                        "vintage_id": vintage,
                        "metric": metric,
                        "prior_usd": money(values[metric]),
                        "revised_usd": money(end),
                        **contributions,
                        "difference_usd": money(
                            end - values[metric] - sum(D(v) for v in contributions.values())
                        ),
                    }
                )


def build(model, result, model_factory):
    names = (
        "service_cost_pools",
        "service_consumption_allocations",
        "management_cost_reconciliation",
        "forecast_vintage_register",
        "forecast_vintage_metrics",
        "forecast_variance_contributions",
    )
    if any(model.tables[name] for name in names):
        raise ValueError("Management views may be built only once on an execution")
    _services(model, result)
    _forecast(model, model_factory)
    return validate(model)


def validate(model):
    pool_actual = defaultdict(D)
    monthly_alloc = defaultdict(D)
    for row in model.tables["service_consumption_allocations"]:
        key = row["scenario"], row["period"], row["pool_id"]
        if D(row["consumption_units"]) != D(row["planned_consumption_units"]) + D(
            row["generated_consumption_units"]
        ):
            raise ValueError(
                "Service consumption does not equal its declared and generated components"
            )
        if D(row["allocation_usd"]) != D(row["gross_allocation_usd"]) - D(
            row["statutory_fee_credit_usd"]
        ):
            raise ValueError("Service allocation failed the statutory fee credit bridge")
        pool_actual[key] += D(row["allocation_usd"])
        monthly_alloc[key[:2]] += D(row["allocation_usd"])
    for row in model.tables["service_cost_pools"]:
        key = row["scenario"], row["period"], row["pool_id"]
        residual = D(row["gross_pool_usd"]) - D(row["statutory_fee_credit_usd"])
        if residual != D(row["residual_pool_usd"]) or pool_actual[key] != residual:
            raise ValueError("Service consumption allocations do not equal the residual cost pool")
    for row in model.tables["management_cost_reconciliation"]:
        expense, revenue = (
            D(row["corporate_expense_usd"]),
            D(row["corporate_revenue_usd"]),
        )
        allocated = monthly_alloc[row["scenario"], row["period"]]
        retained = D(row["retained_corporate_cost_usd"])
        if expense - revenue != allocated + retained or D(row["difference_usd"]):
            raise ValueError("Corporate cost does not reconcile to allocation plus retained cost")
        if retained != D(row["retained_j2_mission_usd"]) + D(row["retained_other_corporate_usd"]):
            raise ValueError("Retained J2 mission costs do not reconcile")
    lookup = {
        (r["scenario"], r["period"], r["unit"], r["vintage_id"], r["metric"]): D(r["amount_usd"])
        for r in model.tables["forecast_vintage_metrics"]
    }
    if len(lookup) != len(model.tables["forecast_vintage_metrics"]):
        raise ValueError("Duplicate forecast metric identity")
    for row in model.tables["forecast_variance_contributions"]:
        key = row["scenario"], row["period"], row["unit"]
        prior = "budget" if row["vintage_id"] == "revised" else "revised"
        if D(row["prior_usd"]) != lookup[(*key, prior, row["metric"])]:
            raise ValueError("Forecast prior value differs from rebuilt vintage")
        if D(row["revised_usd"]) != lookup[(*key, row["vintage_id"], row["metric"])]:
            raise ValueError("Forecast revised value differs from rebuilt vintage")
        delta = D(row["revised_usd"]) - D(row["prior_usd"])
        total = sum(
            D(row[f"{driver}_contribution_usd"])
            for driver in ("price", "volume", "timing", "workforce")
        )
        if delta != total or D(row["difference_usd"]):
            raise ValueError("Forecast driver attribution fails exact reconciliation")
        if row["period"] <= period(6)[2] and (delta or total):
            raise ValueError("Forecast changed a frozen period")
    return {
        "cost_pools": len(model.tables["service_cost_pools"]),
        "service_allocations": len(model.tables["service_consumption_allocations"]),
        "forecast_vintages": len(model.tables["forecast_vintage_register"]),
        "forecast_variances": len(model.tables["forecast_variance_contributions"]),
    }
