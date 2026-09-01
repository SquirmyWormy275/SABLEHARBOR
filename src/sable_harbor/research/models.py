from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sable_harbor.accounting.models import Base


class WillowExperiment(Base):
    __tablename__ = "willow_experiment"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    experiment_number: Mapped[str] = mapped_column(String(40), unique=True)
    question: Mapped[str] = mapped_column(Text)
    belief: Mapped[str] = mapped_column(Text)
    experiment_date: Mapped[date] = mapped_column(Date)
    budget: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    observation: Mapped[str] = mapped_column(Text)
    gate_decision: Mapped[str] = mapped_column(String(16))
    transfer_target: Mapped[str | None] = mapped_column(String(40))
    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))


class AtlasEvaluation(Base):
    __tablename__ = "atlas_evaluation"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    evaluation_number: Mapped[str] = mapped_column(String(40), unique=True)
    evaluation_date: Mapped[date] = mapped_column(Date)
    model_version: Mapped[str] = mapped_column(String(60))
    investigation_question: Mapped[str] = mapped_column(Text)
    compute_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    validation_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    customer_fee: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    owns_final_decision: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))
    revenue_journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))
