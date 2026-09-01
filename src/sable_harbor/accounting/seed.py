from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from sable_harbor.core.ids import stable_id

from .ledger import post_entry
from .models import (
    Account,
    AccountingBook,
    FactState,
    FiscalPeriod,
    JournalEntry,
    JournalLine,
    LegalEntity,
)


def seed_smoke(session: Session) -> str:
    entity_id = stable_id("entity", "SABLE_HARBOR_MODEL_PARENT")
    book_id = stable_id("book", "SABLE_HARBOR_MODEL_PARENT:PRIMARY_USD")
    period_id = stable_id("period", f"{book_id}:2026-08")
    cash_id = stable_id("account", "1000")
    receivable_id = stable_id("account", "1100")
    deferred_revenue_id = stable_id("account", "2200")
    equity_id = stable_id("account", "3000")
    revenue_id = stable_id("account", "4000")
    if session.get(LegalEntity, entity_id):
        return book_id
    session.add(
        LegalEntity(
            id=entity_id,
            code="SH-MODEL",
            name="Sable Harbor model parent",
            fact_state=FactState.MODEL_PROPOSED,
            effective_from=date(2016, 1, 1),
        )
    )
    session.add(AccountingBook(id=book_id, entity_id=entity_id, code="PRIMARY_USD"))
    session.add(
        FiscalPeriod(
            id=period_id,
            book_id=book_id,
            code="2026-08",
            starts_on=date(2026, 8, 1),
            ends_on=date(2026, 8, monthrange(2026, 8)[1]),
        )
    )
    session.add_all(
        [
            Account(
                id=cash_id,
                code="1000",
                name="Operating cash",
                account_class="ASSET",
                normal_balance="DEBIT",
            ),
            Account(
                id=receivable_id,
                code="1100",
                name="Trade accounts receivable",
                account_class="ASSET",
                normal_balance="DEBIT",
            ),
            Account(
                id=deferred_revenue_id,
                code="2200",
                name="Deferred revenue",
                account_class="LIABILITY",
                normal_balance="CREDIT",
            ),
            Account(
                id=equity_id,
                code="3000",
                name="Model opening equity",
                account_class="EQUITY",
                normal_balance="CREDIT",
            ),
            Account(
                id=revenue_id,
                code="4000",
                name="Foundry Field recurring platform revenue",
                account_class="REVENUE",
                normal_balance="CREDIT",
            ),
            Account(id=stable_id("account", "1500"), code="1500", name="Equipment",
                    account_class="ASSET", normal_balance="DEBIT"),
            Account(id=stable_id("account", "1590"), code="1590", name="Accumulated depreciation",
                    account_class="ASSET", normal_balance="CREDIT"),
            Account(id=stable_id("account", "2100"), code="2100", name="Trade accounts payable",
                    account_class="LIABILITY", normal_balance="CREDIT"),
            Account(id=stable_id("account", "2500"), code="2500", name="Long-term debt",
                    account_class="LIABILITY", normal_balance="CREDIT"),
            Account(id=stable_id("account", "2510"), code="2510", name="Accrued interest",
                    account_class="LIABILITY", normal_balance="CREDIT"),
            Account(id=stable_id("account", "6100"), code="6100", name="Payroll and benefits",
                    account_class="EXPENSE", normal_balance="DEBIT"),
            Account(id=stable_id("account", "6300"), code="6300", name="Depreciation expense",
                    account_class="EXPENSE", normal_balance="DEBIT"),
            Account(id=stable_id("account", "7100"), code="7100", name="Interest expense",
                    account_class="OTHER_EXPENSE", normal_balance="DEBIT"),
        ]
    )
    entry = JournalEntry(
        id=stable_id("journal", "SMOKE:OPENING_CAPITAL"),
        book_id=book_id,
        period_id=period_id,
        entry_date=date(2026, 8, 1),
        description="Synthetic opening capital",
        source_type="generation_event",
        source_id=stable_id("event", "SMOKE:OPENING_CAPITAL"),
        lines=[
            JournalLine(
                id=stable_id("line", "SMOKE:OPENING_CAPITAL:1"),
                account_id=cash_id,
                debit=Decimal("1000000.00"),
                credit=Decimal("0"),
                functional_amount=Decimal("1000000.00"),
                reporting_amount=Decimal("1000000.00"),
                fact_state=FactState.SYNTHETIC_INSTANCE,
            ),
            JournalLine(
                id=stable_id("line", "SMOKE:OPENING_CAPITAL:2"),
                account_id=equity_id,
                debit=Decimal("0"),
                credit=Decimal("1000000.00"),
                functional_amount=Decimal("-1000000.00"),
                reporting_amount=Decimal("-1000000.00"),
                fact_state=FactState.SYNTHETIC_INSTANCE,
            ),
        ],
    )
    session.add(entry)
    session.flush()
    post_entry(session, entry)
    return book_id
