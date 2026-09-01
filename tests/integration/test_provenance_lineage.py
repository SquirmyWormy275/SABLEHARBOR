from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from sable_harbor import schema as schema  # noqa: F401
from sable_harbor.accounting.models import Base, JournalEntry
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.models import GenerationRun, LineageEdge, ModelAssumption
from sable_harbor.provenance.service import (
    complete_generation_run,
    lineage_for,
    link_journals,
    record_generation_run,
    seed_provenance,
)


def test_assumptions_generation_and_journals_are_queryable() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        assert seed_provenance(session, Path("config/finance/assumptions/quantitative.yml")) == 8
        assert seed_provenance(session, Path("config/finance/assumptions/quantitative.yml")) == 0
        run = record_generation_run(
            session,
            profile="standard",
            scenario_code="base",
            seed=20260831,
            git_commit="test-commit",
        )
        generate_standard(session)
        edge_count = link_journals(session, run)
        complete_generation_run(session, run)
        session.commit()
        entry = session.scalars(select(JournalEntry).order_by(JournalEntry.id)).first()
        assert entry is not None
        assert edge_count > 0
        assert lineage_for(session, entry.id)
        assert session.scalar(select(func.count(ModelAssumption.id))) == 8
        assert session.scalar(select(func.count(GenerationRun.id))) == 1
        assert session.scalar(select(func.count(LineageEdge.id))) == edge_count
