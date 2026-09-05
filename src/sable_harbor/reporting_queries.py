from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from sable_harbor import schema as schema
from sable_harbor.provenance.service import comparison_run_contexts, run_context

QUERY_ROOT = Path(__file__).resolve().parents[2] / "db" / "sql"
COMPARISON_QUERIES = frozenset({"scenario_variance"})


def named_queries() -> list[str]:
    return sorted(path.stem for path in QUERY_ROOT.glob("*.sql"))


def single_run_named_queries() -> list[str]:
    return [name for name in named_queries() if name not in COMPARISON_QUERIES]


def run_named_query(
    session: Session,
    name: str,
    generation_run_id: str,
    comparison_generation_run_id: str | None = None,
) -> list[dict[str, Any]]:
    if name not in named_queries():
        raise ValueError(f"Unknown named query {name!r}")
    statement = (QUERY_ROOT / f"{name}.sql").read_text()
    context = run_context(session, generation_run_id)
    parameters = {
        "generation_run_id": context.generation_run_id,
        "actual_run_id": context.included_run_ids[0],
    }
    if name in COMPARISON_QUERIES:
        if comparison_generation_run_id is None:
            raise ValueError(f"Named query {name!r} requires an explicit comparison run")
        selected, comparison = comparison_run_contexts(
            session, generation_run_id, comparison_generation_run_id
        )
        parameters.update(
            {
                "calibration_run_id": selected.included_run_ids[0],
                "selected_generation_run_id": selected.generation_run_id,
                "comparison_generation_run_id": comparison.generation_run_id,
            }
        )
    elif comparison_generation_run_id is not None:
        raise ValueError(f"Named query {name!r} does not accept a comparison run")
    return [dict(row) for row in session.execute(text(statement), parameters).mappings()]
