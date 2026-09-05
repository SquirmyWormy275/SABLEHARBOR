import json
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session

from sable_harbor import schema as schema  # noqa: F401
from sable_harbor.accounting.ledger import close_period, post_draft_entries
from sable_harbor.accounting.models import FiscalPeriod, JournalEntry
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.accounting.validation import validate_financial_integrity
from sable_harbor.core.database import build_engine, require_migrated_schema, session_for
from sable_harbor.exports.metadata import public_profile
from sable_harbor.exports.release import package_public_demo
from sable_harbor.exports.units import package_business_units
from sable_harbor.generation import (
    generate_baseline_run,
    generate_full_history,
    generate_standard,
)
from sable_harbor.provenance.identity import RunIdentity, repository_head
from sable_harbor.provenance.models import GenerationRun
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
INTERNAL_INSPECTION_CLASSIFICATION = "INTERNAL_SYNTHETIC_INSPECTION_NOT_RELEASE_ARTIFACT"


def _inspection_envelope(
    session: Session, generation_run_id: str, *, payload_name: str, payload: object
) -> dict[str, object]:
    context = run_context(session, generation_run_id)
    run = session.get(GenerationRun, context.generation_run_id)
    if run is None:  # guarded by run_context
        raise ValueError(f"Unknown generation run {generation_run_id!r}")
    return {
        "classification": INTERNAL_INSPECTION_CLASSIFICATION,
        "generation_run_id": context.generation_run_id,
        "included_run_ids": list(context.included_run_ids),
        "profile": public_profile(run.profile),
        "scenario_code": context.scenario_code,
        "synthetic_calibration_through": (
            run.synthetic_calibration_through.isoformat()
            if run.synthetic_calibration_through
            else None
        ),
        "forecast_from": run.forecast_from.isoformat() if run.forecast_from else None,
        payload_name: payload,
    }


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
        profile, effective_scenario = (
            RunIdentity.build(profile=profile, scenario=scenario, seed=seed).profile,
            RunIdentity.build(profile=profile, scenario=scenario, seed=seed).scenario,
        )
        run = record_generation_run(
            session,
            profile=profile,
            scenario_code=effective_scenario,
            seed=seed,
            git_commit=repository_head(),
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
        else:
            raise typer.BadParameter(
                "Profile must be smoke, baseline, standard, full_history, stress, or full"
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
def post(generation_run_id: str = typer.Option(...)) -> None:
    engine = build_engine()
    with session_for(engine) as session:
        posted_count = post_draft_entries(session, generation_run_id)
        session.commit()
    typer.echo(f"Posted {posted_count} draft entries for generation run {generation_run_id}")


@app.command("close")
def close(
    through: str = typer.Option(..., help="Close periods through YYYY-MM"),
    generation_run_id: str = typer.Option(...),
) -> None:
    engine = build_engine()
    with session_for(engine) as session:
        context = run_context(session, generation_run_id)
        periods = list(
            session.scalars(
                select(FiscalPeriod)
                .join(JournalEntry, JournalEntry.period_id == FiscalPeriod.id)
                .where(
                    FiscalPeriod.code <= through,
                    JournalEntry.generation_run_id.in_(context.included_run_ids),
                )
                .distinct()
                .order_by(FiscalPeriod.code, FiscalPeriod.id)
            )
        )
        for period in periods:
            close_period(session, period, generation_run_id)
        session.commit()
    typer.echo(f"Closed {len(periods)} eligible periods through {through}")


@app.command("validate")
def validate(generation_run_id: str | None = None) -> None:
    engine = build_engine()
    require_migrated_schema(engine)
    with session_for(engine) as session:
        selected_id = run_context(session, generation_run_id).generation_run_id
        report = validate_financial_integrity(session, selected_id)
    typer.echo(f"PASS generation_run_id={report.generation_run_id} controls={len(report.controls)}")


@app.command("report")
def report(
    generation_run_id: str = typer.Option(...),
    output: Path = Path("reports/Sable_Harbor_Synthetic_Model_Preview.xlsx"),
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
def query(
    name: str,
    generation_run_id: str = typer.Option(...),
    comparison_generation_run_id: str | None = typer.Option(None),
) -> None:
    engine = build_engine()
    require_migrated_schema(engine)
    with session_for(engine) as session:
        rows = run_named_query(
            session,
            name,
            generation_run_id,
            comparison_generation_run_id=comparison_generation_run_id,
        )
        output = _inspection_envelope(
            session,
            generation_run_id,
            payload_name="result",
            payload={
                "query": name,
                "comparison_generation_run_id": comparison_generation_run_id,
                "rows": rows,
            },
        )
    typer.echo(output)


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


@app.command("package-business-units")
def package_units(
    generation_run_id: str = typer.Option(...),
    output: Path = Path("releases/generated/business-units"),
) -> None:
    engine = build_engine()
    require_migrated_schema(engine)
    with session_for(engine) as session:
        manifests = package_business_units(session, output, generation_run_id=generation_run_id)
    typer.echo("\n".join(str(path) for path in manifests))


@app.command("valuation")
def valuation() -> None:
    typer.echo(
        json.dumps(calculate_valuation(load_valuation_config()), default=str, sort_keys=True)
    )


@app.command("statements")
def statements(generation_run_id: str = typer.Option(...)) -> None:
    engine = build_engine()
    require_migrated_schema(engine)
    with session_for(engine) as session:
        output = _inspection_envelope(
            session,
            generation_run_id,
            payload_name="statements",
            payload=statement_snapshot(session, generation_run_id),
        )
    typer.echo(output)


@app.command("explain-lineage")
def explain_lineage(record_id: str, generation_run_id: str = typer.Option(...)) -> None:
    engine = build_engine()
    with session_for(engine) as session:
        rows = lineage_for(session, record_id, generation_run_id)
        if not rows:
            typer.echo(f"No lineage edges found for {record_id}")
            raise typer.Exit(code=1)
        output = _inspection_envelope(
            session,
            generation_run_id,
            payload_name="lineage_edges",
            payload=rows,
        )
    typer.echo(output)
