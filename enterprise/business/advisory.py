"""Independent matter acceptance, outcome pricing and client-transfer contracts."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal as D


def payout_factor(achievement, curve):
    """Contractual piecewise-linear payout; below 50% earns zero by default."""
    value = D(str(achievement))
    points = [(D(x), D(y)) for x, y in curve]
    if len(points) < 2 or any(x < 0 or y < 0 for x, y in points):
        raise ValueError("Payout curve requires at least two nonnegative points")
    if any(x2 <= x1 or y2 < y1 for (x1, y1), (x2, y2) in zip(points, points[1:])):
        raise ValueError("Payout curve must have increasing achievement and nondecreasing payout")
    if value < points[0][0]:
        return D(0)
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if value <= x2:
            return y1 + (value - x1) * (y2 - y1) / (x2 - x1)
    return points[-1][1]


def check_transfer(transfer, license_validator=None):
    for key in ("client_owner", "runbook", "stop_authority", "maintenance_owner"):
        if not transfer.get(key):
            raise ValueError("Transfer lacks client operating ownership or support")
    if transfer["test_state"] != "PASS":
        raise ValueError("Client capability not qualified for transfer")
    for component in transfer["components"]:
        if component["plane"] != "client" or component["classification"] not in {
            "CLIENT_OWNED",
            "LICENSED_PRODUCT",
        }:
            raise ValueError(
                "Professional-plane, cross-client or institutional material cannot transfer"
            )
    for component in transfer["components"]:
        if component["classification"] == "LICENSED_PRODUCT" and (
            license_validator is None or license_validator(component) is not True
        ):
            raise ValueError("Licensed transfer requires independent contract-rights validation")
    ids = [c["id"] for c in transfer["components"]]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("Transfer component identities missing or duplicated")


def check_matter(e):
    roles = e["roles"]
    if len(set(roles.values())) != len(roles) or not all(roles.values()):
        raise ValueError("Matter governance requires distinct identified role holders")
    if roles["acceptance_principal"] == roles["originator"]:
        raise ValueError("Originator cannot accept own matter")
    for role in ("independent_reviewer", "value_officer"):
        if roles[role] in {roles["originator"], roles["matter_principal"]}:
            raise ValueError("Delivery/origination cannot independently review or certify value")
    if not 0 <= D(e["committed_fraction"]) <= 1:
        raise ValueError("Invalid committed fraction")
    if e["matter_class"] == "DECISION" and D(e["committed_fraction"]) != 1:
        raise ValueError("Decision recommendation cannot generate a contingent success fee")
    if e["atlas_fee_included"]:
        raise ValueError("Atlas licensing must remain separate from Advisory matter economics")
    if e["fee_usd"] < 150000 and not e.get("minimum_fee_exception"):
        raise ValueError("Below-minimum matter lacks explicit strategic exception")
    if e["measurement"]["addressable_value_usd"] <= 0:
        raise ValueError("Matter measurement needs a positive target")
    if not 0 <= D(e["measurement"]["attribution_fraction"]) <= 1:
        raise ValueError("Attribution fraction outside zero to one")
    if (
        e["measurement"]["measurement_lag_months"] < 0
        or D(e["measurement"]["contract_variable_cap_factor"]) < 0
    ):
        raise ValueError("Invalid measurement lag or variable cap")
    check_transfer(e["transfer"])


def run_matters(model):
    # Import here avoids an import cycle while using the common monetary convention.
    from .model import amount, money, period

    unit = "advisory"
    available = model.capacity[unit]
    for e in model.inputs["engagements"]:
        if e["unit"] != unit or e["start_month"] > model.month:
            continue
        eid = e["engagement_id"]
        target_fee = amount(D(e["fee_usd"]) * D(model.case["price_factor"]))
        committed = amount(target_fee * D(e["committed_fraction"]))
        baseline_hash = hashlib.sha256(
            json.dumps(e["measurement"], sort_keys=True).encode()
        ).hexdigest()
        if eid not in model.matter_started:
            event = model.event(
                "MATTER_ACCEPTANCE",
                eid,
                unit,
                practice=e["practice"],
                matter_class=e["matter_class"],
                disposition=e["acceptance_status"],
                reason=e["acceptance_reason"],
                **e["roles"],
            )
            model.matter_started.add(eid)
            if e["acceptance_status"] == "ACCEPT":
                model.event(
                    "VALUE_BASELINE_APPROVED",
                    eid,
                    unit,
                    baseline_sha256=baseline_hash,
                    value_officer=e["roles"]["value_officer"],
                    baseline_source=e["measurement"]["source_id"],
                    target_fee_usd=money(target_fee),
                    committed_fee_usd=money(committed),
                    target_variable_usd=money(target_fee - committed),
                    attribution=e["measurement"]["attribution_fraction"],
                )
                model.invoice(event, unit, e["customer_id"], committed, deferred=True)
        if e["acceptance_status"] != "ACCEPT":
            continue
        for index, milestone in enumerate(e["milestones"]):
            key = f"{eid}-{milestone['name']}"
            if key in model.accepted or e["start_month"] + milestone["offset"] > model.month:
                continue
            if key not in model.work_done:
                hours = amount(
                    D(e["delivery_hours"])
                    * D(milestone["hours_fraction"])
                    * D(model.case["rework_factor"])
                )
                if milestone["name"] == e["rejection_milestone"]:
                    hours = amount(hours * D("1.15"))
                if hours > available:
                    model.event("ENGAGEMENT_BACKLOG", key, unit, hours_required=money(hours))
                    continue
                available -= hours
                model.work_done[key] = model.month
                model.event(
                    "DELIVERY_WORK",
                    key,
                    unit,
                    engagement_id=eid,
                    hours=money(hours),
                    billing_basis="COST_AND_CAPACITY_ONLY",
                    practice=e["practice"],
                )
                model.cost(
                    f"TRAVEL-{key}", unit, "BIZ_DELIVERY", hours * 12 * D(model.case["cost_factor"])
                )
                if milestone["name"] == e["rejection_milestone"]:
                    model.event(
                        "ACCEPTANCE_REJECTED",
                        key,
                        unit,
                        engagement_id=eid,
                        reason="Transfer/operating test incomplete; rework earns no extra committed fee",
                    )
            due = model.work_done[key] + model.case["acceptance_delay_months"]
            if milestone["name"] == e["rejection_milestone"]:
                due += e["rejection_delay_months"]
            previous = e["milestones"][index - 1]["name"] if index else None
            if due > model.month or (previous and f"{eid}-{previous}" not in model.accepted):
                continue
            event = model.event(
                "OUTCOME_ACCEPTED",
                key,
                unit,
                engagement_id=eid,
                reviewer=e["roles"]["independent_reviewer"],
                committed_recognition_usd=money(committed * D(milestone["fee_fraction"])),
            )
            earned = amount(committed * D(milestone["fee_fraction"]))
            model.post(
                event,
                unit,
                [("BIZ_DEFERRED", earned), ("BIZ_REVENUE", -earned)],
                "Committed matter fee earned by performed/accepted milestone, never hours billed",
            )
            model.accepted.add(key)
            if index == len(e["milestones"]) - 1:
                check_transfer(e["transfer"])
                model.event(
                    "CLIENT_TRANSFER_ACCEPTED",
                    eid,
                    unit,
                    transfer_manifest=e["transfer"],
                    professional_plane_included=False,
                    independent_reviewer=e["roles"]["independent_reviewer"],
                )
                model.measurement_due[eid] = (
                    model.month + e["measurement"]["measurement_lag_months"]
                )
        if (
            eid in model.measurement_due
            and model.measurement_due[eid] <= model.month
            and eid not in model.certified
        ):
            achievement = D(model.case["certified_achievement_factor"]) * D(
                e["measurement"]["attribution_fraction"]
            )
            if e["matter_class"] == "MEASURABLE_VALUE":
                factor = payout_factor(achievement, model.policy["value_payout_curve"])
            elif e["matter_class"] == "CAPABILITY":
                factor = D(
                    1
                )  # Explicit tested transfer acceptance; no subjective satisfaction gate.
            else:
                factor = D(0)  # Fixed Decision Matter; no recommendation-linked contingent fee.
            factor = min(factor, D(e["measurement"]["contract_variable_cap_factor"]))
            variable = amount((target_fee - committed) * factor)
            baseline = D(e["measurement"]["baseline_annual_cost_usd"])
            savings = amount(D(e["measurement"]["addressable_value_usd"]) * achievement)
            event = model.event(
                "VALUE_CERTIFIED",
                eid,
                unit,
                value_officer=e["roles"]["value_officer"],
                baseline_sha256=baseline_hash,
                measured_cost_usd=money(baseline - savings),
                certified_savings_usd=money(savings),
                achievement=str(achievement),
                payout_factor=str(factor),
                variable_fee_usd=money(variable),
                measurement_state="CONDITIONAL_SYNTHETIC_CERTIFICATION",
            )
            model.invoice(event, unit, e["customer_id"], variable)
            model.certified.add(eid)
            model.tables["value_certifications"].append(
                {
                    "scenario": model.scenario,
                    "period": period(model.month)[2],
                    "unit": unit,
                    "engagement_id": eid,
                    "matter_class": e["matter_class"],
                    "baseline_sha256": baseline_hash,
                    "baseline_cost_usd": money(baseline),
                    "target_savings_usd": e["measurement"]["addressable_value_usd"],
                    "certified_savings_usd": money(savings),
                    "achievement": str(achievement),
                    "target_fee_usd": money(target_fee),
                    "committed_fee_usd": money(committed),
                    "variable_fee_usd": money(variable),
                    "total_fee_usd": money(committed + variable),
                    "value_officer": e["roles"]["value_officer"],
                    "source_id": event,
                }
            )
        pending = sum(
            (
                D(m["fee_fraction"])
                for m in e["milestones"]
                if f"{eid}-{m['name']}" not in model.accepted
            ),
            D(0),
        )
        model.tables["matter_rollforward"].append(
            {
                "scenario": model.scenario,
                "period": period(model.month)[2],
                "unit": unit,
                "engagement_id": eid,
                "practice": e["practice"],
                "unperformed_committed_fee_usd": money(committed * pending),
                "uncertified_variable_target_usd": money(
                    0 if eid in model.certified else target_fee - committed
                ),
                "transfer_accepted": eid in model.measurement_due,
                "value_certified": eid in model.certified,
                "carry_obligation": "NOT_AWARDED_OR_ACCRUED; plan mechanics remain OPEN",
            }
        )
    model.tables["capacity"].append(
        {
            "scenario": model.scenario,
            "period": period(model.month)[2],
            "unit": unit,
            "capacity_hours": money(model.capacity[unit]),
            "used_hours": money(model.capacity[unit] - available),
            "remaining_hours": money(available),
        }
    )
