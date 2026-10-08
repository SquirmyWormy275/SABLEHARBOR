"""A selected synthetic component challenge cannot satisfy the CC5.2 task."""

import json
import sqlite3
import stat
from contextlib import closing
from pathlib import Path

import pytest

from enterprise.audit_suite import company_sec001_component_lifecycle_2027 as source
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.documentary_283_route_reconciliation_v6 import _p1_inventory
from enterprise.audit_suite.operating_source_bridge import encoded, sha

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def _create(tmp_path: Path) -> Path:
    tmp_path.chmod(0o700)
    destination = tmp_path / "selected-components"
    source.create(destination, repository=REPOSITORY, private_repository=PRIVATE)
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


def test_selected_history_three_clocks_and_no_credit(tmp_path):
    p1 = _p1_inventory(PRIVATE)
    destination = _create(tmp_path)
    receipt = source.verify(destination, repository=REPOSITORY, private_repository=PRIVATE)
    assert _p1_inventory(PRIVATE) == p1 == source.P1_FREEZE
    assert stat.S_IMODE(destination.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in destination.iterdir())
    assert receipt["task_id"] == source.TASK
    assert receipt["selected_authored_clause"] == source.CLAUSE
    assert receipt["branch_counts"] == {"CLEAN": 10, "MESSY": 15}
    assert receipt["native_count"] == len(receipt["native_originals"]) == 25
    assert receipt["selected_component_ids"] == [source.CORE, source.OUTSOURCED]
    assert receipt["actor_authority"].endswith("PENDING_ACCEPTANCE")
    assert all(
        row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
        and row["existing_targeted_integrated_source_ids"] == ["SEC003_SELECTED_VULNERABILITY_V1"]
        and row["current_status"] == "NOT_STARTED"
        and row["current_conclusion"] == "NOT_RUN"
        and row["authored_test_clause"] == source.CLAUSE
        and row["audit_task_credit"] is False
        for row in receipt["route_disposition"].values()
    )
    assert all(
        receipt[key] is False
        for key in (
            "actual_supplier_selected_or_contracted",
            "actual_deployed_component",
            "approved_enterprise_architecture",
            "independent_approval",
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
    originals = {(r["branch"], r["record"]): r for r in receipt["native_originals"]}
    clean, messy = source.BRANCHES.values()
    assert bodies[(clean, "INVENTORY")]["detail"]["component_ids"] == [
        source.CORE,
        source.OUTSOURCED,
    ]
    assert bodies[(messy, "INVENTORY")]["detail"]["component_ids"] == [source.CORE]
    assert bodies[(clean, "UNSUPPORTED-CHALLENGE")]["detail"]["no_live_probe"] is True
    assert bodies[(messy, "FALSE-CLOSE")]["detail"]["claimed_full_component_coverage"]
    assert bodies[(messy, "FALSE-CLOSE")]["detail"]["actually_incomplete"]
    assert (
        bodies[(messy, "GAP-DISCOVERY")]["record_links"]["FALSE-CLOSE"]["sha256"]
        == originals[(messy, "FALSE-CLOSE")]["sha256"]
    )
    assert (
        bodies[(messy, "FALSE-CLOSE-CORRECTION")]["record_links"]["FALSE-CLOSE"]["sha256"]
        == originals[(messy, "FALSE-CLOSE")]["sha256"]
    )
    assert bodies[(messy, "FALSE-CLOSE-CORRECTION")]["detail"]["false_close_erased"] is False
    assert bodies[(messy, "FINAL")]["detail"]["open_exception_ids"] == [source.EXCEPTION]
    assert bodies[(clean, "FINAL")]["detail"]["open_exception_ids"] == []
    assert all(
        event.startswith("2027-")
        and available >= event
        and imported.startswith("2026-")
        and body["actor_authority"].endswith("PENDING_ACCEPTANCE")
        and body["detail"]["actual_deployed_component"] is False
        and body["detail"]["actual_supplier_selected_or_contracted"] is False
        and body["audit_task_credit"] is False
        for _, _, content, event, available, imported in rows
        for body in (json.loads(content),)
    )
    assert all(
        r["provenance"]["actual_supplier_or_deployment"] is False
        and r["command_id"].startswith("SEC1-COMP-")
        and len(r["input_digest"]) == 64
        for r in receipt["native_originals"]
    )


def test_repacked_credit_and_original_link_fail_closed(tmp_path):
    destination = _create(tmp_path)
    _repack_receipt(destination, lambda row: row.__setitem__("audit_task_credit", True))
    with pytest.raises(CompanyStoreError, match="receipt or original claim differs"):
        source.verify(destination, repository=REPOSITORY, private_repository=PRIVATE)
    other = tmp_path / "other"
    source.create(other, repository=REPOSITORY, private_repository=PRIVATE)
    _repack_receipt(other, lambda row: row["native_originals"][0].__setitem__("sha256", "0" * 64))
    with pytest.raises(CompanyStoreError, match="receipt or original claim differs"):
        source.verify(other, repository=REPOSITORY, private_repository=PRIVATE)


def test_repacked_database_fails_original_byte_check(tmp_path):
    destination = _create(tmp_path)
    database = destination / "company.sqlite3"
    original = database.read_bytes()
    altered = original.replace(b"SIMULATED_CURRENT", b"SIMULATED_CURRENX", 1)
    assert altered != original and len(altered) == len(original)
    database.write_bytes(altered)
    database.chmod(0o600)
    manifest_path = destination / "RUN-MANIFEST.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["native_db_sha256"] = sha(database.read_bytes())
    manifest_path.write_bytes(encoded(manifest))
    manifest_path.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="original, provenance or clocks differ"):
        source.verify(destination, repository=REPOSITORY, private_repository=PRIVATE)


def test_existing_destination_and_sidecar_fail_closed(tmp_path):
    destination = _create(tmp_path)
    original = (destination / "SOURCE_RECEIPT.json").read_bytes()
    with pytest.raises(CompanyStoreError, match="New private selected component destination"):
        source.create(destination, repository=REPOSITORY, private_repository=PRIVATE)
    assert (destination / "SOURCE_RECEIPT.json").read_bytes() == original
    sidecar = destination / "company.sqlite3-wal"
    sidecar.write_bytes(b"not a sealed native original")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="sidecar"):
        source.verify(destination, repository=REPOSITORY, private_repository=PRIVATE)


def test_route_pin_drift_fails_closed(monkeypatch):
    monkeypatch.setattr(source, "ROUTE_SHA", "0" * 64)
    with pytest.raises(CompanyStoreError, match="Reviewed V10 component route bytes differ"):
        source._route(REPOSITORY, PRIVATE)
