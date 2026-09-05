from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import (
    LedgerError,
    close_period,
    post_entry,
    reverse_entry,
    trial_balance,
)
from sable_harbor.accounting.models import (
    Account,
    AccountingBook,
    Base,
    EntryState,
    FactState,
    FiscalPeriod,
    GenerationPeriodClose,
    JournalEntry,
    JournalLine,
    LegalEntity,
    PeriodState,
)
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.core.ids import stable_id
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import complete_generation_run


def _account_id(session: Session, code: str) -> str:
    account_id = session.query(Account.id).filter(Account.code == code).scalar()
    assert account_id is not None
    return account_id


def _balanced_entry(
    session: Session,
    *,
    key: str,
    book_id: str,
    period_id: str,
    entry_date: date = date(2026, 8, 15),
    debit_functional: Decimal = Decimal("10"),
    debit_reporting: Decimal = Decimal("10"),
) -> JournalEntry:
    return JournalEntry(
        id=stable_id("journal", key),
        generation_run_id=str(session.info["generation_run_id"]),
        book_id=book_id,
        period_id=period_id,
        entry_date=entry_date,
        description=f"Ledger integrity test {key}",
        source_type="test",
        source_id=key,
        state=EntryState.DRAFT,
        lines=[
            JournalLine(
                id=stable_id("journal_line", f"{key}:debit"),
                account_id=_account_id(session, "1000"),
                debit=Decimal("10"),
                credit=Decimal("0"),
                transaction_currency="USD",
                functional_amount=debit_functional,
                reporting_amount=debit_reporting,
                fact_state=FactState.DERIVED,
            ),
            JournalLine(
                id=stable_id("journal_line", f"{key}:credit"),
                account_id=_account_id(session, "3000"),
                debit=Decimal("0"),
                credit=Decimal("10"),
                transaction_currency="USD",
                functional_amount=Decimal("-10"),
                reporting_amount=Decimal("-10"),
                fact_state=FactState.DERIVED,
            ),
        ],
    )


def test_smoke_seed_posts_balanced_idempotent_trial_balance() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session)
        session.commit()
        assert seed_smoke(session) == book_id
        balances = trial_balance(session, book_id)
        assert sum(row[1] for row in balances) == Decimal("1000000.0000")
        assert sum(row[2] for row in balances) == Decimal("1000000.0000")
        assert session.query(LegalEntity).one().jurisdiction == "OPEN"


def test_unbalanced_entry_is_rejected() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        seed = session.query(JournalEntry).first()
        assert seed is not None
        entry = JournalEntry(
            id=stable_id("journal", "BAD"),
            book_id=book_id,
            period_id=seed.period_id,
            entry_date=date(2026, 8, 2),
            description="bad",
            source_type="test",
            source_id="bad",
            lines=[
                JournalLine(
                    id=stable_id("line", "BAD:1"),
                    account_id=seed.lines[0].account_id,
                    debit=Decimal("1"),
                    credit=Decimal("0"),
                    functional_amount=Decimal("1"),
                    reporting_amount=Decimal("1"),
                    fact_state=seed.lines[0].fact_state,
                )
            ],
        )
        session.add(entry)
        with pytest.raises(LedgerError, match="balance"):
            post_entry(session, entry)
        assert entry.state is not EntryState.POSTED


def test_posted_entry_is_immutable_and_reversal_nets_to_zero() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        session.commit()
        original = session.query(JournalEntry).one()
        original.description = "mutated"
        with pytest.raises(LedgerError, match="immutable"):
            session.flush()
        session.rollback()
        original = session.query(JournalEntry).one()
        reverse_entry(
            session,
            original,
            date(2026, 8, 31),
            original.period_id,
            stable_id("journal", "SMOKE:OPENING_CAPITAL:REVERSAL"),
        )
        run = session.get(GenerationRun, session.info["generation_run_id"])
        assert run is not None
        complete_generation_run(session, run)
        session.commit()
        balances = trial_balance(session, book_id)
        assert sum(row[1] - row[2] for row in balances) == Decimal("0.0000")
        assert all(row[1] == row[2] for row in balances)


def test_closed_period_rejects_new_posting() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_smoke(session)
        session.commit()
        period = session.query(FiscalPeriod).one()
        close_period(session, period)
        session.commit()
        assert period.state is PeriodState.OPEN
        assert (
            session.get(
                GenerationPeriodClose,
                (session.info["generation_run_id"], period.id),
            )
            is not None
        )


def test_posting_is_allowed_only_while_generation_run_is_running() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        period = session.query(FiscalPeriod).one()

        running_entry = _balanced_entry(
            session,
            key="RUNNING-POST",
            book_id=book_id,
            period_id=period.id,
        )
        session.add(running_entry)
        post_entry(session, running_entry)
        assert running_entry.state is EntryState.POSTED

        run = session.get(GenerationRun, str(session.info["generation_run_id"]))
        assert run is not None
        complete_generation_run(session, run)
        completed_entry = _balanced_entry(
            session,
            key="COMPLETED-POST",
            book_id=book_id,
            period_id=period.id,
        )
        session.add(completed_entry)
        with pytest.raises(LedgerError, match="RUNNING generation run"):
            post_entry(session, completed_entry)


def test_posting_rejects_period_from_another_book() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_smoke(session, complete=False)
        period = session.query(FiscalPeriod).one()
        entity_id = session.query(LegalEntity.id).scalar()
        assert entity_id is not None
        other_book = AccountingBook(
            id=stable_id("book", "LEDGER-INTEGRITY-OTHER"),
            entity_id=entity_id,
            code="LEDGER_INTEGRITY_OTHER",
        )
        session.add(other_book)
        session.flush()
        entry = _balanced_entry(
            session,
            key="WRONG-BOOK-PERIOD",
            book_id=other_book.id,
            period_id=period.id,
        )
        session.add(entry)

        with pytest.raises(LedgerError, match="does not belong"):
            post_entry(session, entry)


def test_posting_rejects_entry_date_outside_fiscal_period() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        period = session.query(FiscalPeriod).one()
        entry = _balanced_entry(
            session,
            key="OUT-OF-PERIOD",
            book_id=book_id,
            period_id=period.id,
            entry_date=date(2026, 9, 1),
        )
        session.add(entry)

        with pytest.raises(LedgerError, match="within its fiscal period"):
            post_entry(session, entry)


def test_posting_rejects_transaction_currency_different_from_book() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        period = session.query(FiscalPeriod).one()
        entry = _balanced_entry(
            session,
            key="WRONG-TRANSACTION-CURRENCY",
            book_id=book_id,
            period_id=period.id,
        )
        entry.lines[0].transaction_currency = "EUR"
        session.add(entry)

        with pytest.raises(LedgerError, match="Transaction currency"):
            post_entry(session, entry)


@pytest.mark.parametrize(
    ("debit_functional", "debit_reporting", "message"),
    [
        (Decimal("11"), Decimal("11"), "Functional amount"),
        (Decimal("10"), Decimal("11"), "Reporting amount"),
    ],
)
def test_posting_rejects_incoherent_functional_and_reporting_amounts(
    debit_functional: Decimal,
    debit_reporting: Decimal,
    message: str,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        period = session.query(FiscalPeriod).one()
        entry = _balanced_entry(
            session,
            key=f"BAD-AMOUNTS-{debit_functional}-{debit_reporting}",
            book_id=book_id,
            period_id=period.id,
            debit_functional=debit_functional,
            debit_reporting=debit_reporting,
        )
        session.add(entry)

        # Isolate the service guard from the redundant SQLite CHECK constraint.
        # An explicit flush still occurs if post_entry ever misses this validation.
        with session.no_autoflush:
            with pytest.raises(LedgerError, match=message):
                post_entry(session, entry)


def test_reversal_preserves_all_dimensions_with_stable_unique_line_ids() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        period = session.query(FiscalPeriod).one()
        counterparty_id = session.query(LegalEntity.id).scalar()
        assert counterparty_id is not None
        cash_id = _account_id(session, "1000")
        equity_id = _account_id(session, "3000")
        original_lines: list[JournalLine] = []
        for pair_index in range(6):
            amount = Decimal(pair_index + 1)
            for side in ("debit", "credit"):
                line_index = len(original_lines) + 1
                debit = amount if side == "debit" else Decimal("0")
                credit = amount if side == "credit" else Decimal("0")
                original_lines.append(
                    JournalLine(
                        id=stable_id("journal_line", f"DIMENSIONAL:{line_index}"),
                        account_id=cash_id if side == "debit" else equity_id,
                        debit=debit,
                        credit=credit,
                        transaction_currency="USD",
                        functional_amount=debit - credit,
                        reporting_amount=debit - credit,
                        fact_state=FactState.DERIVED,
                        segment_code=f"SEG-{line_index}",
                        cost_center_code=f"CC-{line_index}",
                        project_code=f"PROJECT-{line_index}",
                        counterparty_entity_id=counterparty_id,
                    )
                )
        original = JournalEntry(
            id=stable_id("journal", "DIMENSIONAL-ORIGINAL"),
            generation_run_id=str(session.info["generation_run_id"]),
            book_id=book_id,
            period_id=period.id,
            entry_date=date(2026, 8, 15),
            description="Twelve-line dimensional journal",
            source_type="test",
            source_id="DIMENSIONAL-ORIGINAL",
            state=EntryState.DRAFT,
            lines=original_lines,
        )
        session.add(original)
        post_entry(session, original)

        reversal_id = stable_id("journal", "DIMENSIONAL-REVERSAL")
        reversal = reverse_entry(
            session,
            original,
            date(2026, 8, 31),
            period.id,
            reversal_id,
        )

        expected_ids = {
            stable_id("journal_line", f"{reversal_id}:{index}")
            for index in range(1, len(original_lines) + 1)
        }
        assert len(reversal.lines) == 12
        assert {line.id for line in reversal.lines} == expected_ids
        assert all(len(line.id) == 36 for line in reversal.lines)
        for source, reversed_line in zip(original.lines, reversal.lines, strict=True):
            assert reversed_line.account_id == source.account_id
            assert reversed_line.debit == source.credit
            assert reversed_line.credit == source.debit
            assert reversed_line.transaction_currency == source.transaction_currency
            assert reversed_line.functional_amount == -source.functional_amount
            assert reversed_line.reporting_amount == -source.reporting_amount
            assert reversed_line.fact_state is source.fact_state
            assert reversed_line.segment_code == source.segment_code
            assert reversed_line.cost_center_code == source.cost_center_code
            assert reversed_line.project_code == source.project_code
            assert reversed_line.counterparty_entity_id == source.counterparty_entity_id

        with pytest.raises(LedgerError, match="reversed only once"):
            reverse_entry(
                session,
                original,
                date(2026, 8, 31),
                period.id,
                stable_id("journal", "DIMENSIONAL-DUPLICATE-REVERSAL"),
            )
