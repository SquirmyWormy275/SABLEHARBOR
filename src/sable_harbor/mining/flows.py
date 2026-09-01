from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import post_entry
from sable_harbor.accounting.models import (
    Account,
    FactState,
    InventoryLot,
    JournalEntry,
    JournalLine,
)
from sable_harbor.core.ids import stable_id

from .models import MineProductionBatch, UraniumShipment


def _account(session: Session, code: str) -> str:
    value = session.scalar(select(Account.id).where(Account.code == code))
    if value is None:
        raise ValueError(f"Missing posting account {code}")
    return value


def _line(key: str, account: str, debit: Decimal, credit: Decimal) -> JournalLine:
    return JournalLine(
        id=stable_id("journal_line", key),
        account_id=account,
        debit=debit,
        credit=credit,
        functional_amount=debit - credit,
        reporting_amount=debit - credit,
        fact_state=FactState.DERIVED,
        segment_code="PALE_SUN",
    )


def _post(
    session: Session,
    *,
    key: str,
    book_id: str,
    period_id: str,
    event_date: date,
    source_type: str,
    source_id: str,
    lines: list[JournalLine],
) -> JournalEntry:
    entry = JournalEntry(
        id=stable_id("journal", key),
        book_id=book_id,
        period_id=period_id,
        entry_date=event_date,
        description=key,
        source_type=source_type,
        source_id=source_id,
        lines=lines,
    )
    session.add(entry)
    session.flush()
    post_entry(session, entry)
    return entry


def produce_concentrate(
    session: Session,
    *,
    entity_id: str,
    site_id: str,
    book_id: str,
    period_id: str,
    key: str,
    production_date: date,
    feed_tons: Decimal,
    grade_fraction: Decimal,
    recovery_fraction: Decimal,
    production_cost: Decimal,
) -> MineProductionBatch:
    pounds = (feed_tons * Decimal(2000) * grade_fraction * recovery_fraction).quantize(
        Decimal("0.0001")
    )
    lot = InventoryLot(
        id=stable_id("inventory_lot", key),
        lot_number=f"LOT-{key}",
        entity_id=entity_id,
        site_id=site_id,
        inventory_stage="CONCENTRATE",
        quantity=pounds,
        unit="LB_U3O8",
        carrying_value=production_cost,
        as_of_date=production_date,
        fact_state=FactState.SYNTHETIC_INSTANCE,
    )
    batch_id = stable_id("mine_production_batch", key)
    session.add(lot)
    entry = _post(
        session,
        key=f"MINE_PRODUCTION:{key}",
        book_id=book_id,
        period_id=period_id,
        event_date=production_date,
        source_type="mine_production_batch",
        source_id=batch_id,
        lines=[
            _line(f"{key}:INV", _account(session, "1200"), production_cost, Decimal(0)),
            _line(f"{key}:AP", _account(session, "2100"), Decimal(0), production_cost),
        ],
    )
    batch = MineProductionBatch(
        id=batch_id,
        entity_id=entity_id,
        site_id=site_id,
        batch_number=f"BATCH-{key}",
        production_date=production_date,
        feed_tons=feed_tons,
        grade_fraction=grade_fraction,
        recovery_fraction=recovery_fraction,
        pounds_u3o8=pounds,
        production_cost=production_cost,
        inventory_lot_id=lot.id,
        journal_entry_id=entry.id,
    )
    session.add(batch)
    return batch


def ship_and_collect(
    session: Session,
    *,
    batch: MineProductionBatch,
    book_id: str,
    period_id: str,
    shipment_date: date,
    pounds_shipped: Decimal,
    realized_price_per_lb: Decimal,
) -> UraniumShipment:
    if pounds_shipped <= 0 or pounds_shipped > batch.pounds_u3o8:
        raise ValueError("Shipment quantity must be positive and cannot exceed produced pounds")
    key = f"{batch.batch_number}:{shipment_date.isoformat()}"
    revenue = (pounds_shipped * realized_price_per_lb).quantize(Decimal("0.0001"))
    cost = (batch.production_cost * pounds_shipped / batch.pounds_u3o8).quantize(Decimal("0.0001"))
    shipment_id = stable_id("uranium_shipment", key)
    sale = _post(
        session,
        key=f"URANIUM_SALE:{key}",
        book_id=book_id,
        period_id=period_id,
        event_date=shipment_date,
        source_type="uranium_shipment",
        source_id=shipment_id,
        lines=[
            _line(f"{key}:AR", _account(session, "1100"), revenue, Decimal(0)),
            _line(f"{key}:REV", _account(session, "4030"), Decimal(0), revenue),
            _line(f"{key}:COGS", _account(session, "5000"), cost, Decimal(0)),
            _line(f"{key}:INV", _account(session, "1200"), Decimal(0), cost),
        ],
    )
    receipt = _post(
        session,
        key=f"URANIUM_CASH:{key}",
        book_id=book_id,
        period_id=period_id,
        event_date=shipment_date,
        source_type="uranium_cash_receipt",
        source_id=shipment_id,
        lines=[
            _line(f"{key}:CASH", _account(session, "1000"), revenue, Decimal(0)),
            _line(f"{key}:AR:CLEAR", _account(session, "1100"), Decimal(0), revenue),
        ],
    )
    shipment = UraniumShipment(
        id=shipment_id,
        production_batch_id=batch.id,
        shipment_number=f"SHIP-{key}",
        shipment_date=shipment_date,
        pounds_shipped=pounds_shipped,
        realized_price_per_lb=realized_price_per_lb,
        revenue=revenue,
        cost_of_sales=cost,
        sale_journal_entry_id=sale.id,
        receipt_journal_entry_id=receipt.id,
    )
    session.add(shipment)
    return shipment
