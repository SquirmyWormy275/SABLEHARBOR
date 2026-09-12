"""Validate finance evidence extracts, population identity and accounting equations."""

import collections
import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/finance/evidence"
spec = importlib.util.spec_from_file_location(
    "finance_extract", Path(__file__).with_name("build.py")
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def validate(base=BASE):
    totals = {}
    for family in m.FAMILIES:
        folder = base / family
        reg = json.loads((folder / "evidence-register.json").read_text())
        db = sqlite3.connect(folder / "evidence.sqlite3")
        db.row_factory = sqlite3.Row
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert (
            m.digest((folder / "evidence.sqlite3").read_bytes())
            == reg["extracted_database"]["sha256"]
        )
        data = {}
        for s in reg["sources"]:
            p = folder / "source" / Path(s["path"]).name
            assert m.digest(p.read_bytes()) == s["sha256"]
            rs = m.rows(p.read_bytes())
            assert len(rs) == s["row_count"]
            data[p.stem] = rs
            assert [dict(r) for r in db.execute('SELECT * FROM "' + p.stem + '"')] == rs
            assert s.get(
                "selection_role"
            ) == "HISTORICAL_REFERENCE_INPUT_WHOLE_NOT_CURRENT_REVENUE" or all(
                m.selected(r, int(reg["scope"]["period_start"][:4])) for r in rs
            )
        expected_tables = set(m.FAMILIES[family]["tables"]) | set(m.FAMILIES[family]["extras"])
        assert set(data) == expected_tables, (
            f"{family}: source register omits or adds population tables"
        )
        assert {
            r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        } == expected_tables, f"{family}: database table coverage differs"
        db.close()
        actual = m.checks(data, family)
        expected = json.loads((folder / "RECONCILIATION.json").read_text())
        assert actual == expected["checks"]
        assert all(r["status"] == "PASS" for r in actual)
        totals[family] = sum(len(rs) for rs in data.values())
    customer = {p.stem: m.rows(p.read_bytes()) for p in (base / "customer/source").glob("*.csv")}
    journals = m.rows((base / "close/source/journal.csv").read_bytes())
    invoice_ids = {r["invoice_id"] for r in customer["invoices"]}
    event_ids = {r["event_id"] for r in customer["events"]}
    posted = {r["source_id"] for r in journals}
    contract_ids = {r["contract_id"] for r in customer["contracts"]}
    assert all(r["contract_id"] in contract_ids for r in customer["contract_versions"]), (
        "contract_versions.contract_id absent from contracts"
    )
    for table in ("credit_history", "credit_notes", "receivable_aging", "credit_allowance"):
        assert all(r["invoice_id"] in invoice_ids for r in customer[table]), table
    assert all(
        r["source_id"] in event_ids and r["source_id"] in posted for r in customer["credit_history"]
    ), "credit_history.source_id absent from events.event_id or close journal.source_id"
    assert all(r["event_id"] in posted for r in customer["events"] if r.get("invoice_id")), (
        "Invoice events.event_id absent from close journal.source_id"
    )
    issued = {row["source_id"]: row for row in customer["events"] if row["kind"] == "INVOICE"}
    assert len(issued) == sum(row["kind"] == "INVOICE" for row in customer["events"]), (
        "Duplicate INVOICE event source_id"
    )
    assert set(issued) == invoice_ids, "Core invoice issuance population differs from invoices"
    for invoice in customer["invoices"]:
        event = issued[invoice["invoice_id"]]
        assert event["performance_source"] == invoice["source_id"], (
            "Invoice performance source mismatch: " + invoice["invoice_id"]
        )
        assert event["unit"] == invoice["unit"] and m.num(event, "amount_usd") == m.num(
            invoice, "amount_usd"
        ), "Invoice event unit/amount mismatch: " + invoice["invoice_id"]
        assert event["event_id"] in posted, (
            "INVOICE event missing from Core journal: " + event["event_id"]
        )
    lineage = m.rows(
        (base / "treasury/source/industrial_document_journal_lineage.csv").read_bytes()
    )
    identity = {(r["journal_id"], r["event_id"], r["source_id"]) for r in lineage}
    revenue = collections.defaultdict(m.D)
    for row in lineage:
        revenue[row["journal_id"], row["event_id"], row["source_id"], row["account"]] += m.num(
            row, "signed_usd"
        )
    industrial_sales = collections.defaultdict(m.D)
    for row in customer["industrial_sales_invoices"]:
        key = (row["journal_id"], row["event_id"], row["source_id"])
        assert key in identity, "Industrial invoice missing journal lineage: " + row["invoice_id"]
        assert -revenue[(*key, row["revenue_account"])] == m.num(row, "amount_usd"), (
            "Industrial invoice recognition amount mismatch: " + row["invoice_id"]
        )
        industrial_sales[row["source_id"]] += m.num(row, "amount_usd")
    industrial_contract_ids = {r["contract_id"] for r in customer["industrial_contract_register"]}
    industrial_customer_ids = {r["customer_id"] for r in customer["industrial_customer_register"]}
    for row in customer["industrial_contract_revenue"]:
        assert (
            row["contract_id"] in industrial_contract_ids
            and row["customer_id"] in industrial_customer_ids
        ), "Industrial contract/customer reference missing: " + row["source_id"]
        assert industrial_sales[row["source_id"]] == m.num(row, "revenue_usd"), (
            "Industrial contract revenue/invoice mismatch: " + row["source_id"]
        )
    for family, settings in m.FAMILIES.items():
        register = json.loads((base / family / "evidence-register.json").read_text())
        source_rows = m.rows(
            (base / family / "source" / (settings["schedule"] + ".csv")).read_bytes()
        )
        expected = {
            "title": settings["title"],
            "columns": settings["columns"],
            "rows": [{c: r.get(c, "") for c in settings["columns"]} for r in source_rows],
            "source_table": settings["schedule"],
            "scope": register["scope"],
            "limitations": settings["limits"],
        }
        assert json.loads((base / family / "SCHEDULE.json").read_text()) == expected, (
            "Stale schedule source/limitations: " + family
        )
    assignments = m.rows(
        (base / "supporting-schedules/source/workforce_assignments.csv").read_bytes()
    )
    allocation = collections.defaultdict(m.D)
    costs = collections.defaultdict(m.D)
    for row in assignments:
        allocation[row["person_id"], row["period"]] += m.num(row, "assignment_fte")
        costs[row["unit"], row["period"]] += m.num(row, "loaded_cost_usd")
    assert all(value == 1 for value in allocation.values()), (
        "Workforce person/month assignment fractions do not sum to one"
    )
    payroll_requests = {
        row["event_id"] for row in customer["events"] if row["kind"] == "PAYROLL_REQUEST"
    }
    posted_payroll = collections.defaultdict(m.D)
    for row in journals:
        if row["account"] == "BIZ_PAYROLL" and row["source_id"] in payroll_requests:
            posted_payroll[row["unit"], row["period"]] += m.num(row, "signed_usd")
    assert set(costs) == set(posted_payroll), (
        "Workforce and payroll journal unit/period populations differ"
    )
    assert all(abs(value - posted_payroll[key]) <= m.D(".02") for key, value in costs.items()), (
        "Assigned employer costs differ from payroll journal"
    )
    bridge_spec = importlib.util.spec_from_file_location(
        "validate_transaction_bridge", base / "tax-transaction/validate_bridge.py"
    )
    bridge_module = importlib.util.module_from_spec(bridge_spec)
    bridge_spec.loader.exec_module(bridge_module)
    bridge_module.validate(base / "tax-transaction")
    print("PASS exact CSV/database populations, hashes, scope and accounting:", totals)
    return totals


if __name__ == "__main__":
    validate()
