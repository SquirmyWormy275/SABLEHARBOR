"""Cross-module accounting and immutable-source acceptance."""

import pytest

from enterprise.business import validation
from enterprise.business.model import load_inputs
from enterprise.operations import commercial, credit, matters, research, workforce
from enterprise.operations.build import sources
from enterprise.operations.model import OperatingModel
from sable_harbor.provenance.identity import generation_input_paths


@pytest.fixture(scope="module")
def model():
    return OperatingModel().build()


def test_domains_share_one_balanced_ledger(model):
    assert validation.business(model)["business_journals"] > 40000
    for module in (credit, commercial, matters, research, workforce):
        assert module.validate(model)
    count = len(model.tables["events"])
    assert model.build() is model
    assert len(model.tables["events"]) == count


def test_original_sources_are_unchanged_and_instances_isolated(model):
    assert model.inputs == load_inputs()
    other = OperatingModel()
    other.operations_inputs["credit"]["test_mutation"] = True
    assert "test_mutation" not in model.operations_inputs["credit"]


def test_source_inventory_includes_preserved_generation_inputs(model):
    inventory = sources(model)
    assert {str(p) for p in generation_input_paths()} <= set(inventory)
    assert "enterprise/operations/model.py" in inventory
    assert "enterprise/operations/source/credit.json" in inventory
