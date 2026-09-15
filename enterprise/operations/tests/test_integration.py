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


def test_current_records_do_not_change_forecast_identity_but_forecast_inputs_do(
    tmp_path, monkeypatch
):
    import json
    from pathlib import Path

    from enterprise.operations import model as module

    original = OperatingModel()
    source = tmp_path / "source"
    source.mkdir()
    for name, value in original.operations_inputs.items():
        (source / f"{name}.json").write_text(json.dumps(value))
    monkeypatch.setattr(module, "__file__", str(tmp_path / "model.py"))
    (source / "completed_period_2026_08.json").write_text('{"employees": 702}')
    assert OperatingModel().input_hash == original.input_hash
    (source / "completed_period_2026_08.json").write_text('{"employees": 703}')
    assert OperatingModel().input_hash == original.input_hash
    credit_source = Path(source / "credit.json")
    changed = json.loads(credit_source.read_text())
    changed["mutation_for_identity_test"] = "A used source must remain bound"
    credit_source.write_text(json.dumps(changed))
    assert OperatingModel().input_hash != original.input_hash
