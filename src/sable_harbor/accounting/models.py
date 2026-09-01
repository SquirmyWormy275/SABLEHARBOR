from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
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
    entry: Mapped[JournalEntry] = relationship(back_populates="lines")
