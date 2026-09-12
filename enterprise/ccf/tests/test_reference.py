"""Reference planning must never manufacture operating evidence or review approval."""

import hashlib

import pytest

from enterprise.ccf.assurance import reference
from enterprise.ccf.assurance.engine import data, plan
from enterprise.ccf.assurance.models import Assessment, Catalog
from enterprise.ccf.registry import compile_registry, digest


@pytest.fixture(scope="module")
def native():
    return compile_registry()


def test_reference_scope_and_no_fabricated_results(native):
    c, a = reference.reference_inputs(native, include_c5=False)
    assert a.scope.boundaries == ["corporate", "RUNTIME-RENO-COLO", "RUNTIME-BOISE-DR"]
    assert set(a.scope.baseline[0].categories) == {"SECURITY", "AVAILABILITY", "CONFIDENTIALITY"}
    assert a.scope.assessment_mode == "DESIGN" and a.scope.origin == "SYNTHETIC"
    assert a.scope.period_start == a.scope.period_end
    assert a.scope.review is None and not a.evidence and not a.tests and not a.disclosures
    assert not a.scope.targets
    assert all(i.state == "PROPOSED" and i.review is None for i in a.implementations)
    assert all(x.disposition == "UNRESOLVED" for x in a.applicability)
    result = plan(c, a, native)
    assert result["summary"] == {"UNRESOLVED": 447}
    assert not any(f.inventory_complete or f.inventory_review for f in c.frameworks)


def test_criterion_population_and_pdf_anchors(native):
    c, _ = reference.reference_inputs(native, False)
    soc = [r for r in c.requirements if r.framework_id == "SOC2"]
    assert len(soc) == 70
    assert {r.id for r in soc if r.id.startswith("SOC2:DC")} == {
        f"SOC2:DC{i}" for i in range(1, 10)
    }
    assert (
        len([r for r in soc if r.category in {"SECURITY", "AVAILABILITY", "CONFIDENTIALITY"}]) == 47
    )
    assert all("PDF page" in r.locator for r in soc)
    assert all(any(a.id == "SOURCE_CONTEXT" for a in r.attributes) for r in soc)
    assert not any("PREP-DESCRIPTION" in r.id for r in soc)


def test_hipaa_inventory_includes_omitted_context(native):
    c, _ = reference.reference_inputs(native, False)
    hipaa = {r.id: r for r in c.requirements if r.framework_id == "HIPAA"}
    assert len(hipaa) == 102
    assert {
        "HIPAA:160.103",
        "HIPAA:160.310",
        "HIPAA:164.103",
        "HIPAA:164.509",
        "HIPAA:164.535",
    } <= hipaa.keys()
    inv = reference.source_inventory()
    assert sum(len(s["paragraphs"]) for s in inv["sections"]) == 1697
    assert inv["volume2_amendment_date"] == "2026-08-28"
    assert any(a.specification == "ADDRESSABLE" for a in hipaa["HIPAA:164.308"].attributes)
    assert any(a.id == "e(2)(ii)(J)" for a in hipaa["HIPAA:164.504"].attributes)
    assert any(a.id == "b" for a in hipaa["HIPAA:164.410"].attributes)


def test_workpaper_coverage_and_control_bindings(native):
    c, a = reference.reference_inputs(native, False)
    papers = reference.workpapers(c, a, native)
    expected = {
        (r.id, attr.id, b)
        for r in c.requirements
        if r.framework_id == "HIPAA"
        or (
            r.framework_id == "SOC2"
            and r.category in {"SECURITY", "AVAILABILITY", "CONFIDENTIALITY"}
        )
        for attr in r.attributes
        for b in a.scope.boundaries
    }
    assert {
        (p["requirement_id"], p["attribute_id"], p["boundary_id"]) for p in papers["test_plans"]
    } == expected
    assert len({p["id"] for p in papers["test_plans"]}) == len(expected)
    impls = {i.id for i in a.implementations}
    for p in papers["test_plans"]:
        assert set(p["candidate_implementation_ids"]) <= impls
        assert p["state"] == "PLANNED_NOT_EXECUTED"
        assert p["operating_period"] is None and not p["evidence_ids"]
        assert "result" not in p and "expected_population_digest" not in p
    assert all(i["appointment_status"] == "NOT_ASSERTED" for i in papers["implementations"])


def test_c5_candidates_do_not_become_coverage(native):
    c, a = reference.reference_inputs(native)
    assert [s.framework_id for s in a.scope.targets] == ["C5"]
    assert len([r for r in c.requirements if r.framework_id == "C5"]) == 625
    assert len({m.requirement_id for m in c.mappings if m.requirement_id.startswith("C5:")}) == 8
    assert not any(r.framework_id in {"ISO27001", "ISO42001"} for r in a.scope.targets)
    papers = reference.workpapers(c, a, native)
    targeted = [
        p
        for p in papers["test_plans"]
        if p["requirement_id"] == "C5:BCM-02.01B" and p["attribute_id"] == "OBJECTIVE-1"
    ]
    assert len(targeted) == 3 and all(
        p["candidate_control_ids"] == ["SH-BCM-001"] for p in targeted
    )
    report = plan(c, a, native)
    row = next(r for r in report["rows"] if r["requirement_id"] == "C5:BCM-02.01B")
    assert "SH-BCM-001" in row["candidate_reuse_from_baseline"]
    assert row["status"] == "UNRESOLVED"
    assert plan(c, a, native)["summary"] == {"UNRESOLVED": 2322}


@pytest.fixture
def synthetic_sources(tmp_path, monkeypatch, native):
    """Tiny public-shaped test XML and fake PDF bytes, never production source substitutions."""
    sections = ["160.103", "164.306", "164.410", "164.502"]
    xml = (
        "<ROOT>"
        + "".join(
            f'<PART TYPE="PART" N="{ref.split(".")[0]}"><SECTION TYPE="SECTION" N="§ {ref}"><HEAD>Test</HEAD><P>Test definition</P></SECTION></PART>'
            for ref in sections
        )
        + "</ROOT>"
    ).encode()
    h = hashlib.sha256(xml).hexdigest()
    inv = dict(
        source_url="https://example.invalid/test.xml",
        source_sha256=h,
        source_bytes=len(xml),
        volume2_amendment_date="2026-08-28",
        retrieved_on="2026-09-11",
        limitation="Synthetic test inventory",
        sections=[
            dict(
                locator=ref,
                title="Test definition",
                paragraphs=[
                    dict(
                        id="P0001",
                        text_sha256=hashlib.sha256(b"Test definition").hexdigest(),
                        leading_markers=None,
                    )
                ],
            )
            for ref in sections
        ],
    )
    monkeypatch.setattr(reference, "source_inventory", lambda: inv)
    original = reference.reference_inputs

    def inputs(n, include_c5=True):
        c, a = original(n, include_c5)
        d = data(c)
        for source in d["sources"]:
            if source["access"] == "AVAILABLE":
                content = (
                    xml
                    if source["id"] == "SOURCE-HIPAA"
                    else b"%PDF-SYNTHETIC-TEST-" + source["id"].encode()
                )
                source["content_sha256"] = hashlib.sha256(content).hexdigest()
                (tmp_path / source["content_sha256"]).write_bytes(content)
        c = Catalog.model_validate(d)
        d = data(a)
        d["catalog_digest"] = digest(data(c))
        return c, Assessment.model_validate(d)

    monkeypatch.setattr(reference, "reference_inputs", inputs)
    return tmp_path, inv


def test_bundle_reperformance_and_tamper_rejection(native, synthetic_sources, tmp_path):
    sources, _ = synthetic_sources
    output = tmp_path / "bundle"
    reference.build_reference(output, native, sources, include_c5=False)
    assert reference.verify_reference(output, native, sources)["verified"]
    path = output / "WORKPAPERS.json"
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="member/hash"):
        reference.verify_reference(output, native, sources)


def test_inventory_reconciliation_rejects_omission(native, synthetic_sources):
    sources, inv = synthetic_sources
    c, _ = reference.reference_inputs(native, False)
    reference.validate_source_inventory(c, sources)
    inv["sections"][0]["paragraphs"] = []
    with pytest.raises(ValueError, match="inventory differs"):
        reference.validate_source_inventory(c, sources)


def test_available_original_required(native, synthetic_sources):
    sources, _ = synthetic_sources
    c, _ = reference.reference_inputs(native, False)
    s = next(s for s in c.sources if s.access == "AVAILABLE")
    (sources / s.content_sha256).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash mismatch"):
        reference.validate_source_inventory(c, sources)
