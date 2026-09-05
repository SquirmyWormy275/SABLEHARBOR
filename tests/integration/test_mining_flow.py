from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import trial_balance
from sable_harbor.accounting.models import Base, FactState, FiscalPeriod, LegalEntity, Site
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.core.ids import stable_id
from sable_harbor.mining.flows import produce_concentrate, ship_and_collect
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import complete_generation_run


def test_red_wash_quantity_inventory_sales_and_gl_reconcile() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        entity_id = session.query(LegalEntity.id).scalar()
        period_id = session.query(FiscalPeriod.id).scalar()
        site = Site(
            id=stable_id("site", "RED_WASH_TEST"),
            code="RED_WASH_TEST",
            name="Red Wash synthetic test site",
            site_type="UNDERGROUND_MINE_MILL",
            region="Wyoming",
            owner_entity_id=entity_id,
            fact_state=FactState.SYNTHETIC_INSTANCE,
        )
        session.add(site)
        batch = produce_concentrate(
            session,
            entity_id=entity_id,
            site_id=site.id,
            book_id=book_id,
            period_id=period_id,
            key="RW-2026-08",
            production_date=date(2026, 8, 15),
            feed_tons=Decimal("1000"),
            grade_fraction=Decimal("0.001"),
            recovery_fraction=Decimal("0.90"),
            production_cost=Decimal("90000"),
        )
        shipment = ship_and_collect(
            session,
            batch=batch,
            book_id=book_id,
            period_id=period_id,
            shipment_date=date(2026, 8, 25),
            pounds_shipped=Decimal("1200"),
            realized_price_per_lb=Decimal("80"),
        )
        run = session.get(GenerationRun, session.info["generation_run_id"])
        assert run is not None
        complete_generation_run(session, run)
        session.commit()
        assert batch.pounds_u3o8 == Decimal("1800.0000")
        assert batch.pounds_u3o8 - shipment.pounds_shipped == Decimal("600.0000")
        assert shipment.revenue == Decimal("96000.0000")
        assert shipment.cost_of_sales == Decimal("60000.0000")
        balances = trial_balance(session, book_id)
        assert sum(debit for _, debit, _ in balances) == sum(credit for _, _, credit in balances)
