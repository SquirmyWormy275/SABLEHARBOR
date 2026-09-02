from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import xlsxwriter  # type: ignore[import-untyped]
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import (
    Account,
    JournalEntry,
    JournalLine,
    ScenarioValue,
)
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import run_context
from sable_harbor.reporting_queries import run_named_query
from sable_harbor.reports.statements import monthly_statements

WORKBOOKS: dict[str, list[str]] = {
    "SABLE_HARBOR_CONSOLIDATED_OPERATING_MODEL_v0.1.xlsx": [
        "Cover",
        "Read Me",
        "Control Panel",
        "Scenario Selector",
        "Key Assumptions",
        "Assumption Register",
        "Executive Dashboard",
        "Historical Annual Summary",
        "Monthly Consolidated P&L",
        "Monthly Balance Sheet",
        "Monthly Cash Flow",
        "Changes in Equity",
        "Segment P&L",
        "Revenue Build",
        "Gross Profit Cost Build",
        "Operating Expense Build",
        "Headcount and Compensation",
        "Working Capital",
        "Capex Deprec Depletion",
        "Debt and Liquidity",
        "Intercompany Eliminations",
        "Tax Summary",
        "Checks",
        "Sources and Limitations",
    ],
    "SABLE_HARBOR_SOFTWARE_AND_SERVICES_v0.1.xlsx": [
        "Cover",
        "Control Panel",
        "Customer Roster",
        "Sites and Deployments",
        "Contract Roster",
        "ARR-MRR Bridge",
        "Bookings Billings Revenue",
        "Deferred Revenue",
        "Retention and Cohorts",
        "Customer Concentration",
        "Customer Unit Economics",
        "Foundry Revenue Build",
        "Foundry Cost Build",
        "Implementation Backlog",
        "Services Utilization",
        "Engagement Margin",
        "Atlas Commercial Build",
        "Atlas R&D and Compute",
        "Willow Portfolio and Burn",
        "Historical Emberline Bridge",
        "Emerging Advisory",
        "Checks",
    ],
    "SABLE_HARBOR_INDUSTRIAL_OPERATIONS_v0.1.xlsx": [
        "Cover",
        "Control Panel",
        "Red Wash Assumptions",
        "Red Wash Operating Schedule",
        "Red Wash Production Inv",
        "Red Wash Revenue",
        "Red Wash Operating Cost",
        "Red Wash Capex and ARO",
        "Red Wash DCF-NAV",
        "Red Wash Sensitivities",
        "ARU-BS&T Assumptions",
        "ARU-BS&T Volume and Rates",
        "ARU-BS&T Operating Cost",
        "ARU-BS&T Fleet Assets",
        "ARU-BS&T EBITDA Cash Flow",
        "Cradle Assumptions",
        "Cradle Pilot Build",
        "Cradle Contract Structures",
        "Cradle Project DCF",
        "Industrial Intercompany",
        "Checks",
    ],
    "SABLE_HARBOR_GL_CLOSE_AND_SUBLEDGERS_v0.1.xlsx": [
        "Cover",
        "Control Panel",
        "Chart of Accounts",
        "Dimension Dictionary",
        "Trial Balance",
        "Journal Summary",
        "Journal Detail Extract",
        "Close Calendar",
        "Close Tasks",
        "Account Reconciliations",
        "AR Aging",
        "AP Aging",
        "Deferred Revenue Rollforward",
        "Payroll Summary",
        "Fixed Assets",
        "Inventory Rollforward",
        "Debt Schedule",
        "Intercompany Matches",
        "Consolidation Entries",
        "Checks",
    ],
    "SABLE_HARBOR_CAPITAL_MA_AND_VALUATION_v0.1.xlsx": [
        "Cover",
        "Control Panel",
        "Financing History",
        "Capitalization Table",
        "Equity Awards",
        "Debt and Warrants",
        "Red Wash Acquisition",
        "ARU Acquisition",
        "Purchase Price Allocation",
        "Integration Costs",
        "Consolidated SOTP",
        "Software DCF-Multiples",
        "Red Wash Mine NAV",
        "ARU-BS&T Valuation",
        "Cradle Project Option Value",
        "Atlas-Willow Optionality",
        "Advisory Valuation",
        "EV to Equity Value",
        "Net Debt Debt-like Items",
        "Working Capital Peg",
        "Transaction Fees",
        "Buyer Case",
        "Seller Case",
        "Sensitivities",
        "Checks",
    ],
    "SABLE_HARBOR_DATA_DICTIONARY_AND_RELEASE_CONTROL_v0.1.xlsx": [
        "Cover",
        "Control Panel",
        "Release Summary",
        "Package Manifest",
        "Table Inventory",
        "Field Dictionary",
        "Relationships",
        "Canon State Definitions",
        "Assumption Register",
        "Scenario Definitions",
        "Generation Runs",
        "Coverage Metrics",
        "Data Quality Results",
        "Lineage Examples",
        "Named Queries",
        "License Usage Terms",
        "Known Limitations",
        "Checksums",
        "Checks",
    ],
}


@dataclass(frozen=True)
class SheetSpec:
    purpose: str
    query: str
    units: str = "as labeled"
    sort_order: tuple[str, ...] = ()
    required_columns: tuple[str, ...] = ()
    empty_state: str = "No records for this optional domain"
    tolerance: float = 0.0


# Exact semantic routing. Titles are registry keys only; no title parsing influences data.
_QUERY_GROUPS: dict[str, tuple[str, ...]] = {
    "entity_trial_balance": (
        "Chart of Accounts", "Trial Balance",
    ),
    "journal_to_source_trace": (
        "Journal Summary", "Journal Detail Extract", "Lineage Examples",
        "Sources and Limitations",
    ),
    "consolidated_monthly_pnl": (
        "Executive Dashboard", "Historical Annual Summary", "Monthly Consolidated P&L",
        "Segment P&L", "Revenue Build",
        "Gross Profit Cost Build", "Operating Expense Build", "Tax Summary",
        "Bookings Billings Revenue", "Foundry Revenue Build", "Foundry Cost Build",
        "Atlas Commercial Build", "Emerging Advisory", "Red Wash Revenue",
        "Red Wash Operating Cost", "ARU-BS&T EBITDA Cash Flow",
    ),
    "assumption_impact": (
        "Control Panel", "Scenario Selector", "Key Assumptions", "Assumption Register",
        "Red Wash Assumptions", "Red Wash Sensitivities", "ARU-BS&T Assumptions",
        "Cradle Assumptions", "Cradle Contract Structures", "Scenario Definitions",
        "Buyer Case", "Seller Case", "Sensitivities", "Willow Portfolio and Burn",
        "Atlas R&D and Compute", "Integration Costs", "Purchase Price Allocation",
        "Working Capital Peg", "Transaction Fees", "Equity Awards",
    ),
    "employee_loaded_cost": (
        "Headcount and Compensation", "Payroll Summary", "Services Utilization",
    ),
    "customer_arr_bridge": (
        "Customer Roster", "Sites and Deployments", "Contract Roster", "ARR-MRR Bridge",
        "Deferred Revenue", "Retention and Cohorts", "Customer Concentration",
        "Customer Unit Economics", "Implementation Backlog", "Historical Emberline Bridge",
    ),
    "engagement_margin_wip": ("Engagement Margin",),
    "red_wash_unit_cost_bridge": (
        "Red Wash Operating Schedule", "Red Wash Production Inv", "Red Wash Capex and ARO",
        "Red Wash DCF-NAV", "Red Wash Acquisition", "Red Wash Mine NAV",
    ),
    "aru_route_customer_margin": (
        "ARU-BS&T Volume and Rates", "ARU-BS&T Operating Cost", "ARU-BS&T Fleet Assets",
        "ARU Acquisition", "ARU-BS&T Valuation", "Industrial Intercompany",
    ),
    "cradle_project_economics": (
        "Cradle Pilot Build", "Cradle Project DCF", "Cradle Project Option Value",
    ),
    "debt_covenant_calculation": (
        "Debt and Warrants", "Financing History",
        "Net Debt Debt-like Items",
    ),
    "fixed_asset_rollforward": (),
    "deferred_revenue_rollforward": ("Deferred Revenue Rollforward",),
    "ar_ap_aging": ("AR Aging", "AP Aging"),
    "intercompany_mismatch_elimination": (
        "Intercompany Eliminations", "Intercompany Matches", "Consolidation Entries",
    ),
    "release_coverage_lineage": (
        "Cover", "Read Me", "Checks", "Close Calendar", "Close Tasks",
        "Account Reconciliations", "Release Summary", "Package Manifest", "Table Inventory",
        "Field Dictionary", "Relationships", "Canon State Definitions", "Generation Runs",
        "Coverage Metrics", "Data Quality Results", "Named Queries", "License Usage Terms",
        "Known Limitations", "Checksums", "Dimension Dictionary", "Capitalization Table",
        "Consolidated SOTP", "Software DCF-Multiples", "Atlas-Willow Optionality",
        "Advisory Valuation", "EV to Equity Value",
    ),
    "monthly_balance_sheet": ("Monthly Balance Sheet",),
    "monthly_cash_flow": ("Monthly Cash Flow",),
    "monthly_equity": ("Changes in Equity",),
    "monthly_working_capital": ("Working Capital",),
    "monthly_fixed_assets": ("Capex Deprec Depletion", "Fixed Assets"),
    "monthly_debt": ("Debt and Liquidity", "Debt Schedule"),
    "monthly_inventory": ("Inventory Rollforward",),
}


def _build_sheet_specs() -> dict[str, SheetSpec]:
    assignments: dict[str, str] = {}
    for query, sheet_names in _QUERY_GROUPS.items():
        for sheet_name in sheet_names:
            if sheet_name in assignments:
                raise ValueError(f"Duplicate workbook sheet specification: {sheet_name}")
            assignments[sheet_name] = query
    required = {sheet for sheets in WORKBOOKS.values() for sheet in sheets}
    missing = required - assignments.keys()
    unexpected = assignments.keys() - required
    if missing or unexpected:
        raise ValueError(
            f"Workbook specification mismatch; missing={sorted(missing)}, "
            f"unexpected={sorted(unexpected)}"
        )
    return {
        sheet_name: SheetSpec(
            purpose=f"Database-controlled evidence for {sheet_name}",
            query=query,
            sort_order=("query-defined deterministic order",),
        )
        for sheet_name, query in assignments.items()
    }


SHEET_SPECS = _build_sheet_specs()


def _rows_for_sheet(
    session: Session, sheet_name: str, generation_run_id: str
) -> list[dict[str, Any]]:
    specification = SHEET_SPECS[sheet_name]
    monthly_columns = {
        "monthly_balance_sheet": (
            "period", "assets", "liabilities", "equity", "balance_sheet_difference"
        ),
        "monthly_cash_flow": ("period", "cash_flow", "ending_cash"),
        "monthly_equity": ("period", "net_income", "equity"),
        "monthly_working_capital": ("period", "working_capital"),
        "monthly_fixed_assets": ("period", "net_fixed_assets"),
        "monthly_debt": ("period", "debt"),
        "monthly_inventory": ("period", "inventory"),
    }
    if specification.query in monthly_columns:
        columns = monthly_columns[specification.query]
        results: list[dict[str, Any]] = []
        for row in monthly_statements(session, generation_run_id):
            materialized: dict[str, Any] = dict(row)
            results.append({column: materialized[column] for column in columns})
        return results
    return run_named_query(session, specification.query, generation_run_id)[:5000]


def _write_rows(
    worksheet: Any, rows: Iterable[dict[str, Any]], header_format: Any, money_format: Any
) -> None:
    materialized = list(rows)
    if not materialized:
        worksheet.write_row(6, 0, ["Status", "No records for this optional domain"], header_format)
        return
    headings = list(materialized[0])
    worksheet.write_row(6, 0, headings, header_format)
    for row_number, row in enumerate(materialized, start=7):
        for column, heading in enumerate(headings):
            value = row[heading]
            if isinstance(value, (int, float)):
                worksheet.write_number(row_number, column, float(value), money_format)
            else:
                worksheet.write(row_number, column, value)
    worksheet.autofilter(6, 0, 6 + len(materialized), len(headings) - 1)
    worksheet.freeze_panes(7, 1)


def generate_workbook_suite(
    session: Session,
    output_directory: Path = Path("workbooks/outputs"),
    *,
    generation_run_id: str,
) -> list[Path]:
    context = run_context(session, generation_run_id)
    run = session.get(GenerationRun, context.generation_run_id)
    if run is None:
        raise ValueError(f"Unknown generation run {generation_run_id!r}")
    output_directory.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    debit, credit = session.execute(
        select(func.sum(JournalLine.debit), func.sum(JournalLine.credit))
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(JournalEntry.generation_run_id.in_(context.included_run_ids))
    ).one()
    assumption_count = session.scalar(
        select(func.count(ScenarioValue.id)).where(
            ScenarioValue.generation_run_id == context.generation_run_id
        )
    ) or 0
    account_count = session.scalar(select(func.count(Account.id))) or 0
    journal_count = session.scalar(
        select(func.count(JournalEntry.id)).where(
            JournalEntry.generation_run_id.in_(context.included_run_ids)
        )
    ) or 0
    for filename, sheets in WORKBOOKS.items():
        path = output_directory / filename
        workbook = xlsxwriter.Workbook(path)
        workbook.set_properties(
            {
                "title": filename,
                "company": "Sable Harbor",
                # OOXML core metadata is otherwise wall-clock dependent.
                "created": run.completed_at,
            }
        )
        title = workbook.add_format(
            {"bold": True, "font_size": 15, "font_color": "#FFFFFF", "bg_color": "#17384A"}
        )
        header = workbook.add_format(
            {"bold": True, "font_color": "#FFFFFF", "bg_color": "#17384A", "border": 1}
        )
        label = workbook.add_format({"bold": True, "font_color": "#17384A"})
        input_format = workbook.add_format({"font_color": "#0000FF", "bg_color": "#FFF2CC"})
        money = workbook.add_format({"num_format": "#,##0.00;[Red](#,##0.00);-"})
        pass_format = workbook.add_format({"bold": True, "font_color": "#008000"})
        for sheet_name in sheets:
            sheet = workbook.add_worksheet(sheet_name)
            sheet.hide_gridlines(2)
            sheet.set_column(0, 0, 34)
            sheet.set_column(1, 12, 20)
            sheet.write(0, 0, f"SABLE HARBOR — {sheet_name}", title)
            sheet.merge_range(0, 0, 0, 5, f"SABLE HARBOR — {sheet_name}", title)
            sheet.write(2, 0, "Scenario", label)
            sheet.write(2, 1, context.scenario_code, input_format)
            sheet.write(3, 0, "As of", label)
            sheet.write(3, 1, "2026-08-31")
            sheet.write(4, 0, "Generation seed", label)
            sheet.write_number(4, 1, run.seed, input_format)
            sheet.write(5, 0, "Source commit", label)
            sheet.write(5, 1, run.git_commit)
            if sheet_name == "Checks":
                sheet.write_row(7, 0, ["Control", "Database value", "Workbook result"], header)
                controls = [
                    ("Journal debits equal credits", float((debit or 0) - (credit or 0))),
                    ("Accounts loaded", account_count),
                    ("Journals loaded", journal_count),
                    ("Scenario values loaded", assumption_count),
                ]
                for row_index, (control, value) in enumerate(controls, start=8):
                    sheet.write(row_index, 0, control)
                    sheet.write_number(row_index, 1, value, money)
                    if control == "Journal debits equal credits":
                        formula = f'=IF(ABS(B{row_index + 1})<=0.01,"PASS","FAIL")'
                    else:
                        formula = f'=IF(B{row_index + 1}>0,"PASS","FAIL")'
                    sheet.write_formula(row_index, 2, formula, pass_format, "PASS")
            else:
                _write_rows(
                    sheet,
                    _rows_for_sheet(session, sheet_name, generation_run_id),
                    header,
                    money,
                )
        workbook.close()
        outputs.append(path)
    return outputs
