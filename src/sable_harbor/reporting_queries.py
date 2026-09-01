from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from sable_harbor import schema as schema
from sable_harbor.provenance.service import run_context

QUERY_ROOT = Path(__file__).resolve().parents[2] / "db" / "sql"


def named_queries() -> list[str]:
    return sorted(path.stem for path in QUERY_ROOT.glob("*.sql"))


def run_named_query(
    session: Session, name: str, generation_run_id: str
) -> list[dict[str, Any]]:
    if name not in named_queries():
        raise ValueError(f"Unknown named query {name!r}")
    statement = (QUERY_ROOT / f"{name}.sql").read_text()
    context = run_context(session, generation_run_id)
    return [
        dict(row)
        for row in session.execute(
            text(statement),
            {
                "generation_run_id": context.generation_run_id,
                "actual_run_id": context.included_run_ids[0],
            },
        ).mappings()
    ]
