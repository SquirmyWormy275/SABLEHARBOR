from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import (
    Account,
    AccountingBook,
    Base,
    FiscalPeriod,
    InventoryLot,
    JournalEntry,
    JournalLine,
    LegalEntity,
    ScenarioValue,
    Site,
)
from sable_harbor.commercial.models import CashReceipt, Engagement, RevenueRecognition
from sable_harbor.commercial.models import Contract as CustomerContract
from sable_harbor.generation import generate_standard
from sable_harbor.logistics.models import Waybill
from sable_harbor.mining.models import MineProductionBatch, UraniumShipment
from sable_harbor.operations.models import (
    DebtDraw,
    DebtRepayment,
    DepreciationRecord,
    PayrollRun,
    VendorBill,
    VendorPayment,
)
from sable_harbor.provenance.service import record_generation_run
from sable_harbor.recovery.models import RecoveryRun
from sable_harbor.research.models import AtlasEvaluation, WillowExperiment


def test_standard_generation_has_48_months_actual_forecast_and_is_idempotent() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="a" * 40
        )
        first = generate_standard(session)
        session.commit()
        first_entries = session.scalar(select(func.count(JournalEntry.id)))

        rwh = session.scalar(select(LegalEntity).where(LegalEntity.code == "RWH"))
        railway_site = session.scalar(select(Site).where(Site.code == "ARU_HUB"))
        cash_account = session.scalar(select(Account).where(Account.code == "1000"))
        consolidation_book = session.scalar(
            select(AccountingBook).where(AccountingBook.code == "CONSOLIDATION_USD")
        )
        assert rwh is not None
        assert railway_site is not None
        assert cash_account is not None
        assert consolidation_book is not None
        rwh.name = "Stale asserted Red Wash legal name"
        rwh.jurisdiction = "US-WY"
        railway_site.name = "ARU regional operating estate"
        railway_site.owner_entity_id = session.scalar(
            select(LegalEntity.id).where(LegalEntity.code == "ARU")
        )
        cash_account.name = "Stale cash label"
        consolidation_book.code = "LEGACY_CONSOLIDATION"
        session.commit()

        second = generate_standard(session)
        session.commit()
        assert first == second
        assert session.scalar(select(func.count(JournalEntry.id))) == first_entries
        assert rwh.name == "Dedicated Red Wash operator (formal legal identity open)"
        assert rwh.jurisdiction == "OPEN"
        assert railway_site.name == "BS&T railway operating estate (details open)"
        assert railway_site.owner_entity_id == session.scalar(
            select(LegalEntity.id).where(LegalEntity.code == "BST")
        )
        assert cash_account.name == "Cash and cash equivalents"
        assert consolidation_book.code == "CONSOLIDATION_USD"
        shi_id = session.scalar(select(LegalEntity.id).where(LegalEntity.code == "SHI"))
        shi_periods = session.scalar(
            select(func.count(FiscalPeriod.id))
            .join_from(FiscalPeriod, AccountingBook)
            .where(
                AccountingBook.entity_id == shi_id,
                AccountingBook.code == "PRIMARY_USD",
            )
        )
        assert shi_periods == 48
        consolidation_periods = session.scalar(
            select(func.count(FiscalPeriod.id))
            .join_from(FiscalPeriod, AccountingBook)
            .where(
                AccountingBook.entity_id == shi_id,
                AccountingBook.code == "CONSOLIDATION_USD",
            )
        )
        assert consolidation_periods == 1
        marker = session.scalar(
            select(ScenarioValue).where(ScenarioValue.period_code == "2023-2026")
        )
        assert marker is not None
        sources = set(session.scalars(select(JournalEntry.source_type)))
        assert {"synthetic_common_reference", "synthetic_scenario_forecast"}.issubset(sources)
        assert {
            "invoice",
            "revenue_recognition",
            "cash_receipt",
            "mine_production_batch",
            "uranium_shipment",
            "uranium_cash_receipt",
            "waybill",
        }.issubset(sources)
        assert session.scalar(select(func.count(CustomerContract.id))) == 4
        assert session.scalar(select(func.count(RevenueRecognition.id))) == 4
        assert session.scalar(select(func.count(CashReceipt.id))) == 4
        assert session.scalar(select(func.count(MineProductionBatch.id))) == 4
        assert session.scalar(select(func.count(UraniumShipment.id))) == 4
        assert session.scalar(select(func.count(Waybill.id))) == 4
        assert session.scalar(select(func.count(PayrollRun.id))) == 4
        assert session.scalar(select(func.count(VendorBill.id))) == 4
        assert session.scalar(select(func.count(VendorPayment.id))) == 4
        assert session.scalar(select(func.count(DepreciationRecord.id))) == 4
        assert session.scalar(select(func.count(DebtDraw.id))) == 4
        assert session.scalar(select(func.count(DebtRepayment.id))) == 4
        assert session.scalar(select(func.count(Engagement.id))) == 4
        assert session.scalar(select(func.count(WillowExperiment.id))) == 4
        assert session.scalar(select(func.count(AtlasEvaluation.id))) == 4
        assert session.scalar(select(func.count(RecoveryRun.id))) == 4
        assert max(len(value) for value in session.scalars(select(InventoryLot.lot_number))) <= 40
        assert (
            max(len(value) for value in session.scalars(select(MineProductionBatch.batch_number)))
            <= 40
        )
        assert (
            max(len(value) for value in session.scalars(select(UraniumShipment.shipment_number)))
            <= 40
        )
        assert max(len(value) for value in session.scalars(select(Waybill.waybill_number))) <= 40
        revenue = session.scalar(
            select(func.sum(ScenarioValue.amount)).where(
                ScenarioValue.generation_run_id.in_((run.actual_generation_run_id, run.id)),
                ScenarioValue.metric_code == "revenue",
            )
        )
        assert revenue == Decimal("446400000.0000")
        debit, credit = session.execute(
            select(func.sum(JournalLine.debit), func.sum(JournalLine.credit))
        ).one()
        assert debit == credit
