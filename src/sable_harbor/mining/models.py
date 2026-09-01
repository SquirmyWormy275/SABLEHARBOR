from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from sable_harbor.accounting.models import Base


class MineProductionBatch(Base):
    __tablename__ = "mine_production_batch"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    site_id: Mapped[str] = mapped_column(ForeignKey("site.id"))
    batch_number: Mapped[str] = mapped_column(String(40), unique=True)
    production_date: Mapped[date] = mapped_column(Date)
    feed_tons: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    grade_fraction: Mapped[Decimal] = mapped_column(Numeric(12, 8))
    recovery_fraction: Mapped[Decimal] = mapped_column(Numeric(12, 8))
    pounds_u3o8: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    production_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    inventory_lot_id: Mapped[str] = mapped_column(ForeignKey("inventory_lot.id"))
    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))


class UraniumShipment(Base):
    __tablename__ = "uranium_shipment"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    production_batch_id: Mapped[str] = mapped_column(ForeignKey("mine_production_batch.id"))
    shipment_number: Mapped[str] = mapped_column(String(40), unique=True)
    shipment_date: Mapped[date] = mapped_column(Date)
    pounds_shipped: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    realized_price_per_lb: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    revenue: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    cost_of_sales: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    sale_journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))
    receipt_journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))
