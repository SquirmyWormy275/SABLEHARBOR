"""Neutral read-only inventory tests; no private company or scenario fixtures."""

import json
import sqlite3

import pytest

from tools.audit_suite.company_inventory import inventory, main, read_snapshot


def fixture(tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    state = {
        "id": "E1",
        "revision": 3,
        "scope": {"period_start": "2027-01-01"},
        "controls": [{"id": "C1", "procedure": "Inspect a dated record", "owner_ids": ["P1"]}],
        "tasks": [{"id": "T1", "control_id": "C1", "kind": "TOE", "status": "NOT_STARTED"}],
        "requests": [],
        "artifacts": [],
    }
    with sqlite3.connect(store / "engagements.sqlite3") as db:
        db.execute("CREATE TABLE engagements(id TEXT, revision INTEGER, state TEXT)")
        db.execute("INSERT INTO engagements VALUES(?,?,?)", ("E1", 3, json.dumps(state)))
    return store


def test_census_preserves_state_and_reports_missing_source_unit(tmp_path):
    store = fixture(tmp_path)
    original = (store / "engagements.sqlite3").read_bytes()
    result = inventory(tmp_path, store, "E1")
    assert result["counts"]["scoped_controls"] == result["counts"]["audit_tasks"] == 1
    assert any(g["gap"] == "FROZEN_SUPPORT_UNIT_ABSENT" for g in result["gaps"])
    assert result["controls"][0]["professional_sufficiency"] == "NOT_ASSESSED"
    assert (store / "engagements.sqlite3").read_bytes() == original


def test_snapshot_identity_and_missing_engagement_fail_closed(tmp_path):
    store = fixture(tmp_path)
    with pytest.raises(ValueError, match="not found"):
        read_snapshot(store, "MISSING")
    with sqlite3.connect(store / "engagements.sqlite3") as db:
        db.execute("UPDATE engagements SET revision=4")
    with pytest.raises(ValueError, match="mismatch"):
        read_snapshot(store, "E1")


def test_output_private_and_never_overwritten(tmp_path, capsys):
    store = fixture(tmp_path)
    output = tmp_path / "private" / "inventory.json"
    argv = [
        "--repository",
        str(tmp_path),
        "--store",
        str(store),
        "--engagement",
        "E1",
        "--output",
        str(output),
    ]
    assert main(argv) == 0
    assert output.stat().st_mode & 0o777 == 0o600
    assert output.parent.stat().st_mode & 0o777 == 0o700
    assert "controls" not in json.loads(capsys.readouterr().out)
    with pytest.raises(ValueError, match="must be new"):
        main(argv)
