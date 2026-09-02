import sqlite3
from pathlib import Path

from blackridge.cli import build_database, validate


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
