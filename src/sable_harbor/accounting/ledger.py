from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import event, func, inspect, select
from sqlalchemy.orm import Session

from .models import (
    Account,
    EntryState,
    FiscalPeriod,
    JournalEntry,
    JournalLine,
    PeriodState,
    ScenarioValue,
)

GENERATION_RUN_SESSION_KEY = "generation_run_id"


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


def close_period(session: Session, period: FiscalPeriod) -> None:
    if period.state is PeriodState.CLOSED:
        raise LedgerError("Period is already closed")
    draft_count = session.scalar(
        select(func.count(JournalEntry.id)).where(
            JournalEntry.period_id == period.id,
            JournalEntry.state == EntryState.DRAFT,
        )
    )
    if draft_count:
        raise LedgerError("Period contains draft journal entries")
    period.state = PeriodState.CLOSED
    session.flush()


def reverse_entry(
    session: Session,
    original: JournalEntry,
    reversal_date: date,
    reversal_period_id: str,
    reversal_id: str,
) -> JournalEntry:
    if original.state is not EntryState.POSTED:
        raise LedgerError("Only posted entries can be reversed")
    reversal = JournalEntry(
        id=reversal_id,
        book_id=original.book_id,
        period_id=reversal_period_id,
        entry_date=reversal_date,
        description=f"Reversal: {original.description}",
        source_type="journal_reversal",
        source_id=original.id,
        reversal_of_id=original.id,
        lines=[
            JournalLine(
                id=f"{reversal_id[:-1]}{index}",
                account_id=line.account_id,
                debit=line.credit,
                credit=line.debit,
                transaction_currency=line.transaction_currency,
                functional_amount=-line.functional_amount,
                reporting_amount=-line.reporting_amount,
                fact_state=line.fact_state,
            )
            for index, line in enumerate(original.lines, start=1)
        ],
    )
    session.add(reversal)
    post_entry(session, reversal)
    return reversal


def reject_posted_mutations(
    session: Session, flush_context: object = None, instances: object = None
) -> None:
    """Reject edits/deletes to posted journals; corrections must use reversal entries."""
    for item in session.dirty.union(session.deleted):
        if isinstance(item, JournalEntry):
            state_history = inspect(item).attrs.state.history
            posting_now = item.state is EntryState.POSTED and state_history.has_changes()
            was_posted = EntryState.POSTED in state_history.deleted or (
                item.state is EntryState.POSTED and not posting_now
            )
            if was_posted:
                raise LedgerError("Posted journal entries are immutable")
        if isinstance(item, JournalLine):
            entry = item.entry
            state_history = inspect(entry).attrs.state.history if entry is not None else None
            posting_now = bool(
                entry is not None
                and entry.state is EntryState.POSTED
                and state_history is not None
                and state_history.has_changes()
            )
            if entry is not None and entry.state is EntryState.POSTED and not posting_now:
                raise LedgerError("Posted journal lines are immutable")


def attach_generation_context(
    session: Session, flush_context: object = None, instances: object = None
) -> None:
    generation_run_id = session.info.get(GENERATION_RUN_SESSION_KEY)
    if generation_run_id is None:
        return
    for item in session.new:
        if isinstance(item, JournalEntry) and item.generation_run_id is None:
            item.generation_run_id = str(generation_run_id)
        if isinstance(item, ScenarioValue) and item.generation_run_id is None:
            item.generation_run_id = str(generation_run_id)


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


event.listen(Session, "before_flush", reject_posted_mutations)
event.listen(Session, "before_flush", attach_generation_context)
