from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from sable_harbor import schema as schema

QUERY_ROOT = Path(__file__).resolve().parents[2] / "db" / "sql"


def named_queries() -> list[str]:
    return sorted(path.stem for path in QUERY_ROOT.glob("*.sql"))


def run_named_query(session: Session, name: str) -> list[dict[str, Any]]:
    if name not in named_queries():
        raise ValueError(f"Unknown named query {name!r}")
    statement = (QUERY_ROOT / f"{name}.sql").read_text()
    return [dict(row) for row in session.execute(text(statement)).mappings()]
