from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import post_entry
from sable_harbor.accounting.models import FactState, JournalEntry, Worker
from sable_harbor.core.ids import stable_id

from .contract_to_cash import _line, account_id
from .models import (
    Contract,
    Engagement,
    EngagementInvoiceLink,
    Invoice,
    InvoiceLine,
    PerformanceObligation,
    ProjectCost,
    ProjectTask,
    TimeEntry,
)


def deliver_and_bill_engagement(
    session: Session,
    *,
    contract: Contract,
    worker: Worker,
    book_id: str,
    period_id: str,
    key: str,
    work_date: date,
    hours: Decimal,
    bill_rate: Decimal,
    cost_rate: Decimal,
    segment_code: str = "ADVISORY",
) -> tuple[Engagement, TimeEntry, Invoice]:
    engagement = Engagement(
        id=stable_id("engagement", key),
        contract_id=contract.id,
        engagement_code=f"ENG-{key}",
        name="Foundry Field implementation",
        billing_method="TIME_AND_MATERIALS",
        starts_on=work_date,
        ends_on=work_date + timedelta(days=30),
        fact_state=FactState.SYNTHETIC_INSTANCE,
    )
    session.add(engagement)
    session.flush()
    task = ProjectTask(
        id=stable_id("project_task", f"{key}:IMPLEMENT"),
        engagement_id=engagement.id,
        task_code="IMPLEMENT",
        name="Implementation and integration",
    )
    session.add(task)
    session.flush()
    time = TimeEntry(
        id=stable_id("time_entry", f"{key}:{work_date.isoformat()}"),
        task_id=task.id,
        worker_id=worker.id,
        work_date=work_date,
        hours=hours,
        bill_rate=bill_rate,
        cost_rate=cost_rate,
        status="APPROVED",
    )
    session.add(time)
    session.flush()
    revenue = hours * bill_rate
    cost = hours * cost_rate
    obligation = PerformanceObligation(
        id=stable_id("obligation", f"{key}:SERVICES"),
        contract_id=contract.id,
        name="Implementation services",
        revenue_method="AS_PERFORMED",
        allocated_price=revenue,
    )
    session.add(obligation)
    session.flush()
    cost_journal = JournalEntry(
        id=stable_id("journal", f"{key}:SERVICES_COST"),
        book_id=book_id,
        period_id=period_id,
        entry_date=work_date,
        description=f"Engagement labor cost {engagement.engagement_code}",
        source_type="project_cost",
        source_id=stable_id("project_cost", key),
        lines=[
            _line(f"{key}:COST:DR", account_id(session, "5000"), cost, Decimal(0), segment_code),
            _line(f"{key}:COST:CR", account_id(session, "2000"), Decimal(0), cost, segment_code),
        ],
    )
    project_cost = ProjectCost(
        id=cost_journal.source_id,
        engagement_id=engagement.id,
        time_entry_id=time.id,
        cost_date=work_date,
        amount=cost,
        journal_entry_id=cost_journal.id,
    )
    session.add_all([cost_journal, project_cost])
    session.flush()
    invoice = Invoice(
        id=stable_id("invoice", f"{key}:SERVICES"),
        contract_id=contract.id,
        invoice_number=f"INV-{key}-SERVICES",
        invoice_date=work_date,
        due_date=work_date + timedelta(days=30),
        currency="USD",
        total=revenue,
        lines=[
            InvoiceLine(
                id=stable_id("invoice_line", f"{key}:SERVICES"),
                performance_obligation_id=obligation.id,
                description="Approved implementation time",
                amount=revenue,
            )
        ],
    )
    billing_journal = JournalEntry(
        id=stable_id("journal", f"{key}:SERVICES_BILLING"),
        book_id=book_id,
        period_id=period_id,
        entry_date=work_date,
        description=f"Engagement billing {engagement.engagement_code}",
        source_type="engagement_invoice",
        source_id=invoice.id,
        lines=[
            _line(f"{key}:BILL:DR", account_id(session, "1100"), revenue, Decimal(0), segment_code),
            _line(f"{key}:BILL:CR", account_id(session, "4010"), Decimal(0), revenue, segment_code),
        ],
    )
    invoice.journal_entry_id = billing_journal.id
    session.add_all([invoice, billing_journal])
    session.flush()
    link = EngagementInvoiceLink(
        id=stable_id("engagement_invoice_link", key),
        engagement_id=engagement.id,
        invoice_id=invoice.id,
        billed_hours=hours,
        billed_amount=revenue,
    )
    session.add(link)
    session.flush()
    post_entry(session, cost_journal)
    post_entry(session, billing_journal)
    return engagement, time, invoice
