import os
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def database_url() -> str:
    return os.getenv("SHFIN_DATABASE_URL", "sqlite:///var/sable_harbor.db")


def build_engine(url: str | None = None) -> Engine:
    selected = url or database_url()
    if selected.startswith("sqlite:///"):
        path = Path(selected.removeprefix("sqlite:///"))
        path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(selected)
    if selected.startswith("sqlite:"):
        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection: object, _record: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()

    return engine


def session_for(engine: Engine) -> Session:
    return Session(engine)


def required_schema_head(config: Config | None = None) -> str:
    heads = ScriptDirectory.from_config(config or Config("alembic.ini")).get_heads()
    if len(heads) != 1:
        raise RuntimeError(f"Expected one Alembic head, found {heads!r}")
    return heads[0]


def require_migrated_schema(engine: Engine) -> None:
    try:
        with engine.connect() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    except SQLAlchemyError as error:
        raise RuntimeError(
            "Database is not installed; run `uv run alembic upgrade head`"
        ) from error
    schema_head = required_schema_head()
    if revision != schema_head:
        raise RuntimeError(
            f"Database revision {revision!r} does not match required head {schema_head!r}; "
            "run `uv run alembic upgrade head`"
        )
