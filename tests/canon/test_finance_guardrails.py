from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base, FactState, LegalEntity, Site
from sable_harbor.generation import generate_standard


def test_required_fact_states_are_complete() -> None:
    assert {state.value for state in FactState} == {
        "LOCKED_CANON",
        "PROVISIONAL_CANON",
        "OPEN_CANON",
        "SUPERSEDED",
        "LEGACY_CALIBRATION",
        "MODEL_PROPOSED",
        "SCENARIO_INPUT",
        "SYNTHETIC_INSTANCE",
        "DERIVED",
        "EXTERNAL_RESEARCH",
    }


def test_generated_structure_preserves_current_canon_boundaries() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        generate_standard(session)
        entities = {entity.code: entity for entity in session.scalars(select(LegalEntity))}
        assert {"SHI", "RWH", "ARU", "CONS"}.issubset(entities)
        assert all("EMBERLINE" not in entity.name.upper() for entity in entities.values())
        assert entities["RWH"].fact_state is FactState.MODEL_PROPOSED
        assert entities["ARU"].parent_id == entities["SHI"].id
        red_wash = session.scalar(select(Site).where(Site.code == "RED_WASH"))
        assert red_wash is not None
        assert red_wash.fact_state is FactState.LOCKED_CANON
