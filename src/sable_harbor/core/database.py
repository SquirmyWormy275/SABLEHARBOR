import os
from pathlib import Path

from sqlalchemy import Engine, create_engine
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
