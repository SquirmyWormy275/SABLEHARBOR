from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class GenerationOwnedMixin:
    @declared_attr
    def generation_run_id(cls) -> Mapped[str]:
        return mapped_column(ForeignKey("generation_run.id"), nullable=False, index=True)


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


class EpistemicState(StrEnum):
    """Constitutional authority state for canon-sensitive master-data facets."""

    LOCKED = "LOCKED"
    DERIVED = "DERIVED"
    SUPPORTED_ESTIMATE = "SUPPORTED_ESTIMATE"
    PROVISIONAL_ASSUMPTION = "PROVISIONAL_ASSUMPTION"
    SCENARIO = "SCENARIO"
    OPEN = "OPEN"
    CONFLICT = "CONFLICT"
    SUPERSEDED = "SUPERSEDED"


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
    existence_state: Mapped[EpistemicState] = mapped_column(
        Enum(EpistemicState), default=EpistemicState.PROVISIONAL_ASSUMPTION
    )
    identity_state: Mapped[EpistemicState] = mapped_column(
        Enum(EpistemicState), default=EpistemicState.PROVISIONAL_ASSUMPTION
    )
    relationship_state: Mapped[EpistemicState] = mapped_column(
        Enum(EpistemicState), default=EpistemicState.PROVISIONAL_ASSUMPTION
    )
    effective_date_state: Mapped[EpistemicState] = mapped_column(
        Enum(EpistemicState), default=EpistemicState.PROVISIONAL_ASSUMPTION
    )
    effective_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    recorded_on: Mapped[date | None] = mapped_column(Date)
    known_on: Mapped[date | None] = mapped_column(Date)
    superseded_on: Mapped[date | None] = mapped_column(Date)
    source_reference: Mapped[str | None] = mapped_column(String(500))
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("legal_entity.id"))
    jurisdiction: Mapped[str] = mapped_column(String(80), default="OPEN")


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
    __table_args__ = (
        UniqueConstraint("book_id", "code"),
        UniqueConstraint("id", "book_id", name="uq_fiscal_period_id_book_id"),
        CheckConstraint("starts_on <= ends_on", name="ck_fiscal_period_date_order"),
    )


class GenerationPeriodClose(Base):
    __tablename__ = "generation_period_close"
    generation_run_id: Mapped[str] = mapped_column(
        ForeignKey("generation_run.id"), primary_key=True
    )
    period_id: Mapped[str] = mapped_column(ForeignKey("fiscal_period.id"), primary_key=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


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
    generation_run_id: Mapped[str] = mapped_column(
        ForeignKey("generation_run.id"), nullable=False, index=True
    )
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
    __table_args__ = (
        UniqueConstraint("id", "generation_run_id", name="uq_journal_entry_id_generation_run_id"),
        UniqueConstraint(
            "generation_run_id",
            "reversal_of_id",
            name="uq_journal_entry_generation_run_id_reversal_of_id",
        ),
        ForeignKeyConstraint(
            ["period_id", "book_id"],
            ["fiscal_period.id", "fiscal_period.book_id"],
            name="fk_journal_entry_period_book",
        ),
        ForeignKeyConstraint(
            ["reversal_of_id", "generation_run_id"],
            ["journal_entry.id", "journal_entry.generation_run_id"],
            name="fk_journal_entry_reversal_of_id_same_run",
        ),
        CheckConstraint(
            "(state = 'DRAFT' AND posted_at IS NULL) OR "
            "(state = 'POSTED' AND posted_at IS NOT NULL)",
            name="ck_journal_entry_lifecycle",
        ),
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
    __table_args__ = (
        CheckConstraint("debit >= 0 AND credit >= 0", name="ck_journal_line_nonnegative"),
        CheckConstraint(
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
            name="ck_journal_line_one_side",
        ),
        CheckConstraint(
            "functional_amount = debit - credit",
            name="ck_journal_line_functional_equation",
        ),
        CheckConstraint(
            "reporting_amount = functional_amount",
            name="ck_journal_line_reporting_equation",
        ),
    )


class Site(Base):
    __tablename__ = "site"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    site_type: Mapped[str] = mapped_column(String(40))
    region: Mapped[str] = mapped_column(String(80))
    owner_entity_id: Mapped[str | None] = mapped_column(ForeignKey("legal_entity.id"))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    effective_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    recorded_on: Mapped[date | None] = mapped_column(Date)
    known_on: Mapped[date | None] = mapped_column(Date)
    superseded_on: Mapped[date | None] = mapped_column(Date)
    source_reference: Mapped[str | None] = mapped_column(String(500))


class Worker(GenerationOwnedMixin, Base):
    __tablename__ = "worker"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    worker_number: Mapped[str] = mapped_column(String(20))
    worker_type: Mapped[str] = mapped_column(String(20))
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    site_id: Mapped[str | None] = mapped_column(ForeignKey("site.id"))
    segment_code: Mapped[str] = mapped_column(String(32))
    function_code: Mapped[str] = mapped_column(String(40))
    annual_cost: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    __table_args__ = (UniqueConstraint("generation_run_id", "worker_number"),)


class BusinessParty(GenerationOwnedMixin, Base):
    __tablename__ = "business_party"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(32))
    party_type: Mapped[str] = mapped_column(String(20))
    segment_code: Mapped[str] = mapped_column(String(32))
    risk_tier: Mapped[str] = mapped_column(String(16))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    __table_args__ = (UniqueConstraint("generation_run_id", "code"),)


class Contract(GenerationOwnedMixin, Base):
    __tablename__ = "contract"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    party_id: Mapped[str] = mapped_column(ForeignKey("business_party.id"))
    contract_type: Mapped[str] = mapped_column(String(32))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    committed_value: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    __table_args__ = (UniqueConstraint("generation_run_id", "code"),)


class FixedAsset(GenerationOwnedMixin, Base):
    __tablename__ = "fixed_asset"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_number: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    site_id: Mapped[str | None] = mapped_column(ForeignKey("site.id"))
    asset_class: Mapped[str] = mapped_column(String(40))
    placed_in_service: Mapped[date] = mapped_column(Date)
    cost: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    useful_life_months: Mapped[int] = mapped_column(Integer)
    acquisition_layer: Mapped[bool] = mapped_column(Boolean, default=False)
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    __table_args__ = (UniqueConstraint("generation_run_id", "asset_number"),)


class InventoryLot(GenerationOwnedMixin, Base):
    __tablename__ = "inventory_lot"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    lot_number: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    site_id: Mapped[str] = mapped_column(ForeignKey("site.id"))
    inventory_stage: Mapped[str] = mapped_column(String(24))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    unit: Mapped[str] = mapped_column(String(16))
    carrying_value: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    as_of_date: Mapped[date] = mapped_column(Date)
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    __table_args__ = (UniqueConstraint("generation_run_id", "lot_number"),)


class ProductionRecord(GenerationOwnedMixin, Base):
    __tablename__ = "production_record"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    site_id: Mapped[str] = mapped_column(ForeignKey("site.id"))
    period_code: Mapped[str] = mapped_column(String(7))
    ore_tonnes: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    mill_feed_tonnes: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    concentrate_lbs: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    recovery_rate: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    __table_args__ = (UniqueConstraint("generation_run_id", "site_id", "period_code"),)


class FreightMovement(GenerationOwnedMixin, Base):
    __tablename__ = "freight_movement"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    movement_number: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    customer_party_id: Mapped[str | None] = mapped_column(ForeignKey("business_party.id"))
    movement_date: Mapped[date] = mapped_column(Date)
    commodity: Mapped[str] = mapped_column(String(40))
    tonnes: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    revenue: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    intercompany: Mapped[bool] = mapped_column(Boolean, default=False)
    custody_status: Mapped[str] = mapped_column(String(24))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    __table_args__ = (UniqueConstraint("generation_run_id", "movement_number"),)


class EnvironmentalObligation(GenerationOwnedMixin, Base):
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
    generation_run_id: Mapped[str] = mapped_column(
        ForeignKey("generation_run.id"), nullable=False, index=True
    )
    scenario_code: Mapped[str] = mapped_column(String(20))
    metric_code: Mapped[str] = mapped_column(String(60))
    entity_code: Mapped[str] = mapped_column(String(32))
    period_code: Mapped[str] = mapped_column(String(64))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    unit: Mapped[str] = mapped_column(String(20))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    provenance: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint(
            "generation_run_id",
            "scenario_code",
            "metric_code",
            "entity_code",
            "period_code",
            name="uq_scenario_value_run_metric_entity_period",
        ),
    )
