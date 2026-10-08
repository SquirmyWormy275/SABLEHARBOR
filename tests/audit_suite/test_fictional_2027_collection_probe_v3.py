"""Fail-closed selected-source and disposable collection checks."""

from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.fictional_2027_candidate_registry import CandidateRegistryError
from enterprise.audit_suite.fictional_2027_collection_probe_v3 import (
    ENGAGEMENT,
    PRINCIPAL,
    _component_rows,
    _journal,
    _native,
    _ordinary_copy,
)


def _source(tmp_path: Path) -> tuple[Path, dict]:
    tmp_path.chmod(0o700)
    source = tmp_path / "original"
    source.mkdir(mode=0o700)
    store = CompanyStore(source)
    store.register_system("FICTION", "CLEAN", "events", "OWNER")
    store.append_version(
        "FICTION",
        "CLEAN",
        "events",
        "R1",
        expected_version=0,
        command_id="SOURCE-1",
        event_at="2027-01-02T00:00:00+00:00",
        available_at="2027-01-03T00:00:00+00:00",
        content=b"synthetic original",
        provenance={"source_reference": "selected synthetic test"},
    )
    component = {
        "company": "FICTION",
        "branch": "CLEAN",
        "systems": ["events"],
        "namespace": "F27TEST",
        "root": str(source),
    }
    return source / "company.sqlite3", component


def test_native_selected_original_and_sidecar_gate(tmp_path: Path) -> None:
    db_path, component = _source(tmp_path)
    ref, digest = _native(db_path, component)
    assert (ref["company"], ref["branch"], ref["record"], ref["version"]) == (
        "FICTION",
        "CLEAN",
        "R1",
        1,
    )
    assert len(digest) == 64
    sidecar = Path(str(db_path) + "-wal")
    sidecar.write_bytes(b"uncheckpointed")
    sidecar.chmod(0o600)
    with pytest.raises(CandidateRegistryError, match="sidecar"):
        _native(db_path, component)


def test_disposable_collection_journal_requires_exact_source(tmp_path: Path) -> None:
    db_path, component = _source(tmp_path)
    ref, business = _native(db_path, component)
    clone = tmp_path / "clone" / "company.sqlite3"
    _ordinary_copy(db_path, clone)
    assert _native(clone, component)[1] == business
    store = CompanyStore(clone.parent)
    store.grant(PRINCIPAL, ENGAGEMENT, "FICTION", "CLEAN", "events")
    store.collect(
        PRINCIPAL,
        ENGAGEMENT,
        "FICTION",
        "CLEAN",
        "events",
        "R1",
        version=1,
        as_of="2027-12-31T23:59:59+00:00",
        command_id="COLLECT-1",
    )
    assert _journal(clone, ref)["collections"] == 1
    wrong = {**ref, "sha256": "0" * 64}
    with pytest.raises(CandidateRegistryError, match="exact scoped collection"):
        _journal(clone, wrong)
    assert _native(clone, component)[1] == business
    assert db_path.stat().st_ino != clone.stat().st_ino


def test_component_roster_requires_separate_iam_ledgers() -> None:
    pins = [{"source": f"cohort_{n}"} for n in range(20)] + [
        {"source": "iam005", "ledger": "human"},
        {"source": "iam005", "ledger": "service"},
    ]
    names = [
        "scenario-"
        + pin["source"].replace("_", "-")
        + ("-" + pin["ledger"] if "ledger" in pin else "")
        for pin in pins
    ]
    profile = {
        "source_pins": pins,
        "manifest": {
            "components": {name: {} for name in names} | {f"frozen-{n}": {} for n in range(13)}
        },
    }
    assert len(_component_rows(profile)) == 22
    profile["source_pins"][-1] = {"source": "iam005", "ledger": "human"}
    with pytest.raises(CandidateRegistryError, match="22 scenario components"):
        _component_rows(profile)
