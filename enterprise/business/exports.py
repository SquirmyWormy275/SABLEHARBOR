"""Portable evidence exports using the repository's existing finance export stack."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import xlsxwriter

from sable_harbor.exports.safety import scan_generated_artifacts

UNITS = (
    "foundry-field",
    "atlas-meridian",
    "advisory",
    "willow",
    "project-cradle",
    "pale-sun",
    "american-resource-utility",
)
CORE_TABLES = (
    "events",
    "contracts",
    "engagements",
    "invoices",
    "payables",
    "recovery_lots",
    "commercial_metrics",
    "capacity",
    "asset_rollforward",
    "inventory_rollforward",
    "receivable_aging",
    "subledger_rollforward",
    "value_certifications",
    "matter_rollforward",
    "workforce_assignments",
)
INDUSTRIAL_TABLES = (
    "vendors",
    "purchase_orders",
    "receipts",
    "supplier_invoices",
    "work_orders",
    "sales_invoices",
    "bank_reconciliations",
    "document_journal_lineage",
    "ledger_events",
    "payroll_batches",
    "payroll_role_details",
    "service_manifests",
    "procurement_monthly_costs",
    "bank_transactions",
)


def encoded(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    if value is None:
        return ""
    return str(value)


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(dict.fromkeys(k for row in rows for k in row))
    if not columns:
        columns = ["scope_state"]
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows({k: encoded(v) for k, v in row.items()} for row in rows)
    return columns


def database(path, tables):
    path = Path(path)
    if path.exists():
        path.unlink()
    schema = {}
    with sqlite3.connect(path) as db:
        for name, rows in tables.items():
            columns = list(dict.fromkeys(k for row in rows for k in row)) or ["scope_state"]
            if not all(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", key) for key in [name, *columns]):
                raise ValueError("Unsafe export schema identifier")
            definition = ",".join(f'"{c}" TEXT NOT NULL' for c in columns)
            db.execute(f'CREATE TABLE "{name}" ({definition})')
            db.executemany(
                f'INSERT INTO "{name}" VALUES ({",".join("?" for _ in columns)})',
                [[encoded(row.get(c)) for c in columns] for row in rows],
            )
            schema[name] = {"columns": columns, "rows": len(rows)}
        if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ValueError("SQLite evidence export is corrupt")
    return schema


def workbook(path, tables, unit, run_id):
    """Auditable evidence workbook; formulas reconcile exported numeric populations.

    Extends the production XlsxWriter convention of sable_harbor.exports.units.
    No macros, workbook links, formula-like input interpretation or live data sources.
    """
    book = xlsxwriter.Workbook(path, {"strings_to_formulas": False, "strings_to_urls": False})
    book.set_properties(
        {
            "title": f"{unit} business audit evidence",
            "company": "Sable Harbor",
            "created": datetime(2026, 9, 9),
            "comments": "Public synthetic conditional planning evidence",
        }
    )
    heading = book.add_format(
        {"bold": True, "font_color": "#FFFFFF", "bg_color": "#233845", "text_wrap": True}
    )
    title = book.add_format({"bold": True, "font_size": 18, "font_color": "#233845"})
    numeric = book.add_format({"num_format": "#,##0.0000;[Red](#,##0.0000);–"})
    wrap = book.add_format({"text_wrap": True, "valign": "top"})
    cover = book.add_worksheet("Read first")
    cover.set_landscape()
    cover.fit_to_pages(1, 1)
    cover.print_area(0, 0, 13, 5)
    cover.set_column(0, 0, 26)
    cover.set_column(1, 5, 22)
    cover.merge_range("A1:F2", f"{unit} — audit evidence", title)
    notes = [
        ("Run identity", run_id),
        ("Period", "2026 retained reconstruction; 2027–2031 conditional business forecast"),
        (
            "Book meaning",
            "Operating-unit reporting view; legal entities and reporting clearing are explicit.",
        ),
        (
            "Financial source",
            "Annual, monthly, trial balance and journal tables reconcile to the unit SQLite database.",
        ),
        (
            "Operational source",
            "Business source events drive Core economics. Industrial evidence retains its disclosed reconstruction roles.",
        ),
        (
            "Cash boundary",
            "Payment records are scheduled requests. Enterprise Treasury separately reports finite funding and unpaid obligations.",
        ),
        (
            "Historical boundary",
            "2026 legacy Core is preserved calibration, not recast as current Advisory/Cradle doctrine.",
        ),
        (
            "Authority",
            "Scenarios do not approve operations, financing, list prices, a tax election, carry or legal form.",
        ),
        (
            "Use",
            "Filter scenario and period together. Numeric source tables are evidence; formulas are terminal review checks.",
        ),
    ]
    for i, (label, value) in enumerate(notes, 4):
        cover.write(i, 0, label, heading)
        cover.merge_range(i, 1, i, 5, value, wrap)
        cover.set_row(i, 34)
    positions = {}
    ordered = [
        "annual_statements",
        "monthly_statements",
        "trial_balance",
        "journal",
        *[
            key
            for key in tables
            if key not in {"annual_statements", "monthly_statements", "trial_balance", "journal"}
        ],
    ]
    aliases = {
        "annual_statements": "Annual",
        "monthly_statements": "Monthly",
        "trial_balance": "Trial balance",
        "journal": "Journals",
        "subledger_rollforward": "Working capital",
        "value_certifications": "Value certification",
        "workforce_assignments": "Staff assignments",
        "enterprise_funding": "Treasury boundary",
    }
    used = set()
    for name in ordered:
        rows = tables[name]
        sheet_name = aliases.get(name, name.replace("_", " ")[:31])
        if sheet_name in used:
            raise ValueError("Workbook tab identity collision")
        used.add(sheet_name)
        sheet = book.add_worksheet(sheet_name)
        columns = list(dict.fromkeys(k for row in rows for k in row)) or ["scope_state"]
        positions[name] = (sheet_name, columns, len(rows))
        sheet.freeze_panes(1, 2)
        sheet.set_row(0, 30)
        sheet.set_column(0, len(columns) - 1, 19)
        for col, key in enumerate(columns):
            if key.endswith("_id") or key in {"source_path", "source_revision", "period"}:
                sheet.set_column(col, col, 32)
            elif key in {"description", "reason", "scope", "fact_state", "posting_state"}:
                sheet.set_column(col, col, 48)

        sheet.write_row(0, 0, columns, heading)
        for row_no, row in enumerate(rows, 1):
            for col, key in enumerate(columns):
                value = row.get(key)
                if key.endswith(("_usd", "_hours", "_kg")) or key in {
                    "year",
                    "month",
                    "month_index",
                    "active_customers",
                }:
                    try:
                        sheet.write_number(row_no, col, float(Decimal(str(value))), numeric)
                        continue
                    except (ValueError, TypeError, ArithmeticError):
                        pass
                sheet.write_string(row_no, col, encoded(value)[:32767])
        if rows:
            sheet.autofilter(0, 0, len(rows), len(columns) - 1)
        sheet.set_landscape()
        sheet.fit_to_pages(1, 0)
        sheet.repeat_rows(0)
        sheet.set_footer("&LPublic synthetic planning evidence&RPage &P of &N")
    check = book.add_worksheet("Checks")
    check.set_column(0, 0, 42)
    check.set_column(1, 3, 24)
    check.write_row(
        0, 0, ["Reconciliation", "Workbook formula", "Database/source total", "Difference"], heading
    )
    from xlsxwriter.utility import xl_col_to_name

    index = 1
    for table, value_column in [
        ("annual_statements", "net_income_usd"),
        ("monthly_statements", "ending_cash_usd"),
        ("trial_balance", "signed_usd"),
    ]:
        sheet_name, columns, count = positions[table]
        if not count:
            continue
        letter = xl_col_to_name(columns.index(value_column))
        total = sum(Decimal(str(r[value_column])) for r in tables[table])
        check.write(index, 0, f"{table}: {value_column}")
        check.write_formula(
            index, 1, f"=SUM('{sheet_name}'!{letter}2:{letter}{count + 1})", numeric, float(total)
        )
        check.write_number(index, 2, float(total), numeric)
        check.write_formula(index, 3, f"=B{index + 1}-C{index + 1}", numeric, 0)
        index += 1
    book.close()


def industrial_unit(row):
    scope = str(row.get("entity", ""))
    segment = str(row.get("segment", ""))
    if scope in {"RWH", "PS", "RWH_PS"} or segment in {"RWH", "PS", "MINE"}:
        return "pale-sun"
    if scope in {"ARU", "BST", "ARU_GROUP"} or segment in {
        "ARU",
        "BST",
        "TRUCKING",
        "TERMINAL",
        "TERMINALS",
        "WAREHOUSE",
    }:
        return "american-resource-utility"
    return None


# Explicit release population, never a glob over an execution database or private material.
PHYSICAL_REGISTERS = {
    "american-resource-utility": {
        "industrial/generated/finance": (
            "customer_register",
            "contract_register",
            "employee_census_payroll",
            "parts_fuel_materials_inventory",
            "aru_2026_fixed_assets",
            "aru_2026_debt_leases",
        ),
        "industrial/generated/operations/registers": (
            "locomotives",
            "railcars",
            "road_equipment",
            "handling_equipment",
            "facilities",
            "track_segments",
            "structures",
            "labor_agreements",
            "contract_facility_assignments",
        ),
    },
    "pale-sun": {
        "red_wash/generated": (
            "employee_census_2026",
            "inventory_rollforward_2026",
            "uranium_contracts",
            "monthly_production_2026",
            "custody_authority_matrix",
            "aru_red_wash_integration_gates",
            "maintenance_backlog",
            "permit_register",
        ),
        "industrial/generated/finance": ("red_wash_closure_cashflow_calibration",),
    },
}


def physical_registers(unit):
    root = Path(__file__).resolve().parents[2]
    answer = {}
    inventory = []
    for directory, names in PHYSICAL_REGISTERS[unit].items():
        for name in names:
            path = root / directory / (name + ".csv")
            with path.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            table = "reference_" + name
            answer[table] = rows
            inventory.append(
                {
                    "table_name": table,
                    "source_path": str(path.relative_to(root)),
                    "source_sha256": file_hash(path),
                    "row_count": len(rows),
                    "scope": "PRESERVED_PHYSICAL_OR_2025_2026_REFERENCE_NOT_ADDITIONAL_FORECAST_POSTING",
                }
            )
    answer["physical_reference_inventory"] = inventory
    return answer


def validate_population(tables, unit, identity):
    schema = json.loads((Path(__file__).parent / "export_schema.json").read_text())[unit]
    if set(tables) != set(schema):
        raise ValueError("Unexpected or missing unit table population")
    legal = {"pale-sun": {"PS", "RWH"}, "american-resource-utility": {"ARU", "BST"}}.get(
        unit, {"SHI"}
    )
    segments = {
        "foundry-field": {"CORE", "FOUNDRY_FIELD", "DELIVERY"},
        "atlas-meridian": {"ATLAS"},
        "advisory": {"ADVISORY"},
        "willow": {"WILLOW"},
        "project-cradle": {"CRADLE"},
        "pale-sun": {"CORPORATE"},
        "american-resource-utility": {"CORPORATE"},
    }[unit]
    assets = json.loads((Path(__file__).parent / "source/assets.json").read_text())
    sites = {r["site"] for r in assets if r["unit"] == unit or r.get("transfer_unit") == unit}
    if unit == "project-cradle":
        recovery = json.loads((Path(__file__).parent / "source/recovery.json").read_text())
        sites.update(r["site"] for r in recovery.values() if isinstance(r, dict) and "site" in r)
    if not set(identity["scenarios"]) <= {"base", "downside", "expansion"}:
        raise ValueError("Unexpected scenario identity")
    for name, rows in tables.items():
        allowed = set(schema[name]["columns"])
        for row in rows:
            if not set(row) <= allowed:
                raise ValueError(f"Unexpected export column: {unit}/{name}")
            if name.startswith("reference_") or name == "physical_reference_inventory":
                continue
            if "scenario" in row and row["scenario"] not in identity["scenarios"]:
                raise ValueError("Unexpected export scenario")
            if "fact_state" in row and row["fact_state"] not in {
                "CONDITIONAL_FORECAST",
                "SYNTHETIC_SUCCESSOR_RECONSTRUCTION",
                "PROVISIONAL_ASSUMPTION",
                "LOCKED_DERIVED_IMPLEMENTATION",
                "SYNTHETIC_INSTANCE",
                "CONDITIONAL_OCCUPANCY_NOT_2026_ACTUAL",
                "FORECAST",
            }:
                raise ValueError(f"Unexpected fact state: {unit}/{name}/{row['fact_state']}")
            if (
                name in {"annual_statements", "monthly_statements", "trial_balance", "journal"}
                and row["unit"] != unit
            ):
                raise ValueError("Financial row outside unit scope")
            if name in {"journal", "intercompany_bridge"}:
                if row.get("entity") is not None and row["entity"] not in legal:
                    raise ValueError("Unexpected legal entity")
                if row.get("segment") is not None and row["segment"] not in segments:
                    raise ValueError("Unexpected reporting segment")
            for key in ("site", "site_id", "original_site"):
                if row.get(key) and row[key] not in sites:
                    raise ValueError("Unexpected business site")
            if name == "model_identity" and (
                row["unit"] != unit
                or row["run_id"] != identity["run_id"]
                or row["source_revision"] != identity["source_revision"]
            ):
                raise ValueError("Unexpected model identity")


def unit_packages(output, model, result, industrial, identity):
    all_tables = {}
    for unit in UNITS:
        path = Path(output) / unit
        path.mkdir(parents=True, exist_ok=True)
        tables = {
            "annual_statements": [r for r in result["unit_annual_rows"] if r["unit"] == unit],
            "monthly_statements": [r for r in result["unit_monthly_rows"] if r["unit"] == unit],
            "trial_balance": [r for r in result["unit_rows"] if r["unit"] == unit],
            "journal": [r for r in result["journal_rows"] if r["unit"] == unit],
        }
        for name in CORE_TABLES:
            rows = [r for r in model.tables.get(name, []) if r.get("unit") == unit]
            if rows:
                tables[name] = rows
        tables["workforce_positions"] = [r for r in model.roster if unit in r["assignments"]]
        if unit in {"pale-sun", "american-resource-utility"}:
            for name in INDUSTRIAL_TABLES:
                rows = [r for r in industrial.get(name, []) if industrial_unit(r) == unit]
                if rows:
                    # Industrial 'unit' is a physical measurement unit, never a business ID.
                    tables["industrial_" + name] = rows
        if unit in {"pale-sun", "american-resource-utility"}:
            vendor_ids = {
                r.get("vendor_id") for rows in tables.values() for r in rows if r.get("vendor_id")
            }
            tables["industrial_vendors"] = [
                r for r in industrial.get("vendors", []) if r["vendor_id"] in vendor_ids
            ]
            tables.update(physical_registers(unit))
        tables["enterprise_funding"] = [
            r
            for r in result["funding_rows"]
            if r.get("scope") == "CORE_OPERATIONS" or r.get("entity") in {"SHI", "CONSOLIDATED"}
        ]
        equity = []
        previous = {}
        for row in sorted(
            tables["annual_statements"], key=lambda r: (r["scenario"], int(r["year"]))
        ):
            scenario = row["scenario"]
            opening = previous.get(scenario, Decimal(0))
            closing = Decimal(row["equity_usd"])
            income = Decimal(row["net_income_usd"])
            equity.append(
                {
                    "scenario": scenario,
                    "year": row["year"],
                    "unit": unit,
                    "opening_equity_usd": str(opening),
                    "net_income_usd": str(income),
                    "capital_reporting_and_other_movement_usd": str(closing - opening - income),
                    "closing_equity_usd": str(closing),
                    "classification": "2026 includes opening reconstruction; reporting allocations are not external financing",
                }
            )
            previous[scenario] = closing
        tables["equity_bridge"] = equity
        tables["intercompany_bridge"] = [
            r
            for r in tables["journal"]
            if r["account"].startswith(
                ("INV_", "IC_", "SHARED_", "UNIT_CLEARING", "BIZ_UNIT_CLEARING")
            )
        ]
        tables["scope_dispositions"] = [
            {
                "population": "2026 Core operating records",
                "state": "PRESERVED_LEGACY_CALIBRATION",
                "reason": "Business-driven successor begins 2027; no retrospective rewrite of release fixtures.",
            },
            {
                "population": "Detailed physical registers",
                "state": "REFER_TO_INDUSTRIAL_SOURCE_OR_NOT_APPLICABLE",
                "reason": "Software/matters have no locomotive or mineral-stock semantics. Industrial registers retain their existing source and granularity.",
            },
            {
                "population": "Observed individual waybills / daily freight movements / tool-by-tool counts",
                "state": "NOT_MODELED_AT_THIS_GRANULARITY",
                "reason": "Industrial monthly service manifests, source route/customer allocations and reference equipment/inventory registers are included; no fabricated observations.",
            },
            {
                "population": "Advisory carry",
                "state": "NOT_AWARDED_NOT_ACCRUED",
                "reason": "Eligibility is testable; economic instrument mechanics remain OPEN.",
            },
            {
                "population": "Actual statutory bank statement",
                "state": "NOT_MODELED",
                "reason": "This is conditional planning. Unit cash contains disclosed reporting/treasury allocation.",
            },
        ]
        tables["model_identity"] = [
            {
                "run_id": identity["run_id"],
                "source_revision": identity["source_revision"],
                "business_input_sha256": model.input_hash,
                "unit": unit,
                "classification": "PUBLIC_SYNTHETIC_CONDITIONAL_FORECAST",
            }
        ]
        validate_population(tables, unit, identity)
        all_tables[unit] = tables
    # Validate every unit before producing any database or workbook.
    for unit, tables in all_tables.items():
        path = Path(output) / unit
        for name, rows in tables.items():
            write_csv(path / (name + ".csv"), rows)
        schema = database(path / "evidence.sqlite3", tables)
        workbook(path / "audit.xlsx", tables, unit, identity["run_id"])
        (path / "schema.json").write_text(json.dumps(schema, indent=2) + "\n")
        (path / "README.md").write_text(f"""# {unit} — standalone evidence package

Public synthetic planning records, not real company accounts. Source revision: {identity["source_revision"]}.
Run: {identity["run_id"]}. Scenarios: base/downside/expansion. Business inputs: {model.input_hash}.

Annual/monthly statements, trial balances and journal rows are exact enterprise-unit extracts. UNIT_CLEARING
and BIZ_UNIT_CLEARING are reporting/transfer reconciliations, not external financing. Corporate and
elimination residuals remain in the parent package. Payroll positions are counted once globally; borrowed
assignments carry fractions rather than additional employed people. Physical measurement units in
industrial service records are not reporting-line identifiers.

Invoices and payments are conditional forecasts. Treasury may defer modeled operating cash requests;
the enterprise funding and operating/capital/debt unpaid-obligation schedules control that limitation. A subledger marked
requested/assumed settled is not proof of a real bank transaction. New Core records start in 2027;
2026 retained calibration must not override current business doctrine.

The workbook and SQLite contain the same allowed populations. The Checks tab is terminal review;
financial calculations do not depend on it. Schema/row counts are explicit. No raw execution database,
macros, external workbook links or private evaluator material is distributed.
""")
    failures = scan_generated_artifacts(Path(output))
    if failures:
        raise ValueError("Generated-artifact safety failures: " + json.dumps(failures[:10]))
    (Path(output) / "public_safety.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "failures": failures,
                "scope": "All unit CSV/SQLite/workbooks; existing repository artifact scanner",
            },
            indent=2,
        )
        + "\n"
    )
    for unit, tables in all_tables.items():
        path = Path(output) / unit
        (path / "public_safety.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "failures": [],
                    "scope": "Unit CSV/SQLite/workbook scanned by existing repository artifact scanner",
                },
                indent=2,
            )
            + "\n"
        )
        artifacts = {p.name: file_hash(p) for p in sorted(path.iterdir()) if p.is_file()}
        manifest = {
            "version": "1.0.0",
            "classification": "PUBLIC_SYNTHETIC_CONDITIONAL_FORECAST",
            "unit": unit,
            "identity": identity,
            "artifacts": artifacts,
            "filters": {
                "unit": unit,
                "scenarios": identity["scenarios"],
                "periods": identity["periods"],
                "schema": "schema.json",
            },
            "financial_boundary": "Exact unit slice; shared Treasury and copied physical references labeled separately",
        }
        (path / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        hashes = {**artifacts, "manifest.json": file_hash(path / "manifest.json")}
        (path / "SHA256SUMS.txt").write_text(
            "".join(f"{h}  {name}\n" for name, h in sorted(hashes.items()))
        )
    return all_tables


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
