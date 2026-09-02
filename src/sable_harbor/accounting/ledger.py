from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import event, func, inspect, select
from sqlalchemy.orm import Session

from .models import (
    Account,
    EntryState,
    FiscalPeriod,
    GenerationPeriodClose,
    JournalEntry,
    JournalLine,
)

GENERATION_RUN_SESSION_KEY = "generation_run_id"


class LedgerError(ValueError):
    pass


def post_entry(session: Session, entry: JournalEntry) -> None:
    if entry.state not in (None, EntryState.DRAFT):
        raise LedgerError("Only draft entries can be posted")
    period = session.get(FiscalPeriod, entry.period_id)
    if period is None or period.state.value == "CLOSED":
        raise LedgerError("Posting period is missing or closed")
    active_run_id = session.info.get(GENERATION_RUN_SESSION_KEY)
    if not entry.generation_run_id and active_run_id:
        entry.generation_run_id = str(active_run_id)
    if not entry.generation_run_id:
        raise LedgerError("Posting requires an explicit generation run")
    if active_run_id:
        from sable_harbor.provenance.models import GenerationRun

        active_run = session.get(GenerationRun, str(active_run_id))
        if active_run is None:
            raise LedgerError(f"Active generation run {active_run_id!r} does not exist")
        compatible_run_ids = {active_run.id}
        if active_run.actual_generation_run_id is not None:
            compatible_run_ids.add(active_run.actual_generation_run_id)
        if entry.generation_run_id not in compatible_run_ids:
            raise LedgerError(
                "Journal generation run is incompatible with the active session context"
            )
    if session.get(GenerationPeriodClose, (entry.generation_run_id, entry.period_id)):
        raise LedgerError("Posting period is closed for this generation run")
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


def post_draft_entries(session: Session, generation_run_id: str) -> int:
    """Post only drafts belonging to one completed, compatible run context."""
    from sable_harbor.provenance.service import run_context

    context = run_context(session, generation_run_id)
    previous_run_id = session.info.get(GENERATION_RUN_SESSION_KEY)
    session.info[GENERATION_RUN_SESSION_KEY] = context.generation_run_id
    try:
        drafts = list(
            session.scalars(
                select(JournalEntry).where(
                    JournalEntry.state == EntryState.DRAFT,
                    JournalEntry.generation_run_id.in_(context.included_run_ids),
                )
            )
        )
        for entry in drafts:
            post_entry(session, entry)
        return len(drafts)
    finally:
        if previous_run_id is None:
            session.info.pop(GENERATION_RUN_SESSION_KEY, None)
        else:
            session.info[GENERATION_RUN_SESSION_KEY] = previous_run_id


def close_period(
    session: Session, period: FiscalPeriod, generation_run_id: str | None = None
) -> None:
    from sable_harbor.provenance.service import run_context

    context = run_context(session, generation_run_id)
    missing_run_ids = tuple(
        run_id
        for run_id in context.included_run_ids
        if session.get(GenerationPeriodClose, (run_id, period.id)) is None
    )
    if not missing_run_ids:
        return
    draft_count = session.scalar(
        select(func.count(JournalEntry.id)).where(
            JournalEntry.period_id == period.id,
            JournalEntry.generation_run_id.in_(context.included_run_ids),
            JournalEntry.state == EntryState.DRAFT,
        )
    )
    if draft_count:
        raise LedgerError("Period contains draft journal entries")
    closed_at = datetime.now(UTC)
    session.add_all(
        [
            GenerationPeriodClose(
                generation_run_id=run_id,
                period_id=period.id,
                closed_at=closed_at,
            )
            for run_id in missing_run_ids
        ]
    )
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
        generation_run_id=original.generation_run_id,
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
        if hasattr(item, "generation_run_id") and item.generation_run_id is None:
            item.generation_run_id = str(generation_run_id)


def trial_balance(
    session: Session, book_id: str, generation_run_id: str | None = None
) -> list[tuple[str, Decimal, Decimal]]:
    from sable_harbor.provenance.service import run_context

    context = run_context(session, generation_run_id)
    statement = (
        select(Account.code, func.sum(JournalLine.debit), func.sum(JournalLine.credit))
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.book_id == book_id,
            JournalEntry.state == EntryState.POSTED,
            JournalEntry.generation_run_id.in_(context.included_run_ids),
        )
        .group_by(Account.code)
        .order_by(Account.code)
    )
    return [(code, debit, credit) for code, debit, credit in session.execute(statement)]


def compare_trial_balances(
    session: Session,
    book_id: str,
    left_generation_run_id: str,
    right_generation_run_id: str,
) -> list[tuple[str, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]]:
    """Compare two scenario runs that share one compatible actual dataset.

    The explicit, distinct selectors prevent an accidental comparison against the
    session default. Requiring the same profile and actual dataset makes the delta
    attributable to scenario-owned forecast facts rather than seed, profile, or
    actual-layer differences.
    """
    from sable_harbor.provenance.models import GenerationRun
    from sable_harbor.provenance.service import run_context

    if left_generation_run_id == right_generation_run_id:
        raise ValueError("Comparison requires two distinct generation runs")
    left_context = run_context(session, left_generation_run_id)
    right_context = run_context(session, right_generation_run_id)
    left_run = session.get(GenerationRun, left_context.generation_run_id)
    right_run = session.get(GenerationRun, right_context.generation_run_id)
    if left_run is None or right_run is None:  # guarded by run_context
        raise ValueError("Comparison generation run does not exist")
    if (
        left_run.profile != right_run.profile
        or left_run.actual_dataset_id != right_run.actual_dataset_id
        or left_run.actual_through != right_run.actual_through
        or left_run.forecast_from != right_run.forecast_from
        or left_run.schema_head != right_run.schema_head
    ):
        raise ValueError(
            "Comparison runs must use the same profile, actual dataset, cutoff, "
            "forecast start, and schema"
        )

    left = {
        code: (debit, credit)
        for code, debit, credit in trial_balance(
            session, book_id, left_generation_run_id
        )
    }
    right = {
        code: (debit, credit)
        for code, debit, credit in trial_balance(session, book_id, right_generation_run_id)
    }
    rows = []
    for code in sorted(left.keys() | right.keys()):
        left_debit, left_credit = left.get(code, (Decimal("0"), Decimal("0")))
        right_debit, right_credit = right.get(code, (Decimal("0"), Decimal("0")))
        rows.append(
            (
                code,
                left_debit,
                left_credit,
                right_debit,
                right_credit,
                right_debit - left_debit,
                right_credit - left_credit,
            )
        )
    return rows


event.listen(Session, "before_flush", reject_posted_mutations)
event.listen(Session, "before_flush", attach_generation_context)
