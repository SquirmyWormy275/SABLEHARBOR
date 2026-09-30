"""Selected future-fictional conflict source never becomes an audit conclusion."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from enterprise.audit_suite.company_eth004_conflict_activity import (
    BRANCHES,
    EXCEPTION,
    MATRIX,
    OPPORTUNITY,
    SIGNAL,
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


def test_selected_clean_messy_causality_and_exact_uncredited_routes(tmp_path):
    destination = _source(tmp_path)
    report = verify(destination, repository=REPOSITORY, private_repository=PRIVATE)
    receipt = json.loads((destination / "SOURCE_RECEIPT.json").read_text())
    assert report["native_count"] == len(report["native_originals"]) == 13
    assert report["branch_counts"] == {"CLEAN": 6, "MESSY": 7}
    assert receipt["route_sha256"][MATRIX]
    assert {side: len(tasks) for side, tasks in report["route_disposition"].items()} == {
        "A": 4,
        "B": 4,
    }
    assert all(
        task["current_status"] == "NOT_STARTED"
        and task["current_conclusion"] == "NOT_RUN"
        and task["task_credit"] is False
        for tasks in report["route_disposition"].values()
        for task in tasks
    )
    with closing(sqlite3.connect(destination / "company.sqlite3")) as db:
        rows = db.execute(
            "SELECT branch,record,content,event_at,available_at,imported_at "
            "FROM versions ORDER BY rowid"
        ).fetchall()
        for table in ("grants", "collections", "access_events"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    bodies = {(branch, record): json.loads(content) for branch, record, content, *_ in rows}
    assert (BRANCHES["CLEAN"], "LOCAL-RECOMMENDATION") not in bodies
    assert bodies[(BRANCHES["CLEAN"], "FINAL")]["open_exception_ids"] == []
    messy = BRANCHES["MESSY"]
    assert bodies[(messy, "INDICATOR")]["indicator_id"] == SIGNAL
    assert bodies[(messy, "LOCAL-RECOMMENDATION")]["omitted_indicator_id"] == SIGNAL
    assert bodies[(messy, "LOCAL-RECOMMENDATION")]["indicator_included"] is False
    assert bodies[(messy, "WITHDRAWAL")]["original_draft_remains_in_HISTORY"] is True
    assert bodies[(messy, "FINAL")]["open_exception_ids"] == [EXCEPTION]
    assert all(
        event == available
        and event.startswith("2027-")
        and imported.startswith("2026-")
        and body["opportunity_id"] == OPPORTUNITY
        and body["award_or_payment"] is False
        and body["actual_affiliation_or_fraud"] is False
        for branch, record, content, event, available, imported in rows
        for body in (json.loads(content),)
    )
    assert report["audit_task_credit"] is False
    assert report["actual_2027_operation"] is False


def test_sqlite_sidecar_fails_closed(tmp_path):
    destination = _source(tmp_path)
    sidecar = destination / "company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed source")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="sidecar"):
        verify(destination, repository=REPOSITORY, private_repository=PRIVATE)


def test_receipt_completion_claim_fails_closed(tmp_path):
    destination = _source(tmp_path)
    receipt = destination / "SOURCE_RECEIPT.json"
    value = json.loads(receipt.read_text())
    value["audit_task_credit"] = True
    receipt.write_text(json.dumps(value, sort_keys=True))
    receipt.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="manifest differs"):
        verify(destination, repository=REPOSITORY, private_repository=PRIVATE)


def test_existing_destination_never_overwritten(tmp_path):
    destination = _source(tmp_path)
    original = (destination / "SOURCE_RECEIPT.json").read_bytes()
    with pytest.raises(CompanyStoreError, match="New private destination"):
        create(destination, repository=REPOSITORY, private_repository=PRIVATE)
    assert (destination / "SOURCE_RECEIPT.json").read_bytes() == original
