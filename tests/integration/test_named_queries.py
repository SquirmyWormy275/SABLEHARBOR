from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.service import complete_generation_run, record_generation_run
from sable_harbor.reporting_queries import named_queries, run_named_query, single_run_named_queries


def test_all_required_named_queries_execute() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="a" * 40
        )
        generate_standard(session)
        complete_generation_run(session, run)
        comparison_run = record_generation_run(
            session,
            profile="standard",
            scenario_code="stress",
            seed=20260831,
            git_commit="a" * 40,
        )
        generate_standard(session, scenario="stress")
        complete_generation_run(session, comparison_run)
        session.commit()
        names = named_queries()
        assert len(names) >= 20
        for name in single_run_named_queries():
            result = run_named_query(session, name, run.id)
            assert isinstance(result, list), name
        with pytest.raises(ValueError, match="explicit comparison run"):
            run_named_query(session, "scenario_variance", run.id)
        with pytest.raises(ValueError, match="distinct"):
            run_named_query(session, "scenario_variance", run.id, run.id)
        variance = run_named_query(
            session,
            "scenario_variance",
            run.id,
            comparison_generation_run_id=comparison_run.id,
        )
        calibration_row = next(
            row
            for row in variance
            if row["metric_code"] == "revenue"
            and row["entity_code"] == "SHI"
            and row["period_code"] == "2026-08"
        )
        forecast_row = next(
            row
            for row in variance
            if row["metric_code"] == "revenue"
            and row["entity_code"] == "SHI"
            and row["period_code"] == "2026-09"
        )
        assert calibration_row["selected_amount"] is not None
        assert calibration_row["comparison_amount"] is not None
        assert Decimal(calibration_row["comparison_variance"]) == 0
        assert forecast_row["selected_amount"] is not None
        assert forecast_row["comparison_amount"] is not None
        assert Decimal(forecast_row["comparison_variance"]) != 0
        engagement_margin = run_named_query(session, "engagement_margin_wip", run.id)
        assert engagement_margin
        assert all(row["revenue"] > 0 and row["cost"] > 0 for row in engagement_margin)
        assert all(abs(row["wip"]) <= 0.0001 for row in engagement_margin)
