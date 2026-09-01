from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.service import record_generation_run
from sable_harbor.reporting_queries import named_queries, run_named_query


def test_all_required_named_queries_execute() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="test"
        )
        generate_standard(session)
        session.commit()
        names = named_queries()
        assert len(names) >= 20
        for name in names:
            result = run_named_query(session, name, run.id)
            assert isinstance(result, list), name
