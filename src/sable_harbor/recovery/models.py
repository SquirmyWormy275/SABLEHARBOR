from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from sable_harbor.accounting.models import Base, GenerationOwnedMixin


class RecoveryRun(GenerationOwnedMixin, Base):
    __tablename__ = "recovery_run"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    run_number: Mapped[str] = mapped_column(String(40), unique=True)
    run_date: Mapped[date] = mapped_column(Date)
    host_operator_code: Mapped[str] = mapped_column(String(40))
    host_asset_owned: Mapped[bool] = mapped_column(Boolean, default=False)
    feed_tons: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    grade_fraction: Mapped[Decimal] = mapped_column(Numeric(12, 8))
    recovery_fraction: Mapped[Decimal] = mapped_column(Numeric(12, 8))
    recovered_units: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    operating_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    host_share: Mapped[Decimal] = mapped_column(Numeric(12, 8))
    gross_sale: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    host_share_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    production_journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))
    sale_journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))
