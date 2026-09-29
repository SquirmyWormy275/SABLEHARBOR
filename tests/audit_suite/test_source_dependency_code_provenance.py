"""Maintained source-file pins; not loaded interpreter or dependency attestation."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import source_dependency_reconciliation as reports
from enterprise.audit_suite.operating_source_bridge import sha
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_access_remediation_report_integration import context as native_context

BASE = "source_dependency_reconciliation.py"
IAM = "iam_review_reconciliation.py"
REMOVAL = "access_remediation_reconciliation.py"


@pytest.fixture(scope="module")
def context(tmp_path_factory):
    return native_context.__wrapped__(tmp_path_factory.mktemp("analysis-source-pins"))


def _plan(context, mode):
    plan = deepcopy(context[3])
    parent = plan["access_remediation_contracts"][0]["parent"]
    if mode in ("base", "iam"):
        del plan["access_remediation_contracts"]
    if mode in ("iam", "both"):
        plan["iam_review_contracts"] = [
            {
                "population_ref_id": parent["population_ref_id"],
                "decisions_ref_id": parent["decisions_ref_id"],
                "reconciliation_ref_id": parent["reconciliation_ref_id"],
                "application_ref_ids": [parent["application_ref_id"]],
                "hr_ref_ids": [parent["hr_ref_id"]],
            }
        ]
    return plan


@pytest.mark.parametrize("mode", ["base", "iam", "removal", "both"])
def test_exact_active_analysis_source_files_and_legacy_module_pin(context, tmp_path, mode):
    tmp_path.chmod(0o700)
    engine, actor, state, *_ = context
    plan = _plan(context, mode)
    output = tmp_path / "report"
    reports.write_report(engine, actor["id"], state["id"], plan, output=output)
    manifest = json.loads((output / "MANIFEST.json").read_bytes())
    expected = {BASE, "inference.py"} | (
        {IAM} if mode == "iam" else {IAM, REMOVAL} if mode in ("removal", "both") else set()
    )
    assert set(manifest["analysis_modules_sha256"]) == expected
    assert manifest["module_sha256"] == manifest["analysis_modules_sha256"][BASE]
    assert isinstance(manifest["module_sha256"], str)
    assert manifest["analysis_pin_scope"] == "MAINTAINED_SOURCE_FILES_NOT_LOADED_BINARY_ATTESTATION"
    for filename, digest in manifest["analysis_modules_sha256"].items():
        assert digest == sha((Path(reports.__file__).parent / filename).read_bytes())
    report = json.loads((output / "REPORT.json").read_bytes())
    assert ("iam_review_reconciliation" in report) == (mode in ("iam", "both"))
    assert ("access_remediation_reconciliation" in report) == (mode in ("removal", "both"))
    assert engine.store.get(actor["id"], state["id"])["revision"] == state["revision"]


@pytest.mark.parametrize("boundary", ["analysis", "final_authority"])
def test_changed_active_source_pin_rejects_before_publication(
    context, tmp_path, monkeypatch, boundary
):
    tmp_path.chmod(0o700)
    engine, actor, state, *_ = context
    changed = False
    original_pins = reports._analysis_source_pins
    original_reconcile = reports.reconcile
    original_current = reports._check_current
    checks = 0

    def pins(plan):
        value = original_pins(plan)
        if changed:
            value[REMOVAL] = "b" * 64
        return value

    def reconcile(*args, **kwargs):
        nonlocal changed
        result = original_reconcile(*args, **kwargs)
        if boundary == "analysis":
            changed = True
        return result

    def current(*args, **kwargs):
        nonlocal changed, checks
        result = original_current(*args, **kwargs)
        checks += 1
        if boundary == "final_authority" and checks >= 2:
            changed = True
        return result

    monkeypatch.setattr(reports, "_analysis_source_pins", pins)
    monkeypatch.setattr(reports, "reconcile", reconcile)
    monkeypatch.setattr(reports, "_check_current", current)
    output = tmp_path / "report"
    with pytest.raises(DomainError):
        reports.write_report(
            engine, actor["id"], state["id"], _plan(context, "removal"), output=output
        )
    assert changed and not output.exists()
    assert not list(tmp_path.glob(".source-reconciliation-*"))
    assert engine.store.get(actor["id"], state["id"])["revision"] == state["revision"]
