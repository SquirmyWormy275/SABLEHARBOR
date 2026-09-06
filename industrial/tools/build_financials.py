#!/usr/bin/env python3
"""Deterministic, synthetic industrial successor financial case.

Inputs are versioned JSON; outputs are exclusively industrial/generated/finance.
No released enterprise finance configuration or financial snapshot is rewritten.
Money is whole USD, rounded half up. Every journal balances independently.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
OUT = ROOT / "generated" / "finance"
SOURCE = ROOT / "source" / "finance.json"
OPS = ROOT / "source" / "operations.json"
CORE = REPO / "red_wash" / "source" / "core_operating_data.json"

ACCOUNTS = {
    "1000": ("Cash", "asset"),
    "1100": ("External receivables, net of allowance", "asset"),
    "1150": ("Intercompany receivable", "asset"),
    "1200": ("Inventory cash cost", "asset"),
    "1210": ("Inventory DD&A", "asset"),
    "1300": ("Prepaids", "asset"),
    "1400": ("PPE gross", "asset"),
    "1490": ("Accumulated PPE depreciation", "asset"),
    "1500": ("Finance lease ROU gross", "asset"),
    "1590": ("Accumulated finance lease ROU depreciation", "asset"),
    "1600": ("Goodwill", "asset"),
    "1700": ("Debt issuance cost, contra term debt", "liability"),
    "1800": ("Deferred tax asset on reserved liabilities", "asset"),
    "1801": ("Deferred tax asset on interim modeled tax loss", "asset"),
    "1810": ("Investment in controlled subsidiary", "asset"),
    "1180": ("Intercompany treasury current account", "intercompany"),
    "2000": ("Trade payables", "liability"),
    "2100": ("Operating accruals", "liability"),
    "2110": ("Retention compensation payable", "liability"),
    "2150": ("Intercompany payable", "liability"),
    "2200": ("Environmental reserve / ARO", "liability"),
    "2300": ("Claim reserve / other liabilities", "liability"),
    "2250": ("Deferred tax liability on tax goodwill amortization", "liability"),
    "2700": ("Current income tax payable / prepaid", "current_settlement"),
    "2400": ("Term debt face value", "liability"),
    "2500": ("Revolver", "liability"),
    "2600": ("Finance lease obligation", "liability"),
    "3000": ("Contributed equity", "equity"),
    "3100": ("Prior retained earnings", "equity"),
    "3200": ("Owner distributions", "equity"),
    "4000": ("External revenue", "revenue"),
    "4100": ("Intercompany service revenue", "revenue"),
    "5000": ("Payroll and employer burden", "expense"),
    "5100": ("External operating cost", "expense"),
    "5150": ("Intercompany logistics expense", "expense"),
    "5200": ("Incremental interface external operating cost", "expense"),
    "5300": ("Depreciation in earnings", "expense"),
    "5400": ("Interest and financing fees", "expense"),
    "5500": ("Modeled income tax", "expense"),
    "5501": ("Deferred income tax expense", "expense"),
    "5600": ("ARO accretion", "expense"),
    "5700": ("Retention and seller consulting", "expense"),
    "5800": ("Acquisition transaction expense", "expense"),
    "5900": ("Shared service allocation / recovery", "expense"),
}


def usd(value):
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def alloc(total, weights):
    """Largest-remainder allocation preserves exact integer units/dollars."""
    values = [
        Decimal(total) * Decimal(str(w)) / sum(map(lambda n: Decimal(str(n)), weights))
        for w in weights
    ]
    result = [int(v) for v in values]
    remainder = total - sum(result)
    for i in sorted(range(len(values)), key=lambda j: (-(values[j] - result[j]), j))[:remainder]:
        result[i] += 1
    return result


def period_role(year, month):
    if year < 2026:
        return "SYNTHETIC_HISTORICAL_CASE"
    return "SYNTHETIC_CALIBRATION" if month <= 8 else "MANAGEMENT_FORECAST"


class Ledger:
    def __init__(self, entity, year):
        self.entity, self.year = entity, year
        self.rows = []
        self.balances = defaultdict(int)
        self.sequence = 0

    def entry(self, month, description, lines, source, segment="ARU", cash_flow=None):
        if sum(amount for _, amount in lines):
            raise ValueError(f"Unbalanced journal: {description}: {lines}")
        self.sequence += 1
        ident = f"{self.entity}-{self.year}-{self.sequence:05}"
        for account, signed in lines:
            if signed == 0:
                continue
            self.balances[account] += signed
            self.rows.append(
                {
                    "journal_id": ident,
                    "entity": self.entity,
                    "year": self.year,
                    "month": month,
                    "segment": segment,
                    "account": account,
                    "account_name": ACCOUNTS[account][0],
                    "debit_usd": max(signed, 0),
                    "credit_usd": max(-signed, 0),
                    "signed_usd": signed,
                    "description": description,
                    "source_id": source,
                    "cash_flow": cash_flow or "NONCASH_OR_OPENING",
                    "period_role": period_role(self.year, max(month, 1)),
                    "record_origin": "PUBLIC_SYNTHETIC_DIEGETIC",
                    "fact_state": "LOCKED_DERIVED_IMPLEMENTATION",
                }
            )

    def pair(
        self, month, debit, credit, amount, description, source, segment="ARU", cash_flow=None
    ):
        self.entry(
            month, description, [(debit, amount), (credit, -amount)], source, segment, cash_flow
        )

    def cash(
        self, month, account, amount, description, source, segment="ARU", cash_flow="OPERATING"
    ):
        """Positive amount is cash payment/debit to account; negative is receipt."""
        self.pair(month, account, "1000", amount, description, source, segment, cash_flow)

    def summary(self):
        group = defaultdict(int)
        for a, signed in self.balances.items():
            kind = ACCOUNTS[a][1]
            if kind in ["intercompany", "current_settlement"]:
                kind = "asset" if signed >= 0 else "liability"
            group[kind] += signed
        income = -group["revenue"] - group["expense"]
        liabilities = -group["liability"]
        equity = -group["equity"] + income
        assert group["asset"] == liabilities + equity
        cf = defaultdict(int)
        for row in self.rows:
            if row["account"] == "1000":
                cf[row["cash_flow"]] += row["signed_usd"]
        opening = cf.pop("NONCASH_OR_OPENING", 0)
        assert opening + sum(cf.values()) == self.balances["1000"]
        return {
            "entity": self.entity,
            "year": self.year,
            "revenue_usd": -group["revenue"],
            "expense_usd": group["expense"],
            "net_income_usd": income,
            "assets_usd": group["asset"],
            "liabilities_usd": liabilities,
            "equity_including_current_income_usd": equity,
            "balance_sheet_difference_usd": 0,
            "opening_cash_usd": opening,
            "cash_flow": dict(cf),
            "ending_cash_usd": self.balances["1000"],
            "trial_balance_difference_usd": sum(self.balances.values()),
        }

    def trial_balance(self):
        return [
            {
                "entity": self.entity,
                "year": self.year,
                "account": account,
                "account_name": ACCOUNTS[account][0],
                "type": ACCOUNTS[account][1],
                "debit_balance_usd": max(value, 0),
                "credit_balance_usd": max(-value, 0),
                "signed_usd": value,
            }
            for account, value in sorted(self.balances.items())
        ]


def read_sources():
    return json.loads(SOURCE.read_text()), json.loads(OPS.read_text()), json.loads(CORE.read_text())


def customer_schedules(source):
    customers = {r["customer_id"]: dict(r, annual_revenue_usd=0) for r in source["customers"]}
    rows, monthly = [], []
    for contract in source["contracts"]:
        annual = (
            contract["annual_units"] * contract["unit_price_usd"]
            + contract["annual_reserved_capacity_accessorial_usd"]
        )
        customers[contract["customer_id"]]["annual_revenue_usd"] += annual
        segment = source["segment_baseline"][contract["segment"]]
        row = dict(
            contract,
            annual_revenue_usd=annual,
            analytical_allocated_opex_usd=usd(
                Decimal(annual) * segment["opex"] / segment["revenue"]
            ),
        )
        row["analytical_margin_usd"] = annual - row["analytical_allocated_opex_usd"]
        rows.append(row)
        quantities = alloc(contract["annual_units"], source["monthly_weights_2025"])
        fixed = alloc(contract["annual_reserved_capacity_accessorial_usd"], [1] * 12)
        for i, quantity in enumerate(quantities):
            monthly.append(
                {
                    "month": i + 1,
                    "period": f"2025-{i + 1:02}",
                    "contract_id": contract["contract_id"],
                    "customer_id": contract["customer_id"],
                    "segment": contract["segment"],
                    "commodity": contract["commodity"],
                    "unit": contract["unit"],
                    "units": quantity,
                    "unit_price_usd": contract["unit_price_usd"],
                    "fixed_fee_usd": fixed[i],
                    "revenue_usd": quantity * contract["unit_price_usd"] + fixed[i],
                    "period_role": "SYNTHETIC_HISTORICAL_CASE",
                }
            )
    for row in customers.values():
        row["concentration_pct"] = round(row["annual_revenue_usd"] / 420000, 6)
    return list(customers.values()), rows, monthly


def payroll_schedules(source):
    rows, totals = [], defaultdict(int)
    for employee in source["employees"]:
        burden = usd(
            Decimal(employee["annual_salary_usd"]) * employee["annual_employer_burden_pct"] / 100
        )
        cost = employee["annual_salary_usd"] + burden
        totals[employee["segment"]] += cost
        rows.append(
            dict(employee, annual_employer_burden_usd=burden, annual_loaded_payroll_usd=cost)
        )
    return rows, totals


def opening_2025(ledger, source):
    o = source["opening_2025"]
    names = {
        "cash": "1000",
        "receivables": "1100",
        "inventory": "1200",
        "prepaids": "1300",
        "ppe_gross": "1400",
        "ppe_accum_depreciation": "1490",
        "lease_rou_gross": "1500",
        "lease_rou_accum_depreciation": "1590",
        "payables": "2000",
        "operating_accruals": "2100",
        "environment_reserve": "2200",
        "claim_reserve": "2300",
        "term_debt": "2400",
        "revolver": "2500",
        "finance_lease_liability": "2600",
        "paid_in_capital": "3000",
        "retained_earnings": "3100",
    }
    negative = {
        "1490",
        "1590",
        "2000",
        "2100",
        "2200",
        "2300",
        "2400",
        "2500",
        "2600",
        "3000",
        "3100",
    }
    ledger.entry(
        0,
        "Explicit synthetic 2025 opening trial balance",
        [(a, -o[k] if a in negative else o[k]) for k, a in names.items()],
        "FIN-DER-003",
    )


def build_2025(source, monthly, payroll):
    ledger = Ledger("ARU_GROUP", 2025)
    opening_2025(ledger, source)
    o, c = source["opening_2025"], source["closing_2025_drivers"]
    segments = source["segment_baseline"]
    monthly_summary = []
    for month in range(1, 13):
        for row in monthly:
            if row["month"] == month:
                ledger.pair(
                    month,
                    "1100",
                    "4000",
                    row["revenue_usd"],
                    "External customer contract invoice",
                    row["contract_id"],
                    row["segment"],
                )
        for segment, plan in segments.items():
            pay = alloc(payroll[segment], [1] * 12)[month - 1]
            external_cost = plan["opex"] - plan["shared_allocation"]
            other = alloc(external_cost - payroll[segment], [1] * 12)[month - 1]
            assert other >= 0
            ledger.pair(
                month,
                "5000",
                "2000",
                pay,
                "Employee census payroll and employer burden",
                "FIN-DER-002",
                segment,
            )
            ledger.pair(
                month,
                "5100",
                "2000",
                other,
                "External operating supplier/service schedule",
                f"OPEX-{segment}",
                segment,
            )
            allocation = alloc(abs(plan["shared_allocation"]), [1] * 12)[month - 1]
            if segment != "ARU":
                # Separate segment debits and corporate recovery, zero at consolidation.
                ledger.entry(
                    month,
                    "Shared service allocation",
                    [("5900", allocation), ("2100", -allocation)],
                    "ALLOC-2025",
                    segment,
                )
                ledger.entry(
                    month,
                    "Corporate shared service cost recovery",
                    [("2100", allocation), ("5900", -allocation)],
                    "ALLOC-2025",
                    "ARU",
                )
        for key, account in [("inventory", "1200"), ("prepaids", "1300")]:
            change = alloc(c[key] - o[key], [1] * 12)[month - 1]
            ledger.pair(
                month, account, "2000", change, "Working-capital asset purchases", f"WC-{key}"
            )
        for key, account in [
            ("operating_accruals", "2100"),
            ("environment_reserve", "2200"),
            ("claim_reserve", "2300"),
        ]:
            change = alloc(c[key] - o[key], [1] * 12)[month - 1]
            ledger.pair(
                month,
                "2000",
                account,
                change,
                "Unpaid operating cost reserved by liability class",
                f"WC-{key}",
            )
        ar_target = o["receivables"] + sum(
            alloc(c["receivables"] - o["receivables"], [1] * 12)[:month]
        )
        ledger.cash(
            month,
            "1100",
            -(ledger.balances["1100"] - ar_target),
            "Customer invoice collections",
            "AR-AGING",
        )
        ap_target = o["payables"] + sum(alloc(c["payables"] - o["payables"], [1] * 12)[:month])
        ledger.cash(
            month,
            "2000",
            -ledger.balances["2000"] - ap_target,
            "Payroll and supplier disbursements",
            "AP-SETTLEMENT",
        )
        for segment, plan in segments.items():
            ledger.cash(
                month,
                "1400",
                alloc(plan["sustaining_capex"], [1] * 12)[month - 1],
                "Sustaining fixed-asset additions",
                f"CAPEX-{segment}",
                segment,
                "INVESTING",
            )
        ledger.pair(
            month,
            "5300",
            "1490",
            alloc(c["ppe_depreciation"], [1] * 12)[month - 1],
            "PPE depreciation",
            "FIXED-ASSET-2025",
        )
        ledger.pair(
            month,
            "5300",
            "1590",
            alloc(c["lease_rou_depreciation"], [1] * 12)[month - 1],
            "Finance lease ROU depreciation",
            "LEASE-2025",
        )
        interest = sum(
            alloc(c[k], [1] * 12)[month - 1]
            for k in ["term_interest", "revolver_interest", "lease_interest"]
        )
        ledger.cash(
            month, "5400", interest, "Interest paid under preclose credit facilities", "DEBT-2025"
        )
        if month in [3, 6, 9, 12]:
            ledger.cash(
                month,
                "2400",
                alloc(c["term_principal"], [1] * 4)[month // 3 - 1],
                "Quarterly term principal",
                "DEBT-2025",
                cash_flow="FINANCING",
            )
        ledger.cash(
            month,
            "2600",
            alloc(c["lease_principal"], [1] * 12)[month - 1],
            "Finance lease principal",
            "LEASE-2025",
            cash_flow="FINANCING",
        )
        if month == 12:
            sweep = ledger.balances["1000"] - c["cash_target"]
            assert sweep >= 0
            ledger.cash(
                month,
                "3200",
                sweep,
                "Declared ordinary surplus-cash owner distribution",
                "2025-DIVIDEND-POLICY",
                cash_flow="FINANCING",
            )
        monthly_summary.append(dict(ledger.summary(), through_month=month))
    return ledger, monthly_summary


def interface_schedules(operations):
    interface = operations["interface"]
    rates = {r["commodity"]: r for r in interface["rates"]}
    normalized, invoices = [], []
    for commodity, rate in rates.items():
        revenue = (
            rate["rail_rate"]
            + rate["terminal_rate"]
            + rate["truck_legs_per_car"] * rate["dray_rate"]
        )
        cost = (
            rate["rail_unit_cost"]
            + rate["terminal_unit_cost"]
            + rate["truck_legs_per_car"] * rate["dray_unit_cost"]
        )
        volume = rate["normalized_billable_cars"]
        normalized.append(
            {
                "commodity": commodity,
                "cars": volume,
                "revenue_per_car_usd": revenue,
                "variable_cost_per_car_usd": cost,
                "revenue_usd": volume * revenue,
                "variable_cost_usd": volume * cost,
                "external_linehaul_usd": volume * rate["external_linehaul_per_car"],
            }
        )
    for period in interface["monthly_2026"]:
        for commodity, cars in period["carloads"].items():
            if not cars:
                continue
            rate = rates[commodity]
            for segment, revenue, cost in [
                ("BST", rate["rail_rate"], rate["rail_unit_cost"]),
                ("TERMINALS", rate["terminal_rate"], rate["terminal_unit_cost"]),
                (
                    "TRUCKING",
                    rate["truck_legs_per_car"] * rate["dray_rate"],
                    rate["truck_legs_per_car"] * rate["dray_unit_cost"],
                ),
            ]:
                invoices.append(
                    {
                        "invoice_id": f"IC-{period['month']}-{commodity}-{segment}",
                        "period": period["month"],
                        "month": int(period["month"][-2:]),
                        "seller_entity": "BST" if segment == "BST" else "ARU",
                        "buyer_entity": "RWH",
                        "segment": segment,
                        "commodity": commodity,
                        "cars": cars,
                        "revenue_usd": cars * revenue,
                        "external_variable_cost_usd": cars * cost,
                        "payment_terms": (
                            "Payment in following calendar month; December payable settled "
                            "January 2027"
                        ),
                        "period_role": period_role(2026, int(period["month"][-2:])),
                        "fact_state": "LOCKED_DERIVED_IMPLEMENTATION",
                    }
                )
    return normalized, invoices


def acquisition(source, history):
    t = source["transaction"]
    closing = history.summary()
    net_book_after_sweep = (
        closing["equity_including_current_income_usd"] - t["excess_cash_distribution"]
    )
    book_ppe = history.balances["1400"] + history.balances["1490"]
    fair_ppe = sum(a["fair_value"] for a in source["ppa_assets"])
    deferred_tax_asset = usd(
        Decimal(t["environment_reserve"] + t["claim_reserve"])
        * Decimal(str(source["forecast_2026"]["tax_rate_pct"]))
        / 100
    )
    net_identifiable = net_book_after_sweep + fair_ppe - book_ppe + deferred_tax_asset
    goodwill = t["buyer_consideration"] - net_identifiable
    assert goodwill >= 0
    tax_policy = source["acquisition_tax_allocation"]
    assumed_tax_liabilities = -sum(
        history.balances[a] for a in tax_policy["recognized_assumed_liability_accounts"]
    )
    deferred_assumed_liabilities = -sum(
        history.balances[a] for a in tax_policy["deferred_assumed_liability_accounts"]
    )
    tax_other_assets = {
        "cash": t["retained_cash"],
        "receivables_net": history.balances["1100"],
        "inventory": history.balances["1200"],
        "prepaids": history.balances["1300"],
        "owned_ppe": fair_ppe,
        "tax_owned_finance_lease_assets": t["retained_leases"],
    }
    tax_stock_basis = (
        t["buyer_consideration"] + tax_policy["additional_capitalized_stock_basis_usd"]
    )
    modeled_agub = tax_stock_basis + assumed_tax_liabilities
    tax_goodwill = modeled_agub - sum(tax_other_assets.values())
    if not 0 < tax_goodwill <= goodwill:
        raise ValueError(
            "Changed tax allocation requires reconsidering initial goodwill tax accounting"
        )
    sources = t["new_debt"] + t["parent_equity_before_fees"]
    uses = t["buyer_consideration"] + t["existing_term_revolver_refinance"]
    assert sources == uses
    nwc = (
        history.balances["1100"]
        + history.balances["1200"]
        + history.balances["1300"]
        + history.balances["2000"]
        + history.balances["2100"]
    )
    assert nwc == t["working_capital_peg"]
    return {
        "close_date": t["close"],
        "net_book_equity_after_excess_cash_distribution_usd": net_book_after_sweep,
        "book_ppe_net_usd": book_ppe,
        "fair_ppe_usd": fair_ppe,
        "fair_ppe_step_up_usd": fair_ppe - book_ppe,
        "identifiable_net_assets_before_refinancing_usd": net_identifiable,
        "stock_consideration_usd": t["buyer_consideration"],
        "goodwill_usd": goodwill,
        "tax_goodwill_basis_usd": tax_goodwill,
        "initial_book_goodwill_excess_over_tax_usd": goodwill - tax_goodwill,
        "tax_allocation": {
            "stock_tax_basis_usd": tax_stock_basis,
            "recognized_assumed_liabilities_usd": assumed_tax_liabilities,
            "deferred_assumed_liabilities_usd": deferred_assumed_liabilities,
            "modeled_agub_usd": modeled_agub,
            "other_tax_asset_bases_usd": tax_other_assets,
            "tax_goodwill_basis_usd": tax_goodwill,
            "initial_goodwill_dtl_usd": 0,
            "policy": tax_policy,
        },
        "close_sources_before_fees_usd": sources,
        "close_uses_before_fees_usd": uses,
        "deferred_tax_asset_usd": deferred_tax_asset,
        "deferred_tax_basis_usd": t["environment_reserve"] + t["claim_reserve"],
        "deferred_tax_assumptions": (
            "Environmental/claim book accruals have no current deduction or included "
            "assumed-liability tax basis before economic performance. Settlement may "
            "increase deemed-acquisition asset basis recoverable through later tax "
            "amortization rather than create an immediate deduction. At the 25% "
            "scenario rate, full future DTA realization is assumed from "
            "positive forecast taxable income; no 2026 settlement/reversal of these "
            "ARU reserves. Other deemed-acquisition asset book/tax bases assumed "
            "aligned; debt issue costs amortized identically in this simplified "
            "scenario."
        ),
        "new_debt_upstream_acquisition_distribution_usd": t["new_debt"]
        - t["existing_term_revolver_refinance"],
        "parent_cash_before_fees_usd": t["parent_equity_before_fees"],
        "parent_cash_including_fees_usd": t["parent_equity_before_fees"]
        + t["transaction_expense"]
        + t["debt_issuance_cost"],
        "working_capital_usd": nwc,
        "working_capital_true_up_usd": nwc - t["working_capital_peg"],
        "tax_basis_boundary": (
            "Synthetic book-tax step-up alignment is conditional on the tax memo; no "
            "audited deferred tax conclusion."
        ),
        "goodwill_method": (
            "Residual of consideration over disclosed fair identifiable net assets; "
            "not an operating income or cash plug."
        ),
    }


def acquisition_opening(source, history, ppa):
    t = source["transaction"]
    ledger = Ledger("ARU_GROUP", 2026)
    balances = {
        a: v for a, v in history.balances.items() if ACCOUNTS[a][1] in ["asset", "liability"]
    }
    balances.update(
        {
            "1000": t["retained_cash"],
            "1400": ppa["fair_ppe_usd"],
            "1490": 0,
            "1500": t["retained_leases"],
            "1590": 0,
            "1600": ppa["goodwill_usd"],
            "1700": t["debt_issuance_cost"],
            "1800": ppa["deferred_tax_asset_usd"],
            "2400": -t["new_debt"],
            "2500": 0,
            "3000": -t["parent_equity_before_fees"] - t["debt_issuance_cost"],
        }
    )
    ledger.entry(
        0,
        "Acquisition pushdown opening balance sheet after financing and fees",
        list(balances.items()),
        "PPA-2026-01-07",
    )
    ledger.summary()
    return ledger


def build_2026(source, operations, history, monthly, payroll, invoices, ppa):
    ledger = acquisition_opening(source, history, ppa)
    opening_tb = ledger.trial_balance()
    t, f = source["transaction"], source["forecast_2026"]
    if t["close"] != "2026-01-07" or f["interface_in_service"] != "2026-07-07":
        raise ValueError("This dated successor requires January 7 close and July 7 commissioning")
    if t["new_revolver_draw"] != 0:
        raise ValueError("Revolver draws require a new explicit borrowing/repayment schedule")
    price_factor = 1 + Decimal(str(f["external_price_increase_pct"])) / 100
    volume_factor = 1 + Decimal(str(f["external_volume_growth_pct"])) / 100
    revenue_factor = price_factor * volume_factor
    cost_factor = 1 + Decimal(str(f["external_cash_opex_inflation_pct"])) / 100
    close_date = date.fromisoformat(t["close"])
    first_principal = date.fromisoformat(t["new_debt_first_payment"])
    if first_principal.year != 2026 or first_principal < close_date:
        raise ValueError("The declared first principal payment must follow close in 2026")
    if f["goodwill_tax_amortization_months"] != 180:
        raise ValueError("The intended section 197 case requires 180-month amortization")
    consult_end = date.fromisoformat(t["seller_consulting_end"])
    consulting_service_days = (consult_end - close_date).days
    owned_day_weights = [
        calendar.monthrange(2026, m)[1] - (6 if m == 1 else 0) for m in range(1, 13)
    ]
    retention_total = usd(Decimal(t["retention_pool"]) * sum(owned_day_weights) / 365)
    retention_schedule = alloc(retention_total, owned_day_weights)
    lease_principal_total = usd(
        Decimal(f["debt_lease_annual_principal"]) * sum(owned_day_weights) / 365
    )
    lease_principal_schedule = alloc(lease_principal_total, owned_day_weights)
    consulting_weights = []
    for m in range(1, 13):
        start = max(date(2026, m, 1), close_date)
        end = date(2027, 1, 1) if m == 12 else date(2026, m + 1, 1)
        consulting_weights.append(max((min(end, consult_end) - start).days, 0))
    consulting_total = usd(
        Decimal(t["seller_consulting_total"]) * sum(consulting_weights) / consulting_service_days
    )
    consulting_schedule = alloc(consulting_total, consulting_weights)
    nwc = f["nwc_forecast_drivers"]
    history_cost = sum(s["opex"] for s in source["segment_baseline"].values())
    history_dda = history.balances["5300"]
    history_interest = history.balances["5400"]
    funding, monthly_results, asset_schedule, debt_schedule, tax_schedule = [], [], [], [], []
    cumulative_pretax = 0
    prior_current_tax = 0
    prior_deferred_tax = 0
    prior_loss_tax_asset = 0
    fair_dda = sum(
        Decimal(a["fair_value"]) / a["useful_life_years"]
        for a in source["ppa_assets"]
        if a["useful_life_years"]
    )
    catchup_life = Decimal(f["catchup_composite_life_years"])
    cumulative_sustaining = 0
    cumulative_catchup = 0
    previous_ic = 0
    stub_revenue = sum(
        usd(Decimal(r["revenue_usd"]) * revenue_factor)
        - usd(Decimal(usd(Decimal(r["revenue_usd"]) * revenue_factor)) * 25 / 31)
        for r in monthly
        if r["month"] == 1
    )
    stub_cash_cost = usd(Decimal(history_cost) * cost_factor / 12 * 6 / 31)
    stub_dda = usd(Decimal(history_dda) / 12 * 6 / 31)
    stub_interest = usd(Decimal(history_interest) / 12 * 6 / 31)
    stub_profit = stub_revenue - stub_cash_cost - stub_dda - stub_interest
    stub = {
        "period_from": "2026-01-01",
        "period_through": "2026-01-06",
        "economic_close": "2026-01-07T00:00:00-07:00",
        "record_role": "SYNTHETIC_MANAGEMENT_CLOSING_BRIDGE_NOT_FEDERAL_TAX_PERIOD",
        "revenue_usd": stub_revenue,
        "cash_opex_usd": stub_cash_cost,
        "depreciation_usd": stub_dda,
        "interest_usd": stub_interest,
        "net_income_usd": stub_profit,
        "replacement_capex_usd": stub_dda,
        "ordinary_preclose_profit_distribution_usd": max(stub_profit, 0),
        "seller_preclose_liquidity_contribution_usd": max(-stub_profit, 0),
        "cash_change_usd": stub_revenue - stub_cash_cost - stub_interest - stub_dda - stub_profit,
        "nwc_change_usd": 0,
        "net_asset_change_usd": 0,
        "boundary": (
            "Cash-settled management stub: replacement capital equals depreciation; "
            "seller owners fund a winter operating loss or receive any profit under "
            "an explicit synthetic cash-maintenance policy. Owner transfers are "
            "separate from transaction consideration. Federal deemed-sale and "
            "short-year rules are addressed separately in the tax memo."
        ),
    }
    assert stub["cash_change_usd"] == 0
    for month in range(1, 13):
        days = calendar.monthrange(2026, month)[1]
        owned_days = days - 6 if month == 1 else days
        owned = Decimal(owned_days) / days
        opening_term = -ledger.balances["2400"]
        opening_lease = -ledger.balances["2600"]
        for row in monthly:
            if row["month"] == month:
                full = usd(Decimal(row["revenue_usd"]) * revenue_factor)
                amount = usd(Decimal(full) * owned)
                ledger.pair(
                    month,
                    "1100",
                    "4000",
                    amount,
                    "External customer invoice under source price and volume indices",
                    row["contract_id"],
                    row["segment"],
                )
        for segment, plan in source["segment_baseline"].items():
            pay = usd(Decimal(payroll[segment]) * cost_factor / 12 * owned)
            external = plan["opex"] - plan["shared_allocation"]
            other = usd(Decimal(external - payroll[segment]) * cost_factor / 12 * owned)
            ledger.pair(
                month,
                "5000",
                "2000",
                pay,
                "2026 loaded payroll under source cost index and unchanged census",
                "PAYROLL-2026",
                segment,
            )
            ledger.pair(
                month,
                "5100",
                "2000",
                other,
                "External suppliers under source cost index",
                "OPEX-2026",
                segment,
            )
            if segment != "ARU":
                amount = usd(Decimal(plan["shared_allocation"]) * cost_factor / 12 * owned)
                ledger.pair(
                    month,
                    "5900",
                    "2100",
                    amount,
                    "Shared services allocated",
                    "ALLOC-2026",
                    segment,
                )
                ledger.pair(
                    month, "2100", "5900", amount, "Shared services recovered", "ALLOC-2026", "ARU"
                )
        for key, account, change in [
            ("inventory", "1200", nwc["inventory_increase"]),
            ("prepaids", "1300", nwc["prepaids_increase"]),
        ]:
            ledger.pair(
                month,
                account,
                "2000",
                alloc(change, [1] * 12)[month - 1],
                "Forecast working capital purchases",
                f"WC26-{key}",
            )
        accrued = alloc(nwc["operating_accrual_increase"], [1] * 12)[month - 1]
        ledger.pair(month, "2000", "2100", accrued, "Operating accrual growth", "WC26-ACCRUAL")
        ar_target = history.balances["1100"] + sum(
            alloc(nwc["receivables_increase"], [1] * 12)[:month]
        )
        ledger.cash(
            month,
            "1100",
            -(ledger.balances["1100"] - ar_target),
            "External invoice collections",
            "AR26",
        )
        ap_target = -history.balances["2000"] + sum(
            alloc(nwc["payables_increase"], [1] * 12)[:month]
        )
        ledger.cash(
            month,
            "2000",
            -ledger.balances["2000"] - ap_target,
            "Payroll/supplier settlement",
            "AP26",
        )
        current_ic = 0
        for row in invoices:
            if row["month"] == month:
                current_ic += row["revenue_usd"]
                ledger.pair(
                    month,
                    "1150",
                    "4100",
                    row["revenue_usd"],
                    "Red Wash service invoice",
                    row["invoice_id"],
                    row["segment"],
                )
                ledger.cash(
                    month,
                    "5200",
                    row["external_variable_cost_usd"],
                    "Interface physical cost-to-serve",
                    row["invoice_id"],
                    row["segment"],
                )
        if previous_ic:
            ledger.cash(
                month, "1150", -previous_ic, "Prior-month Red Wash invoice settled", "IC-PAYMENT"
            )
        previous_ic = current_ic
        if month >= 7:
            for key, segment in [
                ("rail", "BST"),
                ("terminal", "TERMINALS"),
                ("trucking", "TRUCKING"),
            ]:
                ledger.cash(
                    month,
                    "5200",
                    operations["interface"]["fixed_cost_by_segment"][key] // 12,
                    "Interface standby/insurance/maintenance/compliance",
                    "IC-FIXED",
                    segment,
                )
        if month == 6:
            ledger.cash(
                month,
                "5200",
                operations["interface"]["commissioning_expense_2026_usd"],
                "Noncapital commissioning and training",
                "IC-COMMISSION",
                "TERMINALS",
            )
        retention = retention_schedule[month - 1]
        ledger.pair(
            month,
            "5700",
            "2110",
            retention,
            "Retention compensation accrued by service days",
            "RETENTION-POOL",
        )
        if month == 7:
            ledger.cash(
                month,
                "2110",
                usd(Decimal(t["retention_pool"]) / 2),
                "Six-month retention installment paid July 7",
                "RETENTION-PAYMENT",
            )
        consult = consulting_schedule[month - 1]
        if consult:
            ledger.cash(
                month,
                "5700",
                consult,
                "Seller knowledge-transfer consulting, no operating authority",
                "TOLMAN-CONSULTING",
            )
        is_payment_month = (
            month >= first_principal.month and (month - first_principal.month) % 3 == 0
        )
        principal = min(t["new_debt_quarterly_principal"], opening_term) if is_payment_month else 0
        interest_base = Decimal(opening_term) * owned_days - Decimal(principal) * max(
            days - first_principal.day + 1, 0
        )
        interest = usd(interest_base * Decimal(str(t["new_debt_rate_pct"])) / 100 / 365)
        lease_principal = lease_principal_schedule[month - 1]
        lease_interest = usd(
            (Decimal(opening_lease) - Decimal(lease_principal) / 2)
            * Decimal(str(f["lease_interest_pct"]))
            / 100
            * owned_days
            / 365
        )
        commitment = usd(
            Decimal(t["new_revolver_capacity"])
            * Decimal(str(t["new_revolver_undrawn_commitment_fee_pct"]))
            / 100
            * owned_days
            / 365
        )
        ledger.cash(
            month,
            "5400",
            interest + lease_interest + commitment,
            "Term/lease interest and undrawn revolver fee",
            "DEBT26",
        )
        amort = usd(
            Decimal(t["debt_issuance_cost"]) / t["debt_issuance_amortization_months"] * owned
        )
        ledger.pair(
            month, "5400", "1700", amort, "Debt issuance cost amortization", "DEBT26-ISSUANCE"
        )
        ledger.cash(
            month,
            "2400",
            principal,
            "Acquisition debt principal due seventh of quarter",
            "DEBT26",
            cash_flow="FINANCING",
        )
        ledger.cash(
            month,
            "2600",
            lease_principal,
            "Finance lease principal",
            "LEASE26",
            cash_flow="FINANCING",
        )
        sustaining = alloc(f["sustaining_capex"], [1] * 12)[month - 1]
        catchup = dict(
            zip(
                f["catchup_months"],
                alloc(f["catchup_capex"], [1] * len(f["catchup_months"])),
                strict=True,
            )
        ).get(month, 0)
        interface = dict(
            zip(
                f["phase1_spend_months"],
                alloc(f["aru_interface_capex"], [1] * len(f["phase1_spend_months"])),
                strict=True,
            )
        ).get(month, 0)
        earmarked = catchup + interface
        if earmarked:
            ledger.cash(
                month,
                "3000",
                -earmarked,
                "Parent equity for catch-up and Phase 1 infrastructure",
                "CAPITAL-FUNDING",
                cash_flow="FINANCING",
            )
            funding.append(
                {
                    "month": month,
                    "recipient": "ARU",
                    "purpose": "catchup" if not interface else "catchup_and_interface",
                    "amount_usd": earmarked,
                }
            )
        ledger.cash(
            month,
            "1400",
            sustaining + catchup + interface,
            "Sustaining/catch-up/Phase 1 capital additions",
            "CAPEX26",
            cash_flow="INVESTING",
        )
        lease_dda = usd(Decimal(f["lease_rou_annual_depreciation"]) * owned_days / 365)
        dda = usd(fair_dda * owned_days / 365) + lease_dda
        new_dda = usd(
            Decimal(cumulative_sustaining) / f["sustaining_composite_life_years"] / 12
            + Decimal(cumulative_catchup) / catchup_life / 12
        )
        phase_dda = (
            usd(Decimal(f["aru_interface_capex"]) / f["interface_life_years"] / 12)
            if month >= 7
            else 0
        )
        # Lease component is kept separate from owned PPE.
        ledger.pair(
            month,
            "5300",
            "1490",
            dda - lease_dda + new_dda + phase_dda,
            "PPE depreciation and completed program assets",
            "FIXED26",
        )
        ledger.pair(
            month, "5300", "1590", lease_dda, "Retained finance lease ROU depreciation", "LEASE26"
        )
        cumulative_sustaining += sustaining
        cumulative_catchup += catchup
        pre_tax = -sum(
            r["signed_usd"]
            for r in ledger.rows
            if r["month"] == month and ACCOUNTS[r["account"]][1] in ["revenue", "expense"]
        )
        cumulative_pretax += pre_tax
        tax_rate = Decimal(str(f["tax_rate_pct"])) / 100
        goodwill_deduction = usd(
            Decimal(ppa["tax_goodwill_basis_usd"]) * month / f["goodwill_tax_amortization_months"]
        )
        cumulative_taxable_income = cumulative_pretax - goodwill_deduction
        current_tax = usd(Decimal(max(cumulative_taxable_income, 0)) * tax_rate)
        ledger.pair(
            month,
            "5500",
            "2700",
            current_tax - prior_current_tax,
            "Cumulative annual current tax, including tax-goodwill amortization",
            "TAX26-CURRENT",
        )
        deferred_tax = usd(Decimal(goodwill_deduction) * tax_rate)
        ledger.pair(
            month,
            "5501",
            "2250",
            deferred_tax - prior_deferred_tax,
            "Deferred tax on section 197 goodwill tax/book basis difference",
            "TAX26-DEFERRED",
        )
        loss_tax_asset = usd(Decimal(max(-cumulative_taxable_income, 0)) * tax_rate)
        ledger.pair(
            month,
            "1801",
            "5501",
            loss_tax_asset - prior_loss_tax_asset,
            "Interim modeled tax-loss asset supported by positive annual forecast",
            "TAX26-INTERIM-LOSS",
        )
        current_tax_paid = (
            max(-ledger.balances["2700"], 0) if month in f["modeled_tax_cash_payment_months"] else 0
        )
        ledger.cash(
            month,
            "2700",
            current_tax_paid,
            "Quarter-end estimated income-tax payment; overpayments carried, no instant refund",
            "TAX26-PAYMENT",
        )
        tax_schedule.append(
            {
                "month": month,
                "book_pretax_income_usd": pre_tax,
                "cumulative_book_pretax_income_usd": cumulative_pretax,
                "cumulative_goodwill_tax_deduction_usd": goodwill_deduction,
                "cumulative_taxable_income_usd": cumulative_taxable_income,
                "current_tax_expense_usd": current_tax - prior_current_tax,
                "deferred_tax_expense_usd": deferred_tax
                - prior_deferred_tax
                - (loss_tax_asset - prior_loss_tax_asset),
                "current_tax_cash_paid_usd": current_tax_paid,
                "current_tax_settlement_signed_balance_usd": ledger.balances["2700"],
                "deferred_tax_asset_reserves_usd": ledger.balances["1800"],
                "deferred_tax_asset_interim_loss_usd": ledger.balances["1801"],
                "deferred_tax_liability_goodwill_usd": -ledger.balances["2250"],
                "goodwill_tax_basis_usd": ppa["tax_goodwill_basis_usd"] - goodwill_deduction,
                "goodwill_book_basis_usd": ppa["goodwill_usd"],
                "initial_goodwill_excess_excluded_from_opening_dtl_usd": ppa[
                    "initial_book_goodwill_excess_over_tax_usd"
                ],
            }
        )
        prior_current_tax = current_tax
        prior_deferred_tax = deferred_tax
        prior_loss_tax_asset = loss_tax_asset
        shortage = max(f["retained_cash_floor"] - ledger.balances["1000"], 0)
        if shortage:
            ledger.cash(
                month,
                "3000",
                -shortage,
                "Additional parent liquidity equity to preserve cash floor",
                "LIQUIDITY26",
                cash_flow="FINANCING",
            )
            funding.append(
                {
                    "month": month,
                    "recipient": "ARU",
                    "purpose": "liquidity_floor",
                    "amount_usd": shortage,
                }
            )
        asset_schedule.append(
            {
                "month": month,
                "sustaining_additions_usd": sustaining,
                "catchup_additions_usd": catchup,
                "phase1_additions_usd": interface,
                "legacy_depreciation_usd": dda,
                "new_program_depreciation_usd": new_dda + phase_dda,
                "ppe_gross_usd": ledger.balances["1400"],
                "ppe_accumulated_depreciation_usd": -ledger.balances["1490"],
            }
        )
        debt_schedule.append(
            {
                "month": month,
                "opening_term_usd": opening_term,
                "term_principal_usd": principal,
                "term_interest_usd": interest,
                "closing_term_usd": -ledger.balances["2400"],
                "lease_principal_usd": lease_principal,
                "lease_interest_usd": lease_interest,
                "closing_lease_usd": -ledger.balances["2600"],
                "debt_issue_amortization_usd": amort,
                "deferred_debt_issue_cost_usd": ledger.balances["1700"],
                "revolver_draw_usd": 0,
            }
        )
        monthly_results.append(dict(ledger.summary(), through_month=month))
    if cumulative_taxable_income <= 0:
        raise ValueError("An annual tax-loss case requires a new DTA realization assessment")
    return (
        ledger,
        opening_tb,
        stub,
        monthly_results,
        funding,
        asset_schedule,
        debt_schedule,
        tax_schedule,
    )


def mine_selected(core):
    m, f, a = core["mine_2026"], core["finance_2026"], core["inventory_cost_assumptions_2026"]
    opening_cash = usd(
        Decimal(m["opening_finished_inventory_lb"])
        * Decimal(str(a["opening_finished_inventory_cash_cost_usd_lb"]))
    )
    opening_dda = usd(
        Decimal(m["opening_finished_inventory_lb"])
        * Decimal(str(a["opening_finished_inventory_dd_and_a_usd_lb"]))
    )
    produced_dda = usd(
        Decimal(
            core["transaction"]["operating_assets_usd"]
            + core["transaction"]["capitalized_rehabilitation_usd"]
        )
        * m["produced_u3o8_lb"]
        / core["resource_basis"]["recoverable_lb"]
    )
    units = m["opening_finished_inventory_lb"] + m["produced_u3o8_lb"]
    cash_cogs = usd(
        Decimal(opening_cash + f["cash_production_cost_incurred_usd"]) * m["sold_u3o8_lb"] / units
    )
    dda_cogs = usd(Decimal(opening_dda + produced_dda) * m["sold_u3o8_lb"] / units)
    fixed = sum(
        f[k]
        for k in [
            "production_mineral_taxes_usd",
            "royalties_usd",
            "freight_assay_handling_usd",
            "pale_sun_site_g_and_a_usd",
        ]
    )
    pretax = f["revenue_usd"] - cash_cogs - dda_cogs - fixed - f["aro_accretion_usd"]
    tax = usd(Decimal(max(pretax, 0)) * Decimal(str(a["income_tax_rate_pct"])) / 100)
    net = pretax - tax
    cfo = (
        net
        + dda_cogs
        + f["aro_accretion_usd"]
        - (f["cash_production_cost_incurred_usd"] - cash_cogs)
        - a["other_working_capital_use_usd"]
    )
    return {
        "opening_cash_inventory_usd": opening_cash,
        "opening_dda_inventory_usd": opening_dda,
        "produced_dda_usd": produced_dda,
        "cash_cogs_usd": cash_cogs,
        "dda_cogs_usd": dda_cogs,
        "pretax_income_usd": pretax,
        "income_tax_usd": tax,
        "net_income_usd": net,
        "operating_cash_flow_usd": cfo,
        "free_cash_flow_usd": cfo - f["sustaining_capex_usd"] - f["rehabilitation_capex_usd"],
    }


def closure_schedule(core, source):
    """Explicit timing calibration to the inherited liability, not a kill-study estimate."""
    acquired = Decimal(core["transaction"]["aro_assumed_usd"])
    rate = Decimal(str(core["closure"]["discount_pct"])) / 100
    inflation = Decimal(str(core["closure"]["inflation_pct"])) / 100
    days = (date(2026, 1, 1) - date.fromisoformat(core["transaction"]["close_date"])).days
    h2_accretion = usd(acquired * ((1 + rate) ** (Decimal(days) / 365) - 1))
    opening = int(acquired) + h2_accretion
    current = core["closure"]["current_cost_usd"]

    def factor(year):
        return ((1 + inflation) / (1 + rate)) ** (year - 2025)

    spec = source["aro_successor"]
    early_year = spec["calibrated_early_year"]
    terminal_year = spec["terminal_year"]
    fixed = {
        year: spec["minor_progressive_current_cost_per_year"]
        for year in range(2026, terminal_year)
        if year != early_year
    }
    fixed_pv = sum(Decimal(amount) * factor(year) for year, amount in fixed.items())
    remaining = current - sum(fixed.values())
    early = usd(
        (Decimal(opening) - fixed_pv - Decimal(remaining) * factor(terminal_year))
        / (factor(early_year) - factor(terminal_year))
    )
    assert 0 < early < remaining
    values = {**fixed, early_year: early, terminal_year: remaining - early}
    rows = []
    for year, current_cost in sorted(values.items()):
        years = year - 2025
        nominal = usd(Decimal(current_cost) * (1 + inflation) ** years)
        present = usd(Decimal(nominal) / (1 + rate) ** years)
        rows.append(
            {
                "year": year,
                "settlement_date": f"{year}-12-31",
                "current_cost_usd": current_cost,
                "inflated_cash_settlement_usd": nominal,
                "present_value_usd": present,
                "scope": "Final sealing, mill demolition, tailings cover and surveillance transfer"
                if year == 2039
                else "Progressive reclamation, water management and inactive-cell closure",
                "fact_state": "PROVISIONAL_ASSUMPTION",
                "method": (
                    "Timing calibrated to locked acquisition liability rolled forward; "
                    "independent engineering cost validation is not claimed."
                ),
            }
        )
    pv = sum(r["present_value_usd"] for r in rows)
    assert sum(r["current_cost_usd"] for r in rows) == current and abs(pv - opening) <= 3
    return {
        "acquisition_aro_usd": int(acquired),
        "acquisition_date": core["transaction"]["close_date"],
        "h2_2025_actual_365_days": days,
        "h2_2025_accretion_usd": h2_accretion,
        "opening_2026_aro_usd": opening,
        "2026_accretion_usd": usd(Decimal(opening) * rate),
        "2026_settlement_usd": rows[0]["inflated_cash_settlement_usd"],
        "schedule_present_value_usd": pv,
        "rounding_difference_usd": pv - opening,
        "current_cost_valuation_date": "2026-01-01",
        "current_cost_usd": current,
        "calibration_boundary": (
            "The original $16M 2026 opening remains in the historical simplified "
            "model. The integrated successor accrues the acquired $16M for 167 days "
            "before 2026. The $25M current-cost scenario is measured at 2026 "
            "opening; timing is calibrated to that carried liability, not "
            "independently measured engineering evidence."
        ),
    }, rows


def build_mine(source, core, invoices, operations):
    baseline = mine_selected(core)
    aro, closure_rows = closure_schedule(core, source)
    ledger = Ledger("RWH_PS", 2026)
    # This is an explicit successor opening scenario, not recovered historical TB.
    o = source["opening_red_wash_2026_scenario"]
    opening = {
        "1000": o["cash"],
        "1100": o["receivables"],
        "1200": baseline["opening_cash_inventory_usd"],
        "1210": baseline["opening_dda_inventory_usd"],
        "1300": o["prepaids"],
        "1400": o["ppe_net_before_2026"],
        "2000": -o["trade_payables"],
        "2200": -aro["opening_2026_aro_usd"],
        "2300": -o["other_liabilities"],
        "3000": -o["contributed_equity"],
        "3100": o["prior_repair_loss_before_h2_aro"] + aro["h2_2025_accretion_usd"],
    }
    ledger.entry(
        0,
        "Explicit synthetic successor opening scenario; not historical audited balance sheet",
        list(opening.items()),
        "RW-OPENING-SCENARIO",
    )
    f, a = core["finance_2026"], core["inventory_cost_assumptions_2026"]
    scenario = source["forecast_2026"]
    funding, monthly = [], []
    annual_ic = sum(r["revenue_usd"] for r in invoices)
    external_linehaul = sum(
        period["carloads"][rate["commodity"]] * rate["external_linehaul_per_car"]
        for period in operations["interface"]["monthly_2026"]
        for rate in operations["interface"]["rates"]
    )
    addon_dda = usd(
        Decimal(scenario["mine_interface_capex"]) / scenario["interface_life_years"] / 2
    )
    integrated_pretax = (
        baseline["pretax_income_usd"]
        - annual_ic
        - external_linehaul
        - addon_dda
        + scenario["mine_displaced_cost_credit"]
        - (aro["2026_accretion_usd"] - f["aro_accretion_usd"])
    )
    integrated_tax = usd(
        Decimal(max(integrated_pretax, 0)) * Decimal(str(a["income_tax_rate_pct"])) / 100
    )
    previous_ic = 0
    for month in range(1, 13):

        def share(total, current_month=month):
            return alloc(total, [1] * 12)[current_month - 1]

        ledger.pair(
            month,
            "1100",
            "4000",
            share(f["revenue_usd"]),
            "Selected contract book revenue; annual baseline allocated monthly",
            "RW-CONTRACT-2026",
            "RWH",
        )
        ledger.cash(
            month,
            "1100",
            -share(f["revenue_usd"] - a["other_working_capital_use_usd"]),
            "Collections net of disclosed other working-capital use allocated to AR",
            "RW-AR-ASSUMPTION",
            "RWH",
        )
        ledger.pair(
            month,
            "1200",
            "2000",
            share(f["cash_production_cost_incurred_usd"]),
            "Selected production cost incurred",
            "RW-COST",
            "RWH",
        )
        ledger.cash(
            month,
            "2000",
            share(f["cash_production_cost_incurred_usd"]),
            "Production cost payments",
            "RW-COST",
            "RWH",
        )
        ledger.pair(
            month,
            "1210",
            "1490",
            share(baseline["produced_dda_usd"]),
            "Selected production DD&A capitalized into inventory",
            "RW-DDA",
            "RWH",
        )
        ledger.pair(
            month,
            "5100",
            "1200",
            share(baseline["cash_cogs_usd"]),
            "Weighted-average cash cost released to sales",
            "RW-COGS",
            "RWH",
        )
        ledger.pair(
            month,
            "5300",
            "1210",
            share(baseline["dda_cogs_usd"]),
            "Weighted-average DD&A released to sales",
            "RW-COGS",
            "RWH",
        )
        for key in [
            "production_mineral_taxes_usd",
            "royalties_usd",
            "freight_assay_handling_usd",
            "pale_sun_site_g_and_a_usd",
        ]:
            ledger.cash(
                month,
                "5100",
                share(f[key]),
                key.replace("_", " "),
                "RW-FINANCE-SELECTED",
                "PS" if key == "pale_sun_site_g_and_a_usd" else "RWH",
            )
        ledger.pair(
            month,
            "5600",
            "2200",
            share(aro["2026_accretion_usd"]),
            "Integrated ARO accretion on acquisition-date carryforward",
            "RW-ARO",
            "RWH",
        )
        if month == 12:
            ledger.cash(
                month,
                "2200",
                aro["2026_settlement_usd"],
                "Progressive reclamation settlement reduces ARO; separate from capex",
                "RW-CLOSURE-CASH",
                "RWH",
            )
        current_ic = 0
        for row in invoices:
            if row["month"] == month:
                current_ic += row["revenue_usd"]
                ledger.pair(
                    month,
                    "5150",
                    "2150",
                    row["revenue_usd"],
                    "ARU/BS&T logistics invoice; incremental scenario",
                    "IC-RECIPROCAL:" + row["invoice_id"],
                    "RWH",
                )
        if previous_ic:
            ledger.cash(
                month,
                "2150",
                previous_ic,
                "Prior-month intercompany invoice payment",
                "IC-PAYMENT",
                "RWH",
            )
        previous_ic = current_ic
        external = 0
        for period in operations["interface"]["monthly_2026"]:
            if int(period["month"][-2:]) == month:
                for rate in operations["interface"]["rates"]:
                    external += (
                        period["carloads"][rate["commodity"]] * rate["external_linehaul_per_car"]
                    )
        ledger.cash(
            month,
            "5200",
            external,
            "Origin-carrier linehaul directly paid outside ARU; provisional quoted scenario",
            "RW-EXTERNAL-LINEHAUL",
            "RWH",
        )
        if scenario["mine_displaced_cost_credit"]:
            ledger.cash(
                month,
                "5200",
                -share(scenario["mine_displaced_cost_credit"]),
                "Explicit scenario avoided external cost; requires supporting evidence",
                "RW-AVOIDED-COST-SENSITIVITY",
                "RWH",
            )
        if month >= 7:
            ledger.pair(
                month,
                "5300",
                "1490",
                alloc(addon_dda, [1] * 6)[month - 7],
                "New mine-interface asset depreciation",
                "RW-PHASE1-DDA",
                "RWH",
            )
        tax = share(integrated_tax)
        ledger.cash(
            month,
            "5500",
            tax,
            "Integrated scenario income tax, 18% modeled assumption",
            "RW-TAX",
            "RWH",
        )
        capex = share(f["sustaining_capex_usd"] + f["rehabilitation_capex_usd"])
        interface = dict(
            zip(
                scenario["phase1_spend_months"],
                alloc(scenario["mine_interface_capex"], [1] * len(scenario["phase1_spend_months"])),
                strict=True,
            )
        ).get(month, 0)
        ledger.cash(
            month,
            "1400",
            capex + interface,
            "Selected capital plus separately identified mine interface capital",
            "RW-CAPEX",
            "RWH",
            "INVESTING",
        )
        shortage = max(scenario["mine_retained_cash_floor"] - ledger.balances["1000"], 0)
        if shortage:
            ledger.cash(
                month,
                "3000",
                -shortage,
                "Parent equity through Pale Sun to fund explicit cash deficit",
                "RW-EQUITY",
                "RWH",
                "FINANCING",
            )
            funding.append(
                {
                    "month": month,
                    "recipient": "RWH_VIA_PS",
                    "purpose": "mine_selected_deficit_and_incremental_interface",
                    "amount_usd": shortage,
                }
            )
        monthly.append(dict(ledger.summary(), through_month=month))
    assert ledger.summary()["net_income_usd"] == integrated_pretax - integrated_tax
    bridge = {
        "selected_baseline": baseline,
        "integrated_aro": aro,
        "intercompany_invoices_usd": annual_ic,
        "external_origin_linehaul_usd": external_linehaul,
        "new_interface_depreciation_usd": addon_dda,
        "displaced_external_cost_credit_usd": scenario["mine_displaced_cost_credit"],
        "integrated_pretax_income_usd": integrated_pretax,
        "integrated_income_tax_usd": integrated_tax,
        "integrated_net_income_usd": integrated_pretax - integrated_tax,
        "new_mine_capex_usd": scenario["mine_interface_capex"],
        "incremental_scenario_boundary": (
            "Conservative changed operating scenario with zero claimed "
            "displaced-cost credit, not an assertion of duplicate actual external "
            "purchases. Original selected model retained separately."
        ),
        "opening_balance_boundary": (
            "Derived synthetic opening position: $44.3125M contributed capital and "
            "$3M prior retained loss; includes $5.3125M additional modeled H2 2025 "
            "working-capital funding beyond $28M purchase plus $11M stabilization. "
            "This is an explicit model assumption, not an asserted recovered payment."
        ),
    }
    return ledger, monthly, funding, bridge, closure_rows


def expense_support(source, payroll):
    rows = []
    # Locked budgets are never claimed to be independent supplier quotations.
    for segment, plan in source["segment_baseline"].items():
        external = plan["opex"] - plan["shared_allocation"]
        remainder = external - payroll[segment]
        weights = {
            "BST": [20, 25, 18, 17, 20],
            "TERMINALS": [25, 25, 20, 15, 15],
            "TRUCKING": [35, 25, 20, 10, 10],
            "WAREHOUSE": [35, 20, 15, 15, 15],
            "ARU": [25, 25, 20, 20, 10],
        }[segment]
        titles = [
            "Purchased materials and fuel",
            "Contract equipment maintenance/services",
            "Property occupancy and utilities",
            "Insurance/environment and regulatory cost",
            "Other external operating services",
        ]
        for i, (title, cost) in enumerate(zip(titles, alloc(remainder, weights), strict=True), 1):
            rows.append(
                {
                    "expense_id": f"OPEX-{segment}-{i}",
                    "segment": segment,
                    "cost_category": title,
                    "annual_service_units": 12,
                    "unit": "monthly_service_budget",
                    "annual_cost_usd": cost,
                    "monthly_average_usd": str(Decimal(cost) / 12),
                    "state": "PROVISIONAL_ASSUMPTION",
                    "source": (
                        "Locked segment envelope less census-derived payroll and explicit "
                        "shared-service allocation"
                    ),
                    "limitation": (
                        "Transparent allocation of locked budget; no fabricated supplier quote "
                        "or claim of independently validated cost engineering."
                    ),
                }
            )
    return rows


def rail_expense_class_support(source):
    functions = defaultdict(int)
    for employee in source["employees"]:
        if employee["segment"] == "BST":
            functions[employee["function"]] += employee["annual_salary_usd"] + usd(
                Decimal(employee["annual_salary_usd"])
                * employee["annual_employer_burden_pct"]
                / 100
            )
    mapping = source["rail_payroll_expense_class_mapping"]
    rows = []
    for category, amount in source["rail_opex_classes"].items():
        payroll = sum(
            value for function, value in functions.items() if mapping[function] == category
        )
        shared = (
            source["segment_baseline"]["BST"]["shared_allocation"]
            if category == "aru_shared_services"
            else 0
        )
        other = amount - payroll - shared
        if other < 0:
            raise ValueError(
                f"Rail expense class does not cover mapped payroll/allocation: {category}"
            )
        rows.append(
            {
                "year": 2025,
                "expense_class": category,
                "reported_opex_usd": amount,
                "census_payroll_usd": payroll,
                "shared_service_allocation_usd": shared,
                "external_nonpayroll_budget_usd": other,
                "state": "PROVISIONAL_ASSUMPTION",
                "basis": (
                    "Locked rail expense class decomposed into census payroll, shared services "
                    "and residual disclosed external budget; not independently observed "
                    "supplier cost."
                ),
            }
        )
    if sum(r["reported_opex_usd"] for r in rows) != source["segment_baseline"]["BST"]["opex"]:
        raise ValueError("Rail operating expense classes must reconcile to segment expense")
    return rows


def legal_book_views(source, history, aru, mine, mine_funding, invoices):
    """Explicit legal-entity closing books from a centralized treasury model.

    Operating invoices and payroll retain segment ownership. Shared asset/liability
    allocations and treasury settlements are disclosed case assumptions. The clearing
    balance represents funding, never revenue, and eliminates exactly at group level.
    """
    views, rows, reconciliations = [], [], []
    policy = source["legal_book_policy"]
    shares = policy["bst_balance_allocation_pct"]
    account_ownership = {
        "1000": "cash",
        "1100": "receivables",
        "1200": "inventory",
        "1300": "prepaids",
        "1400": "owned_ppe",
        "1490": "owned_ppe",
        "1500": "leased_equipment",
        "1590": "leased_equipment",
        "2000": "payables",
        "2100": "operating_accruals",
        "2600": "leased_equipment",
    }
    ratios = {
        account: Decimal(str(shares[key])) / 100 for account, key in account_ownership.items()
    }
    ratios.update(
        {
            "2200": Decimal(policy["bst_environment_reserve"])
            / source["transaction"]["environment_reserve"],
            "2300": Decimal(policy["bst_claim_reserve"]) / source["transaction"]["claim_reserve"],
            "1800": Decimal(policy["bst_deferred_tax_asset"]) / aru.balances["1800"],
        }
    )
    if any(not 0 <= share <= 1 for share in ratios.values()):
        raise ValueError("Legal ownership allocation must remain between zero and 100 percent")
    for group in [history, aru]:
        initial = defaultdict(int)
        for row in group.rows:
            if row["month"] == 0:
                initial[row["account"]] += row["signed_usd"]
        initial_owned = {
            a: usd(Decimal(v) * ratios.get(a, 0))
            for a, v in initial.items()
            if ACCOUNTS[a][1] in ["asset", "liability"]
        }
        bst_capital = sum(initial_owned.values())
        child = Ledger("BST", group.year)
        bst = {
            a: usd(Decimal(v) * ratios.get(a, 0))
            for a, v in group.balances.items()
            if ACCOUNTS[a][1] in ["asset", "liability"]
        }
        for a in [a for a in ACCOUNTS if ACCOUNTS[a][1] in ["revenue", "expense"]]:
            bst[a] = sum(
                r["signed_usd"] for r in group.rows if r["account"] == a and r["segment"] == "BST"
            )
        # These costs are paid/booked centrally and assigned by the disclosed ownership schedule.
        bst["5300"] = usd(
            Decimal(group.balances["5300"])
            * Decimal(str(policy["central_depreciation_to_bst_pct"]))
            / 100
        )
        bst["5400"] = usd(
            Decimal(group.balances["5400"])
            * Decimal(str(policy["central_financing_cost_to_bst_pct"]))
            / 100
        )
        bst["5500"] = (
            0  # Tax-sharing policy: loss-making rail book has no stand-alone current tax charge.
        )
        if group.year == 2026:
            retention_expense = sum(
                r["signed_usd"]
                for r in group.rows
                if r["account"] == "5700" and r["source_id"] == "RETENTION-POOL"
            )
            consulting_expense = sum(
                r["signed_usd"]
                for r in group.rows
                if r["account"] == "5700" and r["source_id"] == "TOLMAN-CONSULTING"
            )
            bst["5700"] = usd(
                Decimal(retention_expense)
                * source["transaction"]["retention_allocations"]["Seth Kettering"]
                / source["transaction"]["retention_pool"]
            ) + usd(
                Decimal(consulting_expense)
                * Decimal(str(policy["seller_consulting_to_bst_pct"]))
                / 100
            )
            bst["1150"] = sum(
                r["revenue_usd"] for r in invoices if r["month"] == 12 and r["segment"] == "BST"
            )
        bst["3000"] = -bst_capital
        bst["1180"] = -sum(bst.values())
        child.entry(
            0,
            (
                "Derived legal closing book with explicit ownership allocations and "
                "treasury reconciliation"
            ),
            list(bst.items()),
            "LEGAL-BOOK-ALLOCATION",
        )
        parent = Ledger("ARU", group.year)
        parent_values = {a: group.balances[a] - bst.get(a, 0) for a in group.balances}
        parent_values["1810"] = bst_capital
        # Remove child capital from parent subtraction: group capital belongs to ARU owners.
        parent_values["3000"] = group.balances["3000"]
        parent_values["1180"] = -bst["1180"]
        parent.entry(
            0,
            "ARU direct nonrail closing book, BS&T investment and reciprocal treasury account",
            list(parent_values.items()),
            "LEGAL-BOOK-ALLOCATION",
        )
        for account in ACCOUNTS:
            summed = parent.balances[account] + child.balances[account]
            expected = group.balances[account]
            if account == "1810":
                summed -= bst_capital
            if account == "3000":
                summed += bst_capital
            assert summed == expected, (group.year, account, summed, expected)
        for book in [child, parent]:
            view = book.summary()
            view["cash_flow_boundary"] = (
                "Closing legal-book allocation only; cash-flow statements are at ARU "
                "group level. Treasury current-account amounts are financing, not income."
            )
            views.append(view)
            rows.extend(book.trial_balance())
        reconciliations.append(
            {
                "year": group.year,
                "parent": "ARU",
                "subsidiary": "BST",
                "investment_and_subsidiary_opening_capital_eliminated_usd": bst_capital,
                "bst_treasury_current_account_signed_usd": bst["1180"],
                "aru_reciprocal_treasury_account_signed_usd": -bst["1180"],
                "post_elimination_difference_usd": 0,
                "rationale": (
                    "Explicit centralized treasury and shared-balance ownership allocation, "
                    "not asserted bank transfer evidence. Segment invoice/payroll costs are "
                    "preserved; centrally booked D&A and interest assigned under declared "
                    "policy."
                ),
            }
        )
    # The platform/site G&A allocation changes legal books without adding aggregate cost.
    platform_fee = source["legal_book_policy"]["pale_sun_annual_platform_service_fee"]
    rw = Ledger("RWH", 2026)
    rw_values = dict(mine.balances)
    rw_values["5100"] -= platform_fee
    rw_values["5150"] += platform_fee
    rw.entry(
        0,
        "Red Wash separate closing book; platform fee reclassifies selected G&A",
        list(rw_values.items()),
        "PS-RWH-SERVICE-ALLOCATION",
    )
    ps = Ledger("PS", 2026)
    investment = source["opening_red_wash_2026_scenario"]["contributed_equity"] + sum(
        r["amount_usd"] for r in mine_funding
    )
    ps.entry(
        0,
        "Pale Sun separate investment and management-service book",
        [
            ("1810", investment),
            ("3000", -investment),
            ("4100", -platform_fee),
            ("5100", platform_fee),
        ],
        "PS-RWH-SERVICE-ALLOCATION",
    )
    for book in [rw, ps]:
        views.append(book.summary())
        rows.extend(book.trial_balance())
    reconciliations.append(
        {
            "year": 2026,
            "parent": "PS",
            "subsidiary": "RWH",
            "investment_and_subsidiary_capital_eliminated_usd": investment,
            "platform_service_revenue_and_expense_eliminated_usd": platform_fee,
            "post_elimination_difference_usd": 0,
            "rationale": (
                "Platform service fee is within original $2.8M selected G&A; paid "
                "monthly, no year-end platform receivable/payable. Removes duplicate "
                "service revenue/expense on consolidation."
            ),
        }
    )
    return views, rows, reconciliations


def financial_statement_rows(ledgers):
    rows = []
    for ledger in ledgers:
        summary = ledger.summary()
        for account, value in sorted(ledger.balances.items()):
            kind = ACCOUNTS[account][1]
            if not value:
                continue
            statement = "INCOME_STATEMENT" if kind in ["revenue", "expense"] else "BALANCE_SHEET"
            rows.append(
                {
                    "entity": ledger.entity,
                    "year": ledger.year,
                    "statement": statement,
                    "line_id": account,
                    "line": ACCOUNTS[account][0],
                    "amount_usd": -value if kind in ["revenue", "liability", "equity"] else value,
                    "sign_convention": (
                        "Revenue, liability and equity credit balances presented positive; "
                        "expense and asset debit balances positive; contra accounts retain "
                        "negative signs."
                    ),
                }
            )
        for label, key in [
            ("Net income", "net_income_usd"),
            ("Total assets", "assets_usd"),
            ("Total liabilities", "liabilities_usd"),
            ("Equity including current income", "equity_including_current_income_usd"),
        ]:
            rows.append(
                {
                    "entity": ledger.entity,
                    "year": ledger.year,
                    "statement": "INCOME_STATEMENT" if key == "net_income_usd" else "BALANCE_SHEET",
                    "line_id": key,
                    "line": label,
                    "amount_usd": summary[key],
                }
            )
        for label, amount in [
            ("Opening cash", summary["opening_cash_usd"]),
            *list(summary["cash_flow"].items()),
            ("Closing cash", summary["ending_cash_usd"]),
        ]:
            rows.append(
                {
                    "entity": ledger.entity,
                    "year": ledger.year,
                    "statement": "CASH_FLOW_STATEMENT",
                    "line_id": label,
                    "line": label,
                    "amount_usd": amount,
                }
            )
    return rows


def sensitivities(source, aru, customers, normalized, operations):
    rows = []
    interface_fixed = sum(operations["interface"]["fixed_cost_by_segment"].values())
    revenue = -aru.balances["4000"]
    before_tax = aru.summary()["net_income_usd"] + aru.balances["5500"] + aru.balances["5501"]
    for rate in [20, 25, 30]:
        tax = usd(Decimal(max(before_tax, 0)) * rate / 100)
        rows.append(
            {
                "scenario": f"ARU_TAX_{rate}",
                "changed_driver": "Modeled tax rate",
                "driver_value": rate,
                "pretax_income_usd": before_tax,
                "modeled_income_tax_usd": tax,
                "net_income_usd": before_tax - tax,
                "state": "PROVISIONAL_ASSUMPTION",
                "boundary": (
                    "Annual simplified tax sensitivity; timing and loss-offset rules excluded."
                ),
            }
        )
    for change in [-10, -5, 0, 5, 10]:
        rev_change = usd(Decimal(revenue) * change / 100)
        # Explicit contribution-margin sensitivity, not revised selected contracts.
        contribution = usd(Decimal(rev_change) * Decimal("0.35"))
        rows.append(
            {
                "scenario": f"ARU_VOLUME_{change:+}",
                "changed_driver": (
                    "External volume sensitivity at 35% incremental contribution margin"
                ),
                "driver_value": change,
                "revenue_change_usd": rev_change,
                "pretax_income_change_usd": contribution,
                "state": "PROVISIONAL_ASSUMPTION",
                "boundary": (
                    "35% contribution is a disclosed sensitivity assumption, not proven "
                    "avoidable cost."
                ),
            }
        )
    risky = next(c for c in customers if c["renewal_risk"])
    rows.append(
        {
            "scenario": "MATERIAL_RENEWAL_LOST_DECEMBER",
            "changed_driver": risky["legal_name"],
            "annual_customer_revenue_usd": risky["annual_revenue_usd"],
            "one_month_revenue_exposure_usd": usd(Decimal(risky["annual_revenue_usd"]) / 12),
            "state": "PROVISIONAL_ASSUMPTION",
            "boundary": (
                "Even-month exposure sensitivity; actual seasonal schedule remains in "
                "contract ledger."
            ),
        }
    )
    for multiplier in [0, 0.5, 1, 1.25]:
        rev = usd(sum(r["revenue_usd"] for r in normalized) * multiplier)
        variable = usd(sum(r["variable_cost_usd"] for r in normalized) * multiplier)
        rows.append(
            {
                "scenario": f"INTERFACE_UTILIZATION_{multiplier}",
                "changed_driver": "Billable utilization of 215 physical-car normalized plan",
                "revenue_usd": rev,
                "variable_cost_usd": variable,
                "fixed_cost_usd": interface_fixed,
                "incremental_ebitda_usd": rev - variable - interface_fixed,
                "state": "PROVISIONAL_ASSUMPTION",
                "boundary": (
                    "No take-or-pay guarantee; fixed readiness cost survives zero "
                    "volume. 1.25 is a sensitivity within 300-car design allowance, not "
                    "committed demand."
                ),
            }
        )
    return rows


def working_capital_and_ebitda_support(source, history, aru):
    """Supporting gross-to-net subledgers preserve recorded net ledger balances."""
    policy = source["working_capital_support"]
    allowance_rows, inventory_rows, ebitda_rows = [], [], []
    periods = [
        (
            "2025_OPENING",
            2025,
            0,
            source["opening_2025"]["receivables"],
            source["opening_2025"]["inventory"],
        ),
        ("2025_CLOSING", 2025, 12, history.balances["1100"], history.balances["1200"]),
        ("2026_CLOSING", 2026, 12, aru.balances["1100"], aru.balances["1200"]),
    ]
    for period, year, month, net_ar, inventory in periods:
        allowance = policy["specific_receivable_allowance_usd"]
        gross = net_ar + allowance
        buckets = policy["aging_fixed_buckets_usd"]
        allowance_rows.append(
            {
                "period_id": period,
                "year": year,
                "month": month,
                "gross_external_receivables_usd": gross,
                "current_0_30_days_usd": gross - sum(buckets.values()),
                "days_31_60_usd": buckets["31_60"],
                "days_61_90_usd": buckets["61_90"],
                "days_over_90_usd": buckets["over_90"],
                "specific_allowance_usd": allowance,
                "net_external_receivables_usd": net_ar,
                "allowance_opening_usd": allowance,
                "allowance_provision_usd": 0,
                "allowance_writeoffs_usd": 0,
                "allowance_recoveries_usd": 0,
                "specific_reserved_customer_id": policy["specific_reserved_customer_id"],
                "state": "PROVISIONAL_ASSUMPTION",
                "basis": policy["receivable_basis"],
            }
        )
        classes = policy["inventory_classes"]
        amounts = alloc(inventory, [r["value_allocation_pct"] for r in classes])
        for item, amount in zip(classes, amounts, strict=True):
            inventory_rows.append(
                {
                    "period_id": period,
                    "year": year,
                    "month": month,
                    "inventory_class": item["class"],
                    "quantity_unit": item["unit"],
                    "modeled_quantity": str(
                        Decimal(amount) / Decimal(str(item["average_unit_cost_usd"]))
                    ),
                    "average_unit_cost_usd": item["average_unit_cost_usd"],
                    "gross_inventory_cost_usd": amount,
                    "obsolescence_allowance_usd": 0,
                    "net_inventory_usd": amount,
                    "state": "PROVISIONAL_ASSUMPTION",
                    "basis": policy["inventory_basis"],
                }
            )
    for ledger in [history, aru]:
        ni = ledger.summary()["net_income_usd"]
        tax = ledger.balances["5500"] + ledger.balances["5501"]
        interest = ledger.balances["5400"]
        depreciation = ledger.balances["5300"]
        ebitda = ni + tax + interest + depreciation
        ebitda_rows.append(
            {
                "entity": ledger.entity,
                "year": ledger.year,
                "net_income_usd": ni,
                "income_tax_usd": tax,
                "interest_usd": interest,
                "depreciation_usd": depreciation,
                "reported_case_ebitda_usd": ebitda,
                "seller_discretionary_addbacks_usd": 0,
                "retention_consulting_addbacks_usd": 0,
                "commissioning_addbacks_usd": 0,
                "normalized_case_ebitda_usd": ebitda,
                "basis": (
                    "No unsupported earnings addback; all recorded payroll, owner service, "
                    "retention and commissioning expenses remain in normalized earnings. "
                    "Reported means this synthetic case, not audited company records."
                ),
            }
        )
    return allowance_rows, inventory_rows, ebitda_rows


def validate(
    source, customers, contracts, monthly, payroll, history, aru, mine, normalized, invoices, ppa
):
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    check(len(customers) >= 21, "At least 21 independent fictional customers required")
    amounts = sorted((r["annual_revenue_usd"] for r in customers), reverse=True)
    check(sum(amounts) == 42000000, "Customer revenue total")
    check(amounts[0] == 4620000 and sum(amounts[:5]) == 16800000, "Largest/top five concentration")
    check(
        len(source["employees"]) == 131
        and sum(e["segment"] == "BST" for e in source["employees"]) == 58,
        "Employee count",
    )
    check(
        sum(c["annual_units"] for c in contracts if c["segment"] == "BST") == 9000, "Rail car count"
    )
    for segment, plan in source["segment_baseline"].items():
        check(
            sum(r["revenue_usd"] for r in monthly if r["segment"] == segment) == plan["revenue"],
            f"Monthly revenue:{segment}",
        )
        check(
            plan["opex"] - plan["shared_allocation"] >= payroll[segment],
            f"External expense covers payroll:{segment}",
        )
    check(history.summary()["net_income_usd"] == 5695000, "2025 income")
    check(history.summary()["ending_cash_usd"] == 3500000, "2025 cash")
    check(
        -sum(
            r["signed_usd"]
            for r in history.rows
            if r["account"] in ["4000", "5000", "5100", "5900"]
        )
        == 9800000,
        "2025 EBITDA",
    )
    check(sum(r["revenue_usd"] for r in normalized) == 583480, "Rate-derived normalized revenue")
    check(
        sum(r["revenue_usd"] - r["variable_cost_usd"] for r in normalized) - 48000 == 203290,
        "Rate-derived incremental EBITDA",
    )
    check(
        aru.balances["1150"] == -mine.balances["2150"], "Reciprocal intercompany closing balances"
    )
    check(
        -aru.balances["4100"] == mine.balances["5150"] == sum(r["revenue_usd"] for r in invoices),
        "Reciprocal intercompany invoices",
    )
    check(sum(h["percent"] for h in source["transaction"]["stockholders"]) == 100, "Cap table 100%")
    check(sum(source["transaction"]["retention_allocations"].values()) == 500000, "Retention pool")
    check(
        ppa["close_sources_before_fees_usd"] == ppa["close_uses_before_fees_usd"],
        "Acquisition sources and uses",
    )
    for ledger in [history, aru, mine]:
        ledger.summary()
        journals = defaultdict(int)
        for row in ledger.rows:
            journals[row["journal_id"]] += row["signed_usd"]
        check(
            all(v == 0 for v in journals.values()),
            f"Every journal balances:{ledger.entity}/{ledger.year}",
        )
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "PASS",
        "checks": (
            "Contract pricing, customer concentration, employee reconciliation, "
            "segment revenue/cost, sources/uses, per-journal double entry, three "
            "balance sheets, cash rollforwards, reciprocal intercompany balances and "
            "elimination."
        ),
        "boundary": (
            "Synthetic model consistency, not independent operational feasibility, "
            "audited financial reporting, legal eligibility or market-price "
            "validation."
        ),
    }


def write_csv(path, rows):
    if not rows:
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v
                    for k, v in row.items()
                }
            )


def build(output=OUT):
    source, operations, core = read_sources()
    customers, contracts, monthly = customer_schedules(source)
    employee_rows, payroll = payroll_schedules(source)
    history, hist_monthly = build_2025(source, monthly, payroll)
    normalized, invoices = interface_schedules(operations)
    ppa = acquisition(source, history)
    aru, opening, stub, aru_monthly, aru_funding, assets, debt, tax_schedule = build_2026(
        source, operations, history, monthly, payroll, invoices, ppa
    )
    mine, mine_monthly, mine_funding, mine_bridge, closure_rows = build_mine(
        source, core, invoices, operations
    )
    legal_views, legal_tbs, legal_eliminations = legal_book_views(
        source, history, aru, mine, mine_funding, invoices
    )
    validation = validate(
        source,
        customers,
        contracts,
        monthly,
        payroll,
        history,
        aru,
        mine,
        normalized,
        invoices,
        ppa,
    )
    receivable_support, inventory_support, ebitda_support = working_capital_and_ebitda_support(
        source, history, aru
    )
    eliminations = [
        {
            "entry_id": "ELIM-IC-PNL",
            "debit": "Intercompany revenue",
            "credit": "Intercompany logistics expense",
            "amount_usd": -aru.balances["4100"],
        },
        {
            "entry_id": "ELIM-IC-BS",
            "debit": "Intercompany payable",
            "credit": "Intercompany receivable",
            "amount_usd": aru.balances["1150"],
        },
    ]
    consolidated = {
        "scope": (
            "ARU group plus Pale Sun/Red Wash operating case; excludes unrelated "
            "Sable Harbor businesses and holding-company investment accounts"
        ),
        "external_revenue_usd": aru.summary()["revenue_usd"]
        + mine.summary()["revenue_usd"]
        + aru.balances["4100"],
        "net_income_before_parent_transaction_expense_usd": aru.summary()["net_income_usd"]
        + mine.summary()["net_income_usd"],
        "parent_transaction_expense_usd": source["transaction"]["transaction_expense"],
        "net_income_after_parent_transaction_expense_usd": aru.summary()["net_income_usd"]
        + mine.summary()["net_income_usd"]
        - source["transaction"]["transaction_expense"],
        "assets_after_intercompany_receivable_elimination_usd": aru.summary()["assets_usd"]
        + mine.summary()["assets_usd"]
        - aru.balances["1150"],
        "liabilities_after_intercompany_payable_elimination_usd": aru.summary()["liabilities_usd"]
        + mine.summary()["liabilities_usd"]
        - aru.balances["1150"],
        "equity_before_parent_transaction_expense_usd": aru.summary()[
            "equity_including_current_income_usd"
        ]
        + mine.summary()["equity_including_current_income_usd"],
    }
    assert (
        consolidated["assets_after_intercompany_receivable_elimination_usd"]
        == consolidated["liabilities_after_intercompany_payable_elimination_usd"]
        + consolidated["equity_before_parent_transaction_expense_usd"]
    )
    report = {
        "source_id": source["record_id"],
        "cutoff": source["decision_cutoff"],
        "basis": (
            "Synthetic 2025 history; 2026 January–August calibration and "
            "September–December forecast; ARU postclose books cover January "
            "7–December 31."
        ),
        "aru_2025": history.summary(),
        "acquisition": ppa,
        "closing_stub": stub,
        "aru_2026_postclose": aru.summary(),
        "mine_integrated_2026": mine.summary(),
        "mine_bridge": mine_bridge,
        "industrial_operating_consolidation": consolidated,
        "separate_legal_book_views": legal_views,
        "legal_book_allocation_boundary": source["legal_book_policy"],
        "normalized_interface": {
            "cars": 215,
            "unbilled_contingency_cars": 10,
            "revenue_usd": sum(r["revenue_usd"] for r in normalized),
            "incremental_ebitda_usd": 203290,
        },
        "funding": {
            "acquisition_and_fees_usd": ppa["parent_cash_including_fees_usd"],
            "aru_postclose_equity_usd": sum(r["amount_usd"] for r in aru_funding),
            "mine_2026_equity_usd": sum(r["amount_usd"] for r in mine_funding),
        },
        "validation": validation,
    }
    output.mkdir(parents=True, exist_ok=True)
    datasets = {
        "customer_register.csv": customers,
        "contract_register.csv": contracts,
        "contract_monthly_2025.csv": monthly,
        "employee_census_payroll.csv": employee_rows,
        "external_cost_budget_support.csv": expense_support(source, payroll),
        "rail_opex_class_bridge.csv": rail_expense_class_support(source),
        "receivables_aging_and_allowance.csv": receivable_support,
        "parts_fuel_materials_inventory.csv": inventory_support,
        "reported_to_normalized_ebitda.csv": ebitda_support,
        "aru_2025_journal.csv": history.rows,
        "aru_2025_trial_balance.csv": history.trial_balance(),
        "aru_2025_monthly_statements.csv": hist_monthly,
        "aru_acquisition_opening_trial_balance.csv": opening,
        "aru_acquisition_tax_allocation.csv": [
            {"line": key, "amount_usd": value, "state": "PROVISIONAL_ASSUMPTION"}
            for key, value in ppa["tax_allocation"].items()
            if isinstance(value, int)
        ]
        + [
            {
                "line": "Other tax basis: " + key,
                "amount_usd": value,
                "state": "PROVISIONAL_ASSUMPTION",
            }
            for key, value in ppa["tax_allocation"]["other_tax_asset_bases_usd"].items()
        ]
        + [
            {
                "line": "Initial book goodwill excess over tax basis",
                "amount_usd": ppa["initial_book_goodwill_excess_over_tax_usd"],
                "state": "PROVISIONAL_ASSUMPTION",
            }
        ],
        "aru_2026_journal.csv": aru.rows,
        "aru_2026_trial_balance.csv": aru.trial_balance(),
        "aru_2026_monthly_statements.csv": aru_monthly,
        "aru_2026_fixed_assets.csv": assets,
        "aru_2026_debt_leases.csv": debt,
        "aru_2026_tax_rollforward.csv": tax_schedule,
        "red_wash_2026_journal.csv": mine.rows,
        "red_wash_2026_trial_balance.csv": mine.trial_balance(),
        "red_wash_2026_monthly_statements.csv": mine_monthly,
        "red_wash_closure_cashflow_calibration.csv": closure_rows,
        "financial_statements.csv": financial_statement_rows([history, aru, mine]),
        "separate_legal_entity_trial_balances.csv": legal_tbs,
        "ownership_and_treasury_eliminations.csv": legal_eliminations,
        "scenario_sensitivities.csv": sensitivities(source, aru, customers, normalized, operations),
        "interface_normalized_economics.csv": normalized,
        "intercompany_invoices_2026.csv": invoices,
        "intercompany_eliminations.csv": eliminations,
        "parent_equity_funding_2026.csv": aru_funding + mine_funding,
        "seller_cap_table.csv": [
            dict(
                r,
                consideration_usd=source["transaction"]["buyer_consideration"]
                * r["percent"]
                // 100,
                escrow_usd=source["transaction"]["escrow"] * r["percent"] // 100,
                excess_cash_usd=source["transaction"]["excess_cash_distribution"]
                * r["percent"]
                // 100,
            )
            for r in source["transaction"]["stockholders"]
        ],
    }
    for filename, rows in datasets.items():
        for row in rows:
            year = int(
                row.get(
                    "year",
                    2025
                    if "2025" in filename
                    or filename
                    in {
                        "customer_register.csv",
                        "contract_register.csv",
                        "employee_census_payroll.csv",
                        "external_cost_budget_support.csv",
                    }
                    else 2026,
                )
            )
            month = row.get("month", row.get("through_month"))
            if "period_role" not in row:
                row["period_role"] = (
                    period_role(year, int(month))
                    if month is not None
                    else "SYNTHETIC_HISTORICAL_CASE"
                    if year == 2025
                    else "MANAGEMENT_SCENARIO_AT_2026_09_05"
                )
            row.setdefault("record_origin", "PUBLIC_SYNTHETIC_DIEGETIC")
            row.setdefault("fact_state", row.get("state", "LOCKED_DERIVED_IMPLEMENTATION"))
            row.setdefault("as_of_cutoff", "2026-09-05")
            if filename in {
                "aru_acquisition_opening_trial_balance.csv",
                "aru_acquisition_tax_allocation.csv",
            }:
                row["period_role"] = "SYNTHETIC_CALIBRATION"
                period_end = "2026-01-07"
            elif month == 0:
                period_end = (
                    f"{year}-01-07"
                    if year == 2026 and row.get("entity") == "ARU_GROUP"
                    else f"{year}-01-01"
                )
            elif month is not None:
                period_end = f"{year}-{int(month):02}-{calendar.monthrange(year, int(month))[1]:02}"
            else:
                period_end = f"{year}-12-31"
            row.setdefault("effective_period_end", period_end)
            row.setdefault("available_at", "2026-09-05")
        write_csv(output / filename, rows)
    (output / "financial_summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    manifests = []
    for filename in sorted([*datasets, "financial_summary.json"]):
        path = output / filename
        manifests.append(
            {
                "path": filename,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    manifest = {
        "source_inputs": [
            {"path": str(p.relative_to(REPO)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in [SOURCE, OPS, CORE]
        ],
        "artifacts": manifests,
        "generated_at_semantics": (
            "No wall-clock timestamp; identical source inputs produce identical artifacts."
        ),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    report = build(args.output)
    print(
        json.dumps(
            {
                "status": report["validation"]["status"],
                "aru_2025": report["aru_2025"],
                "aru_2026": report["aru_2026_postclose"],
                "mine": report["mine_integrated_2026"],
                "funding": report["funding"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
