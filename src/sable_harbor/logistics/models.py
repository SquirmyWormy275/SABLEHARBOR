from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from sable_harbor.accounting.models import Base


class Waybill(Base):
    __tablename__ = "waybill"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    waybill_number: Mapped[str] = mapped_column(String(40), unique=True)
    movement_date: Mapped[date] = mapped_column(Date)
    carloads: Mapped[int] = mapped_column()
    tons: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    route_miles: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    ton_miles: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    base_rate: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    fuel_surcharge: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    revenue: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    fuel_gallons: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    fuel_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    crew_hours: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    crew_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    intercompany: Mapped[bool] = mapped_column(Boolean, default=False)
    custody_status: Mapped[str] = mapped_column(String(24))
    revenue_journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))
    cost_journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))
    receipt_journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))
