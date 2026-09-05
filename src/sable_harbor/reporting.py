import os
import tempfile
from pathlib import Path

import xlsxwriter  # type: ignore[import-untyped]
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import (
    Account,
    EntryState,
    FiscalPeriod,
    JournalEntry,
    JournalLine,
    ScenarioValue,
)
from sable_harbor.accounting.validation import validate_financial_integrity
from sable_harbor.exports.metadata import generation_manifest_metadata
from sable_harbor.exports.safety import scan_generated_artifacts
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import run_context

EXCEL_MAX_ROWS = 1_048_576
PREVIEW_DATA_START_ROW = 1


def financial_rows(session: Session, generation_run_id: str) -> list[tuple[str, str, str, float]]:
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
    context = run_context(session, generation_run_id)
    run = session.get(GenerationRun, context.generation_run_id)
    if run is None or run.completed_at is None:
        raise ValueError(f"Unknown or incomplete generation run {generation_run_id!r}")
    validate_financial_integrity(session, generation_run_id)
    period_start, period_end = session.execute(
        select(func.min(FiscalPeriod.code), func.max(FiscalPeriod.code))
        .join(JournalEntry, JournalEntry.period_id == FiscalPeriod.id)
        .where(
            JournalEntry.state == EntryState.POSTED,
            JournalEntry.generation_run_id.in_(context.included_run_ids),
        )
    ).one()
    if period_start is None or period_end is None:
        raise ValueError("Reporting preview requires a nonempty reporting period")
    metadata = generation_manifest_metadata(
        run,
        scenario_code=context.scenario_code,
        built_at=run.completed_at,
        effective_from=str(period_start),
        effective_through=str(period_end),
        effective_period_basis="posted_fiscal_period_codes",
    )
    data = financial_rows(session, generation_run_id)
    assumption_rows = session.scalars(
        select(ScenarioValue)
        .where(ScenarioValue.generation_run_id == context.generation_run_id)
        .order_by(ScenarioValue.metric_code)
    ).all()
    largest_row_count = max(len(data), len(assumption_rows))
    if largest_row_count > EXCEL_MAX_ROWS - PREVIEW_DATA_START_ROW:
        raise ValueError(
            "Reporting preview exceeds the Excel row limit: "
            f"{largest_row_count} data rows (maximum "
            f"{EXCEL_MAX_ROWS - PREVIEW_DATA_START_ROW})"
        )

    requested_destination = destination.expanduser()
    if requested_destination.is_symlink():
        raise ValueError(f"Report destination cannot be a symbolic link: {destination}")
    destination = requested_destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}.", suffix=destination.suffix or ".xlsx", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    workbook = xlsxwriter.Workbook(
        temporary, {"strings_to_formulas": False, "strings_to_urls": False}
    )
    workbook.set_properties(
        {
            "title": "Sable Harbor internal synthetic model reporting preview",
            "company": "Sable Harbor",
            "created": run.completed_at,
        }
    )
    title = workbook.add_format({"bold": True, "font_size": 15, "font_color": "#17324D"})
    header = workbook.add_format({"bold": True, "bg_color": "#17324D", "font_color": "white"})
    money = workbook.add_format({"num_format": "$#,##0;[Red]($#,##0)"})
    note = workbook.add_format({"font_color": "#666666", "italic": True})

    cover = workbook.add_worksheet("Read Me")
    cover.write("A1", "Sable Harbor synthetic model reporting preview", title)
    cover.write("A3", "Status")
    cover.write("B3", "INTERNAL_SYNTHETIC_PREVIEW — NOT A RELEASE ARTIFACT")
    cover.write(
        "A5",
        "Use the governed workbook-suite or release-package command for publishable artifacts.",
        note,
    )
    cover.write("A7", "Epistemic mode")
    cover.write("B7", metadata["epistemic_mode"])
    cover.write("A8", "Period covered")
    cover.write("B8", f"{period_start} through {period_end}")
    cover.write("A9", "Canon effective through")
    cover.write("B9", metadata["canon_effective_through"])
    cover.write("A10", "Generation run")
    cover.write("B10", context.generation_run_id)
    cover.set_column("A:A", 34)
    cover.set_column("B:B", 65)

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
    income.write_row(0, 0, [f"{period_start} through {period_end} consolidated", "USD"], header)
    revenue = -sum(amount for _, _, cls, amount in data if cls == "REVENUE")
    expense = sum(amount for _, _, cls, amount in data if cls in {"EXPENSE", "OTHER_EXPENSE"})
    income.write("A2", "Revenue")
    income.write_number("B2", revenue, money)
    income.write("A3", "Operating costs and expenses")
    income.write_number("B3", expense, money)
    income.write("A4", "Operating income (loss)")
    income.write_formula("B4", "=B2-B3", money)
    income.set_column("A:A", 36)
    income.set_column("B:B", 20)

    balance = workbook.add_worksheet("Balance Sheet")
    balance.write_row(0, 0, [f"Through {period_end}", "USD"], header)
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
    balance.write("A5", "Cumulative scenario income (loss)")
    balance.write_number("B5", net_income, money)
    balance.write("A6", "Liabilities and equity")
    balance.write_formula("B6", "=SUM(B3:B5)", money)
    balance.write("A8", "Reconciliation difference")
    balance.write_formula("B8", "=B2-B6", money)
    balance.set_column("A:A", 38)
    balance.set_column("B:B", 20)

    cashflow = workbook.add_worksheet("Cash Flow Bridge")
    cashflow.write_row(0, 0, [f"{period_start} through {period_end} cash bridge", "USD"], header)
    cash = next((amount for code, _, _, amount in data if code == "1000"), 0.0)
    cashflow.write("A2", "Ending cash per ledger")
    cashflow.write_number("B2", cash, money)
    cashflow.write("A4", "Model note", note)
    cashflow.write(
        "B4",
        "Opening/acquisition cash and cumulative cash-realized synthetic activity; "
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
    for idx, item in enumerate(assumption_rows, 1):
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
    assumptions.autofilter(0, 0, len(assumption_rows), 7)
    assumptions.set_column("A:D", 18)
    assumptions.set_column("E:E", 18)
    assumptions.set_column("F:G", 18)
    assumptions.set_column("H:H", 60)

    try:
        workbook.close()
        failures = scan_generated_artifacts(temporary)
        if failures:
            raise ValueError("Reporting preview safety scan failed:\n" + "\n".join(failures))
        os.replace(temporary, destination)
        return destination
    finally:
        if temporary.exists():
            temporary.unlink()
