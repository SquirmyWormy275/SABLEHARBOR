from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import post_entry
from sable_harbor.accounting.models import (
    Account,
    AccountingBook,
    Base,
    EntryState,
    FactState,
    FiscalPeriod,
    JournalEntry,
    JournalLine,
    LegalEntity,
)
from sable_harbor.accounting.seed import seed_smoke
from sable_harbor.accounting.validation import FinancialIntegrityError, validate_financial_integrity
from sable_harbor.commercial.contract_to_cash import (
    create_foundry_contract_flow,
    recognize_month,
)
from sable_harbor.commercial.models import Invoice, PerformanceObligation
from sable_harbor.core.ids import stable_id
from sable_harbor.operations.flows import depreciate_asset, procure_and_pay_asset
from sable_harbor.operations.models import GoodsReceipt, PurchaseOrder, Vendor, VendorBill
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import complete_generation_run, record_generation_run
from sable_harbor.reporting_queries import run_named_query


def _account_id(session: Session, code: str) -> str:
    account_id = session.query(Account.id).filter(Account.code == code).scalar()
    assert account_id is not None
    return account_id


def _amount(row: dict[str, object], column: str) -> Decimal:
    return Decimal(str(row[column]))


def _post(
    session: Session,
    *,
    key: str,
    book_id: str,
    period_id: str,
    entry_date: date,
    postings: list[tuple[str, Decimal, Decimal, str | None]],
) -> JournalEntry:
    entry = JournalEntry(
        id=stable_id("journal", key),
        generation_run_id=str(session.info["generation_run_id"]),
        book_id=book_id,
        period_id=period_id,
        entry_date=entry_date,
        description=f"Financial query integrity fixture {key}",
        source_type="query_integrity_fixture",
        source_id=key,
        state=EntryState.DRAFT,
        lines=[
            JournalLine(
                id=stable_id("journal_line", f"{key}:{index}"),
                account_id=_account_id(session, account_code),
                debit=debit,
                credit=credit,
                transaction_currency="USD",
                functional_amount=debit - credit,
                reporting_amount=debit - credit,
                fact_state=FactState.DERIVED,
                counterparty_entity_id=counterparty_id,
            )
            for index, (account_code, debit, credit, counterparty_id) in enumerate(
                postings, start=1
            )
        ],
    )
    session.add(entry)
    post_entry(session, entry)
    return entry


def _complete(session: Session) -> GenerationRun:
    run = session.get(GenerationRun, str(session.info["generation_run_id"]))
    assert run is not None
    complete_generation_run(session, run)
    session.commit()
    return run


def test_fixed_asset_rollforward_does_not_repeat_cost_for_multiple_depreciation_rows() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        entity_id = session.query(LegalEntity.id).scalar()
        period_id = session.query(FiscalPeriod.id).scalar()
        assert entity_id is not None
        assert period_id is not None
        _, _, asset = procure_and_pay_asset(
            session,
            entity_id=entity_id,
            book_id=book_id,
            period_id=period_id,
            key="ROLLFORWARD-ASSET",
            event_date=date(2026, 8, 1),
            amount=Decimal("120000"),
        )
        first = depreciate_asset(
            session,
            asset=asset,
            book_id=book_id,
            period_id=period_id,
            depreciation_date=date(2026, 8, 15),
        )
        second = depreciate_asset(
            session,
            asset=asset,
            book_id=book_id,
            period_id=period_id,
            depreciation_date=date(2026, 8, 31),
        )
        run = _complete(session)

        rows = run_named_query(session, "fixed_asset_rollforward", run.id)
        assert len(rows) == 1
        assert _amount(rows[0], "gross_cost") == Decimal("120000")
        assert _amount(rows[0], "accumulated_depreciation") == first.amount + second.amount
        assert _amount(rows[0], "net_book_value") == Decimal("116000")


def test_ar_ap_exposure_splits_due_status_and_independently_reconciles_gl() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        entity_id = session.query(LegalEntity.id).scalar()
        august = session.query(FiscalPeriod).one()
        assert entity_id is not None
        july = FiscalPeriod(
            id=stable_id("period", f"{book_id}:2026-07"),
            book_id=book_id,
            code="2026-07",
            starts_on=date(2026, 7, 1),
            ends_on=date(2026, 7, 31),
        )
        session.add(july)
        session.flush()

        create_foundry_contract_flow(
            session,
            book_id=book_id,
            entity_id=entity_id,
            period_id=july.id,
            natural_key="PAST-DUE-AR",
            invoice_date=date(2026, 7, 1),
            annual_value=Decimal("100"),
        )
        create_foundry_contract_flow(
            session,
            book_id=book_id,
            entity_id=entity_id,
            period_id=august.id,
            natural_key="NOT-DUE-AR",
            invoice_date=date(2026, 8, 15),
            annual_value=Decimal("200"),
        )

        vendor = Vendor(
            id=stable_id("vendor", "UNPAID-AP"),
            code="VEN-UNPAID-AP",
            name="Unpaid AP fixture vendor",
            category="TEST",
        )
        session.add(vendor)
        session.flush()
        purchase_order = PurchaseOrder(
            id=stable_id("purchase_order", "UNPAID-AP"),
            entity_id=entity_id,
            vendor_id=vendor.id,
            po_number="PO-UNPAID-AP",
            order_date=date(2026, 8, 10),
            amount=Decimal("80"),
            status="RECEIVED",
        )
        session.add(purchase_order)
        session.flush()
        receipt = GoodsReceipt(
            id=stable_id("goods_receipt", "UNPAID-AP"),
            purchase_order_id=purchase_order.id,
            receipt_date=date(2026, 8, 10),
            amount=Decimal("80"),
        )
        session.add(receipt)
        session.flush()
        bill_entry = _post(
            session,
            key="UNPAID-AP-DOCUMENT",
            book_id=book_id,
            period_id=august.id,
            entry_date=date(2026, 8, 10),
            postings=[
                ("1500", Decimal("80"), Decimal("0"), None),
                ("2100", Decimal("0"), Decimal("80"), None),
            ],
        )
        session.add(
            VendorBill(
                id=stable_id("vendor_bill", "UNPAID-AP"),
                purchase_order_id=purchase_order.id,
                receipt_id=receipt.id,
                bill_number="BILL-UNPAID-AP",
                bill_date=date(2026, 8, 10),
                amount=Decimal("80"),
                match_status="MATCHED",
                journal_entry_id=bill_entry.id,
            )
        )

        _post(
            session,
            key="NON-DOCUMENT-AR",
            book_id=book_id,
            period_id=august.id,
            entry_date=date(2026, 8, 31),
            postings=[
                ("1100", Decimal("25"), Decimal("0"), None),
                ("2200", Decimal("0"), Decimal("25"), None),
            ],
        )
        _post(
            session,
            key="NON-DOCUMENT-AP",
            book_id=book_id,
            period_id=august.id,
            entry_date=date(2026, 8, 31),
            postings=[
                ("1500", Decimal("30"), Decimal("0"), None),
                ("2100", Decimal("0"), Decimal("30"), None),
            ],
        )
        run = _complete(session)

        rows = {
            str(row["ledger"]): row
            for row in run_named_query(session, "ar_ap_exposure_reconciliation", run.id)
        }
        assert set(rows) == {"AR", "AP"}
        ar = rows["AR"]
        assert str(ar["as_of_date"]) == "2026-08-31"
        assert _amount(ar, "document_open_amount") == Decimal("300")
        assert _amount(ar, "past_due_amount") == Decimal("100")
        assert _amount(ar, "not_due_amount") == Decimal("200")
        assert _amount(ar, "non_document_source_event_amount") == Decimal("25")
        assert _amount(ar, "gl_open_amount") == Decimal("325")
        assert _amount(ar, "reconciliation_difference") == Decimal("0")

        ap = rows["AP"]
        assert str(ap["as_of_date"]) == "2026-08-31"
        assert _amount(ap, "document_open_amount") == Decimal("80")
        assert _amount(ap, "due_date_unavailable_amount") == Decimal("80")
        assert _amount(ap, "not_due_amount") == Decimal("0")
        assert _amount(ap, "past_due_amount") == Decimal("0")
        assert _amount(ap, "non_document_source_event_amount") == Decimal("30")
        assert _amount(ap, "gl_open_amount") == Decimal("110")
        assert _amount(ap, "reconciliation_difference") == Decimal("0")


def test_ar_ap_reconciliation_detects_document_to_journal_mismatch() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        entity_id = session.query(LegalEntity.id).scalar()
        period = session.query(FiscalPeriod).one()
        assert entity_id is not None
        _, invoice = create_foundry_contract_flow(
            session,
            book_id=book_id,
            entity_id=entity_id,
            period_id=period.id,
            natural_key="MISMATCHED-AR",
            invoice_date=date(2026, 8, 1),
            annual_value=Decimal("100"),
        )
        invoice.total = Decimal("101")
        run = _complete(session)

        ar = next(
            row
            for row in run_named_query(session, "ar_ap_exposure_reconciliation", run.id)
            if row["ledger"] == "AR"
        )
        assert _amount(ar, "document_open_amount") == Decimal("101")
        assert _amount(ar, "gl_open_amount") == Decimal("100")
        assert _amount(ar, "non_document_source_event_amount") == Decimal("0")
        assert _amount(ar, "reconciliation_difference") == Decimal("-1")
        with pytest.raises(FinancialIntegrityError, match="AR_AP_RECONCILE_TO_GL"):
            validate_financial_integrity(session, run.id)


def _intercompany_fixture(session: Session, *, reciprocal: bool) -> tuple[GenerationRun, str, str]:
    seller_book_id = seed_smoke(session, complete=False)
    seller = session.query(LegalEntity).one()
    seller_period = session.query(FiscalPeriod).one()
    buyer = LegalEntity(
        id=stable_id("entity", "RECIPROCAL-BUYER"),
        code="RECIPROCAL-BUYER",
        name="Reciprocal buyer fixture",
        fact_state=FactState.MODEL_PROPOSED,
        effective_from=date(2026, 1, 1),
    )
    buyer_book = AccountingBook(
        id=stable_id("book", "RECIPROCAL-BUYER:PRIMARY_USD"),
        entity_id=buyer.id,
        code="PRIMARY_USD",
    )
    buyer_period = FiscalPeriod(
        id=stable_id("period", f"{buyer_book.id}:2026-08"),
        book_id=buyer_book.id,
        code="2026-08",
        starts_on=date(2026, 8, 1),
        ends_on=date(2026, 8, 31),
    )
    session.add_all(
        [
            buyer,
            buyer_book,
            buyer_period,
            Account(
                id=stable_id("account", "6400"),
                code="6400",
                name="Intercompany freight and services",
                account_class="EXPENSE",
                normal_balance="DEBIT",
            ),
        ]
    )
    session.flush()

    _post(
        session,
        key="INTERCOMPANY-SELLER",
        book_id=seller_book_id,
        period_id=seller_period.id,
        entry_date=date(2026, 8, 31),
        postings=[
            ("1100", Decimal("100"), Decimal("0"), buyer.id),
            ("4090", Decimal("0"), Decimal("100"), buyer.id),
        ],
    )
    if reciprocal:
        _post(
            session,
            key="INTERCOMPANY-BUYER",
            book_id=buyer_book.id,
            period_id=buyer_period.id,
            entry_date=date(2026, 8, 31),
            postings=[
                ("6400", Decimal("100"), Decimal("0"), seller.id),
                ("2000", Decimal("0"), Decimal("100"), seller.id),
            ],
        )
    return _complete(session), seller.code, buyer.code


def test_intercompany_query_detects_one_sided_reciprocal_mismatch() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run, seller_code, buyer_code = _intercompany_fixture(session, reciprocal=False)

        rows = run_named_query(session, "intercompany_mismatch_elimination", run.id)
        assert len(rows) == 1
        assert {rows[0]["entity_a"], rows[0]["entity_b"]} == {seller_code, buyer_code}
        assert _amount(rows[0], "balance_sheet_mismatch") == Decimal("100")
        assert _amount(rows[0], "income_statement_mismatch") == Decimal("100")
        assert _amount(rows[0], "total_mismatch") == Decimal("200")


def test_intercompany_query_clears_for_truly_reciprocal_pair() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run, seller_code, buyer_code = _intercompany_fixture(session, reciprocal=True)

        rows = run_named_query(session, "intercompany_mismatch_elimination", run.id)
        assert len(rows) == 1
        assert {rows[0]["entity_a"], rows[0]["entity_b"]} == {seller_code, buyer_code}
        assert _amount(rows[0], "receivable") == _amount(rows[0], "payable")
        assert _amount(rows[0], "intercompany_revenue") == _amount(rows[0], "intercompany_expense")
        assert _amount(rows[0], "balance_sheet_mismatch") == Decimal("0")
        assert _amount(rows[0], "income_statement_mismatch") == Decimal("0")
        assert _amount(rows[0], "total_mismatch") == Decimal("0")


def test_vendor_spend_query_excludes_vendors_owned_by_other_runs() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_smoke(session, complete=False)
        session.add(
            Vendor(
                id=stable_id("vendor", "SELECTED-RUN"),
                code="VEN-SELECTED-RUN",
                name="Selected-run fixture vendor",
                category="TEST",
            )
        )
        selected_run = _complete(session)

        other_run = record_generation_run(
            session,
            profile="smoke",
            scenario_code="base",
            seed=20260901,
            git_commit="0" * 40,
        )
        session.add(
            Vendor(
                id=stable_id("vendor", "OTHER-RUN"),
                code="VEN-OTHER-RUN",
                name="Other-run fixture vendor",
                category="TEST",
            )
        )
        complete_generation_run(session, other_run)
        session.commit()

        rows = run_named_query(session, "vendor_spend_concentration", selected_run.id)
        assert [row["code"] for row in rows] == ["VEN-SELECTED-RUN"]


def test_customer_profitability_preaggregates_independent_child_populations() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        book_id = seed_smoke(session, complete=False)
        entity_id = session.query(LegalEntity.id).scalar()
        period_id = session.query(FiscalPeriod.id).scalar()
        assert entity_id is not None
        assert period_id is not None

        contract, _ = create_foundry_contract_flow(
            session,
            book_id=book_id,
            entity_id=entity_id,
            period_id=period_id,
            natural_key="PROFITABILITY",
            invoice_date=date(2026, 8, 1),
            annual_value=Decimal("100"),
        )
        first_obligation = (
            session.query(PerformanceObligation)
            .filter(PerformanceObligation.contract_id == contract.id)
            .one()
        )
        second_obligation = PerformanceObligation(
            id=stable_id("obligation", "PROFITABILITY:SERVICES"),
            contract_id=contract.id,
            name="Synthetic implementation services",
            revenue_method="MILESTONE",
            allocated_price=Decimal("40"),
        )
        session.add(second_obligation)
        session.flush()
        second_invoice_journal = _post(
            session,
            key="PROFITABILITY-SECOND-INVOICE",
            book_id=book_id,
            period_id=period_id,
            entry_date=date(2026, 8, 2),
            postings=[
                ("1100", Decimal("40"), Decimal("0"), None),
                ("2200", Decimal("0"), Decimal("40"), None),
            ],
        )
        session.add(
            Invoice(
                id=stable_id("invoice", "PROFITABILITY:SECOND"),
                contract_id=contract.id,
                invoice_number="INV-PROFITABILITY-SECOND",
                invoice_date=date(2026, 8, 2),
                due_date=date(2026, 9, 1),
                currency="USD",
                total=Decimal("40"),
                journal_entry_id=second_invoice_journal.id,
            )
        )
        recognize_month(
            session,
            obligation=first_obligation,
            book_id=book_id,
            period_id=period_id,
            recognition_date=date(2026, 8, 20),
            amount=Decimal("30"),
        )
        recognize_month(
            session,
            obligation=second_obligation,
            book_id=book_id,
            period_id=period_id,
            recognition_date=date(2026, 8, 21),
            amount=Decimal("20"),
        )
        run = _complete(session)

        rows = run_named_query(session, "customer_profitability", run.id)
        assert len(rows) == 1
        assert _amount(rows[0], "billings") == Decimal("140")
        assert _amount(rows[0], "recognized_revenue") == Decimal("50")


def test_entity_trial_balance_excludes_consolidation_book_entries() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_smoke(session, complete=False)
        entity_id = session.query(LegalEntity.id).scalar()
        assert entity_id is not None
        consolidation_book = AccountingBook(
            id=stable_id("book", "SABLE_HARBOR_MODEL_PARENT:CONSOLIDATION_USD"),
            entity_id=entity_id,
            code="CONSOLIDATION_USD",
        )
        consolidation_period = FiscalPeriod(
            id=stable_id("period", f"{consolidation_book.id}:2026-08"),
            book_id=consolidation_book.id,
            code="2026-08",
            starts_on=date(2026, 8, 1),
            ends_on=date(2026, 8, 31),
        )
        session.add_all([consolidation_book, consolidation_period])
        session.flush()
        _post(
            session,
            key="CONSOLIDATION-ONLY",
            book_id=consolidation_book.id,
            period_id=consolidation_period.id,
            entry_date=date(2026, 8, 31),
            postings=[
                ("1000", Decimal("77"), Decimal("0"), None),
                ("3000", Decimal("0"), Decimal("77"), None),
            ],
        )
        run = _complete(session)

        rows = run_named_query(session, "entity_trial_balance", run.id)
        cash = next(row for row in rows if row["account"] == "1000")
        equity = next(row for row in rows if row["account"] == "3000")
        assert _amount(cash, "debit") == Decimal("1000000")
        assert _amount(equity, "credit") == Decimal("1000000")
