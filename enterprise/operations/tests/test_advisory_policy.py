"""Locked payout boundaries, contract caps and immutable baseline regression."""

import copy
from decimal import Decimal as D

import pytest

from enterprise.business.advisory import payout_factor
from enterprise.business.model import BusinessModel, load_inputs
from enterprise.operations import advisory_policy
from enterprise.operations.model import OperatingModel


@pytest.mark.parametrize(
    "achievement,expected",
    [("0", "0"), ("0.50", "0"), ("0.699999", "0"), ("0.70", "0.25"),
     ("0.775", "0.425"), ("0.85", "0.60"), ("0.925", "0.80"),
     ("1.00", "1.00"), ("1.10", "1.125"), ("1.20", "1.25"), ("2", "1.25")],
)
def test_locked_thresholds_interpolation_and_ceiling(achievement, expected):
    model = OperatingModel()
    assert payout_factor(achievement, model.policy["value_payout_curve"]) == D(expected)


def test_overlay_preserves_baseline_and_input_objects():
    original = load_inputs()
    before = copy.deepcopy(original)
    baseline = BusinessModel(original)
    successor = OperatingModel(original)
    assert original == before == successor.inputs == baseline.inputs
    assert baseline.policy["value_payout_curve"] == before["policy"]["value_payout_curve"]
    assert successor.policy is not successor.inputs["policy"]
    assert successor.policy["value_payout_curve"] != baseline.policy["value_payout_curve"]
    successor.policy["cases"]["base"]["price_factor"] = "2"
    assert original == before
    assert baseline.policy["cases"]["base"]["price_factor"] == "1"


@pytest.mark.parametrize("key", ["version", "effective_date", "classification", "value_payout_curve"])
def test_policy_drift_fails_closed(key):
    model = OperatingModel()
    operations = copy.deepcopy(model.operations_inputs)
    operations["advisory_policy"][key] = "unapproved"
    with pytest.raises(ValueError, match="locked Tier 1"):
        OperatingModel(operations_inputs=operations)


@pytest.fixture(scope="module")
def built():
    inputs = load_inputs()
    engagement = next(e for e in inputs["engagements"] if e["engagement_id"] == "ADV-2027-01")
    engagement["measurement"]["contract_variable_cap_factor"] = "0.30"
    return OperatingModel(inputs).build()


def test_certifications_respect_lower_contractual_caps(built):
    rows = [r for r in built.tables["value_certifications"] if r["engagement_id"] == "ADV-2027-01"]
    assert len(rows) == 3
    for row in rows:
        variable_target = D(row["target_fee_usd"]) - D(row["committed_fee_usd"])
        assert D(row["variable_fee_usd"]) <= variable_target * D("0.30")
    assert any(D(r["variable_fee_usd"]) > 0 for r in rows)
    assert advisory_policy.validate(built)["certifications_checked"] > 0


def test_fixed_decisions_and_carry_boundary_remain_explicit(built):
    decisions = [r for r in built.tables["value_certifications"] if r["matter_class"] == "DECISION"]
    assert decisions and all(D(r["variable_fee_usd"]) == 0 for r in decisions)
    assert all(r["carry_obligation"] == advisory_policy.CARRY_STATUS for r in built.tables["matter_rollforward"])
    assert built.inputs["policy"] == load_inputs()["policy"]


def test_tampered_certification_is_rejected(built):
    changed = copy.copy(built)
    changed.tables = copy.copy(built.tables)
    changed.tables["value_certifications"] = copy.deepcopy(built.tables["value_certifications"])
    changed.tables["value_certifications"][0]["variable_fee_usd"] = "999999999.0000"
    with pytest.raises(ValueError, match="certification disagrees"):
        advisory_policy.validate(changed)


def test_overlay_sources_and_fingerprint_are_retained():
    from enterprise.operations.build import sources
    model = OperatingModel()
    inventory = sources(model)
    assert set(advisory_policy.SOURCES) <= inventory.keys()
    assert "enterprise/operations/source/advisory_policy.json" in inventory
    assert "enterprise/operations/advisory_policy.py" in inventory
    operations = copy.deepcopy(model.operations_inputs)
    operations["credit"]["test_input_identity"] = "changed"
    assert OperatingModel(operations_inputs=operations).input_hash != model.input_hash
