"""Source-based investment purposes and cash attribution; never a target-seeking forecast."""

import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

from industrial.planning.enterprise import load_anchor, read_csv, write_csv

ROOT = Path(__file__).resolve().parents[2]
Q = D(".0001")
CURRENT_TAX_PAYABLES = {
    "CO_FF_TAX_PAY",
    "CO_SOFTWARE_TAX_PAY",
    "CO_RWH_ROT_PAY",
    "CO_STATE_MIN_PAY",
    "CO_TAX_PAY_FED",
    "CO_TAX_PAY_CA",
    "CO_SUB_TAX_PAY_FED",
    "CO_SUB_TAX_PAY_STATE",
    "CO_SUB_TAX_PAY_CA",
    "CO_SUB_TAX_PAY_IL",
    "CO_SUB_TAX_PAY_WV",
    "CO_PAYROLL_EMP_TAX_PAY",
}


def tax_requirements(trial):
    """Current tax balances; no deferred tax, interentity netting or tax paid twice."""
    totals, rows, seen = defaultdict(D), [], set()
    for row in trial:
        if int(row["month"]) != 12 or row["account"] not in CURRENT_TAX_PAYABLES:
            continue
        if row["entity"] not in {"SHI", "SHIH", "PS", "RWH", "ARU", "BST"}:
            raise ValueError("Tax requirement must use legal-entity balances once")
        key = row["scenario"], row["entity"], int(row["year"]), row["account"]
        if key in seen or row["account_type"] != "liability":
            raise ValueError("Duplicate or misclassified current tax balance")
        seen.add(key)
        amount = max(-D(row["signed_usd"]), D(0))
        totals[row["scenario"], int(row["year"])] += amount
        rows.append(
            dict(
                row,
                booked_unpaid_tax_usd=str(amount),
                due_state="SEE_FILING_CALENDAR_NOT_ALL_CURRENTLY_PAST_DUE",
            )
        )
    return totals, rows


def attribute(operating, sustaining, financing_paid, reserve_change, growth, member, other_in):
    """Annual cash waterfall; unknown opening cash is not assumed self-generated."""
    # A released prior requirement is not new current-year internally generated cash.
    available = operating - sustaining - financing_paid - max(reserve_change, D(0))
    internal = min(max(available, D(0)), growth)
    externally_available = max(member + other_in - max(-available, D(0)), D(0))
    external = min(growth - internal, externally_available)
    opening = growth - internal - external
    if min(internal, external, opening) < 0 or internal + external + opening != growth:
        raise ValueError("Growth cash attribution failed")
    return available, internal, external, opening


def runtime_sustaining_share(source_id, case, year, data):
    from enterprise.runtime.planning import capacity

    assumptions = data["capital"]["implementation_assumptions"]
    refresh = assumptions["commercial"]["hardware_refresh_years"]
    if not source_id.startswith("RT-FORECAST-hardware_cash_request-"):
        return D(0)
    if year <= 2027 or (year - 2027) % refresh:
        return D(0)
    scenario = {"base": "base", "downside": "slower_adoption", "expansion": "high_demand"}[case]

    def equipment(y):
        return D(capacity(assumptions, y, scenario)["equipment_cost"]) + D(
            capacity(assumptions, y, scenario, True)["equipment_cost"]
        )

    current, prior = equipment(year), equipment(year - 1)
    return min(prior, current) / current if current else D(0)


def core_purpose(source_id, case, year, runtime):
    if source_id.startswith("RT-FORECAST-") and any(
        name in source_id for name in ("hardware_cash_request", "facility_cash_request")
    ):
        return runtime_sustaining_share(source_id, case, year, runtime)
    if "-ASSET_RECEIPT-" in source_id:
        return D(0)  # Existing new research capability equipment, not routine replacement.
    raise ValueError("Unclassified Core investment source: " + source_id)


def enrich(out, result):
    from enterprise.runtime import model

    runtime = model.load()
    journal = read_csv(out / "enterprise/enterprise_journal.csv")
    native = read_csv(out / "industrial/forecast/journal.csv")
    obligations = read_csv(out / "exports/tables/treasury_obligations.csv")
    history = read_csv(out / "exports/tables/treasury_obligation_history.csv")
    industrial_months = read_csv(out / "industrial/forecast/monthly_statements.csv")
    industrial_assets = read_csv(out / "industrial/forecast/assets.csv")
    annual = read_csv(out / "enterprise/enterprise_annual_statements.csv")
    tax_unpaid, tax_details = tax_requirements(
        read_csv(out / "enterprise/legal_monthly_trial_balances.csv")
    )
    write_csv(out / "sovereignty_tax_requirements.csv", tax_details)
    by_obligation = {r["obligation_id"]: r for r in obligations}
    if len(by_obligation) != len(obligations):
        raise ValueError("Duplicate treasury obligation")
    totals = defaultdict(lambda: defaultdict(D))
    details = []

    def investment(case, year, entity, source, value, share, origin):
        if not 0 <= share <= 1:
            raise ValueError("Invalid investment purpose share")
        sustain = (value * share).quantize(Q)
        growth = value - sustain
        totals[case, year]["sustaining"] += sustain
        totals[case, year]["growth"] += growth
        details.append(
            dict(
                scenario=case,
                year=year,
                entity=entity,
                source_id=source,
                net_paid_usd=str(value),
                sustaining_usd=str(sustain),
                growth_usd=str(growth),
                classification_basis=origin,
            )
        )

    source = json.loads((ROOT / "industrial/source/finance.json").read_bytes())
    f = source["forecast_2026"]
    mine = json.loads((ROOT / "red_wash/source/core_operating_data.json").read_bytes())[
        "finance_2026"
    ]
    anchor = load_anchor()
    for case in ("base", "downside", "expansion"):
        # The consolidated acquisition flow is net; disclose the source gross draw/uses.
        grossup = D(source["transaction"]["existing_term_revolver_refinance"]) + D(
            source["transaction"]["debt_issuance_cost"]
        )
        totals[case, 2026]["financing_paid"] += grossup
        totals[case, 2026]["other_external_in"] += grossup
        for r in anchor:
            if r["account"] != "1000" or int(r["month"]) == 0:
                continue
            value = -D(r["signed_usd"])
            if r["cash_flow"] == "INVESTING":
                sustain = (
                    D(f["sustaining_capex"] + f["catchup_capex"])
                    if r["entity"] == "ARU_GROUP"
                    else D(mine["sustaining_capex_usd"] + mine["rehabilitation_capex_usd"])
                )
                growth = D(
                    f["aru_interface_capex"]
                    if r["entity"] == "ARU_GROUP"
                    else f["mine_interface_capex"]
                )
                investment(
                    case,
                    2026,
                    r["entity"],
                    r["journal_id"],
                    value,
                    sustain / (sustain + growth),
                    "EXISTING_2026_PROGRAM_BUDGET; catch-up/rehabilitation sustain existing "
                    "capability, interface adds capability",
                )
            elif r["cash_flow"] == "FINANCING" and value > 0:
                totals[case, 2026]["financing_paid"] += value
        acquired_cash = sum(
            D(r["signed_usd"])
            for r in anchor
            if r["entity"] == "ARU_GROUP" and r["account"] == "1000" and int(r["month"]) == 0
        )
        investment(
            case,
            2026,
            "ARU_GROUP",
            "PPA-2026-01-07-CASH",
            -acquired_cash,
            D(0),
            "ACQUIRED_CASH_OFFSET; not internally generated revenue",
        )
    for r in native:
        if r["account"] != "1000" or int(r["month"]) == 0:
            continue
        key = r["scenario"], int(r["year"])
        value = -D(r["signed_usd"])
        if r["cash_flow"] == "INVESTING":
            if r["source_type"] != "CAPITAL_PURCHASE":
                raise ValueError("Unreviewed industrial capital source")
            if r["source_id"].endswith("-replacement"):
                share = D(1)
            elif "construction" in r["description"].lower():
                share = D(0)
            else:
                raise ValueError("Unclassified industrial investment purpose")
            investment(*key, r["entity"], r["source_id"], value, share, r["description"])
        elif r["cash_flow"] == "FINANCING":
            if value > 0:
                totals[key]["financing_paid"] += value
            elif r["source_type"] == "CONDITIONAL_DEBT_DRAW":
                totals[key]["other_external_in"] -= value
    for r in journal:
        if r["account"] != "1000" or int(r["month"]) == 0:
            continue
        key = r["scenario"], int(r["year"])
        value = -D(r["signed_usd"])
        if key[1] == 2026:
            if r["cash_flow"] == "INVESTING" and r["source_type"] in (
                "EXTERNAL_ACQUISITION",
                "CASH_FLOW_RECLASSIFICATION",
            ):
                investment(
                    *key,
                    r["entity"],
                    r["source_id"],
                    value,
                    D(0),
                    "EXISTING_ACQUISITION_CASH_PRESENTATION",
                )
            elif (
                r["entity"] == "SHI"
                and r["cash_flow"] == "INVESTING"
                and r["source_type"] == "LEGACY_ADAPTER"
            ):
                investment(
                    *key,
                    "SHI",
                    r["source_id"],
                    value,
                    D(1),
                    "AUTHORED_PURPOSE: routine legacy equipment refresh within existing operations",
                )
            if r["cash_flow"] == "FINANCING" and (
                (r["entity"] == "SHI" and r["source_type"] == "LEGACY_ADAPTER")
                or r["source_type"] == "CASH_FLOW_RECLASSIFICATION"
            ):
                totals[key]["financing_paid" if value > 0 else "other_external_in"] += abs(value)
    peak_unpaid = defaultdict(D)
    monthly_unpaid = defaultdict(D)
    for r in history:
        o = by_obligation[r["obligation_id"]]
        case, year = r["scenario"], int(r["period"][:4])
        key = case, year
        paid = D(r["funded_in_period_usd"])
        unpaid = D(r["closing_unpaid_usd"])
        monthly_unpaid[case, r["period"]] += unpaid
        if r["cash_flow"] == "INVESTING" and paid:
            share = core_purpose(o["source_id"], case, int(o["year"]), runtime)
            investment(
                *key,
                "SHI",
                o["source_id"] + "@" + r["period"],
                paid,
                share,
                "EXISTING_TREASURY_FUNDED_HISTORY; runtime refresh sustains prior capacity, "
                "incremental capacity adds growth",
            )
        elif r["cash_flow"] == "FINANCING":
            totals[key]["financing_paid"] += paid
        if r["period"][5:7] == "12":
            totals[key]["core_unpaid"] += unpaid
            if r["cash_flow"] == "INVESTING":
                totals[key]["growth_or_sustaining_unpaid"] += unpaid
    for (case, period), value in monthly_unpaid.items():
        key = case, int(period[:4])
        peak_unpaid[key] = max(peak_unpaid[key], value)
    for r in industrial_months:
        if int(r["month"]) == 12:
            key = r["scenario"], int(r["year"])
            totals[key]["industrial_unpaid"] += D(r["unpaid_due_obligations_usd"])
            totals[key]["deferred_capex"] += D(r["deferred_capex_usd"])
    projects = {}
    for r in industrial_assets:
        if int(r["month"]) == 12 and r["project_id"]:
            key = r["scenario"], int(r["year"]), r["project_id"]
            values = D(r["project_budget_usd"]), D(r["project_paid_to_date_usd"])
            if key in projects and projects[key] != values:
                raise ValueError("Inconsistent repeated project budget")
            projects[key] = values
    for (case, year, _), (budget, paid) in projects.items():
        totals[case, year]["planned_project_balance"] += max(budget - paid, D(0))
    land = defaultdict(D)
    for r in journal:
        if (
            r["entity"] == "SHI"
            and r["account"] == "RT_SETTLEMENT_UNRESOLVED"
            and int(r["month"]) > 0
        ):
            land[r["scenario"], int(r["year"])] -= D(r["signed_usd"])
    cumulative_land = defaultdict(D)
    previous_reserve = defaultdict(D)
    previous_operating = {}
    annual_lookup = {
        (r["scenario"], int(r["year"])): r for r in annual if r["entity"] == "CONSOLIDATED"
    }
    for row in result:
        key = row["scenario"], int(row["year"])
        t = totals[key]
        investing = -D(annual_lookup[key]["investing_cash_flow_usd"])
        if abs(t["sustaining"] + t["growth"] - investing) > D(".01"):
            raise ValueError(
                f"Investment purpose population does not reconcile: {key}: "
                f"{t['sustaining'] + t['growth']} vs {investing}"
            )
        cumulative_land[key[0]] += land[key]
        legacy_requirements = t["core_unpaid"] + t["industrial_unpaid"] + cumulative_land[key[0]]
        reserve = legacy_requirements + tax_unpaid[key]
        reserve_change = reserve - previous_reserve[key[0]]
        previous_reserve[key[0]] = reserve
        operating, member = D(row["operating_cash_generation_usd"]), D(row["member_cash_usd"])
        available, internal, external, opening = attribute(
            operating,
            t["sustaining"],
            t["financing_paid"],
            reserve_change,
            t["growth"],
            member,
            t["other_external_in"],
        )
        values = dict(
            sustaining_investment_paid_usd=t["sustaining"],
            growth_net_investment_paid_usd=t["growth"],
            required_financing_cash_paid_usd=t["financing_paid"],
            other_external_financing_in_usd=t["other_external_in"],
            outstanding_due_or_unresolved_settlement_usd=legacy_requirements,
            booked_current_tax_payables_usd=tax_unpaid[key],
            outstanding_booked_cash_requirements_usd=reserve,
            unpaid_requirement_change_usd=reserve_change,
            released_prior_requirement_origin_unattributed_usd=max(-reserve_change, D(0)),
            consolidated_cash_coverage_before_other_needs_usd=min(
                max(D(row["ending_cash_usd"]), D(0)), reserve
            ),
            requirement_excess_over_consolidated_cash_usd=max(
                reserve - max(D(row["ending_cash_usd"]), D(0)), D(0)
            ),
            internally_available_before_growth_usd=available,
            growth_internal_current_year_usd=internal,
            growth_external_current_year_usd=external,
            growth_cash_origin_unattributed_usd=opening,
            investing_obligations_unpaid_usd=t["growth_or_sustaining_unpaid"],
            industrial_due_obligations_unpaid_usd=t["industrial_unpaid"],
            peak_core_unpaid_within_year_usd=peak_unpaid[key],
            planned_industrial_project_balance_usd=t["planned_project_balance"],
            deferred_industrial_capex_usd=t["deferred_capex"],
        )
        row.update({k: str(v) for k, v in values.items()})
        current_statement = annual_lookup[key]
        prior_statement = annual_lookup.get((key[0], key[1] - 1))
        revenue = D(current_statement["revenue_usd"])
        income = D(current_statement["net_income_usd"])
        row["net_margin"] = str(income / revenue) if revenue else "N/A"
        row["operating_cash_less_net_income_usd"] = str(operating - income)
        row["cash_requirement_coverage_scope"] = (
            "Aggregate mathematical coverage before other needs/floors; not segregated cash "
            "or legal permission to transfer funds. Negative coverage remains unfunded."
        )
        row["growth_vs_sustaining_split"] = "SOURCE_CLASSIFIED_SEE_INVESTMENT_PURPOSE_ROWS"
        row["binding_growth_commitment_state"] = (
            "No binding commitment inferred from scenario budget or capital request; "
            "booked unpaid and planned amounts above remain distinct"
        )
        row["ownership_control_state"] = (
            "No issuance/dilution/forfeiture generated; exact holder allocation follows "
            "accepted capital register, unresolved holders remain explicit"
        )
        prior = previous_operating.get(key[0])
        row["progress_explanation"] = (
            (
                "Initial calibration: "
                if prior is None
                else f"Operating cash changed by {operating - prior}; "
            )
            + f"member cash {member}; sustaining {t['sustaining']}; growth {t['growth']}; "
            f"debt/financing payments {t['financing_paid']}; "
            f"unpaid/reserve change {reserve_change}. These explain dependence; zero annual "
            "member cash is not proof of all-growth self-funding or resilience."
        )
        if prior_statement:
            revenue_delta = revenue - D(prior_statement["revenue_usd"])
            expense_delta = D(current_statement["expense_usd"]) - D(prior_statement["expense_usd"])
            row["progress_explanation"] += (
                f" Revenue changed by {revenue_delta}; total expense including the tax provision "
                f"changed by {expense_delta}. Net margin is {row['net_margin']}; "
                f"operating cash less net income is {operating - income}, combining noncash "
                "items and working-capital timing. Tax and asset workpapers explain their "
                "individual movements; deferred investment and unpaid bills remain above."
            )
        row["unattributed_cash_scope"] = (
            "May include opening cash or unpaid-obligation timing; origin is not assigned "
            "to internal generation or external financing without support. No balancing receipt."
        )
        previous_operating[key[0]] = operating
    write_csv(out / "sovereignty_investment_purposes.csv", details)
    liquidity = read_csv(out / "enterprise/enterprise_monthly_statements.csv")
    write_csv(
        out / "sovereignty_entity_liquidity.csv",
        [
            {
                k: r[k]
                for k in (
                    "scenario",
                    "entity",
                    "year",
                    "month",
                    "ending_cash_usd",
                    "operating_cash_flow_usd",
                    "investing_cash_flow_usd",
                    "financing_cash_flow_usd",
                    "fact_state",
                    "available_at",
                )
            }
            | {"scope": "Existing legal/consolidated cash; no new reserve or transfer permission"}
            for r in liquidity
            if r["entity"] != "ELIM"
        ],
    )
    return result
