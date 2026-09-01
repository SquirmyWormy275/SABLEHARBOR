from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base, JournalEntry, JournalLine
from sable_harbor.generation import generate_standard
from sable_harbor.reports.statements import statement_snapshot


def test_statements_balance_and_intercompany_eliminates() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        generate_standard(session)
        session.commit()
        statements = statement_snapshot(session)
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
