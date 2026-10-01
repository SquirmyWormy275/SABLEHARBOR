"""V9 disposable collection reaches LEG001 records without source writes."""

import tempfile
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_collection_probe_v9 as probe
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_candidate_registry_v8 import (
    candidate_profiles as prior_profiles,
)
from enterprise.audit_suite.fictional_2027_candidate_registry_v9 import candidate_profiles
from enterprise.audit_suite.fictional_2027_collection_probe_v8 import (
    _component_rows as prior_component_rows,
)
from enterprise.audit_suite.fictional_2027_collection_probe_v9 import (
    REC_BASELINE,
    _component_rows,
    run,
    verify,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
ZERO = {"grants": 0, "collections": 0, "access_events": 0}
ONE = {"grants": 1, "collections": 1, "access_events": 1}


def test_v9_has_exact_leg001_route_per_side_and_rejects_pin_drift():
    _, profiles = candidate_profiles(REPOSITORY, PRIVATE)
    _, v8_profiles = prior_profiles(REPOSITORY, PRIVATE)
    for side, branch in (("A", "LEG-CLEAN"), ("B", "LEG-MESSY")):
        rows = _component_rows(profiles[side])
        assert len(rows) == 31
        assert rows[:30] == prior_component_rows(v8_profiles[side])
        leg = [(pin, component) for name, pin, component in rows if name == "scenario-leg001docket"]
        assert len(leg) == 1
        assert leg[0][0]["physical_branch"] == leg[0][1]["branch"] == branch
        assert leg[0][0]["system_count"] == len(leg[0][1]["systems"]) == 6
        assert leg[0][0]["inherited_audit_journals"] == ZERO
        assert sum(name == "scenario-rec003-dq" for name, _, _ in rows) == 1
        damaged = dict(profiles[side])
        damaged["source_pins"] = [dict(pin) for pin in damaged["source_pins"]]
        damaged["source_pins"][-1]["source_review_sha256"] = "0" * 64
        with pytest.raises(CandidateRegistryError, match="LEG001 source route differs"):
            _component_rows(damaged)


def test_reviewed_main_v9_pin_drift_blocks_probe_before_copy(monkeypatch):
    monkeypatch.setattr(probe, "REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="package hash differs"):
        probe._reviewed_v9(REPOSITORY, PRIVATE)


def test_v9_private_copies_collect_leg001_record_and_preserve_rec003_history():
    with tempfile.TemporaryDirectory(prefix=".probe-v9-test-", dir=REPOSITORY) as temp:
        destination = Path(temp) / "probe-v9"
        result = run(REPOSITORY, PRIVATE, destination)
        assert result == verify(destination, REPOSITORY, PRIVATE)
        assert (
            result["reviewed_source_count"],
            result["reviewed_native_version_count"],
            result["disposable_copy_count"],
            result["disposable_collection_count"],
        ) == (30, 660, 88, 62)
        for side in "AB":
            rows = result["sides"][side]["collections"]
            assert len(rows) == 31
            leg = [row for row in rows if row["source_store_id"] == "scenario-leg001docket"]
            assert len(leg) == 1
            assert leg[0]["native_identity"]["branch"] == (
                "LEG-CLEAN" if side == "A" else "LEG-MESSY"
            )
            assert leg[0]["inherited_journal_counts"] == ZERO
            assert leg[0]["disposable_journal_delta"]["post_counts"] == ONE
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
