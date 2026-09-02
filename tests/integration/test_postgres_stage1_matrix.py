import os
from datetime import date

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from sable_harbor.cli import app
from sable_harbor.core.database import build_engine
from sable_harbor.provenance.identity import RunIdentity


def _postgres_url() -> str:
    url = os.getenv("SHFIN_POSTGRES_TEST_URL")
    if not url:
        pytest.skip("SHFIN_POSTGRES_TEST_URL is not configured")
    return url


def _reset_database(url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def _generate(runner: CliRunner, url: str, profile: str, scenario: str, seed: int) -> None:
    result = runner.invoke(
        app,
        [
            "generate",
            "--profile",
            profile,
            "--scenario",
            scenario,
            "--seed",
            str(seed),
        ],
        env={
            "SHFIN_DATABASE_URL": url,
            "SHFIN_PRIVATE_BENCHMARK": "1" if profile == "benchmark_private" else "0",
        },
    )
    assert result.exit_code == 0, result.output


def test_postgres_stage1_profile_coexistence_and_integrity_matrix() -> None:
    url = _postgres_url()
    _reset_database(url)
    runner = CliRunner()

    for profile in (
        "smoke",
        "baseline",
        "standard",
        "full",
        "full_history",
        "benchmark_private",
    ):
        _generate(runner, url, profile, "base", 101)
    for scenario in ("low", "high", "stress"):
        _generate(runner, url, "standard", scenario, 101)
    _generate(runner, url, "standard", "base", 202)

    engine = build_engine(url)
    actual_101 = RunIdentity.build(
        profile="actual_common", scenario="actual_common", seed=101
    ).run_id
    actual_202 = RunIdentity.build(
        profile="actual_common", scenario="actual_common", seed=202
    ).run_id
    base_101 = RunIdentity.build(profile="standard", scenario="base", seed=101).run_id

    with Session(engine) as session:
        identities = session.execute(
            text(
                "SELECT profile, scenario.code, seed, status "
                "FROM generation_run JOIN scenario ON scenario.id = generation_run.scenario_id"
            )
        ).all()
        assert {
            (profile, scenario, 101, "COMPLETED")
            for profile, scenario in (
                ("smoke", "base"),
                ("baseline", "base"),
                ("standard", "base"),
                ("standard", "low"),
                ("standard", "high"),
                ("standard", "stress"),
                ("full", "base"),
                ("full_history", "base"),
                ("benchmark_private", "base"),
            )
        }.issubset(set(identities))
        assert ("standard", "base", 202, "COMPLETED") in identities

        worker_numbers = session.execute(
            text(
                "SELECT worker_number, COUNT(DISTINCT generation_run_id) "
                "FROM worker GROUP BY worker_number "
                "HAVING COUNT(DISTINCT generation_run_id) > 1"
            )
        ).all()
        assert worker_numbers

        with pytest.raises(IntegrityError):
            session.execute(
                text("UPDATE worker SET generation_run_id = NULL WHERE generation_run_id = :run"),
                {"run": actual_101},
            )
            session.commit()
        session.rollback()

        contract_id = session.scalar(
            text("SELECT id FROM contract WHERE generation_run_id = :run LIMIT 1"),
            {"run": actual_101},
        )
        party_id = session.scalar(
            text("SELECT id FROM business_party WHERE generation_run_id = :run LIMIT 1"),
            {"run": actual_202},
        )
        assert contract_id is not None and party_id is not None
        with pytest.raises(IntegrityError):
            session.execute(
                text("UPDATE contract SET party_id = :party WHERE id = :contract"),
                {"party": party_id, "contract": contract_id},
            )
            session.commit()
        session.rollback()

        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "UPDATE generation_run SET actual_generation_run_id = :actual "
                    "WHERE id = :scenario"
                ),
                {"actual": actual_202, "scenario": base_101},
            )
            session.commit()
        session.rollback()

        with pytest.raises(IntegrityError, match="immutable"):
            session.execute(
                text("UPDATE generation_run SET seed = seed + 1 WHERE id = :run"),
                {"run": base_101},
            )
            session.commit()
        session.rollback()

        cutoff_violations = session.scalar(
            text(
                "SELECT COUNT(*) FROM ("
                "SELECT 1 FROM production_record WHERE "
                "(generation_run_id = :actual AND period_code > '2026-08') OR "
                "(generation_run_id = :scenario AND period_code <= '2026-08') "
                "UNION ALL SELECT 1 FROM freight_movement WHERE "
                "(generation_run_id = :actual AND movement_date > :cutoff) OR "
                "(generation_run_id = :scenario AND movement_date <= :cutoff) "
                "UNION ALL SELECT 1 FROM inventory_lot WHERE "
                "(generation_run_id = :actual AND as_of_date > :cutoff) OR "
                "(generation_run_id = :scenario AND as_of_date <= :cutoff)"
                ") AS violations"
            ),
            {
                "actual": actual_101,
                "scenario": base_101,
                "cutoff": date(2026, 8, 31),
            },
        )
        assert cutoff_violations == 0
