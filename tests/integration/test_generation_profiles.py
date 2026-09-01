from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from sable_harbor.cli import app
from sable_harbor.core.ids import stable_id
from sable_harbor.provenance.models import GenerationRun


@pytest.mark.parametrize(
    "arguments",
    [
        ["report", "--generation-run-id", "missing"],
        ["workbooks", "--generation-run-id", "missing"],
        ["package-release", "--generation-run-id", "missing"],
        ["query", "entity_trial_balance", "--generation-run-id", "missing"],
        ["statements", "--generation-run-id", "missing"],
    ],
)
def test_read_commands_never_install_or_generate_on_fresh_database(
    tmp_path: Path, arguments: list[str]
) -> None:
    database = tmp_path / "fresh.db"
    url = f"sqlite:///{database}"
    result = CliRunner().invoke(app, arguments, env={"SHFIN_DATABASE_URL": url})
    assert result.exit_code != 0
    assert inspect(create_engine(url)).get_table_names() == []


@pytest.mark.parametrize(
    ("profile", "scenario"),
    [
        ("standard", "base"),
        ("baseline", "low"),
        ("full", "high"),
        ("full_history", "base"),
        ("stress", "stress"),
        ("benchmark_private", "base"),
    ],
)
def test_generation_profile_has_run_marker_and_no_null_owned_facts(
    tmp_path: Path, profile: str, scenario: str
) -> None:
    database = tmp_path / "var" / "private" / f"{profile}.db"
    database.parent.mkdir(parents=True)
    url = f"sqlite:///{database}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")

    requested_scenario = "base" if profile == "stress" else scenario
    result = CliRunner().invoke(
        app,
        [
            "generate",
            "--profile",
            profile,
            "--scenario",
            requested_scenario,
            "--seed",
            "20260831",
        ],
        env={"SHFIN_DATABASE_URL": url},
    )
    assert result.exit_code == 0, result.output

    run_id = stable_id("generation_run", f"v0.1:{profile}:{scenario}:20260831")
    engine = create_engine(url)
    with Session(engine) as session:
        run = session.get(GenerationRun, run_id)
        assert run is not None
        assert run.status == "COMPLETED"
        marker_count = session.scalar(
            text(
                "SELECT COUNT(*) FROM scenario_value "
                "WHERE generation_run_id=:run_id AND metric_code='run_marker'"
            ),
            {"run_id": run_id},
        )
        assert marker_count == 1
        inspector = inspect(engine)
        for table in inspector.get_table_names():
            columns = {item["name"] for item in inspector.get_columns(table)}
            if "generation_run_id" not in columns:
                continue
            null_count = session.scalar(
                text(f'SELECT COUNT(*) FROM "{table}" WHERE generation_run_id IS NULL')
            )
            assert null_count == 0, table

        before = session.scalar(select(GenerationRun.status).where(GenerationRun.id == run_id))
    rerun = CliRunner().invoke(
        app,
        ["generate", "--profile", profile, "--scenario", requested_scenario, "--seed", "20260831"],
        env={"SHFIN_DATABASE_URL": url},
    )
    assert rerun.exit_code == 0, rerun.output
    with Session(engine) as session:
        assert (
            session.scalar(select(GenerationRun.status).where(GenerationRun.id == run_id)) == before
        )
        assert (
            session.scalar(
                text(
                    "SELECT COUNT(*) FROM scenario_value "
                    "WHERE generation_run_id=:run_id AND metric_code='run_marker'"
                ),
                {"run_id": run_id},
            )
            == 1
        )
