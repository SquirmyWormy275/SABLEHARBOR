from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Column, String, Table, create_engine, inspect

from sable_harbor import schema as _schema  # noqa: F401
from sable_harbor.accounting.models import Base


def _config(database: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    return config


def _database_fingerprint(database: Path) -> dict[str, tuple[tuple[str, str, bool], ...]]:
    inspector = inspect(create_engine(f"sqlite:///{database}"))
    return {
        table: tuple(
            sorted(
                (column["name"], column["type"].__class__.__name__, column["nullable"])
                for column in inspector.get_columns(table)
            )
        )
        for table in inspector.get_table_names()
        if table != "alembic_version"
    }


def test_migration_builds_fresh_sqlite_database(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    reference = tmp_path / "metadata-reference.db"
    config = _config(database)
    command.upgrade(config, "head")
    tables = set(inspect(create_engine(f"sqlite:///{database}")).get_table_names())
    assert {"legal_entity", "journal_entry", "journal_line"}.issubset(tables)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    Base.metadata.create_all(create_engine(f"sqlite:///{reference}"))
    assert _database_fingerprint(database) == _database_fingerprint(reference)


def test_historical_migration_ignores_unrelated_live_metadata(tmp_path: Path) -> None:
    database = tmp_path / "migration-isolation.db"
    unrelated = Table(
        "future_unrelated_model",
        Base.metadata,
        Column("id", String(36), primary_key=True),
    )
    try:
        command.upgrade(_config(database), "head")
        tables = set(inspect(create_engine(f"sqlite:///{database}")).get_table_names())
        assert "future_unrelated_model" not in tables
    finally:
        Base.metadata.remove(unrelated)
