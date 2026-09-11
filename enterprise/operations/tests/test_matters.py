from __future__ import annotations

import copy
import hashlib
import json

import pytest

from enterprise.business.model import BusinessModel, load_inputs
from enterprise.operations import matters


class MatterModel(matters.MatterMixin, BusinessModel):
    pass


@pytest.fixture(scope="module")
def model():
    return MatterModel().build()


def actions(model, eid, kind):
    return [
        r
        for r in model.tables["events"]
        if r["kind"] == kind and r.get("engagement_id", r["source_id"]) == eid
    ]


def test_complete_gates_and_preserved_inputs(model):
    report = matters.validate(model)
    assert report == {"selected_matters": 6, "monthly_gate_decisions": 1062}
    assert model.inputs == load_inputs()
    assert model.build() is model


def test_missing_rights_delays_actual_committed_billing(model):
    accepted = actions(model, "ADV-2027-02", "MATTER_ACCEPTANCE")
    assert len(accepted) == 3
    assert {r["period"] for r in accepted} == {"2027-03-31"}
    assert all(r["period"] >= "2027-03-31" for r in actions(model, "ADV-2027-02", "DELIVERY_WORK"))


@pytest.mark.parametrize(
    "eid,first,last",
    [
        ("ADV-2027-03", "2027-04-30", "2027-05-31"),
        ("ADV-2027-04", "2027-04-30", "2027-06-30"),
        ("ADV-2027-05", "2027-05-31", "2027-07-31"),
    ],
)
def test_failure_stop_and_change_causally_block_activity(model, eid, first, last):
    for kind in (
        "DELIVERY_WORK",
        "OUTCOME_ACCEPTED",
        "VALUE_CERTIFIED",
        "CLIENT_TRANSFER_ACCEPTED",
    ):
        assert not any(first <= r["period"] <= last for r in actions(model, eid, kind))
    assert len(actions(model, eid, "CLIENT_TRANSFER_ACCEPTED")) == 3


def test_decline_never_starts_or_bills(model):
    for kind in (
        "MATTER_ACCEPTANCE",
        "DELIVERY_WORK",
        "OUTCOME_ACCEPTED",
        "VALUE_CERTIFIED",
        "CLIENT_TRANSFER_ACCEPTED",
    ):
        assert actions(model, "ADV-2027-06", kind) == []
    rows = [r for r in model.tables["matter_determinations"] if r["engagement_id"] == "ADV-2027-06"]
    assert len(rows) == 3 and all(r["decision"] == "DECLINE" for r in rows)


def test_fixed_decision_fee_cannot_gain_contingent_success(model):
    rows = [r for r in model.tables["value_certifications"] if r["engagement_id"] == "ADV-2027-03"]
    assert len(rows) == 3
    assert {r["variable_fee_usd"] for r in rows} == {"0.0000"}


def test_missing_gate_is_not_treated_as_approved(model):
    changed = copy.copy(model)
    changed.tables = copy.copy(model.tables)
    changed.tables["matter_gate_decisions"] = model.tables["matter_gate_decisions"][1:]
    with pytest.raises(ValueError, match="gate|history"):
        matters.validate(changed)


def test_relabeling_failed_control_as_pass_is_rejected(model):
    changed = copy.copy(model)
    changed.tables = copy.copy(model.tables)
    changed.tables["matter_controls"] = copy.deepcopy(model.tables["matter_controls"])
    next(r for r in changed.tables["matter_controls"] if r["result"] == "FAIL")["result"] = "PASS"
    with pytest.raises(ValueError, match="source determinations"):
        matters.validate(changed)


@pytest.mark.parametrize(
    "mutation", ["authority", "order", "correction", "identity", "classification"]
)
def test_source_controls_reject_invalid_histories(mutation):
    model = MatterModel()
    inputs = copy.deepcopy(matters._inputs(model))
    if mutation == "authority":
        inputs["matters"][0]["events"][0]["role"] = "originator"
    elif mutation == "order":
        inputs["matters"][1]["events"][1]["month"] = 1
    elif mutation == "correction":
        inputs["matters"][0]["events"][0]["decision"] = "REACCEPT"
    elif mutation == "identity":
        inputs["matters"][1]["engagement_id"] = inputs["matters"][0]["engagement_id"]
    else:
        inputs["classification"] = "ACTUAL"
    model.operations_inputs = {"matters": inputs}
    with pytest.raises(ValueError):
        model.build()


@pytest.fixture(scope="module")
def packages(model, tmp_path_factory):
    output = tmp_path_factory.mktemp("client-matters")
    return matters.build_matter_packages(model, output)


def test_packages_execute_seven_tests_for_every_accepted_case(model, packages):
    assert len(packages) == 15
    assert len(model.tables["matter_handover_evidence"]) == 15
    for package in packages:
        manifest = matters.verify_matter_package(package)
        assert manifest["engagement_id"] != "ADV-2027-06"
        assert len(list(package.iterdir())) == 8
    matters.validate(model)


def test_client_bundles_are_deterministic(model, packages, tmp_path):
    again = matters.build_matter_packages(model, tmp_path)
    for first, second in zip(packages, again):
        assert {p.name: p.read_bytes() for p in first.iterdir()} == {
            p.name: p.read_bytes() for p in second.iterdir()
        }


@pytest.mark.parametrize(
    "mutation",
    [
        "content",
        "extra",
        "missing",
        "wrong_client",
        "proof",
        "resigned_payload",
        "extra_metadata",
        "wrong_matter",
    ],
)
def test_packages_reject_tampering(packages, tmp_path, mutation):
    import shutil

    package = tmp_path / "package"
    shutil.copytree(packages[0], package)
    if mutation == "content":
        (package / "workflow.py").write_text("raise RuntimeError('tampered')\n")
    elif mutation == "extra":
        (package / "professional-plane.txt").write_text("not allowed")
    elif mutation == "missing":
        (package / "verification.json").unlink()
    elif mutation == "wrong_client":
        with pytest.raises(ValueError, match="different client"):
            matters.verify_matter_package(package, "SYN-CUSTOMER-999")
        return
    elif mutation == "proof":
        proof = json.loads((package / "verification.json").read_text())
        proof["executed_tests"] = 0
        (package / "verification.json").write_text(json.dumps(proof))
    elif mutation == "resigned_payload":
        (package / "workflow.py").write_text("print('invented PASS')\n")
        manifest = json.loads((package / "manifest.json").read_text())
        manifest["files_sha256"]["workflow.py"] = hashlib.sha256(
            (package / "workflow.py").read_bytes()
        ).hexdigest()
        (package / "manifest.json").write_text(json.dumps(manifest))
    else:
        manifest = json.loads((package / "manifest.json").read_text())
        if mutation == "extra_metadata":
            manifest["private_notes"] = "Unapproved field"
        else:
            manifest["engagement_id"] = "ADV-2027-06"
        (package / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        matters.verify_matter_package(package)


def test_changed_source_inputs_are_not_mutated_on_gate_exception():
    class BrokenEngine:
        def outcomes(self):
            raise RuntimeError("fee engine failure")

    class BrokenModel(matters.MatterMixin, BrokenEngine, BusinessModel):
        pass

    model = BrokenModel()
    original = copy.deepcopy(model.inputs)
    with pytest.raises(RuntimeError, match="fee engine failure"):
        model.build()
    assert model.inputs == original
