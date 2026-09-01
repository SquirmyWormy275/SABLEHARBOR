from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import post_entry
from sable_harbor.accounting.models import Account, FactState, JournalEntry, JournalLine
from sable_harbor.core.ids import stable_id

from .models import Waybill


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
        segment_code="ARU_BST",
    )


def _post(
    session: Session,
    key: str,
    book_id: str,
    period_id: str,
    event_date: date,
    source_id: str,
    lines: list[JournalLine],
) -> JournalEntry:
    entry = JournalEntry(
        id=stable_id("journal", key),
        book_id=book_id,
        period_id=period_id,
        entry_date=event_date,
        description=key,
        source_type="waybill",
        source_id=source_id,
        lines=lines,
    )
    session.add(entry)
    session.flush()
    post_entry(session, entry)
    return entry


def operate_waybill(
    session: Session,
    *,
    entity_id: str,
    book_id: str,
    period_id: str,
    key: str,
    movement_date: date,
    carloads: int,
    tons: Decimal,
    route_miles: Decimal,
    base_rate: Decimal,
    fuel_surcharge: Decimal,
    fuel_gallons: Decimal,
    fuel_price: Decimal,
    crew_hours: Decimal,
    crew_rate: Decimal,
    intercompany: bool = False,
    custody_status: str = "COMPLETE",
) -> Waybill:
    if carloads <= 0 or tons <= 0 or route_miles <= 0:
        raise ValueError("Waybill operating quantities must be positive")
    revenue = (base_rate + fuel_surcharge).quantize(Decimal("0.0001"))
    fuel_cost = (fuel_gallons * fuel_price).quantize(Decimal("0.0001"))
    crew_cost = (crew_hours * crew_rate).quantize(Decimal("0.0001"))
    ton_miles = (tons * route_miles).quantize(Decimal("0.0001"))
    waybill_id = stable_id("waybill", key)
    revenue_entry = _post(
        session,
        f"WAYBILL_REVENUE:{key}",
        book_id,
        period_id,
        movement_date,
        waybill_id,
        [
            _line(f"{key}:AR", _account(session, "1100"), revenue, Decimal(0)),
            _line(
                f"{key}:REV",
                _account(session, "4090" if intercompany else "4040"),
                Decimal(0),
                revenue,
            ),
        ],
    )
    cost_entry = _post(
        session,
        f"WAYBILL_COST:{key}",
        book_id,
        period_id,
        movement_date,
        waybill_id,
        [
            _line(f"{key}:COST", _account(session, "5000"), fuel_cost + crew_cost, Decimal(0)),
            _line(f"{key}:AP", _account(session, "2100"), Decimal(0), fuel_cost + crew_cost),
        ],
    )
    receipt_entry = _post(
        session,
        f"WAYBILL_CASH:{key}",
        book_id,
        period_id,
        movement_date,
        waybill_id,
        [
            _line(f"{key}:CASH", _account(session, "1000"), revenue, Decimal(0)),
            _line(f"{key}:AR:CLEAR", _account(session, "1100"), Decimal(0), revenue),
        ],
    )
    waybill = Waybill(
        id=waybill_id,
        entity_id=entity_id,
        waybill_number=f"WB-{key}",
        movement_date=movement_date,
        carloads=carloads,
        tons=tons,
        route_miles=route_miles,
        ton_miles=ton_miles,
        base_rate=base_rate,
        fuel_surcharge=fuel_surcharge,
        revenue=revenue,
        fuel_gallons=fuel_gallons,
        fuel_cost=fuel_cost,
        crew_hours=crew_hours,
        crew_cost=crew_cost,
        intercompany=intercompany,
        custody_status=custody_status,
        revenue_journal_entry_id=revenue_entry.id,
        cost_journal_entry_id=cost_entry.id,
        receipt_journal_entry_id=receipt_entry.id,
    )
    session.add(waybill)
    return waybill
