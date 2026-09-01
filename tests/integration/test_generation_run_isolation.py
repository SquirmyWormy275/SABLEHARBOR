from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from sable_harbor import schema as _schema  # noqa: F401
from sable_harbor.accounting.models import Base, JournalEntry, ScenarioValue
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.service import (
    complete_generation_run,
    record_generation_run,
    resolve_generation_run,
)


def _generate(session: Session, scenario: str) -> str:
    run = record_generation_run(
        session,
        profile="standard",
        scenario_code=scenario,
        seed=20260831,
        git_commit="test-commit",
    )
    generate_standard(session, scenario=scenario)
    complete_generation_run(session, run)
    session.commit()
    return run.id


def test_base_and_stress_coexist_without_cross_run_contamination() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        base_run = _generate(session, "base")
        base_journal_count = session.scalar(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.generation_run_id == base_run
            )
        )
        stress_run = _generate(session, "stress")

        assert base_run != stress_run
        with pytest.raises(ValueError, match="explicit generation run"):
            resolve_generation_run(session)
        assert resolve_generation_run(session, base_run) == base_run

        base_revenue = session.scalar(
            select(func.sum(ScenarioValue.amount)).where(
                ScenarioValue.generation_run_id == base_run,
                ScenarioValue.metric_code == "revenue",
            )
        )
        stress_revenue = session.scalar(
            select(func.sum(ScenarioValue.amount)).where(
                ScenarioValue.generation_run_id == stress_run,
                ScenarioValue.metric_code == "revenue",
            )
        )
        assert base_revenue == Decimal("446400000.0000")
        assert stress_revenue == Decimal("321408000.0000")
        assert session.scalar(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.generation_run_id == base_run
            )
        ) == base_journal_count

        journal_run_ids = set(
            session.scalars(
                select(JournalEntry.generation_run_id).where(
                    JournalEntry.generation_run_id.in_([base_run, stress_run])
                )
            )
        )
        value_run_ids = set(
            session.scalars(
                select(ScenarioValue.generation_run_id).where(
                    ScenarioValue.generation_run_id.in_([base_run, stress_run])
                )
            )
        )
        assert journal_run_ids == {base_run, stress_run}
        assert value_run_ids == {base_run, stress_run}

        _generate(session, "base")
        assert session.scalar(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.generation_run_id == base_run
            )
        ) == base_journal_count
