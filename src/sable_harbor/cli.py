from pathlib import Path

import typer

from sable_harbor.accounting.ledger import trial_balance
from sable_harbor.accounting.models import Base
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.core.database import build_engine, session_for

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
    if profile != "smoke":
        raise typer.BadParameter("Only the smoke profile is implemented in this increment")
    engine = build_engine()
    Base.metadata.create_all(engine)
    with session_for(engine) as session:
        book_id = seed_smoke(session)
        session.commit()
    typer.echo(f"Generated profile={profile} scenario={scenario} seed={seed} book={book_id}")


@app.command("validate")
def validate() -> None:
    engine = build_engine()
    with session_for(engine) as session:
        book_id = seed_smoke(session)
        balances = trial_balance(session, book_id)
        debit = sum(row[1] for row in balances)
        credit = sum(row[2] for row in balances)
        if debit != credit:
            raise typer.Exit(code=1)
    typer.echo(f"PASS trial balance debit={debit} credit={credit}")


@app.command("source-lock")
def source_lock() -> None:
    path = Path("docs/finance/CANON_SOURCE_LOCK.json")
    if not path.exists():
        raise typer.Exit(code=1)
    typer.echo(path)
