"""Selected native source snapshot must retain lineage and fail on source drift."""

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from enterprise.audit_suite import rec003_lineage_gap as rec003
from enterprise.audit_suite import rec003_native_snapshot_candidate as candidate
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError


def _source(root: Path, side: str) -> tuple[Path, dict]:
    source = root / "dq/run-v1" / side.lower()
    source.mkdir(parents=True, mode=0o700)
    for parent in (root / "dq", root / "dq/run-v1", source):
        parent.chmod(0o700)
    store = CompanyStore(source)
    branch = f"local-data-quality-{side.lower()}"
    for system in candidate.SYSTEMS:
        store.register_system("SABLEHARBOR", branch, system, "LOCAL-OWNER")
    for index in range(11):
        store.append_version(
            "SABLEHARBOR",
            branch,
            candidate.SYSTEMS[index % 6],
            f"R{index}",
            expected_version=0,
            command_id=f"SOURCE-{index}",
            event_at="2027-01-02T00:00:00+00:00",
            available_at="2027-01-02T00:00:00+00:00",
            content=json.dumps({"row": index}).encode(),
            provenance={"source_reference": "nonpersonal synthetic fixture"},
        )
    db_path = source / "company.sqlite3"
    with sqlite3.connect(db_path) as db:
        db.executemany(
            "INSERT INTO grants VALUES(?,?,?,?,?,?)",
            [(f"P{n}", "OLD-AUDIT", "SABLEHARBOR", branch, "quality_raw", 1) for n in range(12)],
        )
        db.executemany(
            "INSERT INTO collections VALUES(?,?,?)",
            [(f"OLD-{n}", "digest", "{}") for n in range(22)],
        )
        db.executemany(
            "INSERT INTO access_events(principal,engagement,company,branch,system,active,"
            "recorded_at) "
            "VALUES(?,?,?,?,?,?,?)",
            [
                (
                    "OLD",
                    "OLD-AUDIT",
                    "SABLEHARBOR",
                    branch,
                    "quality_raw",
                    1,
                    "2026-09-29T00:00:00+00:00",
                )
                for _ in range(25)
            ],
        )
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT company,branch,system,record,version,sha256,event_at,available_at,imported_at "
            "FROM versions ORDER BY system,record,version"
        ).fetchall()
    packet = {
        "branch": branch,
        "native_original_refs": [{name: row[name] for name in candidate.FIELDS} for row in rows],
        "audit_journal_counts_excluded_from_company_lineage": candidate.JOURNALS,
    }
    return db_path, packet


def test_candidate_copies_exact_rebased_source_and_fails_on_original_drift(
    tmp_path: Path, monkeypatch
) -> None:
    tmp_path.chmod(0o700)
    paths = {}
    branches = {}
    for side in "AB":
        paths[side], branches[side] = _source(tmp_path, side)
    monkeypatch.setattr(rec003, "DQ", "dq")
    monkeypatch.setattr(
        rec003, "EXPECTED_DB", {side.lower(): candidate._sha(path) for side, path in paths.items()}
    )
    monkeypatch.setattr(candidate, "_lineage", lambda *_: {"branches": branches})
    # pytest's /tmp is not Btrfs and cannot provide unprivileged FIEMAP here.
    monkeypatch.setattr(candidate, "_no_shared_extents", lambda _path: None)
    destination = tmp_path / "candidate"
    result = candidate.create(destination, repository=tmp_path, private_repository=tmp_path)
    assert result["source_original_count"] == 22
    assert result["source_complete"] is result["audit_task_credit"] is False
    for side in "AB":
        assert (
            result["sides"][side]["inherited_audit_journals_excluded_from_company_lineage"]
            == candidate.JOURNALS
        )
        assert paths[side].stat().st_ino != (destination / side / "company.sqlite3").stat().st_ino
    assert candidate.verify(destination, repository=tmp_path, private_repository=tmp_path) == result
    with sqlite3.connect(paths["A"]) as db:
        db.execute(
            "INSERT INTO access_events(principal,engagement,company,branch,system,active,"
            "recorded_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (
                "LATE",
                "OLD-AUDIT",
                "SABLEHARBOR",
                "local-data-quality-a",
                "quality_raw",
                1,
                "2026-09-30T00:00:00+00:00",
            ),
        )
    with pytest.raises(CompanyStoreError, match="source hash differs"):
        candidate.verify(destination, repository=tmp_path, private_repository=tmp_path)


def test_shared_or_unavailable_extent_inspection_fails_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        candidate.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            stdout="ext: flags:\n  0: 0..1: shared\n1 extents found\n"
        ),
    )
    with pytest.raises(CompanyStoreError, match="shared or uninspectable"):
        candidate._no_shared_extents(tmp_path / "copy.sqlite3")
    monkeypatch.setattr(
        candidate.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(stdout="unavailable")
    )
    with pytest.raises(CompanyStoreError, match="shared or uninspectable"):
        candidate._no_shared_extents(tmp_path / "copy.sqlite3")
