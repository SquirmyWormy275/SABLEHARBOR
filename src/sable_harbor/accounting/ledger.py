from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Account, EntryState, FiscalPeriod, JournalEntry, JournalLine, PeriodState


class LedgerError(ValueError):
    pass


def post_entry(session: Session, entry: JournalEntry) -> None:
    if entry.state not in (None, EntryState.DRAFT):
        raise LedgerError("Only draft entries can be posted")
    period = session.get(FiscalPeriod, entry.period_id)
    if period is None or period.state is PeriodState.CLOSED:
        raise LedgerError("Posting period is missing or closed")
    debit = sum((line.debit for line in entry.lines), Decimal("0"))
    credit = sum((line.credit for line in entry.lines), Decimal("0"))
    if not entry.lines or debit != credit or debit == 0:
        raise LedgerError(f"Entry must balance with nonzero lines: debit={debit} credit={credit}")
    for line in entry.lines:
        if line.debit < 0 or line.credit < 0 or bool(line.debit) == bool(line.credit):
            raise LedgerError("Each line must contain exactly one positive debit or credit")
    entry.state = EntryState.POSTED
    entry.posted_at = datetime.now(UTC)
    session.flush()


def trial_balance(session: Session, book_id: str) -> list[tuple[str, Decimal, Decimal]]:
    statement = (
        select(Account.code, func.sum(JournalLine.debit), func.sum(JournalLine.credit))
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(JournalEntry.book_id == book_id, JournalEntry.state == EntryState.POSTED)
        .group_by(Account.code)
        .order_by(Account.code)
    )
    return [(code, debit, credit) for code, debit, credit in session.execute(statement)]
