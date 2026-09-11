"""Versioned Tier 1 pricing overlay; never mutate the accepted finance sources."""

import copy
from decimal import Decimal as D

from enterprise.business.advisory import payout_factor
from enterprise.business.model import amount

POLICY_ID = "SH-OPERATIONS-ADVISORY-POLICY-001"
CLASSIFICATION = "PUBLIC_SYNTHETIC_CONDITIONAL_FORECAST"
SOURCES = (
    "docs/advisory/COMMERCIAL_CONTRACTING_AND_PRICING_STANDARD.md",
    "docs/advisory/CARRY_PLAN_STANDARD.md",
    "docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-09_ADVISORY_TIER1.md",
)
LOCKED_CURVE = (("0.70", "0.25"), ("0.85", "0.60"), ("1.00", "1.00"), ("1.20", "1.25"))
CARRY_STATUS = (
    "NOT_AWARDED_OR_ACCRUED; plan direction LOCKED; "
    "individual awards and legal implementation remain gated"
)


def check_declaration(declaration):
    """A different operating policy requires an explicit versioned implementation."""
    expected = {
        "policy_id": POLICY_ID,
        "version": "1.0.0",
        "effective_date": "2026-09-09",
        "classification": CLASSIFICATION,
        "canonical_sources": list(SOURCES),
        "value_payout_curve": [list(point) for point in LOCKED_CURVE],
        "carry_obligation": CARRY_STATUS,
    }
    if declaration != expected:
        raise ValueError("Advisory policy declaration differs from locked Tier 1 version 1.0.0")


def effective_policy(baseline, declaration):
    """Use a separate execution policy; original business input objects stay intact."""
    check_declaration(declaration)
    result = copy.deepcopy(baseline)
    result["value_payout_curve"] = copy.deepcopy(declaration["value_payout_curve"])
    result["canonical_sources"] = list(dict.fromkeys(result["canonical_sources"] + list(SOURCES)))
    return result


def validate(model):
    """Reperform all certifications and reject stale pricing or carry-status output."""
    declaration = model.operations_inputs["advisory_policy"]
    check_declaration(declaration)
    if model.policy["value_payout_curve"] != declaration["value_payout_curve"]:
        raise ValueError("Operating Advisory payout curve bypasses its policy overlay")
    engagements = {row["engagement_id"]: row for row in model.inputs["engagements"]}
    checked = 0
    for row in model.tables["value_certifications"]:
        engagement = engagements[row["engagement_id"]]
        if engagement["unit"] != "advisory":
            raise ValueError("Advisory certification belongs to a different business")
        if engagement["matter_class"] == "MEASURABLE_VALUE":
            factor = payout_factor(row["achievement"], declaration["value_payout_curve"])
        elif engagement["matter_class"] == "CAPABILITY":
            factor = D(1)
        else:
            factor = D(0)
        factor = min(factor, D(engagement["measurement"]["contract_variable_cap_factor"]))
        target = amount(D(engagement["fee_usd"]) * D(model.policy["cases"][row["scenario"]]["price_factor"]))
        committed = amount(target * D(engagement["committed_fraction"]))
        variable = amount((target - committed) * factor)
        expected = {
            "target_fee_usd": target,
            "committed_fee_usd": committed,
            "variable_fee_usd": variable,
            "total_fee_usd": committed + variable,
        }
        if any(D(row[key]) != value for key, value in expected.items()):
            raise ValueError("Advisory certification disagrees with the versioned payout policy")
        checked += 1
    if any(row["carry_obligation"] != CARRY_STATUS for row in model.tables["matter_rollforward"]):
        raise ValueError("Operating carry status incorrectly reopens settled plan direction")
    return {"policy_id": POLICY_ID, "version": declaration["version"], "certifications_checked": checked}
