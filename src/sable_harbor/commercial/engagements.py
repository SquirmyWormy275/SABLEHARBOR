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
    task = ProjectTask(
        id=stable_id("project_task", f"{key}:IMPLEMENT"),
        engagement_id=engagement.id,
        task_code="IMPLEMENT",
        name="Implementation and integration",
    )
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
    revenue = hours * bill_rate
    cost = hours * cost_rate
    obligation = PerformanceObligation(
        id=stable_id("obligation", f"{key}:SERVICES"),
        contract_id=contract.id,
        name="Implementation services",
        revenue_method="AS_PERFORMED",
        allocated_price=revenue,
    )
    cost_journal = JournalEntry(
        id=stable_id("journal", f"{key}:SERVICES_COST"),
        book_id=book_id,
        period_id=period_id,
        entry_date=work_date,
        description=f"Engagement labor cost {engagement.engagement_code}",
        source_type="project_cost",
        source_id=stable_id("project_cost", key),
        lines=[
            _line(f"{key}:COST:DR", account_id(session, "5000"), cost, Decimal(0)),
            _line(f"{key}:COST:CR", account_id(session, "2000"), Decimal(0), cost),
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
            _line(f"{key}:BILL:DR", account_id(session, "1100"), revenue, Decimal(0)),
            _line(f"{key}:BILL:CR", account_id(session, "4010"), Decimal(0), revenue),
        ],
    )
    invoice.journal_entry_id = billing_journal.id
    link = EngagementInvoiceLink(
        id=stable_id("engagement_invoice_link", key),
        engagement_id=engagement.id,
        invoice_id=invoice.id,
        billed_hours=hours,
        billed_amount=revenue,
    )
    session.add_all(
        [
            engagement,
            task,
            time,
            obligation,
            cost_journal,
            project_cost,
            invoice,
            billing_journal,
            link,
        ]
    )
    session.flush()
    post_entry(session, cost_journal)
    post_entry(session, billing_journal)
    return engagement, time, invoice
