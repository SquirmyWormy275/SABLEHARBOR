"""V4 disposable collection must preserve REC003's inherited audit journals."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_candidate_registry_v4 import candidate_profiles
from enterprise.audit_suite.fictional_2027_collection_probe import _ordinary_copy
from enterprise.audit_suite.fictional_2027_collection_probe_v4 import (
    AS_OF,
    ENGAGEMENT,
    PRINCIPAL,
    REC_BASELINE,
    _component_rows,
    _journal,
    _journal_baseline,
    _native,
    run,
    verify,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
REC_DB = (
    PRIVATE
    / "enterprise/generated/audit-suite/company-rec003-native-snapshot-2026-09-29"
    / "main-run-v2/A/company.sqlite3"
)


def _rec_clone(tmp_path: Path) -> tuple[Path, dict]:
    tmp_path.chmod(0o700)
    target = tmp_path / "rec003" / "company.sqlite3"
    _ordinary_copy(REC_DB, target)
    component = {
        "root": str(target.parent),
        "company": "SABLEHARBOR",
        "branch": "local-data-quality-a",
        "namespace": "F27REC003DQ",
        "systems": [
            "quality_aggregate",
            "quality_definition",
            "quality_derived",
            "quality_operation",
            "quality_raw",
            "quality_reference",
        ],
    }
    return target, component


def test_rec003_historical_journals_are_preserved_and_one_delta_is_scoped(tmp_path):
    target, component = _rec_clone(tmp_path)
    ref, business = _native(target, component)
    original_rows, counts, digest = _journal_baseline(target, "scenario-rec003-dq")
    assert counts == REC_BASELINE and len(digest) == 64
    store = CompanyStore(target.parent)
    store.grant(PRINCIPAL, ENGAGEMENT, ref["company"], ref["branch"], ref["system"])
    store.collect(
        PRINCIPAL,
        ENGAGEMENT,
        ref["company"],
        ref["branch"],
        ref["system"],
        ref["record"],
        version=ref["version"],
        as_of=AS_OF,
        command_id="V4-TEST-COLLECT",
    )
    result = _journal(target, ref, original_rows)
    assert result["inherited_counts"] == REC_BASELINE
    assert result["post_counts"] == {"grants": 13, "collections": 23, "access_events": 26}
    assert _native(target, component)[1] == business
    with pytest.raises(CandidateRegistryError, match="baseline"):
        _journal_baseline(target, "scenario-rec003-dq")
    with sqlite3.connect(target) as db:
        db.execute(
            "UPDATE grants SET active=1-active WHERE principal=(SELECT principal FROM grants "
            "WHERE principal<>? LIMIT 1)",
            (PRINCIPAL,),
        )
    with pytest.raises(CandidateRegistryError, match="historical journals changed"):
        _journal(target, ref, original_rows)


def test_exact_v4_component_roster_routes_one_rec_snapshot_per_profile():
    _, profiles = candidate_profiles(REPOSITORY, PRIVATE)
    for side in "AB":
        rows = _component_rows(profiles[side])
        assert len(rows) == 25
        rec = [
            (name, pin, component) for name, pin, component in rows if name == "scenario-rec003-dq"
        ]
        assert len(rec) == 1
        assert rec[0][1]["root_locator"] == "snapshot://" + side
        assert rec[0][2]["branch"] == "local-data-quality-" + side.lower()
    damaged = dict(profiles["A"])
    damaged["source_pins"] = list(damaged["source_pins"])
    damaged["source_pins"][-1] = damaged["source_pins"][22]
    with pytest.raises(CandidateRegistryError, match="25 scenario components"):
        _component_rows(damaged)


def test_final_disposable_probe_uses_only_private_clones():
    # Keep the full FIEMAP assertion on the repository's Btrfs filesystem.
    with tempfile.TemporaryDirectory(prefix=".probe-v4-test-", dir=REPOSITORY) as temp:
        destination = Path(temp) / "probe-v4"
        result = run(REPOSITORY, PRIVATE, destination)
        assert result == verify(destination, REPOSITORY, PRIVATE)
        assert (
            result["reviewed_source_count"],
            result["reviewed_native_version_count"],
            result["disposable_collection_count"],
        ) == (24, 401, 50)
        for side in "AB":
            rows = result["sides"][side]["collections"]
            assert len(rows) == 25
            rec = [row for row in rows if row["source_store_id"] == "scenario-rec003-dq"]
            assert len(rec) == 1 and rec[0]["inherited_journal_counts"] == REC_BASELINE
            assert rec[0]["disposable_journal_delta"]["post_counts"] == {
                "grants": 13,
                "collections": 23,
                "access_events": 26,
            }
        assert result["source_complete"] is result["audit_task_credit"] is False
