from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from sable_harbor import schema as _schema  # noqa: F401
from sable_harbor.accounting.models import (
    Base,
    FreightMovement,
    InventoryLot,
    JournalEntry,
    ProductionRecord,
    ScenarioValue,
)
from sable_harbor.generation import generate_standard
from sable_harbor.provenance import identity as identity_module
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

        base_context = run_context(session, base_run)
        stress_context = run_context(session, stress_run)
        base_revenue = session.scalar(
            select(func.sum(ScenarioValue.amount)).where(
                ScenarioValue.generation_run_id.in_(base_context.included_run_ids),
                ScenarioValue.metric_code == "revenue",
            )
        )
        stress_revenue = session.scalar(
            select(func.sum(ScenarioValue.amount)).where(
                ScenarioValue.generation_run_id.in_(stress_context.included_run_ids),
                ScenarioValue.metric_code == "revenue",
            )
        )
        assert base_revenue == Decimal("446400000.0000")
        assert stress_revenue == Decimal("426344708.7567")
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
            context = run_context(session, run_id)
            actual_revenue = session.scalar(
                select(func.sum(ScenarioValue.amount)).where(
                    ScenarioValue.generation_run_id.in_(context.included_run_ids),
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


def test_monthly_actuals_and_forecasts_obey_the_persisted_run_cutoff_partition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Use a deliberately non-default cutoff so this test fails if generation
    # embeds the production August boundary instead of reading GenerationRun.
    monkeypatch.setattr(identity_module, "ACTUAL_THROUGH", date(2026, 6, 30))
    monkeypatch.setattr(identity_module, "FORECAST_FROM", date(2026, 7, 1))
    database = tmp_path / "persisted-cutoff.db"
    url = f"sqlite:///{database}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    with Session(engine) as session:
        base_run = _generate(session, "base")
        stress_run = _generate(session, "stress")
        base_context = run_context(session, base_run)
        stress_context = run_context(session, stress_run)
        actual_run_id = base_context.included_run_ids[0]
        assert stress_context.included_run_ids[0] == actual_run_id
        persisted_run = session.get(GenerationRun, base_run)
        assert persisted_run is not None
        assert persisted_run.actual_through == date(2026, 6, 30)
        assert persisted_run.forecast_from == date(2026, 7, 1)
        cutoff_period = persisted_run.actual_through.strftime("%Y-%m")

        assert session.scalar(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.source_type == "monthly_actual",
                JournalEntry.generation_run_id.in_((base_run, stress_run)),
            )
        ) == 0

        dated_fact_specs = (
            (ProductionRecord, ProductionRecord.period_code, cutoff_period),
            (FreightMovement, FreightMovement.movement_date, persisted_run.actual_through),
            (InventoryLot, InventoryLot.as_of_date, persisted_run.actual_through),
        )
        for model, date_column, cutoff in dated_fact_specs:
            assert session.scalar(
                select(func.count(model.id)).where(
                    model.generation_run_id == actual_run_id,
                    date_column > cutoff,
                )
            ) == 0
            assert session.scalar(
                select(func.count(model.id)).where(
                    model.generation_run_id.in_((base_run, stress_run)),
                    date_column <= cutoff,
                )
            ) == 0
        assert session.scalar(
            select(func.count(ProductionRecord.id)).where(
                ProductionRecord.generation_run_id == actual_run_id
            )
        ) == 6
        assert session.scalar(
            select(func.count(ProductionRecord.id)).where(
                ProductionRecord.generation_run_id == base_run
            )
        ) == 6
        assert session.scalar(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.source_type == "monthly_actual",
                JournalEntry.generation_run_id == actual_run_id,
            )
        ) > 0
        assert session.scalar(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.source_type == "monthly_forecast",
                JournalEntry.generation_run_id == actual_run_id,
            )
        ) == 0
        assert session.scalar(
            select(func.count(ScenarioValue.id)).where(
                ScenarioValue.metric_code.in_(("revenue", "operating_cost")),
                ScenarioValue.period_code <= cutoff_period,
                ScenarioValue.generation_run_id.in_((base_run, stress_run)),
            )
        ) == 0
        assert session.scalar(
            select(func.count(ScenarioValue.id)).where(
                ScenarioValue.metric_code.in_(("revenue", "operating_cost")),
                ScenarioValue.period_code > cutoff_period,
                ScenarioValue.generation_run_id == actual_run_id,
            )
        ) == 0


def test_ending_inventory_is_materialized_by_actual_layer_at_cutoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(identity_module, "ACTUAL_THROUGH", date(2026, 12, 31))
    monkeypatch.setattr(identity_module, "FORECAST_FROM", date(2027, 1, 1))
    database = tmp_path / "actual-ending-inventory.db"
    url = f"sqlite:///{database}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url)

    with Session(engine) as session:
        base_run = _generate(session, "base")
        context = run_context(session, base_run)
        actual_run_id = context.included_run_ids[0]
        ending_lots = session.scalars(
            select(InventoryLot).where(InventoryLot.lot_number == "RWH-2026-ENDING")
        ).all()

        assert len(ending_lots) == 1
        assert ending_lots[0].generation_run_id == actual_run_id
        assert ending_lots[0].as_of_date == date(2026, 12, 31)
        assert ending_lots[0].quantity == Decimal("68400.0000")
        assert ending_lots[0].carrying_value == Decimal("2900000.00")
        assert session.scalar(
            select(func.count(InventoryLot.id)).where(
                InventoryLot.generation_run_id == base_run,
                InventoryLot.as_of_date <= date(2026, 12, 31),
            )
        ) == 0
