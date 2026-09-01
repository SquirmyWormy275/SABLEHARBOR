from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class FactState(StrEnum):
    LOCKED_CANON = "LOCKED_CANON"
    PROVISIONAL_CANON = "PROVISIONAL_CANON"
    OPEN_CANON = "OPEN_CANON"
    SUPERSEDED = "SUPERSEDED"
    LEGACY_CALIBRATION = "LEGACY_CALIBRATION"
    MODEL_PROPOSED = "MODEL_PROPOSED"
    SCENARIO_INPUT = "SCENARIO_INPUT"
    SYNTHETIC_INSTANCE = "SYNTHETIC_INSTANCE"
    DERIVED = "DERIVED"
    EXTERNAL_RESEARCH = "EXTERNAL_RESEARCH"


class PeriodState(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class EntryState(StrEnum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"


class LegalEntity(Base):
    __tablename__ = "legal_entity"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    effective_from: Mapped[date] = mapped_column(Date)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("legal_entity.id"))
    jurisdiction: Mapped[str] = mapped_column(String(80), default="US-DE")


class AccountingBook(Base):
    __tablename__ = "accounting_book"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    code: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    __table_args__ = (UniqueConstraint("entity_id", "code"),)


class FiscalPeriod(Base):
    __tablename__ = "fiscal_period"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("accounting_book.id"))
    code: Mapped[str] = mapped_column(String(7))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    state: Mapped[PeriodState] = mapped_column(Enum(PeriodState), default=PeriodState.OPEN)
    __table_args__ = (UniqueConstraint("book_id", "code"),)


class Account(Base):
    __tablename__ = "account"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    account_class: Mapped[str] = mapped_column(String(32))
    normal_balance: Mapped[str] = mapped_column(String(6))


class JournalEntry(Base):
    __tablename__ = "journal_entry"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    generation_run_id: Mapped[str | None] = mapped_column(ForeignKey("generation_run.id"))
    book_id: Mapped[str] = mapped_column(ForeignKey("accounting_book.id"))
    period_id: Mapped[str] = mapped_column(ForeignKey("fiscal_period.id"))
    entry_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(300))
    source_type: Mapped[str] = mapped_column(String(80))
    source_id: Mapped[str] = mapped_column(String(100))
    state: Mapped[EntryState] = mapped_column(Enum(EntryState), default=EntryState.DRAFT)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reversal_of_id: Mapped[str | None] = mapped_column(ForeignKey("journal_entry.id"))
    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )


class JournalLine(Base):
    __tablename__ = "journal_line"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    debit: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    credit: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    transaction_currency: Mapped[str] = mapped_column(String(3), default="USD")
    functional_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    reporting_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    segment_code: Mapped[str | None] = mapped_column(String(32))
    cost_center_code: Mapped[str | None] = mapped_column(String(32))
    project_code: Mapped[str | None] = mapped_column(String(32))
    counterparty_entity_id: Mapped[str | None] = mapped_column(ForeignKey("legal_entity.id"))
    entry: Mapped[JournalEntry] = relationship(back_populates="lines")


class Site(Base):
    __tablename__ = "site"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    site_type: Mapped[str] = mapped_column(String(40))
    region: Mapped[str] = mapped_column(String(80))
    owner_entity_id: Mapped[str | None] = mapped_column(ForeignKey("legal_entity.id"))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))


class Worker(Base):
    __tablename__ = "worker"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    worker_number: Mapped[str] = mapped_column(String(20), unique=True)
    worker_type: Mapped[str] = mapped_column(String(20))
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    site_id: Mapped[str | None] = mapped_column(ForeignKey("site.id"))
    segment_code: Mapped[str] = mapped_column(String(32))
    function_code: Mapped[str] = mapped_column(String(40))
    annual_cost: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))


class BusinessParty(Base):
    __tablename__ = "business_party"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    party_type: Mapped[str] = mapped_column(String(20))
    segment_code: Mapped[str] = mapped_column(String(32))
    risk_tier: Mapped[str] = mapped_column(String(16))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))


class Contract(Base):
    __tablename__ = "contract"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    party_id: Mapped[str] = mapped_column(ForeignKey("business_party.id"))
    contract_type: Mapped[str] = mapped_column(String(32))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    committed_value: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))


class FixedAsset(Base):
    __tablename__ = "fixed_asset"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_number: Mapped[str] = mapped_column(String(32), unique=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    site_id: Mapped[str | None] = mapped_column(ForeignKey("site.id"))
    asset_class: Mapped[str] = mapped_column(String(40))
    placed_in_service: Mapped[date] = mapped_column(Date)
    cost: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    useful_life_months: Mapped[int] = mapped_column(Integer)
    acquisition_layer: Mapped[bool] = mapped_column(Boolean, default=False)
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))


class InventoryLot(Base):
    __tablename__ = "inventory_lot"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    lot_number: Mapped[str] = mapped_column(String(40), unique=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    site_id: Mapped[str] = mapped_column(ForeignKey("site.id"))
    inventory_stage: Mapped[str] = mapped_column(String(24))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    unit: Mapped[str] = mapped_column(String(16))
    carrying_value: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    as_of_date: Mapped[date] = mapped_column(Date)
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))


class ProductionRecord(Base):
    __tablename__ = "production_record"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    site_id: Mapped[str] = mapped_column(ForeignKey("site.id"))
    period_code: Mapped[str] = mapped_column(String(7))
    ore_tonnes: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    mill_feed_tonnes: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    concentrate_lbs: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    recovery_rate: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    __table_args__ = (UniqueConstraint("site_id", "period_code"),)


class FreightMovement(Base):
    __tablename__ = "freight_movement"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    movement_number: Mapped[str] = mapped_column(String(40), unique=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    customer_party_id: Mapped[str | None] = mapped_column(ForeignKey("business_party.id"))
    movement_date: Mapped[date] = mapped_column(Date)
    commodity: Mapped[str] = mapped_column(String(40))
    tonnes: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    revenue: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    intercompany: Mapped[bool] = mapped_column(Boolean, default=False)
    custody_status: Mapped[str] = mapped_column(String(24))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))


class EnvironmentalObligation(Base):
    __tablename__ = "environmental_obligation"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    site_id: Mapped[str] = mapped_column(ForeignKey("site.id"))
    obligation_type: Mapped[str] = mapped_column(String(32))
    undiscounted_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    discount_rate: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    recognized_liability: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    expected_settlement_year: Mapped[int] = mapped_column(Integer)
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))


class ScenarioValue(Base):
    __tablename__ = "scenario_value"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    generation_run_id: Mapped[str | None] = mapped_column(ForeignKey("generation_run.id"))
    scenario_code: Mapped[str] = mapped_column(String(20))
    metric_code: Mapped[str] = mapped_column(String(60))
    entity_code: Mapped[str] = mapped_column(String(32))
    period_code: Mapped[str] = mapped_column(String(16))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    unit: Mapped[str] = mapped_column(String(20))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    provenance: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint(
            "generation_run_id", "scenario_code", "metric_code", "entity_code", "period_code"
        ),
    )
