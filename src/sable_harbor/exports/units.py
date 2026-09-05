import csv
import hashlib
import json
import re
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import xlsxwriter  # type: ignore[import-untyped]
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from sable_harbor.accounting.validation import validate_financial_integrity
from sable_harbor.exports.metadata import (
    REPOSITORY_ROOT,
    file_sha256,
    generation_manifest_metadata,
    included_run_metadata,
    public_profile,
    require_current_build_identity,
)
from sable_harbor.exports.safety import (
    TECHNICAL_SAFETY_SCOPE,
    scan_generated_artifacts,
    spreadsheet_safe_value,
    staged_package_directory,
)
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import run_context

UNIT_REGISTRY = REPOSITORY_ROOT / "config/finance/unit_scopes.json"
UNIT_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SCOPE_CODE = re.compile(r"^[A-Z][A-Z0-9_]*$")
SUPPORTED_UNIT_IDS = {
    "foundry-field",
    "willow",
    "atlas-meridian",
    "pale-sun",
    "project-cradle",
    "american-resource-utility",
    "advisory",
}
MONEY_QUANTUM = Decimal("0.0001")
EXCEL_MAX_ROWS = 1_048_576
UNIT_TRIAL_BALANCE_DATA_START_ROW = 3


def _scope_codes(unit: dict[str, Any], key: str) -> list[str]:
    values = unit.get(key)
    if not isinstance(values, list) or not values:
        raise ValueError(f"Unit {unit.get('id')!r} requires a nonempty {key!r} list")
    if any(not isinstance(value, str) or SCOPE_CODE.fullmatch(value) is None for value in values):
        raise ValueError(f"Unit {unit.get('id')!r} has an unsafe {key!r} value")
    if len(values) != len(set(values)):
        raise ValueError(f"Unit {unit.get('id')!r} has duplicate {key!r} values")
    return values


def _unit_registry() -> dict[str, Any]:
    registry = json.loads(UNIT_REGISTRY.read_text())
    if not isinstance(registry, dict) or registry.get("schema_version") != "1.0.0":
        raise ValueError("Unit scope registry must use schema_version '1.0.0'")
    if registry.get("classification") != "MODEL_PROPOSED_FINANCE_REPORTING_SCOPE":
        raise ValueError("Unit scope registry has an unsupported classification")
    units = registry.get("units")
    if not isinstance(units, list) or not units:
        raise ValueError("Unit scope registry requires a nonempty units list")
    identifiers: list[str] = []
    all_segments: list[str] = []
    unsegmented_unit_count = 0
    for unit in units:
        if not isinstance(unit, dict):
            raise ValueError("Every unit scope must be an object")
        unit_id = unit.get("id")
        if not isinstance(unit_id, str) or UNIT_ID.fullmatch(unit_id) is None:
            raise ValueError(f"Unit scope has an unsafe id: {unit_id!r}")
        name = unit.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Unit {unit_id!r} requires a nonempty name")
        if not isinstance(unit.get("include_unsegmented"), bool):
            raise ValueError(f"Unit {unit_id!r} requires a Boolean include_unsegmented value")
        if unit["include_unsegmented"]:
            unsegmented_unit_count += 1
        _scope_codes(unit, "entity_codes")
        segments = _scope_codes(unit, "segment_codes")
        _scope_codes(unit, "site_codes")
        identifiers.append(unit_id)
        all_segments.extend(segments)
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Unit scope registry has duplicate unit ids")
    if set(identifiers) != SUPPORTED_UNIT_IDS:
        raise ValueError("Unit scope registry must define exactly the supported seven units")
    if len(all_segments) != len(set(all_segments)):
        raise ValueError("Unit scope registry assigns a reporting segment to multiple units")
    if unsegmented_unit_count > 1:
        raise ValueError("At most one unit scope may include unsegmented journal lines")
    return registry


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("status\nNO_RECORDS\n")
        return
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(
            [
                {column: spreadsheet_safe_value(value) for column, value in row.items()}
                for row in rows
            ]
        )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unit_lines(
    session: Session,
    run_ids: tuple[str, ...],
    entity_codes: list[str],
    segments: list[str],
    *,
    include_unsegmented: bool,
) -> list[dict[str, Any]]:
    statement = text(
        """
        SELECT je.id AS journal_entry_id, je.entry_date, je.source_type, je.source_id,
               le.code AS entity_code, jl.id AS journal_line_id, a.code AS account_code,
               a.name AS account_name, a.account_class, jl.segment_code,
               cp.code AS counterparty_code, jl.debit, jl.credit
        FROM journal_line jl
        JOIN journal_entry je ON je.id = jl.entry_id
        JOIN accounting_book ab ON ab.id = je.book_id
        JOIN legal_entity le ON le.id = ab.entity_id
        JOIN account a ON a.id = jl.account_id
        LEFT JOIN legal_entity cp ON cp.id = jl.counterparty_entity_id
        WHERE je.state = 'POSTED'
          AND je.generation_run_id IN (:actual_run_id, :generation_run_id)
          AND le.code IN :entity_codes
          AND (jl.segment_code IN :segments
               OR (:include_unsegmented AND jl.segment_code IS NULL))
        ORDER BY je.entry_date, je.id, jl.id
        """
    ).bindparams(
        bindparam("entity_codes", expanding=True),
        bindparam("segments", expanding=True),
    )
    return [
        {key: str(value) if value is not None else "" for key, value in row.items()}
        for row in session.execute(
            statement,
            {
                "actual_run_id": run_ids[0],
                "generation_run_id": run_ids[-1],
                "entity_codes": entity_codes,
                "segments": segments,
                "include_unsegmented": include_unsegmented,
            },
        ).mappings()
    ]


def _trial_balance(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    balances: dict[tuple[str, str, str], tuple[Decimal, Decimal]] = {}
    for row in lines:
        key = (row["account_code"], row["account_name"], row["account_class"])
        debit, credit = balances.get(key, (Decimal(0), Decimal(0)))
        balances[key] = (debit + Decimal(row["debit"]), credit + Decimal(row["credit"]))
    return [
        {
            "account_code": code,
            "account_name": name,
            "account_class": account_class,
            "debit": str(debit),
            "credit": str(credit),
            "balance": str(debit - credit),
        }
        for (code, name, account_class), (debit, credit) in sorted(balances.items())
    ]


def _scoped_rows(
    session: Session,
    sql: str,
    run_ids: tuple[str, ...],
    entity_codes: list[str],
) -> list[dict[str, Any]]:
    statement = text(sql).bindparams(bindparam("entity_codes", expanding=True))
    return [
        {key: str(value) if value is not None else "" for key, value in row.items()}
        for row in session.execute(
            statement,
            {
                "actual_run_id": run_ids[0],
                "generation_run_id": run_ids[-1],
                "entity_codes": entity_codes,
            },
        ).mappings()
    ]


def _operational_registers(
    session: Session,
    unit_id: str,
    run_ids: tuple[str, ...],
    entity_codes: list[str],
    segments: list[str],
    site_codes: list[str],
) -> dict[str, list[dict[str, Any]]]:
    shared = {
        "asset-register": """
            SELECT fa.asset_number, le.code AS entity_code, fa.asset_class,
                   fa.placed_in_service, fa.cost, fa.useful_life_months, fa.fact_state
            FROM fixed_asset fa JOIN legal_entity le ON le.id=fa.entity_id
            WHERE le.code IN :entity_codes
              AND fa.site_id IN (SELECT id FROM site WHERE code IN :site_codes)
              AND fa.generation_run_id IN (:actual_run_id,:generation_run_id)
            ORDER BY fa.asset_number
        """,
        "inventory-register": """
            SELECT il.lot_number, le.code AS entity_code, il.inventory_stage, il.quantity,
                   il.unit, il.carrying_value, il.as_of_date, il.fact_state
            FROM inventory_lot il JOIN legal_entity le ON le.id=il.entity_id
            WHERE le.code IN :entity_codes
              AND il.site_id IN (SELECT id FROM site WHERE code IN :site_codes)
              AND il.generation_run_id IN (:actual_run_id,:generation_run_id)
            ORDER BY il.lot_number
        """,
        "workforce-summary": """
            SELECT le.code AS entity_code, w.worker_type, w.segment_code, w.function_code,
                   COUNT(*) AS workers, SUM(w.annual_cost) AS annual_cost
            FROM worker w JOIN legal_entity le ON le.id=w.entity_id
            WHERE le.code IN :entity_codes
              AND w.segment_code IN :segments
              AND w.generation_run_id IN (:actual_run_id,:generation_run_id)
            GROUP BY le.code,w.worker_type,w.segment_code,w.function_code
            ORDER BY le.code,w.segment_code,w.function_code
        """,
    }
    domain = {
        "foundry-field": """
            SELECT c.contract_number,c.starts_on,c.ends_on,c.currency,
                   c.transaction_price,c.fact_state
            FROM customer_contract c JOIN legal_entity le ON le.id=c.entity_id
            WHERE le.code IN :entity_codes
              AND c.generation_run_id IN (:actual_run_id,:generation_run_id)
            ORDER BY c.contract_number
        """,
        "willow": """
            SELECT we.experiment_number,we.experiment_date,we.question,we.belief,we.budget,
                   we.actual_cost,we.observation,we.gate_decision,we.transfer_target
            FROM willow_experiment we JOIN legal_entity le ON le.id=we.entity_id
            WHERE le.code IN :entity_codes
              AND we.generation_run_id IN (:actual_run_id,:generation_run_id)
            ORDER BY we.experiment_number
        """,
        "atlas-meridian": """
            SELECT ae.evaluation_number,ae.evaluation_date,ae.model_version,
                   ae.investigation_question,ae.compute_cost,ae.validation_cost,
                   ae.customer_fee,ae.owns_final_decision
            FROM atlas_evaluation ae JOIN legal_entity le ON le.id=ae.entity_id
            WHERE le.code IN :entity_codes
              AND ae.generation_run_id IN (:actual_run_id,:generation_run_id)
            ORDER BY ae.evaluation_number
        """,
        "pale-sun": """
            SELECT mpb.batch_number,mpb.production_date,mpb.feed_tons,mpb.grade_fraction,
                   mpb.recovery_fraction,mpb.pounds_u3o8,mpb.production_cost
            FROM mine_production_batch mpb JOIN legal_entity le ON le.id=mpb.entity_id
            WHERE le.code IN :entity_codes
              AND mpb.generation_run_id IN (:actual_run_id,:generation_run_id)
            ORDER BY mpb.batch_number
        """,
        "project-cradle": """
            SELECT rr.run_number,rr.run_date,rr.host_operator_code,rr.feed_tons,
                   rr.grade_fraction,rr.recovery_fraction,rr.recovered_units,
                   rr.operating_cost,rr.host_share_amount,rr.gross_sale
            FROM recovery_run rr JOIN legal_entity le ON le.id=rr.entity_id
            WHERE le.code IN :entity_codes
              AND rr.generation_run_id IN (:actual_run_id,:generation_run_id)
            ORDER BY rr.run_number
        """,
        "american-resource-utility": """
            SELECT w.waybill_number,w.movement_date,w.carloads,w.tons,w.route_miles,
                   w.ton_miles,w.base_rate,w.fuel_surcharge,w.revenue,w.fuel_gallons,
                   w.fuel_cost,w.crew_hours,w.crew_cost,w.custody_status
            FROM waybill w JOIN legal_entity le ON le.id=w.entity_id
            WHERE le.code IN :entity_codes
              AND w.generation_run_id IN (:actual_run_id,:generation_run_id)
            ORDER BY w.waybill_number
        """,
        "advisory": """
            SELECT e.engagement_code,e.name,e.billing_method,e.starts_on,e.ends_on,e.fact_state
            FROM engagement e JOIN customer_contract c ON c.id=e.contract_id
            JOIN legal_entity le ON le.id=c.entity_id
            WHERE le.code IN :entity_codes
              AND e.generation_run_id IN (:actual_run_id,:generation_run_id)
            ORDER BY e.engagement_code
        """,
    }
    output = {}
    for name, sql in shared.items():
        parameters: dict[str, object] = {
            "actual_run_id": run_ids[0],
            "generation_run_id": run_ids[-1],
            "entity_codes": entity_codes,
        }
        expanding: list[Any] = [bindparam("entity_codes", expanding=True)]
        if ":segments" in sql:
            parameters["segments"] = segments
            expanding.append(bindparam("segments", expanding=True))
        if ":site_codes" in sql:
            parameters["site_codes"] = site_codes
            expanding.append(bindparam("site_codes", expanding=True))
        statement = text(sql).bindparams(*expanding)
        output[name] = [
            {key: str(value) if value is not None else "" for key, value in row.items()}
            for row in session.execute(statement, parameters).mappings()
        ]
    output["domain-registers/primary-register"] = _scoped_rows(
        session, domain[unit_id], run_ids, entity_codes
    )
    return output


def _statement_rows(trial_balance: list[dict[str, Any]], classes: set[str]) -> list[dict[str, Any]]:
    return [row for row in trial_balance if row["account_class"] in classes]


def _cash_flow_rows(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    movements: dict[str, Decimal] = {}
    for row in lines:
        if row["account_code"] != "1000":
            continue
        period = row["entry_date"][:7]
        movements[period] = movements.get(period, Decimal(0)) + (
            Decimal(row["debit"]) - Decimal(row["credit"])
        )
    ending_cash = Decimal(0)
    output = []
    for period, movement in sorted(movements.items()):
        ending_cash += movement
        output.append(
            {"period": period, "change_in_cash": str(movement), "ending_cash": str(ending_cash)}
        )
    return output


def _equity_change_rows(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    movements: dict[str, Decimal] = {}
    for row in lines:
        if row["account_class"] != "EQUITY":
            continue
        period = row["entry_date"][:7]
        movements[period] = movements.get(period, Decimal(0)) + (
            Decimal(row["credit"]) - Decimal(row["debit"])
        )
    ending_equity = Decimal(0)
    output = []
    for period, movement in sorted(movements.items()):
        ending_equity += movement
        output.append(
            {
                "period": period,
                "change_in_equity": str(movement),
                "ending_equity": str(ending_equity),
            }
        )
    return output


def _intercompany_rows(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    balances: dict[tuple[str, str, str], tuple[Decimal, Decimal]] = {}
    for row in lines:
        if not row["counterparty_code"]:
            continue
        key = (row["entity_code"], row["counterparty_code"], row["account_code"])
        debit, credit = balances.get(key, (Decimal(0), Decimal(0)))
        balances[key] = (debit + Decimal(row["debit"]), credit + Decimal(row["credit"]))
    return [
        {
            "entity_code": entity,
            "counterparty_code": counterparty,
            "account_code": account,
            "debit": str(debit),
            "credit": str(credit),
            "balance": str(debit - credit),
        }
        for (entity, counterparty, account), (debit, credit) in sorted(balances.items())
    ]


def _unit_control_results(
    lines: list[dict[str, Any]], allowed_segments: list[str], *, include_unsegmented: bool
) -> list[dict[str, str]]:
    debit = sum((Decimal(row["debit"]) for row in lines), Decimal(0))
    credit = sum((Decimal(row["credit"]) for row in lines), Decimal(0))
    journals: dict[str, tuple[Decimal, Decimal]] = {}
    for row in lines:
        journal_debit, journal_credit = journals.get(
            row["journal_entry_id"], (Decimal(0), Decimal(0))
        )
        journals[row["journal_entry_id"]] = (
            journal_debit + Decimal(row["debit"]),
            journal_credit + Decimal(row["credit"]),
        )
    invalid_journals = [
        journal_id
        for journal_id, (journal_debit, journal_credit) in journals.items()
        if journal_debit <= 0 or journal_debit != journal_credit
    ]
    out_of_scope = [
        row["journal_line_id"]
        for row in lines
        if row["segment_code"] not in allowed_segments
        and not (include_unsegmented and not row["segment_code"])
    ]
    checks = (
        ("UNIT_LINES_NONEMPTY", bool(lines), len(lines), "unit has scoped journal evidence"),
        (
            "UNIT_AGGREGATE_BALANCE",
            debit == credit,
            debit - credit,
            "unit-scoped debits equal credits",
        ),
        (
            "UNIT_JOURNALS_BALANCE",
            not invalid_journals,
            len(invalid_journals),
            "every included journal is independently balanced",
        ),
        (
            "UNIT_SEGMENT_SCOPE",
            not out_of_scope,
            len(out_of_scope),
            "every included line belongs to an allowed reporting segment",
        ),
        (
            "UNIT_SOURCE_LINEAGE",
            all(row["source_type"] and row["source_id"] for row in lines),
            len(lines),
            "every included line retains its journal source identity",
        ),
    )
    return [
        {
            "code": code,
            "status": "PASS" if passed else "FAIL",
            "observed": str(observed),
            "details": details,
        }
        for code, passed, observed, details in checks
    ]


def _enterprise_line_totals(
    session: Session, run_ids: tuple[str, ...]
) -> dict[str, tuple[Decimal, Decimal]]:
    rows = session.execute(
        text(
            "SELECT jl.id, jl.debit, jl.credit FROM journal_line jl "
            "JOIN journal_entry je ON je.id = jl.entry_id "
            "WHERE je.state = 'POSTED' "
            "AND je.generation_run_id IN (:actual_run_id, :generation_run_id)"
        ),
        {"actual_run_id": run_ids[0], "generation_run_id": run_ids[-1]},
    )
    return {
        row.id: (
            Decimal(str(row.debit)).quantize(MONEY_QUANTUM),
            Decimal(str(row.credit)).quantize(MONEY_QUANTUM),
        )
        for row in rows
    }


def _workbook(
    path: Path,
    unit_name: str,
    trial_balance: list[dict[str, Any]],
    created_at: datetime,
) -> None:
    if len(trial_balance) > EXCEL_MAX_ROWS - UNIT_TRIAL_BALANCE_DATA_START_ROW:
        raise ValueError(
            "Unit trial-balance workbook exceeds the Excel row limit: "
            f"{len(trial_balance)} data rows (maximum "
            f"{EXCEL_MAX_ROWS - UNIT_TRIAL_BALANCE_DATA_START_ROW})"
        )
    workbook = xlsxwriter.Workbook(path, {"strings_to_formulas": False, "strings_to_urls": False})
    workbook.set_properties(
        {
            "title": f"{unit_name} scoped synthetic evidence extract",
            "company": "Sable Harbor",
            "created": created_at,
        }
    )
    sheet = workbook.add_worksheet("Trial Balance")
    sheet.write(0, 0, f"{unit_name} — scoped synthetic evidence extract")
    if trial_balance:
        headings = list(trial_balance[0])
        sheet.write_row(2, 0, headings)
        for index, row in enumerate(trial_balance, 3):
            sheet.write_row(index, 0, [row[column] for column in headings])
    workbook.close()


def _database(path: Path, lines: list[dict[str, Any]], trial_balance: list[dict[str, Any]]) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE journal_line_evidence (journal_entry_id TEXT, entry_date TEXT, "
            "source_type TEXT, source_id TEXT, entity_code TEXT, journal_line_id TEXT, "
            "account_code TEXT, account_name TEXT, account_class TEXT, segment_code TEXT, "
            "counterparty_code TEXT, debit TEXT, credit TEXT)"
        )
        connection.executemany(
            "INSERT INTO journal_line_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ([row[column] for column in row] for row in lines),
        )
        connection.execute(
            "CREATE TABLE trial_balance (account_code TEXT, account_name TEXT, "
            "account_class TEXT, debit TEXT, credit TEXT, balance TEXT)"
        )
        connection.executemany(
            "INSERT INTO trial_balance VALUES (?,?,?,?,?,?)",
            ([row[column] for column in row] for row in trial_balance),
        )
        connection.commit()
    finally:
        connection.close()


def _build_business_unit_packages(
    session: Session,
    destination: Path = Path("releases/generated/business-units"),
    *,
    generation_run_id: str,
    generated_at: datetime | None = None,
) -> list[Path]:
    context = run_context(session, generation_run_id)
    run = session.get(GenerationRun, context.generation_run_id)
    if run is None or run.completed_at is None:
        raise ValueError("Unit packages require a completed generation run")
    if run.profile != "standard":
        raise ValueError("Business-unit release packages require the standard profile")
    if (
        len(context.included_run_ids) != 2
        or run.shared_synthetic_calibration_run_id != context.included_run_ids[0]
    ):
        raise ValueError(
            "Business-unit packages require one selected standard run and its governed "
            "shared synthetic calibration run"
        )
    require_current_build_identity(run)
    enterprise_validation = validate_financial_integrity(session, generation_run_id)
    registry = _unit_registry()
    controlled_timestamp = generated_at or run.completed_at
    included_runs = [
        item
        for run_id in context.included_run_ids
        if (item := session.get(GenerationRun, run_id)) is not None
    ]
    if len(included_runs) != len(context.included_run_ids):
        raise ValueError("Unit-package context contains an unknown generation run")
    unit_lines = {
        unit["id"]: _unit_lines(
            session,
            context.included_run_ids,
            unit["entity_codes"],
            unit["segment_codes"],
            include_unsegmented=bool(unit["include_unsegmented"]),
        )
        for unit in registry["units"]
    }
    enterprise_lines = _enterprise_line_totals(session, context.included_run_ids)
    packaged_occurrences = [
        row["journal_line_id"] for lines in unit_lines.values() for row in lines
    ]
    packaged_ids = set(packaged_occurrences)
    duplicate_line_count = len(packaged_occurrences) - len(packaged_ids)
    unknown_line_count = len(packaged_ids - enterprise_lines.keys())
    excluded_ids = enterprise_lines.keys() - packaged_ids
    packaged_debit = sum(
        (enterprise_lines[line_id][0] for line_id in sorted(packaged_ids)), Decimal(0)
    )
    packaged_credit = sum(
        (enterprise_lines[line_id][1] for line_id in sorted(packaged_ids)), Decimal(0)
    )
    excluded_debit = sum(
        (enterprise_lines[line_id][0] for line_id in sorted(excluded_ids)), Decimal(0)
    )
    excluded_credit = sum(
        (enterprise_lines[line_id][1] for line_id in sorted(excluded_ids)), Decimal(0)
    )
    enterprise_debit = sum(
        (enterprise_lines[line_id][0] for line_id in sorted(enterprise_lines)), Decimal(0)
    )
    enterprise_credit = sum(
        (enterprise_lines[line_id][1] for line_id in sorted(enterprise_lines)), Decimal(0)
    )
    debit_difference = packaged_debit + excluded_debit - enterprise_debit
    credit_difference = packaged_credit + excluded_credit - enterprise_credit
    currency_tolerance = Decimal("0.000001")
    bridge = {
        "status": (
            "PASS"
            if duplicate_line_count == 0
            and unknown_line_count == 0
            and packaged_ids | excluded_ids == enterprise_lines.keys()
            and abs(debit_difference) <= currency_tolerance
            and abs(credit_difference) <= currency_tolerance
            else "FAIL"
        ),
        "enterprise_line_count": len(enterprise_lines),
        "packaged_unique_line_count": len(packaged_ids),
        "excluded_enterprise_line_count": len(excluded_ids),
        "duplicate_packaged_line_count": duplicate_line_count,
        "unknown_packaged_line_count": unknown_line_count,
        "enterprise_debits": str(enterprise_debit),
        "enterprise_credits": str(enterprise_credit),
        "packaged_debits": str(packaged_debit),
        "packaged_credits": str(packaged_credit),
        "excluded_debits": str(excluded_debit),
        "excluded_credits": str(excluded_credit),
        "debit_difference": str(debit_difference),
        "credit_difference": str(credit_difference),
        "currency_tolerance": str(currency_tolerance),
        "excluded_scope": "corporate, consolidation, elimination, and unassigned activity",
    }
    if bridge["status"] != "PASS":
        raise ValueError(f"Business-unit-to-enterprise bridge failed: {bridge}")
    manifests: list[Path] = []
    for unit in registry["units"]:
        root = destination / unit["id"] / context.generation_run_id
        for folder in (
            "database",
            "csv",
            "financials",
            "operations/domain-registers",
            "controls",
            "workbooks",
        ):
            (root / folder).mkdir(parents=True, exist_ok=True)
        lines = unit_lines[unit["id"]]
        trial_balance = _trial_balance(lines)
        debit = sum((Decimal(row["debit"]) for row in lines), Decimal(0))
        credit = sum((Decimal(row["credit"]) for row in lines), Decimal(0))
        controls = _unit_control_results(
            lines,
            unit["segment_codes"],
            include_unsegmented=bool(unit["include_unsegmented"]),
        )
        controls.append(
            {
                "code": "UNIT_TO_ENTERPRISE_BRIDGE",
                "status": bridge["status"],
                "observed": str(bridge["excluded_enterprise_line_count"]),
                "details": "unit union plus disclosed excluded activity equals enterprise lines",
            }
        )
        unit_status = "PASS" if all(item["status"] == "PASS" for item in controls) else "FAIL"
        if unit_status != "PASS":
            raise ValueError(f"Unit financial controls failed for {unit['id']}: {controls}")
        _write_csv(root / "csv/journal-lines.csv", lines)
        _write_csv(root / "financials/trial-balance.csv", trial_balance)
        _write_csv(
            root / "financials/income-statement.csv",
            _statement_rows(trial_balance, {"REVENUE", "EXPENSE", "OTHER_EXPENSE"}),
        )
        _write_csv(
            root / "financials/balance-sheet.csv",
            _statement_rows(trial_balance, {"ASSET", "LIABILITY", "EQUITY"}),
        )
        _write_csv(root / "financials/cash-flow.csv", _cash_flow_rows(lines))
        _write_csv(root / "financials/changes-in-equity.csv", _equity_change_rows(lines))
        _write_csv(root / "financials/intercompany-bridge.csv", _intercompany_rows(lines))
        sources = [
            {
                "journal_entry_id": row["journal_entry_id"],
                "source_type": row["source_type"],
                "source_id": row["source_id"],
            }
            for row in lines
        ]
        _write_csv(root / "controls/source-lineage.csv", sources)
        _write_csv(root / "operations/domain-registers/source-events.csv", sources)
        registers = _operational_registers(
            session,
            unit["id"],
            context.included_run_ids,
            unit["entity_codes"],
            unit["segment_codes"],
            unit["site_codes"],
        )
        for name, rows in registers.items():
            _write_csv(root / f"operations/{name}.csv", rows)
        reconciliation = {
            "status": unit_status,
            "debits": str(debit),
            "credits": str(credit),
            "difference": str(debit - credit),
            "enterprise_bridge": bridge,
        }
        (root / "controls/reconciliation.json").write_text(
            json.dumps(reconciliation, indent=2) + "\n"
        )
        (root / "controls/validation-results.json").write_text(
            json.dumps(
                {"status": unit_status, "control_count": len(controls), "controls": controls},
                indent=2,
            )
            + "\n"
        )
        (root / "controls/public-safety-report.json").write_text(
            json.dumps({"status": "PENDING"}, indent=2) + "\n"
        )
        _database(root / f"database/{unit['id']}.sqlite", lines, trial_balance)
        _workbook(
            root / f"workbooks/{unit['id']}-audit-workbook.xlsx",
            unit["name"],
            trial_balance,
            controlled_timestamp,
        )
        (root / "README.md").write_text(
            f"# {unit['name']} scoped financial evidence extract\n\n"
            "Deterministic synthetic scenario/calibration evidence prepared retrospectively "
            "under the current canon source lock. This is not a source-system replica, an "
            "audited statement package, observed history, or canon. Excluded enterprise activity "
            "is disclosed in `controls/reconciliation.json`; exact source and epistemic metadata "
            "is in `manifest.json`.\n"
        )
        effective_dates = [row["entry_date"] for row in lines]
        generation_metadata = generation_manifest_metadata(
            run,
            scenario_code=context.scenario_code,
            built_at=controlled_timestamp,
            effective_from=min(effective_dates),
            effective_through=max(effective_dates),
            effective_period_basis="included_posted_journal_entry_dates",
        )
        manifest = {
            "package_version": "0.1.0",
            "schema_version": run.schema_head,
            "unit_id": unit["id"],
            "display_name": unit["name"],
            "source_commit": run.git_commit,
            "generation_run_id": context.generation_run_id,
            "included_run_ids": list(context.included_run_ids),
            "included_runs": included_run_metadata(
                included_runs, selected_run_id=context.generation_run_id
            ),
            "profile": public_profile(run.profile),
            "seed": run.seed,
            "filters": {
                "entities": unit["entity_codes"],
                "segments": unit["segment_codes"],
                "sites": unit["site_codes"],
                "include_unsegmented": unit["include_unsegmented"],
            },
            "row_counts": {
                "journal_line_evidence": len(lines),
                "trial_balance": len(trial_balance),
            },
            "validation": reconciliation,
            "enterprise_financial_validation": {
                "status": "PASS" if enterprise_validation.passed else "FAIL",
                "control_count": len(enterprise_validation.controls),
            },
            "classification": "PUBLIC_SAFE_SYNTHETIC_RELEASE_CANDIDATE",
            "database_artifact_type": "SCOPED_JOURNAL_AND_TRIAL_BALANCE_EVIDENCE_EXTRACT",
            "limitations": (
                "Excludes corporate, consolidation, elimination, and unassigned activity; "
                "excluded population counts and totals are reconciled in "
                "controls/reconciliation.json."
            ),
            "artifact_safety_scan": {"status": "PENDING"},
            "checksum_algorithm": "SHA-256",
            "package_input_digests": {
                "unit_scope_registry_sha256": file_sha256(UNIT_REGISTRY),
            },
            **generation_metadata,
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        scan_failures = scan_generated_artifacts(root)
        if scan_failures:
            raise ValueError("Unit artifact safety scan failed:\n" + "\n".join(scan_failures))
        (root / "controls/public-safety-report.json").write_text(
            json.dumps(
                {"status": "PASS", "failures": 0, "scope": TECHNICAL_SAFETY_SCOPE},
                indent=2,
            )
            + "\n"
        )
        manifest["artifact_safety_scan"] = {
            "status": "PASS",
            "failures": 0,
            "scope": TECHNICAL_SAFETY_SCOPE,
        }
        artifact_inventory = [
            {
                "path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "sha256": _digest(path),
            }
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.name not in {"manifest.json", "SHA256SUMS.txt"}
        ]
        manifest["artifacts"] = artifact_inventory
        manifest["output_hashes"] = {
            artifact["path"]: artifact["sha256"] for artifact in artifact_inventory
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        final_scan_failures = scan_generated_artifacts(root)
        if final_scan_failures:
            raise ValueError(
                "Final unit artifact safety scan failed:\n" + "\n".join(final_scan_failures)
            )
        artifacts = sorted(
            path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"
        )
        (root / "SHA256SUMS.txt").write_text(
            "".join(f"{_digest(path)}  {path.relative_to(root)}\n" for path in artifacts)
        )
        manifests.append(manifest_path)
    aggregate_paths = sorted(
        path
        for path in destination.rglob("*")
        if path.is_file() and path != destination / "SHA256SUMS.txt"
    )
    (destination / "SHA256SUMS.txt").write_text(
        "".join(f"{_digest(path)}  {path.relative_to(destination)}\n" for path in aggregate_paths)
    )
    aggregate_failures = scan_generated_artifacts(destination / "SHA256SUMS.txt")
    if aggregate_failures:
        raise ValueError(
            "Business-unit aggregate checksum safety scan failed:\n" + "\n".join(aggregate_failures)
        )
    return manifests


def package_business_units(
    session: Session,
    destination: Path = Path("releases/generated/business-units"),
    *,
    generation_run_id: str,
    generated_at: datetime | None = None,
) -> list[Path]:
    with staged_package_directory(
        destination,
        package_kind="business-units-v0.1",
        repository_output_root=REPOSITORY_ROOT / "releases/generated",
    ) as (final_destination, staging):
        staged_manifests = _build_business_unit_packages(
            session,
            staging,
            generation_run_id=generation_run_id,
            generated_at=generated_at,
        )
        relative_manifests = [path.relative_to(staging) for path in staged_manifests]
    return [final_destination / path for path in relative_manifests]
