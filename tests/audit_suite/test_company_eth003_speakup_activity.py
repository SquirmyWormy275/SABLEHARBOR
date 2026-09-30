"""One payload-free speak-up marker remains distinct from a real case or audit."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from enterprise.audit_suite.company_eth003_speakup_activity import (
    BRANCHES,
    CASE,
    EXCEPTION,
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


def test_exact_routing_and_no_real_case_or_task_credit(tmp_path):
    destination = _source(tmp_path)
    report = verify(destination, repository=REPOSITORY, private_repository=PRIVATE)
    assert report["native_count"] == len(report["native_originals"]) == 14
    assert report["branch_counts"] == {"CLEAN": 6, "MESSY": 8}
    assert {side: len(rows) for side, rows in report["route_disposition"].items()} == {
        "A": 5,
        "B": 5,
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
    assert (BRANCHES["CLEAN"], "MISROUTE") not in bodies
    assert (
        bodies[(BRANCHES["CLEAN"], "RESTRICTED-ROUTE")]["case_existence_sent_to_implicated_line"]
        is False
    )
    messy = BRANCHES["MESSY"]
    assert bodies[(messy, "MISROUTE")]["case_existence_sent_to_implicated_line"] is True
    assert bodies[(messy, "RESTRICTED-CORRECTION")]["prior_misroute_erased"] is False
    assert bodies[(messy, "FINAL")]["open_exception_ids"] == [EXCEPTION]
    assert all(
        event == available
        and event.startswith("2027-")
        and imported.startswith("2026-")
        and body["case_id"] == CASE
        and body["reporter_identity"] is None
        and body["report_payload"] is None
        and body["real_report_or_allegation"] is False
        and body["actual_retaliation"] is False
        and body["sanction_or_performance_decision"] is False
        for _branch, _record, content, event, available, imported in rows
        for body in (json.loads(content),)
    )
    assert report["source_complete"] is False
    assert report["audit_task_credit"] is False


def test_sidecar_is_rejected(tmp_path):
    destination = _source(tmp_path)
    sidecar = destination / "company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed source")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="sidecar"):
        verify(destination, repository=REPOSITORY, private_repository=PRIVATE)


def test_resealed_credit_claim_is_rejected(tmp_path):
    destination = _source(tmp_path)
    source = destination / "SOURCE_RECEIPT.json"
    data = json.loads(source.read_text())
    data["audit_task_credit"] = True
    source.write_text(json.dumps(data, sort_keys=True))
    source.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="manifest differs"):
        verify(destination, repository=REPOSITORY, private_repository=PRIVATE)


def test_existing_source_cannot_be_overwritten(tmp_path):
    destination = _source(tmp_path)
    initial = (destination / "SOURCE_RECEIPT.json").read_bytes()
    with pytest.raises(CompanyStoreError, match="New private speak-up destination"):
        create(destination, repository=REPOSITORY, private_repository=PRIVATE)
    assert (destination / "SOURCE_RECEIPT.json").read_bytes() == initial
