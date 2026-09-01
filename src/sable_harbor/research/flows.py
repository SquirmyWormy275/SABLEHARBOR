from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import post_entry
from sable_harbor.accounting.models import Account, FactState, JournalEntry, JournalLine
from sable_harbor.core.ids import stable_id

from .models import AtlasEvaluation, WillowExperiment

GATE_DECISIONS = {"CONTINUE", "CHANGE", "TRANSFER", "KILL"}


def _account(session: Session, code: str) -> str:
    result = session.scalar(select(Account.id).where(Account.code == code))
    if result is None:
        raise ValueError(f"Missing posting account {code}")
    return result


def _line(key: str, account: str, debit: Decimal, credit: Decimal, segment: str) -> JournalLine:
    return JournalLine(
        id=stable_id("journal_line", key),
        account_id=account,
        debit=debit,
        credit=credit,
        functional_amount=debit - credit,
        reporting_amount=debit - credit,
        fact_state=FactState.DERIVED,
        segment_code=segment,
    )


def _post(
    session: Session,
    *,
    key: str,
    book_id: str,
    period_id: str,
    event_date: date,
    source_type: str,
    source_id: str,
    lines: list[JournalLine],
) -> JournalEntry:
    entry = JournalEntry(
        id=stable_id("journal", key),
        book_id=book_id,
        period_id=period_id,
        entry_date=event_date,
        description=key,
        source_type=source_type,
        source_id=source_id,
        lines=lines,
    )
    session.add(entry)
    session.flush()
    post_entry(session, entry)
    return entry


def run_willow_experiment(
    session: Session,
    *,
    entity_id: str,
    book_id: str,
    period_id: str,
    key: str,
    experiment_date: date,
    question: str,
    belief: str,
    budget: Decimal,
    actual_cost: Decimal,
    observation: str,
    gate_decision: str,
    transfer_target: str | None = None,
) -> WillowExperiment:
    if gate_decision not in GATE_DECISIONS:
        raise ValueError("Willow gate must continue, change, transfer, or kill")
    if gate_decision == "TRANSFER" and not transfer_target:
        raise ValueError("A Willow transfer requires an operating or product target")
    experiment_id = stable_id("willow_experiment", key)
    entry = _post(
        session,
        key=f"WILLOW:{key}",
        book_id=book_id,
        period_id=period_id,
        event_date=experiment_date,
        source_type="willow_experiment",
        source_id=experiment_id,
        lines=[
            _line(f"{key}:RND", _account(session, "6000"), actual_cost, Decimal(0), "WILLOW"),
            _line(f"{key}:AP", _account(session, "2100"), Decimal(0), actual_cost, "WILLOW"),
        ],
    )
    experiment = WillowExperiment(
        id=experiment_id,
        entity_id=entity_id,
        experiment_number=f"WIL-{key}",
        question=question,
        belief=belief,
        experiment_date=experiment_date,
        budget=budget,
        actual_cost=actual_cost,
        observation=observation,
        gate_decision=gate_decision,
        transfer_target=transfer_target,
        journal_entry_id=entry.id,
    )
    session.add(experiment)
    return experiment


def run_atlas_evaluation(
    session: Session,
    *,
    entity_id: str,
    book_id: str,
    period_id: str,
    key: str,
    evaluation_date: date,
    model_version: str,
    investigation_question: str,
    compute_cost: Decimal,
    validation_cost: Decimal,
    customer_fee: Decimal,
    owns_final_decision: bool = False,
) -> AtlasEvaluation:
    if owns_final_decision:
        raise ValueError("Atlas cannot own the final operating or capital decision")
    evaluation_id = stable_id("atlas_evaluation", key)
    total_cost = compute_cost + validation_cost
    cost_entry = _post(
        session,
        key=f"ATLAS_COST:{key}",
        book_id=book_id,
        period_id=period_id,
        event_date=evaluation_date,
        source_type="atlas_evaluation",
        source_id=evaluation_id,
        lines=[
            _line(f"{key}:RND", _account(session, "6000"), total_cost, Decimal(0), "ATLAS"),
            _line(f"{key}:AP", _account(session, "2100"), Decimal(0), total_cost, "ATLAS"),
        ],
    )
    revenue_entry = _post(
        session,
        key=f"ATLAS_REVENUE:{key}",
        book_id=book_id,
        period_id=period_id,
        event_date=evaluation_date,
        source_type="atlas_customer_fee",
        source_id=evaluation_id,
        lines=[
            _line(f"{key}:CASH", _account(session, "1000"), customer_fee, Decimal(0), "ATLAS"),
            _line(f"{key}:REV", _account(session, "4020"), Decimal(0), customer_fee, "ATLAS"),
        ],
    )
    evaluation = AtlasEvaluation(
        id=evaluation_id,
        entity_id=entity_id,
        evaluation_number=f"ATL-{key}",
        evaluation_date=evaluation_date,
        model_version=model_version,
        investigation_question=investigation_question,
        compute_cost=compute_cost,
        validation_cost=validation_cost,
        customer_fee=customer_fee,
        owns_final_decision=False,
        cost_journal_entry_id=cost_entry.id,
        revenue_journal_entry_id=revenue_entry.id,
    )
    session.add(evaluation)
    return evaluation
