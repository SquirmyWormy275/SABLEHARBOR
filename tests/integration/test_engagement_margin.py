from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import trial_balance
from sable_harbor.accounting.models import Base, FactState, FiscalPeriod, LegalEntity, Worker
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.commercial.contract_to_cash import create_foundry_contract_flow
from sable_harbor.commercial.engagements import deliver_and_bill_engagement
from sable_harbor.core.ids import stable_id
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import complete_generation_run


def test_services_time_cost_billing_and_margin_tie_to_gl() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        entity_id = session.query(LegalEntity.id).scalar()
        period_id = session.query(FiscalPeriod.id).scalar()
        contract, _ = create_foundry_contract_flow(
            session,
            book_id=book_id,
            entity_id=entity_id,
            period_id=period_id,
            natural_key="SERVICES-CUSTOMER",
            invoice_date=date(2026, 8, 1),
            annual_value=Decimal("1200"),
        )
        worker = Worker(
            id=stable_id("worker", "CONSULTANT-1"),
            worker_number="CONSULTANT-1",
            worker_type="EMPLOYEE",
            entity_id=entity_id,
            segment_code="CORECO",
            function_code="IMPLEMENTATION",
            annual_cost=Decimal("150000"),
            starts_on=date(2026, 1, 1),
            fact_state=FactState.SYNTHETIC_INSTANCE,
        )
        session.add(worker)
        _, time, invoice = deliver_and_bill_engagement(
            session,
            contract=contract,
            worker=worker,
            book_id=book_id,
            period_id=period_id,
            key="ENG-1",
            work_date=date(2026, 8, 15),
            hours=Decimal("100"),
            bill_rate=Decimal("250"),
            cost_rate=Decimal("100"),
        )
        run = session.get(GenerationRun, session.info["generation_run_id"])
        assert run is not None
        complete_generation_run(session, run)
        session.commit()
        balances = {
            code: (debit, credit) for code, debit, credit in trial_balance(session, book_id)
        }
        assert time.hours == Decimal("100.00")
        assert invoice.total == Decimal("25000.0000")
        assert balances["4010"][1] == Decimal("25000.0000")
        assert balances["5000"][0] == Decimal("10000.0000")
        assert invoice.total - Decimal("10000") == Decimal("15000.0000")
