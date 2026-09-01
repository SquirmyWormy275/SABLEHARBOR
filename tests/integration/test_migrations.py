import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Column, Engine, String, Table, create_engine, inspect

from sable_harbor import schema as _schema  # noqa: F401
from sable_harbor.accounting.models import Base


def _config(database: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    return config


def schema_fingerprint(engine: Engine) -> dict[str, Any]:
    inspector = inspect(engine)
    tables: dict[str, Any] = {}
    for table in inspector.get_table_names():
        if table == "alembic_version":
            continue
        columns = tuple(
            sorted(
                (
                    column["name"],
                    str(column["type"]),
                    column["nullable"],
                    str(column.get("default")),
                )
                for column in inspector.get_columns(table)
            )
        )
        foreign_keys = tuple(
            sorted(
                (
                    tuple(key["constrained_columns"]),
                    key["referred_table"],
                    tuple(key["referred_columns"]),
                )
                for key in inspector.get_foreign_keys(table)
            )
        )
        uniques = tuple(
            sorted(
                tuple(constraint["column_names"])
                for constraint in inspector.get_unique_constraints(table)
            )
        )
        indexes = tuple(
            sorted(
                (
                    index["name"],
                    tuple(index["column_names"]),
                    index["unique"],
                )
                for index in inspector.get_indexes(table)
            )
        )
        checks = tuple(
            sorted(
                str(constraint["sqltext"]) for constraint in inspector.get_check_constraints(table)
            )
        )
        tables[table] = {
            "columns": columns,
            "primary_key": tuple(inspector.get_pk_constraint(table)["constrained_columns"]),
            "foreign_keys": foreign_keys,
            "unique_constraints": uniques,
            "indexes": indexes,
            "check_constraints": checks,
        }
    enums = ()
    if hasattr(inspector, "get_enums"):
        enums = tuple(
            sorted((item["name"], tuple(item["labels"])) for item in inspector.get_enums())
        )
    return {"tables": tables, "enums": enums}


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
    assert schema_fingerprint(create_engine(f"sqlite:///{database}")) == schema_fingerprint(
        create_engine(f"sqlite:///{reference}")
    )


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


def test_postgres_upgrade_downgrade_upgrade_schema_fingerprint() -> None:
    url = os.getenv("SHFIN_POSTGRES_TEST_URL")
    if not url:
        pytest.skip("SHFIN_POSTGRES_TEST_URL is not configured")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    engine = create_engine(url)
    command.upgrade(config, "head")
    first = schema_fingerprint(engine)
    assert "generation_run" in first["tables"]
    assert (
        "factstate",
        (
            "LOCKED_CANON",
            "PROVISIONAL_CANON",
            "OPEN_CANON",
            "SUPERSEDED",
            "LEGACY_CALIBRATION",
            "MODEL_PROPOSED",
            "SCENARIO_INPUT",
            "SYNTHETIC_INSTANCE",
            "DERIVED",
            "EXTERNAL_RESEARCH",
        ),
    ) in first["enums"]
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    assert schema_fingerprint(engine) == first
    digest = hashlib.sha256(
        json.dumps(first, sort_keys=True, default=str).encode()
    ).hexdigest()
    print(f"POSTGRES_SCHEMA_SHA256={digest}")
