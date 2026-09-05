import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import xlsxwriter  # type: ignore[import-untyped]
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import (
    Account,
    FiscalPeriod,
    JournalEntry,
    JournalLine,
    ScenarioValue,
)
from sable_harbor.accounting.validation import validate_financial_integrity
from sable_harbor.exports.metadata import (
    REPOSITORY_ROOT,
    file_sha256,
    generation_manifest_metadata,
    included_run_metadata,
    public_profile,
)
from sable_harbor.exports.safety import (
    TECHNICAL_SAFETY_SCOPE,
    scan_generated_artifacts,
    spreadsheet_safe_value,
    staged_package_directory,
)
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import run_context
from sable_harbor.reporting_queries import named_queries, run_named_query
from sable_harbor.reports.statements import monthly_statements

WORKBOOKS: dict[str, list[str]] = {
    "SABLE_HARBOR_CONSOLIDATED_OPERATING_MODEL_v0.1.xlsx": [
        "Cover",
        "Run Control",
        "Monthly Consolidated P&L",
        "Monthly Balance Sheet",
        "Monthly Cash Flow",
        "Changes in Equity",
        "Working Capital",
        "Capex Deprec Depletion",
        "Debt and Liquidity",
        "Intercompany Reconciliation",
        "Checks",
        "Known Limitations",
    ],
    "SABLE_HARBOR_SOFTWARE_AND_SERVICES_v0.1.xlsx": [
        "Cover",
        "Run Control",
        "Customer Contract Summary",
        "Engagement Margin",
        "Headcount and Compensation",
        "Deferred Revenue Rollforward",
        "Journal Detail Extract",
        "Checks",
        "Known Limitations",
    ],
    "SABLE_HARBOR_INDUSTRIAL_OPERATIONS_v0.1.xlsx": [
        "Cover",
        "Run Control",
        "Red Wash Unit Cost",
        "Mine Inventory Shipment Bridge",
        "BS&T Route Customer Margin",
        "Cradle Project Contribution",
        "Fixed Assets",
        "Inventory Rollforward",
        "Industrial Intercompany",
        "Checks",
        "Known Limitations",
    ],
    "SABLE_HARBOR_GL_CLOSE_AND_SUBLEDGERS_v0.1.xlsx": [
        "Cover",
        "Run Control",
        "Trial Balance",
        "Journal Detail Extract",
        "AR-AP Exposure",
        "Deferred Revenue Rollforward",
        "Payroll Summary",
        "Fixed Assets",
        "Debt Schedule",
        "Intercompany Reconciliation",
        "Checks",
        "Known Limitations",
    ],
    "SABLE_HARBOR_CAPITAL_MA_AND_VALUATION_v0.1.xlsx": [
        "Cover",
        "Run Control",
        "Debt Schedule",
        "Scenario Driver Ranges",
        "Valuation Scope Limitation",
        "Checks",
        "Known Limitations",
    ],
    "SABLE_HARBOR_DATA_DICTIONARY_AND_RELEASE_CONTROL_v0.1.xlsx": [
        "Cover",
        "Run Control",
        "Release Coverage",
        "Assumption Impact",
        "Generation Runs",
        "Named Queries",
        "Checks",
        "Known Limitations",
    ],
}
EXCEL_MAX_ROWS = 1_048_576
WORKSHEET_DATA_START_ROW = 8


@dataclass(frozen=True)
class SheetSpec:
    purpose: str
    query: str
    units: str = "as labeled"
    sort_order: tuple[str, ...] = ("query-defined deterministic order",)
    required_columns: tuple[str, ...] = ()
    empty_state: str = "No records in the selected synthetic run context"
    tolerance: float = 0.0001


SHEET_SPECS: dict[str, SheetSpec] = {
    "Cover": SheetSpec(
        "Identifies this synthetic evidence workbook and its persisted run contract.",
        "@run_control",
        required_columns=("field", "value"),
    ),
    "Run Control": SheetSpec(
        "Reports the synthetic scenario, calibration boundary, current-canon basis, schema, and "
        "source lineage.",
        "@run_control",
        required_columns=("field", "value"),
    ),
    "Monthly Consolidated P&L": SheetSpec(
        "Monthly synthetic revenue and expense from posted selected-context journals.",
        "consolidated_monthly_pnl",
        "USD",
        required_columns=("period", "revenue", "expense"),
    ),
    "Monthly Balance Sheet": SheetSpec(
        "Monthly balance-sheet rollforward from the posted general ledger.",
        "@monthly_balance_sheet",
        "USD",
        required_columns=("period", "assets", "liabilities", "equity"),
    ),
    "Monthly Cash Flow": SheetSpec(
        "Monthly change in cash and ending cash; not a classified GAAP cash-flow statement.",
        "@monthly_cash_flow",
        "USD",
        required_columns=("period", "cash_flow", "ending_cash"),
    ),
    "Changes in Equity": SheetSpec(
        "Monthly modeled net income and ending equity from the general ledger.",
        "@monthly_equity",
        "USD",
        required_columns=("period", "net_income", "equity"),
    ),
    "Working Capital": SheetSpec(
        "Monthly modeled working-capital balance from general-ledger classifications.",
        "@monthly_working_capital",
        "USD",
        required_columns=("period", "working_capital"),
    ),
    "Capex Deprec Depletion": SheetSpec(
        "Monthly net fixed assets; depletion and a complete capex schedule are not implemented.",
        "@monthly_fixed_assets",
        "USD",
        required_columns=("period", "net_fixed_assets"),
    ),
    "Debt and Liquidity": SheetSpec(
        "Run-scoped debt draws, repayments, accrued interest, and availability.",
        "debt_covenant_calculation",
        "USD",
        required_columns=("facility_number", "principal_outstanding", "availability"),
    ),
    "Intercompany Reconciliation": SheetSpec(
        "Reciprocal intercompany operating balances and mismatches by entity pair and period.",
        "intercompany_mismatch_elimination",
    ),
    "Customer Contract Summary": SheetSpec(
        "Aggregated synthetic contract value and term dates by customer identifier; not ARR/MRR.",
        "customer_arr_bridge",
        "USD",
        required_columns=("customer_id", "contracted_value"),
    ),
    "Engagement Margin": SheetSpec(
        "Billed revenue, attributed cost, and approved-time WIP by synthetic engagement.",
        "engagement_margin_wip",
        "USD",
        required_columns=("engagement", "revenue", "cost", "wip"),
    ),
    "Headcount and Compensation": SheetSpec(
        "Synthetic workforce count and annual loaded cost by segment and function.",
        "employee_loaded_cost",
        "USD and workers",
        required_columns=("segment_code", "function_code", "workers"),
    ),
    "Deferred Revenue Rollforward": SheetSpec(
        "Monthly general-ledger movement in modeled deferred revenue.",
        "deferred_revenue_rollforward",
        "USD",
        required_columns=("period", "movement"),
    ),
    "Journal Detail Extract": SheetSpec(
        "Posted journal lines with source identifiers for the selected run context.",
        "journal_to_source_trace",
        "USD",
        required_columns=("journal_id", "source_type", "source_id", "account"),
    ),
    "Red Wash Unit Cost": SheetSpec(
        "Synthetic batch production cost divided by synthetic U3O8 output.",
        "red_wash_unit_cost_bridge",
        "USD per modeled lb",
        required_columns=("batch_number", "production_cost", "pounds_u3o8", "cost_per_lb"),
    ),
    "Mine Inventory Shipment Bridge": SheetSpec(
        "Synthetic production less linked shipment quantity; not a reserve or assay statement.",
        "mine_inventory_shipment_reconciliation",
        required_columns=("batch_number", "produced", "shipped", "closing"),
    ),
    "BS&T Route Customer Margin": SheetSpec(
        "Synthetic BS&T railway waybill revenue less modeled fuel and crew direct cost.",
        "bst_route_customer_margin",
        "USD",
        required_columns=("waybill_number", "revenue", "direct_cost"),
    ),
    "Cradle Project Contribution": SheetSpec(
        "Synthetic recovery-run contribution; not a discounted cash-flow valuation.",
        "cradle_project_economics",
        "USD",
        required_columns=("run_number", "gross_sale", "project_contribution"),
    ),
    "Fixed Assets": SheetSpec(
        "Run-scoped fixed-asset gross cost and separately aggregated depreciation.",
        "fixed_asset_rollforward",
        "USD",
        required_columns=("entity_id", "asset_class", "gross_cost"),
    ),
    "Inventory Rollforward": SheetSpec(
        "Monthly general-ledger inventory balance; not a lot-level physical count.",
        "@monthly_inventory",
        "USD",
        required_columns=("period", "inventory"),
    ),
    "Industrial Intercompany": SheetSpec(
        "Reciprocal industrial intercompany operating balances and mismatches.",
        "intercompany_mismatch_elimination",
    ),
    "Trial Balance": SheetSpec(
        "Posted debit and credit totals by legal entity and account.",
        "entity_trial_balance",
        "USD",
        required_columns=("entity", "account", "debit", "credit"),
    ),
    "AR-AP Exposure": SheetSpec(
        "Invoice/bill exposure buckets and explicit residual bridge to the general ledger.",
        "ar_ap_exposure_reconciliation",
        "USD",
        required_columns=("ledger", "open_amount", "gl_open_amount"),
    ),
    "Payroll Summary": SheetSpec(
        "Synthetic workforce count and annual cost; not a payroll-register extract.",
        "employee_loaded_cost",
        "USD and workers",
    ),
    "Debt Schedule": SheetSpec(
        "Run-scoped modeled debt draws, repayments, interest, and availability.",
        "debt_covenant_calculation",
        "USD",
    ),
    "Scenario Driver Ranges": SheetSpec(
        "Ranges among values stored in the selected scenario run; not a cross-run comparison.",
        "assumption_impact",
    ),
    "Valuation Scope Limitation": SheetSpec(
        "States that this v0.1 workbook does not contain a completed M&A or valuation model.",
        "@valuation_limitation",
        required_columns=("status", "limitation"),
    ),
    "Release Coverage": SheetSpec(
        "Counts journal sources represented in the selected release context.",
        "release_coverage_lineage",
        required_columns=("source_type", "source_records", "journal_entries"),
    ),
    "Assumption Impact": SheetSpec(
        "Stored selected-run metric ranges; no claim of causal sensitivity attribution.",
        "assumption_impact",
    ),
    "Generation Runs": SheetSpec(
        "Persisted identity and lifecycle fields for selected and included runs.",
        "@generation_runs",
    ),
    "Named Queries": SheetSpec(
        "Named SQL evidence views exercised by the validation registry.",
        "@named_queries",
        required_columns=("query",),
    ),
    "Known Limitations": SheetSpec(
        "Material scope limits that prevent synthetic evidence from being mistaken for canon "
        "or audit.",
        "@known_limitations",
        required_columns=("status", "limitation"),
    ),
    "Checks": SheetSpec(
        "Formula-backed workbook checks plus the database financial-validation registry.",
        "@checks",
    ),
}


def _assert_registry_complete() -> None:
    required = {sheet for sheets in WORKBOOKS.values() for sheet in sheets}
    missing = required - SHEET_SPECS.keys()
    unexpected = SHEET_SPECS.keys() - required
    if missing or unexpected:
        raise ValueError(
            f"Workbook specification mismatch; missing={sorted(missing)}, "
            f"unexpected={sorted(unexpected)}"
        )


_assert_registry_complete()


def _run_control(
    run: GenerationRun, scenario_code: str, generation_metadata: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {"field": "generation_run_id", "value": run.id},
        {"field": "build_id", "value": run.build_id},
        {"field": "profile", "value": public_profile(run.profile)},
        {"field": "scenario_id", "value": run.scenario_id},
        {"field": "scenario_code", "value": scenario_code},
        {"field": "scenario_version", "value": generation_metadata["scenario_version"]},
        {"field": "classification", "value": "SYNTHETIC_SCENARIO_EVIDENCE"},
        {"field": "epistemic_mode", "value": generation_metadata["epistemic_mode"]},
        {
            "field": "synthetic_calibration_through",
            "value": generation_metadata["synthetic_calibration_through"],
        },
        {"field": "forecast_from", "value": generation_metadata["forecast_from"]},
        {
            "field": "effective_period",
            "value": json.dumps(generation_metadata["effective_period"], sort_keys=True),
        },
        {
            "field": "canon_effective_through",
            "value": generation_metadata["canon_effective_through"],
        },
        {"field": "canon_reconciled_at", "value": generation_metadata["canon_reconciled_at"]},
        {"field": "prepared_at", "value": generation_metadata["prepared_at"]},
        {
            "field": "source_snapshot_ids",
            "value": json.dumps(generation_metadata["source_snapshot_ids"], sort_keys=True),
        },
        {
            "field": "source_snapshot_digests",
            "value": json.dumps(generation_metadata["source_snapshot_digests"], sort_keys=True),
        },
        {"field": "generator_version", "value": run.generator_version},
        {"field": "generator_source_digest", "value": run.generator_source_digest},
        {"field": "input_version", "value": generation_metadata["input_version"]},
        {"field": "input_manifest_digest", "value": run.input_manifest_digest},
        {"field": "assumptions_digest", "value": run.assumptions_digest},
        {"field": "canon_source_lock_digest", "value": run.canon_source_lock_digest},
        {"field": "schema_head", "value": run.schema_head},
        {"field": "source_commit", "value": run.git_commit},
        {"field": "built_at", "value": generation_metadata["built_at"]},
    ]


def _rows_for_sheet(
    session: Session,
    sheet_name: str,
    generation_run_id: str,
    run: GenerationRun,
    scenario_code: str,
    generation_metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    query = SHEET_SPECS[sheet_name].query
    if query == "@run_control":
        return _run_control(run, scenario_code, generation_metadata)
    if query == "@valuation_limitation":
        return [
            {
                "status": "NOT_IMPLEMENTED",
                "limitation": (
                    "No completed capitalization, purchase-price allocation, DCF, NAV, or M&A "
                    "opinion is included in v0.1; only scenario evidence is supplied."
                ),
            }
        ]
    if query == "@known_limitations":
        return [
            {
                "status": "SYNTHETIC_ONLY",
                "limitation": (
                    "Generated amounts are deterministic scenario/calibration fixtures, "
                    "not observed, audited, reserve, tax, legal, or investment facts."
                ),
            }
        ]
    if query == "@named_queries":
        return [{"query": name} for name in named_queries()]
    if query == "@generation_runs":
        context = run_context(session, generation_run_id)
        included_runs = [
            item
            for run_id in context.included_run_ids
            if (item := session.get(GenerationRun, run_id)) is not None
        ]
        return included_run_metadata(included_runs, selected_run_id=context.generation_run_id)
    monthly_columns = {
        "@monthly_balance_sheet": (
            "period",
            "assets",
            "liabilities",
            "equity",
            "balance_sheet_difference",
        ),
        "@monthly_cash_flow": ("period", "cash_flow", "ending_cash"),
        "@monthly_equity": ("period", "net_income", "equity"),
        "@monthly_working_capital": ("period", "working_capital"),
        "@monthly_fixed_assets": ("period", "net_fixed_assets"),
        "@monthly_inventory": ("period", "inventory"),
    }
    if query in monthly_columns:
        columns = monthly_columns[query]
        selected_rows: list[dict[str, Any]] = []
        for statement_row in monthly_statements(session, generation_run_id):
            row_values: dict[str, Any] = dict(statement_row)
            selected_rows.append({column: row_values[column] for column in columns})
        return selected_rows
    return run_named_query(session, query, generation_run_id)


def _write_rows(
    worksheet: Any,
    rows: Iterable[dict[str, Any]],
    header_format: Any,
    money_format: Any,
    empty_state: str,
) -> None:
    materialized = list(rows)
    if not materialized:
        worksheet.write_row(7, 0, ["Status", "Limitation"], header_format)
        worksheet.write_row(8, 0, ["NO_RECORDS", empty_state])
        return
    if len(materialized) > EXCEL_MAX_ROWS - WORKSHEET_DATA_START_ROW:
        raise ValueError(
            "Workbook sheet exceeds the Excel row limit: "
            f"{len(materialized)} data rows (maximum "
            f"{EXCEL_MAX_ROWS - WORKSHEET_DATA_START_ROW})"
        )
    headings = list(materialized[0])
    worksheet.write_row(7, 0, headings, header_format)
    for row_number, row in enumerate(materialized, start=8):
        for column, heading in enumerate(headings):
            value = row[heading]
            if isinstance(value, (int, float, Decimal)):
                worksheet.write_number(row_number, column, float(value), money_format)
            elif isinstance(value, (date, datetime)):
                worksheet.write(row_number, column, value.isoformat())
            else:
                worksheet.write(row_number, column, spreadsheet_safe_value(value))
    worksheet.autofilter(7, 0, 7 + len(materialized), len(headings) - 1)
    worksheet.freeze_panes(8, 1)


def _build_workbook_suite(
    session: Session,
    output_directory: Path = Path("workbooks/outputs"),
    *,
    generation_run_id: str,
    generated_at: datetime | None = None,
) -> list[Path]:
    context = run_context(session, generation_run_id)
    run = session.get(GenerationRun, context.generation_run_id)
    if run is None or run.completed_at is None:
        raise ValueError(f"Unknown or incomplete generation run {generation_run_id!r}")
    validation = validate_financial_integrity(session, generation_run_id)
    output_directory.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    controlled_timestamp = generated_at or run.completed_at
    period_start, period_end = session.execute(
        select(func.min(FiscalPeriod.code), func.max(FiscalPeriod.code))
        .join(JournalEntry, JournalEntry.period_id == FiscalPeriod.id)
        .where(
            JournalEntry.state == "POSTED",
            JournalEntry.generation_run_id.in_(context.included_run_ids),
        )
    ).one()
    if period_start is None or period_end is None:
        raise ValueError("Workbook suite requires a nonempty reporting period")
    included_runs = [
        item
        for run_id in context.included_run_ids
        if (item := session.get(GenerationRun, run_id)) is not None
    ]
    if len(included_runs) != len(context.included_run_ids):
        raise ValueError("Workbook context contains an unknown generation run")
    generation_metadata = generation_manifest_metadata(
        run,
        scenario_code=context.scenario_code,
        built_at=controlled_timestamp,
        effective_from=str(period_start),
        effective_through=str(period_end),
        effective_period_basis="posted_fiscal_period_codes",
    )
    debit, credit = session.execute(
        select(func.sum(JournalLine.debit), func.sum(JournalLine.credit))
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.state == "POSTED",
            JournalEntry.generation_run_id.in_(context.included_run_ids),
        )
    ).one()
    controls = [
        ("Journal debit-credit difference", float((debit or 0) - (credit or 0)), True),
        (
            "Accounts loaded",
            session.scalar(
                select(func.count(Account.id.distinct()))
                .join(JournalLine, JournalLine.account_id == Account.id)
                .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
                .where(
                    JournalEntry.state == "POSTED",
                    JournalEntry.generation_run_id.in_(context.included_run_ids),
                )
            )
            or 0,
            False,
        ),
        (
            "Journals loaded",
            session.scalar(
                select(func.count(JournalEntry.id)).where(
                    JournalEntry.generation_run_id.in_(context.included_run_ids)
                )
            )
            or 0,
            False,
        ),
        (
            "Scenario values loaded",
            session.scalar(
                select(func.count(ScenarioValue.id)).where(
                    ScenarioValue.generation_run_id == context.generation_run_id
                )
            )
            or 0,
            False,
        ),
    ]
    for filename, sheets in WORKBOOKS.items():
        path = output_directory / filename
        workbook = xlsxwriter.Workbook(
            path, {"strings_to_formulas": False, "strings_to_urls": False}
        )
        workbook.set_properties(
            {"title": filename, "company": "Sable Harbor", "created": controlled_timestamp}
        )
        workbook.set_calc_mode("auto")
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
        fail_format = workbook.add_format({"bold": True, "font_color": "#C00000"})
        for sheet_name in sheets:
            specification = SHEET_SPECS[sheet_name]
            sheet = workbook.add_worksheet(sheet_name)
            sheet.hide_gridlines(2)
            sheet.set_column(0, 0, 34)
            sheet.set_column(1, 12, 22)
            sheet.merge_range(0, 0, 0, 5, f"SABLE HARBOR — {sheet_name}", title)
            sheet.merge_range(1, 0, 1, 8, specification.purpose)
            sheet.write(2, 0, "Scenario", label)
            sheet.write(2, 1, context.scenario_code, input_format)
            sheet.write(2, 3, "Epistemic mode", label)
            sheet.write(2, 4, generation_metadata["epistemic_mode"])
            sheet.write(3, 0, "Synthetic calibration through", label)
            sheet.write(3, 1, generation_metadata["synthetic_calibration_through"] or "UNSET")
            sheet.write(3, 3, "Canon effective through", label)
            sheet.write(3, 4, generation_metadata["canon_effective_through"])
            sheet.write(4, 0, "Forecast begins", label)
            sheet.write(4, 1, run.forecast_from.isoformat() if run.forecast_from else "UNSET")
            sheet.write(4, 3, "Canon reconciled", label)
            sheet.write(4, 4, generation_metadata["canon_reconciled_at"])
            sheet.write(5, 0, "Generation seed", label)
            sheet.write_number(5, 1, run.seed, input_format)
            sheet.write(5, 3, "Source commit", label)
            sheet.write(5, 4, run.git_commit)
            if sheet_name == "Checks":
                sheet.write_row(7, 0, ["Control", "Database value", "Workbook result"], header)
                for row_index, (control_name, value, zero_tolerance) in enumerate(
                    controls, start=8
                ):
                    passed = abs(float(value)) <= 0.01 if zero_tolerance else float(value) > 0
                    sheet.write(row_index, 0, control_name)
                    sheet.write_number(row_index, 1, float(value), money)
                    excel_row = row_index + 1
                    formula = (
                        f'=IF(ABS(B{excel_row})<=0.01,"PASS","FAIL")'
                        if zero_tolerance
                        else f'=IF(B{excel_row}>0,"PASS","FAIL")'
                    )
                    cached = "PASS" if passed else "FAIL"
                    sheet.write_formula(
                        row_index,
                        2,
                        formula,
                        pass_format if passed else fail_format,
                        cached,
                    )
                registry_start = 8 + len(controls) + 2
                sheet.write_row(
                    registry_start, 0, ["Validation registry", "Observed", "Status"], header
                )
                for offset, validation_control in enumerate(validation.controls, start=1):
                    sheet.write(registry_start + offset, 0, validation_control.code)
                    sheet.write(registry_start + offset, 1, validation_control.observed)
                    sheet.write(
                        registry_start + offset,
                        2,
                        "PASS" if validation_control.passed else "FAIL",
                        pass_format if validation_control.passed else fail_format,
                    )
            else:
                rows = _rows_for_sheet(
                    session,
                    sheet_name,
                    generation_run_id,
                    run,
                    context.scenario_code,
                    generation_metadata,
                )
                if rows and specification.required_columns:
                    missing = set(specification.required_columns) - rows[0].keys()
                    if missing:
                        raise ValueError(
                            f"Sheet {sheet_name!r} is missing required columns {sorted(missing)}"
                        )
                _write_rows(sheet, rows, header, money, specification.empty_state)
        workbook.close()
        outputs.append(path)
    workbook_inventory = [
        {"path": path.name, "bytes": path.stat().st_size, "sha256": file_sha256(path)}
        for path in sorted(outputs)
    ]
    manifest = {
        "package_name": "workbook-suite",
        "package_version": "0.1.0",
        "generation_run_id": context.generation_run_id,
        "included_run_ids": list(context.included_run_ids),
        "included_runs": included_run_metadata(
            included_runs, selected_run_id=context.generation_run_id
        ),
        "profile": public_profile(run.profile),
        "seed": run.seed,
        "source_commit": run.git_commit,
        "classification": "PUBLIC_SAFE_SYNTHETIC_RELEASE_CANDIDATE",
        "checksum_algorithm": "SHA-256",
        "workbooks": workbook_inventory,
        "output_hashes": {artifact["path"]: artifact["sha256"] for artifact in workbook_inventory},
        "artifact_safety_scan": {"status": "PENDING"},
        **generation_metadata,
    }
    manifest_path = output_directory / "workbook-suite-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    scan_targets = [*outputs, manifest_path]
    failures = [failure for path in scan_targets for failure in scan_generated_artifacts(path)]
    if failures:
        raise ValueError("Workbook artifact safety scan failed:\n" + "\n".join(failures))
    manifest["artifact_safety_scan"] = {
        "status": "PASS",
        "failures": 0,
        "scope": TECHNICAL_SAFETY_SCOPE,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    final_failures = [
        failure for path in scan_targets for failure in scan_generated_artifacts(path)
    ]
    if final_failures:
        raise ValueError(
            "Final workbook artifact safety scan failed:\n" + "\n".join(final_failures)
        )
    checksum_path = output_directory / "SHA256SUMS.txt"
    checksum_path.write_text(
        "".join(f"{file_sha256(path)}  {path.name}\n" for path in sorted(scan_targets))
    )
    checksum_failures = scan_generated_artifacts(checksum_path)
    if checksum_failures:
        raise ValueError("Workbook checksum safety scan failed:\n" + "\n".join(checksum_failures))
    return outputs


def generate_workbook_suite(
    session: Session,
    output_directory: Path = Path("workbooks/outputs"),
    *,
    generation_run_id: str,
    generated_at: datetime | None = None,
) -> list[Path]:
    """Build and atomically publish one complete, governed workbook suite."""
    requested = output_directory.expanduser()
    resolved = requested.resolve()
    release_root = REPOSITORY_ROOT / "releases/generated"
    repository_output_root = (
        release_root
        if release_root.resolve() in resolved.parents
        else REPOSITORY_ROOT / "workbooks"
    )
    with staged_package_directory(
        requested,
        package_kind="workbook-suite-v0.1",
        repository_output_root=repository_output_root,
    ) as (final_destination, staging):
        staged_outputs = _build_workbook_suite(
            session,
            staging,
            generation_run_id=generation_run_id,
            generated_at=generated_at,
        )
        relative_outputs = [path.relative_to(staging) for path in staged_outputs]
    return [final_destination / path for path in relative_outputs]
