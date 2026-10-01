"""Reviewed LEG/DAT selected collection extends the exact V17 boundary."""

from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_collection_probe_v18 as probe
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_candidate_registry_v18 import candidate_profiles

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
ZERO = {"grants": 0, "collections": 0, "access_events": 0}


@pytest.fixture(scope="module")
def profiles():
    _, selected = candidate_profiles(REPOSITORY, PRIVATE)
    return selected


def test_reviewed_v17_prefix_and_leg_dat_routes(profiles):
    prior = probe._reviewed_v17_collector(REPOSITORY, PRIVATE)
    assert len(prior["sides"]["A"]["collections"]) == 40
    for side, branches in (
        ("A", ("LEGOV-CLEAN", "DAT002-RIGHTS-CLEAN")),
        ("B", ("LEGOV-MESSY", "DAT002-RIGHTS-MESSY")),
    ):
        rows = probe._component_rows(profiles[side])
        assert len(rows) == 42
        assert [item[0] for item in rows[-2:]] == ["scenario-legprovision", "scenario-dat002rights"]
        for (_, pin, component), branch in zip(rows[-2:], branches, strict=True):
            assert pin["physical_branch"] == component["branch"] == branch
            assert pin["system_count"] == len(component["systems"])
            assert pin["inherited_audit_journals"] == ZERO
        changed = dict(profiles[side])
        changed["source_pins"] = [dict(item) for item in profiles[side]["source_pins"]]
        changed["source_pins"][-1]["database_sha256"] = "0" * 64
        with pytest.raises(CandidateRegistryError, match="LEG/DAT selected source route differs"):
            probe._component_rows(changed)


def test_exact_selected_terminals_and_open_limits(profiles):
    for side, messy in (("A", False), ("B", True)):
        for name, _, component in probe._component_rows(profiles[side])[-2:]:
            origin = Path(component["root"]) / "company.sqlite3"
            ref, _ = probe._native(origin, component)
            if name == "scenario-legprovision":
                selected = probe._leg_provision_final(origin, ref)
                assert ref["record"] == "LEG001-PROVISION-OVERLAY-01"
                assert selected["unresolved_qualified_review_count"] == 18
                assert len(selected["open_historical_exception_ids"]) == (2 if messy else 0)
                assert selected["2027_primary_text_rechecked"] is False
                with pytest.raises(CandidateRegistryError, match="exact LEG provision"):
                    probe._leg_provision_final(origin, dict(ref, record="PROVISION-01"))
            else:
                selected = probe._dat_rights_final(origin, ref)
                assert ref["record"] == "RECON-01"
                assert selected["case_status"] == "HELD_OPEN"
                assert len(selected["open_scope_exception_ids"]) == int(messy)
                assert selected["actual_rights_response_or_disclosure"] is False
                with pytest.raises(CandidateRegistryError, match="exact DAT rights"):
                    probe._dat_rights_final(origin, dict(ref, record="EXC-01"))
            assert selected["audit_task_credit"] is False


def test_v18_review_byte_and_verdict_fail_closed(monkeypatch):
    monkeypatch.setattr(probe, "REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V18 package hash differs"):
        probe._reviewed_v18(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    original = probe._json

    def altered(path: Path):
        value = original(path)
        if path.name == "REVIEW.json" and "company-source-portfolio-v18" in str(path):
            return {**value, "verdict": "NOT_REVIEWED"}
        return value

    monkeypatch.setattr(probe, "_json", altered)
    with pytest.raises(CandidateRegistryError, match="V18 verdict differs"):
        probe._reviewed_v18(REPOSITORY, PRIVATE)


def test_v17_collector_byte_and_verdict_fail_closed(monkeypatch):
    monkeypatch.setattr(probe, "V17_COLLECTOR_REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V17 collector byte pin differs"):
        probe._reviewed_v17_collector(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    original = probe._json

    def altered(path: Path):
        value = original(path)
        if path.name == "REVIEW.json" and "company-collection-probe-v17" in str(path):
            return {**value, "verdict": "NOT_REVIEWED"}
        return value

    monkeypatch.setattr(probe, "_json", altered)
    with pytest.raises(CandidateRegistryError, match="V17 collector verdict differs"):
        probe._reviewed_v17_collector(REPOSITORY, PRIVATE)


def test_semantic_prefix_covers_v17_selected_cases():
    assert set(probe._semantic_prefix_keys()) >= {
        "native_identity",
        "inherited_journal_sha256",
        "eng005_operating_selected_case",
        "gov_oversight_selected_case",
        "prd_concern_selected_case",
    }
