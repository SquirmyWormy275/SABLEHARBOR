from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import trial_balance
from sable_harbor.accounting.models import Base, FiscalPeriod, LegalEntity
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import complete_generation_run
from sable_harbor.recovery.flows import execute_recovery_run


def test_cradle_feed_recovery_host_share_sale_and_gl_reconcile() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        entity_id = session.query(LegalEntity.id).scalar()
        period_id = session.query(FiscalPeriod.id).scalar()
        run = execute_recovery_run(
            session,
            entity_id=entity_id,
            book_id=book_id,
            period_id=period_id,
            key="STREAM17-001",
            run_date=date(2026, 8, 21),
            feed_tons=Decimal("1000"),
            grade_fraction=Decimal("0.002"),
            recovery_fraction=Decimal("0.75"),
            price_per_unit=Decimal("20"),
            host_share=Decimal("0.20"),
            operating_cost=Decimal("15000"),
        )
        generation_run = session.get(GenerationRun, session.info["generation_run_id"])
        assert generation_run is not None
        complete_generation_run(session, generation_run)
        session.commit()
        assert not run.host_asset_owned
        assert run.recovered_units == Decimal("3000.0000")
        assert run.gross_sale == Decimal("60000.0000")
        assert run.host_share_amount == Decimal("12000.0000")
        balances = trial_balance(session, book_id)
        assert sum(debit for _, debit, _ in balances) == sum(credit for _, _, credit in balances)


def test_cradle_rejects_host_ownership_in_base_flow() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session, pytest.raises(ValueError, match="cannot own"):
        book_id = seed_smoke(session, complete=False)
        execute_recovery_run(
            session,
            entity_id=session.query(LegalEntity.id).scalar(),
            book_id=book_id,
            period_id=session.query(FiscalPeriod.id).scalar(),
            key="INVALID",
            run_date=date(2026, 8, 1),
            feed_tons=Decimal(1),
            grade_fraction=Decimal("0.1"),
            recovery_fraction=Decimal("0.5"),
            price_per_unit=Decimal(1),
            host_share=Decimal("0.1"),
            operating_cost=Decimal(1),
            host_asset_owned=True,
        )
