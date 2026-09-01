from pathlib import Path

import typer
from sqlalchemy import func, select

from sable_harbor import schema as schema  # noqa: F401
from sable_harbor.accounting.ledger import trial_balance
from sable_harbor.accounting.models import Base, EntryState, JournalEntry, JournalLine
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.core.database import build_engine, session_for
from sable_harbor.exports.release import package_public_demo
from sable_harbor.generation import generate_baseline, generate_standard
from sable_harbor.reporting import build_workbook
from sable_harbor.reporting_queries import named_queries, run_named_query
from sable_harbor.valuation.model import calculate_valuation, load_valuation_config
from sable_harbor.workbooks.suite import generate_workbook_suite

app = typer.Typer(no_args_is_help=True)


@app.command("status")
def status() -> None:
    typer.echo("Sable Harbor finance platform v0.1")


@app.command("init-db")
def init_db() -> None:
    engine = build_engine()
    Base.metadata.create_all(engine)
    typer.echo(f"Initialized {engine.url.render_as_string(hide_password=True)}")


@app.command("generate")
def generate(profile: str = "smoke", scenario: str = "base", seed: int = 20260831) -> None:
    engine = build_engine()
    Base.metadata.create_all(engine)
    with session_for(engine) as session:
        if profile == "smoke":
            result: object = {"book": seed_smoke(session)}
        elif profile in {"baseline", "full"}:
            result = generate_baseline(session, seed=seed, scenario=scenario)
        elif profile == "standard":
            result = generate_standard(session, seed=seed, scenario=scenario)
        else:
            raise typer.BadParameter("Profile must be smoke, baseline, or standard")
        session.commit()
    typer.echo(f"Generated profile={profile} scenario={scenario} seed={seed} result={result}")


@app.command("validate")
def validate() -> None:
    engine = build_engine()
    with session_for(engine) as session:
        existing = session.scalar(select(func.count(JournalEntry.id))) or 0
        if existing == 0:
            book_id = seed_smoke(session)
            balances = trial_balance(session, book_id)
            debit = sum(row[1] for row in balances)
            credit = sum(row[2] for row in balances)
        else:
            debit, credit = session.execute(
                select(func.sum(JournalLine.debit), func.sum(JournalLine.credit))
                .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
                .where(JournalEntry.state == EntryState.POSTED)
            ).one()
        if debit != credit:
            raise typer.Exit(code=1)
    typer.echo(f"PASS trial balance debit={debit} credit={credit}")


@app.command("report")
def report(output: Path = Path("reports/Sable_Harbor_FY2026_Model.xlsx")) -> None:
    engine = build_engine()
    Base.metadata.create_all(engine)
    with session_for(engine) as session:
        generate_baseline(session)
        session.commit()
        path = build_workbook(session, output)
    typer.echo(path)


@app.command("source-lock")
def source_lock() -> None:
    path = Path("docs/finance/CANON_SOURCE_LOCK.json")
    if not path.exists():
        raise typer.Exit(code=1)
    typer.echo(path)


@app.command("query")
def query(name: str) -> None:
    engine = build_engine()
    with session_for(engine) as session:
        rows = run_named_query(session, name)
    typer.echo({"query": name, "rows": rows})


@app.command("queries")
def queries() -> None:
    typer.echo("\n".join(named_queries()))


@app.command("workbooks")
def workbooks(output: Path = Path("workbooks/outputs")) -> None:
    engine = build_engine()
    Base.metadata.create_all(engine)
    with session_for(engine) as session:
        generate_standard(session)
        session.commit()
        paths = generate_workbook_suite(session, output)
    typer.echo("\n".join(str(path) for path in paths))


@app.command("package-release")
def package_release(output: Path = Path("releases/generated/public-demo-v0.1")) -> None:
    engine = build_engine()
    Base.metadata.create_all(engine)
    with session_for(engine) as session:
        generate_standard(session)
        session.commit()
        manifest = package_public_demo(session, output)
    typer.echo(manifest)


@app.command("valuation")
def valuation() -> None:
    typer.echo(calculate_valuation(load_valuation_config()))
