"""Conditional research, assayed recovery and dated industrial operating detail.

The original asset and industrial journals remain authoritative. New research
spending and rejected Cradle lots change the Core journal through business events.
Industrial detail only allocates existing quantities and dollars.
"""

from __future__ import annotations

import calendar
import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal as D

from enterprise.business.model import amount, money, period

META = {"fact_state": "CONDITIONAL_FORECAST", "record_origin": "PUBLIC_SYNTHETIC_MODEL"}


def digest(row):
    return hashlib.sha256(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def split(total, weights):
    """Exact four-decimal allocation with the rounding remainder on the last row."""
    total = amount(total)
    weights = [D(str(w)) for w in weights]
    if not weights or sum(weights) <= 0 or min(weights) < 0:
        raise ValueError("Positive allocation weights required")
    values = [amount(total * w / sum(weights)) for w in weights[:-1]]
    return values + [total - sum(values)]


def start_scenario(model):
    source = model.operations_inputs["research"]
    seen = set()
    for p in source["follow_on_phases"]:
        if p["phase_id"] in seen:
            raise ValueError("Duplicate research phase")
        seen.add(p["phase_id"])
        if not 1 <= p["start_month"] < p["gate_month"] <= 60:
            raise ValueError("Research phase must be bounded within forecast")
        if not 0 < p["first_attempt_offset"] < p["gate_month"] - p["start_month"]:
            raise ValueError("First attempt must precede independent replicate")
        if min(D(str(p[k])) for k in ("monthly_materials_usd", "materials_budget_usd")) < 0:
            raise ValueError("Negative research materials authorization")
        if any(not 0 <= D(p[k]) <= 1 for k in ("first_score", "replicate_score", "threshold")):
            raise ValueError("Research qualification score outside 0..1")
        if p["decision"] not in {"TRANSFER", "STOP", "CONTINUE"}:
            raise ValueError("Unsupported phase decision")
        if p["decision"] == "TRANSFER" and not (p["receiver"] and p["maintenance_owner"]):
            raise ValueError("Research transfer needs receiver and maintenance owner")
    assay = source["assay"]
    if (
        sum(D(x) for x in assay["run_fractions"]) != 1
        or min(D(x) for x in assay["run_fractions"]) <= 0
    ):
        raise ValueError("Assay split must preserve all feed")
    if (
        not 0
        <= D(assay["rejected_score"])
        < D(assay["minimum_acceptance_score"])
        <= D(assay["normal_score"])
        <= 1
    ):
        raise ValueError("Assay acceptance thresholds are inconsistent")
    model.research_state = {}


class ResearchMixin:
    def research(self):
        super().research()  # Preserves initial projects, reusable assets and carrying basis.
        if not hasattr(self, "research_state"):
            start_scenario(self)
        for phase in self.operations_inputs["research"]["follow_on_phases"]:
            if not phase["start_month"] <= self.month <= phase["gate_month"]:
                continue
            pid = phase["phase_id"]
            if self.month == phase["start_month"]:
                self.research_state[pid] = {"spent": D(0), "attempts": [], "held": False}
                self.tables["research_awards"].append(
                    {
                        "scenario": self.scenario,
                        "unit": "willow",
                        "phase_id": pid,
                        "project_id": phase["project_id"],
                        "period": period(self.month)[2],
                        "materials_budget_usd": money(phase["materials_budget_usd"]),
                        "approval_state": "SCENARIO_AUTHORIZED_NOT_EXECUTED_AWARD",
                        **META,
                    }
                )
            state = self.research_state[pid]
            charge = amount(D(str(phase["monthly_materials_usd"])) * D(self.case["cost_factor"]))
            budget = D(str(phase["materials_budget_usd"]))
            if state["spent"] + charge <= budget:
                self.cost(pid, "willow", "BIZ_RESEARCH", charge)
                state["spent"] += charge
            else:
                state["held"] = True
                self.event("RESEARCH_BUDGET_HOLD", pid, "willow", requested_usd=money(charge))
            first = self.month == phase["start_month"] + phase["first_attempt_offset"]
            final = self.month == phase["gate_month"]
            if first or final:
                score = D(phase["first_score"] if first else phase["replicate_score"])
                passed = score >= D(phase["threshold"]) and not state["held"]
                attempt = {
                    "scenario": self.scenario,
                    "unit": "willow",
                    "period": period(self.month)[2],
                    "phase_id": pid,
                    "attempt_id": f"{self.scenario}-{pid}-{'A1' if first else 'A2'}",
                    "attempt_number": 1 if first else 2,
                    "score": str(score),
                    "threshold": phase["threshold"],
                    "result": "PASS" if passed else "FAIL",
                    "protocol_version": "1" if first else "2",
                    "operator_id": "SYN-WIL-EXPERIMENTER",
                    "reviewer_id": "SYN-WIL-INDEPENDENT-REVIEWER",
                    "predecessor_attempt_id": "" if first else state["attempts"][0]["attempt_id"],
                    "correction": ""
                    if first
                    else "Recalibrated instrument and repeated blinded reference samples",
                    "budget_held": state["held"],
                    **META,
                }
                attempt["evidence_sha256"] = digest(attempt)
                self.tables["research_attempts"].append(attempt)
                state["attempts"].append(attempt)
                if final:
                    decision = phase["decision"] if passed else "STOP"
                    gate = {
                        "scenario": self.scenario,
                        "unit": "willow",
                        "period": period(self.month)[2],
                        "phase_id": pid,
                        "attempt_id": attempt["attempt_id"],
                        "attempt_evidence_sha256": attempt["evidence_sha256"],
                        "qualified": passed,
                        "decision": decision,
                        "receiver": phase["receiver"] if decision == "TRANSFER" else "",
                        "maintenance_owner": phase["maintenance_owner"]
                        if decision == "TRANSFER"
                        else "",
                        "operating_authority": "NO_NEW_AUTHORITY_GRANTED",
                        **META,
                    }
                    self.tables["research_gate_evidence"].append(gate)
                    self.event("FOLLOW_ON_GATE", pid, "willow", decision=decision, qualified=passed)
            remaining = max(phase["gate_month"] - self.month, 0)
            ctc = amount(charge * remaining)
            self.tables["research_phase_forecasts"].append(
                {
                    "scenario": self.scenario,
                    "unit": "willow",
                    "period": period(self.month)[2],
                    "phase_id": pid,
                    "materials_budget_usd": money(budget),
                    "materials_incurred_usd": money(state["spent"]),
                    "cost_to_complete_usd": money(ctc),
                    "committed_materials_usd": money(min(ctc, charge * 2)),
                    "estimate_at_completion_usd": money(state["spent"] + ctc),
                    "budget_headroom_usd": money(budget - state["spent"] - ctc),
                    "state": "BUDGET_HOLD"
                    if state["held"]
                    else "GATE_COMPLETE"
                    if final
                    else "ACTIVE",
                    "cost_scope": "DIRECT_MATERIALS_ONLY_PAYROLL_RECORDED_ONCE_IN_WORKFORCE",
                    **META,
                }
            )

    def recovery(self):
        unit = "project-cradle"
        assay = self.operations_inputs["research"]["assay"]
        for stream in ("stream17", "demotte"):
            r = self.inputs["recovery"][stream]
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
            cost_basis = D(0)
            if recovered and stream == "stream17":
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
                    "Captured Stream 17 lot; direct expense reclassified once",
                )
            fractions = assay["run_fractions"]
            rejected = self.month in assay["rejected_months"][stream]
            runs = []
            for n, values in enumerate(
                zip(
                    split(feed, fractions),
                    split(contained, fractions),
                    split(recovered, fractions),
                    split(cost_basis, fractions),
                    strict=True,
                ),
                1,
            ):
                run = {
                    "scenario": self.scenario,
                    "unit": unit,
                    "period": period(self.month)[2],
                    "stream": stream,
                    "lot_id": lot_id,
                    "run_id": f"{lot_id}-RUN-{n}",
                    "feed_unit": basis_unit,
                    "feed_quantity": money(values[0]),
                    "contained_kg": money(values[1]),
                    "recovered_kg": money(values[2]),
                    "allocated_cost_usd": money(values[3]),
                    "bypass": availability == 0,
                    "assay_score": assay["rejected_score"]
                    if rejected and n == 2
                    else assay["normal_score"],
                    "minimum_score": assay["minimum_acceptance_score"],
                    "assay_status": "NO_CAPTURE_BYPASS"
                    if not recovered
                    else "FAIL"
                    if rejected and n == 2
                    else "PASS",
                    "sample_custodian": "SYN-CRADLE-LAB-CUSTODIAN",
                    **META,
                }
                run["evidence_sha256"] = digest(run)
                self.tables["recovery_run_assays"].append(run)
                runs.append(run)
            if not recovered:
                continue
            original_cost = cost_basis
            sale = amount(
                recovered
                * D(r["assay_payable_fraction"])
                * D(r["realized_usd_per_kg"])
                * D(self.case["price_factor"])
            )
            freight = amount(
                recovered
                * D(r.get("bedford_and_freight_usd_per_kg", 0))
                * D(self.case["cost_factor"])
            )
            nrv = D(0) if rejected else max(sale * (1 - D(r["host_share"])) - freight, D(0))
            impairment = max(cost_basis - amount(nrv), D(0))
            if impairment:
                self.post(
                    event,
                    unit,
                    [("BIZ_INVENTORY_LOSS", impairment), ("BIZ_INVENTORY", -impairment)],
                    "Rejected assayed lot written to zero"
                    if rejected
                    else "Captured lot at assayed net realizable value",
                )
                cost_basis -= impairment
            for run in runs:
                # Feed is split to runs; captured run outputs merge into one Bedford lot.
                self.tables["recovery_genealogy"].append(
                    {
                        "scenario": self.scenario,
                        "unit": unit,
                        "period": period(self.month)[2],
                        "stream": stream,
                        "parent_id": f"FEED-{lot_id}",
                        "child_id": run["run_id"],
                        "lot_id": lot_id,
                        "edge_type": "FEED_SPLIT",
                        "mass_basis": basis_unit,
                        "quantity": run["feed_quantity"],
                        "cost_usd": "0.0000",
                        **META,
                    }
                )
                self.tables["recovery_genealogy"].append(
                    {
                        "scenario": self.scenario,
                        "unit": unit,
                        "period": period(self.month)[2],
                        "stream": stream,
                        "parent_id": run["run_id"],
                        "child_id": f"BEDFORD-{lot_id}",
                        "lot_id": lot_id,
                        "edge_type": "CAPTURE_MERGE",
                        "mass_basis": "RECOVERED_KG",
                        "quantity": run["recovered_kg"],
                        "cost_usd": run["allocated_cost_usd"],
                        **META,
                    }
                )
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
                "original_cost_usd": money(original_cost),
                "impairment_usd": money(impairment),
                "sale_value_usd": money(sale),
                "freight_usd": money(freight),
                "host_share": r["host_share"],
                "accept_month": self.month
                + r["sale_lag_months"]
                + self.case["acceptance_delay_months"],
                "assay_status": "REJECTED" if rejected else "ACCEPTABLE",
                "status": "QUARANTINED_REJECTED" if rejected else "CAPTURED_UNSOLD",
                "assay_evidence_sha256": digest([x["evidence_sha256"] for x in runs]),
            }
            self.lots.append(lot)
            self.tables["recovery_custody"].append(
                {
                    "scenario": self.scenario,
                    "unit": unit,
                    "period": period(self.month)[2],
                    "lot_id": lot_id,
                    "from_custodian": "HOST_CAPTURE_POINT",
                    "to_custodian": "CRADLE_CONTROLLED_LOT",
                    "state": "QUARANTINED_REJECTED" if rejected else "CAPTURED_PENDING_ACCEPTANCE",
                    "authority": "HOST_PRIMARY_OPERATION_AND_STOP_AUTHORITY",
                    **META,
                }
            )
        for lot in self.lots:
            if lot["accept_month"] != self.month or lot["status"] != "CAPTURED_UNSOLD":
                continue
            if lot["assay_status"] != "ACCEPTABLE":
                raise ValueError("Unaccepted assay reached invoicing")
            event = self.event(
                "DOWNSTREAM_ACCEPTANCE",
                lot["lot_id"],
                unit,
                bedford_batch_id=lot["bedford_batch_id"],
                payable_kg=lot["payable_kg"],
                host=lot["host"],
                sales_value_usd=lot["sale_value_usd"],
                assay_evidence_sha256=lot["assay_evidence_sha256"],
            )
            lot["status"] = "ACCEPTED_SALE"  # Evidence/state precedes actual billing.
            self.tables["recovery_custody"].append(
                {
                    "scenario": self.scenario,
                    "unit": unit,
                    "period": period(self.month)[2],
                    "lot_id": lot["lot_id"],
                    "from_custodian": "CRADLE_CONTROLLED_LOT",
                    "to_custodian": "SYN-SPECIALIST-REFINER",
                    "state": "ACCEPTED_SALE",
                    "authority": "ACCEPTED_CAPTURED_MATERIAL_ONLY_NO_HOST_OPERATION_TRANSFER",
                    **META,
                }
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
                "Accepted lot releases cost",
            )
            self.cost(f"FREIGHT-{lot['lot_id']}", unit, "BIZ_DELIVERY", lot["freight_usd"])
        unsold = [l for l in self.lots if l["status"] == "CAPTURED_UNSOLD"]
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


def validate(model):
    """Recompute evidence, mass, cost and acceptance links independently."""
    attempts = {(r["scenario"], r["attempt_id"]): r for r in model.tables["research_attempts"]}
    for attempt in attempts.values():
        if (
            digest({k: v for k, v in attempt.items() if k != "evidence_sha256"})
            != attempt["evidence_sha256"]
        ):
            raise ValueError("Research evidence digest mismatch")
        passed = D(attempt["score"]) >= D(attempt["threshold"]) and not attempt["budget_held"]
        if (attempt["result"] == "PASS") != passed or attempt["operator_id"] == attempt[
            "reviewer_id"
        ]:
            raise ValueError("Invalid independent research qualification")
    for gate in model.tables["research_gate_evidence"]:
        attempt = attempts[(gate["scenario"], gate["attempt_id"])]
        if gate["attempt_evidence_sha256"] != attempt["evidence_sha256"] or gate["qualified"] != (
            attempt["result"] == "PASS"
        ):
            raise ValueError("Gate lacks qualified replicate evidence")
        if gate["decision"] == "TRANSFER" and not (
            gate["qualified"] and gate["receiver"] and gate["maintenance_owner"]
        ):
            raise ValueError("Unqualified research transfer")
    costs = defaultdict(D)
    for journal in model.tables["journal"]:
        if journal["account"] == "BIZ_RESEARCH":
            for phase in model.operations_inputs["research"]["follow_on_phases"]:
                if journal["source_id"].endswith("COST-" + phase["phase_id"]):
                    costs[journal["scenario"], phase["phase_id"], journal["period"]] += D(
                        journal["signed_usd"]
                    )
    for row in model.tables["research_phase_forecasts"]:
        incurred = sum(
            v
            for (scenario, phase, dt), v in costs.items()
            if scenario == row["scenario"] and phase == row["phase_id"] and dt <= row["period"]
        )
        if incurred != D(row["materials_incurred_usd"]):
            raise ValueError("Research materials do not reconcile to journal")
        if D(row["estimate_at_completion_usd"]) != incurred + D(row["cost_to_complete_usd"]):
            raise ValueError("Research estimate at completion does not reconcile")
        if D(row["committed_materials_usd"]) > D(row["cost_to_complete_usd"]):
            raise ValueError("Research commitment exceeds remaining work")
    runs = defaultdict(list)
    for row in model.tables["recovery_run_assays"]:
        if (
            digest({k: v for k, v in row.items() if k != "evidence_sha256"})
            != row["evidence_sha256"]
        ):
            raise ValueError("Assay evidence digest mismatch")
        if not 0 <= D(row["recovered_kg"]) <= D(row["contained_kg"]):
            raise ValueError("Assay recovered mass exceeds contained mass")
        if row["bypass"] and D(row["recovered_kg"]):
            raise ValueError("Bypassed run captured material")
        runs[row["scenario"], row["lot_id"]].append(row)
    genealogy = defaultdict(list)
    for row in model.tables["recovery_genealogy"]:
        genealogy[row["scenario"], row["lot_id"], row["edge_type"]].append(row)
    capture_events = {
        (r["scenario"], r["source_id"]): r
        for r in model.tables["events"]
        if r["kind"] == "RECOVERY_RUN"
    }
    invoices = {(r["scenario"], r["source_id"]): r for r in model.tables["invoices"]}
    for lot in model.tables["recovery_lots"]:
        key = lot["scenario"], lot["lot_id"]
        parts = runs[key]
        edges = genealogy[(*key, "CAPTURE_MERGE")]
        feed_edges = genealogy[(*key, "FEED_SPLIT")]
        captured = capture_events[key]
        run_ids = {r["run_id"] for r in parts}
        if len(run_ids) != len(parts) or len(edges) != len(parts) or len(feed_edges) != len(parts):
            raise ValueError("Recovery genealogy has missing or duplicate run links")
        if {r["parent_id"] for r in edges} != run_ids or any(
            r["child_id"] != lot["bedford_batch_id"] or r["mass_basis"] != "RECOVERED_KG"
            for r in edges
        ):
            raise ValueError("Recovery genealogy merge identity mismatch")
        if {r["child_id"] for r in feed_edges} != run_ids or any(
            r["parent_id"] != "FEED-" + lot["lot_id"] or r["mass_basis"] != captured["feed_unit"]
            for r in feed_edges
        ):
            raise ValueError("Recovery genealogy feed identity mismatch")
        if sum(D(r["quantity"]) for r in feed_edges) != D(captured["feed_quantity"]):
            raise ValueError("Recovery genealogy feed mass mismatch")
        for field in ("feed_quantity", "contained_kg", "recovered_kg"):
            if sum(D(r[field]) for r in parts) != D(captured[field]):
                raise ValueError("Assay runs do not conserve original capture event")
        if sum(D(r["recovered_kg"]) for r in parts) != D(lot["recovered_kg"]) or sum(
            D(r["quantity"]) for r in edges
        ) != D(lot["recovered_kg"]):
            raise ValueError("Recovery genealogy mass mismatch")
        if sum(D(r["cost_usd"]) for r in edges) != D(lot["original_cost_usd"]):
            raise ValueError("Recovery genealogy cost mismatch")
        if D(lot["original_cost_usd"]) - D(lot["impairment_usd"]) != D(lot["cost_usd"]):
            raise ValueError("Recovery lot cost rollforward mismatch")
        if lot["assay_evidence_sha256"] != digest([r["evidence_sha256"] for r in parts]):
            raise ValueError("Lot does not bind its assay evidence")
        event = f"{lot['scenario']}-{lot['accept_month']:02}-DOWNSTREAM_ACCEPTANCE-{lot['lot_id']}"
        invoice = invoices.get((lot["scenario"], event))
        if lot["status"] == "QUARANTINED_REJECTED" and (invoice or D(lot["cost_usd"])):
            raise ValueError("Rejected lot was sold or retained recoverable cost")
        if invoice and (
            lot["status"] != "ACCEPTED_SALE"
            or invoice["issue_month"] <= lot["capture_month"]
            or any(r["assay_status"] != "PASS" for r in parts)
        ):
            raise ValueError("Recovery billing lacks prior accepted assay")
    return {
        "research_attempts": len(attempts),
        "assay_runs": sum(map(len, runs.values())),
        "quarantined_lots": sum(
            r["status"] == "QUARANTINED_REJECTED" for r in model.tables["recovery_lots"]
        ),
    }


def _apportion(total, weights, quantum=D("0.0001")):
    """Largest remainders, retaining integral railcars and truck dispatches."""
    from decimal import ROUND_FLOOR

    units = D(str(total)) / quantum
    if units != units.to_integral_value():
        raise ValueError("Physical source quantity exceeds its reporting precision")
    weights = [D(str(w)) for w in weights]
    if not any(weights):
        if units:
            raise ValueError("Nonzero quantity has no service population")
        return [D(0)] * len(weights)
    raw = [units * w / sum(weights) for w in weights]
    result = [int(x.to_integral_value(rounding=ROUND_FLOOR)) for x in raw]
    order = sorted(range(len(raw)), key=lambda i: (-(raw[i] - result[i]), i))
    for i in order[: int(units) - sum(result)]:
        result[i] += 1
    return [D(x) * quantum for x in result]


def _service_days(year, month):
    return [
        date(year, month, day).isoformat()
        for day in range(1, calendar.monthrange(year, month)[1] + 1)
        if date(year, month, day).weekday() < 5
    ]


def build_industrial_detail(
    model, operating_rows, transaction_tables, industrial_journal_rows=None
):
    """Allocate monthly records to dates, preserving all source quantities/dollars.

    Capacity findings are planning exceptions. An internally reconciling allocation
    may be infeasible; no row claims that a shipment or inspection actually occurred.
    """
    policy = model.operations_inputs["research"]["industrial"]
    if D(str(policy["shift_hours"])) <= 0 or int(policy["maintenance_jobs_per_work_order"]) < 1:
        raise ValueError("Industrial shifts and maintenance jobs must be positive")
    operations = {(r["scenario"], int(r["year"]), int(r["month"])): r for r in operating_rows}
    if len(operations) != len(operating_rows):
        raise ValueError("Duplicate industrial operating month")
    tables = transaction_tables.get("tables", transaction_tables)
    details, jobs, reconciliation, shifts = [], [], [], []
    downtime = defaultdict(D)
    supplier = {(r["scenario"], r["invoice_id"]): r for r in tables.get("supplier_invoices", [])}
    for work in tables.get("work_orders", []):
        key = work["scenario"], int(work["year"]), int(work["month"])
        if key not in operations:
            raise ValueError("Maintenance lacks operating-month source")
        invoice = supplier.get((work["scenario"], work["invoice_id"]))
        if invoice is None or D(str(invoice["amount_usd"])) != D(str(work["expense_usd"])):
            raise ValueError("Maintenance work order does not tie to supplier invoice")
        n = int(policy["maintenance_jobs_per_work_order"])
        costs = split(work["expense_usd"], [1] * n)
        quantities = split(work["planned_service_quantity"], [1] * n)
        days = _service_days(key[1], key[2])
        for i, (cost, quantity) in enumerate(zip(costs, quantities, strict=True)):
            scheduled = days[(4 + i * 9) % len(days)]
            hours = D(policy["maintenance_downtime_hours_per_job"])
            row = {
                "scenario": key[0],
                "unit": "american-resource-utility",
                "period": date(key[1], key[2], calendar.monthrange(key[1], key[2])[1]).isoformat(),
                "segment": work["segment"],
                "maintenance_job_id": f"{work['work_order_id']}-JOB-{i + 1}",
                "work_order_id": work["work_order_id"],
                "invoice_id": work["invoice_id"],
                "source_id": work["source_id"],
                "scheduled_date": scheduled,
                "asset_scope": work["asset_scope"],
                "service_quantity": money(quantity),
                "expense_usd": money(cost),
                "downtime_hours": money(hours),
                "cost_basis": "EXISTING_SUPPLIER_INVOICE_ALLOCATION_NO_NEW_POSTING",
                "state": "PLANNED_NOT_COMPLETED_INSPECTION",
                **META,
            }
            jobs.append(row)
            downtime[(*key, work["segment"], scheduled)] += hours
        reconciliation.append(
            {
                "scenario": key[0],
                "unit": "american-resource-utility",
                "period": jobs[-1]["period"],
                "segment": work["segment"],
                "source_id": work["work_order_id"],
                "kind": "MAINTENANCE_WORK_ORDER",
                "source_quantity": money(work["planned_service_quantity"]),
                "detail_quantity": money(sum(quantities)),
                "source_amount_usd": money(work["expense_usd"]),
                "detail_amount_usd": money(sum(costs)),
                "status": "PASS",
                **META,
            }
        )

    # Mine production debits allocate only the disclosed maintenance share; payment
    # entries and credits never count as a second production/maintenance cost.
    production = defaultdict(D)
    for row in industrial_journal_rows or []:
        if row.get("source_type") == "PRODUCTION_COST" and D(str(row["signed_usd"])) > 0:
            key = row["scenario"], int(row["year"]), int(row["month"]), row["source_id"]
            production[key] += D(str(row["signed_usd"]))
    fraction = D(policy["mine_maintenance_fraction_of_production_cost"])
    if not 0 <= fraction <= 1:
        raise ValueError("Mine maintenance share must be within production cost")
    for (scenario, year, month, source_id), total in sorted(production.items()):
        part = amount(total * fraction)
        dt = date(year, month, calendar.monthrange(year, month)[1]).isoformat()
        jobs.append(
            {
                "scenario": scenario,
                "unit": "pale-sun",
                "period": dt,
                "segment": "RWH",
                "maintenance_job_id": f"{source_id}-MAINT-ALLOC",
                "work_order_id": "",
                "invoice_id": "",
                "source_id": source_id,
                "scheduled_date": date(year, month, 15).isoformat(),
                "asset_scope": "RWH_EXISTING_PROCESS_PLANT",
                "service_quantity": "1.0000",
                "expense_usd": money(part),
                "downtime_hours": "0.0000",
                "cost_basis": "ASSUMED_SHARE_OF_EXISTING_PRODUCTION_COST_NOT_SEPARATE_INVOICE",
                "state": "COST_ALLOCATION_ONLY_NO_NEW_DOWNTIME_ASSUMED",
                **META,
            }
        )
        reconciliation.append(
            {
                "scenario": scenario,
                "unit": "pale-sun",
                "period": dt,
                "segment": "RWH",
                "source_id": source_id,
                "kind": "MINE_PRODUCTION_COST_ALLOCATION",
                "source_quantity": "1.0000",
                "detail_quantity": "1.0000",
                "source_amount_usd": money(total),
                "detail_amount_usd": money(part + (total - part)),
                "maintenance_amount_usd": money(part),
                "remaining_production_amount_usd": money(total - part),
                "status": "PASS",
                **META,
            }
        )

    manifests = defaultdict(list)
    for manifest in tables.get("service_manifests", []):
        key = (
            manifest["scenario"],
            int(manifest["year"]),
            int(manifest["month"]),
            manifest["segment"],
        )
        manifests[key].append(manifest)
    sales = {(r["scenario"], r["invoice_id"]): r for r in tables.get("sales_invoices", [])}
    for (*month_key, segment), sources in sorted(manifests.items()):
        key = tuple(month_key)
        if key not in operations:
            raise ValueError("Service allocation lacks operating-month source")
        op = operations[key]
        quantities = [D(str(r["allocated_realized_units"])) for r in sources]
        physical = op["segments"][segment]
        if amount(sum(quantities)) != amount(physical["served_units"]):
            raise ValueError("Industrial monthly service quantity mismatch")
        quantum = D(1) if segment in {"BST", "TRUCKING"} else D("0.001")
        owned = _apportion(physical["owned_served_units"], quantities, quantum)
        days = _service_days(key[1], key[2])
        dt = date(key[1], key[2], calendar.monthrange(key[1], key[2])[1]).isoformat()
        rail = op["capacity"]["rail"]
        if segment == "BST":
            source_days = int(rail["service_days"])
            # Model service-day count can differ from weekday count. Dated allocation
            # uses the declared count when it fits the month, without inventing more.
            days = [date(key[1], key[2], i + 1).isoformat() for i in range(source_days)]
        max_batch = {
            "BST": max(int(rail["loaded_cars_per_train"]), 1),
            "TRUCKING": 1,
            "TERMINALS": 500,
            "WAREHOUSE": 500,
        }[segment]
        day_rows = defaultdict(list)
        row_index = 0
        for manifest, total, owned_quantity in zip(sources, quantities, owned, strict=True):
            invoice = sales.get((key[0], manifest["invoice_id"]))
            if invoice is None or D(str(invoice["amount_usd"])) != D(str(manifest["revenue_usd"])):
                raise ValueError("Service manifest revenue does not match source invoice")
            batches = []
            for provider, quantity in (
                ("OWNED", owned_quantity),
                ("OUTSIDE", total - owned_quantity),
            ):
                while quantity > 0:
                    chunk = min(quantity, D(max_batch))
                    batches.append((provider, chunk))
                    quantity -= chunk
            if not batches:
                if D(str(manifest["revenue_usd"])):
                    raise ValueError("Nonzero service invoice has zero activity")
                continue
            revenues = split(manifest["revenue_usd"], [q for _, q in batches])
            manifest_rows = []
            for i, ((provider, quantity), revenue) in enumerate(
                zip(batches, revenues, strict=True)
            ):
                scheduled = days[row_index % len(days)]
                row_index += 1
                if segment == "BST":
                    hours = D(str(rail["train_hours_daily"])) / max(
                        int(rail["round_trips_daily"]), 1
                    )
                elif segment == "TRUCKING":
                    hours = quantity * 2 * D(str(op["capacity"]["truck_cycle_multiplier"]))
                else:
                    rate = (
                        policy["terminal_hours_per_ton"]
                        if segment == "TERMINALS"
                        else policy["warehouse_hours_per_pallet_month"]
                    )
                    hours = quantity * D(rate)
                row = {
                    "scenario": key[0],
                    "unit": "american-resource-utility",
                    "period": dt,
                    "segment": segment,
                    "service_detail_id": f"{manifest['service_manifest_id']}-D-{i + 1:05}",
                    "manifest_id": manifest["service_manifest_id"],
                    "invoice_id": manifest["invoice_id"],
                    "source_id": manifest["source_id"],
                    "contract_id": manifest["contract_id"],
                    "customer_id": manifest["customer_id"],
                    "service_date": scheduled,
                    "origin_destination": manifest.get("origin_destination", ""),
                    "physical_unit": manifest["unit"],
                    "quantity": money(quantity),
                    "revenue_usd": money(revenue),
                    "provider": provider,
                    "required_resource_hours": money(hours),
                    "resource_pool": f"{segment}-{'OWNED' if provider == 'OWNED' else 'CONTRACTED'}-POOL",
                    "capacity_state": "OUTSIDE_PROVIDER_CAPACITY_NOT_INDEPENDENTLY_VERIFIED"
                    if provider == "OUTSIDE"
                    else "PENDING",
                    "custody_authority": "EXISTING_NON_URANIUM_SERVICE_SCOPE",
                    "evidence_role": "DATED_ALLOCATION_NOT_OBSERVED_SHIPMENT",
                    **META,
                }
                details.append(row)
                manifest_rows.append(row)
                day_rows[scheduled].append(row)
            reconciliation.append(
                {
                    "scenario": key[0],
                    "unit": "american-resource-utility",
                    "period": dt,
                    "segment": segment,
                    "source_id": manifest["service_manifest_id"],
                    "kind": "SERVICE_INVOICE",
                    "source_quantity": money(total),
                    "detail_quantity": money(sum(D(r["quantity"]) for r in manifest_rows)),
                    "source_amount_usd": money(manifest["revenue_usd"]),
                    "detail_amount_usd": money(sum(D(r["revenue_usd"]) for r in manifest_rows)),
                    "status": "PASS",
                    **META,
                }
            )
        for scheduled, rows in sorted(day_rows.items()):
            requested = sum(
                D(r["required_resource_hours"]) for r in rows if r["provider"] == "OWNED"
            )
            capacity = op["capacity"]
            if segment == "BST":
                available = D(str(rail["crew_duty_hours_daily"]))
                reserved = (
                    D(str(op["capacity"]["rail_owned_used_cars"] - physical["owned_served_units"]))
                    / max(D(str(rail["loaded_cars_per_train"])), D(1))
                    * D(str(rail["train_hours_daily"]))
                    / max(int(rail["round_trips_daily"]), 1)
                    / len(days)
                )
                equipment = available
            elif segment == "TRUCKING":
                available = D(str(capacity["truck_driver_hours"])) / len(days)
                equipment = D(str(capacity["truck_tractor_hours"])) / len(days)
                reserved = D(str(op["interface"]["aru_truck_hours"])) / len(days)
            elif segment == "TERMINALS":
                available = (
                    D(str(capacity["terminal_owned_capacity_tons"]))
                    * D(policy["terminal_hours_per_ton"])
                    / len(days)
                )
                equipment = available
                reserved = (
                    D(str(op["interface"]["aru_handled_tons"]))
                    * D(policy["terminal_hours_per_ton"])
                    / len(days)
                )
            else:
                available = (
                    D(str(capacity["warehouse_owned_slots"]))
                    * D(policy["warehouse_hours_per_pallet_month"])
                    / len(days)
                )
                equipment, reserved = available, D(0)
            maintenance = downtime[(*key, segment, scheduled)]
            available, equipment, reserved, maintenance = map(
                amount, (available, equipment, reserved, maintenance)
            )
            net = max(min(available, equipment) - reserved - maintenance, D(0))
            state = "PASS" if requested <= net else "INFEASIBLE_CAPACITY"
            for row in rows:
                if row["provider"] == "OWNED":
                    row["capacity_state"] = state
            shifts.append(
                {
                    "scenario": key[0],
                    "unit": "american-resource-utility",
                    "period": dt,
                    "segment": segment,
                    "service_date": scheduled,
                    "crew_hours_available": money(available),
                    "equipment_hours_available": money(equipment),
                    "interface_hours_reserved": money(reserved),
                    "maintenance_downtime_hours": money(maintenance),
                    "net_available_hours": money(net),
                    "service_hours_requested": money(requested),
                    "nominal_shift_hours": money(policy["shift_hours"]),
                    "required_shift_equivalents": money(requested / D(str(policy["shift_hours"]))),
                    "available_shift_equivalents": money(net / D(str(policy["shift_hours"]))),
                    "over_capacity_hours": money(max(requested - net, D(0))),
                    "capacity_state": state,
                    "scope": "OWNED_RESOURCE_POOL_DATED_PLANNING_CHECK",
                    **META,
                }
            )
    for row in reconciliation:
        if D(row["source_quantity"]) != D(row["detail_quantity"]) or D(
            row["source_amount_usd"]
        ) != D(row["detail_amount_usd"]):
            raise ValueError("Industrial detail reconciliation failed")
    model.tables["industrial_service_detail"] = details
    model.tables["industrial_maintenance_jobs"] = jobs
    model.tables["industrial_detail_reconciliation"] = reconciliation
    model.tables["industrial_shift_capacity"] = shifts
    return {
        "service_allocations": len(details),
        "maintenance_jobs": len(jobs),
        "source_reconciliations": len(reconciliation),
        "infeasible_owned_shift_allocations": sum(
            r["capacity_state"] == "INFEASIBLE_CAPACITY" for r in shifts
        ),
    }
