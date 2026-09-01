from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import trial_balance
from sable_harbor.accounting.models import Base, FactState, FiscalPeriod, LegalEntity, Worker
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.core.ids import stable_id
from sable_harbor.operations.flows import (
    depreciate_asset,
    draw_debt_and_accrue_interest,
    procure_and_pay_asset,
    run_payroll,
)


def test_payroll_procurement_asset_and_debt_flows_reconcile() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session)
        entity_id = session.query(LegalEntity.id).scalar()
        period_id = session.query(FiscalPeriod.id).scalar()
        worker = Worker(
            id=stable_id("worker", "W001"), worker_number="W001", worker_type="EMPLOYEE",
            entity_id=entity_id, segment_code="CORECO", function_code="FINANCE",
            annual_cost=Decimal("120000"), starts_on=date(2026, 1, 1),
            fact_state=FactState.SYNTHETIC_INSTANCE,
        )
        session.add(worker)
        run = run_payroll(
            session, entity_id=entity_id, book_id=book_id, period_id=period_id,
            worker=worker, pay_date=date(2026, 8, 31), gross_pay=Decimal("10000"),
            employer_cost=Decimal("2000"),
        )
        bill, payment, asset = procure_and_pay_asset(
            session, entity_id=entity_id, book_id=book_id, period_id=period_id,
            key="LAB001", event_date=date(2026, 8, 15), amount=Decimal("60000"),
        )
        depreciation = depreciate_asset(
            session, asset=asset, book_id=book_id, period_id=period_id,
            depreciation_date=date(2026, 8, 31),
        )
        draw, interest = draw_debt_and_accrue_interest(
            session, entity_id=entity_id, book_id=book_id, period_id=period_id,
            key="FAC001", event_date=date(2026, 8, 1), principal=Decimal("120000"),
            annual_rate=Decimal("0.12"),
        )
        session.commit()
        balances = trial_balance(session, book_id)
        assert sum(debit for _, debit, _ in balances) == sum(credit for _, _, credit in balances)
        assert run.journal_entry_id and bill.journal_entry_id and payment.journal_entry_id
        assert depreciation.amount == Decimal("1000.0000")
        assert draw.principal == Decimal("120000.0000")
        assert interest.amount == Decimal("1200.0000")
