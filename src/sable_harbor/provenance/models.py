from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from sable_harbor.accounting.models import Base, FactState


class SourceDocument(Base):
    __tablename__ = "source_document"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    path: Mapped[str] = mapped_column(String(500))
    branch: Mapped[str] = mapped_column(String(200))
    commit_sha: Mapped[str] = mapped_column(String(40))
    controlling: Mapped[bool] = mapped_column(Boolean)
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    __table_args__ = (UniqueConstraint("path", "commit_sha"),)


class ModelAssumption(Base):
    __tablename__ = "model_assumption"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    assumption_code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("source_document.id"))
    effective_from: Mapped[date | None] = mapped_column(Date)
    base_value: Mapped[str] = mapped_column(String(100))
    low_value: Mapped[str | None] = mapped_column(String(100))
    high_value: Mapped[str | None] = mapped_column(String(100))
    units: Mapped[str] = mapped_column(String(40))
    rationale: Mapped[str] = mapped_column(Text)
    sensitivity: Mapped[str] = mapped_column(String(40))
    reversible: Mapped[bool] = mapped_column(Boolean)
    decision_owner: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40))
    last_review_date: Mapped[date] = mapped_column(Date)


class Scenario(Base):
    __tablename__ = "scenario"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    fact_state: Mapped[FactState] = mapped_column(Enum(FactState))


class GenerationRun(Base):
    __tablename__ = "generation_run"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile: Mapped[str] = mapped_column(String(32))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario.id"))
    # These three ``actual_*`` column names are deprecated storage aliases retained
    # for pre-release Alembic-history compatibility. Application and output surfaces
    # use the explicitly synthetic properties below.
    actual_generation_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("generation_run.id"), index=True
    )
    actual_dataset_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    build_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    input_manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    seed: Mapped[int] = mapped_column(Integer)
    generator_version: Mapped[str] = mapped_column(String(40))
    git_commit: Mapped[str] = mapped_column(String(40))
    generator_source_digest: Mapped[str | None] = mapped_column(String(64))
    assumptions_digest: Mapped[str | None] = mapped_column(String(64))
    canon_source_lock_digest: Mapped[str | None] = mapped_column(String(64))
    actual_through: Mapped[date | None] = mapped_column(Date)
    forecast_from: Mapped[date | None] = mapped_column(Date)
    schema_head: Mapped[str | None] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24))
    __table_args__ = (
        UniqueConstraint("id", "actual_dataset_id", name="uq_generation_run_id_actual_dataset_id"),
        ForeignKeyConstraint(
            ["actual_generation_run_id", "actual_dataset_id"],
            ["generation_run.id", "generation_run.actual_dataset_id"],
            name="fk_generation_run_actual_dataset_compatible",
        ),
        CheckConstraint(
            "(status = 'RUNNING' AND completed_at IS NULL) OR "
            "(status = 'COMPLETED' AND completed_at IS NOT NULL)",
            name="ck_generation_run_lifecycle",
        ),
    )

    @property
    def shared_synthetic_calibration_run_id(self) -> str | None:
        return self.actual_generation_run_id

    @shared_synthetic_calibration_run_id.setter
    def shared_synthetic_calibration_run_id(self, value: str | None) -> None:
        self.actual_generation_run_id = value

    @property
    def synthetic_calibration_dataset_id(self) -> str:
        return self.actual_dataset_id

    @synthetic_calibration_dataset_id.setter
    def synthetic_calibration_dataset_id(self, value: str) -> None:
        self.actual_dataset_id = value

    @property
    def synthetic_calibration_through(self) -> date | None:
        return self.actual_through

    @synthetic_calibration_through.setter
    def synthetic_calibration_through(self, value: date | None) -> None:
        self.actual_through = value


class Artifact(Base):
    __tablename__ = "artifact"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    generation_run_id: Mapped[str] = mapped_column(ForeignKey("generation_run.id"))
    artifact_type: Mapped[str] = mapped_column(String(40))
    path: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str | None] = mapped_column(String(64))
    public_classification: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("generation_run_id", "path"),)


class LineageEdge(Base):
    __tablename__ = "lineage_edge"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    generation_run_id: Mapped[str] = mapped_column(ForeignKey("generation_run.id"))
    upstream_type: Mapped[str] = mapped_column(String(80))
    upstream_id: Mapped[str] = mapped_column(String(100))
    downstream_type: Mapped[str] = mapped_column(String(80))
    downstream_id: Mapped[str] = mapped_column(String(100))
    transformation: Mapped[str] = mapped_column(String(120))
    __table_args__ = (
        UniqueConstraint(
            "generation_run_id", "upstream_type", "upstream_id", "downstream_type", "downstream_id"
        ),
    )


class ValidationResult(Base):
    __tablename__ = "validation_result"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    generation_run_id: Mapped[str] = mapped_column(ForeignKey("generation_run.id"))
    check_code: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(16))
    observed_value: Mapped[str] = mapped_column(String(200))
    details: Mapped[str] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("generation_run_id", "check_code"),)
