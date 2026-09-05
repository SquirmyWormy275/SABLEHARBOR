from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from sable_harbor.accounting.ledger import (
    LedgerError,
    close_period,
    compare_trial_balances,
    post_entry,
    reverse_entry,
    trial_balance,
)
from sable_harbor.accounting.models import (
    AccountingBook,
    FiscalPeriod,
    GenerationPeriodClose,
    JournalEntry,
    JournalLine,
    LegalEntity,
    ScenarioValue,
    Worker,
)
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.cli import app
from sable_harbor.core.database import build_engine, required_schema_head
from sable_harbor.core.ids import stable_id
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.identity import (
    FORECAST_FROM,
    GENERATOR_VERSION,
    SYNTHETIC_CALIBRATION_THROUGH,
    RunIdentity,
    generation_input_manifest,
    generation_input_manifest_digest,
    normalize_profile_scenario,
    repository_head,
)
from sable_harbor.provenance.models import GenerationRun, Scenario
from sable_harbor.provenance.service import lineage_for, record_generation_run, run_context


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
    assert identity.synthetic_calibration_through == SYNTHETIC_CALIBRATION_THROUGH
    assert identity.forecast_from == FORECAST_FROM


def test_required_schema_head_comes_from_alembic_script_directory() -> None:
    config = Config("alembic.ini")
    assert required_schema_head(config) == "0015"


def test_generation_input_manifest_is_complete_portable_and_cwd_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest = generation_input_manifest()
    paths = {item["path"] for item in manifest}
    assert "config/finance/scenarios/operating.yml" in paths
    assert "config/finance/unit_scopes.json" in paths
    assert "config/finance/assumptions/quantitative.yml" in paths
    assert "docs/finance/CANON_SOURCE_LOCK.json" in paths
    assert "docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.md" in paths
    assert "db/sql/entity_trial_balance.sql" in paths
    assert "db/migrations/versions/0009_generation_input_identity.py" in paths
    assert "db/migrations/versions/0010_run_scoped_natural_keys.py" in paths
    assert "src/sable_harbor/generation.py" in paths
    assert all(not Path(path).is_absolute() for path in paths)
    digest = generation_input_manifest_digest()
    monkeypatch.chdir(tmp_path)
    assert generation_input_manifest_digest() == digest


def test_repository_head_is_full_sha_and_caller_cwd_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    expected = repository_head()
    assert len(expected) == 40
    assert set(expected) <= set("0123456789abcdef")
    monkeypatch.chdir(tmp_path)
    assert repository_head() == expected


def test_generation_run_rejects_noncanonical_source_commit(tmp_path: Path) -> None:
    with Session(create_engine(_migrated_url(tmp_path, "invalid-source-commit.db"))) as session:
        with pytest.raises(ValueError, match="full lowercase Git SHA-1"):
            record_generation_run(
                session,
                profile="standard",
                scenario_code="base",
                seed=20260831,
                git_commit="UNKNOWN",
            )


def test_run_identity_is_content_addressed_by_complete_input_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sable_harbor.provenance.identity as identity_module

    monkeypatch.setattr(identity_module, "generation_input_manifest_digest", lambda: "a" * 64)
    first = RunIdentity.build(profile="standard", scenario="base", seed=20260831)
    monkeypatch.setattr(identity_module, "generation_input_manifest_digest", lambda: "b" * 64)
    second = RunIdentity.build(profile="standard", scenario="base", seed=20260831)

    assert first.run_id != second.run_id
    assert first.build_id != second.build_id
    assert first.synthetic_calibration_dataset_id != second.synthetic_calibration_dataset_id
    assert first.input_manifest_digest == "a" * 64
    assert second.input_manifest_digest == "b" * 64


def test_profile_contract_rejects_unknown_and_incompatible_requests() -> None:
    smoke = RunIdentity.build(profile="smoke", scenario="base", seed=1)
    assert (smoke.profile, smoke.scenario) == ("smoke", "base")
    with pytest.raises(ValueError, match="Unknown generation profile"):
        RunIdentity.build(profile="typo", scenario="base", seed=1)
    with pytest.raises(ValueError, match="incompatible"):
        RunIdentity.build(profile="synthetic_common", scenario="base", seed=1)
    with pytest.raises(ValueError, match="incompatible"):
        RunIdentity.build(profile="smoke", scenario="stress", seed=1)


@pytest.mark.parametrize(
    ("arguments", "database_name"),
    ((["generate"], "default-smoke.db"), (["generate", "--profile", "smoke"], "smoke.db")),
)
def test_cli_generates_owned_smoke_base_run(
    tmp_path: Path, arguments: list[str], database_name: str
) -> None:
    url = _migrated_url(tmp_path, database_name)
    result = CliRunner().invoke(app, arguments, env={"SHFIN_DATABASE_URL": url})
    assert result.exit_code == 0, result.output
    assert "profile=smoke scenario=base seed=20260831" in result.output

    identity = RunIdentity.build(profile="smoke", scenario="base", seed=20260831)
    with Session(create_engine(url)) as session:
        run = session.get(GenerationRun, identity.run_id)
        assert run is not None
        scenario = session.get(Scenario, run.scenario_id)
        assert scenario is not None
        assert (run.profile, scenario.code, run.seed, run.status) == (
            "smoke",
            "base",
            20260831,
            "COMPLETED",
        )
        assert session.scalar(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.generation_run_id == identity.run_id
            )
        )


def test_completed_content_addressed_run_can_be_resolved_from_a_later_commit(
    tmp_path: Path,
) -> None:
    engine = create_engine(_migrated_url(tmp_path))
    with Session(engine) as session:
        run = record_generation_run(
            session,
            profile="standard",
            scenario_code="base",
            seed=20260831,
            git_commit="a" * 40,
        )
        from sable_harbor.provenance.service import complete_generation_run

        complete_generation_run(session, run)
        session.commit()
        completed_at = run.completed_at

        resolved = record_generation_run(
            session,
            profile="standard",
            scenario_code="base",
            seed=20260831,
            git_commit="b" * 40,
        )
        assert resolved.id == run.id
        persisted = session.get(GenerationRun, run.id)
        assert persisted is not None
        assert persisted.git_commit == "a" * 40
        assert persisted.completed_at == completed_at


def test_content_addressed_builds_coexist_in_one_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import sable_harbor.provenance.identity as identity_module

    engine = create_engine(_migrated_url(tmp_path, "content-builds.db"))
    with Session(engine) as session:
        monkeypatch.setattr(identity_module, "generation_input_manifest_digest", lambda: "a" * 64)
        first = record_generation_run(
            session,
            profile="standard",
            scenario_code="base",
            seed=20260831,
            git_commit="a" * 40,
        )
        from sable_harbor.provenance.service import complete_generation_run

        complete_generation_run(session, first)
        session.commit()

        monkeypatch.setattr(identity_module, "generation_input_manifest_digest", lambda: "b" * 64)
        second = record_generation_run(
            session,
            profile="standard",
            scenario_code="base",
            seed=20260831,
            git_commit="a" * 40,
        )
        session.commit()

        assert first.id != second.id
        assert first.build_id != second.build_id
        assert session.scalar(select(func.count(GenerationRun.id))) == 2


def test_lifecycle_marker_uses_valid_constant_for_every_profile(tmp_path: Path) -> None:
    url = _migrated_url(tmp_path, "var/private/profiles.db")
    profiles = (
        ("standard", "base"),
        ("full_history", "base"),
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
            session.scalars(select(ScenarioValue).where(ScenarioValue.metric_code == "run_marker"))
        )
        assert len(markers) == len(profiles) + 1  # one shared synthetic calibration run
        assert {marker.period_code for marker in markers} == {"RUN"}


def test_validation_is_read_only_and_empty_migrated_database_fails(tmp_path: Path) -> None:
    url = _migrated_url(tmp_path)
    engine = build_engine(url)
    before = {table: 0 for table in inspect(engine).get_table_names() if table != "alembic_version"}
    result = CliRunner().invoke(app, ["validate"], env={"SHFIN_DATABASE_URL": url})
    assert result.exit_code != 0
    with Session(engine) as session:
        after = {
            table: session.scalar(select(func.count()).select_from(inspect_table))
            for table in before
            if (
                inspect_table := __import__("sqlalchemy").Table(
                    table, __import__("sqlalchemy").MetaData(), autoload_with=engine
                )
            )
            is not None
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


def test_completed_lifecycle_transition_is_idempotent_and_cannot_rewrite_time(
    tmp_path: Path,
) -> None:
    engine = create_engine(_migrated_url(tmp_path))
    with Session(engine) as session:
        run = record_generation_run(
            session,
            profile="standard",
            scenario_code="base",
            seed=20260831,
            git_commit="a" * 40,
        )
        from sable_harbor.provenance.service import complete_generation_run

        complete_generation_run(session, run)
        completed_at = run.completed_at
        complete_generation_run(session, run)
        assert run.completed_at == completed_at


def test_baseline_and_standard_profile_order_produces_identical_standard_results(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    seed = 41
    snapshots: list[tuple[int, int, Decimal, Decimal]] = []
    for name, profiles in (
        ("baseline-first.db", ("baseline", "standard")),
        ("standard-first.db", ("standard", "baseline")),
    ):
        url = _migrated_url(tmp_path, name)
        for profile in profiles:
            result = runner.invoke(
                app,
                ["generate", "--profile", profile, "--scenario", "base", "--seed", str(seed)],
                env={"SHFIN_DATABASE_URL": url},
            )
            assert result.exit_code == 0, result.output

        actual_run_id = RunIdentity.build(
            profile="synthetic_common", scenario="synthetic_common", seed=seed
        ).run_id
        standard_run_id = RunIdentity.build(profile="standard", scenario="base", seed=seed).run_id
        engine = create_engine(url)
        with Session(engine) as session:
            actual_run = session.get(GenerationRun, actual_run_id)
            assert actual_run is not None
            assert actual_run.status == "COMPLETED"
            snapshots.append(
                (
                    session.scalar(
                        select(func.count(JournalEntry.id)).where(
                            JournalEntry.generation_run_id == actual_run_id
                        )
                    )
                    or 0,
                    session.scalar(
                        select(func.count(JournalEntry.id)).where(
                            JournalEntry.generation_run_id == standard_run_id
                        )
                    )
                    or 0,
                    session.scalar(
                        select(func.coalesce(func.sum(JournalLine.debit), 0))
                        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
                        .where(JournalEntry.generation_run_id == actual_run_id)
                    ),
                    session.scalar(
                        select(func.coalesce(func.sum(JournalLine.debit), 0))
                        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
                        .where(JournalEntry.generation_run_id == standard_run_id)
                    ),
                )
            )

    assert snapshots[0] == snapshots[1]


@pytest.mark.parametrize(
    ("column", "value"),
    (
        ("seed", "2"),
        ("generator_source_digest", "'changed'"),
        ("assumptions_digest", "'changed'"),
        ("canon_source_lock_digest", "'changed'"),
        ("started_at", "'2000-01-01 00:00:00'"),
    ),
)
def test_database_rejects_invalid_lifecycle_and_completed_identity_mutation(
    tmp_path: Path, column: str, value: str
) -> None:
    engine = create_engine(_migrated_url(tmp_path, "lifecycle.db"))
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="base", seed=1, git_commit="a" * 40
        )
        session.commit()
        with pytest.raises(IntegrityError):
            session.execute(
                text("UPDATE generation_run SET status='COMPLETED' WHERE id=:id"), {"id": run.id}
            )
            session.commit()
        session.rollback()

        from sable_harbor.provenance.service import complete_generation_run

        run = session.get(GenerationRun, run.id)
        assert run is not None
        complete_generation_run(session, run)
        session.commit()
        with pytest.raises(IntegrityError, match="immutable"):
            session.execute(
                text(f"UPDATE generation_run SET {column}={value} WHERE id=:id"),
                {"id": run.id},
            )
            session.commit()


def test_database_freezes_completed_content_and_rejects_running_cross_run_links(
    tmp_path: Path,
) -> None:
    url = _migrated_url(tmp_path, "ownership.db")
    runner = CliRunner()
    for seed in (1, 2):
        result = runner.invoke(
            app,
            ["generate", "--profile", "standard", "--seed", str(seed)],
            env={"SHFIN_DATABASE_URL": url},
        )
        assert result.exit_code == 0, result.output
    engine = build_engine(url)
    with Session(engine) as session:
        completed_actual = RunIdentity.build(
            profile="synthetic_common", scenario="synthetic_common", seed=1
        ).run_id
        with pytest.raises(IntegrityError, match="immutable"):
            session.execute(
                text("UPDATE worker SET function_code=function_code WHERE generation_run_id=:run"),
                {"run": completed_actual},
            )
            session.commit()
        session.rollback()

        running_ids: list[str] = []
        for scenario_code in ("base", "stress"):
            running = record_generation_run(
                session,
                profile="standard",
                scenario_code=scenario_code,
                seed=3,
                git_commit="a" * 40,
            )
            generate_standard(session, seed=3, scenario=scenario_code)
            session.commit()
            running_ids.append(running.id)
        first_contract = session.execute(
            text("SELECT id FROM customer_contract WHERE generation_run_id=:run LIMIT 1"),
            {"run": running_ids[0]},
        ).scalar_one()
        second_customer = session.execute(
            text("SELECT id FROM customer WHERE generation_run_id=:run LIMIT 1"),
            {"run": running_ids[1]},
        ).scalar_one()
        with pytest.raises(IntegrityError):
            session.execute(
                text("UPDATE customer_contract SET customer_id=:customer WHERE id=:contract"),
                {"customer": second_customer, "contract": first_contract},
            )
            session.commit()
        session.rollback()

        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "UPDATE generation_run SET actual_generation_run_id=:actual WHERE id=:scenario"
                ),
                {
                    "actual": RunIdentity.build(
                        profile="synthetic_common", scenario="synthetic_common", seed=2
                    ).run_id,
                    "scenario": running_ids[0],
                },
            )
            session.commit()


def test_database_enforces_posted_journal_integrity_while_run_is_running(
    tmp_path: Path,
) -> None:
    engine = build_engine(_migrated_url(tmp_path, "posted-journal-integrity.db"))
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        session.commit()
        posted = session.scalar(select(JournalEntry).where(JournalEntry.state == "POSTED"))
        period_id = session.scalar(select(FiscalPeriod.id).where(FiscalPeriod.book_id == book_id))
        cash_id = session.scalar(
            select(JournalLine.account_id).where(JournalLine.entry_id == posted.id)
        )
        assert posted is not None and period_id is not None and cash_id is not None
        posted_id = posted.id
        posted_line_id = posted.lines[0].id
        run_id = posted.generation_run_id

        for statement in (
            "UPDATE journal_entry SET description='tampered' WHERE id=:id",
            "DELETE FROM journal_entry WHERE id=:id",
        ):
            with pytest.raises(IntegrityError, match="posted journal entries are immutable"):
                session.execute(text(statement), {"id": posted_id})
                session.commit()
            session.rollback()
        for statement in (
            "UPDATE journal_line SET segment_code='tampered' WHERE id=:id",
            "DELETE FROM journal_line WHERE id=:id",
        ):
            with pytest.raises(IntegrityError, match="journal content is immutable"):
                session.execute(text(statement), {"id": posted_line_id})
                session.commit()
            session.rollback()

        with pytest.raises(IntegrityError, match="inserted as drafts"):
            session.execute(
                text(
                    "INSERT INTO journal_entry "
                    "(id, generation_run_id, book_id, period_id, entry_date, description, "
                    "source_type, source_id, state, posted_at) VALUES "
                    "(:id, :run, :book, :period, '2026-08-15', 'direct posted bypass', "
                    "'test', 'direct-posted', 'POSTED', CURRENT_TIMESTAMP)"
                ),
                {
                    "id": stable_id("journal", "DIRECT-POSTED-BYPASS"),
                    "run": run_id,
                    "book": book_id,
                    "period": period_id,
                },
            )
            session.commit()
        session.rollback()

        draft_id = stable_id("journal", "DIRECT-UNBALANCED-DRAFT")
        session.execute(
            text(
                "INSERT INTO journal_entry "
                "(id, generation_run_id, book_id, period_id, entry_date, description, "
                "source_type, source_id, state, posted_at) VALUES "
                "(:id, :run, :book, :period, '2026-08-15', 'direct draft', "
                "'test', 'direct-draft', 'DRAFT', NULL)"
            ),
            {"id": draft_id, "run": run_id, "book": book_id, "period": period_id},
        )
        session.execute(
            text(
                "INSERT INTO journal_line "
                "(id, entry_id, account_id, debit, credit, transaction_currency, "
                "functional_amount, reporting_amount, fact_state) VALUES "
                "(:id, :entry, :account, 1, 0, 'USD', 1, 1, 'DERIVED')"
            ),
            {
                "id": stable_id("journal_line", "DIRECT-UNBALANCED-DRAFT:1"),
                "entry": draft_id,
                "account": cash_id,
            },
        )
        session.commit()
        with pytest.raises(IntegrityError, match="balanced and nonzero"):
            session.execute(
                text(
                    "UPDATE journal_entry SET state='POSTED', posted_at=CURRENT_TIMESTAMP "
                    "WHERE id=:id"
                ),
                {"id": draft_id},
            )
            session.commit()


def test_two_seeds_coexist_with_run_scoped_operational_natural_keys(tmp_path: Path) -> None:
    url = _migrated_url(tmp_path, "two-seeds.db")
    runner = CliRunner()
    seeds = (20260831, 20260901)
    for seed in seeds:
        result = runner.invoke(
            app,
            ["generate", "--profile", "standard", "--scenario", "base", "--seed", str(seed)],
            env={"SHFIN_DATABASE_URL": url},
        )
        assert result.exit_code == 0, result.output

    actual_ids = tuple(
        RunIdentity.build(profile="synthetic_common", scenario="synthetic_common", seed=seed).run_id
        for seed in seeds
    )
    with Session(create_engine(url)) as session:
        assert (
            session.scalar(
                select(func.count(Worker.id)).where(Worker.generation_run_id.in_(actual_ids))
            )
            == 2 * 769
        )
        for worker_number in ("SHW-00001", "SHC-00001"):
            assert (
                session.scalar(
                    select(func.count(Worker.id)).where(
                        Worker.generation_run_id.in_(actual_ids),
                        Worker.worker_number == worker_number,
                    )
                )
                == 2
            )
        for seed, actual_id in zip(seeds, actual_ids, strict=True):
            selected_id = RunIdentity.build(profile="standard", scenario="base", seed=seed).run_id
            selected = session.get(GenerationRun, selected_id)
            assert selected is not None
            assert selected.actual_generation_run_id == actual_id

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.downgrade(config, "0014")
    with create_engine(url).begin() as connection:
        connection.execute(
            text("UPDATE scenario_value SET period_code = substr(period_code, 1, 16)")
        )
    with pytest.raises(RuntimeError, match="Cannot downgrade revision 0010"):
        command.downgrade(config, "0009")
    with Session(create_engine(url)) as session:
        # Each selected forecast run adds four explicitly run-owned monthly
        # payroll-cohort workers in addition to its 769 shared calibration workers.
        assert session.scalar(select(func.count(Worker.id))) == 2 * (769 + 4)
    assert inspect(create_engine(url)).get_unique_constraints("worker") == [
        {
            "name": "uq_worker_generation_run_id",
            "column_names": ["generation_run_id", "worker_number"],
        }
    ]


def test_profile_runs_receive_distinct_owned_journals(tmp_path: Path) -> None:
    url = _migrated_url(tmp_path, "var/private/coexist.db")
    runner = CliRunner()
    for profile in ("standard", "full_history"):
        result = runner.invoke(
            app,
            ["generate", "--profile", profile, "--scenario", "base"],
            env={"SHFIN_DATABASE_URL": url},
        )
        assert result.exit_code == 0, result.output
    with Session(create_engine(url)) as session:
        runs = list(
            session.scalars(
                select(GenerationRun).where(GenerationRun.profile != "synthetic_common")
            )
        )
        counts = {
            run.profile: session.scalar(
                select(func.count(JournalEntry.id)).where(JournalEntry.generation_run_id == run.id)
            )
            for run in runs
        }
        assert all(count and count > 0 for count in counts.values()), counts
        journal_ids = list(session.scalars(select(JournalEntry.id)))
        assert len(journal_ids) == len(set(journal_ids))


def test_accounting_lineage_and_close_apis_isolate_coexisting_runs(tmp_path: Path) -> None:
    url = _migrated_url(tmp_path, "scoped-apis.db")
    runner = CliRunner()
    run_ids = []
    for seed in (1, 2):
        result = runner.invoke(
            app,
            ["generate", "--profile", "standard", "--seed", str(seed)],
            env={"SHFIN_DATABASE_URL": url},
        )
        assert result.exit_code == 0, result.output
        run_ids.append(RunIdentity.build(profile="standard", scenario="base", seed=seed).run_id)

    with Session(create_engine(url)) as session:
        book_id = session.scalar(select(AccountingBook.id))
        period = session.scalar(
            select(FiscalPeriod)
            .join(JournalEntry, JournalEntry.period_id == FiscalPeriod.id)
            .where(JournalEntry.generation_run_id == run_ids[0])
        )
        assert book_id is not None and period is not None

        with pytest.raises(ValueError, match="explicit generation run"):
            trial_balance(session, book_id)
        for run_id in run_ids:
            balances = trial_balance(session, book_id, run_id)
            expected = session.execute(
                select(func.sum(JournalLine.debit), func.sum(JournalLine.credit))
                .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
                .where(
                    JournalEntry.book_id == book_id,
                    JournalEntry.generation_run_id.in_(
                        run_context(session, run_id).included_run_ids
                    ),
                )
            ).one()
            assert (sum(row[1] for row in balances), sum(row[2] for row in balances)) == expected

        source_entries = [
            session.scalar(select(JournalEntry).where(JournalEntry.generation_run_id == run_id))
            for run_id in run_ids
        ]
        assert all(entry is not None for entry in source_entries)
        first_entry, second_entry = source_entries
        assert first_entry is not None and second_entry is not None
        assert lineage_for(session, first_entry.id, run_ids[0])
        assert not lineage_for(session, first_entry.id, run_ids[1])
        assert lineage_for(session, second_entry.id, run_ids[1])
        assert not lineage_for(session, second_entry.id, run_ids[0])

        close_period(session, period, run_ids[0])
        session.flush()
        first_context = run_context(session, run_ids[0])
        assert all(
            session.get(GenerationPeriodClose, (run_id, period.id)) is not None
            for run_id in first_context.included_run_ids
        )
        assert session.get(GenerationPeriodClose, (run_ids[1], period.id)) is None

        # Generated lineage is part of the completed evidence set. The test
        # consumes the seeded edges instead of appending post-completion data.


def test_cli_close_ignores_unreferenced_global_periods(tmp_path: Path) -> None:
    url = _migrated_url(tmp_path, "close-period-scope.db")
    runner = CliRunner()
    generation = runner.invoke(
        app,
        ["generate", "--profile", "standard", "--seed", "19"],
        env={"SHFIN_DATABASE_URL": url},
    )
    assert generation.exit_code == 0, generation.output
    selected_run_id = RunIdentity.build(profile="standard", scenario="base", seed=19).run_id

    engine = create_engine(url)
    with Session(engine) as session:
        shi_id = session.scalar(select(LegalEntity.id).where(LegalEntity.code == "SHI"))
        assert shi_id is not None
        unrelated_book = AccountingBook(
            id=stable_id("book", "SHI:UNRELATED_TEST_USD"),
            entity_id=shi_id,
            code="UNRELATED_TEST_USD",
            currency="USD",
        )
        unrelated_period = FiscalPeriod(
            id=stable_id("period", f"{unrelated_book.id}:2026-11"),
            book_id=unrelated_book.id,
            code="2026-11",
            starts_on=date(2026, 11, 1),
            ends_on=date(2026, 11, 30),
        )
        session.add_all([unrelated_book, unrelated_period])
        session.commit()
        context = run_context(session, selected_run_id)
        with pytest.raises(LedgerError, match="not referenced"):
            close_period(session, unrelated_period, selected_run_id)

    closing = runner.invoke(
        app,
        [
            "close",
            "--through",
            "2026-12",
            "--generation-run-id",
            selected_run_id,
        ],
        env={"SHFIN_DATABASE_URL": url},
    )
    assert closing.exit_code == 0, closing.output

    with Session(engine) as session:
        context = run_context(session, selected_run_id)
        assert all(
            session.get(GenerationPeriodClose, (run_id, unrelated_period.id)) is None
            for run_id in context.included_run_ids
        )
        relevant_period_ids = set(
            session.scalars(
                select(JournalEntry.period_id)
                .join(FiscalPeriod, FiscalPeriod.id == JournalEntry.period_id)
                .where(
                    FiscalPeriod.code <= "2026-12",
                    JournalEntry.generation_run_id.in_(context.included_run_ids),
                )
                .distinct()
            )
        )
        assert relevant_period_ids
        assert all(
            session.get(GenerationPeriodClose, (run_id, period_id)) is not None
            for run_id in context.included_run_ids
            for period_id in relevant_period_ids
        )


def test_period_close_evidence_is_immutable_in_orm_and_database(tmp_path: Path) -> None:
    engine = build_engine(_migrated_url(tmp_path, "immutable-period-close.db"))
    with Session(engine) as session:
        seed_smoke(session)
        period = session.query(FiscalPeriod).one()
        close_period(session, period)
        session.commit()

        marker = session.query(GenerationPeriodClose).one()
        marker.closed_at += timedelta(seconds=1)
        with pytest.raises(LedgerError, match="Period-close evidence is immutable"):
            session.flush()
        session.rollback()

        marker = session.query(GenerationPeriodClose).one()
        session.delete(marker)
        with pytest.raises(LedgerError, match="Period-close evidence is immutable"):
            session.flush()
        session.rollback()

        marker = session.query(GenerationPeriodClose).one()
        with pytest.raises(IntegrityError, match="period-close evidence is immutable"):
            session.execute(
                text(
                    "UPDATE generation_period_close SET closed_at=:closed_at "
                    "WHERE generation_run_id=:run_id AND period_id=:period_id"
                ),
                {
                    "closed_at": marker.closed_at + timedelta(seconds=1),
                    "run_id": marker.generation_run_id,
                    "period_id": marker.period_id,
                },
            )
            session.commit()
        session.rollback()

        with pytest.raises(IntegrityError, match="period-close evidence is immutable"):
            session.execute(
                text(
                    "DELETE FROM generation_period_close "
                    "WHERE generation_run_id=:run_id AND period_id=:period_id"
                ),
                {
                    "run_id": marker.generation_run_id,
                    "period_id": marker.period_id,
                },
            )
            session.commit()


def test_0012_preserves_legacy_closed_periods_across_upgrade_and_downgrade(
    tmp_path: Path,
) -> None:
    url = _migrated_url(tmp_path, "legacy-period-close.db")
    result = CliRunner().invoke(
        app,
        ["generate", "--profile", "standard", "--scenario", "base", "--seed", "31"],
        env={"SHFIN_DATABASE_URL": url},
    )
    assert result.exit_code == 0, result.output
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.downgrade(config, "0014")
    # This test isolates revision 0012 behavior; make the populated fixture
    # representable in its historical 16-character period-code schema first.
    with create_engine(url).begin() as connection:
        connection.execute(
            text("UPDATE scenario_value SET period_code = substr(period_code, 1, 16)")
        )
    command.downgrade(config, "0011")

    engine = create_engine(url)
    with engine.begin() as connection:
        period_id = connection.scalar(
            text("SELECT period_id FROM journal_entry ORDER BY id LIMIT 1")
        )
        assert period_id is not None
        connection.execute(
            text("UPDATE fiscal_period SET state = 'CLOSED' WHERE id = :period_id"),
            {"period_id": period_id},
        )

    command.upgrade(config, "0012")
    with Session(engine) as session:
        run_count = session.scalar(select(func.count(GenerationRun.id)))
        marker_count = session.scalar(
            select(func.count(GenerationPeriodClose.generation_run_id)).where(
                GenerationPeriodClose.period_id == period_id
            )
        )
        assert run_count == marker_count
        assert marker_count and marker_count > 0

    command.downgrade(config, "0011")
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT state FROM fiscal_period WHERE id = :period_id"),
                {"period_id": period_id},
            )
            == "CLOSED"
        )

    command.upgrade(config, "0012")
    with engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM generation_period_close "
                "WHERE generation_run_id = "
                "(SELECT generation_run_id FROM generation_period_close LIMIT 1)"
            )
        )
    with pytest.raises(RuntimeError, match="cannot be represented"):
        command.downgrade(config, "0011")


def test_sibling_scenarios_can_close_a_period_with_shared_actuals(tmp_path: Path) -> None:
    url = _migrated_url(tmp_path, "sibling-scenario-close.db")
    runner = CliRunner()
    seed = 17
    run_ids = {
        scenario: RunIdentity.build(profile="standard", scenario=scenario, seed=seed).run_id
        for scenario in ("base", "stress")
    }
    for scenario in run_ids:
        result = runner.invoke(
            app,
            [
                "generate",
                "--profile",
                "standard",
                "--scenario",
                scenario,
                "--seed",
                str(seed),
            ],
            env={"SHFIN_DATABASE_URL": url},
        )
        assert result.exit_code == 0, result.output

    with Session(create_engine(url)) as session:
        contexts = {scenario: run_context(session, run_id) for scenario, run_id in run_ids.items()}
        shared_actual_id = session.get(GenerationRun, run_ids["base"]).actual_generation_run_id
        assert shared_actual_id is not None
        assert (
            session.get(GenerationRun, run_ids["stress"]).actual_generation_run_id
            == shared_actual_id
        )
        period = session.scalar(
            select(FiscalPeriod)
            .join(JournalEntry, JournalEntry.period_id == FiscalPeriod.id)
            .where(JournalEntry.generation_run_id == shared_actual_id)
        )
        assert period is not None

        close_period(session, period, run_ids["base"])
        session.flush()
        original_actual_close = session.get(GenerationPeriodClose, (shared_actual_id, period.id))
        assert original_actual_close is not None
        original_closed_at = original_actual_close.closed_at

        close_period(session, period, run_ids["stress"])
        session.flush()
        assert all(
            session.get(GenerationPeriodClose, (run_id, period.id)) is not None
            for context in contexts.values()
            for run_id in context.included_run_ids
        )
        assert (
            session.get(GenerationPeriodClose, (shared_actual_id, period.id)).closed_at
            == original_closed_at
        )

        close_period(session, period, run_ids["stress"])
        session.flush()
        assert (
            session.scalar(
                select(func.count(GenerationPeriodClose.generation_run_id)).where(
                    GenerationPeriodClose.period_id == period.id,
                    GenerationPeriodClose.generation_run_id.in_(
                        contexts["base"].included_run_ids + contexts["stress"].included_run_ids
                    ),
                )
            )
            == 3
        )


def test_trial_balance_comparison_requires_compatible_explicit_runs(tmp_path: Path) -> None:
    url = _migrated_url(tmp_path, "scenario-comparison.db")
    runner = CliRunner()
    seed = 29
    run_ids = {
        scenario: RunIdentity.build(profile="standard", scenario=scenario, seed=seed).run_id
        for scenario in ("base", "stress")
    }
    for scenario in run_ids:
        result = runner.invoke(
            app,
            [
                "generate",
                "--profile",
                "standard",
                "--scenario",
                scenario,
                "--seed",
                str(seed),
            ],
            env={"SHFIN_DATABASE_URL": url},
        )
        assert result.exit_code == 0, result.output

    incompatible_id = RunIdentity.build(profile="standard", scenario="base", seed=30).run_id
    result = runner.invoke(
        app,
        ["generate", "--profile", "standard", "--seed", "30"],
        env={"SHFIN_DATABASE_URL": url},
    )
    assert result.exit_code == 0, result.output

    with Session(create_engine(url)) as session:
        book_id = session.scalar(
            select(AccountingBook.id)
            .join(LegalEntity, LegalEntity.id == AccountingBook.entity_id)
            .where(AccountingBook.code == "PRIMARY_USD", LegalEntity.code == "SHI")
        )
        assert book_id is not None
        rows = compare_trial_balances(session, book_id, run_ids["base"], run_ids["stress"])
        assert rows
        assert any(debit_delta != 0 or credit_delta != 0 for *_, debit_delta, credit_delta in rows)
        with pytest.raises(ValueError, match="distinct"):
            compare_trial_balances(session, book_id, run_ids["base"], run_ids["base"])
        with pytest.raises(ValueError, match="same profile, synthetic calibration dataset"):
            compare_trial_balances(session, book_id, run_ids["base"], incompatible_id)


@pytest.mark.parametrize(
    ("changed_field", "changed_value"),
    (
        ("profile", "baseline"),
        ("seed", 42),
        ("actual_dataset_id", stable_id("actual_dataset", "comparison-mismatch")),
        ("actual_through", date(2026, 7, 31)),
        ("forecast_from", date(2026, 8, 1)),
        ("schema_head", "incompatible-head"),
    ),
)
def test_trial_balance_comparison_rejects_each_context_mismatch(
    tmp_path: Path, changed_field: str, changed_value: object
) -> None:
    url = _migrated_url(tmp_path, f"comparison-{changed_field}.db")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["generate", "--profile", "standard", "--scenario", "base", "--seed", "41"],
        env={"SHFIN_DATABASE_URL": url},
    )
    assert result.exit_code == 0, result.output
    source_id = RunIdentity.build(profile="standard", scenario="base", seed=41).run_id

    with Session(create_engine(url)) as session:
        source = session.get(GenerationRun, source_id)
        assert source is not None
        comparison_id = stable_id("generation_run", f"comparison:{changed_field}")
        values = {
            "profile": source.profile,
            "seed": source.seed,
            "actual_dataset_id": source.actual_dataset_id,
            "actual_through": source.actual_through,
            "forecast_from": source.forecast_from,
            "schema_head": source.schema_head,
        }
        values[changed_field] = changed_value
        session.add(
            GenerationRun(
                id=comparison_id,
                profile=values["profile"],
                scenario_id=source.scenario_id,
                actual_generation_run_id=None,
                actual_dataset_id=values["actual_dataset_id"],
                build_id=stable_id("build", f"comparison:{changed_field}"),
                input_manifest_digest=source.input_manifest_digest,
                seed=values["seed"],
                generator_version=source.generator_version,
                git_commit=source.git_commit,
                generator_source_digest=source.generator_source_digest,
                assumptions_digest=source.assumptions_digest,
                canon_source_lock_digest=source.canon_source_lock_digest,
                actual_through=values["actual_through"],
                forecast_from=values["forecast_from"],
                schema_head=values["schema_head"],
                started_at=source.started_at,
                completed_at=source.completed_at,
                status="COMPLETED",
            )
        )
        session.flush()
        book_id = session.scalar(select(AccountingBook.id).order_by(AccountingBook.code))
        assert book_id is not None
        with pytest.raises(ValueError, match="same profile, synthetic calibration dataset"):
            compare_trial_balances(session, book_id, source_id, comparison_id)


def test_trial_balance_comparison_rejects_incomplete_run(tmp_path: Path) -> None:
    url = _migrated_url(tmp_path, "comparison-incomplete.db")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["generate", "--profile", "standard", "--scenario", "base", "--seed", "43"],
        env={"SHFIN_DATABASE_URL": url},
    )
    assert result.exit_code == 0, result.output
    completed_id = RunIdentity.build(profile="standard", scenario="base", seed=43).run_id

    with Session(create_engine(url)) as session:
        incomplete = record_generation_run(
            session,
            profile="standard",
            scenario_code="stress",
            seed=43,
            git_commit="a" * 40,
        )
        book_id = session.scalar(select(AccountingBook.id).order_by(AccountingBook.code))
        assert book_id is not None
        with pytest.raises(ValueError, match="must be COMPLETED"):
            compare_trial_balances(session, book_id, completed_id, incomplete.id)


def test_posting_and_reversal_reject_incompatible_active_run_context(tmp_path: Path) -> None:
    url = _migrated_url(tmp_path, "posting-context.db")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["generate", "--profile", "smoke", "--seed", "1"],
        env={"SHFIN_DATABASE_URL": url},
    )
    assert result.exit_code == 0, result.output

    with Session(create_engine(url)) as session:
        template = session.scalar(select(JournalEntry).where(JournalEntry.state == "POSTED"))
        assert template is not None
        owner = record_generation_run(
            session, profile="smoke", scenario_code="base", seed=2, git_commit="a" * 40
        )
        active = record_generation_run(
            session, profile="smoke", scenario_code="base", seed=3, git_commit="a" * 40
        )
        session.info["generation_run_id"] = owner.id
        original = JournalEntry(
            id=stable_id("incompatible_original", owner.id),
            generation_run_id=owner.id,
            book_id=template.book_id,
            period_id=template.period_id,
            entry_date=template.entry_date,
            description="posted before context switch",
            source_type="test",
            source_id="context-original",
            lines=[
                JournalLine(
                    id=stable_id("incompatible_original_line", "1"),
                    account_id=template.lines[0].account_id,
                    debit=Decimal("1"),
                    credit=Decimal("0"),
                    functional_amount=Decimal("1"),
                    reporting_amount=Decimal("1"),
                    fact_state=template.lines[0].fact_state,
                ),
                JournalLine(
                    id=stable_id("incompatible_original_line", "2"),
                    account_id=template.lines[1].account_id,
                    debit=Decimal("0"),
                    credit=Decimal("1"),
                    functional_amount=Decimal("-1"),
                    reporting_amount=Decimal("-1"),
                    fact_state=template.lines[1].fact_state,
                ),
            ],
        )
        session.add(original)
        post_entry(session, original)
        session.info["generation_run_id"] = active.id
        incompatible = JournalEntry(
            id=stable_id("incompatible_post", owner.id),
            generation_run_id=owner.id,
            book_id=original.book_id,
            period_id=original.period_id,
            entry_date=original.entry_date,
            description="cross-run write",
            source_type="test",
            source_id="cross-run",
            lines=[
                JournalLine(
                    id=stable_id("incompatible_post_line", "1"),
                    account_id=original.lines[0].account_id,
                    debit=Decimal("1"),
                    credit=Decimal("0"),
                    functional_amount=Decimal("1"),
                    reporting_amount=Decimal("1"),
                    fact_state=original.lines[0].fact_state,
                ),
                JournalLine(
                    id=stable_id("incompatible_post_line", "2"),
                    account_id=original.lines[1].account_id,
                    debit=Decimal("0"),
                    credit=Decimal("1"),
                    functional_amount=Decimal("-1"),
                    reporting_amount=Decimal("-1"),
                    fact_state=original.lines[1].fact_state,
                ),
            ],
        )
        session.add(incompatible)
        with pytest.raises(LedgerError, match="incompatible"):
            post_entry(session, incompatible)
        session.expunge(incompatible)

        with pytest.raises(LedgerError, match="incompatible"):
            reverse_entry(
                session,
                original,
                original.entry_date,
                original.period_id,
                stable_id("incompatible_reversal", original.id),
            )


def test_post_command_requires_run_and_leaves_unrelated_drafts_untouched(
    tmp_path: Path,
) -> None:
    url = _migrated_url(tmp_path, "scoped-post-command.db")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["generate", "--profile", "smoke", "--seed", "10"],
        env={"SHFIN_DATABASE_URL": url},
    )
    assert result.exit_code == 0, result.output

    draft_ids: list[str] = []
    run_ids: list[str] = []
    with Session(create_engine(url)) as session:
        source = session.scalar(select(JournalEntry).where(JournalEntry.state == "POSTED"))
        assert source is not None
        for seed in (11, 12):
            run = record_generation_run(
                session,
                profile="smoke",
                scenario_code="base",
                seed=seed,
                git_commit="a" * 40,
            )
            run_id = run.id
            run_ids.append(run_id)
            draft_id = stable_id("scoped_post_command", run_id)
            draft_ids.append(draft_id)
            session.add(
                JournalEntry(
                    id=draft_id,
                    generation_run_id=run_id,
                    book_id=source.book_id,
                    period_id=source.period_id,
                    entry_date=source.entry_date,
                    description="run-scoped posting regression",
                    source_type="test",
                    source_id=draft_id,
                    lines=[
                        JournalLine(
                            id=stable_id("scoped_post_command_line", f"{run_id}:1"),
                            account_id=source.lines[0].account_id,
                            debit=Decimal("1"),
                            credit=Decimal("0"),
                            functional_amount=Decimal("1"),
                            reporting_amount=Decimal("1"),
                            fact_state=source.lines[0].fact_state,
                        ),
                        JournalLine(
                            id=stable_id("scoped_post_command_line", f"{run_id}:2"),
                            account_id=source.lines[1].account_id,
                            debit=Decimal("0"),
                            credit=Decimal("1"),
                            functional_amount=Decimal("-1"),
                            reporting_amount=Decimal("-1"),
                            fact_state=source.lines[1].fact_state,
                        ),
                    ],
                )
            )
        session.commit()

    missing_selector = runner.invoke(app, ["post"], env={"SHFIN_DATABASE_URL": url})
    assert missing_selector.exit_code != 0
    result = runner.invoke(
        app,
        ["post", "--generation-run-id", run_ids[0]],
        env={"SHFIN_DATABASE_URL": url},
    )
    assert result.exit_code == 0, result.output
    assert "Posted 1 draft entries" in result.output

    with Session(create_engine(url)) as session:
        assert session.get(JournalEntry, draft_ids[0]).state.value == "POSTED"
        assert session.get(JournalEntry, draft_ids[1]).state.value == "DRAFT"
