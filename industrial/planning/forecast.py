"""Conditional monthly industrial forecast; accepted 2026 bytes remain untouched.

This module consumes physical operating rows and item-level procurement, then
posts double-entry journals. Finite conditional capital limits can leave unpaid
obligations and deferred capital; they never manufacture operating income.
"""

from __future__ import annotations

import argparse
import calendar
import copy
import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from industrial.tools.build_financials import ACCOUNTS as ACCEPTED_ACCOUNTS
from industrial.tools.build_financials import customer_schedules, payroll_schedules

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "industrial/planning/source/forecast.json"
OUT = ROOT / "industrial/generated/planning/forecast"
OLD_SOURCE = ROOT / "industrial/source/finance.json"
OLD_OPERATIONS = ROOT / "industrial/source/operations.json"
D = Decimal
ACCOUNTS = dict(ACCEPTED_ACCOUNTS)
ACCOUNTS.update(
    {
        "1410": ("Construction in progress, conditional projects", "asset"),
        "1701": ("Refinancing issuance cost, contra new term debt", "liability"),
        "2410": ("Conditional replacement term debt", "liability"),
        "2720": ("Accrued interest and financing services payable", "liability"),
    }
)


def money(value):
    return int(D(str(value)).quantize(D(1), rounding=ROUND_HALF_UP))


def split(total, weights):
    if total < 0:
        return [-v for v in split(-total, weights)]
    denominator = sum(D(str(w)) for w in weights)
    if denominator <= 0:
        raise ValueError("Allocation weights must have a positive sum")
    exact = [D(total) * D(str(w)) / denominator for w in weights]
    values = [int(v) for v in exact]
    for i in sorted(range(len(weights)), key=lambda j: (-(exact[j] - values[j]), j))[
        : total - sum(values)
    ]:
        values[i] += 1
    return values


def metadata(source):
    return {
        "available_at": source["available_at"],
        "record_origin": source["record_origin"],
        "fact_state": "CONDITIONAL_FORECAST",
        "period_role": "CONDITIONAL_FORECAST",
    }


def source_data(source=None):
    result = json.loads(SOURCE.read_text()) if source is None else copy.deepcopy(source)
    if result["forecast_years"] != list(range(2027, 2032)):
        raise ValueError("This release is scoped to all sixty months of 2027–2031")
    if set(result["scenarios"]) != {"base", "downside", "expansion"}:
        raise ValueError("All three named scenarios are required")
    for balances in result["anchor"]["opening_balances"].values():
        if sum(balances.values()):
            raise ValueError("Accepted opening balances must balance")
    for key in ["external_collection_profile", "opening_ar_collection_profile"]:
        profile = result["working_capital"][key]
        if sum(D(str(r["fraction"])) for r in profile) != 1 or any(
            r["lag_months"] < 0 for r in profile
        ):
            raise ValueError("Collection profiles must preserve every invoice dollar")
    for entity in ["ARU_GROUP", "RWH_PS"]:
        tax = result["tax"][entity]
        if not 0 <= tax["nol_utilization_limit_pct"] <= 100 or not 0 < tax["rate_pct"] < 100:
            raise ValueError("Invalid tax scenario inputs")
        if tax["recognize_new_nol_dta"]:
            raise ValueError("Recognizing new loss DTAs requires a separate realization assessment")
    for row in result["opening_assets"]:
        if not 0 <= row["accum_usd"] <= row["gross_usd"]:
            raise ValueError("Invalid opening asset carrying amount")
    return result


class Book:
    def __init__(self, scenario, entity, year, opening, source):
        self.scenario, self.entity, self.year = scenario, entity, year
        self.source = source
        self.rows = []
        self.balance = defaultdict(int)
        self.sequence = 0
        self.entry(
            0,
            list(opening.items()),
            "OPENING",
            "OPENING_BALANCE",
            "Carried closing balance; prior income closed to retained earnings",
        )

    def entry(
        self,
        month,
        lines,
        source_id,
        source_type,
        description,
        segment="ARU",
        counterparty="",
        cash_flow="NONCASH_OR_OPENING",
    ):
        if sum(value for _, value in lines):
            raise ValueError(f"Unbalanced journal: {source_id}")
        self.sequence += 1
        ident = f"{self.scenario}-{self.entity}-{self.year}-{self.sequence:06}"
        for account, value in lines:
            if not value:
                continue
            self.balance[account] += value
            self.rows.append(
                {
                    "scenario": self.scenario,
                    "entity": self.entity,
                    "year": self.year,
                    "month": month,
                    "period": f"{self.year}-{max(month, 1):02}",
                    "journal_id": ident,
                    "account": account,
                    "account_name": ACCOUNTS[account][0],
                    "account_type": ACCOUNTS[account][1],
                    "debit_usd": max(value, 0),
                    "credit_usd": max(-value, 0),
                    "signed_usd": value,
                    "source_id": source_id,
                    "source_type": source_type,
                    "description": description,
                    "segment": segment,
                    "counterparty": counterparty,
                    "cash_flow": cash_flow,
                    **metadata(self.source),
                }
            )

    def pair(self, month, debit, credit, amount, source_id, source_type, description, **kwargs):
        self.entry(
            month,
            [(debit, amount), (credit, -amount)],
            source_id,
            source_type,
            description,
            **kwargs,
        )

    def cash(self, month, account, amount, source_id, source_type, description, **kwargs):
        kwargs.setdefault("cash_flow", "OPERATING")
        self.pair(month, account, "1000", amount, source_id, source_type, description, **kwargs)

    def income(self, month=None, pretax=False):
        return -sum(
            r["signed_usd"]
            for r in self.rows
            if r["account_type"] in ["revenue", "expense"]
            and (month is None or r["month"] == month)
            and (not pretax or r["account"] not in ["5500", "5501"])
        )

    def summary(self, month):
        totals = defaultdict(int)
        for a, value in self.balance.items():
            kind = ACCOUNTS[a][1]
            if kind in ["intercompany", "current_settlement"]:
                kind = "asset" if value >= 0 else "liability"
            totals[kind] += value
        assets, liabilities = totals["asset"], -totals["liability"]
        income = -totals["revenue"] - totals["expense"]
        equity = -totals["equity"] + income
        if assets != liabilities + equity or sum(self.balance.values()):
            raise ValueError("Balance-sheet identity failed")
        cf, period_cf = defaultdict(int), defaultdict(int)
        for row in self.rows:
            if row["account"] == "1000":
                cf[row["cash_flow"]] += row["signed_usd"]
                if row["month"] == month:
                    period_cf[row["cash_flow"]] += row["signed_usd"]
        if sum(cf.values()) != self.balance["1000"]:
            raise ValueError("Cash rollforward failed")
        return {
            "scenario": self.scenario,
            "entity": self.entity,
            "year": self.year,
            "month": month,
            "period": f"{self.year}-{month:02}",
            "assets_usd": assets,
            "liabilities_usd": liabilities,
            "equity_including_current_income_usd": equity,
            "net_income_ytd_usd": income,
            "net_income_usd": self.income(month),
            "pretax_income_usd": self.income(month, pretax=True),
            "revenue_usd": -sum(
                r["signed_usd"]
                for r in self.rows
                if r["month"] == month and r["account_type"] == "revenue"
            ),
            "opening_year_cash_usd": cf["NONCASH_OR_OPENING"],
            "ending_cash_usd": self.balance["1000"],
            "operating_cash_flow_usd": period_cf["OPERATING"],
            "investing_cash_flow_usd": period_cf["INVESTING"],
            "financing_cash_flow_usd": period_cf["FINANCING"],
            "operating_cash_flow_ytd_usd": cf["OPERATING"],
            "investing_cash_flow_ytd_usd": cf["INVESTING"],
            "financing_cash_flow_ytd_usd": cf["FINANCING"],
            "balance_sheet_difference_usd": assets - liabilities - equity,
            **metadata(self.source),
        }

    def trial_balance(self, month):
        return [
            {
                "scenario": self.scenario,
                "entity": self.entity,
                "year": self.year,
                "month": month,
                "account": a,
                "account_name": ACCOUNTS[a][0],
                "account_type": ACCOUNTS[a][1],
                "signed_usd": v,
                "debit_usd": max(v, 0),
                "credit_usd": max(-v, 0),
                **metadata(self.source),
            }
            for a, v in sorted(self.balance.items())
        ]

    def carry(self):
        result = {
            a: v for a, v in self.balance.items() if ACCOUNTS[a][1] not in ["revenue", "expense"]
        }
        result["3100"] = result.get("3100", 0) - self.income()
        if sum(result.values()):
            raise ValueError("Year-end income closing failed")
        return result


def add_due(
    state,
    due,
    account,
    amount,
    source_id,
    source_type,
    segment="ARU",
    counterparty="",
    priority=5,
    cash_flow="OPERATING",
):
    if amount > 0:
        state["obligations"].append(
            {
                "due": due,
                "account": account,
                "amount": amount,
                "source_id": source_id,
                "source_type": source_type,
                "segment": segment,
                "counterparty": counterparty,
                "priority": priority,
                "cash_flow": cash_flow,
            }
        )


def expense(
    book,
    state,
    month,
    index,
    amount,
    account,
    source_id,
    source_type,
    due=None,
    segment="ARU",
    counterparty="",
    payable="2000",
    priority=5,
):
    book.pair(
        month,
        account,
        payable,
        amount,
        source_id,
        source_type,
        "Forecast expense supported by declared operating driver",
        segment=segment,
        counterparty=counterparty,
    )
    add_due(
        state,
        index if due is None else due,
        payable,
        amount,
        source_id,
        source_type,
        segment,
        counterparty,
        priority,
    )


def invoice(
    book, state, month, index, amount, source_id, source_type, segment, counterparty, source
):
    book.pair(
        month,
        "1100",
        "4000",
        amount,
        source_id,
        source_type,
        "Physical fulfilled units and declared contract price",
        segment=segment,
        counterparty=counterparty,
    )
    profile = source["working_capital"]["external_collection_profile"]
    for rule, value in zip(profile, split(amount, [r["fraction"] for r in profile]), strict=True):
        state["collections"].append(
            {
                "due": index + rule["lag_months"],
                "amount": value,
                "source_id": source_id,
                "counterparty": counterparty,
                "segment": segment,
            }
        )


def collect(book, state, month, index):
    remaining = []
    for row in state["collections"]:
        if row["due"] <= index:
            book.cash(
                month,
                "1100",
                -row["amount"],
                row["source_id"],
                "CUSTOMER_COLLECTION",
                "Scheduled modeled invoice receipt",
                counterparty=row["counterparty"],
                segment=row["segment"],
            )
        else:
            remaining.append(row)
    state["collections"] = remaining


def prepare_rows(operating_rows, source):
    if operating_rows is None:
        from industrial.planning.operating_model import calculate

        operating_rows = calculate()
    if isinstance(operating_rows, dict):
        operating_rows = operating_rows["operating_rows"]
    result = copy.deepcopy(operating_rows)
    required = {
        (s, y, m)
        for s in source["scenarios"]
        for y in source["forecast_years"]
        for m in range(1, 13)
    }
    keys = [(r["scenario"], int(r["year"]), int(r["month"])) for r in result]
    if len(keys) != len(set(keys)) or set(keys) != required:
        raise ValueError("Operating rows must contain exactly every scenario-year-month")
    for row in result:
        changes = source["adjustments"][row["scenario"]]
        for value in changes.values():
            if isinstance(value, (int, float)) and value < 0:
                raise ValueError("Negative forecast multiplier")
        row["assumptions"]["external_price_index"] = str(
            D(str(row["assumptions"]["external_price_index"]))
            * D(str(changes["revenue_price_multiplier"]))
        )
        row["assumptions"]["cash_cost_index"] = str(
            D(str(row["assumptions"]["cash_cost_index"])) * D(str(changes["cash_cost_multiplier"]))
        )
        row["mine"]["uranium_price_usd_lb"] = str(
            D(str(row["mine"]["uranium_price_usd_lb"]))
            * D(str(changes["revenue_price_multiplier"]))
        )
        row["mine"]["production_cash_cost_index"] = str(
            D(str(row["mine"]["production_cash_cost_index"]))
            * D(str(changes["cash_cost_multiplier"]))
        )
    return sorted(result, key=lambda r: (r["scenario"], r["year"], r["month"]))


def initial_state(entity, scenario, source):
    balances = source["anchor"]["opening_balances"][entity]
    state = {
        "obligations": [],
        "collections": [],
        "cards": [copy.deepcopy(c) for c in source["opening_assets"] if c["entity"] == entity],
        "nol": source["tax"][entity]["opening_nol_usd"],
        "equity_by_year": defaultdict(int),
        "goodwill_amortization": source["tax"]["opening_goodwill_amortization_usd"],
        "inventory_units": D(str(source["mine"]["opening_finished_inventory_lb"])),
        "refinancing_done": False,
        "refinance_original": 0,
        "refinance_fee_original": 0,
        "refinance_start": 0,
        "deferred_capital": [],
        "unfunded_growth_to_date": 0,
    }
    for card in state["cards"]:
        card["first_index"] = 0
    if (
        sum(c["gross_usd"] for c in state["cards"]) != balances["1400"]
        or sum(c["accum_usd"] for c in state["cards"]) != -balances["1490"]
    ):
        raise ValueError("Opening fixed-asset cards must equal accepted PPE control")
    profile = source["working_capital"]["opening_ar_collection_profile"]
    for rule, amount in zip(
        profile, split(balances["1100"], [r["fraction"] for r in profile]), strict=True
    ):
        state["collections"].append(
            {
                "due": 1 + rule["lag_months"],
                "amount": amount,
                "source_id": f"OPEN-AR-{scenario}-{entity}-{rule['lag_months']}",
                "counterparty": "OPENING_CUSTOMER_AGING",
                "segment": entity,
            }
        )
    add_due(
        state,
        source["working_capital"]["opening_payables_due_month"],
        "2000",
        -balances["2000"],
        "OPEN-AP",
        "OPENING_PAYABLE",
        priority=5,
    )
    if balances.get("2100"):
        add_due(
            state,
            source["working_capital"]["opening_operating_accruals_due_month"],
            "2100",
            -balances["2100"],
            "OPEN-ACCRUAL",
            "OPENING_ACCRUAL",
            priority=2,
        )
    if entity == "RWH_PS":
        ownership = source["working_capital"]["opening_ic_payable_by_seller_segment_usd"]
        if sum(ownership.values()) != -balances["2150"]:
            raise ValueError("Opening intercompany ownership must match the accepted payable")
        for segment, amount in ownership.items():
            add_due(
                state,
                1,
                "2150",
                amount,
                f"OPEN-IC-202612-{segment}",
                "INTERCOMPANY_PAYMENT",
                segment=segment,
                counterparty="ARU_GROUP",
                priority=3,
            )
    return state


def activate_projects(book, state, month, index):
    """Move fully funded projects from CIP at the conditional service gate."""
    for project_id, project in state.get("projects", {}).items():
        if project.get("actual_service_index") is not None:
            continue
        if project["paid_usd"] != project["budget_usd"] or index < project["service_index"]:
            continue
        project["actual_service_index"] = index
        book.pair(
            month,
            "1400",
            "1410",
            project["paid_usd"],
            project_id,
            "CONDITIONAL_CIP_COMMISSIONING",
            "Fully funded construction transferred at the conditional in-service gate",
        )
        for card in state["cards"]:
            if card.get("project_id") == project_id:
                card["first_index"] = index
                card["ledger_account"] = "1400"


def asset_row(book, card, month, charge=0, inventory_charge=0, additions=0):
    return {
        "scenario": book.scenario,
        "entity": book.entity,
        "year": book.year,
        "month": month,
        "asset_id": card["asset_id"],
        "project_id": card.get("project_id", ""),
        "ledger_account": card.get("ledger_account", "1400"),
        "asset_status": "CONSTRUCTION_IN_PROGRESS"
        if card.get("ledger_account") == "1410"
        else "CONDITIONAL_IN_SERVICE",
        "conditional_service_index": card.get("planned_service_index", 0),
        "actual_conditional_service_index": card["first_index"],
        "conditional_service_period": index_period(card.get("planned_service_index", 0)),
        "actual_conditional_service_period": index_period(card["first_index"]),
        "method": card["mode"],
        "gross_usd": card["gross_usd"],
        "opening_net_book_usd": card["gross_usd"] - card["accum_usd"] + charge - additions,
        "additions_usd": additions,
        "depreciation_usd": charge,
        "accumulated_depreciation_usd": card["accum_usd"],
        "closing_net_book_usd": card["gross_usd"] - card["accum_usd"],
        "capitalized_to_inventory_usd": inventory_charge,
        "expense_depreciation_usd": charge - inventory_charge,
    }


def index_period(index):
    if index is None:
        return ""
    if not index:
        return "ACCEPTED_2026_OPENING"
    return f"{2027 + (index - 1) // 12}-{(index - 1) % 12 + 1:02}"


def depreciate(book, state, month, index, production, source, output):
    activate_projects(book, state, month, index)
    capitalized = 0
    for card in state["cards"]:
        opening_net = card["gross_usd"] - card["accum_usd"]
        if card["mode"] == "UNITS_OF_PRODUCTION":
            charge = money(production * D(str(source["mine"]["legacy_production_dda_usd_lb"])))
        else:
            annual = money(card["annual_depreciation_usd"])
            charge = (
                split(annual, [1] * 12)[month - 1]
                if card["first_index"] is not None and index > card["first_index"]
                else 0
            )
        charge = min(opening_net, charge)
        is_production = card["mode"] in ["UNITS_OF_PRODUCTION", "PRODUCTION_STRAIGHT_LINE"]
        production_share = min(
            production / (D(source["mine"]["base_annual_production_lb"]) / 12), D(1)
        )
        inventory_charge = (
            money(D(charge) * production_share)
            if card["mode"] == "PRODUCTION_STRAIGHT_LINE"
            else charge
            if is_production
            else 0
        )
        book.entry(
            month,
            [("1210", inventory_charge), ("5300", charge - inventory_charge), ("1490", -charge)],
            card["asset_id"],
            "PRODUCTION_DEPRECIATION" if is_production else "FIXED_ASSET_DEPRECIATION",
            "Declared asset life/method; unallocated idle fixed depreciation remains expense",
        )
        card["accum_usd"] += charge
        capitalized += inventory_charge
        output.append(asset_row(book, card, month, charge, inventory_charge))
    if book.entity == "ARU_GROUP":
        charge = min(
            book.balance["1500"] + book.balance["1590"],
            split(source["debt"]["lease_annual_rou_depreciation_usd"], [1] * 12)[month - 1],
        )
        book.pair(
            month,
            "5300",
            "1590",
            charge,
            "OPEN-LEASE-ROU",
            "LEASE_DEPRECIATION",
            "Retained ROU amortization capped at remaining carrying amount",
        )
    return capitalized


def production_costs(physical, policy):
    """Abnormal idle fixed overhead is expense, never stock with no production."""
    activity = D(str(physical["ore_tons"])) / (D(policy["base_annual_ore_tons"]) / 12)
    cost_index = D(str(physical["production_cash_cost_index"])) / D(
        str(policy["production_cost_base_index"])
    )
    staff_ratio = (
        D(str(physical.get("site_fte", policy["baseline_site_fte"]))) / policy["baseline_site_fte"]
    )
    cost_index *= 1 + D(str(policy["site_staff_cost_exposure_share"])) * (staff_ratio - 1)
    fixed = (
        D(policy["base_annual_production_cash_usd"])
        / 12
        * D(str(policy["production_fixed_cost_share"]))
        * cost_index
    )
    variable = (
        D(policy["base_annual_production_cash_usd"])
        / 12
        * (1 - D(str(policy["production_fixed_cost_share"])))
        * activity
        * cost_index
    )
    total = money(fixed + variable)
    idle = money(fixed * (1 - min(activity, D(1))))
    return total, total - idle, idle


def post_debt(book, state, month, index, source, output):
    if book.entity != "ARU_GROUP":
        return
    policy = source["debt"]
    opening_term, opening_new, opening_lease = (
        -book.balance["2400"],
        -book.balance["2410"],
        -book.balance["2600"],
    )
    maturity = date.fromisoformat(policy["legacy_term_maturity"])
    matured = (book.year, month) >= (maturity.year, maturity.month)
    refinancing = policy["refinancing"][book.scenario]
    if matured and not state["refinancing_done"]:
        draw = min(opening_term, refinancing["available_principal_usd"])
        fee = money(D(draw) * D(str(refinancing["fee_pct"])) / 100)
        book.cash(
            month,
            "2410",
            -draw,
            "REPLACEMENT-TERM-DRAW",
            "CONDITIONAL_DEBT_DRAW",
            "Finite hypothetical refinancing, not a committed facility",
            cash_flow="FINANCING",
            counterparty="CONDITIONAL_REFINANCING_LENDER",
        )
        book.pair(
            month,
            "1701",
            "2720",
            fee,
            "REFINANCING-FEE",
            "DEBT_ISSUANCE_COST",
            "New financing cost recorded as contra debt",
        )
        add_due(
            state,
            index,
            "2720",
            fee,
            "REFINANCING-FEE",
            "DEBT_ISSUANCE_PAYMENT",
            priority=1,
            cash_flow="FINANCING",
        )
        state.update(
            refinancing_done=True,
            refinance_original=draw,
            refinance_fee_original=fee,
            refinance_start=index,
        )
    queued = sum(r["amount"] for r in state["obligations"] if r["account"] == "2400")
    principal = (
        max(opening_term - queued, 0)
        if matured
        else min(max(opening_term - queued, 0), policy["legacy_quarterly_principal_usd"])
        if month in policy["legacy_principal_months"]
        else 0
    )
    add_due(
        state,
        index,
        "2400",
        principal,
        f"LEGACY-TERM-{book.year}{month:02}",
        "TERM_PRINCIPAL",
        priority=1,
        cash_flow="FINANCING",
    )
    lease_queued = sum(r["amount"] for r in state["obligations"] if r["account"] == "2600")
    lease = min(
        max(opening_lease - lease_queued, 0),
        split(policy["lease_annual_principal_usd"], [1] * 12)[month - 1],
    )
    add_due(
        state,
        index,
        "2600",
        lease,
        f"LEASE-{book.year}{month:02}",
        "LEASE_PRINCIPAL",
        priority=1,
        cash_flow="FINANCING",
    )
    if state["refinance_original"] and index > state["refinance_start"]:
        amount = money(
            D(state["refinance_original"])
            * D(str(policy["new_term_annual_principal_pct"]))
            / 100
            / 12
        )
        queued_new = sum(r["amount"] for r in state["obligations"] if r["account"] == "2410")
        add_due(
            state,
            index,
            "2410",
            min(max(-book.balance["2410"] - queued_new, 0), amount),
            f"NEW-TERM-{book.year}{month:02}",
            "REFINANCE_PRINCIPAL",
            priority=1,
            cash_flow="FINANCING",
        )
    days = calendar.monthrange(book.year, month)[1]
    interest = money(
        (
            D(opening_term) * D(str(policy["legacy_term_rate_pct"]))
            + D(opening_new) * D(str(refinancing["rate_pct"]))
            + D(opening_lease) * D(str(policy["lease_rate_pct"]))
            + D(policy["revolver_capacity_usd"]) * D(str(policy["revolver_fee_pct"]))
        )
        / 100
        * days
        / 365
    )
    expense(
        book,
        state,
        month,
        index,
        interest,
        "5400",
        f"INTEREST-{book.year}{month:02}",
        "DEBT_INTEREST",
        payable="2720",
        priority=1,
    )
    amort = (
        book.balance["1700"]
        if matured
        else min(book.balance["1700"], policy["legacy_issue_amortization_per_month_usd"])
    )
    book.pair(
        month,
        "5400",
        "1700",
        amort,
        "LEGACY-ISSUE-AMORT",
        "DEBT_ISSUANCE_AMORTIZATION",
        "Legacy issuance cost amortization/writeoff at maturity",
    )
    new_amort = (
        min(
            book.balance["1701"],
            money(D(state["refinance_fee_original"]) / policy["new_term_months"]),
        )
        if state["refinancing_done"]
        else 0
    )
    book.pair(
        month,
        "5400",
        "1701",
        new_amort,
        "NEW-ISSUE-AMORT",
        "DEBT_ISSUANCE_AMORTIZATION",
        "Conditional new issuance cost amortization",
    )
    output.append(
        {
            "scenario": book.scenario,
            "entity": book.entity,
            "year": book.year,
            "month": month,
            "opening_legacy_term_usd": opening_term,
            "opening_replacement_term_usd": opening_new,
            "opening_lease_usd": opening_lease,
            "scheduled_legacy_principal_usd": principal,
            "scheduled_lease_principal_usd": lease,
            "interest_expense_usd": interest,
            "issuance_cost_amortization_usd": amort + new_amort,
            "legacy_matured": matured,
            "conditional_refinance_capacity_usd": refinancing["available_principal_usd"],
        }
    )


def post_tax(book, state, month, index, source, output):
    policy = source["tax"][book.entity]
    if month == 1:
        state.update(tax_opening_nol=state["nol"], tax_previous_expense=0, tax_year_goodwill=0)
    goodwill_deduction = 0
    if book.entity == "ARU_GROUP":
        tax = source["tax"]
        reserve_gross = money(
            D(tax["reserve_temporary_difference_usd"]) * D(str(policy["rate_pct"])) / 100
        )
        allowance = money(
            D(reserve_gross)
            * D(str(tax["reserve_dta_valuation_allowance_pct"][book.scenario]))
            / 100
        )
        target_dta = reserve_gross - allowance
        book.pair(
            month,
            "1800",
            "5501",
            target_dta - book.balance["1800"],
            f"RESERVE-DTA-{book.year}{month:02}",
            "DEFERRED_TAX_ASSESSMENT",
            "Scenario tax rate and explicitly declared reserve DTA valuation allowance",
        )
        cumulative = min(
            tax["goodwill_original_tax_basis_usd"],
            money(
                D(tax["goodwill_original_tax_basis_usd"])
                * (tax["goodwill_completed_months_at_anchor"] + index)
                / tax["goodwill_original_amortization_months"]
            ),
        )
        goodwill_deduction = cumulative - state["goodwill_amortization"]
        state["goodwill_amortization"] = cumulative
        state["tax_year_goodwill"] += goodwill_deduction
        target = money(D(cumulative) * D(str(policy["rate_pct"])) / 100)
        book.pair(
            month,
            "5501",
            "2250",
            target + book.balance["2250"],
            f"TAX-GOODWILL-{book.year}{month:02}",
            "DEFERRED_TAX",
            (
                "Subsequent tax amortization temporary difference; "
                "initial goodwill excess remains separate"
            ),
        )
    pretax = book.income(pretax=True)
    taxable_before_nol = pretax - state["tax_year_goodwill"]
    utilized = min(
        state["tax_opening_nol"],
        money(D(max(taxable_before_nol, 0)) * D(str(policy["nol_utilization_limit_pct"])) / 100),
    )
    taxable = max(taxable_before_nol - utilized, 0)
    current = money(D(taxable) * D(str(policy["rate_pct"])) / 100)
    delta = current - state["tax_previous_expense"]
    book.pair(
        month,
        "5500",
        "2700",
        delta,
        f"TAX-{book.year}{month:02}",
        "CURRENT_TAX",
        "Cumulative annual taxable result with explicit NOL utilization ceiling",
    )
    state["tax_previous_expense"] = current
    nol_closing = state["tax_opening_nol"] - utilized + max(-taxable_before_nol, 0)
    if month == 12:
        state["nol"] = nol_closing
    # Reassess unpaid estimated tax without manufacturing a refund.
    credit = max(-book.balance["2700"], 0)
    for row in [r for r in state["obligations"] if r["account"] == "2700"]:
        row["amount"] = min(row["amount"], credit)
        credit -= row["amount"]
    if month in source["tax"]["payment_months"]:
        add_due(
            state,
            index,
            "2700",
            credit,
            f"TAX-CASH-{book.year}{month:02}",
            "TAX_PAYMENT",
            priority=2,
        )
    output.append(
        {
            "scenario": book.scenario,
            "entity": book.entity,
            "year": book.year,
            "month": month,
            "book_pretax_ytd_usd": pretax,
            "tax_goodwill_deduction_usd": goodwill_deduction,
            "tax_goodwill_deduction_ytd_usd": state["tax_year_goodwill"],
            "taxable_before_nol_ytd_usd": taxable_before_nol,
            "opening_year_nol_usd": state["tax_opening_nol"],
            "nol_utilized_ytd_usd": utilized,
            "modeled_closing_nol_usd": nol_closing,
            "taxable_after_nol_ytd_usd": taxable,
            "current_tax_expense_usd": delta,
            "current_tax_expense_ytd_usd": current,
            "new_nol_dta_recognized_usd": 0,
            "new_nol_dta_full_valuation_allowance_usd": money(
                D(nol_closing) * D(str(policy["rate_pct"])) / 100
            ),
            "goodwill_dtl_usd": -book.balance["2250"],
            "reserve_dta_usd": book.balance["1800"],
            "remaining_tax_goodwill_basis_usd": source["tax"]["goodwill_original_tax_basis_usd"]
            - state["goodwill_amortization"]
            if book.entity == "ARU_GROUP"
            else 0,
        }
    )


def fund_and_pay(
    book, state, month, index, capital, source, funding, payments, assets, other_book=None
):
    floor = source["funding"]["cash_floor_usd"][book.entity]
    due = [r for r in state["obligations"] if r["due"] <= index and r["amount"] > 0]
    old_deferred = state["deferred_capital"]
    desired_capital = old_deferred + capital
    wanted_capital = sum(r["amount"] for r in desired_capital)
    requirement = max(
        floor + sum(r["amount"] for r in due) + wanted_capital - book.balance["1000"], 0
    )
    limit = source["funding"]["annual_conditional_equity_limits_usd"][book.scenario][
        str(book.year)
    ][book.entity]
    remaining = max(limit - state["equity_by_year"][book.year], 0)
    received = min(requirement, remaining)
    recipient = "ARU" if book.entity == "ARU_GROUP" else "RWH_VIA_PS"
    book.cash(
        month,
        "3000",
        -received,
        f"EQUITY-{book.scenario}-{book.entity}-{book.year}{month:02}",
        "PARENT_EQUITY",
        "Receipt within finite conditional parent allocation",
        cash_flow="FINANCING",
        counterparty="SHIH" if recipient == "ARU" else "PS",
    )
    state["equity_by_year"][book.year] += received
    for row in sorted(due, key=lambda r: (r["priority"], r["due"], r["source_id"])):
        paid = min(row["amount"], max(book.balance["1000"] - floor, 0))
        if paid:
            book.cash(
                month,
                row["account"],
                paid,
                row["source_id"],
                "INTERCOMPANY_PAYMENT"
                if row["account"] == "2150"
                else "PAYMENT_" + row["source_type"],
                "Cash settlement of modeled obligation; unpaid remainder stays outstanding",
                segment=row["segment"],
                counterparty=row["counterparty"],
                cash_flow=row["cash_flow"],
            )
            if row["account"] == "2150":
                if other_book is None:
                    raise ValueError("Intercompany cash requires a reciprocal ledger")
                other_book.cash(
                    month,
                    "1150",
                    -paid,
                    row["source_id"],
                    "INTERCOMPANY_PAYMENT",
                    "Reciprocal receipt from mine",
                    counterparty="RWH_PS",
                    segment=row["segment"],
                )
            row["amount"] -= paid
        payments.append(
            {
                "scenario": book.scenario,
                "entity": book.entity,
                "year": book.year,
                "month": month,
                "source_id": row["source_id"],
                "account": row["account"],
                "paid_usd": paid,
                "remaining_due_usd": row["amount"],
                "scheduled_due_index": row["due"],
            }
        )
    state["obligations"] = [r for r in state["obligations"] if r["amount"]]
    state["deferred_capital"] = []
    paid_capital = 0
    for row in desired_capital:
        amount = min(row["amount"], max(book.balance["1000"] - floor, 0))
        if amount:
            project_id = row.get("project_id", "")
            account = "1410" if project_id else "1400"
            book.cash(
                month,
                account,
                amount,
                row["source_id"],
                "CAPITAL_PURCHASE",
                "Paid construction awaits full funding and conditional service"
                if project_id
                else "Paid replacement capital; depreciation starts next month",
                cash_flow="INVESTING",
            )
            life = source["capital"][
                "aru_new_asset_life_years"
                if book.entity == "ARU_GROUP"
                else "mine_new_asset_life_years"
            ]
            card = {
                "asset_id": f"{row['source_id']}-PAID-{index}",
                "entity": book.entity,
                "gross_usd": amount,
                "accum_usd": 0,
                "annual_depreciation_usd": str(D(amount) / life),
                "mode": "STRAIGHT_LINE"
                if book.entity == "ARU_GROUP"
                else "PRODUCTION_STRAIGHT_LINE",
                "first_index": None if project_id else index,
                "ledger_account": account,
                "project_id": project_id,
                "planned_service_index": row.get("service_index", index),
            }
            state["cards"].append(card)
            assets.append(asset_row(book, card, month, additions=amount))
            if project_id:
                state["projects"][project_id]["paid_usd"] += amount
            paid_capital += amount
        if amount < row["amount"]:
            state["deferred_capital"].append(dict(row, amount=row["amount"] - amount))
    activate_projects(book, state, month, index)
    # Completion can occur after the month's final funding payment. Update the
    # month-end card classification; no depreciation is backdated into this month.
    cards = {c["asset_id"]: c for c in state["cards"]}
    for asset in assets:
        if (
            asset["scenario"] == book.scenario
            and asset["entity"] == book.entity
            and asset["year"] == book.year
            and asset["month"] == month
        ):
            card = cards[asset["asset_id"]]
            asset["ledger_account"] = card.get("ledger_account", "1400")
            asset["asset_status"] = (
                "CONSTRUCTION_IN_PROGRESS"
                if asset["ledger_account"] == "1410"
                else "CONDITIONAL_IN_SERVICE"
            )
            asset["actual_conditional_service_index"] = card["first_index"]
            asset["actual_conditional_service_period"] = index_period(card["first_index"])
            project = state["projects"].get(card.get("project_id"), {})
            asset["project_budget_usd"] = project.get("budget_usd", 0)
            asset["project_paid_to_date_usd"] = project.get("paid_usd", 0)
    arrears = sum(r["amount"] for r in state["obligations"] if r["due"] <= index)
    deferred = sum(r["amount"] for r in state["deferred_capital"])
    funding.append(
        {
            "scenario": book.scenario,
            "entity": book.entity,
            "year": book.year,
            "month": month,
            "recipient": recipient,
            "required_equity_usd": requirement,
            "available_equity_usd": received,
            "received_equity_usd": received,
            "funding_gap_usd": requirement - received,
            "annual_conditional_limit_usd": limit,
            "remaining_annual_capacity_usd": limit - state["equity_by_year"][book.year],
            "unpaid_due_obligations_usd": arrears,
            "deferred_capex_usd": deferred,
            "capital_paid_usd": paid_capital,
            "cash_floor_usd": floor,
            "financially_feasible": arrears == 0 and deferred == 0,
            "funding_state": "CONDITIONAL_ALLOCATION_NOT_COMMITTED_CAPITAL",
        }
    )
    return arrears, deferred


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(
            {
                k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v
                for k, v in row.items()
            }
            for row in rows
        )


def capital_schedule(rows, source):
    """Tie every growth dollar to its operating project's dated service gate."""
    mapping = source["capital"]["growth_project_by_segment"]
    service = {}
    for row in rows:
        index = (row["year"] - 2027) * 12 + row["month"]
        for event in row["capital"]["conditional_in_service_events"]:
            key = row["scenario"], event["project_id"]
            if key in service:
                raise ValueError("A growth project must have one conditional service event")
            service[key] = index
    plans, projects = {}, defaultdict(dict)
    for row in rows:
        scenario, year, month = row["scenario"], row["year"], row["month"]
        for entity, prefix in (("ARU_GROUP", "aru"), ("RWH_PS", "mine")):
            values = [
                {
                    "amount": money(row["capital"][f"{prefix}_replacement_usd"]),
                    "kind": "replacement",
                    "source_id": f"CAPEX-{scenario}-{entity}-{year}{month:02}-replacement",
                }
            ]
            growth = money(row["capital"][f"{prefix}_growth_usd"])
            segments = {
                segment: value
                for segment, value in row["capital"].get("growth_by_segment", {}).items()
                if (segment == "RWH") == (entity == "RWH_PS") and value
            }
            if abs(sum(D(str(v)) for v in segments.values()) - growth) > 1:
                raise ValueError("Growth capital requires a complete segment/project bridge")
            allocations = split(growth, list(segments.values())) if segments else []
            for segment, value in zip(segments, allocations, strict=True):
                project_id = mapping[segment]
                if (scenario, project_id) not in service:
                    raise ValueError("Paid growth has no conditional in-service event")
                index = service[scenario, project_id]
                values.append(
                    {
                        "amount": value,
                        "kind": "growth",
                        "source_id": f"CAPEX-{scenario}-{entity}-{year}{month:02}-growth-{segment}",
                        "project_id": project_id,
                        "service_index": index,
                    }
                )
                project = projects[scenario, entity].setdefault(
                    project_id,
                    {
                        "budget_usd": 0,
                        "paid_usd": 0,
                        "service_index": index,
                        "actual_service_index": None,
                    },
                )
                project["budget_usd"] += value
            plans[scenario, entity, year, month] = values
    return plans, projects


def build(output=OUT, operating_rows=None, source=None):
    from industrial.planning.transactions import procurement_costs

    source = source_data(source)
    rows = prepare_rows(operating_rows, source)
    capital_plans, growth_projects = capital_schedule(rows, source)
    historical = json.loads(OLD_SOURCE.read_text())
    operations = json.loads(OLD_OPERATIONS.read_text())
    _, _, contracts = customer_schedules(historical)
    _, payroll = payroll_schedules(historical)
    headcounts = {
        segment: sum(e["fte"] for e in historical["employees"] if e["segment"] == segment)
        for segment in historical["segment_baseline"]
    }
    purchases = {
        (r["scenario"], r["year"], r["month"], r["segment"]): r for r in procurement_costs(rows)
    }
    datasets = {
        name: []
        for name in [
            "journal",
            "trial_balances",
            "monthly_statements",
            "opening_balances",
            "funding",
            "payments",
            "assets",
            "debt",
            "tax",
            "intercompany",
            "inventory",
            "contract_revenue",
            "eliminations",
        ]
    }
    summaries = {}
    for scenario in source["scenarios"]:
        states = {
            e: initial_state(e, scenario, source) for e in source["anchor"]["opening_balances"]
        }
        for entity, state in states.items():
            state["projects"] = copy.deepcopy(growth_projects[scenario, entity])
        carry = copy.deepcopy(source["anchor"]["opening_balances"])
        books = {}
        for op in [r for r in rows if r["scenario"] == scenario]:
            year, month = op["year"], op["month"]
            index = (year - 2027) * 12 + month
            if month == 1:
                books = {e: Book(scenario, e, year, carry[e], source) for e in states}
                for book in books.values():
                    datasets["opening_balances"].extend(book.trial_balance(0))
            aru, mine = books["ARU_GROUP"], books["RWH_PS"]
            astate, mstate = states["ARU_GROUP"], states["RWH_PS"]
            cost_index = D(str(op["assumptions"]["cash_cost_index"]))
            price_index = D(str(op["assumptions"]["external_price_index"]))
            lost_customers = set(op.get("lost_customer_ids", []))
            for segment, physical_segment in op["segments"].items():
                factor = D(str(physical_segment["revenue_volume_factor"]))
                group_contracts = [
                    r for r in contracts if r["month"] == month and r["segment"] == segment
                ]
                if (
                    physical_segment.get("customer_loss_revenue_fraction", 0) > 0
                    and not lost_customers
                ):
                    raise ValueError("Customer cancellation requires explicit lost_customer_ids")
                eligible = [r for r in group_contracts if r["customer_id"] not in lost_customers]
                target = money(
                    sum(r["revenue_usd"] for r in group_contracts) * factor * price_index
                )
                allocations = (
                    dict(
                        zip(
                            [r["contract_id"] for r in eligible],
                            split(target, [r["revenue_usd"] for r in eligible]),
                            strict=True,
                        )
                    )
                    if eligible
                    else {}
                )
                for contract in group_contracts:
                    renewal = D(
                        str(
                            source["adjustments"][scenario][
                                "contract_renewal_price_multipliers"
                            ].get(contract["customer_id"], 1)
                        )
                    )
                    amount = money(D(allocations.get(contract["contract_id"], 0)) * renewal)
                    ident = f"SALE-{scenario}-{year}{month:02}-{contract['contract_id']}"
                    invoice(
                        aru,
                        astate,
                        month,
                        index,
                        amount,
                        ident,
                        "CUSTOMER_INVOICE",
                        segment,
                        contract["customer_id"],
                        source,
                    )
                    datasets["contract_revenue"].append(
                        {
                            "scenario": scenario,
                            "year": year,
                            "month": month,
                            "contract_id": contract["contract_id"],
                            "customer_id": contract["customer_id"],
                            "segment": segment,
                            "source_id": ident,
                            "revenue_usd": amount,
                            "segment_revenue_volume_factor": str(factor),
                            "canceled_customer": contract["customer_id"] in lost_customers,
                            "price_index": str(price_index),
                            "renewal_price_multiplier": str(renewal),
                        }
                    )
            for segment in historical["segment_baseline"]:
                fte = (
                    source["payroll"]["corporate_fte"]
                    if segment == "ARU"
                    else op["segments"][segment]["fte"]
                )
                amount = money(
                    D(payroll[segment])
                    / 12
                    * D(str(fte))
                    / headcounts[segment]
                    * cost_index
                    * D(str(source["adjustments"][scenario]["payroll_multiplier"]))
                )
                expense(
                    aru,
                    astate,
                    month,
                    index,
                    amount,
                    "5000",
                    f"PAYROLL-{scenario}-{year}{month:02}-{segment}",
                    "PAYROLL",
                    segment=segment,
                    counterparty="SYNTHETIC_EMPLOYEE_CENSUS",
                    priority=0,
                )
                for item in purchases[(scenario, year, month, segment)]["items"]:
                    due = date.fromisoformat(item["due_date"])
                    due_index = (due.year - 2027) * 12 + due.month
                    expense(
                        aru,
                        astate,
                        month,
                        index,
                        item["amount_usd"],
                        "5100",
                        item["source_id"],
                        "PROCUREMENT",
                        due=due_index,
                        segment=segment,
                        counterparty=item["vendor_id"],
                    )
                if segment != "ARU":
                    expense(
                        aru,
                        astate,
                        month,
                        index,
                        money(op["segments"][segment]["additional_cash_cost_usd"]),
                        "5200",
                        f"DISRUPTION-{scenario}-{year}{month:02}-{segment}",
                        "DISRUPTION_AND_OUTSIDE_CAPACITY",
                        segment=segment,
                    )
            if index == 1:
                remaining_service = (
                    historical["transaction"]["retention_pool"] - 250000 + aru.balance["2110"]
                )
                aru.pair(
                    month,
                    "5700",
                    "2110",
                    remaining_service,
                    "FINAL-RETENTION-SERVICE",
                    "RETENTION",
                    "Final six service days of accepted retention program",
                )
                add_due(
                    astate,
                    index,
                    "2110",
                    -aru.balance["2110"],
                    "FINAL-RETENTION-PAYMENT",
                    "RETENTION",
                    priority=0,
                )
            safety_target = money(
                D(source["working_capital"]["aru_safety_stock_minimum_usd"])
                * (
                    1
                    + D(str(source["working_capital"]["aru_safety_stock_growth_share"]))
                    * max(cost_index / D("1.03") - 1, D(0))
                )
            )
            if safety_target > aru.balance["1200"]:
                amount = safety_target - aru.balance["1200"]
                aru.pair(
                    month,
                    "1200",
                    "2000",
                    amount,
                    f"SPARES-{scenario}-{year}{month:02}",
                    "INVENTORY_PURCHASE",
                    "Additional indexed safety stock, no downward revaluation/refund",
                )
                add_due(
                    astate,
                    index + 1,
                    "2000",
                    amount,
                    f"SPARES-{scenario}-{year}{month:02}",
                    "INVENTORY_PURCHASE",
                )
            for rate in operations["interface"]["rates"]:
                commodity = rate["commodity"]
                cars = op["interface"]["aru_served_cars_by_commodity"][commodity]
                for segment, rate_value, unit_cost in [
                    ("BST", rate["rail_rate"], rate["rail_unit_cost"]),
                    ("TERMINALS", rate["terminal_rate"], rate["terminal_unit_cost"]),
                    (
                        "TRUCKING",
                        rate["truck_legs_per_car"] * rate["dray_rate"],
                        rate["truck_legs_per_car"] * rate["dray_unit_cost"],
                    ),
                ]:
                    amount = money(
                        D(str(cars))
                        * rate_value
                        * D(str(op["assumptions"]["interface_price_index"]))
                    )
                    cost = money(
                        D(str(cars)) * unit_cost * D(str(op["assumptions"]["interface_cost_index"]))
                    )
                    ident = f"IC-{scenario}-{year}{month:02}-{commodity}-{segment}"
                    aru.pair(
                        month,
                        "1150",
                        "4100",
                        amount,
                        ident,
                        "INTERCOMPANY_SERVICE",
                        "Served physical cars at declared interface rates",
                        segment=segment,
                        counterparty="RWH_PS",
                    )
                    mine.pair(
                        month,
                        "5150",
                        "2150",
                        amount,
                        ident,
                        "INTERCOMPANY_SERVICE",
                        "Reciprocal mine service charge",
                        segment="RWH",
                        counterparty="ARU_GROUP",
                    )
                    add_due(
                        mstate,
                        index + 1,
                        "2150",
                        amount,
                        ident,
                        "INTERCOMPANY_PAYMENT",
                        segment=segment,
                        counterparty="ARU_GROUP",
                        priority=3,
                    )
                    expense(
                        aru,
                        astate,
                        month,
                        index,
                        cost,
                        "5200",
                        ident + "-COST",
                        "INTERFACE_VARIABLE_COST",
                        segment=segment,
                    )
                    datasets["intercompany"].append(
                        {
                            "scenario": scenario,
                            "year": year,
                            "month": month,
                            "invoice_id": ident,
                            "seller_entity": "ARU_GROUP",
                            "buyer_entity": "RWH_PS",
                            "segment": segment,
                            "commodity": commodity,
                            "physical_cars": cars,
                            "revenue_usd": amount,
                            "external_variable_cost_usd": cost,
                        }
                    )
            for segment, field in [
                ("BST", "rail"),
                ("TERMINALS", "terminal"),
                ("TRUCKING", "trucking"),
            ]:
                amount = money(
                    D(operations["interface"]["fixed_cost_by_segment"][field])
                    / 12
                    * D(str(op["assumptions"]["interface_cost_index"]))
                )
                expense(
                    aru,
                    astate,
                    month,
                    index,
                    amount,
                    "5200",
                    f"IF-FIXED-{scenario}-{year}{month:02}-{segment}",
                    "INTERFACE_READINESS",
                    segment=segment,
                )
            mine_policy, physical = source["mine"], op["mine"]
            produced, sold = (
                D(str(physical["production_u3o8_lb"])),
                D(str(physical["sales_u3o8_lb"])),
            )
            available_units = mstate["inventory_units"] + produced
            if sold > available_units or min(produced, sold) < 0:
                raise ValueError("Mine sales exceed physical inventory available")
            production_cost, capitalized_production_cost, idle_production_cost = production_costs(
                physical, mine_policy
            )
            mine.entry(
                month,
                [
                    ("1200", capitalized_production_cost),
                    ("5100", idle_production_cost),
                    ("2000", -production_cost),
                ],
                f"MINE-PRODUCTION-{scenario}-{year}{month:02}",
                "PRODUCTION_COST",
                "Normal production cost capitalized; abnormal idle fixed overhead expensed",
                segment="RWH",
            )
            add_due(
                mstate,
                index,
                "2000",
                production_cost,
                f"MINE-PRODUCTION-{scenario}-{year}{month:02}",
                "PRODUCTION_COST",
                segment="RWH",
            )
            depreciate(aru, astate, month, index, D(0), source, datasets["assets"])
            produced_dda = depreciate(
                mine, mstate, month, index, produced, source, datasets["assets"]
            )
            cash_cogs = (
                money(D(mine.balance["1200"]) * sold / available_units) if available_units else 0
            )
            dda_cogs = (
                money(D(mine.balance["1210"]) * sold / available_units) if available_units else 0
            )
            mine.pair(
                month,
                "5100",
                "1200",
                cash_cogs,
                f"MINE-COGS-{scenario}-{year}{month:02}",
                "WEIGHTED_AVERAGE_COGS",
                "Cash inventory cost released in proportion to shipped pounds",
                segment="RWH",
            )
            mine.pair(
                month,
                "5300",
                "1210",
                dda_cogs,
                f"MINE-COGS-{scenario}-{year}{month:02}",
                "WEIGHTED_AVERAGE_COGS",
                "Inventory production depreciation released to sales",
                segment="RWH",
            )
            mstate["inventory_units"] = available_units - sold
            if abs(mstate["inventory_units"] - D(str(physical["ending_product_inventory_lb"]))) > 1:
                raise ValueError("Financial and operating product inventory disagree")
            revenue = money(sold * D(str(physical["uranium_price_usd_lb"])))
            invoice(
                mine,
                mstate,
                month,
                index,
                revenue,
                f"MINE-SALE-{scenario}-{year}{month:02}",
                "MINE_CUSTOMER_INVOICE",
                "RWH",
                "SYNTHETIC_URANIUM_OFFTAKE_BOOK",
                source,
            )
            charges = [
                (
                    money(
                        produced
                        * D(str(mine_policy["production_tax_usd_per_lb_at_base_price"]))
                        * D(str(physical["uranium_price_usd_lb"]))
                        / D(str(mine_policy["base_price_usd_lb"]))
                    ),
                    "PRODUCTION_MINERAL_TAX",
                    "RWH",
                ),
                (
                    money(D(revenue) * D(str(mine_policy["royalty_revenue_pct"])) / 100),
                    "ROYALTY",
                    "RWH",
                ),
                (
                    money(
                        D(mine_policy["annual_freight_assay_base_usd"])
                        * sold
                        / mine_policy["base_sales_lb"]
                        * cost_index
                        / D("1.03")
                    ),
                    "MINE_FREIGHT_ASSAY",
                    "RWH",
                ),
                (
                    money(
                        D(mine_policy["annual_platform_site_ga_base_usd"])
                        / 12
                        * cost_index
                        / D("1.03")
                        * (
                            1
                            + D(str(mine_policy["platform_staff_cost_exposure_share"]))
                            * (
                                D(str(physical["platform_fte"]))
                                / mine_policy["baseline_platform_fte"]
                                - 1
                            )
                        )
                    ),
                    "MINE_PLATFORM_SITE_GA",
                    "PS",
                ),
                (money(physical["additional_cash_cost_usd"]), "MINE_DISRUPTION", "RWH"),
            ]
            for amount, kind, segment in charges:
                expense(
                    mine,
                    mstate,
                    month,
                    index,
                    amount,
                    "5100",
                    f"{kind}-{scenario}-{year}{month:02}",
                    kind,
                    segment=segment,
                )
            outside = money(
                D(str(op["interface"]["external_linehaul_usd"]))
                + D(str(op["interface"]["outside_service_cash_usd"]))
            )
            expense(
                mine,
                mstate,
                month,
                index,
                outside,
                "5200",
                f"OUTSIDE-LOGISTICS-{scenario}-{year}{month:02}",
                "EXTERNAL_LOGISTICS",
                segment="RWH",
            )
            aro = money(
                D(-mine.balance["2200"])
                * ((1 + D(str(mine_policy["aro_discount_pct"])) / 100) ** (D(1) / 12) - 1)
            )
            mine.pair(
                month,
                "5600",
                "2200",
                aro,
                f"ARO-{scenario}-{year}{month:02}",
                "ARO_ACCRETION",
                "Effective annual rate compounded monthly",
                segment="RWH",
            )
            if month == 12:
                add_due(
                    mstate,
                    index,
                    "2200",
                    mine_policy["aro_settlement_schedule_usd"][str(year)],
                    f"CLOSURE-{scenario}-{year}",
                    "ARO_SETTLEMENT",
                    segment="RWH",
                    priority=2,
                )
            datasets["inventory"].append(
                {
                    "scenario": scenario,
                    "year": year,
                    "month": month,
                    "produced_lb": str(produced),
                    "sold_lb": str(sold),
                    "ending_inventory_lb": str(mstate["inventory_units"]),
                    "production_cash_cost_usd": production_cost,
                    "capitalized_production_cash_usd": capitalized_production_cost,
                    "idle_production_expense_usd": idle_production_cost,
                    "production_depreciation_usd": produced_dda,
                    "cash_cogs_usd": cash_cogs,
                    "dda_cogs_usd": dda_cogs,
                    "ending_cash_inventory_usd": mine.balance["1200"],
                    "ending_dda_inventory_usd": mine.balance["1210"],
                }
            )
            post_debt(aru, astate, month, index, source, datasets["debt"])
            for book in books.values():
                collect(book, states[book.entity], month, index)
                post_tax(book, states[book.entity], month, index, source, datasets["tax"])
            for book, state in [(mine, mstate), (aru, astate)]:
                capital = capital_plans[scenario, book.entity, year, month]
                arrears, deferred = fund_and_pay(
                    book,
                    state,
                    month,
                    index,
                    capital,
                    source,
                    datasets["funding"],
                    datasets["payments"],
                    datasets["assets"],
                    aru if book is mine else None,
                )
                summary = book.summary(month)
                summary.update(
                    unpaid_due_obligations_usd=arrears,
                    deferred_capex_usd=deferred,
                    financially_feasible=not (arrears or deferred),
                    operational_constraints=op["constraints"],
                )
                datasets["monthly_statements"].append(summary)
                datasets["trial_balances"].extend(book.trial_balance(month))
                for tax in [r for r in datasets["tax"][-2:] if r["entity"] == book.entity]:
                    tax["current_tax_cash_paid_usd"] = sum(
                        r["signed_usd"]
                        for r in book.rows
                        if r["month"] == month
                        and r["account"] == "2700"
                        and r["cash_flow"] == "OPERATING"
                    )
                    tax["current_tax_settlement_signed_usd"] = book.balance["2700"]
                    tax["deferred_tax_expense_usd"] = sum(
                        r["signed_usd"]
                        for r in book.rows
                        if r["month"] == month and r["account"] == "5501"
                    )
                if book.entity == "ARU_GROUP":
                    debt = datasets["debt"][-1]
                    for account, label in [
                        ("2400", "legacy_term"),
                        ("2410", "replacement_term"),
                        ("2600", "lease"),
                    ]:
                        debt[f"closing_{label}_usd"] = -book.balance[account]
                        debt[f"principal_cash_paid_{label}_usd"] = sum(
                            r["signed_usd"]
                            for r in book.rows
                            if r["month"] == month
                            and r["account"] == account
                            and r["cash_flow"] == "FINANCING"
                            and r["signed_usd"] > 0
                        )
                    debt["replacement_debt_draw_usd"] = -sum(
                        r["signed_usd"]
                        for r in book.rows
                        if r["month"] == month and r["account"] == "2410" and r["signed_usd"] < 0
                    )
                    debt["closing_issuance_costs_usd"] = book.balance["1700"] + book.balance["1701"]
                    debt["overdue_matured_legacy_term_usd"] = (
                        -book.balance["2400"] if debt["legacy_matured"] else 0
                    )
                if (
                    sum(c["gross_usd"] for c in state["cards"])
                    != book.balance["1400"] + book.balance["1410"]
                    or sum(c["accum_usd"] for c in state["cards"]) != -book.balance["1490"]
                ):
                    raise ValueError("Fixed asset subledger does not reconcile")
            if aru.balance["1150"] != -mine.balance["2150"]:
                raise ValueError("Reciprocal intercompany balance failed")
            current_ic = -sum(
                r["signed_usd"] for r in aru.rows if r["month"] == month and r["account"] == "4100"
            )
            datasets["eliminations"].append(
                {
                    "scenario": scenario,
                    "year": year,
                    "month": month,
                    "service_revenue_expense_elimination_usd": current_ic,
                    "receivable_payable_elimination_usd": aru.balance["1150"],
                }
            )
            if month == 12:
                for book in books.values():
                    datasets["journal"].extend(book.rows)
                    carry[book.entity] = book.carry()
        summaries[scenario] = {
            "ending_2031": {e: b.summary(12) for e, b in books.items()},
            "total_conditional_equity_received_usd": sum(
                r["received_equity_usd"] for r in datasets["funding"] if r["scenario"] == scenario
            ),
            "maximum_monthly_funding_gap_usd": max(
                r["funding_gap_usd"] for r in datasets["funding"] if r["scenario"] == scenario
            ),
            "months_with_funding_gap": sum(
                r["funding_gap_usd"] > 0 for r in datasets["funding"] if r["scenario"] == scenario
            ),
        }
    for records in datasets.values():
        for row in records:
            for key, value in metadata(source).items():
                row.setdefault(key, value)
            if "year" in row and "month" in row:
                month = max(row["month"], 1)
                last_day = 1 if row["month"] == 0 else calendar.monthrange(row["year"], month)[1]
                row.setdefault(
                    "effective_period_end",
                    f"{row['year']}-{month:02}-{last_day:02}",
                )
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, records in datasets.items():
        path = output / (name + ".csv")
        write_csv(path, records)
        paths[name] = str(path)
    summary = {
        "status": "PASS",
        "basis": "Conditional 2027–2031 planning, not actual results or committed funding",
        "source_id": source["record_id"],
        "anchor": source["anchor"],
        "scenarios": summaries,
        "row_counts": {k: len(v) for k, v in datasets.items()},
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    manifest = {
        "artifacts": [
            {
                "path": p.name,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "bytes": p.stat().st_size,
            }
            for p in sorted(output.glob("*.csv"))
        ],
        "source_sha256": hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest(),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return {
        "summary": summary,
        "journal_rows": datasets["journal"],
        "trial_balance_rows": datasets["trial_balances"],
        "monthly_rows": datasets["monthly_statements"],
        "funding_rows": datasets["funding"],
        "opening_rows": datasets["opening_balances"],
        "operating_rows": rows,
        "paths": paths,
        "datasets": datasets,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    result = build(args.output)
    print(
        json.dumps(
            {
                "status": result["summary"]["status"],
                "rows": result["summary"]["row_counts"],
                "output": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
