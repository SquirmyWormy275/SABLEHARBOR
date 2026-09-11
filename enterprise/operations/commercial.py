"""Causal commercial histories over the preserved synthetic contract population.

Service capacity and explicit customer decisions govern activation and renewals.
Contract changes alter actual invoice, recognition, credit and ARR movements.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal as D

from enterprise.business.model import amount, money, period

PRODUCT_UNITS = ("foundry-field", "atlas-meridian")
COMPONENTS = ("new", "expansion", "price", "contraction", "churn")


def _row(model, unit, **fields):
    return {
        "scenario": model.scenario,
        "period": period(model.month)[2],
        "month_index": model.month,
        "unit": unit,
        "fact_state": "PUBLIC_SYNTHETIC_CONDITIONAL_FORECAST",
        **fields,
    }


def start_scenario(model):
    """Reset scenario state without mutating any baseline or operations input."""
    config = model.operations_inputs["commercial"]
    if not 0 <= D(config["service_capacity_fraction"]) <= D("0.20"):
        raise ValueError("Shared service fraction may not consume Atlas outcome capacity")
    if config["renewal_breach_threshold"] < 1:
        raise ValueError("Renewal breach threshold must be positive")
    contracts = {r["contract_id"]: r for r in model.inputs["contracts"]}
    ids = set()
    for change in config["changes"]:
        if change["change_id"] in ids or change["contract_id"] not in contracts:
            raise ValueError("Duplicate amendment or unknown commercial contract")
        ids.add(change["change_id"])
        if change["effective_month"] < 1 or not change["approval_id"]:
            raise ValueError("Changes require a dated synthetic approval")
        delta = D(change["monthly_delta_usd"])
        if change["kind"] not in {"EXPANSION", "PRICE", "CONTRACTION", "CANCELLATION"}:
            raise ValueError("Unknown commercial change kind")
        if (change["kind"] in {"EXPANSION", "PRICE"} and delta < 0) or (
            change["kind"] == "CONTRACTION" and delta > 0
        ):
            raise ValueError("Amendment sign contradicts movement class")
    for section, identity in (("pipeline", "contract_id"), ("incidents", "incident_id")):
        seen = set()
        for row in config[section]:
            if row[identity] in seen or row["contract_id"] not in contracts:
                raise ValueError("Duplicate or unknown commercial source")
            seen.add(row[identity])
            if section == "pipeline":
                if set(row["outcomes"]) != set(model.policy["cases"]) or set(
                    row["decision_months"]
                ) != set(model.policy["cases"]):
                    raise ValueError("Pipeline needs all scenario decisions")
                if any(v not in {"WON", "LOST", "HELD"} for v in row["outcomes"].values()):
                    raise ValueError("Unknown pipeline state")
                if min(row["decision_months"].values()) < 1:
                    raise ValueError("Pipeline decision precedes horizon")
            elif D(row["required_hours"]) < 0 or not 0 <= D(row["service_credit_fraction"]) <= 1:
                raise ValueError("Invalid service incident hours or credit")
    model.commercial_state = {
        cid: {
            "contract": contract,
            "rate": D(0),
            "seats": contract["seats"],
            "term": 0,
            "term_end": 0,
            "deferred": D(0),
            "claims": [],
            "version": 0,
            "breaches": [],
        }
        for cid, contract in contracts.items()
    }
    model.commercial_done_changes = set()
    model.commercial_incidents = {}
    model.commercial_previous_arr = defaultdict(D)
    model.commercial_pipeline_overrides = {r["contract_id"]: r for r in config["pipeline"]}


class CommercialMixin:
    def _commercial_version(self, cid, reason, approval, effective_month):
        state = self.commercial_state[cid]
        state["version"] += 1
        self.tables["contract_versions"].append(
            _row(
                self,
                state["contract"]["unit"],
                contract_id=cid,
                version=state["version"],
                reason=reason,
                approval_id=approval,
                original_effective_month=effective_month,
                applied_month=self.month,
                monthly_rate_usd=money(state["rate"]),
                seats=state["seats"],
                term=state["term"],
                term_end_month=state["term_end"],
            )
        )

    def _commercial_bill(self, cid, source, value, movement):
        value = amount(value)
        if not value:
            return
        state = self.commercial_state[cid]
        contract = state["contract"]
        self.invoice(source, contract["unit"], contract["customer_id"], value, deferred=True)
        invoice = self.invoices[-1]
        if invoice["source_id"] != source:
            raise ValueError("Commercial invoice source identity changed")
        state["claims"].append({"invoice": invoice, "unearned": value})
        state["deferred"] += value
        movement["billings"] += value

    def _commercial_reduce(self, cid, value, reason, movement):
        state = self.commercial_state[cid]
        remaining = amount(value)
        if remaining > state["deferred"] or remaining < 0:
            raise ValueError("Commercial credit exceeds unearned service")
        for claim in reversed(state["claims"]):
            credit = min(remaining, claim["unearned"])
            if not credit:
                continue
            self.issue_credit(
                claim["invoice"]["invoice_id"],
                credit,
                reason,
                deferred=True,
                credit_id=f"{reason}-{claim['invoice']['invoice_id']}",
            )
            claim["unearned"] -= credit
            remaining -= credit
            state["deferred"] -= credit
            movement["credits"] += credit
        if remaining:
            raise ValueError("Deferred credit cannot be traced to an invoice")

    def subscriptions(self):
        config = self.operations_inputs["commercial"]
        movements = defaultdict(lambda: defaultdict(D))
        deferred = {
            cid: {
                "opening": state["deferred"],
                "billings": D(0),
                "credits": D(0),
                "recognized": D(0),
            }
            for cid, state in self.commercial_state.items()
        }
        available = {
            unit: amount(self.capacity[unit] * D(config["service_capacity_fraction"]))
            for unit in PRODUCT_UNITS
        }
        capacity = dict(available)
        support_required, support_served, incident_served, deployment_served = (
            defaultdict(D) for _ in range(4)
        )
        incident_required = defaultdict(D)
        # Existing customers reserve routine support before incident/deployment work.
        for cid, state in self.commercial_state.items():
            if cid not in self.contract_starts or cid in self.churned:
                continue
            unit = state["contract"]["unit"]
            required = D(self.policy["support_hours_per_customer"])
            served = min(required, available[unit])
            support_required[unit] += required
            support_served[unit] += served
            available[unit] -= served
            self.tables["commercial_service_tickets"].append(
                _row(
                    self,
                    unit,
                    ticket_id=f"SUPPORT-{cid}-{self.month}",
                    contract_id=cid,
                    required_hours=money(required),
                    served_hours=money(served),
                    backlog_hours=money(required - served),
                    status="COMPLETE" if served == required else "BACKLOG",
                )
            )
        for source in config["incidents"]:
            cid, iid = source["contract_id"], source["incident_id"]
            if (
                source["start_month"] <= self.month
                and cid in self.contract_starts
                and cid not in self.churned
                and iid not in self.commercial_incidents
            ):
                self.commercial_incidents[iid] = {
                    "source": source,
                    "remaining": D(source["required_hours"]),
                    "breached": False,
                    "credited": False,
                    "closed": False,
                }
        for iid, incident in self.commercial_incidents.items():
            if incident["closed"]:
                continue
            source = incident["source"]
            cid = source["contract_id"]
            unit = self.commercial_state[cid]["contract"]["unit"]
            opening = incident["remaining"]
            incident_required[unit] += opening
            served = min(opening, available[unit])
            incident_served[unit] += served
            available[unit] -= served
            incident["remaining"] -= served
            if incident["remaining"] and not incident["breached"]:
                incident["breached"] = True
                self.commercial_state[cid]["breaches"].append(self.month)
            incident["closed"] = incident["remaining"] == 0
            self.tables["service_incidents"].append(
                _row(
                    self,
                    unit,
                    incident_id=iid,
                    contract_id=cid,
                    requested_month=source["start_month"],
                    severity=source["severity"],
                    opening_hours=money(opening),
                    served_hours=money(served),
                    remaining_hours=money(incident["remaining"]),
                    sla_breached=incident["breached"],
                    status="RESOLVED" if incident["closed"] else "OPEN",
                )
            )
        for cid, state in self.commercial_state.items():
            contract, unit = state["contract"], state["contract"]["unit"]
            override = self.commercial_pipeline_overrides.get(cid)
            decision_month = (
                override["decision_months"][self.scenario] if override else contract["start_month"]
            )
            outcome = override["outcomes"][self.scenario] if override else "WON"
            decision = "HELD" if self.month < decision_month else outcome
            planned = max(contract["start_month"], decision_month) + (
                self.case["acceptance_delay_months"] if contract["deployment_fee_usd"] else 0
            )
            if cid not in self.contract_starts and self.month >= contract["start_month"]:
                status = decision
                if decision == "WON" and self.month >= planned:
                    effort = (
                        amount(D(self.policy["deployment_hours"]) * D(self.case["rework_factor"]))
                        if contract["deployment_fee_usd"]
                        else D(0)
                    )
                    # Newly accepted customers also reserve this month's routine support.
                    routine = D(self.policy["support_hours_per_customer"])
                    if effort + routine <= available[unit]:
                        available[unit] -= effort + routine
                        deployment_served[unit] += effort
                        support_required[unit] += routine
                        support_served[unit] += routine
                        self.tables["commercial_service_tickets"].append(
                            _row(
                                self,
                                unit,
                                ticket_id=f"SUPPORT-{cid}-{self.month}",
                                contract_id=cid,
                                required_hours=money(routine),
                                served_hours=money(routine),
                                backlog_hours=money(0),
                                status="COMPLETE",
                            )
                        )
                        self.contract_starts[cid] = self.month
                        state["rate"] = amount(
                            D(contract["monthly_subscription_usd"]) * D(self.case["price_factor"])
                        )
                        state["term_end"] = self.month + 12
                        event = self.event(
                            "DEPLOYMENT_ACCEPTANCE",
                            cid,
                            unit,
                            approved_hours=money(effort),
                            customer_id=contract["customer_id"],
                            authority="MODELED_CUSTOMER_ACCEPTANCE_NOT_OPERATING_AUTHORITY",
                        )
                        self.invoice(
                            event,
                            unit,
                            contract["customer_id"],
                            D(contract["deployment_fee_usd"]) * D(self.case["price_factor"]),
                        )
                        self._commercial_bill(
                            cid, f"{cid}-TERM-0", state["rate"] * 12, deferred[cid]
                        )
                        movements[unit]["new"] += state["rate"] * 12
                        self._commercial_version(
                            cid, "ACTIVATION", "SYNTHETIC_CUSTOMER_ACCEPTANCE", self.month
                        )
                        status = "ACTIVATED"
                    else:
                        status = "CAPACITY_HELD"
                        self.event(
                            "DEPLOYMENT_BACKLOG", cid, unit, hours_required=money(effort + routine)
                        )
                elif decision == "WON":
                    status = "ACCEPTANCE_HELD"
                self.tables["commercial_pipeline"].append(
                    _row(
                        self,
                        unit,
                        contract_id=cid,
                        decision_id=override["decision_id"] if override else f"SYN-PIPE-{cid}",
                        decision_month=decision_month,
                        planned_activation_month=planned,
                        outcome=decision,
                        status=status,
                    )
                )
            if (
                cid in self.contract_starts
                and cid not in self.churned
                and self.month == state["term_end"]
            ):
                prior = state["rate"]
                breaches = sum(self.month - 12 <= m < self.month for m in state["breaches"])
                incident_failure = breaches >= config["renewal_breach_threshold"]
                baseline_churn = int(cid.split("-")[-1]) % self.case["churn_modulus"] == 0
                decline = incident_failure or baseline_churn
                self.tables["commercial_renewals"].append(
                    _row(
                        self,
                        unit,
                        contract_id=cid,
                        term=state["term"] + 1,
                        decision="DECLINED" if decline else "RENEWED",
                        cause="SERVICE_BREACH"
                        if incident_failure
                        else "BASELINE_SCENARIO_CHURN"
                        if baseline_churn
                        else "SYNTHETIC_CUSTOMER_RENEWAL",
                        lookback_breaches=breaches,
                        prior_monthly_usd=money(prior),
                    )
                )
                if decline:
                    self.churned.add(cid)
                    movements[unit]["churn"] += prior * 12
                    state["rate"] = D(0)
                    self.event("CHURN", cid, unit, renewal_term=state["term"] + 1)
                    self._commercial_version(
                        cid, "RENEWAL_DECLINED", "SYNTHETIC_CUSTOMER_DECISION", self.month
                    )
                else:
                    state["term"] += 1
                    state["term_end"] += 12
                    state["rate"] = amount(
                        prior * (1 + D(self.policy["annual_subscription_escalation"]))
                    )
                    movements[unit]["price"] += (state["rate"] - prior) * 12
                    self._commercial_bill(
                        cid, f"{cid}-TERM-{state['term']}", state["rate"] * 12, deferred[cid]
                    )
                    self._commercial_version(
                        cid, "RENEWAL", "SYNTHETIC_CUSTOMER_RENEWAL", self.month
                    )
            for change in config["changes"]:
                change_id = change["change_id"]
                if (
                    change["contract_id"] != cid
                    or change_id in self.commercial_done_changes
                    or change["effective_month"] > self.month
                ):
                    continue
                if cid in self.churned or decision == "LOST":
                    status = "NOT_APPLICABLE_CLOSED"
                    self.commercial_done_changes.add(change_id)
                elif cid not in self.contract_starts:
                    status = "HELD_PENDING_ACTIVATION"
                else:
                    prior = state["rate"]
                    delta = amount(D(change["monthly_delta_usd"]) * D(self.case["price_factor"]))
                    new = D(0) if change["kind"] == "CANCELLATION" else prior + delta
                    if new < 0 or state["seats"] + change["seat_delta"] < 0:
                        raise ValueError("Amendment creates negative rate or seats")
                    delta = new - prior
                    months_remaining = state["term_end"] - self.month
                    if delta > 0:
                        self._commercial_bill(
                            cid, f"{cid}-{change_id}", delta * months_remaining, deferred[cid]
                        )
                    elif delta < 0:
                        self._commercial_reduce(
                            cid, -delta * months_remaining, change_id, deferred[cid]
                        )
                    component = (
                        "churn" if change["kind"] == "CANCELLATION" else change["kind"].lower()
                    )
                    movements[unit][component] += abs(delta) * 12
                    state["rate"] = new
                    state["seats"] += change["seat_delta"]
                    if change["kind"] == "CANCELLATION":
                        self.churned.add(cid)
                    self.commercial_done_changes.add(change_id)
                    self._commercial_version(
                        cid, change["kind"], change["approval_id"], change["effective_month"]
                    )
                    status = "APPLIED"
                self.tables["commercial_changes"].append(
                    _row(
                        self,
                        unit,
                        contract_id=cid,
                        change_id=change_id,
                        kind=change["kind"],
                        original_effective_month=change["effective_month"],
                        approval_id=change["approval_id"],
                        applied_month=self.month if status == "APPLIED" else 0,
                        status=status,
                    )
                )
            if cid not in self.contract_starts or cid in self.churned:
                continue
            rate = state["rate"]
            event = self.event(
                "SUBSCRIPTION_SERVICE",
                cid,
                unit,
                customer_id=contract["customer_id"],
                monthly_revenue_usd=money(rate),
                annual_recurring_usd=money(rate * 12),
                seats=state["seats"],
                term=state["term"],
            )
            self.post(
                event,
                unit,
                [("BIZ_DEFERRED", rate), ("BIZ_REVENUE", -rate)],
                "Monthly service under effective contract version",
            )
            state["deferred"] -= rate
            deferred[cid]["recognized"] += rate
            consume = rate
            for claim in state["claims"]:
                recognized = min(consume, claim["unearned"])
                claim["unearned"] -= recognized
                consume -= recognized
            if consume:
                raise ValueError("Recognized service lacks billed deferred balance")
            self.cost(
                f"HOSTING-{cid}",
                unit,
                "BIZ_DELIVERY",
                D(contract["compute_monthly_usd"]) * D(self.case["cost_factor"]),
            )
            for iid, incident in self.commercial_incidents.items():
                if (
                    incident["source"]["contract_id"] != cid
                    or not incident["breached"]
                    or incident["credited"]
                ):
                    continue
                credit = amount(rate * D(incident["source"]["service_credit_fraction"]))
                if not credit:
                    incident["credited"] = True
                    continue
                # Follow earned invoice claims: this also handles a zero-priced
                # original term later expanded by an incremental invoice.
                remaining_credit = credit
                for claim in reversed(state["claims"]):
                    invoice = claim["invoice"]
                    earned_available = max(
                        D(invoice["amount_usd"]) - D(invoice["credit_usd"]) - claim["unearned"],
                        D(0),
                    )
                    portion = min(remaining_credit, earned_available)
                    if portion:
                        self.issue_credit(
                            invoice["invoice_id"],
                            portion,
                            "SLA_SERVICE_CREDIT",
                            credit_id=f"{iid}-{invoice['invoice_id']}",
                        )
                        remaining_credit -= portion
                    if not remaining_credit:
                        break
                if remaining_credit:
                    raise ValueError("SLA credit lacks earned invoice evidence")
                incident["credited"] = True
        for cid, state in self.commercial_state.items():
            movement = deferred[cid]
            closing = (
                movement["opening"]
                + movement["billings"]
                - movement["credits"]
                - movement["recognized"]
            )
            if (
                closing != state["deferred"]
                or closing < 0
                or closing != sum((c["unearned"] for c in state["claims"]), D(0))
            ):
                raise ValueError("Contract deferred revenue failed reconciliation")
            self.tables["commercial_deferred_rollforward"].append(
                _row(
                    self,
                    state["contract"]["unit"],
                    contract_id=cid,
                    opening_usd=money(movement["opening"]),
                    billings_usd=money(movement["billings"]),
                    credits_usd=money(movement["credits"]),
                    recognized_usd=money(movement["recognized"]),
                    closing_usd=money(closing),
                )
            )
        for unit in PRODUCT_UNITS:
            active = [
                s
                for cid, s in self.commercial_state.items()
                if s["contract"]["unit"] == unit
                and cid in self.contract_starts
                and cid not in self.churned
            ]
            total = sum((s["rate"] for s in active), D(0))
            opening, closing = self.commercial_previous_arr[unit], total * 12
            bridge = movements[unit]
            calculated = (
                opening
                + bridge["new"]
                + bridge["expansion"]
                + bridge["price"]
                - bridge["contraction"]
                - bridge["churn"]
            )
            if calculated != closing:
                raise ValueError("Commercial ARR bridge does not reconcile")
            self.tables["commercial_arr_bridge"].append(
                _row(
                    self,
                    unit,
                    opening_arr_usd=money(opening),
                    closing_arr_usd=money(closing),
                    **{f"{key}_arr_usd": money(bridge[key]) for key in COMPONENTS},
                )
            )
            self.commercial_previous_arr[unit] = closing
            self.tables["commercial_capacity"].append(
                _row(
                    self,
                    unit,
                    capacity_hours=money(capacity[unit]),
                    routine_required_hours=money(support_required[unit]),
                    routine_served_hours=money(support_served[unit]),
                    incident_required_hours=money(incident_required[unit]),
                    incident_served_hours=money(incident_served[unit]),
                    deployment_served_hours=money(deployment_served[unit]),
                    unused_hours=money(available[unit]),
                )
            )
            self.tables["commercial_metrics"].append(
                _row(
                    self,
                    unit,
                    active_customers=len(active),
                    arr_usd=money(closing),
                    largest_customer_share=str(
                        max((s["rate"] for s in active), default=D(0)) / (total or 1)
                    ),
                    support_required_hours=money(support_required[unit] + incident_required[unit]),
                    support_capacity_hours=money(capacity[unit]),
                    support_backlog_hours=money(
                        support_required[unit]
                        - support_served[unit]
                        + incident_required[unit]
                        - incident_served[unit]
                    ),
                )
            )
            deferred_total = sum(
                (
                    s["deferred"]
                    for s in self.commercial_state.values()
                    if s["contract"]["unit"] == unit
                ),
                D(0),
            )
            if deferred_total != -self.balances[unit]["BIZ_DEFERRED"]:
                raise ValueError("Commercial deferred subledger differs from general ledger")


def validate(model):
    """Independently reperform exported mathematical and population controls."""
    expected = {
        (scenario, month, unit)
        for scenario in model.policy["cases"]
        for month in range(1, 61)
        for unit in PRODUCT_UNITS
    }
    actual = [
        (r["scenario"], r["month_index"], r["unit"]) for r in model.tables["commercial_arr_bridge"]
    ]
    if set(actual) != expected or len(actual) != len(expected):
        raise ValueError("Commercial monthly coverage is incomplete or duplicated")
    prior = defaultdict(D)
    for row in model.tables["commercial_arr_bridge"]:
        key = (row["scenario"], row["unit"])
        opening = D(row["opening_arr_usd"])
        if opening != prior[key]:
            raise ValueError("ARR opening does not equal prior close")
        closing = (
            opening
            + sum((D(row[f"{k}_arr_usd"]) for k in ("new", "expansion", "price")), D(0))
            - sum((D(row[f"{k}_arr_usd"]) for k in ("contraction", "churn")), D(0))
        )
        if closing != D(row["closing_arr_usd"]):
            raise ValueError("Exported ARR bridge mismatch")
        prior[key] = closing
    deferred_expected = {
        (scenario, month, contract["contract_id"])
        for scenario in model.policy["cases"]
        for month in range(1, 61)
        for contract in model.inputs["contracts"]
    }
    deferred_actual = [
        (r["scenario"], r["month_index"], r["contract_id"])
        for r in model.tables["commercial_deferred_rollforward"]
    ]
    if set(deferred_actual) != deferred_expected or len(deferred_actual) != len(deferred_expected):
        raise ValueError("Deferred monthly contract coverage is incomplete or duplicated")
    prior_deferred = defaultdict(D)
    balances = defaultdict(D)
    for row in model.tables["commercial_deferred_rollforward"]:
        key = (row["scenario"], row["contract_id"])
        opening = D(row["opening_usd"])
        closing = (
            opening + D(row["billings_usd"]) - D(row["credits_usd"]) - D(row["recognized_usd"])
        )
        if opening != prior_deferred[key] or closing != D(row["closing_usd"]) or closing < 0:
            raise ValueError("Exported deferred revenue bridge mismatch")
        prior_deferred[key] = closing
        balances[row["scenario"], row["month_index"], row["unit"]] += closing
    for row in model.tables["subledger_rollforward"]:
        if (
            row["unit"] in PRODUCT_UNITS
            and D(row["deferred_revenue_usd"])
            != balances[
                row["scenario"],
                row.get(
                    "month_index", (int(row["period"][:4]) - 2027) * 12 + int(row["period"][5:7])
                ),
                row["unit"],
            ]
        ):
            raise ValueError("Exported deferred balances disagree with month-end books")
    for row in model.tables["commercial_capacity"]:
        used = sum(
            (
                D(row[k])
                for k in (
                    "routine_served_hours",
                    "incident_served_hours",
                    "deployment_served_hours",
                    "unused_hours",
                )
            ),
            D(0),
        )
        if used != D(row["capacity_hours"]) or any(
            D(row[k]) < 0 for k in row if k.endswith("_hours")
        ):
            raise ValueError("Commercial capacity overallocated")
    for row in model.tables["commercial_changes"]:
        if row["status"] == "APPLIED" and (
            row["applied_month"] < row["original_effective_month"] or not row["approval_id"]
        ):
            raise ValueError("Amendment applied without effective approval")
    return {
        "arr_bridges": len(model.tables["commercial_arr_bridge"]),
        "deferred_bridges": len(model.tables["commercial_deferred_rollforward"]),
        "status": "PASS",
    }
