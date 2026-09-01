from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_migration_builds_fresh_sqlite_database(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "head")
    tables = set(inspect(create_engine(f"sqlite:///{database}")).get_table_names())
    assert {"legal_entity", "journal_entry", "journal_line"}.issubset(tables)
    command.downgrade(config, "base")
