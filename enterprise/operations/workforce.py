"""Effective-dated synthetic staffing, one payroll and finite delivery capacity."""

from __future__ import annotations

import copy
from collections import defaultdict
from decimal import Decimal as D

from enterprise.business.model import SEGMENTS, amount, money, period


def start_scenario(model):
    model.staff = {r["position_id"]: copy.deepcopy(r) for r in model.roster}
    model.staff_changes = sorted(
        copy.deepcopy(model.operations_inputs["workforce"]["events"]),
        key=lambda r: (r["month"], r["change_id"]),
    )
    ids = [r["change_id"] for r in model.staff_changes]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate workforce change identity")
    for change in model.staff_changes:
        if (
            type(change["month"]) is not int
            or not 1 <= change["month"] <= 60
            or change["position_id"] not in model.staff
        ):
            raise ValueError("Workforce change outside authorized position or period")
        if not change.get("scenarios", model.policy["cases"]) or not set(
            change.get("scenarios", model.policy["cases"])
        ) <= set(model.policy["cases"]):
            raise ValueError("Workforce change has unknown or empty scenario applicability")
    for position in model.staff.values():
        position.update(on_leave=False, joined_month=0, ramp_months=1)


def _apply(model, change):
    p = model.staff[change["position_id"]]
    prior_person = p["person_id"]
    action = change["action"]
    if action == "JOIN":
        if p["occupied"] or not p["authorized"]:
            raise ValueError("Join requires a vacant authorized position")
        person = change.get("person_id", "")
        ramp = change.get("ramp_months", 1)
        if not person or type(ramp) is not int or ramp < 1:
            raise ValueError("Join requires person identity and positive ramp duration")
        if any(r["occupied"] and r["person_id"] == person for r in model.staff.values()):
            raise ValueError("Person already occupies a paid position")
        p.update(occupied=True, person_id=person, joined_month=model.month, ramp_months=ramp)
    elif action == "EXIT":
        if not p["occupied"]:
            raise ValueError("Exit requires occupied position")
        p.update(occupied=False, person_id="", on_leave=False)
    elif action in {"LEAVE", "RETURN"}:
        if not p["occupied"] or p["on_leave"] == (action == "LEAVE"):
            raise ValueError("Invalid leave/return transition")
        p["on_leave"] = action == "LEAVE"
    elif action == "ASSIGNMENT_TRANSFER":
        assignments = change["assignments"]
        if not p["occupied"] or not assignments:
            raise ValueError("Transfer requires occupied position and assignment")
        if any(u not in SEGMENTS or D(f) < 0 for u, f in assignments.items()):
            raise ValueError("Invalid assignment destination or fraction")
        if sum(D(f) for f in assignments.values()) != 1:
            raise ValueError("Assignment fractions must sum to one")
        if p["home_group"] in {"j2", "atlas-meridian"} and D(assignments.get("advisory", 0)):
            raise ValueError("J2/Atlas cannot be an Advisory staffing reserve")
        p["assignments"] = copy.deepcopy(assignments)
    else:
        raise ValueError(f"Unknown workforce action: {action}")
    model.tables["workforce_changes"].append(
        {
            "scenario": model.scenario,
            "period": period(model.month)[2],
            "month_index": model.month,
            "unit": p["home_unit"],
            "change_id": change["change_id"],
            "action": action,
            "position_id": p["position_id"],
            "person_id": p["person_id"],
            "prior_person_id": prior_person,
            "state": "APPLIED_CONDITIONAL_PLANNING_EVENT",
        }
    )


class WorkforceMixin:
    def workforce(self):
        if not hasattr(self, "staff") or getattr(self, "staff_scenario", None) != self.scenario:
            start_scenario(self)
            self.staff_scenario = self.scenario
        for change in self.staff_changes:
            if change["month"] == self.month and self.scenario in change.get(
                "scenarios", self.policy["cases"]
            ):
                _apply(self, change)
        factor = (1 + D(self.policy["payroll_inflation"])) ** ((self.month - 1) // 12)
        factor *= D(self.case["cost_factor"])
        self.capacity, self.payroll = defaultdict(D), defaultdict(D)
        for p in self.staff.values():
            occupied = p["occupied"]
            ramp = min(D(1), D(self.month - p["joined_month"] + 1) / p["ramp_months"])
            ramp = amount(ramp) if occupied and not p["on_leave"] else D(0)
            total = amount(D(p["annual_loaded_usd"]) / 12 * factor) if occupied else D(0)
            capacity = D(0)
            allocated = D(0)
            if occupied:
                assignments = list(p["assignments"].items())
                for index, (unit, fraction) in enumerate(assignments):
                    value = (
                        total - allocated
                        if index == len(assignments) - 1
                        else amount(total * D(fraction))
                    )
                    allocated += value
                    self.payroll[unit] += value
                    hours = (
                        amount(
                            D(self.policy["hours_per_month"])
                            * D(self.policy["delivery_utilization"])
                            * D(fraction)
                            * ramp
                        )
                        if p["delivery_role"]
                        else D(0)
                    )
                    self.capacity[unit] += hours
                    capacity += hours
                    self.tables["workforce_assignments"].append(
                        {
                            "scenario": self.scenario,
                            "period": period(self.month)[2],
                            "month_index": self.month,
                            "position_id": p["position_id"],
                            "person_id": p["person_id"],
                            "home_group": p["home_group"],
                            "unit": unit,
                            "assignment_fte": fraction,
                            "loaded_cost_usd": money(value),
                            "delivery_capacity_hours": money(hours),
                            "ramp_fraction": money(ramp),
                            "leave_state": "PAID_LEAVE" if p["on_leave"] else "ACTIVE",
                        }
                    )
                if allocated != total:
                    raise ValueError("Employee payroll is not allocated exactly once")
            self.tables["workforce_positions_history"].append(
                {
                    "scenario": self.scenario,
                    "period": period(self.month)[2],
                    "month_index": self.month,
                    "unit": p["home_unit"],
                    "position_id": p["position_id"],
                    "person_id": p["person_id"],
                    "home_group": p["home_group"],
                    "authorized": p["authorized"],
                    "occupied": occupied,
                    "ramp_fraction": money(ramp),
                    "leave_state": "PAID_LEAVE"
                    if p["on_leave"]
                    else ("ACTIVE" if occupied else "VACANT"),
                    "expected_loaded_cost_usd": money(total),
                    "capacity_hours": money(capacity),
                    "fact_state": "CONDITIONAL_FORECAST_NOT_ACTUAL_EMPLOYMENT",
                }
            )
        for unit, value in self.payroll.items():
            event = self.event("PAYROLL_REQUEST", unit, unit, amount_usd=money(value))
            self.post(
                event,
                unit,
                [("BIZ_PAYROLL", value), ("1000", -value)],
                "Effective-dated occupied-position payroll; conditional treasury settlement",
            )
        occupied_ess = sum(p["occupied"] for p in self.staff.values() if p["home_group"] == "ess")
        support = D(self.policy["corporate_monthly_facility_usd"])
        support += D(self.policy["annual_ess_vendor_per_occupied_usd"]) * occupied_ess / 12
        self.cost(
            "ESS-FACILITY-VENDORS",
            "corporate",
            "BIZ_SUPPORT",
            support * D(self.case["cost_factor"]),
        )


def validate(model):
    histories = model.tables["workforce_positions_history"]
    keys = [(r["scenario"], r["period"], r["position_id"]) for r in histories]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate position-month")
    required = {
        (scenario, period(month)[2], p["position_id"])
        for scenario in model.policy["cases"]
        for month in range(1, 61)
        for p in model.roster
    }
    if set(keys) != required:
        raise ValueError("Authorized position-month population is incomplete")
    expected = {(r["scenario"], r["period"], r["position_id"]): r for r in histories}
    assigned_cost, assigned_fte, assigned_capacity = (
        defaultdict(D),
        defaultdict(D),
        defaultdict(D),
    )
    person_positions = defaultdict(set)
    for row in model.tables["workforce_assignments"]:
        key = row["scenario"], row["period"], row["position_id"]
        if key not in expected or row["person_id"] != expected[key]["person_id"]:
            raise ValueError("Assignment lacks matching occupied position-month")
        assigned_cost[key] += D(row["loaded_cost_usd"])
        assigned_fte[key] += D(row["assignment_fte"])
        assigned_capacity[key] += D(row["delivery_capacity_hours"])
        person_positions[row["scenario"], row["period"], row["person_id"]].add(row["position_id"])
    if any(len(v) != 1 for v in person_positions.values()):
        raise ValueError("Person is paid through multiple positions")
    for key, row in expected.items():
        if row["occupied"] and not row["authorized"]:
            raise ValueError("Occupancy exceeds position authorization")
        if assigned_fte[key] != int(row["occupied"]):
            raise ValueError("Occupied position assignment is not exactly one FTE")
        if assigned_cost[key] != D(row["expected_loaded_cost_usd"]):
            raise ValueError("Position payroll does not reconcile")
        if assigned_capacity[key] != D(row["capacity_hours"]):
            raise ValueError("Position capacity does not reconcile")
        if row["leave_state"] != "ACTIVE" and D(row["capacity_hours"]):
            raise ValueError("Leave/vacancy still provides delivery capacity")
        if not 0 <= D(row["ramp_fraction"]) <= 1:
            raise ValueError("Ramp exceeds full position capacity")
    payroll = defaultdict(D)
    journal = defaultdict(D)
    requests = {r["event_id"] for r in model.tables["events"] if r["kind"] == "PAYROLL_REQUEST"}
    for row in model.tables["workforce_assignments"]:
        payroll[row["scenario"], row["period"], row["unit"]] += D(row["loaded_cost_usd"])
    for row in model.tables["journal"]:
        if row["account"] == "BIZ_PAYROLL" and row["source_id"] in requests:
            journal[row["scenario"], row["period"], row["unit"]] += D(row["signed_usd"])
    if dict(payroll) != dict(journal):
        raise ValueError("Effective-dated payroll fails ledger reconciliation")
    if model.roster != model.make_roster():
        raise ValueError("Conditional changes mutated the source roster")
    return {
        "position_months": len(histories),
        "occupied_person_months": len(person_positions),
        "changes": len(model.tables["workforce_changes"]),
    }
