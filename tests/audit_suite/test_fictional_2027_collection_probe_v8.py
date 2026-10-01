"""V8 disposable collection reaches physical-site records without source writes."""

import tempfile
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_collection_probe_v8 as probe
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_candidate_registry_v8 import candidate_profiles
from enterprise.audit_suite.fictional_2027_collection_probe_v8 import (
    REC_BASELINE,
    _component_rows,
    run,
    verify,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
ZERO = {"grants": 0, "collections": 0, "access_events": 0}
ONE = {"grants": 1, "collections": 1, "access_events": 1}


def test_v8_has_exact_physical_route_per_side_and_rejects_pin_drift():
    _, profiles = candidate_profiles(REPOSITORY, PRIVATE)
    for side, branch in (("A", "PHYSICAL-CLEAN"), ("B", "PHYSICAL-MESSY")):
        rows = _component_rows(profiles[side])
        assert len(rows) == 30
        phys = [
            (pin, component) for name, pin, component in rows if name == "scenario-physicalsite"
        ]
        assert len(phys) == 1
        assert phys[0][0]["physical_branch"] == phys[0][1]["branch"] == branch
        assert phys[0][0]["system_count"] == len(phys[0][1]["systems"]) == 8
        assert phys[0][0]["inherited_audit_journals"] == ZERO
        assert sum(name == "scenario-rec003-dq" for name, _, _ in rows) == 1
        damaged = dict(profiles[side])
        damaged["source_pins"] = [dict(pin) for pin in damaged["source_pins"]]
        damaged["source_pins"][-1]["source_review_sha256"] = "0" * 64
        with pytest.raises(CandidateRegistryError, match="physical-site source route differs"):
            _component_rows(damaged)


def test_reviewed_main_v8_pin_drift_blocks_probe_before_copy(monkeypatch):
    monkeypatch.setattr(probe, "REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="package hash differs"):
        probe._reviewed_v8(REPOSITORY, PRIVATE)


def test_v8_private_copies_collect_physical_record_and_preserve_rec003_history():
    with tempfile.TemporaryDirectory(prefix=".probe-v8-test-", dir=REPOSITORY) as temp:
        destination = Path(temp) / "probe-v8"
        result = run(REPOSITORY, PRIVATE, destination)
        assert result == verify(destination, REPOSITORY, PRIVATE)
        assert (
            result["reviewed_source_count"],
            result["reviewed_native_version_count"],
            result["disposable_copy_count"],
            result["disposable_collection_count"],
        ) == (29, 560, 86, 60)
        for side in "AB":
            rows = result["sides"][side]["collections"]
            assert len(rows) == 30
            phys = [row for row in rows if row["source_store_id"] == "scenario-physicalsite"]
            assert len(phys) == 1
            assert phys[0]["native_identity"]["branch"] == (
                "PHYSICAL-CLEAN" if side == "A" else "PHYSICAL-MESSY"
            )
            assert phys[0]["inherited_journal_counts"] == ZERO
            assert phys[0]["disposable_journal_delta"]["post_counts"] == ONE
            rec = [row for row in rows if row["source_store_id"] == "scenario-rec003-dq"]
            assert len(rec) == 1
            assert rec[0]["inherited_journal_counts"] == REC_BASELINE
            assert rec[0]["disposable_journal_delta"]["post_counts"] == {
                "grants": 13,
                "collections": 23,
                "access_events": 26,
            }
        assert result["original_company_sources_unchanged"] is True
        assert result["source_complete"] is result["audit_task_credit"] is False
