"""Security and branch-isolation checks for candidate registry routing."""

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from enterprise.audit_suite.fictional_2027_candidate_registry import (
    BASE,
    CandidateRegistryError,
    _sha,
    _source_component,
)


def test_candidate_source_routes_exact_branch_and_rejects_aliasing(tmp_path: Path) -> None:
    source = SimpleNamespace(
        folder="mock-source", run="run-v1", key="mock", review_sha256="review-pin"
    )
    run = tmp_path / BASE / source.folder / source.run
    run.mkdir(parents=True, mode=0o700)
    run.chmod(0o700)
    db_path = run / "company.sqlite3"
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE systems(company TEXT, branch TEXT, system TEXT)")
        db.execute("CREATE TABLE versions(company TEXT, branch TEXT)")
        for branch in ("CLEAN-NATIVE", "MESSY-NATIVE"):
            db.execute("INSERT INTO systems VALUES(?,?,?)", ("REFERENCE", branch, "source_events"))
            db.execute("INSERT INTO versions VALUES(?,?)", ("REFERENCE", branch))
    db_path.chmod(0o600)
    receipt_path = run / "RECEIPT.json"
    receipt_path.write_text(
        json.dumps({"branches": {"CLEAN": "CLEAN-NATIVE", "MESSY": "MESSY-NATIVE"}})
    )
    receipt_path.chmod(0o600)
    before = (_sha(db_path), _sha(receipt_path))

    clean, _ = _source_component(tmp_path, source, "CLEAN")
    messy, _ = _source_component(tmp_path, source, "MESSY")
    assert clean["branch"] == "CLEAN-NATIVE"
    assert messy["branch"] == "MESSY-NATIVE"
    assert clean["root"] == messy["root"]
    assert clean["systems"] == messy["systems"] == ["source_events"]
    assert (_sha(db_path), _sha(receipt_path)) == before

    receipt_path.write_text(
        json.dumps({"branches": {"CLEAN": "CLEAN-NATIVE", "MESSY": "CLEAN-NATIVE"}})
    )
    with pytest.raises(CandidateRegistryError, match="Distinct fictional"):
        _source_component(tmp_path, source, "CLEAN")

    receipt_path.write_text(
        json.dumps({"branches": {"CLEAN": "CLEAN-NATIVE", "MESSY": "MESSY-NATIVE"}})
    )
    Path(str(db_path) + "-wal").touch(mode=0o600)
    with pytest.raises(CandidateRegistryError, match="sidecar"):
        _source_component(tmp_path, source, "CLEAN")
