from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import trial_balance
from sable_harbor.accounting.models import Base, FiscalPeriod, LegalEntity
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.commercial.contract_to_cash import (
    create_foundry_contract_flow,
    receive_cash,
    recognize_month,
)
from sable_harbor.commercial.models import PerformanceObligation
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import complete_generation_run


def test_contract_invoice_revenue_cash_reconcile_to_gl() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        entity_id = session.query(LegalEntity.id).scalar()
        period_id = session.query(FiscalPeriod.id).scalar()
        contract, invoice = create_foundry_contract_flow(
            session,
            book_id=book_id,
            entity_id=entity_id,
            period_id=period_id,
            natural_key="C001",
            invoice_date=date(2026, 8, 1),
            annual_value=Decimal("1200.00"),
        )
        obligation = session.query(PerformanceObligation).filter_by(contract_id=contract.id).one()
        recognize_month(
            session,
            obligation=obligation,
            book_id=book_id,
            period_id=period_id,
            recognition_date=date(2026, 8, 31),
            amount=Decimal("100.00"),
        )
        receive_cash(
            session,
            invoice=invoice,
            book_id=book_id,
            period_id=period_id,
            receipt_date=date(2026, 8, 25),
        )
        run = session.get(GenerationRun, session.info["generation_run_id"])
        assert run is not None
        complete_generation_run(session, run)
        session.commit()
        by_account = {
            code: (debit, credit) for code, debit, credit in trial_balance(session, book_id)
        }
        assert by_account["1100"] == (Decimal("1200.0000"), Decimal("1200.0000"))
        assert by_account["2200"] == (Decimal("100.0000"), Decimal("1200.0000"))
        assert by_account["4000"] == (Decimal("0.0000"), Decimal("100.0000"))
        assert invoice.status == "PAID"
