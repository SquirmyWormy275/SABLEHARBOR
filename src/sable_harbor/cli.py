import subprocess
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select, text

from sable_harbor import schema as schema  # noqa: F401
from sable_harbor.accounting.ledger import close_period, post_entry
from sable_harbor.accounting.models import (
    EntryState,
    FiscalPeriod,
    JournalEntry,
    JournalLine,
    ScenarioValue,
)
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.core.database import build_engine, require_migrated_schema, session_for
from sable_harbor.exports.release import package_public_demo
from sable_harbor.generation import (
    generate_baseline_run,
    generate_full_history,
    generate_standard,
)
from sable_harbor.provenance.identity import RunIdentity
from sable_harbor.provenance.service import (
    complete_generation_run,
    lineage_for,
    link_journals,
    record_generation_run,
    run_context,
    seed_provenance,
)
from sable_harbor.reporting import build_workbook
from sable_harbor.reporting_queries import named_queries, run_named_query
from sable_harbor.reports.statements import statement_snapshot
from sable_harbor.valuation.model import calculate_valuation, load_valuation_config
from sable_harbor.workbooks.suite import generate_workbook_suite

app = typer.Typer(no_args_is_help=True)


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=False, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


@app.command("status")
def status() -> None:
    typer.echo("Sable Harbor finance platform v0.1")


@app.command("run-id")
def run_id(profile: str, scenario: str = "base", seed: int = 20260831) -> None:
    typer.echo(RunIdentity.build(profile=profile, scenario=scenario, seed=seed).run_id)


@app.command("init-db")
def init_db() -> None:
    command.upgrade(Config("alembic.ini"), "head")
    typer.echo("Database migrated to head")


@app.command("migrate")
def migrate() -> None:
    command.upgrade(Config("alembic.ini"), "head")
    typer.echo("Database migrated to head")


@app.command("seed-canon")
def seed_canon() -> None:
    engine = build_engine()
    require_migrated_schema(engine)
    with session_for(engine) as session:
        count = seed_provenance(session)
        session.commit()
    typer.echo(f"Seeded {count} new assumptions")


@app.command("generate")
def generate(profile: str = "smoke", scenario: str = "base", seed: int = 20260831) -> None:
    engine = build_engine()
    require_migrated_schema(engine)
    with session_for(engine) as session:
        profile, effective_scenario = RunIdentity.build(
            profile=profile, scenario=scenario, seed=seed
        ).profile, RunIdentity.build(profile=profile, scenario=scenario, seed=seed).scenario
        run = record_generation_run(
            session,
            profile=profile,
            scenario_code=effective_scenario,
            seed=seed,
            git_commit=_git_commit(),
        )
        if profile == "smoke":
            result: object = {"book": seed_smoke(session)}
        elif profile in {"baseline", "full"}:
            result = generate_baseline_run(session, seed=seed, scenario=scenario)
        elif profile == "standard":
            result = generate_standard(session, seed=seed, scenario=scenario)
        elif profile == "full_history":
            result = generate_full_history(session, seed=seed, scenario=scenario)
        elif profile == "stress":
            scenario = effective_scenario
            result = generate_standard(session, seed=seed, scenario=scenario)
        elif profile == "benchmark_private":
            if "var/private/" not in str(engine.url):
                raise typer.BadParameter(
                    "benchmark_private requires SHFIN_DATABASE_URL under var/private/"
                )
            result = generate_standard(session, seed=seed, scenario=scenario)
        else:
            raise typer.BadParameter(
                "Profile must be smoke, baseline, standard, full_history, "
                "stress, or benchmark_private"
            )
        seed_provenance(session)
        lineage_count = link_journals(session, run)
        complete_generation_run(session, run)
        session.commit()
    typer.echo(
        f"Generated profile={profile} scenario={scenario} seed={seed} "
        f"lineage_edges={lineage_count} result={result}"
    )


@app.command("post")
def post() -> None:
    engine = build_engine()
    with session_for(engine) as session:
        drafts = list(
            session.scalars(select(JournalEntry).where(JournalEntry.state == EntryState.DRAFT))
        )
        for entry in drafts:
            post_entry(session, entry)
        session.commit()
    typer.echo(f"Posted {len(drafts)} draft entries")


@app.command("close")
def close(through: str = typer.Option(..., help="Close periods through YYYY-MM")) -> None:
    engine = build_engine()
    with session_for(engine) as session:
        periods = list(
            session.scalars(
                select(FiscalPeriod).where(FiscalPeriod.code <= through).order_by(FiscalPeriod.code)
            )
        )
        for period in periods:
            if period.state.value == "OPEN":
                close_period(session, period)
        session.commit()
    typer.echo(f"Closed {len(periods)} eligible periods through {through}")


@app.command("validate")
def validate(generation_run_id: str | None = None) -> None:
    engine = build_engine()
    with session_for(engine) as session:
        existing = session.scalar(select(func.count(JournalEntry.id))) or 0
        if existing == 0:
            raise ValueError("Validation requires an existing completed generation run")
        else:
            context = run_context(session, generation_run_id)
            debit, credit = session.execute(
                select(func.sum(JournalLine.debit), func.sum(JournalLine.credit))
                .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
                .where(
                    JournalEntry.state == EntryState.POSTED,
                    JournalEntry.generation_run_id.in_(context.included_run_ids),
                )
            ).one()
            marker_count = session.scalar(
                select(func.count(ScenarioValue.id)).where(
                    ScenarioValue.generation_run_id == context.generation_run_id,
                    ScenarioValue.metric_code == "run_marker",
                )
            )
            if marker_count != 1:
                raise ValueError("Selected generation run does not have exactly one run marker")
            if len(context.included_run_ids) == 2:
                opening_count = session.scalar(
                    select(func.count(JournalEntry.id)).where(
                        JournalEntry.generation_run_id == context.included_run_ids[0],
                        JournalEntry.description.like("Scenario opening%"),
                    )
                )
                if opening_count != 3:
                    raise ValueError(
                        f"Common actual layer has {opening_count} opening entries; expected 3"
                    )
            inspector = inspect(engine)
            null_owned: list[str] = []
            for table in inspector.get_table_names():
                columns = {column["name"] for column in inspector.get_columns(table)}
                if "generation_run_id" not in columns:
                    continue
                null_count = session.scalar(
                    text(f'SELECT COUNT(*) FROM "{table}" WHERE generation_run_id IS NULL')
                )
                if null_count:
                    null_owned.append(f"{table}={null_count}")
            if null_owned:
                raise ValueError("Null generation ownership: " + ", ".join(null_owned))
        if debit != credit:
            raise typer.Exit(code=1)
    typer.echo(f"PASS trial balance debit={debit} credit={credit}")


@app.command("report")
def report(
    generation_run_id: str = typer.Option(...),
    output: Path = Path("reports/Sable_Harbor_FY2026_Model.xlsx"),
) -> None:
    engine = build_engine()
    require_migrated_schema(engine)
    with session_for(engine) as session:
        path = build_workbook(session, output, generation_run_id)
    typer.echo(path)


@app.command("source-lock")
def source_lock() -> None:
    path = Path("docs/finance/CANON_SOURCE_LOCK.json")
    if not path.exists():
        raise typer.Exit(code=1)
    typer.echo(path)


@app.command("query")
def query(name: str, generation_run_id: str = typer.Option(...)) -> None:
    engine = build_engine()
    require_migrated_schema(engine)
    with session_for(engine) as session:
        rows = run_named_query(session, name, generation_run_id)
    typer.echo({"query": name, "rows": rows})


@app.command("queries")
def queries() -> None:
    typer.echo("\n".join(named_queries()))


@app.command("workbooks")
def workbooks(
    generation_run_id: str = typer.Option(...), output: Path = Path("workbooks/outputs")
) -> None:
    engine = build_engine()
    require_migrated_schema(engine)
    with session_for(engine) as session:
        paths = generate_workbook_suite(session, output, generation_run_id=generation_run_id)
    typer.echo("\n".join(str(path) for path in paths))


@app.command("package-release")
def package_release(
    generation_run_id: str = typer.Option(...),
    output: Path = Path("releases/generated/public-demo-v0.1"),
) -> None:
    engine = build_engine()
    require_migrated_schema(engine)
    with session_for(engine) as session:
        manifest = package_public_demo(session, output, generation_run_id=generation_run_id)
    typer.echo(manifest)


@app.command("valuation")
def valuation() -> None:
    typer.echo(calculate_valuation(load_valuation_config()))


@app.command("statements")
def statements(generation_run_id: str = typer.Option(...)) -> None:
    engine = build_engine()
    require_migrated_schema(engine)
    with session_for(engine) as session:
        typer.echo(statement_snapshot(session, generation_run_id))


@app.command("explain-lineage")
def explain_lineage(record_id: str) -> None:
    engine = build_engine()
    with session_for(engine) as session:
        rows = lineage_for(session, record_id)
    if not rows:
        typer.echo(f"No lineage edges found for {record_id}")
        raise typer.Exit(code=1)
    typer.echo(rows)
