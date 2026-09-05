from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base, FiscalPeriod, LegalEntity
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.operations.flows import draw_debt_and_accrue_interest, repay_debt
from sable_harbor.operations.models import DebtRepayment


def test_cumulative_debt_repayments_cannot_exceed_draw_principal() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        entity_id = session.query(LegalEntity.id).scalar()
        period_id = session.query(FiscalPeriod.id).scalar()
        assert entity_id is not None
        assert period_id is not None
        draw, _ = draw_debt_and_accrue_interest(
            session,
            entity_id=entity_id,
            book_id=book_id,
            period_id=period_id,
            key="CUMULATIVE-REPAYMENT",
            event_date=date(2026, 8, 1),
            principal=Decimal("100000"),
            annual_rate=Decimal("0.12"),
        )

        repay_debt(
            session,
            draw=draw,
            book_id=book_id,
            period_id=period_id,
            repayment_date=date(2026, 8, 15),
            principal=Decimal("70000"),
        )
        repay_debt(
            session,
            draw=draw,
            book_id=book_id,
            period_id=period_id,
            repayment_date=date(2026, 8, 20),
            principal=Decimal("30000"),
        )

        with pytest.raises(ValueError, match="Cumulative debt repayments"):
            repay_debt(
                session,
                draw=draw,
                book_id=book_id,
                period_id=period_id,
                repayment_date=date(2026, 8, 31),
                principal=Decimal("0.0001"),
            )

        repayment_count, repaid_principal = session.execute(
            select(func.count(DebtRepayment.id), func.sum(DebtRepayment.principal)).where(
                DebtRepayment.debt_draw_id == draw.id
            )
        ).one()
        assert repayment_count == 2
        assert repaid_principal == draw.principal == Decimal("100000.0000")
