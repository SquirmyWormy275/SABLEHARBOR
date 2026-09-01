from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base, ScenarioValue
from sable_harbor.generation import generate_full_history, generate_standard


def _scenario_revenue(scenario: str) -> Decimal:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        generate_standard(session, scenario=scenario)
        return session.scalar(
            select(func.sum(ScenarioValue.amount)).where(
                ScenarioValue.scenario_code == scenario,
                ScenarioValue.metric_code == "revenue",
            )
        )


def test_low_high_and_stress_are_correlated_configured_cases() -> None:
    assert _scenario_revenue("low") == Decimal("401760000.0000")
    assert _scenario_revenue("high") == Decimal("499968000.0000")
    assert _scenario_revenue("stress") == Decimal("321408000.0000")


def test_full_history_adds_noncontrolling_2016_to_2022_anchors() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
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
