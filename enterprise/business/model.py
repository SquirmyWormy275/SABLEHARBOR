"""Business events drive a separately versioned, public synthetic Core forecast.

No released source or prior financial amount is used to backsolve commercial rates.
Cash entries are conditional settlement requests; enterprise treasury applies finite
funding and separately identifies any unpaid operating cash obligations.
"""

from __future__ import annotations

import calendar
import copy
import hashlib
import json
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from .advisory import check_matter, run_matters

D = Decimal
Q = D("0.0001")
SOURCE = Path(__file__).parent / "source"
ACCOUNTS = {
    "1000": "asset",
    "BIZ_AR": "asset",
    "BIZ_ALLOWANCE": "asset",
    "BIZ_INVENTORY": "asset",
    "BIZ_PPE": "asset",
    "BIZ_ACCUM": "asset",
    "BIZ_AP": "liability",
    "BIZ_DEFERRED": "liability",
    "BIZ_HOST_AP": "liability",
    "BIZ_REVENUE": "revenue",
    "BIZ_PAYROLL": "expense",
    "BIZ_DELIVERY": "expense",
    "BIZ_RESEARCH": "expense",
    "BIZ_PROCESSING": "expense",
    "BIZ_COGS": "expense",
    "BIZ_HOST_SHARE": "expense",
    "BIZ_DDA": "expense",
    "BIZ_SUPPORT": "expense",
    "BIZ_CREDIT_LOSS": "expense",
    "BIZ_INVENTORY_LOSS": "expense",
    "BIZ_UNIT_CLEARING": "intercompany",
    "BIZ_CAPITAL_UNPAID": "liability",
    "BIZ_DEBT_UNPAID": "liability",
}
SEGMENTS = {
    "foundry-field": "FOUNDRY_FIELD",
    "atlas-meridian": "ATLAS",
    "advisory": "ADVISORY",
    "willow": "WILLOW",
    "project-cradle": "CRADLE",
    "corporate": "CORPORATE",
}
UNITS = tuple(SEGMENTS)


def amount(value):
    return D(str(value)).quantize(Q, rounding=ROUND_HALF_UP)


def money(value):
    return format(amount(value), ".4f")


def period(month):
    year = 2027 + (month - 1) // 12
    m = (month - 1) % 12 + 1
    return year, m, f"{year}-{m:02}-{calendar.monthrange(year, m)[1]}"


def load_inputs(source=SOURCE):
    return {p.stem: json.loads(p.read_text()) for p in sorted(Path(source).glob("*.json"))}


def fingerprint(inputs):
    return hashlib.sha256(
        json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def check_inputs(inputs):
    policy = inputs["policy"]
    if policy["start_year"] != 2027 or policy["years"] != 5:
        raise ValueError("This integration explicitly covers January 2027 to December 2031")
    if set(policy["cases"]) != {"base", "downside", "expansion"}:
        raise ValueError("Cases must match industrial scenario identities")
    for key in ("delivery_utilization", "support_staff_fraction", "expected_credit_loss_rate"):
        if not 0 <= D(policy[key]) <= 1:
            raise ValueError(f"Invalid policy fraction {key}")
    for case in policy["cases"].values():
        for key in ("price_factor", "cost_factor", "rework_factor"):
            if D(case[key]) <= 0:
                raise ValueError(f"Invalid positive scenario driver {key}")
        if case["churn_modulus"] < 1:
            raise ValueError("Churn modulus must be positive")
        for key in ("mineral_availability", "mineral_recovery"):
            if not 0 <= D(case[key]) <= 1:
                raise ValueError(f"Out-of-range fraction: {key}")
        if case["collection_delay_months"] < 1 or case["acceptance_delay_months"] < 0:
            raise ValueError("Invalid settlement or acceptance timing")
    for name in ("contracts", "engagements", "assets", "projects"):
        idkey = {
            "contracts": "contract_id",
            "engagements": "engagement_id",
            "assets": "asset_id",
            "projects": "project_id",
        }[name]
        ids = [r[idkey] for r in inputs[name]]
        if len(set(ids)) != len(ids):
            raise ValueError(f"Duplicate source identity: {name}")
    for c in inputs["contracts"]:
        if c["unit"] not in {"foundry-field", "atlas-meridian"} or c["start_month"] < 1:
            raise ValueError("Invalid subscription scope or start")
        if c["deployment_fee_usd"] < 0 or c["compute_monthly_usd"] < 0:
            raise ValueError("Negative subscription economics")
        if c["term_months"] != 12 or c["monthly_subscription_usd"] < 0:
            raise ValueError("Supported subscription policy: nonnegative annual terms")
    for e in inputs["engagements"]:
        if (
            e["unit"] not in {"advisory", "atlas-meridian"}
            or e["fee_usd"] < 0
            or e["delivery_hours"] < 0
            or e["start_month"] < 1
        ):
            raise ValueError("Invalid engagement scope or economics")
        if any(
            D(m["fee_fraction"]) < 0 or D(m["hours_fraction"]) < 0 or m["offset"] < 0
            for m in e["milestones"]
        ):
            raise ValueError("Invalid milestone fraction or timing")
        if e["unit"] == "advisory":
            check_matter(e)
        if e["billing_basis"] != "ACCEPTED_OUTCOME":
            raise ValueError("Advisory/Atlas bill accepted outcomes")
        if sum(D(m["fee_fraction"]) for m in e["milestones"]) != 1:
            raise ValueError("Milestone fees must sum to contract value")
        if sum(D(m["hours_fraction"]) for m in e["milestones"]) != 1:
            raise ValueError("Milestone effort must sum to engagement effort")
    for a in inputs["assets"]:
        if a["purchase_month"] < 1 or a.get("transfer_month", 61) <= a["purchase_month"]:
            raise ValueError("Asset receipt must precede transfer")
        if a["cost_usd"] < 0 or a["life_months"] <= 0:
            raise ValueError("Invalid asset cost/life")
        if a.get("transfer_month") and a.get("qualification_required") and not a.get("qualified"):
            raise ValueError("Unqualified asset transfer must not authorize production")
    for p in inputs["projects"]:
        if p["decision"] == "TRANSFER" and not (
            p["qualified"] and p["receiver"] and p["maintenance_owner"]
        ):
            raise ValueError("Transfer requires receiver, qualification and maintenance owner")
    for row in policy["workforce"].values():
        if not 0 <= row["occupied"] <= row["authorized"]:
            raise ValueError("Occupied workforce exceeds declared authorization")
    if policy["workforce"]["j2"]["authorized"] != 237:
        raise ValueError("J2 authorized establishment must preserve 237 billets")
    for stream, r in inputs["recovery"].items():
        if not isinstance(r, dict):
            continue
        for key in (
            "monthly_feed_tonnes",
            "monthly_water_m3",
            "concentration_mg_l",
            "processing_usd_per_feed_tonne",
            "realized_usd_per_kg",
            "monthly_reagent_and_lab_usd",
            "bedford_and_freight_usd_per_kg",
        ):
            if key in r and D(r[key]) < 0:
                raise ValueError(f"Negative recovery driver {stream}/{key}")
        if r.get("sale_lag_months", 1) < 1:
            raise ValueError("Recovery sales require downstream acceptance after capture")
        for key in (
            "assay_payable_fraction",
            "host_share",
            "contained_reo_fraction",
            "gen1_recovery",
            "gen2_recovery",
            "gen1_availability",
            "gen2_availability",
        ):
            if key in r and not 0 <= D(r[key]) <= 1:
                raise ValueError(f"Invalid recovery fraction {stream}/{key}")


class BusinessModel:
    """Mutable execution state is isolated by instance and scenario."""

    account_types = ACCOUNTS

    def __init__(self, inputs=None):
        self.inputs = copy.deepcopy(inputs if inputs is not None else load_inputs())
        check_inputs(self.inputs)
        self.policy = self.inputs["policy"]
        self.input_hash = fingerprint(self.inputs)
        self.tables = defaultdict(list)
        self.by_month = defaultdict(list)
        self.roster = self.make_roster()
        self.tables["workforce_positions"] = self.roster
        self.tables["contracts"] = copy.deepcopy(self.inputs["contracts"])
        self.tables["engagements"] = copy.deepcopy(self.inputs["engagements"])
        self._built = False

    def make_roster(self):
        rows = []
        for group, policy in self.policy["workforce"].items():
            home = group if group in SEGMENTS else "corporate"
            for n in range(1, policy["authorized"] + 1):
                occupied = n <= policy["occupied"]
                borrowed = occupied and group == "willow" and n <= 2
                assignments = {home: "0.8", "advisory": "0.2"} if borrowed else {home: "1"}
                rows.append(
                    {
                        "position_id": f"SYN-{group.upper()}-{n:03}",
                        "person_id": f"SYN-PERSON-{group.upper()}-{n:03}" if occupied else "",
                        "home_group": group,
                        "home_unit": home,
                        "delivery_role": not (group == "advisory" and n <= 4),
                        "authorized": True,
                        "occupied": occupied,
                        "paid_fte": "1" if occupied else "0",
                        "annual_loaded_usd": policy["annual_loaded_usd"],
                        "assignments": assignments,
                        "fact_state": "CONDITIONAL_OCCUPANCY_NOT_2026_ACTUAL",
                    }
                )
        return rows

    def event(self, kind, source_id, unit, **fields):
        row = {
            "event_id": f"{self.scenario}-{self.month:02}-{kind}-{source_id}",
            "scenario": self.scenario,
            "period": period(self.month)[2],
            "month_index": self.month,
            "unit": unit,
            "kind": kind,
            "source_id": source_id,
            "available_at": self.policy["available_at"],
            "fact_state": "CONDITIONAL_FORECAST",
            **fields,
        }
        self.tables["events"].append(row)
        return row["event_id"]

    def post(self, source, unit, lines, description):
        rounded = [(a, amount(v)) for a, v in lines if amount(v)]
        if sum(v for _, v in rounded):
            raise ValueError(f"Unbalanced business journal {source}: {rounded}")
        if not rounded:
            return
        self.sequence += 1
        journal_id = f"BIZ-{self.scenario}-{self.sequence:07}"
        year, month, date = period(self.month)
        for a, v in rounded:
            if a not in ACCOUNTS:
                raise ValueError(f"Unknown account {a}")
            cash_flow = "INVESTING" if "BIZ_PPE" in [a for a, _ in rounded] else "OPERATING"
            row = {
                "scenario": self.scenario,
                "entity": "SHI",
                "year": year,
                "month": month,
                "period": date,
                "month_index": self.month,
                "journal_id": journal_id,
                "account": a,
                "account_type": ACCOUNTS[a],
                "unit": unit,
                "segment": SEGMENTS[unit],
                "signed_usd": money(v),
                "debit_usd": money(max(v, 0)),
                "credit_usd": money(max(-v, 0)),
                "source_id": source,
                "source_type": "BUSINESS_DRIVEN_FORECAST",
                "description": description,
                "cash_flow": cash_flow if a == "1000" else "NONCASH_OR_OPENING",
                "available_at": self.policy["available_at"],
                "fact_state": "CONDITIONAL_FORECAST",
            }
            self.tables["journal"].append(row)
            self.by_month[self.scenario, year, month].append(row)
            self.balances[unit][a] += v

    def invoice(self, source, unit, customer, value, deferred=False, host_share="0"):
        value = amount(value)
        if not value:
            return
        iid = f"INV-{self.scenario}-{source}"
        if iid in self.invoice_ids:
            raise ValueError(f"Duplicate invoice {iid}")
        self.invoice_ids.add(iid)
        due = self.month + 1
        collect = self.month + max(1, self.case["collection_delay_months"])
        event = self.event(
            "INVOICE",
            iid,
            unit,
            customer_id=customer,
            amount_usd=money(value),
            due_date=period(due)[2],
            performance_source=source,
        )
        self.post(
            event,
            unit,
            [("BIZ_AR", value), ("BIZ_DEFERRED" if deferred else "BIZ_REVENUE", -value)],
            "Annual subscription billing" if deferred else "Accepted outcome/product billing",
        )
        row = {
            "invoice_id": iid,
            "scenario": self.scenario,
            "unit": unit,
            "customer_id": customer,
            "source_id": source,
            "issue_month": self.month,
            "due_month": due,
            "due_date": period(due)[2],
            "collection_month": collect,
            "amount_usd": money(value),
            "remaining_usd": money(value),
            "host_share": host_share,
        }
        self.invoices.append(row)
        if D(host_share):
            share = amount(value * D(host_share))
            self.post(
                event,
                unit,
                [("BIZ_HOST_SHARE", share), ("BIZ_HOST_AP", -share)],
                "Estimated realized-value host obligation; settlement follows customer collection",
            )

    def cost(self, source, unit, account, value, pay_lag=1):
        value = amount(value)
        if not value:
            return
        event = self.event("COST", source, unit, amount_usd=money(value), account=account)
        self.post(event, unit, [(account, value), ("BIZ_AP", -value)], "Source-driven vendor cost")
        self.payables.append(
            {
                "payable_id": f"AP-{self.scenario}-{self.month}-{source}",
                "scenario": self.scenario,
                "unit": unit,
                "source_id": event,
                "accrual_month": self.month,
                "due_month": self.month + pay_lag,
                "due_date": period(self.month + pay_lag)[2],
                "amount_usd": money(value),
                "remaining_usd": money(value),
            }
        )

    def settle(self):
        for invoice in self.invoices:
            if invoice["collection_month"] == self.month:
                value = D(invoice["remaining_usd"])
                event = self.event(
                    "COLLECTION",
                    invoice["invoice_id"],
                    invoice["unit"],
                    amount_usd=money(value),
                    invoice_id=invoice["invoice_id"],
                )
                self.post(
                    event,
                    invoice["unit"],
                    [("1000", value), ("BIZ_AR", -value)],
                    "Conditional contractual customer collection",
                )
                invoice["remaining_usd"] = "0.0000"
                if D(invoice["host_share"]):
                    self.host_payables.append(
                        {
                            "source_id": invoice["invoice_id"],
                            "due_month": self.month + 1,
                            "amount": amount(value * D(invoice["host_share"])),
                        }
                    )
        for payable in self.payables:
            if payable["due_month"] == self.month:
                value = D(payable["remaining_usd"])
                event = self.event(
                    "PAYMENT_REQUEST",
                    payable["payable_id"],
                    payable["unit"],
                    amount_usd=money(value),
                    payable_id=payable["payable_id"],
                    settlement_state="CONDITIONAL_SUBJECT_TO_ENTERPRISE_FUNDING",
                )
                self.post(
                    event,
                    payable["unit"],
                    [("BIZ_AP", value), ("1000", -value)],
                    "Scheduled vendor cash request; treasury shortfalls separately reported",
                )
                payable["remaining_usd"] = "0.0000"
        for payable in self.host_payables:
            if payable["due_month"] == self.month:
                v = payable["amount"]
                event = self.event(
                    "HOST_SETTLEMENT_REQUEST",
                    payable["source_id"],
                    "project-cradle",
                    amount_usd=money(v),
                    settlement_state="CONDITIONAL_SUBJECT_TO_ENTERPRISE_FUNDING",
                )
                self.post(
                    event,
                    "project-cradle",
                    [("BIZ_HOST_AP", v), ("1000", -v)],
                    "Host settlement after modeled realized customer proceeds",
                )

    def workforce(self):
        year_index = (self.month - 1) // 12
        factor = (1 + D(self.policy["payroll_inflation"])) ** year_index * D(
            self.case["cost_factor"]
        )
        self.capacity = defaultdict(D)
        self.payroll = defaultdict(D)
        for position in self.roster:
            if not position["occupied"]:
                continue
            total = amount(D(position["annual_loaded_usd"]) / 12 * factor)
            allocated = D(0)
            assignments = list(position["assignments"].items())
            for index, (unit, fraction) in enumerate(assignments):
                value = (
                    total - allocated
                    if index == len(assignments) - 1
                    else amount(total * D(fraction))
                )
                allocated += value
                self.payroll[unit] += value
                hours = (
                    D(self.policy["hours_per_month"])
                    * D(fraction)
                    * D(self.policy["delivery_utilization"])
                )
                if not position["delivery_role"]:
                    hours = D(0)
                self.capacity[unit] += hours
                self.tables["workforce_assignments"].append(
                    {
                        "scenario": self.scenario,
                        "period": period(self.month)[2],
                        "month_index": self.month,
                        "position_id": position["position_id"],
                        "person_id": position["person_id"],
                        "home_group": position["home_group"],
                        "unit": unit,
                        "assignment_fte": fraction,
                        "loaded_cost_usd": money(value),
                        "delivery_capacity_hours": money(hours),
                    }
                )
            if allocated != total:
                raise ValueError("Employee cost allocated more or less than once")
        for unit, value in self.payroll.items():
            event = self.event("PAYROLL_REQUEST", unit, unit, amount_usd=money(value))
            self.post(
                event,
                unit,
                [("BIZ_PAYROLL", value), ("1000", -value)],
                "One occupied-position payroll, assigned once; conditional treasury settlement",
            )
        occupied = sum(p["occupied"] for p in self.roster if p["home_group"] == "ess")
        support = (
            D(self.policy["corporate_monthly_facility_usd"])
            + D(self.policy["annual_ess_vendor_per_occupied_usd"]) * occupied / 12
        )
        self.cost(
            "ESS-FACILITY-VENDORS",
            "corporate",
            "BIZ_SUPPORT",
            support * D(self.case["cost_factor"]),
        )

    def subscriptions(self):
        active = defaultdict(list)
        start_capacity = self.capacity["foundry-field"] * D("0.20")
        for c in self.inputs["contracts"]:
            cid = c["contract_id"]
            unit = c["unit"]
            planned = c["start_month"] + (
                self.case["acceptance_delay_months"] if c["deployment_fee_usd"] else 0
            )
            if cid not in self.contract_starts and planned <= self.month:
                effort = (
                    D(self.policy["deployment_hours"]) * D(self.case["rework_factor"])
                    if c["deployment_fee_usd"]
                    else D(0)
                )
                if effort > start_capacity:
                    self.event("DEPLOYMENT_BACKLOG", cid, unit, hours_required=money(effort))
                    continue
                start_capacity -= effort
                self.contract_starts[cid] = self.month
                acceptance = self.event(
                    "DEPLOYMENT_ACCEPTANCE",
                    cid,
                    unit,
                    customer_id=c["customer_id"],
                    approved_hours=money(effort),
                    authority="MODELED_CUSTOMER_ACCEPTANCE_NOT_OPERATING_AUTHORITY",
                )
                self.invoice(
                    acceptance,
                    unit,
                    c["customer_id"],
                    D(c["deployment_fee_usd"]) * D(self.case["price_factor"]),
                )
            if cid not in self.contract_starts or cid in self.churned:
                continue
            elapsed = self.month - self.contract_starts[cid]
            term = elapsed // 12
            if (
                elapsed > 0
                and elapsed % 12 == 0
                and int(cid.split("-")[-1]) % self.case["churn_modulus"] == 0
            ):
                self.churned.add(cid)
                self.event("CHURN", cid, unit, renewal_term=term)
                continue
            rate = amount(
                D(c["monthly_subscription_usd"])
                * D(self.case["price_factor"])
                * (1 + D(self.policy["annual_subscription_escalation"])) ** term
            )
            if elapsed % 12 == 0:
                self.invoice(f"{cid}-TERM-{term}", unit, c["customer_id"], rate * 12, deferred=True)
            event = self.event(
                "SUBSCRIPTION_SERVICE",
                cid,
                unit,
                customer_id=c["customer_id"],
                monthly_revenue_usd=money(rate),
                annual_recurring_usd=money(rate * 12),
                seats=c["seats"],
                term=term,
            )
            self.post(
                event,
                unit,
                [("BIZ_DEFERRED", rate), ("BIZ_REVENUE", -rate)],
                "One month of annual subscription service",
            )
            self.cost(
                f"HOSTING-{cid}",
                unit,
                "BIZ_DELIVERY",
                D(c["compute_monthly_usd"]) * D(self.case["cost_factor"]),
            )
            active[unit].append((c, rate))
        for unit, population in active.items():
            required = len(population) * D(self.policy["support_hours_per_customer"])
            capacity = self.capacity[unit] * D(self.policy["support_staff_fraction"])
            total = sum((r for _, r in population), D(0))
            self.tables["commercial_metrics"].append(
                {
                    "scenario": self.scenario,
                    "period": period(self.month)[2],
                    "unit": unit,
                    "active_customers": len(population),
                    "arr_usd": money(total * 12),
                    "largest_customer_share": str(
                        max((r for _, r in population), default=D(0)) / (total or 1)
                    ),
                    "support_required_hours": money(required),
                    "support_capacity_hours": money(capacity),
                    "support_backlog_hours": money(max(required - capacity, 0)),
                }
            )

    def outcomes(self):
        run_matters(self)

    def product_outcomes(self):
        available = {"atlas-meridian": self.capacity["atlas-meridian"] * D("0.80")}
        for e in self.inputs["engagements"]:
            if e["unit"] == "advisory":
                continue
            for milestone_index, milestone in enumerate(e["milestones"]):
                key = f"{e['engagement_id']}-{milestone['name']}"
                if key in self.accepted:
                    continue
                planned = e["start_month"] + milestone["offset"]
                if planned > self.month:
                    continue
                unit = e["unit"]
                if key not in self.work_done:
                    hours = amount(
                        D(e["delivery_hours"])
                        * D(milestone["hours_fraction"])
                        * D(self.case["rework_factor"])
                    )
                    # Rejected modeled outcomes consume additional effort, without additional fees.
                    if milestone["name"] == e["rejection_milestone"]:
                        hours = amount(hours * D("1.15"))
                    if available[unit] < hours:
                        self.event("ENGAGEMENT_BACKLOG", key, unit, hours_required=money(hours))
                        continue
                    available[unit] -= hours
                    self.work_done[key] = self.month
                    self.event(
                        "DELIVERY_WORK",
                        key,
                        unit,
                        engagement_id=e["engagement_id"],
                        hours=money(hours),
                        billing_basis="INTERNAL_COST_AND_CAPACITY_ONLY",
                    )
                    if unit == "atlas-meridian":
                        self.cost(
                            f"COMPUTE-{key}",
                            unit,
                            "BIZ_RESEARCH",
                            hours * 18 * D(self.case["cost_factor"]),
                        )
                    else:
                        self.cost(
                            f"TRAVEL-{key}",
                            unit,
                            "BIZ_DELIVERY",
                            hours * 12 * D(self.case["cost_factor"]),
                        )
                    if milestone["name"] == e["rejection_milestone"]:
                        self.event(
                            "ACCEPTANCE_REJECTED",
                            key,
                            unit,
                            engagement_id=e["engagement_id"],
                            reason="Modeled transfer test incomplete; fixed fee unchanged",
                        )
                due = self.work_done[key] + self.case["acceptance_delay_months"]
                if milestone["name"] == e["rejection_milestone"]:
                    due += e["rejection_delay_months"]
                previous = e["milestones"][milestone_index - 1]["name"] if milestone_index else None
                if due > self.month or (
                    previous and f"{e['engagement_id']}-{previous}" not in self.accepted
                ):
                    continue
                event = self.event(
                    "OUTCOME_ACCEPTED",
                    key,
                    unit,
                    engagement_id=e["engagement_id"],
                    customer_id=e["customer_id"],
                    fee_fraction=milestone["fee_fraction"],
                    independent_atlas_fee=not e["atlas_fee_included"],
                )
                self.accepted.add(key)
                self.invoice(
                    event,
                    unit,
                    e["customer_id"],
                    D(e["fee_usd"]) * D(milestone["fee_fraction"]) * D(self.case["price_factor"]),
                )
        for unit in available:
            self.tables["capacity"].append(
                {
                    "scenario": self.scenario,
                    "period": period(self.month)[2],
                    "unit": unit,
                    "capacity_hours": money(self.capacity[unit] * D("0.80")),
                    "used_hours": money(self.capacity[unit] * D("0.80") - available[unit]),
                    "remaining_hours": money(available[unit]),
                }
            )

    def research(self):
        for project in self.inputs["projects"]:
            # Bounded initial projects; future follow-on awards are not automatically fabricated.
            if self.month > project["gate_month"]:
                continue
            self.cost(
                project["project_id"],
                "willow",
                "BIZ_RESEARCH",
                D(project["monthly_materials_usd"]) * D(self.case["cost_factor"]),
            )
            if self.month == project["gate_month"]:
                self.event(
                    "EXPERIMENT_GATE",
                    project["project_id"],
                    "willow",
                    question=project["question"],
                    decision=project["decision"],
                    receiver=project["receiver"],
                    qualified=project["qualified"],
                    direct_materials_usd=money(
                        D(project["monthly_materials_usd"])
                        * self.month
                        * D(self.case["cost_factor"])
                    ),
                    authorized_materials_budget_usd=project["budget_usd"],
                    maintenance_owner=project["maintenance_owner"],
                )
        for asset in self.inputs["assets"]:
            aid = asset["asset_id"]
            if self.month < asset["purchase_month"]:
                continue
            owner = asset["unit"]
            if self.month == asset["purchase_month"]:
                self.asset_cost[aid] = amount(D(asset["cost_usd"]) * D(self.case["cost_factor"]))
                self.asset_accum[aid] = D(0)
                event = self.event(
                    "ASSET_RECEIPT",
                    aid,
                    owner,
                    site=asset["site"],
                    cost_center=asset["cost_center"],
                    amount_usd=money(self.asset_cost[aid]),
                )
                self.post(
                    event,
                    owner,
                    [("BIZ_PPE", self.asset_cost[aid]), ("1000", -self.asset_cost[aid])],
                    "Reusable owned equipment purchase; conditional investing cash request",
                )
            if asset.get("transfer_month", 999) <= self.month:
                owner = asset["transfer_unit"]
                if asset["transfer_month"] == self.month:
                    event = self.event(
                        "QUALIFIED_ASSET_TRANSFER",
                        aid,
                        owner,
                        from_unit=asset["unit"],
                        qualified=asset["qualified"],
                        cost_usd=money(self.asset_cost[aid]),
                        accumulated_usd=money(self.asset_accum[aid]),
                    )
                    # Internal same-entity transfer moves gross and accumulated basis without gain.
                    net = self.asset_cost[aid] - self.asset_accum[aid]
                    self.post(
                        event,
                        asset["unit"],
                        [
                            ("BIZ_PPE", -self.asset_cost[aid]),
                            ("BIZ_ACCUM", self.asset_accum[aid]),
                            ("BIZ_UNIT_CLEARING", net),
                        ],
                        "Transfer carrying basis out; paired same-entity management reclassification",
                    )
                    self.post(
                        event,
                        owner,
                        [
                            ("BIZ_PPE", self.asset_cost[aid]),
                            ("BIZ_ACCUM", -self.asset_accum[aid]),
                            ("BIZ_UNIT_CLEARING", -net),
                        ],
                        "Transfer carrying basis in; no enterprise gain or cash",
                    )
            if self.month > asset["purchase_month"]:
                charge = min(
                    amount(self.asset_cost[aid] / asset["life_months"]),
                    self.asset_cost[aid] - self.asset_accum[aid],
                )
                self.asset_accum[aid] += charge
                event = self.event("DEPRECIATION", aid, owner, amount_usd=money(charge))
                self.post(
                    event,
                    owner,
                    [("BIZ_DDA", charge), ("BIZ_ACCUM", -charge)],
                    "Depreciation starts following receipt; transferred asset retains basis",
                )
            self.tables["asset_rollforward"].append(
                {
                    "scenario": self.scenario,
                    "period": period(self.month)[2],
                    "asset_id": aid,
                    "unit": owner,
                    "original_site": asset["site"],
                    "cost_usd": money(self.asset_cost[aid]),
                    "accumulated_usd": money(self.asset_accum[aid]),
                    "net_book_usd": money(self.asset_cost[aid] - self.asset_accum[aid]),
                }
            )

    def recovery(self):
        streams = self.inputs["recovery"]
        unit = "project-cradle"
        for stream in ("stream17", "demotte"):
            r = streams[stream]
            if stream == "stream17":
                availability = D(self.case["mineral_availability"])
                feed = D(r["monthly_feed_tonnes"]) * availability
                contained = feed * 1000 * D(r["contained_reo_fraction"])
                recovered = amount(contained * D(self.case["mineral_recovery"]))
                basis_unit = "MINERAL_TONNES"
                cost = amount(
                    feed * D(r["processing_usd_per_feed_tonne"]) * D(self.case["cost_factor"])
                )
            else:
                gen2 = self.month >= r["gen2_from_month"]
                availability = D(r["gen2_availability"] if gen2 else r["gen1_availability"])
                bypass = self.month in r["hard_bypass_months"]
                if bypass:
                    availability = D(0)
                feed = D(r["monthly_water_m3"]) * availability
                # m3 * 1000 L/m3 * mg/L / 1,000,000 mg/kg = m3*mg/L/1000 kg.
                contained = feed * D(r["concentration_mg_l"]) / 1000
                recovered = amount(
                    contained * D(r["gen2_recovery"] if gen2 else r["gen1_recovery"])
                )
                basis_unit = "WATER_M3"
                cost = amount(
                    D(r["monthly_reagent_and_lab_usd"])
                    * D(self.case["cost_factor"])
                    * (D("0.25") if bypass else 1)
                )
            lot_id = f"{stream.upper()}-{self.scenario}-{self.month:02}"
            event = self.event(
                "RECOVERY_RUN",
                lot_id,
                unit,
                stream=stream,
                host=r["host"],
                site=r["site"],
                feed_unit=basis_unit,
                feed_quantity=money(feed),
                contained_kg=money(contained),
                recovered_kg=money(recovered),
                availability=str(availability),
                bypass=availability == 0,
                custody="CAPTURED_MATERIAL_TITLE_AT_DECLARED_RECOVERY_POINT",
                operating_authority="HOST_PRIMARY_OPERATION_AND_STOP_AUTHORITY",
            )
            self.cost(f"PROCESS-{lot_id}", unit, "BIZ_PROCESSING", cost)
            if not recovered:
                continue
            cost_basis = D(0)
            if stream == "stream17":
                direct_labor = amount(
                    self.payroll[unit]
                    * D(r["direct_payroll_fte"])
                    / self.policy["workforce"][unit]["occupied"]
                )
                cost_basis = amount(cost + direct_labor)
                self.post(
                    event,
                    unit,
                    [
                        ("BIZ_INVENTORY", cost_basis),
                        ("BIZ_PROCESSING", -cost),
                        ("BIZ_PAYROLL", -direct_labor),
                    ],
                    "Cost captured Stream 17 lot; no duplicated direct expense",
                )
            price = D(r["realized_usd_per_kg"]) * D(self.case["price_factor"])
            sale_value = amount(recovered * D(r["assay_payable_fraction"]) * price)
            freight = amount(
                recovered
                * D(r.get("bedford_and_freight_usd_per_kg", 0))
                * D(self.case["cost_factor"])
            )
            nrv = max(sale_value * (1 - D(r["host_share"])) - freight, D(0))
            impairment = max(cost_basis - amount(nrv), D(0))
            if impairment:
                self.post(
                    event,
                    unit,
                    [("BIZ_INVENTORY_LOSS", impairment), ("BIZ_INVENTORY", -impairment)],
                    "Captured lot written to modeled assayed net realizable value",
                )
                cost_basis -= impairment
            lot = {
                "lot_id": lot_id,
                "scenario": self.scenario,
                "unit": unit,
                "stream": stream,
                "host": r["host"],
                "capture_month": self.month,
                "source_id": event,
                "bedford_batch_id": f"BEDFORD-{lot_id}",
                "recovered_kg": money(recovered),
                "payable_kg": money(recovered * D(r["assay_payable_fraction"])),
                "cost_usd": money(cost_basis),
                "impairment_usd": money(impairment),
                "sale_value_usd": money(sale_value),
                "freight_usd": money(freight),
                "host_share": r["host_share"],
                "accept_month": self.month
                + r["sale_lag_months"]
                + self.case["acceptance_delay_months"],
                "status": "CAPTURED_UNSOLD",
            }
            self.lots.append(lot)
        for lot in self.lots:
            if lot["accept_month"] != self.month:
                continue
            event = self.event(
                "DOWNSTREAM_ACCEPTANCE",
                lot["lot_id"],
                unit,
                bedford_batch_id=lot["bedford_batch_id"],
                payable_kg=lot["payable_kg"],
                host=lot["host"],
                sales_value_usd=lot["sale_value_usd"],
            )
            self.invoice(
                event,
                unit,
                "SYN-SPECIALIST-REFINER",
                lot["sale_value_usd"],
                host_share=lot["host_share"],
            )
            value = D(lot["cost_usd"])
            self.post(
                event,
                unit,
                [("BIZ_COGS", value), ("BIZ_INVENTORY", -value)],
                "Accepted lot releases its cost; capture alone is not revenue",
            )
            self.cost(f"FREIGHT-{lot['lot_id']}", unit, "BIZ_DELIVERY", lot["freight_usd"])
            lot["status"] = "ACCEPTED_SALE"
        unsold = [lot for lot in self.lots if lot["status"] == "CAPTURED_UNSOLD"]
        self.tables["inventory_rollforward"].append(
            {
                "scenario": self.scenario,
                "period": period(self.month)[2],
                "unit": unit,
                "unsold_lots": len(unsold),
                "unsold_kg": money(sum(D(l["recovered_kg"]) for l in unsold)),
                "closing_cost_usd": money(sum(D(l["cost_usd"]) for l in unsold)),
            }
        )

    def close(self):
        for unit in UNITS:
            open_ar = [r for r in self.invoices if r["unit"] == unit and D(r["remaining_usd"])]
            allowance = amount(
                sum((D(r["remaining_usd"]) for r in open_ar), D(0))
                * D(self.policy["expected_credit_loss_rate"])
            )
            change = allowance + self.balances[unit]["BIZ_ALLOWANCE"]
            event = self.event("MONTH_END_ESTIMATE", unit, unit, allowance_usd=money(allowance))
            self.post(
                event,
                unit,
                [("BIZ_CREDIT_LOSS", change), ("BIZ_ALLOWANCE", -change)],
                "Explicit expected credit-loss estimate, not observed customer default",
            )
            for r in open_ar:
                self.tables["receivable_aging"].append(
                    {
                        "scenario": self.scenario,
                        "period": period(self.month)[2],
                        "unit": unit,
                        "invoice_id": r["invoice_id"],
                        "customer_id": r["customer_id"],
                        "due_date": r["due_date"],
                        "months_past_due": max(self.month - r["due_month"], 0),
                        "outstanding_usd": r["remaining_usd"],
                    }
                )
            pending = [p for p in self.payables if p["unit"] == unit and D(p["remaining_usd"])]
            self.tables["subledger_rollforward"].append(
                {
                    "scenario": self.scenario,
                    "period": period(self.month)[2],
                    "unit": unit,
                    "gross_ar_usd": money(sum(D(r["remaining_usd"]) for r in open_ar)),
                    "allowance_usd": money(allowance),
                    "vendor_ap_usd": money(sum(D(p["remaining_usd"]) for p in pending)),
                    "deferred_revenue_usd": money(-self.balances[unit]["BIZ_DEFERRED"]),
                    "host_payable_usd": money(-self.balances[unit]["BIZ_HOST_AP"]),
                    "inventory_usd": money(self.balances[unit]["BIZ_INVENTORY"]),
                    "gross_ppe_usd": money(self.balances[unit]["BIZ_PPE"]),
                    "accumulated_depreciation_usd": money(-self.balances[unit]["BIZ_ACCUM"]),
                }
            )
            if self.balances[unit]["BIZ_AR"] != sum((D(r["remaining_usd"]) for r in open_ar), D(0)):
                raise ValueError("AR subledger mismatch")
            if -self.balances[unit]["BIZ_AP"] != sum(
                (D(r["remaining_usd"]) for r in pending), D(0)
            ):
                raise ValueError("Vendor AP subledger mismatch")
            if self.balances[unit]["BIZ_INVENTORY"] < 0 or self.balances[unit]["BIZ_DEFERRED"] > 0:
                raise ValueError("Negative inventory/deferred-revenue liability")
        inventory = sum(
            (D(l["cost_usd"]) for l in self.lots if l["status"] == "CAPTURED_UNSOLD"), D(0)
        )
        if inventory != self.balances["project-cradle"]["BIZ_INVENTORY"]:
            raise ValueError("Costed lot inventory fails ledger reconciliation")

    def build(self):
        if self._built:
            return self
        for scenario, case in self.policy["cases"].items():
            self.scenario, self.case = scenario, case
            self.sequence = 0
            self.balances = defaultdict(lambda: defaultdict(D))
            self.invoices, self.payables, self.host_payables, self.lots = [], [], [], []
            self.invoice_ids, self.accepted, self.churned = set(), set(), set()
            self.contract_starts, self.work_done, self.asset_cost, self.asset_accum = {}, {}, {}, {}
            self.matter_started, self.certified, self.measurement_due = set(), set(), {}
            for month in range(1, 61):
                self.month = month
                self.settle()
                self.workforce()
                self.subscriptions()
                self.outcomes()
                self.product_outcomes()
                self.research()
                self.recovery()
                self.close()
            self.tables["invoices"].extend(self.invoices)
            self.tables["payables"].extend(self.payables)
            self.tables["recovery_lots"].extend(self.lots)
        self._built = True
        return self

    def post_month(self, books, year, month):
        """Import complete source journals; enterprise retains treasury/ownership authority."""
        rows = self.by_month[books.scenario, year, month]
        grouped = defaultdict(list)
        for row in rows:
            grouped[row["journal_id"]].append(row)
        for journal in grouped.values():
            first = journal[0]
            books.post(
                "SHI",
                year,
                month,
                [(r["account"], amount(r["signed_usd"]), r["cash_flow"]) for r in journal],
                first["source_id"],
                first["description"],
                kind="BUSINESS_DRIVEN_FORECAST",
                segment=first["segment"],
            )
