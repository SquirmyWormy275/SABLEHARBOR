from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import LedgerError, post_entry, trial_balance
from sable_harbor.accounting.models import Base, EntryState, JournalEntry, JournalLine
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.core.ids import stable_id


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


def test_unbalanced_entry_is_rejected() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session)
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
        assert entry.state is EntryState.DRAFT
