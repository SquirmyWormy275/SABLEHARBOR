"""Selected SEC001 transfer stays synthetic and preserves the V11 probe."""

import tempfile
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_collection_probe_v12 as probe
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_candidate_registry_v11 import (
    candidate_profiles as prior_profiles,
)
from enterprise.audit_suite.fictional_2027_candidate_registry_v12 import candidate_profiles
from enterprise.audit_suite.fictional_2027_collection_probe_v11 import (
    _component_rows as prior_component_rows,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
ZERO = {"grants": 0, "collections": 0, "access_events": 0}
ONE = {"grants": 1, "collections": 1, "access_events": 1}


@pytest.fixture(scope="module")
def profiles() -> dict:
    _, selected = candidate_profiles(REPOSITORY, PRIVATE)
    return selected


def test_exact_v11_route_prefix_and_sec001_final_pins(profiles: dict) -> None:
    _, prior = prior_profiles(REPOSITORY, PRIVATE)
    for side, branch in (("A", "SEC001-XFER-CLEAN"), ("B", "SEC001-XFER-MESSY")):
        rows = probe._component_rows(profiles[side])
        assert len(rows) == 34
        assert rows[:33] == prior_component_rows(prior[side])
        source_id, pin, component = rows[-1]
        assert source_id == "scenario-sec001transfer"
        assert pin["physical_branch"] == component["branch"] == branch
        assert pin["system_count"] == len(component["systems"]) == 5
        assert pin["inherited_audit_journals"] == ZERO
        changed = dict(profiles[side])
        changed["source_pins"] = [dict(item) for item in profiles[side]["source_pins"]]
        changed["source_pins"][-1]["database_sha256"] = "0" * 64
        with pytest.raises(CandidateRegistryError, match="SEC001 transfer source route differs"):
            probe._component_rows(changed)


def test_reviewed_v12_and_v11_collector_pins_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V12 package hash differs"):
        probe._reviewed_v12(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    monkeypatch.setattr(probe, "V11_COLLECTOR_REVIEW_SHA256", "0" * 64)
    with pytest.raises(CandidateRegistryError, match="V11 collector byte pin differs"):
        probe._reviewed_v11_collector(REPOSITORY, PRIVATE)


def test_selected_final_is_fictional_and_messy_exception_remains_open(profiles: dict) -> None:
    for side, messy in (("A", False), ("B", True)):
        _, _, component = probe._component_rows(profiles[side])[-1]
        origin = Path(component["root"]) / "company.sqlite3"
        ref, _ = probe._native(origin, component)
        assert (ref["system"], ref["record"], ref["version"]) == (
            "exception_register",
            "FINAL",
            1,
        )
        selected = probe._sec001_final(origin, ref)
        assert selected["selected_fixture_reconciled"] is True
        assert selected["open_exception_ids"] == (
            ["SIM-SEC001-FALSE-CLOSE-EXC-001"] if messy else []
        )
        for key in (
            "actual_network_transfer",
            "actual_customer_or_phi_data",
            "deployed_channel_or_endpoint",
            "approved_enterprise_transfer_standard",
            "authored_clause_satisfied",
            "audit_task_credit",
        ):
            assert selected[key] is False
        with pytest.raises(CandidateRegistryError, match="exact SEC001 final"):
            probe._sec001_final(origin, dict(ref, record="FALSE-CLOSE"))


def test_v12_disposable_collection_preserves_originals_and_rec003_history() -> None:
    with tempfile.TemporaryDirectory(prefix=".probe-v12-test-", dir=REPOSITORY) as temporary:
        destination = Path(temporary) / "probe-v12"
        report = probe.run(REPOSITORY, PRIVATE, destination)
        assert report == probe.verify(destination, REPOSITORY, PRIVATE)
        assert (
            report["reviewed_source_count"],
            report["reviewed_native_version_count"],
            report["disposable_copy_count"],
            report["disposable_collection_count"],
        ) == (33, 755, 94, 68)
        assert report["p1_freeze"] == probe.P1_FREEZE
        for side, messy in (("A", False), ("B", True)):
            rows = report["sides"][side]["collections"]
            assert len(rows) == 34
            assert len(report["sides"][side]["frozen_copies"]) == 13
            transfer = rows[-1]
            assert transfer["source_store_id"] == "scenario-sec001transfer"
            assert transfer["native_identity"]["record"] == "FINAL"
            assert transfer["sec001_selected_case"]["open_exception_ids"] == (
                ["SIM-SEC001-FALSE-CLOSE-EXC-001"] if messy else []
            )
            assert transfer["inherited_journal_counts"] == ZERO
            assert transfer["disposable_journal_delta"]["post_counts"] == ONE
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
