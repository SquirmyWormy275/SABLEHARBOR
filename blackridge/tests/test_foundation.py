import sqlite3
from pathlib import Path

from blackridge.cli import build_database, build_snapshot, deterministic_replay, validate


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
