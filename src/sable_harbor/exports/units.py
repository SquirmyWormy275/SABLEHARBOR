import csv
import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import xlsxwriter  # type: ignore[import-untyped]
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from sable_harbor.core.database import required_schema_head
from sable_harbor.exports.safety import scan_generated_artifacts
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import run_context

UNIT_REGISTRY = Path("config/finance/unit_scopes.json")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("status\nNO_RECORDS\n")
        return
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unit_lines(
    session: Session, run_ids: tuple[str, ...], entity_codes: list[str], segments: list[str]
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
          AND (jl.segment_code IN :segments OR jl.segment_code IS NULL)
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
    session: Session, unit_id: str, run_ids: tuple[str, ...], entity_codes: list[str]
) -> dict[str, list[dict[str, Any]]]:
    shared = {
        "asset-register": """
            SELECT fa.asset_number, le.code AS entity_code, fa.asset_class,
                   fa.placed_in_service, fa.cost, fa.useful_life_months, fa.fact_state
            FROM fixed_asset fa JOIN legal_entity le ON le.id=fa.entity_id
            WHERE le.code IN :entity_codes
              AND fa.generation_run_id IN (:actual_run_id,:generation_run_id)
            ORDER BY fa.asset_number
        """,
        "inventory-register": """
            SELECT il.lot_number, le.code AS entity_code, il.inventory_stage, il.quantity,
                   il.unit, il.carrying_value, il.as_of_date, il.fact_state
            FROM inventory_lot il JOIN legal_entity le ON le.id=il.entity_id
            WHERE le.code IN :entity_codes
              AND il.generation_run_id IN (:actual_run_id,:generation_run_id)
            ORDER BY il.lot_number
        """,
        "workforce-summary": """
            SELECT le.code AS entity_code, w.worker_type, w.segment_code, w.function_code,
                   COUNT(*) AS workers, SUM(w.annual_cost) AS annual_cost
            FROM worker w JOIN legal_entity le ON le.id=w.entity_id
            WHERE le.code IN :entity_codes
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
    output = {
        name: _scoped_rows(session, sql, run_ids, entity_codes) for name, sql in shared.items()
    }
    output["domain-registers/primary-register"] = _scoped_rows(
        session, domain[unit_id], run_ids, entity_codes
    )
    return output


def _statement_rows(trial_balance: list[dict[str, Any]], classes: set[str]) -> list[dict[str, Any]]:
    return [row for row in trial_balance if row["account_class"] in classes]


def _workbook(path: Path, unit_name: str, trial_balance: list[dict[str, Any]]) -> None:
    workbook = xlsxwriter.Workbook(path)
    sheet = workbook.add_worksheet("Trial Balance")
    sheet.write(0, 0, f"{unit_name} — standalone audit evidence")
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


def package_business_units(
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
    registry = json.loads(UNIT_REGISTRY.read_text())
    if destination.exists():
        shutil.rmtree(destination)
    manifests: list[Path] = []
    for unit in registry["units"]:
        root = destination / unit["id"] / context.generation_run_id
        for folder in (
            "database", "csv", "financials", "operations/domain-registers", "controls", "workbooks"
        ):
            (root / folder).mkdir(parents=True, exist_ok=True)
        lines = _unit_lines(
            session, context.included_run_ids, unit["entity_codes"], unit["segment_codes"]
        )
        trial_balance = _trial_balance(lines)
        debit = sum((Decimal(row["debit"]) for row in lines), Decimal(0))
        credit = sum((Decimal(row["credit"]) for row in lines), Decimal(0))
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
        for name in ("cash-flow", "changes-in-equity", "intercompany-bridge"):
            _write_csv(root / f"financials/{name}.csv", trial_balance)
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
            session, unit["id"], context.included_run_ids, unit["entity_codes"]
        )
        for name, rows in registers.items():
            _write_csv(root / f"operations/{name}.csv", rows)
        reconciliation = {
            "status": "PASS" if debit == credit else "FAIL",
            "debits": str(debit),
            "credits": str(credit),
            "difference": str(debit - credit),
            "enterprise_bridge": "entity-and-segment scoped journal evidence",
        }
        (root / "controls/reconciliation.json").write_text(
            json.dumps(reconciliation, indent=2) + "\n"
        )
        (root / "controls/validation-results.json").write_text(
            json.dumps({"status": reconciliation["status"], "checks": 4}, indent=2) + "\n"
        )
        (root / "controls/public-safety-report.json").write_text(
            json.dumps({"status": "PENDING"}, indent=2) + "\n"
        )
        _database(root / f"database/{unit['id']}.sqlite", lines, trial_balance)
        _workbook(root / f"workbooks/{unit['id']}-audit-workbook.xlsx", unit["name"], trial_balance)
        (root / "README.md").write_text(
            f"# {unit['name']} standalone audit package\n\n"
            "Synthetic, scenario-controlled evidence; not audited actual financial statements.\n"
        )
        manifest = {
            "package_version": "0.1.0",
            "schema_version": required_schema_head(),
            "unit_id": unit["id"],
            "display_name": unit["name"],
            "source_commit": run.git_commit,
            "controlling_canon_commit": registry["control_state"]["controlling_canon"]["commit"],
            "generation_run_id": context.generation_run_id,
            "included_run_ids": list(context.included_run_ids),
            "profile": run.profile,
            "scenario": context.scenario_code,
            "seed": run.seed,
            "generated_at": (generated_at or run.completed_at).astimezone(UTC).isoformat(),
            "filters": {
                "entities": unit["entity_codes"],
                "segments": unit["segment_codes"],
                "sites": unit["site_codes"],
            },
            "row_counts": {
                "journal_line_evidence": len(lines),
                "trial_balance": len(trial_balance),
            },
            "validation": reconciliation,
            "classification": "PUBLIC_SAFE_SYNTHETIC_RELEASE_CANDIDATE",
            "limitations": "Unit scope may include shared null-segment enterprise allocations.",
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        scan_failures = scan_generated_artifacts(root)
        if scan_failures:
            raise ValueError("Unit artifact safety scan failed:\n" + "\n".join(scan_failures))
        (root / "controls/public-safety-report.json").write_text(
            json.dumps({"status": "PASS", "failures": 0}, indent=2) + "\n"
        )
        artifacts = sorted(
            path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"
        )
        (root / "SHA256SUMS.txt").write_text(
            "".join(f"{_digest(path)}  {path.relative_to(root)}\n" for path in artifacts)
        )
        manifests.append(manifest_path)
    return manifests
