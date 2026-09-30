"""A selected nonpersonal requirement gate is not candidate screening evidence."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from enterprise.audit_suite.company_ppl002_screening_gate import (
    BRANCHES,
    EXCEPTION,
    REQUISITION,
    create,
    verify,
)
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def _source(tmp_path: Path) -> Path:
    tmp_path.chmod(0o700)
    destination = tmp_path / "selected-source"
    create(destination, repository=REPOSITORY, private_repository=PRIVATE)
    return destination


def test_clean_block_and_messy_open_denied_nomination(tmp_path):
    destination = _source(tmp_path)
    report = verify(destination, repository=REPOSITORY, private_repository=PRIVATE)
    assert report["native_count"] == len(report["native_originals"]) == 12
    assert report["branch_counts"] == {"CLEAN": 5, "MESSY": 7}
    assert {side: len(rows) for side, rows in report["route_disposition"].items()} == {
        "A": 3,
        "B": 3,
    }
    assert all(
        row["status"] == "NOT_STARTED"
        and row["conclusion"] == "NOT_RUN"
        and row["task_credit"] is False
        for routes in report["route_disposition"].values()
        for row in routes
    )
    with closing(sqlite3.connect(destination / "company.sqlite3")) as db:
        rows = db.execute(
            "SELECT branch,record,content,event_at,available_at,imported_at "
            "FROM versions ORDER BY rowid"
        ).fetchall()
        for table in ("grants", "collections", "access_events"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    bodies = {(branch, record): json.loads(content) for branch, record, content, *_ in rows}
    assert (BRANCHES["CLEAN"], "INVALID-NOMINATION") not in bodies
    assert bodies[(BRANCHES["CLEAN"], "GATE")]["decision"].startswith("BLOCKED_")
    messy = BRANCHES["MESSY"]
    assert bodies[(messy, "INVALID-NOMINATION")]["external_effect"] is False
    assert bodies[(messy, "DENIAL")]["decision"].startswith("INVALID_LOCAL_NOMINATION_DENIED")
    assert bodies[(messy, "CORRECTION")]["prior_invalid_nomination_erased"] is False
    assert bodies[(messy, "FINAL")]["open_exception_ids"] == [EXCEPTION]
    assert all(
        event == available
        and event.startswith("2027-")
        and imported.startswith("2026-")
        and body["requisition_id"] == REQUISITION
        and body["candidate_id"] is None
        and body["background_or_qualification_result"] is None
        and body["actual_assignment_or_access"] is False
        for _branch, _record, content, event, available, imported in rows
        for body in (json.loads(content),)
    )
    assert report["source_complete"] is False
    assert report["audit_task_credit"] is False


def test_sidecar_rejected(tmp_path):
    destination = _source(tmp_path)
    sidecar = destination / "company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed source")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="sidecar"):
        verify(destination, repository=REPOSITORY, private_repository=PRIVATE)


def test_credited_receipt_rejected(tmp_path):
    destination = _source(tmp_path)
    source = destination / "SOURCE_RECEIPT.json"
    value = json.loads(source.read_text())
    value["audit_task_credit"] = True
    source.write_text(json.dumps(value, sort_keys=True))
    source.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="manifest differs"):
        verify(destination, repository=REPOSITORY, private_repository=PRIVATE)


def test_existing_destination_not_overwritten(tmp_path):
    destination = _source(tmp_path)
    source = destination / "SOURCE_RECEIPT.json"
    before = source.read_bytes()
    with pytest.raises(CompanyStoreError, match="New private screening destination"):
        create(destination, repository=REPOSITORY, private_repository=PRIVATE)
    assert source.read_bytes() == before
