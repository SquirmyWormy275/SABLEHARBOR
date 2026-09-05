from collections import defaultdict
from datetime import date
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


class MonthlyStatement(TypedDict):
    period: str
    period_end: date
    revenue: Decimal
    expenses: Decimal
    net_income: Decimal
    assets: Decimal
    liabilities: Decimal
    equity: Decimal
    balance_sheet_difference: Decimal
    ending_cash: Decimal
    cash_flow: Decimal
    working_capital: Decimal
    debt: Decimal
    net_fixed_assets: Decimal
    inventory: Decimal


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


def monthly_statements(session: Session, generation_run_id: str) -> list[MonthlyStatement]:
    """Build reconciled monthly statements and principal rollforwards from the scoped GL."""
    context = run_context(session, generation_run_id)
    rows = session.execute(
        select(
            JournalEntry.entry_date,
            Account.code,
            Account.account_class,
            JournalLine.debit - JournalLine.credit,
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.state == EntryState.POSTED,
            JournalEntry.generation_run_id.in_(context.included_run_ids),
        )
        .order_by(JournalEntry.entry_date, JournalEntry.id, JournalLine.id)
    ).all()
    monthly_activity: dict[str, list[tuple[str, str, Decimal]]] = defaultdict(list)
    period_ends: dict[str, date] = {}
    for entry_date, code, account_class, amount in rows:
        period = entry_date.strftime("%Y-%m")
        monthly_activity[period].append((code, account_class, amount))
        period_ends[period] = max(period_ends.get(period, entry_date), entry_date)

    balances: dict[str, Decimal] = defaultdict(Decimal)
    prior_cash = Decimal(0)
    output: list[MonthlyStatement] = []
    for period in sorted(monthly_activity):
        period_revenue = Decimal(0)
        period_expenses = Decimal(0)
        for code, account_class, amount in monthly_activity[period]:
            balances[code] += amount
            if account_class == "REVENUE":
                period_revenue -= amount
            elif account_class in {"EXPENSE", "OTHER_EXPENSE"}:
                period_expenses += amount
        assets = sum(
            (amount for code, amount in balances.items() if code.startswith("1")), Decimal(0)
        )
        liabilities = -sum(
            (amount for code, amount in balances.items() if code.startswith("2")), Decimal(0)
        )
        contributed_equity = -sum(
            (amount for code, amount in balances.items() if code.startswith("3")), Decimal(0)
        )
        cumulative_revenue = -sum(
            (amount for code, amount in balances.items() if code.startswith("4")), Decimal(0)
        )
        cumulative_expenses = sum(
            (amount for code, amount in balances.items() if code.startswith(("5", "6", "7"))),
            Decimal(0),
        )
        equity = contributed_equity + cumulative_revenue - cumulative_expenses
        cash = balances["1000"]
        output.append(
            {
                "period": period,
                "period_end": period_ends[period],
                "revenue": period_revenue,
                "expenses": period_expenses,
                "net_income": period_revenue - period_expenses,
                "assets": assets,
                "liabilities": liabilities,
                "equity": equity,
                "balance_sheet_difference": assets - liabilities - equity,
                "ending_cash": cash,
                "cash_flow": cash - prior_cash,
                "working_capital": (
                    balances["1100"] + balances["1200"] + balances["2100"] + balances["2200"]
                ),
                "debt": -(balances["2500"] + balances["2510"]),
                "net_fixed_assets": balances["1500"] + balances["1590"],
                "inventory": balances["1200"],
            }
        )
        prior_cash = cash
    return output
