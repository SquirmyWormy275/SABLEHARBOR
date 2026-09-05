from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import (
    AccountingBook,
    Base,
    EpistemicState,
    FactState,
    FixedAsset,
    FreightMovement,
    JournalEntry,
    JournalLine,
    LegalEntity,
    Site,
    Worker,
)
from sable_harbor.generation import generate_standard
from sable_harbor.logistics.models import Waybill
from sable_harbor.provenance.service import record_generation_run


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
    assert {state.value for state in EpistemicState} == {
        "LOCKED",
        "DERIVED",
        "SUPPORTED_ESTIMATE",
        "PROVISIONAL_ASSUMPTION",
        "SCENARIO",
        "OPEN",
        "CONFLICT",
        "SUPERSEDED",
    }


def test_generated_structure_preserves_current_canon_boundaries() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="a" * 40
        )
        generate_standard(session)
        entities = {entity.code: entity for entity in session.scalars(select(LegalEntity))}
        assert {"SHI", "RWH", "ARU", "BST"}.issubset(entities)
        assert "CONS" not in entities
        assert all("EMBERLINE" not in entity.name.upper() for entity in entities.values())
        assert entities["RWH"].fact_state is FactState.MODEL_PROPOSED
        assert entities["ARU"].parent_id == entities["SHI"].id
        assert entities["BST"].parent_id == entities["ARU"].id
        for code in ("SHI", "RWH", "ARU", "BST"):
            assert entities[code].jurisdiction == "OPEN"
            assert entities[code].existence_state is EpistemicState.LOCKED
            assert entities[code].identity_state is EpistemicState.OPEN
            assert entities[code].relationship_state is EpistemicState.LOCKED
            assert entities[code].effective_date_state is EpistemicState.PROVISIONAL_ASSUMPTION
            assert entities[code].recorded_on == date(2026, 9, 5)
            assert entities[code].known_on == date(2026, 9, 3)
            assert entities[code].source_reference
        primary_books = {
            entity.code: book
            for entity, book in session.execute(
                select(LegalEntity, AccountingBook)
                .join(AccountingBook, AccountingBook.entity_id == LegalEntity.id)
                .where(AccountingBook.code == "PRIMARY_USD")
            )
        }
        assert {"SHI", "RWH", "ARU", "BST"}.issubset(primary_books)
        railway_asset_entities = set(
            session.scalars(
                select(LegalEntity.code)
                .join(FixedAsset, FixedAsset.entity_id == LegalEntity.id)
                .where(FixedAsset.asset_class.in_(("TRACK_AND_TERMINALS", "ROLLING_STOCK")))
            )
        )
        railway_worker_entities = set(
            session.scalars(
                select(LegalEntity.code)
                .join(Worker, Worker.entity_id == LegalEntity.id)
                .where(Worker.function_code == "RAILWAY_OPERATIONS")
            )
        )
        freight_movement_entities = set(
            session.scalars(
                select(LegalEntity.code).join(
                    FreightMovement, FreightMovement.entity_id == LegalEntity.id
                )
            )
        )
        waybill_entities = set(
            session.scalars(
                select(LegalEntity.code).join(Waybill, Waybill.entity_id == LegalEntity.id)
            )
        )
        waybill_book_entities = set(
            session.scalars(
                select(LegalEntity.code)
                .join(AccountingBook, AccountingBook.entity_id == LegalEntity.id)
                .join(JournalEntry, JournalEntry.book_id == AccountingBook.id)
                .where(JournalEntry.source_type == "waybill")
            )
        )
        assert railway_asset_entities == {"BST"}
        assert railway_worker_entities == {"BST"}
        assert freight_movement_entities == {"BST"}
        assert waybill_entities == {"BST"}
        assert waybill_book_entities == {"BST"}
        bst_monthly_segments = set(
            session.scalars(
                select(JournalLine.segment_code)
                .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
                .join(AccountingBook, AccountingBook.id == JournalEntry.book_id)
                .where(
                    AccountingBook.entity_id == entities["BST"].id,
                    JournalEntry.description.like("Monthly generated operating control%"),
                )
            )
        )
        assert bst_monthly_segments == {"ARU_BST"}
        assert session.query(Worker).filter(Worker.function_code == "RAILWAY_OPERATIONS").count()
        assert (
            session.query(FixedAsset)
            .filter(FixedAsset.asset_class.in_(("TRACK_AND_TERMINALS", "ROLLING_STOCK")))
            .count()
        )
        red_wash = session.scalar(select(Site).where(Site.code == "RED_WASH"))
        assert red_wash is not None
        assert red_wash.fact_state is FactState.LOCKED_CANON
        pittsburgh = session.scalar(select(Site).where(Site.code == "PIT"))
        assert pittsburgh is not None
        assert pittsburgh.fact_state is FactState.LOCKED_CANON
