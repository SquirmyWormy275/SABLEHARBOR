"""Design completeness, scoped evidence reuse and preserved remediation history."""

from collections import Counter
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
import yaml

from enterprise.ccf.assurance import preparation, reference
from enterprise.ccf.assurance.engine import data, plan
from enterprise.ccf.assurance.examples import bind_fixture_reviews
from enterprise.ccf.assurance.models import Assessment
from enterprise.ccf.assurance.reference_exercise import exercise
from enterprise.ccf.registry import compile_registry


@pytest.fixture(scope="module")
def native():
    return compile_registry()


@pytest.fixture(scope="module")
def stages(native):
    return exercise(native)[0]


def test_design_population_is_complete_without_approval(native):
    design = preparation.designs(native)
    assert len(design["requirements"]) == 149 and len(design["controls"]) == 64
    assert len(design["supplements"]) == 5
    assert all(r["applicability"] == "PROPOSED_ANALYSIS_ONLY" for r in design["requirements"])
    assert all(c["appointment_status"] == "NOT_ASSERTED" for c in design["controls"])
    assert all(m["review"] is None for m in design["mapping_workpapers"])
    assert len({c["procedure"] for c in design["controls"]}) == 64
    assert all(len(c["boundary_execution"]) == 3 for c in design["controls"])
    requirements = {r["requirement_id"]: r for r in design["requirements"]}
    assert requirements["HIPAA:160.302"]["proposed_role_treatment"] == "RESERVED"
    assert requirements["HIPAA:164.509"]["proposed_role_treatment"] == "JUDICIAL_STATUS_HOLD"
    assert requirements["HIPAA:164.404"]["proposed_role_treatment"] == "CUSTOMER_DUTY_SUPPORT"
    assert requirements["HIPAA:164.410"]["proposed_role_treatment"] == "DIRECT_CANDIDATE"
    assert requirements["SOC2:A1.1"]["supplement_ids"] == ["CAPACITY"]


def test_missing_design_cannot_silently_pass(native, monkeypatch):
    original = preparation.indexed

    def missing(filename, key):
        rows = original(filename, key)
        if filename == "control_procedures.json":
            rows.pop("SH-IAM-004")
        return rows

    monkeypatch.setattr(preparation, "indexed", missing)
    with pytest.raises(ValueError, match="procedure population"):
        preparation.designs(native)


def test_shared_evidence_requires_distinct_framework_tests(stages):
    _, _, a, p = stages[0]
    assert p["summary"] == {"SUPPORTED": 12}
    for b in reference.BOUNDARIES:
        tests = [t for t in a.tests if t.boundary_id == b and "ACCESS" in t.requirement_id]
        assert len(tests) == 2 and tests[0].evidence_ids == tests[1].evidence_ids
    shared = [e.payload["shared_corporate_sha256"] for e in a.evidence if "ACCESS" in e.id]
    assert len(shared) == 3 and len(set(shared)) == 1
    assert not a.disclosures and a.scope.origin == "SYNTHETIC"


def test_corporate_evidence_does_not_automatically_cover_site(stages, native):
    _, c, a, _ = stages[0]
    modified = data(a)
    site = next(
        t
        for t in modified["tests"]
        if t["boundary_id"] == reference.BOUNDARIES[1] and "ACCESS" in t["requirement_id"]
    )
    corporate = next(
        e for e in modified["evidence"] if e["boundary_id"] == "corporate" and "ACCESS" in e["id"]
    )
    site["evidence_ids"] = [corporate["id"]]
    a = Assessment.model_validate(bind_fixture_reviews(modified))
    row = next(
        r
        for r in plan(c, a, native)["rows"]
        if r["requirement_id"] == site["requirement_id"] and r["boundary_id"] == site["boundary_id"]
    )
    assert row["status"] == "GAP"
    assert "EVIDENCE_BOUNDARY_MISMATCH" in row["attributes"][0]["issues"]


def test_target_selection_does_not_inherit_baseline_tests(stages):
    p = stages[1][3]
    assert p["summary"] == {"GAP": 6, "SUPPORTED": 12}
    restores = [r for r in p["rows"] if r["requirement_id"] == "C5:FICTIONAL-RESTORE"]
    assert all(
        r["candidate_reuse_from_baseline"] == ["SH-BCM-003"] and r["status"] == "GAP"
        for r in restores
    )
    notices = [r for r in p["rows"] if r["requirement_id"] == "C5:FICTIONAL-NOTICE"]
    assert all("IMPLEMENTATION_GAP" in r["attributes"][0]["issues"] for r in notices)


def test_same_period_pass_preserves_failed_result(stages):
    for stage in stages[2:4]:
        assert stage[3]["summary"] == {"GAP": 1, "SUPPORTED": 17}
    a = stages[3][2]
    tests = [
        t
        for t in a.tests
        if t.requirement_id == "C5:FICTIONAL-RESTORE" and t.boundary_id == reference.BOUNDARIES[2]
    ]
    assert Counter(t.result for t in tests) == {"FAIL": 1, "PASS": 1}


def test_prospective_fix_retains_historical_failure(stages, native):
    _, _, a, p = stages[4]
    assert p["summary"] == {"SUPPORTED": 18}
    assert str(a.scope.period_start) == str(a.scope.period_end) == "2026-09-10"
    failure = next(t for t in a.tests if t.result == "FAIL")
    impl = next(i for i in a.implementations if i.id == failure.implementation_id)
    assert str(impl.effective_to) == "2026-09-09"
    assert any(e.id in failure.evidence_ids for e in a.evidence)
    assert "earlier period remains failed" in exercise(native)[1]["limitation"]


def test_c5_sharpened_population_and_source_reperformance(tmp_path, monkeypatch, native):
    c, _ = reference.reference_inputs(native)
    inventory = reference.read_json(reference.DATA / "c5_inventory.json")
    assert len(inventory["corrected_missing_ids"]) == 29
    assert Counter(x["kind"] for x in inventory["children"].values()) == {
        "basic": 462,
        "additional_sharpen": 29,
        "additional_complement": 132,
    }
    assert set("C5:" + r for r in inventory["corrected_missing_ids"]) <= {
        r.id for r in c.requirements
    }
    # Independently supplied tiny publisher-shaped source: omission and category regression tests.
    members = [
        dict(
            identifier="01",
            basic=[dict(identifier="01B", criterion="Synthetic basic")],
            additional_sharpen=[dict(identifier="01AS", criterion="Synthetic sharpen")],
        )
    ]
    import hashlib

    expected = {
        "AM-01.01B": dict(
            kind="basic",
            member="AM.yml",
            text_sha256=hashlib.sha256(b"Synthetic basic").hexdigest(),
        ),
        "AM-01.01AS": dict(
            kind="additional_sharpen",
            member="AM.yml",
            text_sha256=hashlib.sha256(b"Synthetic sharpen").hexdigest(),
        ),
    }
    inv = dict(source_sha256="source", parents=["AM-01"], children=expected)
    with ZipFile(tmp_path / "source", "w") as z:
        z.writestr("AM.yml", yaml.safe_dump(members))
    monkeypatch.setattr(reference, "read_json", lambda path: inv)
    requirements = [
        SimpleNamespace(id="C5:AM-01.01B", framework_id="C5", category="BASIC"),
        SimpleNamespace(id="C5:AM-01.01AS", framework_id="C5", category="ADDITIONAL"),
    ]
    reference.validate_c5_inventory(SimpleNamespace(requirements=requirements), tmp_path)
    with pytest.raises(ValueError, match="omits or misclassifies"):
        reference.validate_c5_inventory(SimpleNamespace(requirements=requirements[:1]), tmp_path)
    requirements[1].category = "BASIC"
    with pytest.raises(ValueError, match="omits or misclassifies"):
        reference.validate_c5_inventory(SimpleNamespace(requirements=requirements), tmp_path)


def test_real_catalog_remains_unresolved(native):
    c, a = reference.reference_inputs(native)
    assert plan(c, a, native)["summary"] == {"UNRESOLVED": 2322}
    assert all(m.review is None for m in c.mappings)
    assert not a.tests and not a.evidence
