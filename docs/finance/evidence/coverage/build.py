"""Extract complete, declared finance populations from the immutable operations release."""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import sqlite3
import zipfile
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/finance/evidence"
ARCHIVE_SHA = "b8e81572d829fec7209d1d18eb15bac21e52b37714211aee005b5f1a68ab5817"
REVISION = "57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def rows(data):
    return list(csv.DictReader(io.StringIO(data.decode())))


def num(row, key):
    return D(row.get(key, "") or "0")


def selected(row, year):
    if row.get("scenario", "base") != "base":
        return False
    if row.get("year"):
        return row["year"] == str(year)
    if row.get("period"):
        return row["period"].startswith(str(year))
    if row.get("effective_period_end"):
        return row["effective_period_end"].startswith(str(year))
    for key in ("month_index", "issue_month", "accrual_month"):
        if row.get(key):
            return 1 <= int(row[key]) <= 12
    return True


def checks(data, family):
    out = []

    def check(name, residual, count):
        out.append(
            {
                "check": name,
                "tested_rows": count,
                "maximum_absolute_difference": str(residual),
                "status": "PASS" if residual <= D(".02") else "FAIL",
            }
        )

    def equations(name, rs, fn):
        check(name, max((abs(fn(r)) for r in rs), default=D(0)), len(rs))

    if family == "customer":
        rs = data["commercial_deferred_rollforward"]
        equations(
            "Contract deferred rollforward",
            rs,
            lambda r: (
                num(r, "opening_usd")
                + num(r, "billings_usd")
                - num(r, "credits_usd")
                - num(r, "recognized_usd")
                - num(r, "closing_usd")
            ),
        )
        by = collections.defaultdict(D)
        for r in rs:
            by[r["unit"], r["period"]] += num(r, "closing_usd")
        sub = data["subledger_rollforward"]
        equations(
            "Deferred schedule to unit subledger",
            [r for r in sub if (r["unit"], r["period"]) in by],
            lambda r: by[r["unit"], r["period"]] - num(r, "deferred_revenue_usd"),
        )
        ar = collections.defaultdict(D)
        for r in data["receivable_aging"]:
            ar[r["unit"], r["period"]] += num(r, "outstanding_usd")
        equations(
            "Aging to gross AR", sub, lambda r: ar[r["unit"], r["period"]] - num(r, "gross_ar_usd")
        )
    if family == "treasury":
        equations(
            "Treasury arrears rollforward",
            data["treasury_reconciliation"],
            lambda r: (
                num(r, "opening_unpaid_usd")
                + num(r, "new_deferral_usd")
                - num(r, "arrears_paid_usd")
                - num(r, "closing_unpaid_usd")
            ),
        )
        equations(
            "Lifetime request allocation",
            data["treasury_obligations"],
            lambda r: num(r, "requested_usd") - num(r, "funded_usd") - num(r, "unpaid_usd"),
        )
        po = {r["purchase_order_id"]: r for r in data["industrial_purchase_orders"]}
        rc = {r["receipt_id"]: r for r in data["industrial_receipts"]}
        bills = data["industrial_supplier_invoices"]
        missing = sum(r["purchase_order_id"] not in po or r["receipt_id"] not in rc for r in bills)
        check("Complete supplier PO and receipt links", D(missing), len(bills))
        if not missing:
            equations(
                "Supplier invoice to purchase order amount",
                bills,
                lambda r: num(r, "amount_usd") - num(po[r["purchase_order_id"]], "amount_usd"),
            )
            equations(
                "Supplier invoice to receipt amount",
                bills,
                lambda r: num(r, "amount_usd") - num(rc[r["receipt_id"]], "accepted_amount_usd"),
            )
    if family == "close":
        for name in ("journal", "enterprise_journal"):
            by = collections.defaultdict(D)
            for r in data[name]:
                by[r["journal_id"]] += num(r, "debit_usd") - num(r, "credit_usd")
            check(
                name + " every journal balances", max(map(abs, by.values()), default=D(0)), len(by)
            )
        for name, key in [("unit_trial_balance", "unit"), ("legal_trial_balance", "entity")]:
            by = collections.defaultdict(D)
            for r in data[name]:
                by[r[key], r["year"], r["month"]] += num(r, "signed_usd")
            check(
                name + " every monthly book balances",
                max(map(abs, by.values()), default=D(0)),
                len(by),
            )
        for name in ("monthly_statements", "legal_statements"):
            equations(
                name + " balance sheet",
                data[name],
                lambda r: num(r, "assets_usd") - num(r, "liabilities_usd") - num(r, "equity_usd"),
            )
            equations(
                name + " cash bridge",
                data[name],
                lambda r: (
                    num(r, "opening_cash_usd")
                    + num(r, "operating_cash_flow_usd")
                    + num(r, "investing_cash_flow_usd")
                    + num(r, "financing_cash_flow_usd")
                    + num(r, "opening_or_noncash_cash_bridge_usd")
                    - num(r, "ending_cash_usd")
                ),
            )
        by = collections.defaultdict(D)
        for r in data["journal"]:
            by[r["unit"], r["account"], int(r["month"])] += num(r, "signed_usd")
        mappings = {
            "gross_ar_usd": ("BIZ_AR", 1),
            "allowance_usd": ("BIZ_ALLOWANCE", -1),
            "deferred_revenue_usd": ("BIZ_DEFERRED", -1),
            "vendor_ap_usd": ("BIZ_AP", -1),
            "host_payable_usd": ("BIZ_HOST_AP", -1),
            "inventory_usd": ("BIZ_INVENTORY", 1),
            "gross_ppe_usd": ("BIZ_PPE", 1),
            "accumulated_depreciation_usd": ("BIZ_ACCUM", -1),
        }
        for field, (account, sign) in mappings.items():
            equations(
                "Core " + field + " to cumulative journal",
                data["subledger_rollforward"],
                lambda r: (
                    sum(by[r["unit"], account, m] for m in range(1, int(r["period"][5:7]) + 1))
                    * sign
                    - num(r, field)
                ),
            )
    if family == "supporting-schedules":
        equations(
            "Core asset cost less accumulated depreciation",
            data["asset_rollforward"],
            lambda r: num(r, "cost_usd") - num(r, "accumulated_usd") - num(r, "net_book_usd"),
        )
        equations(
            "Management allocation reconciliation",
            data["management_cost_reconciliation"],
            lambda r: num(r, "difference_usd"),
        )
        equations(
            "Industrial term principal rollforward",
            data["industrial_debt"],
            lambda r: (
                num(r, "opening_legacy_term_usd")
                - num(r, "principal_cash_paid_legacy_term_usd")
                - num(r, "closing_legacy_term_usd")
            ),
        )
        equations(
            "Industrial replacement debt rollforward",
            data["industrial_debt"],
            lambda r: (
                num(r, "opening_replacement_term_usd")
                + num(r, "replacement_debt_draw_usd")
                - num(r, "principal_cash_paid_replacement_term_usd")
                - num(r, "closing_replacement_term_usd")
            ),
        )
    if family == "tax-transaction":
        equations(
            "Acquisition consideration less acquired cash",
            data["acquisition_cashflow_bridge"],
            lambda r: (
                num(r, "stock_consideration_usd")
                - num(r, "cash_acquired_usd")
                + num(r, "acquisition_investing_cash_usd")
            ),
        )
    return out


FAMILIES = {
    "customer": {
        "title": "Billing, collections and deferred revenue",
        "tables": [
            "contracts",
            "contract_versions",
            "invoices",
            "credit_history",
            "credit_notes",
            "receivable_aging",
            "credit_allowance",
            "commercial_deferred_rollforward",
            "subledger_rollforward",
            "events",
        ],
        "extras": {},
        "schedule": "subledger_rollforward",
        "columns": ["period", "unit", "gross_ar_usd", "allowance_usd", "deferred_revenue_usd"],
        "limits": "Invoice master rows are end-of-model snapshots for invoices issued in 2027; collected/remaining fields include later lifecycle activity and are NOT December 2027 balances. Period aging and subledger rows control month-end balances. Events include complete 2027 populations, not only invoice events. Contracts without scenario/time fields are shared source inputs, not extra transactions. No original customer bill, signed acceptance, bank confirmation or tax invoice is supplied.",
    },
    "treasury": {
        "title": "Procurement, payables and Treasury",
        "tables": [
            "payables",
            "treasury_obligations",
            "treasury_obligation_history",
            "treasury_reconciliation",
            "host_collection_settlements",
            "subledger_rollforward",
        ],
        "extras": {
            n: "industrial/transactions/" + n.removeprefix("industrial_") + ".csv"
            for n in [
                "industrial_purchase_orders",
                "industrial_receipts",
                "industrial_supplier_invoices",
                "industrial_document_journal_lineage",
            ]
        },
        "schedule": "treasury_reconciliation",
        "columns": [
            "period",
            "cash_flow",
            "opening_unpaid_usd",
            "requested_usd",
            "current_funded_usd",
            "new_deferral_usd",
            "arrears_paid_usd",
            "closing_unpaid_usd",
        ],
        "limits": "Treasury is illustrative FIFO allocation within cash-flow class, not employee/vendor bank-payment proof. Obligation and payable master funded/unpaid fields are terminal snapshots, not month-end balances; history and reconciliation rows control dated exposure. Industrial invoice terminal settlement fields have the same boundary. Complete industrial PO/receipt/invoice joins are present; Core vendor originals and daily bank confirmations are not supplied. Native industrial document lineage is a model support chain, not independent corroboration.",
    },
    "close": {
        "title": "Close, allowance and legal-book reconciliation",
        "tables": [
            "journal",
            "enterprise_journal",
            "unit_trial_balance",
            "legal_trial_balance",
            "monthly_statements",
            "legal_statements",
            "credit_allowance",
            "subledger_rollforward",
        ],
        "extras": {},
        "schedule": "monthly_statements",
        "columns": [
            "unit",
            "year",
            "month",
            "revenue_usd",
            "net_income_usd",
            "assets_usd",
            "liabilities_usd",
            "equity_usd",
            "ending_cash_usd",
        ],
        "limits": "Unit reporting and legal books are alternative views, not populations to add together. Core journal and enterprise replacement journal are different scopes: never concatenate them. Reporting clearing and legal management allocation retain their released classifications. Close validation checks complete monthly books, not an independent audit opinion.",
    },
    "supporting-schedules": {
        "title": "Workforce, inventory, fixed assets and debt",
        "tables": [
            "workforce_positions",
            "workforce_positions_history",
            "workforce_assignments",
            "workforce_changes",
            "asset_rollforward",
            "inventory_rollforward",
            "management_cost_reconciliation",
            "service_cost_pools",
            "service_consumption_allocations",
        ],
        "extras": {
            **{
                n: "industrial/forecast/" + n.removeprefix("industrial_") + ".csv"
                for n in ["industrial_assets", "industrial_debt", "industrial_inventory"]
            },
            "industrial_payroll_batches": "industrial/transactions/payroll_batches.csv",
        },
        "schedule": "asset_rollforward",
        "columns": ["period", "unit", "asset_id", "cost_usd", "accumulated_usd", "net_book_usd"],
        "limits": "Position IDs are synthetic planning records, not new named employees or actual 2026 headcount. Loaded costs are employer costs, not net pay. Core and industrial schedules are separate source systems. Stock quantities are retained in their original units. No payroll remittance, independent valuation, reserve certification, new ownership or covenant threshold is created.",
    },
    "tax-transaction": {
        "title": "Transaction cash and conditional tax support",
        "tables": [],
        "extras": {
            "acquisition_cashflow_bridge": "enterprise/acquisition_cashflow_bridge.csv",
            "enterprise_tax_allocation_bridge": "enterprise/enterprise_tax_allocation_bridge.csv",
        },
        "year": 2026,
        "schedule": "acquisition_cashflow_bridge",
        "columns": [
            "year",
            "month",
            "stock_consideration_usd",
            "cash_acquired_usd",
            "acquisition_investing_cash_usd",
            "parent_acquisition_capital_usd",
            "transaction_operating_expense_usd",
        ],
        "limits": "This separate base-2026 bridge is not added to base-2027 activity. ARU filing-ready is not IRS filing or acceptance. Tax/book PPA assumptions remain conditional current industrial source records, not an election, return or valuation opinion. Red Wash escrow/holdback are included in purchase consideration rather than extra price.",
    },
}


def build(archive):
    raw = archive.read_bytes()
    assert digest(raw) == ARCHIVE_SHA, "Unrecognized archive"
    cfg = json.loads((BASE / "coverage/SCOPE.json").read_text())
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            dbpath = Path(td) / "native.sqlite3"
            dbpath.write_bytes(z.read("enterprise.sqlite3"))
            native = sqlite3.connect(dbpath)
            native.row_factory = sqlite3.Row
            assert native.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            inventory = []
            for name in sorted(n for n in z.namelist() if n.endswith(".csv")):
                data = z.read(name)
                rs = rows(data)
                cols = list(rs[0]) if rs else next(csv.reader(io.StringIO(data.decode())), [])
                scenarios = sorted({r.get("scenario", "SHARED") for r in rs})
                years = sorted(
                    {
                        r.get("year")
                        or (r.get("period") or r.get("effective_period_end") or "")[:4]
                        or "SHARED_OR_INDEXED"
                        for r in rs
                    }
                )
                inventory.append(
                    {
                        "member": name,
                        "sha256": digest(data),
                        "rows": len(rs),
                        "columns": cols,
                        "scenarios": scenarios,
                        "years": years,
                        "disposition": "NATIVE_RELEASE_ACCESS; selected base-2027 families below have additional human schedules; other periods/scenarios not human-complete",
                        "duplicate_boundary": "COMPARISON_ONLY_NOT_ADDITIVE"
                        if name.startswith("comparison/")
                        else "UNIT_SUBSET_NOT_ADDITIVE"
                        if name.startswith("units/")
                        else "PARENT_SOURCE",
                    }
                )
            dump(
                BASE / "coverage/RELEASE_INVENTORY.json",
                {"release": cfg["release"], "archive_sha256": ARCHIVE_SHA, "tables": inventory},
            )
            dbsha = digest(z.read("enterprise.sqlite3"))
            for family, spec in FAMILIES.items():
                folder = BASE / family
                (folder / "source").mkdir(parents=True, exist_ok=True)
                year = spec.get("year", 2027)
                data = {}
                sources = []
                members = {n: "tables/" + n + ".csv" for n in spec["tables"]} | spec["extras"]
                extract_db = folder / "evidence.sqlite3"
                if extract_db.exists():
                    extract_db.unlink()
                dest = sqlite3.connect(extract_db)
                for table, member in members.items():
                    payload = z.read(member)
                    full = rows(payload)
                    filtered = [r for r in full if selected(r, year)]
                    columns = (
                        list(full[0]) if full else next(csv.reader(io.StringIO(payload.decode())))
                    )
                    if member.startswith("tables/"):
                        # Native table and CSV must contain exactly the same full population and serialized values.
                        native_rows = [
                            dict(r) for r in native.execute('SELECT * FROM "' + table + '"')
                        ]
                        canonical = lambda rs: sorted(json.dumps(r, sort_keys=True) for r in rs)
                        assert canonical(native_rows) == canonical(full), (
                            "Native CSV/SQLite mismatch: " + table
                        )
                    target = folder / "source" / f"{table}.csv"
                    with target.open("w", newline="") as f:
                        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
                        w.writeheader()
                        w.writerows(filtered)
                    dest.execute(
                        'CREATE TABLE "'
                        + table
                        + '" ('
                        + ",".join('"' + c + '" TEXT NOT NULL' for c in columns)
                        + ")"
                    )
                    dest.executemany(
                        'INSERT INTO "'
                        + table
                        + '" VALUES ('
                        + ",".join("?" for c in columns)
                        + ")",
                        [[r[c] for c in columns] for r in filtered],
                    )
                    sources.append(
                        {
                            "path": str(target.relative_to(ROOT)),
                            "release_member": member,
                            "native_table": table if member.startswith("tables/") else None,
                            "row_count": len(filtered),
                            "full_release_row_count": len(full),
                            "sha256": digest(target.read_bytes()),
                            "release_member_sha256": digest(payload),
                            "predicate": f"base scenario where supplied; {year} by year/period/month index; shared static inputs retained; terminal master snapshots explicitly identified in README",
                        }
                    )
                    data[table] = filtered
                dest.commit()
                dest.execute("VACUUM")
                dest.close()
                result = checks(data, family)
                dump(
                    folder / "RECONCILIATION.json",
                    {
                        "status": "PASS" if all(r["status"] == "PASS" for r in result) else "FAIL",
                        "checks": result,
                    },
                )
                reg = {
                    "schema_version": 1,
                    "package_id": "SH-FIN-" + family.upper(),
                    "title": spec["title"],
                    "status": "SOURCE_RECONCILED_VISUAL_REVIEW_PENDING",
                    "scope": {
                        "release": cfg["release"],
                        "release_sha256": ARCHIVE_SHA,
                        "source_revision": REVISION,
                        "scenario": "base",
                        "period_start": str(year) + "-01",
                        "period_end": str(year) + "-12",
                    },
                    "native_database": {"release_member": "enterprise.sqlite3", "sha256": dbsha},
                    "extracted_database": {
                        "path": str(extract_db.relative_to(ROOT)),
                        "sha256": digest(extract_db.read_bytes()),
                    },
                    "sources": sources,
                    "markdown": str((folder / "README.md").relative_to(ROOT)),
                    "reconciliation": str((folder / "RECONCILIATION.json").relative_to(ROOT)),
                    "visual_manifest": None,
                }
                if family == "tax-transaction":
                    reg["supplemental_record"] = (
                        "docs/finance/evidence/tax-transaction/CURRENT_SOURCE_BRIDGE.json"
                    )
                dump(folder / "evidence-register.json", reg)
                text = f"# {spec['title']}\n\n**Scope:** base scenario, {year}; complete declared table populations, all applicable reporting units. Public synthetic records. New PDF/Excel presentation remains subject to exact-file review.\n\n{spec['limits']}\n\n"
                text += "## Open and trace the records\n\nOpen the CSV files below directly in Excel, or use `evidence.sqlite3` for the same exact extracted rows. Every original source column is preserved. Match native IDs; never combine comparison releases, unit subsets and enterprise rows as additional transactions. The [register](evidence-register.json) identifies exact archive/database/member hashes and filters.\n\n| Table | Selected rows | Full release rows | Open CSV |\n|---|---:|---:|---|\n"
                for r in sources:
                    text += f"| {Path(r['path']).stem} | {r['row_count']} | {r['full_release_row_count']} | [CSV](source/{Path(r['path']).name}) |\n"
                text += "\n## Reconciliation\n\n| Check | Rows/groups | Maximum difference | Result |\n|---|---:|---:|---|\n"
                for r in result:
                    text += f"| {r['check']} | {r['tested_rows']} | {r['maximum_absolute_difference']} | {r['status']} |\n"
                text += "\nAll monetary checks use decimal arithmetic with a $0.02 tolerance for released rounding. This does not hide an unexplained balancing entry. Complete values, including zero and adverse outcomes, remain in the source tables. See [machine-readable discrepancies](RECONCILIATION.json).\n\nOther scenarios and 2028–2031 remain accessible in the immutable release but are not claimed as human-complete here. [Full release inventory](../coverage/README.md) explains the scope boundary.\n"
                if family == "tax-transaction":
                    text += "\n[Current industrial acquisition and tax support](TRANSACTION_SUPPORT.md) separately reproduces the accepted2026 PPA, full opening trial balance, twelve-month tax/debt/assets schedules and legal documentary limits. Its current-source identity is not the immutable operations archive.\n"
                if family == "customer":
                    text += "\n## Contract, receipt and journal joins\n\nMatch contract_versions.contract_id to contracts.contract_id. The selected model starts product histories in 2027; no pre-2027 product-version population is omitted. Match credit_history.invoice_id to invoices.invoice_id, then credit_history.source_id to events.event_id and [the complete Core journal](../close/source/journal.csv) source_id. Receipts are released history/event rows, not a separate authentic bank receipt. The cross-family validator rejects dangling contract, invoice, event or invoice-event journal joins. Earlier/later commercial sources are not silently imported as new transactions.\n"
                (folder / "README.md").write_text(text)
                dump(
                    folder / "SCHEDULE.json",
                    {
                        "title": spec["title"],
                        "columns": spec["columns"],
                        "rows": [
                            {c: r.get(c, "") for c in spec["columns"]}
                            for r in data[spec["schedule"]]
                        ],
                        "source_table": spec["schedule"],
                        "scope": reg["scope"],
                        "limitations": spec["limits"],
                    },
                )
                print(
                    family, sum(len(rs) for rs in data.values()), len(result), reg["status"], result
                )
                assert all(r["status"] == "PASS" for r in result), (
                    "Reconciliation failure: " + family
                )
            native.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--archive", type=Path, required=True)
    args = p.parse_args()
    build(args.archive)
