"""ENG005 and GOV selected collection preserve reviewed V16 access semantics."""

from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_collection_probe_v17 as probe
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_candidate_registry_v17 import candidate_profiles

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
ZERO = {"grants": 0, "collections": 0, "access_events": 0}


@pytest.fixture(scope="module")
def profiles():
    _, selected = candidate_profiles(REPOSITORY, PRIVATE)
    return selected


def test_exact_v16_route_prefix_and_two_selected_source_pins(profiles):
    reviewed = probe._reviewed_v16_collector(REPOSITORY, PRIVATE)
    assert len(reviewed["sides"]["A"]["collections"]) == 38
    for side, branches in (
        ("A", ("ENG005-OPERATED-CLEAN", "GOV-OVERSIGHT-CLEAN")),
        ("B", ("ENG005-OPERATED-MESSY", "GOV-OVERSIGHT-MESSY")),
    ):
        rows = probe._component_rows(profiles[side])
        assert len(rows) == 40
        assert (
            len(
                probe.prior_probe._component_rows(
                    {
                        "source_pins": profiles[side]["source_pins"][:38],
                        "manifest": {
                            "components": {
                                key: value
                                for key, value in profiles[side]["manifest"]["components"].items()
                                if key not in ("scenario-eng005operating", "scenario-govoversight")
                            }
                        },
                    }
                )
            )
            == 38
        )
        for (name, pin, component), branch in zip(rows[-2:], branches, strict=True):
            assert name == "scenario-" + pin["source"]
            assert pin["physical_branch"] == component["branch"] == branch
            assert pin["system_count"] == len(component["systems"])
            assert pin["inherited_audit_journals"] == ZERO
        changed = dict(profiles[side])
        changed["source_pins"] = [dict(item) for item in profiles[side]["source_pins"]]
        changed["source_pins"][-1]["database_sha256"] = "0" * 64
        with pytest.raises(
            CandidateRegistryError, match="ENG005/GOV selected source route differs"
        ):
            probe._component_rows(changed)


def test_exact_new_native_terminal_and_open_limits(profiles):
    for side, messy in (("A", False), ("B", True)):
        for name, _, component in probe._component_rows(profiles[side])[-2:]:
            origin = Path(component["root"]) / "company.sqlite3"
            ref, _ = probe._native(origin, component)
            if name == "scenario-eng005operating":
                selected = probe._eng005_operating_final(origin, ref)
                assert ref["record"] == ("EXC-ENG005-EMG-01" if messy else "EMG-BLOCKED-REVIEW")
                assert selected["corporate_emergency_authority_status"] == ("NOT_EVIDENCED_OPEN")
                assert selected["messy_emergency_exception_open"] is messy
                assert selected["messy_ordinary_exception_open"] is messy
                assert selected["real_deployment"] is selected["actual_phi"] is False
                with pytest.raises(CandidateRegistryError, match="exact ENG005 selected"):
                    probe._eng005_operating_final(origin, dict(ref, record="ORD-REQUEST"))
            else:
                selected = probe._gov_oversight_final(origin, ref)
                assert ref["record"] == "RECON-01"
                assert selected["selected_cycle_open"] is True
                assert selected["messy_historical_governance_exception_open"] is messy
                assert selected["messy_historical_sec003_exception_open"] is messy
                assert selected["actual_board_meeting"] is selected["adopted_minutes"] is False
                with pytest.raises(CandidateRegistryError, match="exact GOV selected"):
                    probe._gov_oversight_final(origin, dict(ref, record="CASE-01"))
            assert selected["audit_task_credit"] is False


def test_reviewed_v17_package_byte_pin_fails_closed(monkeypatch):
    monkeypatch.setattr(probe, "REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V17 package hash differs"):
        probe._reviewed_v17(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    original = probe._json

    def altered(path: Path):
        value = original(path)
        if path.name == "REVIEW.json" and "company-source-portfolio-v17" in str(path):
            return {**value, "verdict": "NOT_REVIEWED"}
        return value

    monkeypatch.setattr(probe, "_json", altered)
    with pytest.raises(CandidateRegistryError, match="V17 verdict differs"):
        probe._reviewed_v17(REPOSITORY, PRIVATE)


def test_reviewed_v16_collector_byte_and_verdict_fail_closed(monkeypatch):
    monkeypatch.setattr(probe, "V16_COLLECTOR_REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V16 collector byte pin differs"):
        probe._reviewed_v16_collector(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    original = probe._json

    def altered(path: Path):
        value = original(path)
        if path.name == "REVIEW.json" and "company-collection-probe-v16" in str(path):
            return {**value, "verdict": "NOT_REVIEWED"}
        return value

    monkeypatch.setattr(probe, "_json", altered)
    with pytest.raises(CandidateRegistryError, match="V16 collector verdict differs"):
        probe._reviewed_v16_collector(REPOSITORY, PRIVATE)


def test_semantic_prefix_covers_prior_prd_and_emergency_cases():
    assert set(probe._semantic_prefix_keys()) >= {
        "native_identity",
        "inherited_journal_sha256",
        "emergency_selected_case",
        "prd_concern_selected_case",
        "cc52_selected_case",
        "eth001_selected_case",
    }
