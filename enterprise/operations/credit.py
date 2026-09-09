"""Invoice-specific credit histories and source-linked finite-funding allocation."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal as D

from enterprise.business.model import UNITS, amount, money, period


def start_scenario(model):
    model.credit_ids = set()
    policy = model.operations_inputs["credit"]
    ids = [p["source_id"] for p in policy["profiles"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate invoice credit profile")
    for value in policy["allowance_rates"].values():
        if not 0 <= D(value) <= 1:
            raise ValueError("Invalid allowance rate")
    for p in policy["profiles"]:
        if p["kind"] not in {"PARTIAL", "DISPUTED", "DEFAULT"}:
            raise ValueError("Unsupported credit profile")
        if not 0 <= D(p["first_fraction"]) <= 1:
            raise ValueError("Invalid initial collection fraction")
        if p["kind"] == "DEFAULT":
            if not 0 <= D(p["recovery_fraction"]) <= 1:
                raise ValueError("Invalid recovery fraction")
            if not 0 < p["writeoff_delay_months"] < p["recovery_delay_months"]:
                raise ValueError("Recovery must follow writeoff")
        elif p["final_delay_months"] < 1:
            raise ValueError("Final receipt must follow initial receipt")


class CreditMixin:
    def invoice(self, source, unit, customer, value, deferred=False, host_share="0"):
        if amount(value) < 0 or not 0 <= D(host_share) <= 1:
            raise ValueError("Invoice and host-share amounts must be nonnegative")
        super().invoice(source, unit, customer, value, deferred, host_share)
        if not amount(value):
            return None
        row = self.invoices[-1]
        profile = next(
            (p for p in self.operations_inputs["credit"]["profiles"] if p["source_id"] == source),
            None,
        )
        row.update(
            {
                "credit_profile": profile["profile_id"] if profile else "CONTRACTUAL",
                "credit_state": profile["kind"] if profile else "CURRENT",
                "collected_usd": "0.0000",
                "writtenoff_usd": "0.0000",
                "recovered_usd": "0.0000",
                "credit_usd": "0.0000",
                "writtenoff_credit_usd": "0.0000",
                "refunded_usd": "0.0000",
                "host_settled_usd": "0.0000",
            }
        )
        return row

    def _credit_history(self, invoice, action, value, source):
        self.tables["credit_history"].append(
            {
                "scenario": self.scenario,
                "unit": invoice["unit"],
                "period": period(self.month)[2],
                "month_index": self.month,
                "invoice_id": invoice["invoice_id"],
                "customer_id": invoice["customer_id"],
                "action": action,
                "amount_usd": money(value),
                "source_id": source,
                "due_date": invoice["due_date"],
                "invoice_amount_usd": invoice["amount_usd"],
                "remaining_usd": invoice["remaining_usd"],
                **{
                    k: invoice[k]
                    for k in (
                        "collected_usd",
                        "writtenoff_usd",
                        "recovered_usd",
                        "credit_usd",
                        "writtenoff_credit_usd",
                        "refunded_usd",
                    )
                },
                "record_origin": "PUBLIC_SYNTHETIC_PLANNING_MODEL",
            }
        )

    def _collect(self, invoice, value, recovery=False):
        value = amount(value)
        if not value:
            return
        event = self.event(
            "CREDIT_RECOVERY" if recovery else "COLLECTION",
            invoice["invoice_id"],
            invoice["unit"],
            invoice_id=invoice["invoice_id"],
            amount_usd=money(value),
        )
        self.post(
            event,
            invoice["unit"],
            [("1000", value), ("BIZ_CREDIT_LOSS" if recovery else "BIZ_AR", -value)],
            "Modeled post-writeoff recovery" if recovery else "Modeled customer receipt",
        )
        invoice["collected_usd"] = money(D(invoice["collected_usd"]) + value)
        if recovery:
            invoice["recovered_usd"] = money(D(invoice["recovered_usd"]) + value)
        else:
            invoice["remaining_usd"] = money(D(invoice["remaining_usd"]) - value)
        share = amount(value * D(invoice["host_share"]))
        if share:
            if recovery:
                self.post(
                    event,
                    invoice["unit"],
                    [("BIZ_HOST_SHARE", share), ("BIZ_HOST_AP", -share)],
                    "Recovered proceeds restore host entitlement",
                )
            self.host_payables.append(
                {
                    "source_id": invoice["invoice_id"],
                    "unit": invoice["unit"],
                    "due_month": self.month + 1,
                    "amount": share,
                    "settled": False,
                }
            )
        self._credit_history(invoice, "RECOVERY" if recovery else "RECEIPT", value, event)

    def _writeoff(self, invoice):
        value = D(invoice["remaining_usd"])
        if not value:
            return
        event = self.event(
            "CREDIT_WRITEOFF",
            invoice["invoice_id"],
            invoice["unit"],
            invoice_id=invoice["invoice_id"],
            amount_usd=money(value),
        )
        self.post(
            event,
            invoice["unit"],
            [("BIZ_CREDIT_LOSS", value), ("BIZ_AR", -value)],
            "Explicit synthetic default writes off remaining claim; allowance releases at close",
        )
        invoice["remaining_usd"] = "0.0000"
        invoice["writtenoff_usd"] = money(D(invoice["writtenoff_usd"]) + value)
        share = amount(value * D(invoice["host_share"]))
        self.post(
            event,
            invoice["unit"],
            [("BIZ_HOST_AP", share), ("BIZ_HOST_SHARE", -share)],
            "Uncollected default releases proceeds-based host entitlement",
        )
        self._credit_history(invoice, "WRITEOFF", value, event)

    def settle(self):
        profiles = {p["profile_id"]: p for p in self.operations_inputs["credit"]["profiles"]}
        for inv in self.invoices:
            profile = profiles.get(inv["credit_profile"])
            due = inv["collection_month"]
            if self.month == due:
                target = (
                    amount(D(inv["amount_usd"]) * D(profile["first_fraction"]))
                    if profile
                    else D(inv["remaining_usd"])
                )
                self._collect(inv, min(target, D(inv["remaining_usd"])))
            if (
                profile
                and profile["kind"] != "DEFAULT"
                and self.month == due + profile["final_delay_months"]
            ):
                self._collect(inv, D(inv["remaining_usd"]))
                inv["credit_state"] = "RESOLVED"
            if profile and profile["kind"] == "DEFAULT":
                if self.month == due + profile["writeoff_delay_months"]:
                    self._writeoff(inv)
                if self.month == due + profile["recovery_delay_months"]:
                    claim = (
                        D(inv["writtenoff_usd"])
                        - D(inv["recovered_usd"])
                        - D(inv["writtenoff_credit_usd"])
                    )
                    self._collect(
                        inv,
                        min(claim, amount(D(inv["amount_usd"]) * D(profile["recovery_fraction"]))),
                        recovery=True,
                    )
        # Reuse the original vendor request engine without repeating invoice/host settlements.
        invoices, hosts = self.invoices, self.host_payables
        try:
            self.invoices, self.host_payables = [], []
            super().settle()
        finally:
            self.invoices, self.host_payables = invoices, hosts
        for payable in self.host_payables:
            if payable["due_month"] != self.month or payable["settled"]:
                continue
            value = payable["amount"]
            inv = next(r for r in self.invoices if r["invoice_id"] == payable["source_id"])
            event = self.event(
                "HOST_SETTLEMENT_REQUEST",
                f"{inv['invoice_id']}-{self.month}",
                inv["unit"],
                invoice_id=inv["invoice_id"],
                amount_usd=money(value),
                settlement_state="CONDITIONAL_SUBJECT_TO_ENTERPRISE_FUNDING",
            )
            self.post(
                event,
                inv["unit"],
                [("BIZ_HOST_AP", value), ("1000", -value)],
                "Host cash request follows actual modeled customer receipt",
            )
            inv["host_settled_usd"] = money(D(inv["host_settled_usd"]) + value)
            payable["settled"] = True
            self.tables["host_collection_settlements"].append(
                {
                    "scenario": self.scenario,
                    "unit": inv["unit"],
                    "period": period(self.month)[2],
                    "invoice_id": inv["invoice_id"],
                    "source_id": event,
                    "amount_usd": money(value),
                    "collected_usd": inv["collected_usd"],
                    "state": "CASH_REQUEST_SUBJECT_TO_FINITE_ENTERPRISE_FUNDING",
                }
            )

    def issue_credit(self, invoice_id, value, reason, *, deferred=False, credit_id=None):
        inv = (
            invoice_id
            if isinstance(invoice_id, dict)
            else next((r for r in self.invoices if r["invoice_id"] == invoice_id), None)
        )
        if inv is None or inv not in self.invoices:
            raise ValueError("Credit requires an invoice in the active scenario")
        value = amount(value)
        if value <= 0 or value > D(inv["amount_usd"]) - D(inv["credit_usd"]):
            raise ValueError("Credit exceeds uncredited invoice amount")
        credit_id = credit_id or f"CN-{inv['invoice_id']}-{len(self.credit_ids) + 1}"
        if credit_id in self.credit_ids:
            raise ValueError("Duplicate credit-note identity")
        open_applied = min(value, D(inv["remaining_usd"]))
        written_claim = (
            D(inv["writtenoff_usd"]) - D(inv["recovered_usd"]) - D(inv["writtenoff_credit_usd"])
        )
        written_applied = min(value - open_applied, written_claim)
        refund = value - open_applied - written_applied
        if refund > D(inv["collected_usd"]) - D(inv["refunded_usd"]):
            raise ValueError("Refund lacks collected cash backing")
        pending_hosts = [
            r
            for r in self.host_payables
            if r["source_id"] == inv["invoice_id"] and not r["settled"]
        ]
        refund_share = amount(refund * D(inv["host_share"]))
        if refund_share > sum((r["amount"] for r in pending_hosts), D(0)):
            raise ValueError(
                "Host-paid refund requires a separately authorized host clawback; credit is held"
            )
        debit = "BIZ_DEFERRED" if deferred else "BIZ_REVENUE"
        if deferred and value > -self.balances[inv["unit"]]["BIZ_DEFERRED"]:
            raise ValueError("Unearned credit exceeds deferred revenue")
        event = self.event(
            "CREDIT_NOTE",
            credit_id,
            inv["unit"],
            invoice_id=inv["invoice_id"],
            amount_usd=money(value),
            reason=reason,
        )
        self.post(
            event,
            inv["unit"],
            [
                (debit, value),
                ("BIZ_AR", -open_applied),
                ("BIZ_CREDIT_LOSS", -written_applied),
                ("1000", -refund),
            ],
            "Credit reduces open claim, then written-off claim, then cash-backed refund",
        )
        inv["remaining_usd"] = money(D(inv["remaining_usd"]) - open_applied)
        inv["credit_usd"] = money(D(inv["credit_usd"]) + value)
        inv["writtenoff_credit_usd"] = money(D(inv["writtenoff_credit_usd"]) + written_applied)
        inv["refunded_usd"] = money(D(inv["refunded_usd"]) + refund)
        # Written-off host entitlement was already released at writeoff.
        release = amount((open_applied + refund) * D(inv["host_share"]))
        self.post(
            event,
            inv["unit"],
            [("BIZ_HOST_AP", release), ("BIZ_HOST_SHARE", -release)],
            "Credit reduces remaining realized-value host entitlement",
        )
        for p in pending_hosts:
            reduction = min(p["amount"], refund_share)
            p["amount"] -= reduction
            refund_share -= reduction
        self.credit_ids.add(credit_id)
        row = {
            "scenario": self.scenario,
            "unit": inv["unit"],
            "period": period(self.month)[2],
            "invoice_id": inv["invoice_id"],
            "credit_id": credit_id,
            "source_id": event,
            "reason": reason,
            "amount_usd": money(value),
            "debit_account": debit,
            "open_applied_usd": money(open_applied),
            "writtenoff_applied_usd": money(written_applied),
            "refund_usd": money(refund),
        }
        self.tables["credit_notes"].append(row)
        self._credit_history(inv, "CREDIT", value, event)
        return row

    def close(self):
        super().close()
        rates = self.operations_inputs["credit"]["allowance_rates"]
        for unit in UNITS:
            required = D(0)
            for inv in self.invoices:
                if inv["unit"] != unit or not D(inv["remaining_usd"]):
                    continue
                age = max(self.month - inv["due_month"], 0)
                risk = (
                    "default"
                    if inv["credit_state"] == "DEFAULT"
                    else "disputed"
                    if inv["credit_state"] == "DISPUTED"
                    else "past_due"
                    if age
                    else "current"
                )
                allowance = amount(D(inv["remaining_usd"]) * D(rates[risk]))
                required += allowance
                self.tables["credit_allowance"].append(
                    {
                        "scenario": self.scenario,
                        "unit": unit,
                        "period": period(self.month)[2],
                        "invoice_id": inv["invoice_id"],
                        "risk_grade": risk,
                        "months_past_due": age,
                        "gross_ar_usd": inv["remaining_usd"],
                        "rate": rates[risk],
                        "allowance_usd": money(allowance),
                    }
                )
            change = required + self.balances[unit]["BIZ_ALLOWANCE"]
            event = self.event("CREDIT_RISK_ESTIMATE", unit, unit, allowance_usd=money(required))
            self.post(
                event,
                unit,
                [("BIZ_CREDIT_LOSS", change), ("BIZ_ALLOWANCE", -change)],
                "Invoice-specific synthetic graded expected-credit-loss estimate",
            )
            roll = next(
                r
                for r in reversed(self.tables["subledger_rollforward"])
                if r["unit"] == unit and r["scenario"] == self.scenario
            )
            roll["allowance_usd"] = money(required)


def validate(model):
    for inv in model.tables["invoices"]:
        nums = {
            k: D(inv[k])
            for k in (
                "amount_usd",
                "remaining_usd",
                "collected_usd",
                "refunded_usd",
                "writtenoff_usd",
                "recovered_usd",
                "credit_usd",
                "writtenoff_credit_usd",
            )
        }
        if any(v < 0 for v in nums.values()):
            raise ValueError("Negative credit subledger amount")
        explained = (
            nums["remaining_usd"]
            + nums["collected_usd"]
            - nums["refunded_usd"]
            + nums["writtenoff_usd"]
            - nums["recovered_usd"]
            - nums["writtenoff_credit_usd"]
            + nums["credit_usd"]
        )
        if explained != nums["amount_usd"]:
            raise ValueError("Invoice credit/collection/writeoff reconciliation failed")
        if nums["recovered_usd"] + nums["writtenoff_credit_usd"] > nums["writtenoff_usd"]:
            raise ValueError("Recovered or credited written-off claim twice")
        if nums["refunded_usd"] > nums["collected_usd"]:
            raise ValueError("Refund lacks collection backing")
        entitlement = amount((nums["collected_usd"] - nums["refunded_usd"]) * D(inv["host_share"]))
        if D(inv["host_settled_usd"]) > entitlement + D("0.0002"):
            raise ValueError("Host settlement exceeds realized collected proceeds")
    return {
        "invoices": len(model.tables["invoices"]),
        "credit_actions": len(model.tables["credit_history"]),
        "credit_notes": len(model.tables["credit_notes"]),
        "status": "PASS",
    }


def allocate_treasury(model, enterprise_result):
    """Attribute existing funded/arrears amounts; never create money or alter legal journals."""
    names = ("treasury_obligations", "treasury_obligation_history", "treasury_reconciliation")
    for name in names:
        if model.tables[name]:
            raise ValueError("Treasury allocation may be built only once")
    flows = {
        "OPERATING": "CORE_UNPAID",
        "INVESTING": "BIZ_CAPITAL_UNPAID",
        "FINANCING": "BIZ_DEBT_UNPAID",
    }
    by_period = defaultdict(list)
    for row in enterprise_result["journal_rows"]:
        if row["entity"] == "SHI" and int(row["month"]) > 0:
            by_period[row["scenario"], int(row["year"]), int(row["month"])].append(row)
    events = {r["event_id"]: r for r in model.tables["events"]}
    queues = defaultdict(list)
    for (scenario, year, month), rows in sorted(by_period.items()):
        date = f"{year}-{month:02}-" + period((year - 2027) * 12 + month)[2].rsplit("-", 1)[1]
        for flow, account in flows.items():
            queue = queues[scenario, flow]
            opening = sum((D(r["unpaid_usd"]) for r in queue), D(0))
            requests = []
            for row_index, r in enumerate(rows):
                if r["account"] != "1000" or r["cash_flow"] != flow or D(r["signed_usd"]) >= 0:
                    continue
                if r["source_id"].startswith(("CORE-ARREARS-PAID-", "BUSINESS-ARREARS-PAID-")):
                    continue
                if flow != "OPERATING" and not (
                    r["source_type"] == "BUSINESS_DRIVEN_FORECAST"
                    or r["source_id"] == "CORE-PRINCIPAL"
                ):
                    continue
                event = events.get(r["source_id"], {})
                kind = (
                    "PAYROLL_BATCH"
                    if event.get("kind") == "PAYROLL_REQUEST"
                    else "VENDOR_INVOICE"
                    if event.get("kind") == "PAYMENT_REQUEST"
                    else "HOST_SETTLEMENT"
                    if event.get("kind") == "HOST_SETTLEMENT_REQUEST"
                    else "CAPITAL_REQUEST"
                    if flow == "INVESTING"
                    else "DEBT_REQUEST"
                    if flow == "FINANCING"
                    else "OTHER_OPERATING_REQUEST"
                )
                request = {
                    "obligation_id": f"OB-{scenario}-{r['journal_id']}-{r.get('line_no', row_index)}",
                    "scenario": scenario,
                    "entity": "SHI",
                    "unit": r["unit"],
                    "cash_flow": flow,
                    "year": year,
                    "month": month,
                    "period": date,
                    "due_date": date,
                    "source_id": r["source_id"],
                    "journal_id": r["journal_id"],
                    "request_kind": kind,
                    "payable_id": event.get("payable_id", ""),
                    "invoice_id": event.get("invoice_id", ""),
                    "requested_usd": money(-D(r["signed_usd"])),
                    "funded_usd": "0.0000",
                    "unpaid_usd": money(-D(r["signed_usd"])),
                    "allocation_basis": "ILLUSTRATIVE_FIFO_WITHIN_FLOW_NOT_ACTUAL_PAYMENT",
                }
                requests.append(request)
            requested = sum((D(r["requested_usd"]) for r in requests), D(0))
            deferred = -sum(
                (
                    D(r["signed_usd"])
                    for r in rows
                    if r["account"] == account and r["source_type"] == "UNFUNDED_PAYMENT_DEFERRAL"
                ),
                D(0),
            )
            repaid = sum(
                (
                    D(r["signed_usd"])
                    for r in rows
                    if r["account"] == account
                    and r["source_id"].startswith(("CORE-ARREARS-PAID-", "BUSINESS-ARREARS-PAID-"))
                ),
                D(0),
            )
            if not 0 <= deferred <= requested or not 0 <= repaid <= opening + deferred:
                raise ValueError("Treasury journal does not fit identified eligible requests")
            activity = defaultdict(D)
            available = requested - deferred
            for r in requests:
                paid = min(D(r["unpaid_usd"]), available)
                r["funded_usd"], r["unpaid_usd"] = money(paid), money(D(r["unpaid_usd"]) - paid)
                available -= paid
                activity[r["obligation_id"]] += paid
            queue.extend(requests)
            available = repaid
            for r in queue:
                paid = min(D(r["unpaid_usd"]), available)
                r["funded_usd"] = money(D(r["funded_usd"]) + paid)
                r["unpaid_usd"] = money(D(r["unpaid_usd"]) - paid)
                activity[r["obligation_id"]] += paid
                available -= paid
            if available:
                raise ValueError("Unallocated arrears repayment")
            request_ids = {r["obligation_id"] for r in requests}
            for r in queue:
                if (
                    D(r["unpaid_usd"])
                    or activity[r["obligation_id"]]
                    or r["obligation_id"] in request_ids
                ):
                    model.tables["treasury_obligation_history"].append(
                        {
                            "scenario": scenario,
                            "unit": r["unit"],
                            "period": date,
                            "obligation_id": r["obligation_id"],
                            "cash_flow": flow,
                            "funded_in_period_usd": money(activity[r["obligation_id"]]),
                            "closing_unpaid_usd": r["unpaid_usd"],
                        }
                    )
            closing = sum((D(r["unpaid_usd"]) for r in queue), D(0))
            if closing != opening + deferred - repaid:
                raise ValueError("Obligation allocation fails arrears rollforward")
            model.tables["treasury_reconciliation"].append(
                {
                    "scenario": scenario,
                    "unit": "corporate",
                    "year": year,
                    "month": month,
                    "period": date,
                    "cash_flow": flow,
                    "opening_unpaid_usd": money(opening),
                    "requested_usd": money(requested),
                    "current_funded_usd": money(requested - deferred),
                    "new_deferral_usd": money(deferred),
                    "arrears_paid_usd": money(repaid),
                    "closing_unpaid_usd": money(closing),
                    "reconciliation_usd": "0.0000",
                }
            )
    model.tables["treasury_obligations"] = [r for queue in queues.values() for r in queue]
    return validate_treasury(model, enterprise_result)


def validate_treasury(model, enterprise_result):
    for r in model.tables["treasury_obligations"]:
        if (
            D(r["requested_usd"]) != D(r["funded_usd"]) + D(r["unpaid_usd"])
            or min(D(r["funded_usd"]), D(r["unpaid_usd"])) < 0
        ):
            raise ValueError("Individual obligation does not reconcile")
    by_month = defaultdict(dict)
    for r in model.tables["treasury_reconciliation"]:
        by_month[r["scenario"], int(r["year"]), int(r["month"])][r["cash_flow"]] = r
    seen_periods = set()
    for f in enterprise_result["funding_rows"]:
        entity = f.get("entity")
        scope = f.get("scope", "")
        if (
            entity in {"RWH_PS", "ARU_GROUP"}
            and scope == "INDUSTRIAL_SUBSIDIARY_CONDITIONAL_ENVELOPE"
        ):
            # These are separately validated industrial capital envelopes, not
            # Core's obligation-level payment deferral and arrears population.
            continue
        if entity != "SHI" or scope not in (None, ""):
            raise ValueError("Unknown enterprise funding scope/entity")
        required = (
            "unpaid_operating_obligations_usd",
            "unpaid_capital_obligations_usd",
            "unpaid_debt_obligations_usd",
            "new_payment_deferral_usd",
            "arrears_paid_usd",
        )
        if any(f.get(field) in (None, "") for field in required):
            raise ValueError("Missing Core funding reconciliation field")
        key = (f["scenario"], int(f["year"]), int(f["month"]))
        if key in seen_periods or key not in by_month:
            raise ValueError("Duplicate or unexpected Core funding period")
        seen_periods.add(key)
        rows = by_month[key]
        for flow, field in (
            ("OPERATING", "unpaid_operating_obligations_usd"),
            ("INVESTING", "unpaid_capital_obligations_usd"),
            ("FINANCING", "unpaid_debt_obligations_usd"),
        ):
            if D(rows[flow]["closing_unpaid_usd"]) != D(f[field]):
                raise ValueError("Individual allocations fail enterprise funding reconciliation")
        for out, src in (
            ("new_deferral_usd", "new_payment_deferral_usd"),
            ("arrears_paid_usd", "arrears_paid_usd"),
        ):
            if sum((D(r[out]) for r in rows.values()), D(0)) != D(f[src]):
                raise ValueError("Treasury monthly flow differs from enterprise source")
    if seen_periods != set(by_month):
        raise ValueError("Core funding period coverage is incomplete")
    return {
        "status": "PASS",
        "requests": len(model.tables["treasury_obligations"]),
        "monthly_flow_reconciliations": len(model.tables["treasury_reconciliation"]),
    }
