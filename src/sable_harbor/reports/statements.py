from decimal import Decimal
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Account, EntryState, JournalEntry, JournalLine
from sable_harbor.provenance.service import run_context


class StatementSnapshot(TypedDict):
    assets: Decimal
    liabilities: Decimal
    contributed_equity: Decimal
    revenue: Decimal
    expenses: Decimal
    net_income: Decimal
    total_equity: Decimal
    balance_sheet_difference: Decimal
    ending_cash: Decimal


def statement_snapshot(session: Session, generation_run_id: str) -> StatementSnapshot:
    context = run_context(session, generation_run_id)
    rows = session.execute(
        select(
            Account.code,
            Account.account_class,
            func.sum(JournalLine.debit - JournalLine.credit),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.state == EntryState.POSTED,
            JournalEntry.generation_run_id.in_(context.included_run_ids),
        )
        .group_by(Account.code, Account.account_class)
    ).all()
    assets = sum((amount for _, cls, amount in rows if cls == "ASSET"), Decimal(0))
    liabilities = -sum((amount for _, cls, amount in rows if cls == "LIABILITY"), Decimal(0))
    contributed_equity = -sum((amount for _, cls, amount in rows if cls == "EQUITY"), Decimal(0))
    revenue = -sum((amount for _, cls, amount in rows if cls == "REVENUE"), Decimal(0))
    expenses = sum(
        (amount for _, cls, amount in rows if cls in {"EXPENSE", "OTHER_EXPENSE"}),
        Decimal(0),
    )
    net_income = revenue - expenses
    total_equity = contributed_equity + net_income
    ending_cash = sum((amount for code, _, amount in rows if code == "1000"), Decimal(0))
    return {
        "assets": assets,
        "liabilities": liabilities,
        "contributed_equity": contributed_equity,
        "revenue": revenue,
        "expenses": expenses,
        "net_income": net_income,
        "total_equity": total_equity,
        "balance_sheet_difference": assets - liabilities - total_equity,
        "ending_cash": ending_cash,
    }
