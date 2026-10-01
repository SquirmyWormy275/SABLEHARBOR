"""Selected ETH001 final collection stays fictional and preserves the V10 probe."""

import tempfile
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_collection_probe_v11 as probe
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_candidate_registry_v10 import (
    candidate_profiles as prior_profiles,
)
from enterprise.audit_suite.fictional_2027_candidate_registry_v11 import candidate_profiles
from enterprise.audit_suite.fictional_2027_collection_probe_v10 import (
    _component_rows as prior_component_rows,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
ZERO = {"grants": 0, "collections": 0, "access_events": 0}
ONE = {"grants": 1, "collections": 1, "access_events": 1}


@pytest.fixture(scope="module")
def profiles() -> dict:
    _, selected = candidate_profiles(REPOSITORY, PRIVATE)
    return selected


def test_exact_v10_route_prefix_and_eth001_final_pins(profiles: dict) -> None:
    _, prior = prior_profiles(REPOSITORY, PRIVATE)
    for side, branch in (("A", "ETH001-CLEAN"), ("B", "ETH001-MESSY")):
        rows = probe._component_rows(profiles[side])
        assert len(rows) == 33
        assert rows[:32] == prior_component_rows(prior[side])
        source_id, pin, component = rows[-1]
        assert source_id == "scenario-eth001conduct"
        assert pin["physical_branch"] == component["branch"] == branch
        assert pin["system_count"] == len(component["systems"]) == 4
        assert pin["inherited_audit_journals"] == ZERO
        changed = dict(profiles[side])
        changed["source_pins"] = [dict(item) for item in profiles[side]["source_pins"]]
        changed["source_pins"][-1]["database_sha256"] = "0" * 64
        with pytest.raises(CandidateRegistryError, match="ETH001 source route differs"):
            probe._component_rows(changed)


def test_reviewed_v11_and_v10_collector_pins_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V11 package hash differs"):
        probe._reviewed_v11(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    monkeypatch.setattr(probe, "V10_COLLECTOR_REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V10 collector byte pin differs"):
        probe._reviewed_v10_collector(REPOSITORY, PRIVATE)


def test_selected_final_is_fictional_and_messy_exception_remains_open(profiles: dict) -> None:
    for side, messy in (("A", False), ("B", True)):
        _, _, component = probe._component_rows(profiles[side])[-1]
        origin = Path(component["root"]) / "company.sqlite3"
        ref, _ = probe._native(origin, component)
        assert (ref["system"], ref["record"], ref["version"]) == (
            "conduct_reconciliation",
            "FINAL",
            1,
        )
        selected = probe._eth001_final(origin, ref)
        assert selected["selected_acknowledgment_count"] == 2
        assert selected["selected_late_count"] == int(messy)
        assert selected["open_exception_ids"] == (
            ["LOCAL-ETH001-FALSE-CLEAN-EXC-001"] if messy else []
        )
        for key in (
            "real_enterprise_code_approved",
            "workforce_population_complete",
            "actual_employee_action_or_signature",
            "sanctions_or_performance_review_conclusion",
            "audit_task_credit",
        ):
            assert selected[key] is False
        with pytest.raises(CandidateRegistryError, match="exact ETH001 final"):
            probe._eth001_final(origin, dict(ref, record="FALSE-CLEAN"))


def test_v11_disposable_collection_preserves_originals_and_rec003_history() -> None:
    with tempfile.TemporaryDirectory(prefix=".probe-v11-test-", dir=REPOSITORY) as temporary:
        destination = Path(temporary) / "probe-v11"
        report = probe.run(REPOSITORY, PRIVATE, destination)
        assert report == probe.verify(destination, REPOSITORY, PRIVATE)
        assert (
            report["reviewed_source_count"],
            report["reviewed_native_version_count"],
            report["disposable_copy_count"],
            report["disposable_collection_count"],
        ) == (32, 729, 92, 66)
        assert report["p1_freeze"] == probe.P1_FREEZE
        for side, messy in (("A", False), ("B", True)):
            rows = report["sides"][side]["collections"]
            assert len(rows) == 33
            assert len(report["sides"][side]["frozen_copies"]) == 13
            eth = rows[-1]
            assert eth["source_store_id"] == "scenario-eth001conduct"
            assert eth["native_identity"]["record"] == "FINAL"
            assert eth["eth001_selected_case"]["selected_late_count"] == int(messy)
            assert eth["inherited_journal_counts"] == ZERO
            assert eth["disposable_journal_delta"]["post_counts"] == ONE
            rec = next(row for row in rows if row["source_store_id"] == "scenario-rec003-dq")
            assert rec["inherited_journal_counts"] == probe.REC_BASELINE
            assert rec["disposable_journal_delta"]["post_counts"] == {
                "grants": 13,
                "collections": 23,
                "access_events": 26,
            }
        assert report["original_company_sources_unchanged"] is True
        assert (
            report["source_complete"]
            is report["fresh_audit_pair_created"]
            is report["audit_task_credit"]
            is False
        )
