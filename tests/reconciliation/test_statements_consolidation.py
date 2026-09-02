from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Account, Base, JournalEntry, JournalLine
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.service import complete_generation_run, record_generation_run
from sable_harbor.reporting_queries import run_named_query
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


def test_aging_and_debt_controls_reconcile_to_the_scoped_gl() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="test"
        )
        generate_standard(session)
        complete_generation_run(session, run)
        session.commit()
        aging = {row["ledger"]: row for row in run_named_query(session, "ar_ap_aging", run.id)}
        debt = run_named_query(session, "debt_covenant_calculation", run.id)
        monthly = monthly_statements(session, run.id)
        included_runs = (run.actual_generation_run_id, run.id)
        gl_ar = session.scalar(
            select(func.sum(JournalLine.debit - JournalLine.credit))
            .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
            .join(Account, Account.id == JournalLine.account_id)
            .where(Account.code == "1100", JournalEntry.generation_run_id.in_(included_runs))
        )
        gl_ap = session.scalar(
            select(func.sum(JournalLine.credit - JournalLine.debit))
            .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
            .join(Account, Account.id == JournalLine.account_id)
            .where(Account.code == "2100", JournalEntry.generation_run_id.in_(included_runs))
        )

    money = Decimal("0.0001")
    assert Decimal(str(aging["AR"]["open_amount"])).quantize(money) == gl_ar
    assert Decimal(str(aging["AP"]["open_amount"])).quantize(money) == gl_ap
    assert all(row["open_amount"] == row["current_bucket"] for row in aging.values())
    facilities = [
        row for row in debt if row["facility_number"] != "ACQUISITION_OPENING_CONTROL"
    ]
    principal = sum((Decimal(str(row["principal_outstanding"])) for row in debt), Decimal(0))
    interest = sum((Decimal(str(row["accrued_interest"])) for row in debt), Decimal(0))
    assert sum(
        (Decimal(str(row["principal_outstanding"])) for row in facilities), Decimal(0)
    ) == Decimal("300000.0000")
    assert sum(
        (Decimal(str(row["accrued_interest"])) for row in facilities), Decimal(0)
    ).quantize(money) == Decimal("2666.6668")
    assert (principal + interest).quantize(money) == monthly[-1]["debt"]
    assert all(
        row["covenant_status"] == "PROVISIONAL_NO_LOCKED_THRESHOLD" for row in facilities
    )
    assert all(row["unallocated_subledger_amount"] == 0 for row in aging.values())
