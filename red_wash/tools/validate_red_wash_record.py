from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DIST = ROOT / "dist"


def rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def total(records: list[dict[str, str]], field: str) -> Decimal:
    return sum((Decimal(record[field]) for record in records), Decimal("0"))


def validate(generate: bool = False) -> dict[str, object]:
    if generate:
        subprocess.run([sys.executable, str(ROOT / "tools" / "generate_red_wash_corpus.py")], check=True)

    checks: list[str] = []
    failures: list[str] = []

    def check(condition: bool, label: str) -> None:
        (checks if condition else failures).append(label)

    production = rows("monthly_production_2026.csv")
    inventory = rows("inventory_rollforward_2026.csv")
    contracts = rows("uranium_contracts.csv")
    collars = rows("drill_collars.csv")
    surveys = rows("downhole_surveys.csv")
    assays = rows("assays.csv")
    employees = rows("employee_census_2026.csv")
    ppa = rows("purchase_price_allocation.csv")
    statements = rows("financial_statements_2026.csv")
    diligence = rows("diligence_findings.csv")
    vdr = rows("virtual_data_room_index.csv")

    check(len(production) == 12, "12 monthly production records")
    check(total(production, "ore_tons") == Decimal("175000"), "175,000 ore tons")
    check(total(production, "u3o8_produced_lb") == Decimal("547400"), "547,400 lb produced")
    check(total(production, "u3o8_sold_lb") == Decimal("500000"), "500,000 lb sold")
    check(total(production, "revenue_usd") == Decimal("36475000"), "$36.475M revenue")
    check(Decimal(inventory[0]["opening_finished_u3o8_lb"]) == Decimal("125000"), "125,000 lb opening inventory")
    check(Decimal(inventory[-1]["ending_finished_u3o8_lb"]) == Decimal("172400"), "172,400 lb ending inventory")
    check(total(contracts, "committed_lb") == Decimal("500000"), "contract book equals sales")
    weighted = total(contracts, "committed_lb")
    weighted_price = sum(Decimal(r["committed_lb"]) * Decimal(r["modeled_realized_usd_lb"]) for r in contracts) / weighted
    check(weighted_price == Decimal("72.95"), "$72.95 weighted realized price")
    check(len(collars) == 240, "240 drill collars")
    check(len(surveys) == 720, "720 downhole surveys")
    check(len(assays) == 2400, "2,400 assay intervals")
    check(len(employees) == 140, "140 FTE establishment")
    check(sum(1 for r in employees if r["function"] == "Pale Sun Business Layer") == 12, "12 Pale Sun FTE")
    check(len(diligence) >= 16, "integrated diligence register")
    check(len(vdr) == 176, "176-item VDR index")

    ppa_result = sum(Decimal(r["amount_usd"]) for r in ppa if r["line"] != "Net identifiable assets")
    check(ppa_result == Decimal("0"), "purchase allocation and consideration reconcile")

    statement = {(r["statement"], r["line"]): Decimal(r["amount_usd"]) for r in statements}
    check(statement[("Income Statement", "Net income")] == Decimal("903307"), "net income controlled value")
    check(statement[("Cash Flow", "Free cash flow")] == Decimal("-7477787"), "free cash flow controlled value")

    db_path = DIST / "red_wash_transaction_operating_record_v1.sqlite3"
    check(db_path.is_file(), "SQLite database exists")
    if db_path.is_file():
        db = sqlite3.connect(db_path)
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        view = db.execute("SELECT ore_tons, produced_lb, sold_lb, revenue_usd FROM v_2026_production_reconciliation").fetchone()
        db.close()
        check(integrity == "ok", "SQLite integrity_check")
        check(tuple(round(float(v)) for v in view) == (175000, 547400, 500000, 36475000), "SQLite production view reconciles")

    result = {"status":"PASS" if not failures else "FAIL","checks_passed":len(checks),"failures":failures}
    if failures:
        raise SystemExit(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()
    print(json.dumps(validate(args.generate), indent=2))
