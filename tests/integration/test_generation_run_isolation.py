from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from sable_harbor import schema as _schema  # noqa: F401
from sable_harbor.accounting.models import Base, JournalEntry, ScenarioValue
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import (
    complete_generation_run,
    record_generation_run,
    resolve_generation_run,
    run_context,
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
            select(func.count(JournalEntry.id)).where(JournalEntry.generation_run_id == base_run)
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
        assert stress_revenue == Decimal("428558044.3243")
        assert (
            session.scalar(
                select(func.count(JournalEntry.id)).where(
                    JournalEntry.generation_run_id == base_run
                )
            )
            == base_journal_count
        )


def _order_snapshot(order: tuple[str, ...]) -> dict[str, tuple[Decimal, Decimal, int, int]]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run_ids = {scenario: _generate(session, scenario) for scenario in order}
        snapshot: dict[str, tuple[Decimal, Decimal, int, int]] = {}
        for scenario, run_id in run_ids.items():
            actual_revenue = session.scalar(
                select(func.sum(ScenarioValue.amount)).where(
                    ScenarioValue.generation_run_id == run_id,
                    ScenarioValue.metric_code == "revenue",
                    ScenarioValue.period_code <= "2026-08",
                )
            ) or Decimal(0)
            forecast_revenue = session.scalar(
                select(func.sum(ScenarioValue.amount)).where(
                    ScenarioValue.generation_run_id == run_id,
                    ScenarioValue.metric_code == "revenue",
                    ScenarioValue.period_code > "2026-08",
                )
            ) or Decimal(0)
            snapshot[scenario] = (
                actual_revenue,
                forecast_revenue,
                session.scalar(
                    select(func.count(JournalEntry.id)).where(
                        JournalEntry.generation_run_id == run_id
                    )
                )
                or 0,
                session.scalar(
                    select(func.count(ScenarioValue.id)).where(
                        ScenarioValue.generation_run_id == run_id
                    )
                )
                or 0,
            )
            context = run_context(session, run_id)
            assert len(context.included_run_ids) == 2
            actual_run = session.get(GenerationRun, context.included_run_ids[0])
            assert actual_run is not None and actual_run.profile == "actual_common"
        for scenario in reversed(order):
            _generate(session, scenario)
        for scenario, run_id in run_ids.items():
            assert (
                session.scalar(
                    select(func.count(JournalEntry.id)).where(
                        JournalEntry.generation_run_id == run_id
                    )
                )
                == snapshot[scenario][2]
            )
            assert (
                session.scalar(
                    select(func.count(ScenarioValue.id)).where(
                        ScenarioValue.generation_run_id == run_id
                    )
                )
                == snapshot[scenario][3]
            )
        return snapshot


def test_generation_order_is_equivalent_and_all_scenarios_are_idempotent() -> None:
    base_then_stress = _order_snapshot(("base", "stress"))
    stress_then_base = _order_snapshot(("stress", "base"))
    assert base_then_stress == stress_then_base
    all_scenarios = _order_snapshot(("base", "low", "high", "stress"))
    actual_revenues = {values[0] for values in all_scenarios.values()}
    assert len(actual_revenues) == 1
    assert len({values[1] for values in all_scenarios.values()}) == 4
