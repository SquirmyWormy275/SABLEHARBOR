from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import post_entry
from sable_harbor.accounting.models import Account, FactState, JournalEntry, JournalLine
from sable_harbor.core.ids import stable_id

from .models import (
    CashReceipt,
    Contract,
    Customer,
    Invoice,
    InvoiceLine,
    PerformanceObligation,
    RevenueRecognition,
)


def account_id(session: Session, code: str) -> str:
    return session.scalar(select(Account.id).where(Account.code == code)) or _missing(code)


def _missing(code: str) -> str:
    raise ValueError(f"Missing posting account {code}")


def _line(
    key: str,
    account: str,
    debit: Decimal,
    credit: Decimal,
) -> JournalLine:
    signed = debit - credit
    return JournalLine(
        id=stable_id("journal_line", key),
        account_id=account,
        debit=debit,
        credit=credit,
        functional_amount=signed,
        reporting_amount=signed,
        fact_state=FactState.DERIVED,
    )


def create_foundry_contract_flow(
    session: Session,
    *,
    book_id: str,
    entity_id: str,
    period_id: str,
    natural_key: str,
    invoice_date: date,
    annual_value: Decimal,
) -> tuple[Contract, Invoice]:
    customer = Customer(
        id=stable_id("customer", natural_key),
        name=f"Synthetic customer {natural_key}",
        segment="MID_TIER_MINER",
        fact_state=FactState.SYNTHETIC_INSTANCE,
    )
    contract = Contract(
        id=stable_id("contract", natural_key),
        customer_id=customer.id,
        entity_id=entity_id,
        contract_number=f"CTR-{natural_key}",
        starts_on=invoice_date,
        ends_on=(
            date(invoice_date.year + 1, invoice_date.month, invoice_date.day) - timedelta(days=1)
        ),
        transaction_price=annual_value,
        fact_state=FactState.SYNTHETIC_INSTANCE,
    )
    obligation = PerformanceObligation(
        id=stable_id("obligation", f"{natural_key}:PLATFORM"),
        contract_id=contract.id,
        name="Foundry Field platform access",
        revenue_method="RATABLE_MONTHLY",
        allocated_price=annual_value,
    )
    invoice = Invoice(
        id=stable_id("invoice", natural_key),
        contract_id=contract.id,
        invoice_number=f"INV-{natural_key}",
        invoice_date=invoice_date,
        due_date=invoice_date + timedelta(days=30),
        currency="USD",
        total=annual_value,
        lines=[
            InvoiceLine(
                id=stable_id("invoice_line", natural_key),
                performance_obligation_id=obligation.id,
                description="Annual Foundry Field platform access",
                amount=annual_value,
            )
        ],
    )
    journal = JournalEntry(
        id=stable_id("journal", f"{natural_key}:INVOICE"),
        book_id=book_id,
        period_id=period_id,
        entry_date=invoice_date,
        description=f"Invoice {invoice.invoice_number}",
        source_type="invoice",
        source_id=invoice.id,
        lines=[
            _line(f"{natural_key}:INV:AR", account_id(session, "1100"), annual_value, Decimal(0)),
            _line(
                f"{natural_key}:INV:DEFREV",
                account_id(session, "2200"),
                Decimal(0),
                annual_value,
            ),
        ],
    )
    invoice.journal_entry_id = journal.id
    session.add_all([customer, contract, obligation, invoice, journal])
    session.flush()
    post_entry(session, journal)
    return contract, invoice


def recognize_month(
    session: Session,
    *,
    obligation: PerformanceObligation,
    book_id: str,
    period_id: str,
    recognition_date: date,
    amount: Decimal,
) -> RevenueRecognition:
    key = f"{obligation.id}:{recognition_date.isoformat()}"
    journal = JournalEntry(
        id=stable_id("journal", f"REVENUE:{key}"),
        book_id=book_id,
        period_id=period_id,
        entry_date=recognition_date,
        description=f"Revenue recognition {obligation.name}",
        source_type="revenue_recognition",
        source_id=stable_id("revenue_recognition", key),
        lines=[
            _line(f"{key}:DR", account_id(session, "2200"), amount, Decimal(0)),
            _line(f"{key}:CR", account_id(session, "4000"), Decimal(0), amount),
        ],
    )
    recognition = RevenueRecognition(
        id=journal.source_id,
        performance_obligation_id=obligation.id,
        recognition_date=recognition_date,
        amount=amount,
        journal_entry_id=journal.id,
    )
    session.add_all([journal, recognition])
    session.flush()
    post_entry(session, journal)
    return recognition


def receive_cash(
    session: Session,
    *,
    invoice: Invoice,
    book_id: str,
    period_id: str,
    receipt_date: date,
) -> CashReceipt:
    key = invoice.id
    journal = JournalEntry(
        id=stable_id("journal", f"RECEIPT:{key}"),
        book_id=book_id,
        period_id=period_id,
        entry_date=receipt_date,
        description=f"Receipt for {invoice.invoice_number}",
        source_type="cash_receipt",
        source_id=stable_id("cash_receipt", key),
        lines=[
            _line(f"{key}:CASH", account_id(session, "1000"), invoice.total, Decimal(0)),
            _line(f"{key}:AR", account_id(session, "1100"), Decimal(0), invoice.total),
        ],
    )
    receipt = CashReceipt(
        id=journal.source_id,
        invoice_id=invoice.id,
        received_at=datetime.combine(receipt_date, datetime.min.time(), tzinfo=UTC),
        amount=invoice.total,
        currency=invoice.currency,
        journal_entry_id=journal.id,
    )
    invoice.status = "PAID"
    session.add_all([journal, receipt])
    session.flush()
    post_entry(session, journal)
    return receipt
