from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import trial_balance
from sable_harbor.accounting.models import Base, FiscalPeriod, LegalEntity
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.logistics.flows import operate_waybill
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import complete_generation_run


def test_bst_waybill_drivers_revenue_cost_cash_and_gl_reconcile() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        entity_id = session.query(LegalEntity.id).scalar()
        period_id = session.query(FiscalPeriod.id).scalar()
        waybill = operate_waybill(
            session,
            entity_id=entity_id,
            book_id=book_id,
            period_id=period_id,
            key="BST-001",
            movement_date=date(2026, 8, 20),
            carloads=10,
            tons=Decimal("1000"),
            route_miles=Decimal("250"),
            base_rate=Decimal("50000"),
            fuel_surcharge=Decimal("5000"),
            fuel_gallons=Decimal("2000"),
            fuel_price=Decimal("4"),
            crew_hours=Decimal("160"),
            crew_rate=Decimal("75"),
        )
        run = session.get(GenerationRun, session.info["generation_run_id"])
        assert run is not None
        complete_generation_run(session, run)
        session.commit()
        assert waybill.ton_miles == Decimal("250000.0000")
        assert waybill.revenue == Decimal("55000.0000")
        assert waybill.fuel_cost + waybill.crew_cost == Decimal("20000.0000")
        balances = trial_balance(session, book_id)
        assert sum(debit for _, debit, _ in balances) == sum(credit for _, _, credit in balances)
