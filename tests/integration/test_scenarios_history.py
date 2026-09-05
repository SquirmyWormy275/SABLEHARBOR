from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base, ScenarioValue
from sable_harbor.generation import generate_full_history, generate_standard
from sable_harbor.provenance.service import record_generation_run


def _scenario_revenue(scenario: str) -> Decimal:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code=scenario, seed=20260831, git_commit="a" * 40
        )
        generate_standard(session, scenario=scenario)
        assert run.actual_generation_run_id is not None
        return session.scalar(
            select(func.sum(ScenarioValue.amount)).where(
                ScenarioValue.generation_run_id.in_((run.actual_generation_run_id, run.id)),
                ScenarioValue.metric_code == "revenue",
            )
        )


def test_low_high_and_stress_are_correlated_configured_cases() -> None:
    assert _scenario_revenue("low") == Decimal("440186387.7809")
    assert _scenario_revenue("high") == Decimal("452638628.1338")
    assert _scenario_revenue("stress") == Decimal("426344708.7567")


def test_business_line_drivers_are_persisted_with_governance_metadata() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="stress", seed=20260831, git_commit="a" * 40
        )
        generate_standard(session, scenario="stress")
        drivers = session.scalars(
            select(ScenarioValue).where(
                ScenarioValue.generation_run_id == run.id,
                ScenarioValue.metric_code.like("driver_%"),
            )
        ).all()
        assert {driver.entity_code for driver in drivers} == {
            "SHI",
            "RWH",
            "ARU",
            "CRADLE",
            "RESEARCH",
            "ADVISORY",
            "CAPITAL",
        }
        assert all(driver.unit == "multiplier" for driver in drivers)
        assert all(driver.fact_state.value == "SCENARIO_INPUT" for driver in drivers)
        assert all('"owner": "FP&A"' in driver.provenance for driver in drivers)
        applied = {"SHI", "RWH", "ARU"}
        assert all(
            (
                '"application_status": "APPLIED_TO_GENERATION"'
                if driver.entity_code in applied
                else '"application_status": "RECORDED_ONLY_NOT_APPLIED"'
            )
            in driver.provenance
            for driver in drivers
        )
        assert all(driver.period_code == "2026-09_to_2026-12" for driver in drivers)


def test_full_history_adds_noncontrolling_2016_to_2022_anchors() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        record_generation_run(
            session,
            profile="full_history",
            scenario_code="base",
            seed=20260831,
            git_commit="a" * 40,
        )
        result = generate_full_history(session)
        anchors = session.scalars(
            select(ScenarioValue).where(ScenarioValue.metric_code == "historical_revenue_anchor")
        ).all()
        assert result["history_start"] == 2016
        assert len(anchors) == 7
        assert all(anchor.fact_state.value == "LEGACY_CALIBRATION" for anchor in anchors)


def test_unknown_scenario_fails_usefully() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session, pytest.raises(ValueError, match="Unknown scenario"):
        generate_standard(session, scenario="unsupported")
