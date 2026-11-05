from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from sable_harbor import cli
from sable_harbor.accounting.models import EntryState, JournalEntry
from sable_harbor.cli import app
from sable_harbor.core.database import REPOSITORY_ROOT, alembic_config
from sable_harbor.provenance.identity import RunIdentity
from sable_harbor.provenance.models import GenerationRun


def _migrated_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    url = f"sqlite:///{tmp_path / 'nested' / 'cli.db'}"
    # Migrate from an unrelated working directory: the CLI must not depend on CWD.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    result = CliRunner().invoke(app, ["migrate"], env={"SHFIN_DATABASE_URL": url})
    assert result.exit_code == 0, result.output
    return url


def test_alembic_config_is_anchored_at_repository_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = alembic_config("sqlite:///unused.db")
    assert Path(config.config_file_name or "") == REPOSITORY_ROOT / "alembic.ini"
    assert config.get_main_option("script_location") == str(REPOSITORY_ROOT / "db" / "migrations")


def test_post_after_generate_is_a_successful_no_op(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = _migrated_url(tmp_path, monkeypatch)
    runner = CliRunner()
    env = {"SHFIN_DATABASE_URL": url}
    generated = runner.invoke(app, ["generate", "--profile", "smoke", "--seed", "7"], env=env)
    assert generated.exit_code == 0, generated.output
    run_id = RunIdentity.build(profile="smoke", scenario="base", seed=7).run_id

    posted = runner.invoke(app, ["post", "--generation-run-id", run_id], env=env)
    assert posted.exit_code == 0, posted.output
    assert "nothing to post" in posted.output

    with Session(create_engine(url)) as session:
        run = session.get(GenerationRun, run_id)
        assert run is not None and run.status == "COMPLETED"
        assert (
            session.scalar(
                select(JournalEntry.id).where(
                    JournalEntry.generation_run_id == run_id,
                    JournalEntry.state == EntryState.DRAFT,
                )
            )
            is None
        )

    unknown = runner.invoke(app, ["post", "--generation-run-id", "missing"], env=env)
    assert unknown.exit_code == 1
    assert "Unknown generation run" in unknown.output


def test_generate_passes_normalized_scenario_to_generator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = _migrated_url(tmp_path, monkeypatch)
    seen: list[str] = []

    def fake_baseline(session: Session, *, seed: int, scenario: str) -> dict[str, str]:
        seen.append(scenario)
        return {"scenario": scenario}

    monkeypatch.setattr(cli, "generate_baseline_run", fake_baseline)
    result = CliRunner().invoke(
        app,
        ["generate", "--profile", "Baseline", "--scenario", " High ", "--seed", "3"],
        env={"SHFIN_DATABASE_URL": url},
    )
    assert result.exit_code == 0, result.output
    assert seen == ["high"]
    assert "profile=baseline scenario=high" in result.output


def test_generate_rejects_incompatible_scenario_as_bad_parameter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = _migrated_url(tmp_path, monkeypatch)
    result = CliRunner().invoke(
        app,
        ["generate", "--profile", "smoke", "--scenario", "high"],
        env={"SHFIN_DATABASE_URL": url},
    )
    assert result.exit_code == 2
    assert "incompatible" in result.output


@pytest.mark.parametrize("through", ["2026-8", "2026-13", "2026-00", "202608", "2026-08-01", ""])
def test_close_rejects_malformed_period_codes(through: str) -> None:
    result = CliRunner().invoke(
        app,
        ["close", "--through", through, "--generation-run-id", "unused"],
        env={"SHFIN_DATABASE_URL": "sqlite:///:memory:"},
    )
    assert result.exit_code == 2
    assert "YYYY-MM" in result.output
