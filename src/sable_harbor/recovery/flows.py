from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import post_entry
from sable_harbor.accounting.models import Account, FactState, JournalEntry, JournalLine
from sable_harbor.core.ids import stable_id

from .models import RecoveryRun


def _account(session: Session, code: str) -> str:
    result = session.scalar(select(Account.id).where(Account.code == code))
    if result is None:
        raise ValueError(f"Missing posting account {code}")
    return result


def _line(key: str, account: str, debit: Decimal, credit: Decimal) -> JournalLine:
    return JournalLine(
        id=stable_id("journal_line", key),
        account_id=account,
        debit=debit,
        credit=credit,
        functional_amount=debit - credit,
        reporting_amount=debit - credit,
        fact_state=FactState.DERIVED,
        segment_code="CRADLE",
    )


def _post(
    session: Session,
    key: str,
    book_id: str,
    period_id: str,
    run_date: date,
    run_id: str,
    lines: list[JournalLine],
) -> JournalEntry:
    entry = JournalEntry(
        id=stable_id("journal", key),
        book_id=book_id,
        period_id=period_id,
        entry_date=run_date,
        description=key,
        source_type="recovery_run",
        source_id=run_id,
        lines=lines,
    )
    session.add(entry)
    session.flush()
    post_entry(session, entry)
    return entry


def execute_recovery_run(
    session: Session,
    *,
    entity_id: str,
    book_id: str,
    period_id: str,
    key: str,
    run_date: date,
    feed_tons: Decimal,
    grade_fraction: Decimal,
    recovery_fraction: Decimal,
    price_per_unit: Decimal,
    host_share: Decimal,
    operating_cost: Decimal,
    host_asset_owned: bool = False,
) -> RecoveryRun:
    if host_asset_owned:
        raise ValueError("Cradle base flow cannot own the host asset")
    if not Decimal(0) <= host_share <= Decimal(1):
        raise ValueError("Host share must be between zero and one")
    recovered = (feed_tons * Decimal(2000) * grade_fraction * recovery_fraction).quantize(
        Decimal("0.0001")
    )
    gross_sale = (recovered * price_per_unit).quantize(Decimal("0.0001"))
    host_amount = (gross_sale * host_share).quantize(Decimal("0.0001"))
    run_id = stable_id("recovery_run", key)
    production = _post(
        session,
        f"CRADLE_PRODUCTION:{key}",
        book_id,
        period_id,
        run_date,
        run_id,
        [
            _line(f"{key}:INV", _account(session, "1200"), operating_cost, Decimal(0)),
            _line(f"{key}:AP", _account(session, "2100"), Decimal(0), operating_cost),
        ],
    )
    sale = _post(
        session,
        f"CRADLE_SALE:{key}",
        book_id,
        period_id,
        run_date,
        run_id,
        [
            _line(f"{key}:AR", _account(session, "1100"), gross_sale, Decimal(0)),
            _line(f"{key}:REV", _account(session, "4050"), Decimal(0), gross_sale),
            _line(f"{key}:COST", _account(session, "5000"), operating_cost, Decimal(0)),
            _line(f"{key}:INV:OUT", _account(session, "1200"), Decimal(0), operating_cost),
            _line(f"{key}:HOST", _account(session, "5000"), host_amount, Decimal(0)),
            _line(f"{key}:HOST:AP", _account(session, "2100"), Decimal(0), host_amount),
        ],
    )
    run = RecoveryRun(
        id=run_id,
        entity_id=entity_id,
        run_number=f"CR-{key}",
        run_date=run_date,
        host_operator_code="SYNTHETIC_HOST",
        host_asset_owned=False,
        feed_tons=feed_tons,
        grade_fraction=grade_fraction,
        recovery_fraction=recovery_fraction,
        recovered_units=recovered,
        operating_cost=operating_cost,
        host_share=host_share,
        gross_sale=gross_sale,
        host_share_amount=host_amount,
        production_journal_entry_id=production.id,
        sale_journal_entry_id=sale.id,
    )
    session.add(run)
    return run
