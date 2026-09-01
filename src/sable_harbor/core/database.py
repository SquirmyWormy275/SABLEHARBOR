import os
from pathlib import Path

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def database_url() -> str:
    return os.getenv("SHFIN_DATABASE_URL", "sqlite:///var/sable_harbor.db")


def build_engine(url: str | None = None) -> Engine:
    selected = url or database_url()
    if selected.startswith("sqlite:///"):
        path = Path(selected.removeprefix("sqlite:///"))
        path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(selected)


def session_for(engine: Engine) -> Session:
    return Session(engine)


SCHEMA_HEAD = "0007"


def require_migrated_schema(engine: Engine) -> None:
    try:
        with engine.connect() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    except SQLAlchemyError as error:
        raise RuntimeError(
            "Database is not installed; run `uv run alembic upgrade head`"
        ) from error
    if revision != SCHEMA_HEAD:
        raise RuntimeError(
            f"Database revision {revision!r} does not match required head {SCHEMA_HEAD!r}; "
            "run `uv run alembic upgrade head`"
        )
