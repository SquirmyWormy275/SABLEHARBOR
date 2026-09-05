from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import event, func, inspect, select
from sqlalchemy.orm import Session

from sable_harbor.core.ids import stable_id

from .models import (
    Account,
    AccountingBook,
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
    active_run_id = session.info.get(GENERATION_RUN_SESSION_KEY)
    if not entry.generation_run_id and active_run_id:
        entry.generation_run_id = str(active_run_id)
    if not entry.generation_run_id:
        raise LedgerError("Posting requires an explicit generation run")
    from sable_harbor.provenance.models import GenerationRun

    with session.no_autoflush:
        run = session.get(GenerationRun, entry.generation_run_id)
        period = session.get(FiscalPeriod, entry.period_id)
        book = session.get(AccountingBook, entry.book_id)
    if run is None:
        raise LedgerError(f"Generation run {entry.generation_run_id!r} does not exist")
    if run.status != "RUNNING":
        raise LedgerError("Posting requires a RUNNING generation run; completed runs are frozen")
    if period is None or period.state.value == "CLOSED":
        raise LedgerError("Posting period is missing or closed")
    if book is None:
        raise LedgerError("Posting book is missing")
    if period.book_id != entry.book_id:
        raise LedgerError("Posting period does not belong to the journal's accounting book")
    if not period.starts_on <= entry.entry_date <= period.ends_on:
        raise LedgerError("Journal entry date must fall within its fiscal period")
    if active_run_id:
        with session.no_autoflush:
            active_run = session.get(GenerationRun, str(active_run_id))
        if active_run is None:
            raise LedgerError(f"Active generation run {active_run_id!r} does not exist")
        compatible_run_ids = {active_run.id}
        if active_run.shared_synthetic_calibration_run_id is not None:
            compatible_run_ids.add(active_run.shared_synthetic_calibration_run_id)
        if entry.generation_run_id not in compatible_run_ids:
            raise LedgerError(
                "Journal generation run is incompatible with the active session context"
            )
    with session.no_autoflush:
        period_close = session.get(
            GenerationPeriodClose, (entry.generation_run_id, entry.period_id)
        )
    if period_close:
        raise LedgerError("Posting period is closed for this generation run")
    debit = sum((line.debit for line in entry.lines), Decimal("0"))
    credit = sum((line.credit for line in entry.lines), Decimal("0"))
    if not entry.lines or debit != credit or debit == 0:
        raise LedgerError(f"Entry must balance with nonzero lines: debit={debit} credit={credit}")
    for line in entry.lines:
        if line.debit < 0 or line.credit < 0 or bool(line.debit) == bool(line.credit):
            raise LedgerError("Each line must contain exactly one positive debit or credit")
        signed_amount = line.debit - line.credit
        if line.functional_amount != signed_amount:
            raise LedgerError("Functional amount must equal debit less credit")
        if line.reporting_amount != line.functional_amount:
            raise LedgerError("Reporting amount must equal functional amount for the USD ledger")
        if line.transaction_currency is None:
            line.transaction_currency = book.currency
        elif line.transaction_currency != book.currency:
            raise LedgerError("Transaction currency must match the book until FX accounting exists")
    # Persist the draft and its validated lines before the state transition. This
    # gives database triggers a stable line set to validate and lets them reject
    # every later write to posted evidence, including writes issued outside the
    # ORM service.
    entry.state = EntryState.DRAFT
    entry.posted_at = None
    session.flush()
    entry.state = EntryState.POSTED
    entry.posted_at = datetime.now(UTC)
    session.flush()


def post_draft_entries(session: Session, generation_run_id: str) -> int:
    """Post drafts only while their owning generation run is still open."""
    from sable_harbor.provenance.models import GenerationRun

    run = session.get(GenerationRun, generation_run_id)
    if run is None:
        raise LedgerError(f"Unknown generation run {generation_run_id!r}")
    if run.status != "RUNNING":
        raise LedgerError("Completed generation runs are immutable; use a new adjustment run")
    previous_run_id = session.info.get(GENERATION_RUN_SESSION_KEY)
    session.info[GENERATION_RUN_SESSION_KEY] = run.id
    try:
        drafts = list(
            session.scalars(
                select(JournalEntry).where(
                    JournalEntry.state == EntryState.DRAFT,
                    JournalEntry.generation_run_id == run.id,
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
    referenced = session.scalar(
        select(func.count(JournalEntry.id)).where(
            JournalEntry.period_id == period.id,
            JournalEntry.generation_run_id.in_(context.included_run_ids),
        )
    )
    if not referenced:
        raise LedgerError(
            "Cannot close a fiscal period that is not referenced by the selected run context"
        )
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
    if session.scalar(
        select(JournalEntry.id).where(
            JournalEntry.generation_run_id == original.generation_run_id,
            JournalEntry.reversal_of_id == original.id,
        )
    ):
        raise LedgerError("A journal entry may be reversed only once within a generation run")
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
                id=stable_id("journal_line", f"{reversal_id}:{index}"),
                account_id=line.account_id,
                debit=line.credit,
                credit=line.debit,
                transaction_currency=line.transaction_currency,
                functional_amount=-line.functional_amount,
                reporting_amount=-line.reporting_amount,
                fact_state=line.fact_state,
                segment_code=line.segment_code,
                cost_center_code=line.cost_center_code,
                project_code=line.project_code,
                counterparty_entity_id=line.counterparty_entity_id,
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
    for item in session.dirty.union(session.deleted).union(session.new):
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


def reject_completed_run_content_mutations(
    session: Session, flush_context: object = None, instances: object = None
) -> None:
    """Freeze run-owned evidence when its generation lifecycle is completed."""
    from sable_harbor.provenance.models import GenerationRun

    candidates = session.new.union(session.dirty).union(session.deleted)
    for item in candidates:
        if isinstance(item, GenerationPeriodClose):
            if item in session.dirty or item in session.deleted:
                raise LedgerError("Period-close evidence is immutable")
            continue
        if isinstance(item, GenerationRun):
            continue
        run_id = getattr(item, "generation_run_id", None)
        if run_id is None and isinstance(item, JournalLine) and item.entry is not None:
            run_id = item.entry.generation_run_id
        if run_id is None:
            continue
        with session.no_autoflush:
            run = session.get(GenerationRun, str(run_id))
        if run is not None and run.status == "COMPLETED":
            raise LedgerError(
                f"Generation run {run.id!r} is completed; its owned evidence is immutable"
            )


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
    """Compare two scenario runs that share one compatible synthetic calibration dataset.

    The explicit, distinct selectors prevent an accidental comparison against the
    session default. Requiring the same profile and synthetic calibration dataset makes the delta
    attributable to scenario-owned forecast facts rather than seed, profile, or
    shared-calibration-layer differences.
    """
    from sable_harbor.provenance.service import comparison_run_contexts

    comparison_run_contexts(session, left_generation_run_id, right_generation_run_id)

    left = {
        code: (debit, credit)
        for code, debit, credit in trial_balance(session, book_id, left_generation_run_id)
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
event.listen(Session, "before_flush", reject_completed_run_content_mutations)
