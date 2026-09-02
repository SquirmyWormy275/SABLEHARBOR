from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import (
    AccountingBook,
    Base,
    FiscalPeriod,
    JournalEntry,
    JournalLine,
    LegalEntity,
    ScenarioValue,
)
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.service import record_generation_run


def test_standard_generation_has_48_months_actual_forecast_and_is_idempotent() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="test"
        )
        first = generate_standard(session)
        session.commit()
        first_entries = session.scalar(select(func.count(JournalEntry.id)))
        second = generate_standard(session)
        session.commit()
        assert first == second
        assert session.scalar(select(func.count(JournalEntry.id))) == first_entries
        shi_id = session.scalar(select(LegalEntity.id).where(LegalEntity.code == "SHI"))
        shi_periods = session.scalar(
            select(func.count(FiscalPeriod.id))
            .join_from(FiscalPeriod, AccountingBook)
            .where(AccountingBook.entity_id == shi_id)
        )
        assert shi_periods == 48
        marker = session.scalar(
            select(ScenarioValue).where(ScenarioValue.period_code == "2023-2026")
        )
        assert marker is not None
        sources = set(session.scalars(select(JournalEntry.source_type)))
        assert {"monthly_actual", "monthly_forecast"}.issubset(sources)
        revenue = session.scalar(
            select(func.sum(ScenarioValue.amount)).where(
                ScenarioValue.generation_run_id.in_((run.actual_generation_run_id, run.id)),
                ScenarioValue.metric_code == "revenue",
            )
        )
        assert revenue == Decimal("446400000.0000")
        debit, credit = session.execute(
            select(func.sum(JournalLine.debit), func.sum(JournalLine.credit))
        ).one()
        assert debit == credit
