"""The selected transfer trace remains fictional and cannot satisfy CC6.7."""

import json
import sqlite3
import stat
from contextlib import closing
from pathlib import Path

import pytest

from enterprise.audit_suite.company_sec001_selected_transfer import (
    BRANCHES,
    CLAUSE,
    EXCEPTION,
    PAYLOAD_SHA,
    ROUTE_LEDGER,
    TASK,
    create,
    verify,
)
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.documentary_283_route_reconciliation_v6 import _p1_inventory
from enterprise.audit_suite.operating_source_bridge import encoded, sha

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def _source(tmp_path: Path) -> Path:
    tmp_path.chmod(0o700)
    destination = tmp_path / "selected-transfer"
    create(destination, repository=REPOSITORY, private_repository=PRIVATE)
    return destination


def _repack_receipt(destination: Path, change) -> None:
    receipt_path = destination / "SOURCE_RECEIPT.json"
    receipt = json.loads(receipt_path.read_bytes())
    change(receipt)
    receipt_path.write_bytes(encoded(receipt))
    receipt_path.chmod(0o600)
    manifest_path = destination / "RUN-MANIFEST.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["source_receipt_sha256"] = sha(receipt_path.read_bytes())
    manifest_path.write_bytes(encoded(manifest))
    manifest_path.chmod(0o600)


def test_selected_transfer_history_and_limits(tmp_path):
    before_p1 = _p1_inventory(PRIVATE)
    destination = _source(tmp_path)
    receipt = verify(destination, repository=REPOSITORY, private_repository=PRIVATE)
    assert _p1_inventory(PRIVATE) == before_p1
    assert stat.S_IMODE(destination.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in destination.iterdir())
    assert receipt["task_id"] == TASK
    assert receipt["selected_authored_clause"] == CLAUSE
    assert receipt["route_sha256"][ROUTE_LEDGER]
    assert receipt["branch_counts"] == {"CLEAN": 10, "MESSY": 16}
    assert receipt["native_count"] == len(receipt["native_originals"]) == 26
    assert receipt["actor_authority"].endswith("PENDING_ACCEPTANCE")
    assert receipt["independent_approval"] is False
    assert all(
        row["remaining_test_gate"] == CLAUSE
        and row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
        and row["current_status"] == "NOT_STARTED"
        and row["current_conclusion"] == "NOT_RUN"
        and row["audit_task_credit"] is False
        for row in receipt["route_disposition"].values()
    )
    assert all(
        receipt[field] is False
        for field in (
            "actual_network_transmission",
            "actual_customer_or_phi_data",
            "actual_deployed_endpoint_or_channel",
            "enterprise_transfer_standard_approved",
            "population_complete",
            "source_complete",
            "audit_task_credit",
            "active_P1_mutated",
        )
    )
    with closing(
        sqlite3.connect(
            (destination / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
        )
    ) as db:
        rows = db.execute(
            "SELECT branch,record,content,event_at,available_at,imported_at "
            "FROM versions ORDER BY rowid"
        ).fetchall()
        assert all(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
            for table in ("grants", "collections", "access_events")
        )
    bodies = {(branch, record): json.loads(content) for branch, record, content, *_ in rows}
    clean = BRANCHES["CLEAN"]
    messy = BRANCHES["MESSY"]
    originals = {(row["branch"], row["record"]): row for row in receipt["native_originals"]}
    assert bodies[(clean, "FINAL")]["detail"]["open_exception_ids"] == []
    assert (clean, "WRONG-ENDPOINT-ATTEMPT") not in bodies
    assert bodies[(messy, "WRONG-ENDPOINT-ATTEMPT")]["detail"]["payload_sent"] is False
    assert (
        bodies[(messy, "BLOCK")]["record_links"]["WRONG-ENDPOINT-ATTEMPT"]["sha256"]
        == (originals[(messy, "WRONG-ENDPOINT-ATTEMPT")]["sha256"])
    )
    assert bodies[(messy, "ENDPOINT-CORRECTION")]["detail"]["blocked_original_retained"]
    assert bodies[(messy, "FALSE-CLOSE")]["detail"]["claimed_complete_without_receipt"]
    assert (
        bodies[(messy, "FALSE-CLOSE")]["record_links"]["OBSERVATION"]["sha256"]
        == (originals[(messy, "OBSERVATION")]["sha256"])
    )
    assert (
        bodies[(messy, "GAP-DISCOVERY")]["record_links"]["FALSE-CLOSE"]["sha256"]
        == (originals[(messy, "FALSE-CLOSE")]["sha256"])
    )
    assert bodies[(messy, "CORRECTION")]["detail"]["exception_open"] is True
    assert bodies[(messy, "FINAL")]["detail"]["open_exception_ids"] == [EXCEPTION]
    assert all(
        event.startswith("2027-")
        and available >= event
        and imported.startswith("2026-")
        and body["detail"]["payload_sha256"] == PAYLOAD_SHA
        and body["detail"]["real_network_bytes"] == 0
        and body["actor_authority"].endswith("PENDING_ACCEPTANCE")
        and body["audit_task_credit"] is False
        for _, _, content, event, available, imported in rows
        for body in (json.loads(content),)
    )
    assert all(
        row["provenance"]["independent_approval"] is False
        and row["provenance"]["actor_authority"].endswith("PENDING_ACCEPTANCE")
        and row["command_id"].startswith("SEC1-")
        and len(row["input_digest"]) == 64
        for row in receipt["native_originals"]
    )


def test_repacked_credit_claim_fails_closed(tmp_path):
    destination = _source(tmp_path)
    _repack_receipt(destination, lambda row: row.__setitem__("audit_task_credit", True))
    with pytest.raises(CompanyStoreError, match="receipt or original claim differs"):
        verify(destination, repository=REPOSITORY, private_repository=PRIVATE)


def test_repacked_original_link_fails_closed(tmp_path):
    destination = _source(tmp_path)
    _repack_receipt(
        destination,
        lambda row: row["native_originals"][0].__setitem__("sha256", "0" * 64),
    )
    with pytest.raises(CompanyStoreError, match="receipt or original claim differs"):
        verify(destination, repository=REPOSITORY, private_repository=PRIVATE)


def test_repacked_native_database_fails_original_byte_check(tmp_path):
    destination = _source(tmp_path)
    database = destination / "company.sqlite3"
    original = database.read_bytes()
    altered = original.replace(
        b"LOCAL_SECURITY_TRANSFER_TRACE_FIXTURE",
        b"LOCAL_SECURITY_TRANSFER_TRACE_FIXXURE",
        1,
    )
    assert altered != original and len(altered) == len(original)
    database.write_bytes(altered)
    database.chmod(0o600)
    manifest_path = destination / "RUN-MANIFEST.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["native_db_sha256"] = sha(database.read_bytes())
    manifest_path.write_bytes(encoded(manifest))
    manifest_path.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="original bytes, provenance or clocks differ"):
        verify(destination, repository=REPOSITORY, private_repository=PRIVATE)


def test_existing_destination_and_sidecar_fail_closed(tmp_path):
    destination = _source(tmp_path)
    original = (destination / "SOURCE_RECEIPT.json").read_bytes()
    with pytest.raises(CompanyStoreError, match="New private selected transfer destination"):
        create(destination, repository=REPOSITORY, private_repository=PRIVATE)
    assert (destination / "SOURCE_RECEIPT.json").read_bytes() == original
    sidecar = destination / "company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed fictional transfer")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="sidecar"):
        verify(destination, repository=REPOSITORY, private_repository=PRIVATE)
