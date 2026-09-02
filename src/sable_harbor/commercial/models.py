from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sable_harbor.accounting.models import Base, FactState, GenerationOwnedMixin


class Customer(Base):
    __tablename__ = "customer"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    segment: Mapped[str] = mapped_column(String(80))
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))


class Contract(GenerationOwnedMixin, Base):
    __tablename__ = "customer_contract"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customer.id"))
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    contract_number: Mapped[str] = mapped_column(String(80))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    transaction_price: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    __table_args__ = (UniqueConstraint("generation_run_id", "contract_number"),)


class PerformanceObligation(GenerationOwnedMixin, Base):
    __tablename__ = "performance_obligation"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    contract_id: Mapped[str] = mapped_column(ForeignKey("customer_contract.id"))
    name: Mapped[str] = mapped_column(String(200))
    revenue_method: Mapped[str] = mapped_column(String(40))
    allocated_price: Mapped[Decimal] = mapped_column(Numeric(20, 4))


class Invoice(GenerationOwnedMixin, Base):
    __tablename__ = "invoice"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    contract_id: Mapped[str] = mapped_column(ForeignKey("customer_contract.id"))
    invoice_number: Mapped[str] = mapped_column(String(80))
    invoice_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))
    total: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    status: Mapped[str] = mapped_column(String(30), default="ISSUED")
    journal_entry_id: Mapped[str | None] = mapped_column(ForeignKey("journal_entry.id"))
    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        foreign_keys="InvoiceLine.invoice_id",
    )
    __table_args__ = (UniqueConstraint("generation_run_id", "invoice_number"),)


class InvoiceLine(GenerationOwnedMixin, Base):
    __tablename__ = "invoice_line"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoice.id"))
    performance_obligation_id: Mapped[str] = mapped_column(ForeignKey("performance_obligation.id"))
    description: Mapped[str] = mapped_column(String(250))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    invoice: Mapped[Invoice] = relationship(back_populates="lines", foreign_keys=[invoice_id])


class RevenueRecognition(GenerationOwnedMixin, Base):
    __tablename__ = "revenue_recognition"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    performance_obligation_id: Mapped[str] = mapped_column(ForeignKey("performance_obligation.id"))
    recognition_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))


class CashReceipt(GenerationOwnedMixin, Base):
    __tablename__ = "cash_receipt"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoice.id"))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    currency: Mapped[str] = mapped_column(String(3))
    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))


class Engagement(GenerationOwnedMixin, Base):
    __tablename__ = "engagement"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    contract_id: Mapped[str] = mapped_column(ForeignKey("customer_contract.id"))
    engagement_code: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(200))
    billing_method: Mapped[str] = mapped_column(String(30))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    __table_args__ = (UniqueConstraint("generation_run_id", "engagement_code"),)


class ProjectTask(GenerationOwnedMixin, Base):
    __tablename__ = "project_task"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagement.id"))
    task_code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    __table_args__ = (UniqueConstraint("engagement_id", "task_code"),)


class TimeEntry(GenerationOwnedMixin, Base):
    __tablename__ = "time_entry"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("project_task.id"))
    worker_id: Mapped[str] = mapped_column(ForeignKey("worker.id"))
    work_date: Mapped[date] = mapped_column(Date)
    hours: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    bill_rate: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    cost_rate: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    status: Mapped[str] = mapped_column(String(24))


class ProjectCost(GenerationOwnedMixin, Base):
    __tablename__ = "project_cost"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagement.id"))
    time_entry_id: Mapped[str] = mapped_column(ForeignKey("time_entry.id"))
    cost_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))


class EngagementInvoiceLink(GenerationOwnedMixin, Base):
    __tablename__ = "engagement_invoice_link"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagement.id"))
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoice.id"))
    billed_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    billed_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
