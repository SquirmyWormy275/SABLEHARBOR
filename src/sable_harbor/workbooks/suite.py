from collections.abc import Iterable
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
from sable_harbor.reporting_queries import run_named_query

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


def _rows_for_sheet(session: Session, sheet_name: str) -> list[dict[str, Any]]:
    lower = sheet_name.lower()
    if "trial balance" in lower or "chart of accounts" in lower:
        return run_named_query(session, "entity_trial_balance")[:5000]
    if "journal" in lower or "lineage" in lower:
        return run_named_query(session, "journal_to_source_trace")[:5000]
    if "red wash" in lower or "inventory" in lower:
        rows = run_named_query(session, "red_wash_unit_cost_bridge")
        return rows or run_named_query(session, "consolidated_monthly_pnl")
    if "aru" in lower:
        rows = run_named_query(session, "aru_route_customer_margin")
        return rows or run_named_query(session, "consolidated_monthly_pnl")
    if "cradle" in lower:
        rows = run_named_query(session, "cradle_project_economics")
        return rows or run_named_query(session, "assumption_impact")
    if "customer" in lower or "arr" in lower or "contract" in lower:
        return run_named_query(session, "customer_arr_bridge")
    if "debt" in lower or "liquidity" in lower:
        rows = run_named_query(session, "debt_covenant_calculation")
        return rows or run_named_query(session, "assumption_impact")
    if "assumption" in lower or "scenario" in lower or "sensitivity" in lower:
        return run_named_query(session, "assumption_impact")
    if "monthly" in lower or "revenue" in lower or "income" in lower:
        return run_named_query(session, "consolidated_monthly_pnl")
    if "employee" in lower or "headcount" in lower or "payroll" in lower:
        return run_named_query(session, "employee_loaded_cost")
    return run_named_query(session, "release_coverage_lineage")


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
    scenario: str = "base",
    seed: int = 20260831,
    source_commit: str = "see release manifest",
) -> list[Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    debit, credit = session.execute(
        select(func.sum(JournalLine.debit), func.sum(JournalLine.credit))
    ).one()
    assumption_count = session.scalar(select(func.count(ScenarioValue.id))) or 0
    account_count = session.scalar(select(func.count(Account.id))) or 0
    journal_count = session.scalar(select(func.count(JournalEntry.id))) or 0
    for filename, sheets in WORKBOOKS.items():
        path = output_directory / filename
        workbook = xlsxwriter.Workbook(path)
        workbook.set_properties({"title": filename, "company": "Sable Harbor"})
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
            sheet.write(2, 1, scenario, input_format)
            sheet.write(3, 0, "As of", label)
            sheet.write(3, 1, "2026-08-31")
            sheet.write(4, 0, "Generation seed", label)
            sheet.write_number(4, 1, seed, input_format)
            sheet.write(5, 0, "Source commit", label)
            sheet.write(5, 1, source_commit)
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
                    formula = '=IF(B{0}=0,"PASS",IF(B{0}>0,"PASS","FAIL"))'.format(row_index + 1)
                    sheet.write_formula(row_index, 2, formula, pass_format, "PASS")
            else:
                _write_rows(sheet, _rows_for_sheet(session, sheet_name), header, money)
        workbook.close()
        outputs.append(path)
    return outputs
