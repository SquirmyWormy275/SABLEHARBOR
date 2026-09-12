"""The delivery connects real HTTP identity, collection and independent review."""

import hashlib
import json

import pytest

from enterprise.ccf.operations import delivery, rehearsal
from enterprise.ccf.tests.test_operations import plans  # noqa: F401


def test_signed_http_collection_review_rehearsal(tmp_path, plans):  # noqa: F811
    result = rehearsal.run(tmp_path / "rehearsal", plans)
    assert result["status"] == "PASS" and result["real_http_requests"]
    assert result["initial_outcome_retained"] == "NOT_RUN"
    assert result["final_state"] == "CLOSED_CORRECTED_EVIDENCE"
    assert any(r["status"] == 401 for r in result["checks"])
    assert any(r["status"] == 400 for r in result["checks"])
    assert all(
        p.stat().st_mode & 0o077 == 0 for p in (tmp_path / "rehearsal").rglob("*") if p.is_file()
    )


def test_handoff_cannot_promote_synthetic_results(plans):  # noqa: F811
    reference = dict(source_dependencies=[dict(status="REVIEW_REQUIRED")], variant_comparisons={})
    report = dict(period_results={})
    packet = delivery.handoff(reference, plans, report)
    assert all(r["actual_coverage"] == "NOT_ASSERTED" for r in packet["rows"])
    assert all(
        g["status"] == "MISSING_ACTUAL_INPUTS" and not g["supplied_records"]
        for g in packet["required_live_inputs"]
    )
    assert packet["source_dependencies"] == reference["source_dependencies"]


def test_delivery_hash_verification_rejects_modified_member(tmp_path):
    p = tmp_path / "bundle"
    p.mkdir()
    (p / "member.json").write_text("{}")
    (p / "DELIVERY_MANIFEST.json").write_text(
        json.dumps(dict(files={"member.json": hashlib.sha256(b"{}").hexdigest()}))
    )
    (p / "member.json").write_text('{"claimed": "PASS"}')
    with pytest.raises(ValueError, match="hash mismatch"):
        delivery.verify(p)


@pytest.mark.parametrize("member", ["plans", "counts", "coverage", "rehearsal"])
def test_delivery_reperformance_rejects_resealed_inconsistency(
    tmp_path, monkeypatch, plans, member  # noqa: F811
):
    import copy

    selected = copy.deepcopy(plans)
    for p in selected.values():
        p.update(
            is_baseline_control=True,
            selected_frameworks=["SOC2", "HIPAA", "C5"],
            extension_targets=["C5"],
        )
    reference = tmp_path / "reference"
    reference.mkdir()
    (reference / "ASSESSMENT_RUN.json").write_text(
        json.dumps(dict(source_dependencies=[], variant_comparisons={}))
    )
    monkeypatch.setattr(delivery.assessment_run, "verify", lambda *a: None)
    monkeypatch.setattr(delivery, "compile_registry", lambda: {})
    monkeypatch.setattr(
        delivery.selection, "plans", lambda reference, targets: copy.deepcopy(selected)
    )
    bundle = tmp_path / "bundle"
    delivery.build(reference, tmp_path, bundle, targets=["C5"])
    assert delivery.verify(bundle)["verified"]
    if member == "coverage":
        p = bundle / "CONTROL_COVERAGE.csv"
        p.write_text(p.read_text().replace("NOT_ASSERTED", "ACCEPTED", 1))
    else:
        relative = {
            "plans": "control-exercise/TEST_PLANS.json",
            "counts": "DELIVERY_RESULT.json",
            "rehearsal": "integrated-rehearsal/INTEGRATION_RESULT.json",
        }[member]
        p = bundle / relative
        data = json.loads(p.read_text())
        if member == "plans":
            next(iter(data.values()))["selected_frameworks"] = ["SOC2", "HIPAA"]
        elif member == "counts":
            data["selected_controls"] += 1
        else:
            data["initial_outcome_retained"] = "PASS"
        p.write_text(json.dumps(data))
    manifest = bundle / "DELIVERY_MANIFEST.json"
    data = json.loads(manifest.read_text())
    data["files"][str(p.relative_to(bundle))] = hashlib.sha256(p.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="differ"):
        delivery.verify(bundle)
