from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base, JournalEntry, JournalLine
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.service import complete_generation_run, record_generation_run
from sable_harbor.reports.statements import monthly_statements, statement_snapshot


def test_statements_balance_and_intercompany_eliminates() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="test"
        )
        generate_standard(session)
        complete_generation_run(session, run)
        session.commit()
        statements = statement_snapshot(session, run.id)
        assert statements["balance_sheet_difference"] == Decimal("0.0000")
        assert statements["assets"] == statements["liabilities"] + statements["total_equity"]
        elimination_entries = session.scalar(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.source_type == "consolidation_elimination"
            )
        )
        assert elimination_entries == 1
        elimination_balance = session.scalar(
            select(func.sum(JournalLine.debit - JournalLine.credit))
            .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
            .where(JournalEntry.source_type == "consolidation_elimination")
        )
        assert elimination_balance == Decimal("0.0000")


def test_monthly_statements_and_rollforwards_reconcile_to_gl() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="stress", seed=20260831, git_commit="test"
        )
        generate_standard(session, scenario="stress")
        complete_generation_run(session, run)
        session.commit()
        monthly = monthly_statements(session, run.id)
        snapshot = statement_snapshot(session, run.id)
    assert len(monthly) == 48
    assert all(row["balance_sheet_difference"] == Decimal("0.0000") for row in monthly)
    assert sum((row["cash_flow"] for row in monthly), Decimal(0)) == monthly[-1]["ending_cash"]
    assert abs(monthly[-1]["assets"] - snapshot["assets"]) <= Decimal("0.0001")
    assert abs(monthly[-1]["liabilities"] - snapshot["liabilities"]) <= Decimal("0.0001")
    assert abs(monthly[-1]["equity"] - snapshot["total_equity"]) <= Decimal("0.0001")
    assert abs(monthly[-1]["ending_cash"] - snapshot["ending_cash"]) <= Decimal("0.0001")
    assert all(
        {"working_capital", "debt", "net_fixed_assets", "inventory"}.issubset(row)
        for row in monthly
    )
