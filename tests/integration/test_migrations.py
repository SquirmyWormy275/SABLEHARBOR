import csv
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Column, Engine, String, Table, create_engine, inspect, text
from sqlalchemy.orm import Session

from sable_harbor import schema as _schema  # noqa: F401
from sable_harbor.accounting.models import Base
from sable_harbor.accounting.validation import validate_financial_integrity
from sable_harbor.exports.release import package_public_demo
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.service import complete_generation_run, record_generation_run
from sable_harbor.reporting_queries import run_named_query


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


def test_0015_reconciles_populated_legacy_canon_masters(tmp_path: Path) -> None:
    database = tmp_path / "populated-0014.db"
    config = _config(database)
    command.upgrade(config, "0014")
    engine = create_engine(f"sqlite:///{database}")
    entity_ids = {
        "SHI": "71795c5a-bda9-55b8-80e8-b815cfec0dbd",
        "RWH": "66321a51-e743-5644-be4f-85f2ae83f73a",
        "ARU": "932eed72-0384-5a74-8869-90d57bb885bd",
        "CONS": "0dff78a9-a7de-59b4-b4b2-365d64db9448",
    }
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO legal_entity "
                "(id,code,name,fact_state,effective_from,parent_id,jurisdiction) "
                "VALUES (:id,:code,:name,'MODEL_PROPOSED',:effective_from,:parent_id,:jurisdiction)"
            ),
            [
                {
                    "id": entity_ids["SHI"],
                    "code": "SHI",
                    "name": "Sable Harbor Industries",
                    "effective_from": "2016-01-01",
                    "parent_id": None,
                    "jurisdiction": "US-DE",
                },
                {
                    "id": entity_ids["RWH"],
                    "code": "RWH",
                    "name": "Red Wash Operations LLC",
                    "effective_from": "2025-07-01",
                    "parent_id": entity_ids["SHI"],
                    "jurisdiction": "US-WY",
                },
                {
                    "id": entity_ids["ARU"],
                    "code": "ARU",
                    "name": "American Resource Utility LLC",
                    "effective_from": "2026-02-01",
                    "parent_id": entity_ids["SHI"],
                    "jurisdiction": "US-WY",
                },
                {
                    "id": entity_ids["CONS"],
                    "code": "CONS",
                    "name": "Sable Harbor consolidation book",
                    "effective_from": "2026-01-01",
                    "parent_id": entity_ids["SHI"],
                    "jurisdiction": "N/A",
                },
            ],
        )
        connection.execute(
            text(
                "INSERT INTO site "
                "(id,code,name,site_type,region,owner_entity_id,fact_state) VALUES "
                "(:id,:code,:name,:site_type,:region,:owner_entity_id,:fact_state)"
            ),
            [
                {
                    "id": "2d0018d5-a091-534a-82b5-618d9bb4b860",
                    "code": "SAC",
                    "name": "Sacramento headquarters",
                    "site_type": "OFFICE",
                    "region": "California",
                    "owner_entity_id": entity_ids["SHI"],
                    "fact_state": "MODEL_PROPOSED",
                },
                {
                    "id": "2507aa14-4b4d-5684-894e-6198c4d88f80",
                    "code": "RED_WASH",
                    "name": "Red Wash Mine",
                    "site_type": "UNDERGROUND_MINE_MILL",
                    "region": "Wyoming",
                    "owner_entity_id": entity_ids["RWH"],
                    "fact_state": "LOCKED_CANON",
                },
                {
                    "id": "0d36f3af-d2af-5308-bd25-406682b195a8",
                    "code": "ARU_HUB",
                    "name": "ARU regional operating estate",
                    "site_type": "RAIL_TERMINAL_NETWORK",
                    "region": "Mountain West",
                    "owner_entity_id": entity_ids["ARU"],
                    "fact_state": "MODEL_PROPOSED",
                },
            ],
        )
        connection.execute(
            text(
                "INSERT INTO accounting_book (id,entity_id,code,currency) VALUES "
                "(:id,:entity_id,:code,'USD')"
            ),
            [
                {
                    "id": "685d945f-6a1f-5117-9058-2b35c380874c",
                    "entity_id": entity_ids["SHI"],
                    "code": "PRIMARY_USD",
                },
                {
                    "id": "45d09f45-a09f-5740-a69f-8523be1b4db7",
                    "entity_id": entity_ids["CONS"],
                    "code": "PRIMARY_USD",
                },
            ],
        )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        entities = {
            row.code: row
            for row in connection.execute(
                text(
                    "SELECT id,code,name,parent_id,jurisdiction,existence_state,identity_state "
                    "FROM legal_entity"
                )
            ).mappings()
        }
        assert set(entities) == {"SHI", "RWH", "ARU", "BST"}
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
        assert entities["SHI"].name == "Sable Harbor (model parent; formal legal name open)"
        assert entities["RWH"].name == ("Dedicated Red Wash operator (formal legal identity open)")
        assert {code: row.parent_id for code, row in entities.items()} == {
            "SHI": None,
            "RWH": entity_ids["SHI"],
            "ARU": entity_ids["SHI"],
            "BST": entity_ids["ARU"],
        }
        for entity in entities.values():
            assert entity.jurisdiction == "OPEN"
            assert entity.existence_state == "LOCKED"
            assert entity.identity_state == "OPEN"
        railway_site = (
            connection.execute(text("SELECT name,owner_entity_id FROM site WHERE code='ARU_HUB'"))
            .mappings()
            .one()
        )
        assert railway_site.name == "BS&T railway operating estate (details open)"
        assert railway_site.owner_entity_id == entities["BST"].id
        assert connection.scalar(text("SELECT COUNT(*) FROM site WHERE code='PIT'")) == 1
        consolidation_book = (
            connection.execute(
                text(
                    "SELECT entity_id,code FROM accounting_book "
                    "WHERE id='45d09f45-a09f-5740-a69f-8523be1b4db7'"
                )
            )
            .mappings()
            .one()
        )
        assert consolidation_book.entity_id == entities["SHI"].id
        assert consolidation_book.code == "CONSOLIDATION_USD"
        for table_name in inspect(connection).get_table_names():
            for foreign_key in inspect(connection).get_foreign_keys(table_name):
                if foreign_key.get("referred_table") != "legal_entity":
                    continue
                for column_name in foreign_key["constrained_columns"]:
                    count = connection.scalar(
                        text(
                            f'SELECT COUNT(*) FROM "{table_name}" '
                            f'WHERE "{column_name}" = :legacy_cons_id'
                        ),
                        {"legacy_cons_id": entity_ids["CONS"]},
                    )
                    assert count == 0, f"{table_name}.{column_name} still references CONS"

    with Session(engine) as session:
        run = record_generation_run(
            session,
            profile="standard",
            scenario_code="base",
            seed=20260831,
            git_commit="a" * 40,
        )
        generate_standard(session)
        complete_generation_run(session, run)
        session.commit()
        validation = validate_financial_integrity(session, run.id)
        assert validation.passed, validation.as_dict()
        trial_balance = run_named_query(session, "entity_trial_balance", run.id)
        assert trial_balance
        assert {str(row["entity"]) for row in trial_balance} == {"SHI", "RWH", "ARU", "BST"}
        manifest_path = package_public_demo(
            session,
            tmp_path / "upgraded-release",
            generation_run_id=run.id,
            generated_at=datetime(2026, 9, 5, 12, tzinfo=UTC),
        )

    with (manifest_path.parent / "csv/legal_entity.csv").open(newline="") as handle:
        assert {row["code"] for row in csv.DictReader(handle)} == {"SHI", "RWH", "ARU", "BST"}


def test_postgres_0015_reconciles_populated_fact_state_enum() -> None:
    url = os.getenv("SHFIN_POSTGRES_TEST_URL")
    if not url:
        pytest.skip("SHFIN_POSTGRES_TEST_URL is not configured")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.downgrade(config, "base")
    command.upgrade(config, "0014")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO legal_entity "
                "(id,code,name,fact_state,effective_from,parent_id,jurisdiction) VALUES "
                "('71795c5a-bda9-55b8-80e8-b815cfec0dbd','SHI','Legacy parent',"
                "'MODEL_PROPOSED','2016-01-01',NULL,'US-DE')"
            )
        )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        entities = connection.execute(
            text(
                "SELECT code,fact_state FROM legal_entity "
                "WHERE code IN ('SHI','RWH','ARU','BST') ORDER BY code"
            )
        ).all()
        assert entities == [
            ("ARU", "MODEL_PROPOSED"),
            ("BST", "MODEL_PROPOSED"),
            ("RWH", "MODEL_PROPOSED"),
            ("SHI", "MODEL_PROPOSED"),
        ]


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
    digest = hashlib.sha256(json.dumps(first, sort_keys=True, default=str).encode()).hexdigest()
    print(f"POSTGRES_SCHEMA_SHA256={digest}")
