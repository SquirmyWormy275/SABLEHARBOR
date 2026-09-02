import sqlite3
from pathlib import Path

from blackridge.cli import (
    build_database,
    build_snapshot,
    deterministic_replay,
    export_artifacts,
    export_csv,
    validate,
    validate_csv_exports,
    workbook_qa,
)


def test_smoke_build_and_reconcile(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    db = build_database("smoke", 20150112)
    result = validate(db)
    assert result["status"] == "PASS"
    assert result["checks"]["journals_balanced"]
    assert 5_000_000_000 <= result["impairment_minor"] <= 5_400_000_000


def test_public_schema_has_no_oracle(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    db_path = build_database("smoke", 20150112)
    db = sqlite3.connect(db_path)
    names = [r[0].lower() for r in db.execute("SELECT name FROM sqlite_master")]
    assert not any("oracle" in name for name in names)


def test_corruption_unbalanced_journal_is_detected(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    db_path = build_database("smoke", 20150112)
    db = sqlite3.connect(db_path)
    db.execute("UPDATE journal_line_detail SET debit_minor=debit_minor+1 WHERE id=1")
    db.commit()
    db.close()
    result = validate(db_path)
    assert result["status"] == "FAIL"
    assert not result["checks"]["journals_balanced"]


def test_snapshot_excludes_future_available_records(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    db_path = build_database("smoke", 20150112)
    snapshot = build_snapshot(db_path, "2015-05-18")
    db = sqlite3.connect(snapshot)
    leaked = db.execute(
        "SELECT COUNT(*) FROM event_ledger WHERE available_at > '2015-05-18T23:59:59+00:00'"
    ).fetchone()[0]
    assert leaked == 0


def test_deterministic_smoke_replay(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    result = deterministic_replay("smoke", 20150112)
    assert result["status"] == "PASS"


def test_corruption_conservation_is_detected(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    db_path = build_database("smoke", 20150112)
    db = sqlite3.connect(db_path)
    db.execute("UPDATE conservation_balance SET closing_milli=closing_milli+1 WHERE id=1")
    db.commit()
    db.close()
    result = validate(db_path)
    assert result["status"] == "FAIL"
    assert not result["checks"]["physical_conservation"]


def test_corruption_negative_inventory_is_detected(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    db_path = build_database("smoke", 20150112)
    db = sqlite3.connect(db_path)
    db.execute("UPDATE inventory_balance SET quantity_milli=-1 WHERE id=1")
    db.commit()
    db.close()
    result = validate(db_path)
    assert result["status"] == "FAIL"
    assert not result["checks"]["nonnegative_inventory"]


def test_corruption_impossible_timestamp_is_detected(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    db_path = build_database("smoke", 20150112)
    db = sqlite3.connect(db_path)
    db.execute("UPDATE asset SET available_at='2014-01-01T00:00:00+00:00' WHERE id=1")
    db.commit()
    db.close()
    result = validate(db_path)
    assert result["status"] == "FAIL"
    assert not result["checks"]["temporal_ordering"]


def test_corruption_impairment_lineage_is_detected(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    db_path = build_database("smoke", 20150112)
    db = sqlite3.connect(db_path)
    db.execute("UPDATE phase4_valuation SET recoverable_minor=recoverable_minor+1")
    db.commit()
    db.close()
    result = validate(db_path)
    assert result["status"] == "FAIL"
    assert not result["checks"]["impairment_lineage"]


def test_corruption_double_assignment_is_detected(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    db_path = build_database("smoke", 20150112)
    db = sqlite3.connect(db_path)
    row = db.execute("SELECT * FROM exclusive_assignment WHERE id=1").fetchone()
    db.execute(
        "INSERT INTO exclusive_assignment VALUES(?,?,?,?,?,?,?)",
        (999999, row[1], row[2], "CORRUPT-DUPLICATE", row[4], row[5], row[6]),
    )
    db.commit()
    db.close()
    result = validate(db_path)
    assert result["status"] == "FAIL"
    assert not result["checks"]["resource_exclusivity"]


def test_corruption_orphan_purchase_order_line_is_detected(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    db_path = build_database("smoke", 20150112)
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys=OFF")
    db.execute("DELETE FROM purchase_order WHERE id=1")
    db.commit()
    db.close()
    result = validate(db_path)
    assert result["status"] == "FAIL"
    assert not result["checks"]["foreign_keys"]


def test_corruption_missing_haul_destination_is_detected(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    db_path = build_database("smoke", 20150112)
    db = sqlite3.connect(db_path)
    db.execute("UPDATE haul_cycle_detail SET destination_location='' WHERE haul_cycle_id=1")
    db.commit()
    db.close()
    result = validate(db_path)
    assert result["status"] == "FAIL"
    assert not result["checks"]["haul_destinations"]


def test_corruption_missing_subledger_link_is_detected(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    db_path = build_database("smoke", 20150112)
    db = sqlite3.connect(db_path)
    db.execute("DELETE FROM subledger_reconciliation WHERE period='2015-01' AND subledger='AP'")
    db.commit()
    db.close()
    result = validate(db_path)
    assert result["status"] == "FAIL"
    assert not result["checks"]["complete_subledger_links"]


def test_corruption_truncated_vendor_export_is_detected(tmp_path: Path, monkeypatch) -> None:
    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path)
    db_path = build_database("smoke", 20150112)
    exports = export_csv(db_path)
    vendor = next(path for path in exports if path.stem == "vendor")
    lines = vendor.read_text().splitlines()
    vendor.write_text("\n".join(lines[:-1]) + "\n")
    result = validate_csv_exports(db_path, exports)
    assert result["status"] == "FAIL"
    assert result["mismatches"][0]["table"] == "vendor"


def test_corruption_workbook_database_hash_mismatch_is_detected(
    tmp_path: Path, monkeypatch
) -> None:
    from openpyxl import load_workbook

    from blackridge import cli

    monkeypatch.setattr(cli, "PUBLIC", tmp_path / "public")
    monkeypatch.setattr(cli, "REPORTS", tmp_path / "reports")
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    db_path = build_database("smoke", 20150112)
    workbook = export_artifacts(db_path, validate(db_path))
    book = load_workbook(workbook)
    book["START_HERE"]["B3"] = "corrupted-database-hash"
    book.save(workbook)
    result = workbook_qa(workbook, db_path)
    assert result["status"] == "FAIL"
    assert not result["checks"]["database_hash_embedded"]
