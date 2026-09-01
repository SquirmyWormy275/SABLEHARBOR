from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from sable_harbor.accounting.models import JournalEntry, ScenarioValue
from sable_harbor.cli import app
from sable_harbor.core.database import required_schema_head
from sable_harbor.provenance.identity import (
    ACTUAL_THROUGH,
    FORECAST_FROM,
    GENERATOR_VERSION,
    RunIdentity,
    normalize_profile_scenario,
)
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import record_generation_run, run_context


def _migrated_url(tmp_path: Path, name: str = "stage1.db") -> str:
    database = tmp_path / name
    database.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{database}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    return url


def test_run_identity_normalizes_stress_and_cli_uses_same_service() -> None:
    assert normalize_profile_scenario("stress", "base") == ("stress", "stress")
    identity = RunIdentity.build(profile="stress", scenario="base", seed=20260831)
    result = CliRunner().invoke(
        app, ["run-id", "stress", "--scenario", "base", "--seed", "20260831"]
    )
    assert result.exit_code == 0
    assert result.stdout.strip() == identity.run_id
    assert identity.generator_version == GENERATOR_VERSION
    assert identity.actual_through == ACTUAL_THROUGH
    assert identity.forecast_from == FORECAST_FROM


def test_required_schema_head_comes_from_alembic_script_directory() -> None:
    config = Config("alembic.ini")
    assert required_schema_head(config) == "0008"


def test_completed_run_identity_is_immutable(tmp_path: Path) -> None:
    engine = create_engine(_migrated_url(tmp_path))
    with Session(engine) as session:
        run = record_generation_run(
            session,
            profile="standard",
            scenario_code="base",
            seed=20260831,
            git_commit="a" * 40,
        )
        run.status = "COMPLETED"
        session.commit()
        completed_at = run.completed_at

        with pytest.raises(ValueError, match="immutable|identity mismatch"):
            record_generation_run(
                session,
                profile="standard",
                scenario_code="base",
                seed=20260831,
                git_commit="b" * 40,
            )
        session.rollback()
        persisted = session.get(GenerationRun, run.id)
        assert persisted is not None
        assert persisted.git_commit == "a" * 40
        assert persisted.completed_at == completed_at


def test_lifecycle_marker_uses_valid_constant_for_every_profile(tmp_path: Path) -> None:
    url = _migrated_url(tmp_path, "var/private/profiles.db")
    profiles = (
        ("standard", "base"),
        ("full_history", "base"),
        ("benchmark_private", "base"),
        ("stress", "base"),
        ("baseline", "base"),
        ("full", "base"),
    )
    runner = CliRunner()
    for profile, scenario in profiles:
        result = runner.invoke(
            app,
            ["generate", "--profile", profile, "--scenario", scenario],
            env={"SHFIN_DATABASE_URL": url},
        )
        assert result.exit_code == 0, result.output
    with Session(create_engine(url)) as session:
        markers = list(
            session.scalars(
                select(ScenarioValue).where(ScenarioValue.metric_code == "run_marker")
            )
        )
        assert len(markers) == len(profiles) + 1  # one common-actual run
        assert {marker.period_code for marker in markers} == {"RUN"}


def test_validation_is_read_only_and_empty_migrated_database_fails(tmp_path: Path) -> None:
    url = _migrated_url(tmp_path)
    engine = create_engine(url)
    before = {
        table: 0
        for table in inspect(engine).get_table_names()
        if table != "alembic_version"
    }
    result = CliRunner().invoke(app, ["validate"], env={"SHFIN_DATABASE_URL": url})
    assert result.exit_code != 0
    with Session(engine) as session:
        after = {
            table: session.scalar(select(func.count()).select_from(inspect_table))
            for table in before
            if (inspect_table := __import__("sqlalchemy").Table(
                table, __import__("sqlalchemy").MetaData(), autoload_with=engine
            )) is not None
        }
    assert after == before


def test_run_context_rejects_incomplete_run(tmp_path: Path) -> None:
    engine = create_engine(_migrated_url(tmp_path))
    with Session(engine) as session:
        run = record_generation_run(
            session,
            profile="standard",
            scenario_code="base",
            seed=20260831,
            git_commit="a" * 40,
        )
        with pytest.raises(ValueError, match="COMPLETED"):
            run_context(session, run.id)


def test_profile_runs_receive_distinct_owned_journals(tmp_path: Path) -> None:
    url = _migrated_url(tmp_path, "var/private/coexist.db")
    runner = CliRunner()
    for profile in ("standard", "full_history", "benchmark_private"):
        result = runner.invoke(
            app,
            ["generate", "--profile", profile, "--scenario", "base"],
            env={"SHFIN_DATABASE_URL": url},
        )
        assert result.exit_code == 0, result.output
    with Session(create_engine(url)) as session:
        runs = list(
            session.scalars(
                select(GenerationRun).where(GenerationRun.profile != "actual_common")
            )
        )
        counts = {
            run.profile: session.scalar(
                select(func.count(JournalEntry.id)).where(
                    JournalEntry.generation_run_id == run.id
                )
            )
            for run in runs
        }
        assert all(count and count > 0 for count in counts.values()), counts
        journal_ids = list(session.scalars(select(JournalEntry.id)))
        assert len(journal_ids) == len(set(journal_ids))
