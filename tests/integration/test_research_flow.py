from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import trial_balance
from sable_harbor.accounting.models import Base, FiscalPeriod, LegalEntity
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.research.flows import run_atlas_evaluation, run_willow_experiment


def test_willow_and_atlas_cost_revenue_and_authority_boundaries() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session)
        entity_id = session.query(LegalEntity.id).scalar()
        period_id = session.query(FiscalPeriod.id).scalar()
        experiment = run_willow_experiment(
            session,
            entity_id=entity_id,
            book_id=book_id,
            period_id=period_id,
            key="MULE-01",
            experiment_date=date(2026, 8, 12),
            question="Can the sensor survive field vibration?",
            belief="Ruggedization helps",
            budget=Decimal("50000"),
            actual_cost=Decimal("42000"),
            observation="Qualified with operating-owner review",
            gate_decision="TRANSFER",
            transfer_target="PALE_SUN",
        )
        evaluation = run_atlas_evaluation(
            session,
            entity_id=entity_id,
            book_id=book_id,
            period_id=period_id,
            key="ATL-CASE-01",
            evaluation_date=date(2026, 8, 18),
            model_version="0.1",
            investigation_question="Which evidence changes the operating case?",
            compute_cost=Decimal("8000"),
            validation_cost=Decimal("12000"),
            customer_fee=Decimal("15000"),
        )
        session.commit()
        assert experiment.gate_decision == "TRANSFER"
        assert not evaluation.owns_final_decision
        balances = trial_balance(session, book_id)
        assert sum(debit for _, debit, _ in balances) == sum(credit for _, _, credit in balances)


def test_atlas_cannot_own_final_decision() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session, pytest.raises(ValueError, match="cannot own"):
        book_id = seed_smoke(session)
        run_atlas_evaluation(
            session,
            entity_id=session.query(LegalEntity.id).scalar(),
            book_id=book_id,
            period_id=session.query(FiscalPeriod.id).scalar(),
            key="INVALID",
            evaluation_date=date(2026, 8, 1),
            model_version="x",
            investigation_question="x",
            compute_cost=Decimal(1),
            validation_cost=Decimal(1),
            customer_fee=Decimal(1),
            owns_final_decision=True,
        )
