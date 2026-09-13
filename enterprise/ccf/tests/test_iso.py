"""ISO source coverage and candidate deltas must not turn into unsupported assurance."""

from copy import deepcopy

import pytest

from enterprise.ccf.assurance import iso
from enterprise.ccf.assurance.engine import data, plan
from enterprise.ccf.assurance.models import Assessment, Catalog
from enterprise.ccf.registry import compile_registry, digest


@pytest.fixture(scope="module")
def native():
    return compile_registry()


def test_identifier_inventory_rejects_omission_and_substitution():
    rows = iso.read_json(iso.DATA / "requirements.json")
    iso.validate_authored_inventory(rows)
    with pytest.raises(ValueError, match="inventory size"):
        iso.validate_authored_inventory(rows[:-1])
    changed = deepcopy(rows)
    changed[-1]["locator"] = "A.10.99"
    with pytest.raises(ValueError, match="population"):
        iso.validate_authored_inventory(changed)
    changed = deepcopy(rows)
    changed[-1]["guidance_locator"] = "B.10.99"
    with pytest.raises(ValueError, match="guidance"):
        iso.validate_authored_inventory(changed)


def test_sources_available_without_fake_reviews(native):
    c, a = iso.iso_inputs(native, ["ISO27001", "ISO42001"])
    sources = [s for s in c.sources if s.id.startswith("SOURCE-ISO")]
    assert len(sources) == 3 and all(s.access == "AVAILABLE" and s.review is None for s in sources)
    assert not a.evidence and not a.tests and not a.disclosures
    assert all(i.state == "PROPOSED" and i.review is None for i in a.implementations)
    assert all(not f.inventory_complete for f in c.frameworks)
    assert plan(c, a, native)["summary"] == {"UNRESOLVED": 1035}


def test_independent_framework_selection_and_context(native):
    for fid, total in [("ISO27001", 822), ("ISO42001", 660)]:
        c, a = iso.iso_inputs(native, [fid])
        p = plan(c, a, native)
        assert [t.framework_id for t in a.scope.targets] == [fid]
        assert p["summary"] == {"UNRESOLVED": total}
        assert {r["framework_id"] for r in p["rows"]} == {"SOC2", "HIPAA", fid}
    c, a = iso.iso_inputs(native, ["ISO27001", "ISO42001", "C5"])
    assert plan(c, a, native)["summary"] == {"UNRESOLVED": 2910}
    amendment = next(r for r in c.requirements if r.id == "ISO27001:AMD1-4.1-4.2")
    assert {a.id for a in amendment.attributes} == {"RELEVANCE", "PARTY_NOTE"}
    assert amendment.source_id == "SOURCE-ISO27001-AMD1"


def test_guidance_and_soa_remain_separate_from_automatic_coverage(native):
    c, a = iso.iso_inputs(native, ["ISO42001"])
    work = iso.extension_work(c, a, native)
    annex = [r for r in work["rows"] if r["category"] == "ANNEX_A"]
    assert len(annex) == 114 and len(work["statement_of_applicability"]) == 114
    assert all("IMPLEMENTATION_GUIDANCE" in r["unmapped_attribute_ids"] for r in annex)
    assert all(
        r["necessity"] == "UNRESOLVED" and not r["exclusion_justification"]
        for r in work["statement_of_applicability"]
    )
    assert all(r["guidance_locator"].startswith("B.") for r in annex)


def test_baseline_reuse_and_additional_native_work_are_distinct(native):
    c, a = iso.iso_inputs(native, ["ISO27001", "ISO42001"])
    work = iso.extension_work(c, a, native)
    backup = next(r for r in work["rows"] if r["requirement_id"] == "ISO27001:A.8.13")
    assert backup["candidate_baseline_controls"] == ["SH-BCM-002"]
    ai = next(r for r in work["rows"] if r["requirement_id"] == "ISO42001:A.6.2.4")
    assert (
        ai["additional_native_candidates"] == ["SH-AIM-002"]
        and not ai["candidate_baseline_controls"]
    )
    assert len(work["additional_native_control_ids"]) == 22
    assert all(r["review"] is None for r in work["rows"])


def test_invalid_selection_fails(native):
    for targets in [[], ["ISO27001", "ISO27001"], ["UNKNOWN"]]:
        with pytest.raises(ValueError, match="distinct supported"):
            iso.iso_inputs(native, targets)


def test_management_system_cannot_be_dropped(native):
    c, a = iso.iso_inputs(native, ["ISO27001"])
    raw = data(a)
    raw["scope"]["targets"][0]["categories"] = ["ANNEX_A"]
    with pytest.raises(ValueError, match="mandatory categories"):
        plan(c, Assessment.model_validate(raw), native)


def test_bundle_reperformance_rejects_resealed_authored_tamper(tmp_path, monkeypatch, native):
    # Public synthetic source substitutes exercise bundle mechanics only, never production ingestion.
    original = iso.iso_inputs

    def synthetic(native, targets):
        c, a = original(native, targets)
        raw = data(c)
        for s in raw["sources"]:
            s["access"] = "SYNTHETIC"
        c = Catalog.model_validate(raw)
        a = Assessment.model_validate(dict(data(a), catalog_digest=digest(data(c))))
        return c, a

    monkeypatch.setattr(iso, "iso_inputs", synthetic)
    monkeypatch.setattr(iso, "validate_source_inventory", lambda c, p: None)
    out = tmp_path / "bundle"
    iso.build_iso(out, native, tmp_path, ["ISO27001"])
    assert iso.verify_iso(out, native, tmp_path)["verified"]
    path = out / "DELTA_ACTIONS.csv"
    path.write_text(path.read_text() + "tampered\n")
    manifest = iso.read_json(out / "ISO_MANIFEST.json")
    manifest["files"] = iso.members(out)
    iso.write_json(out / "ISO_MANIFEST.json", manifest)
    with pytest.raises(ValueError, match="re-performance"):
        iso.verify_iso(out, native, tmp_path)
