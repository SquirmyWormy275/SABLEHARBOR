from pathlib import Path

import xlsxwriter  # type: ignore[import-untyped]
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import (
    Account,
    EntryState,
    JournalEntry,
    JournalLine,
    ScenarioValue,
)
from sable_harbor.provenance.service import run_context


def financial_rows(
    session: Session, generation_run_id: str
) -> list[tuple[str, str, str, float]]:
    context = run_context(session, generation_run_id)
    stmt = (
        select(
            Account.code,
            Account.name,
            Account.account_class,
            func.sum(JournalLine.debit - JournalLine.credit),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.state == EntryState.POSTED,
            JournalEntry.generation_run_id.in_(context.included_run_ids),
        )
        .group_by(Account.code, Account.name, Account.account_class)
        .order_by(Account.code)
    )
    return [
        (code, name, cls, float(amount or 0)) for code, name, cls, amount in session.execute(stmt)
    ]


def build_workbook(session: Session, destination: Path, generation_run_id: str) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    workbook = xlsxwriter.Workbook(destination)
    title = workbook.add_format({"bold": True, "font_size": 15, "font_color": "#17324D"})
    header = workbook.add_format({"bold": True, "bg_color": "#17324D", "font_color": "white"})
    money = workbook.add_format({"num_format": "$#,##0;[Red]($#,##0)"})
    note = workbook.add_format({"font_color": "#666666", "italic": True})

    cover = workbook.add_worksheet("Read Me")
    cover.write("A1", "Sable Harbor FY2026 model reporting pack", title)
    cover.write("A3", "Status")
    cover.write("B3", "MODEL_PROPOSED / deterministic synthetic instance")
    cover.write(
        "A5",
        "Public-safe output: no hidden benchmark truth, credentials, or personal information.",
        note,
    )
    cover.set_column("A:A", 34)
    cover.set_column("B:B", 65)

    context = run_context(session, generation_run_id)
    data = financial_rows(session, generation_run_id)
    tb = workbook.add_worksheet("Trial Balance")
    tb.write_row(0, 0, ["Account", "Name", "Class", "Debit less credit"], header)
    for row_index, row in enumerate(data, 1):
        tb.write_row(row_index, 0, row[:3])
        tb.write_number(row_index, 3, row[3], money)
    tb.autofilter(0, 0, len(data), 3)
    tb.freeze_panes(1, 0)
    tb.set_column("A:A", 12)
    tb.set_column("B:B", 44)
    tb.set_column("C:C", 15)
    tb.set_column("D:D", 20)

    income = workbook.add_worksheet("Income Statement")
    income.write_row(0, 0, ["FY2026 consolidated", "USD"], header)
    revenue = -sum(amount for _, _, cls, amount in data if cls == "REVENUE")
    expense = sum(amount for _, _, cls, amount in data if cls == "EXPENSE")
    income.write("A2", "Revenue")
    income.write_number("B2", revenue, money)
    income.write("A3", "Operating costs and expenses")
    income.write_number("B3", expense, money)
    income.write("A4", "Operating income (loss)")
    income.write_formula("B4", "=B2-B3", money)
    income.set_column("A:A", 36)
    income.set_column("B:B", 20)

    balance = workbook.add_worksheet("Balance Sheet")
    balance.write_row(0, 0, ["December 31, 2026", "USD"], header)
    assets = sum(amount for _, _, cls, amount in data if cls == "ASSET")
    liabilities = -sum(amount for _, _, cls, amount in data if cls == "LIABILITY")
    equity_before_income = -sum(amount for _, _, cls, amount in data if cls == "EQUITY")
    net_income = revenue - expense
    balance.write("A2", "Assets")
    balance.write_number("B2", assets, money)
    balance.write("A3", "Liabilities")
    balance.write_number("B3", liabilities, money)
    balance.write("A4", "Equity before current-year income")
    balance.write_number("B4", equity_before_income, money)
    balance.write("A5", "Current-year income (loss)")
    balance.write_number("B5", net_income, money)
    balance.write("A6", "Liabilities and equity")
    balance.write_formula("B6", "=SUM(B3:B5)", money)
    balance.write("A8", "Reconciliation difference")
    balance.write_formula("B8", "=B2-B6", money)
    balance.set_column("A:A", 38)
    balance.set_column("B:B", 20)

    cashflow = workbook.add_worksheet("Cash Flow Bridge")
    cashflow.write_row(0, 0, ["FY2026 simplified indirect bridge", "USD"], header)
    cash = next((amount for code, _, _, amount in data if code == "1000"), 0.0)
    cashflow.write("A2", "Ending cash per ledger")
    cashflow.write_number("B2", cash, money)
    cashflow.write("A4", "Model note", note)
    cashflow.write(
        "B4",
        "Opening/acquisition cash and FY2026 cash-realized summary activity; "
        "detailed monthly cash-flow subledger is a subsequent increment.",
    )
    cashflow.set_column("A:A", 34)
    cashflow.set_column("B:B", 90)

    assumptions = workbook.add_worksheet("Assumptions")
    assumptions.write_row(
        0,
        0,
        ["Scenario", "Metric", "Entity", "Period", "Value", "Unit", "Fact state", "Provenance"],
        header,
    )
    rows = session.scalars(
        select(ScenarioValue)
        .where(ScenarioValue.generation_run_id == context.generation_run_id)
        .order_by(ScenarioValue.metric_code)
    ).all()
    for idx, item in enumerate(rows, 1):
        assumptions.write_row(
            idx,
            0,
            [
                item.scenario_code,
                item.metric_code,
                item.entity_code,
                item.period_code,
                float(item.amount),
                item.unit,
                item.fact_state.value,
                item.provenance,
            ],
        )
    assumptions.autofilter(0, 0, len(rows), 7)
    assumptions.set_column("A:D", 18)
    assumptions.set_column("E:E", 18)
    assumptions.set_column("F:G", 18)
    assumptions.set_column("H:H", 60)

    workbook.close()
    return destination
