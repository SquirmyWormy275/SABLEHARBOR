from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import post_entry
from sable_harbor.accounting.models import (
    Account,
    FactState,
    FixedAsset,
    JournalEntry,
    JournalLine,
    Worker,
)
from sable_harbor.core.ids import stable_id

from .models import (
    DebtDraw,
    DebtFacility,
    DepreciationRecord,
    GoodsReceipt,
    InterestAccrual,
    PayrollLine,
    PayrollRun,
    PurchaseOrder,
    Vendor,
    VendorBill,
    VendorPayment,
)


def _account(session: Session, code: str) -> str:
    account = session.scalar(select(Account.id).where(Account.code == code))
    if account is None:
        raise ValueError(f"Missing posting account {code}")
    return account


def _line(key: str, account_id: str, debit: Decimal, credit: Decimal) -> JournalLine:
    return JournalLine(
        id=stable_id("journal_line", key),
        account_id=account_id,
        debit=debit,
        credit=credit,
        functional_amount=debit - credit,
        reporting_amount=debit - credit,
        fact_state=FactState.DERIVED,
    )


def _post(
    session: Session,
    *,
    key: str,
    book_id: str,
    period_id: str,
    event_date: date,
    description: str,
    source_type: str,
    source_id: str,
    lines: list[JournalLine],
) -> JournalEntry:
    entry = JournalEntry(
        id=stable_id("journal", key),
        book_id=book_id,
        period_id=period_id,
        entry_date=event_date,
        description=description,
        source_type=source_type,
        source_id=source_id,
        lines=lines,
    )
    session.add(entry)
    session.flush()
    post_entry(session, entry)
    return entry


def run_payroll(
    session: Session,
    *,
    entity_id: str,
    book_id: str,
    period_id: str,
    worker: Worker,
    pay_date: date,
    gross_pay: Decimal,
    employer_cost: Decimal,
) -> PayrollRun:
    key = f"{worker.id}:{pay_date.isoformat()}"
    run_id = stable_id("payroll_run", key)
    total = gross_pay + employer_cost
    entry = _post(
        session,
        key=f"PAYROLL:{key}",
        book_id=book_id,
        period_id=period_id,
        event_date=pay_date,
        description="Synthetic payroll run",
        source_type="payroll_run",
        source_id=run_id,
        lines=[
            _line(f"{key}:EXP", _account(session, "6100"), total, Decimal(0)),
            _line(f"{key}:CASH", _account(session, "1000"), Decimal(0), total),
        ],
    )
    run = PayrollRun(
        id=run_id,
        entity_id=entity_id,
        pay_date=pay_date,
        status="PAID",
        gross_pay=gross_pay,
        employer_cost=employer_cost,
        journal_entry_id=entry.id,
    )
    session.add_all(
        [
            run,
            PayrollLine(
                id=stable_id("payroll_line", key),
                payroll_run_id=run.id,
                worker_id=worker.id,
                gross_pay=gross_pay,
                employer_cost=employer_cost,
            ),
        ]
    )
    return run


def procure_and_pay_asset(
    session: Session,
    *,
    entity_id: str,
    book_id: str,
    period_id: str,
    key: str,
    event_date: date,
    amount: Decimal,
) -> tuple[VendorBill, VendorPayment, FixedAsset]:
    vendor = Vendor(
        id=stable_id("vendor", key),
        code=f"VEN-{key}",
        name=f"Synthetic vendor {key}",
        category="FIELD_EQUIPMENT",
    )
    po = PurchaseOrder(
        id=stable_id("purchase_order", key),
        entity_id=entity_id,
        vendor_id=vendor.id,
        po_number=f"PO-{key}",
        order_date=event_date,
        amount=amount,
        status="RECEIVED",
    )
    receipt = GoodsReceipt(
        id=stable_id("goods_receipt", key),
        purchase_order_id=po.id,
        receipt_date=event_date,
        amount=amount,
    )
    bill_id = stable_id("vendor_bill", key)
    bill_entry = _post(
        session,
        key=f"BILL:{key}",
        book_id=book_id,
        period_id=period_id,
        event_date=event_date,
        description=f"Asset vendor bill {key}",
        source_type="vendor_bill",
        source_id=bill_id,
        lines=[
            _line(f"{key}:ASSET", _account(session, "1500"), amount, Decimal(0)),
            _line(f"{key}:AP", _account(session, "2100"), Decimal(0), amount),
        ],
    )
    bill = VendorBill(
        id=bill_id,
        purchase_order_id=po.id,
        receipt_id=receipt.id,
        bill_number=f"BILL-{key}",
        bill_date=event_date,
        amount=amount,
        match_status="MATCHED",
        journal_entry_id=bill_entry.id,
    )
    payment_id = stable_id("vendor_payment", key)
    payment_entry = _post(
        session,
        key=f"PAYMENT:{key}",
        book_id=book_id,
        period_id=period_id,
        event_date=event_date,
        description=f"Vendor payment {key}",
        source_type="vendor_payment",
        source_id=payment_id,
        lines=[
            _line(f"{key}:AP:PAY", _account(session, "2100"), amount, Decimal(0)),
            _line(f"{key}:CASH:PAY", _account(session, "1000"), Decimal(0), amount),
        ],
    )
    payment = VendorPayment(
        id=payment_id,
        vendor_bill_id=bill.id,
        payment_date=event_date,
        amount=amount,
        journal_entry_id=payment_entry.id,
    )
    asset = FixedAsset(
        id=stable_id("fixed_asset", key),
        asset_number=f"FA-{key}",
        entity_id=entity_id,
        asset_class="LAB_EQUIPMENT",
        placed_in_service=event_date,
        cost=amount,
        useful_life_months=60,
        acquisition_layer=False,
        fact_state=FactState.SYNTHETIC_INSTANCE,
    )
    session.add_all([vendor, po, receipt, bill, payment, asset])
    return bill, payment, asset


def depreciate_asset(
    session: Session,
    *,
    asset: FixedAsset,
    book_id: str,
    period_id: str,
    depreciation_date: date,
) -> DepreciationRecord:
    amount = (asset.cost / Decimal(asset.useful_life_months)).quantize(Decimal("0.0001"))
    key = f"{asset.id}:{depreciation_date.isoformat()}"
    record_id = stable_id("depreciation", key)
    entry = _post(
        session,
        key=f"DEPR:{key}",
        book_id=book_id,
        period_id=period_id,
        event_date=depreciation_date,
        description=f"Depreciation {asset.asset_number}",
        source_type="depreciation",
        source_id=record_id,
        lines=[
            _line(f"{key}:EXP", _account(session, "6300"), amount, Decimal(0)),
            _line(f"{key}:ACC", _account(session, "1590"), Decimal(0), amount),
        ],
    )
    record = DepreciationRecord(
        id=record_id,
        asset_id=asset.id,
        period_code=depreciation_date.strftime("%Y-%m"),
        depreciation_date=depreciation_date,
        amount=amount,
        journal_entry_id=entry.id,
    )
    session.add(record)
    return record


def draw_debt_and_accrue_interest(
    session: Session,
    *,
    entity_id: str,
    book_id: str,
    period_id: str,
    key: str,
    event_date: date,
    principal: Decimal,
    annual_rate: Decimal,
) -> tuple[DebtDraw, InterestAccrual]:
    facility = DebtFacility(
        id=stable_id("debt_facility", key),
        entity_id=entity_id,
        facility_number=f"DEBT-{key}",
        commitment=principal,
        annual_rate=annual_rate,
    )
    draw_id = stable_id("debt_draw", key)
    draw_entry = _post(
        session,
        key=f"DEBT_DRAW:{key}",
        book_id=book_id,
        period_id=period_id,
        event_date=event_date,
        description=f"Debt draw {key}",
        source_type="debt_draw",
        source_id=draw_id,
        lines=[
            _line(f"{key}:CASH", _account(session, "1000"), principal, Decimal(0)),
            _line(f"{key}:DEBT", _account(session, "2500"), Decimal(0), principal),
        ],
    )
    draw = DebtDraw(
        id=draw_id,
        facility_id=facility.id,
        draw_date=event_date,
        principal=principal,
        journal_entry_id=draw_entry.id,
    )
    interest = (principal * annual_rate / Decimal(12)).quantize(Decimal("0.0001"))
    accrual_id = stable_id("interest_accrual", key)
    interest_entry = _post(
        session,
        key=f"INTEREST:{key}",
        book_id=book_id,
        period_id=period_id,
        event_date=event_date,
        description=f"Interest accrual {key}",
        source_type="interest_accrual",
        source_id=accrual_id,
        lines=[
            _line(f"{key}:INTEXP", _account(session, "7100"), interest, Decimal(0)),
            _line(f"{key}:INTPAY", _account(session, "2510"), Decimal(0), interest),
        ],
    )
    accrual = InterestAccrual(
        id=accrual_id,
        debt_draw_id=draw.id,
        accrual_date=event_date,
        amount=interest,
        journal_entry_id=interest_entry.id,
    )
    session.add_all([facility, draw, accrual])
    return draw, accrual
