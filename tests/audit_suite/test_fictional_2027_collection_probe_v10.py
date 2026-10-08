"""V10 disposable collection observes pending addressable cases without decisions."""

import tempfile
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_collection_probe_v10 as probe
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_candidate_registry_v9 import (
    candidate_profiles as prior_profiles,
)
from enterprise.audit_suite.fictional_2027_candidate_registry_v10 import candidate_profiles
from enterprise.audit_suite.fictional_2027_collection_probe_v9 import (
    _component_rows as prior_component_rows,
)
from enterprise.audit_suite.fictional_2027_collection_probe_v10 import (
    REC_BASELINE,
    _addressable_pending,
    _component_rows,
    run,
    verify,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
ZERO = {"grants": 0, "collections": 0, "access_events": 0}
ONE = {"grants": 1, "collections": 1, "access_events": 1}


def test_v10_has_exact_reviewed_v9_routes_plus_one_pending_docket_per_side():
    _, profiles = candidate_profiles(REPOSITORY, PRIVATE)
    _, v9_profiles = prior_profiles(REPOSITORY, PRIVATE)
    for side, branch in (("A", "ADDR-CLEAN"), ("B", "ADDR-MESSY")):
        rows = _component_rows(profiles[side])
        assert len(rows) == 32
        assert rows[:31] == prior_component_rows(v9_profiles[side])
        name, pin, component = rows[-1]
        assert name == "scenario-addressabledocket"
        assert pin["physical_branch"] == component["branch"] == branch
        assert pin["system_count"] == len(component["systems"]) == 2
        assert pin["inherited_audit_journals"] == ZERO
        assert sum(source == "scenario-rec003-dq" for source, _, _ in rows) == 1
        damaged = dict(profiles[side])
        damaged["source_pins"] = [dict(item) for item in damaged["source_pins"]]
        damaged["source_pins"][-1]["source_review_sha256"] = "0" * 64
        with pytest.raises(CandidateRegistryError, match="pending addressable route differs"):
            _component_rows(damaged)


def test_reviewed_main_v10_and_v9_collector_pin_drift_block_probe(monkeypatch):
    monkeypatch.setattr(probe, "REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V10 package hash differs"):
        probe._reviewed_v10(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    monkeypatch.setattr(probe, "V9_COLLECTOR_REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V9 collector byte pin differs"):
        probe._reviewed_v9_collector(REPOSITORY, PRIVATE)


def test_selected_native_record_must_remain_pending():
    _, profiles = candidate_profiles(REPOSITORY, PRIVATE)
    for side in "AB":
        _, _, component = _component_rows(profiles[side])[-1]
        origin = Path(component["root"]) / "company.sqlite3"
        ref, _ = probe._native(origin, component)
        pending = _addressable_pending(origin, ref)
        assert pending == {
            "source_locator": "164.308(a)(3)(ii)(A)",
            "docket_state": "PENDING_ENVIRONMENT_AND_QUALIFIED_LEGAL_REVIEW",
            "actual_hipaa_applicability": "UNDETERMINED",
            "environmental_decision": False,
            "implemented_safeguard": False,
        }
        changed = dict(ref, record="SPEC-02")
        with pytest.raises(CandidateRegistryError, match="exact pending addressable"):
            _addressable_pending(origin, changed)


def test_v10_disposable_copies_collect_pending_case_and_preserve_rec003_history():
    with tempfile.TemporaryDirectory(prefix=".probe-v10-test-", dir=REPOSITORY) as temp:
        destination = Path(temp) / "probe-v10"
        result = run(REPOSITORY, PRIVATE, destination)
        assert result == verify(destination, REPOSITORY, PRIVATE)
        assert (
            result["reviewed_source_count"],
            result["reviewed_native_version_count"],
            result["disposable_copy_count"],
            result["disposable_collection_count"],
        ) == (31, 710, 90, 64)
        assert result["p1_freeze"] == probe.P1_FREEZE
        for side in "AB":
            rows = result["sides"][side]["collections"]
            assert len(rows) == 32
            assert len(result["sides"][side]["frozen_copies"]) == 13
            pending = [
                row for row in rows if row["source_store_id"] == "scenario-addressabledocket"
            ]
            assert len(pending) == 1
            assert pending[0]["native_identity"]["branch"] == (
                "ADDR-CLEAN" if side == "A" else "ADDR-MESSY"
            )
            assert pending[0]["native_identity"]["record"] == "SPEC-01"
            assert pending[0]["addressable_pending_case"]["environmental_decision"] is False
            assert pending[0]["inherited_journal_counts"] == ZERO
            assert pending[0]["disposable_journal_delta"]["post_counts"] == ONE
            rec = [row for row in rows if row["source_store_id"] == "scenario-rec003-dq"]
            assert len(rec) == 1
            assert rec[0]["inherited_journal_counts"] == REC_BASELINE
            assert rec[0]["disposable_journal_delta"]["post_counts"] == {
                "grants": 13,
                "collections": 23,
                "access_events": 26,
            }
        assert result["original_company_sources_unchanged"] is True
        assert (
            result["source_complete"]
            is result["fresh_audit_pair_created"]
            is result["audit_task_credit"]
            is False
        )
