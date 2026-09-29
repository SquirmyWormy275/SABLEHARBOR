"""Reproduce three public transaction-to-books walkthroughs; create no postings."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sqlite3
import tempfile
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import xlsxwriter

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "docs/legal/gap-instruments/walkthroughs"
D = Decimal


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csvread(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def aggregate(rows, key, value="signed_usd"):
    result = defaultdict(Decimal)
    for row in rows:
        result[row[key]] += D(row[value])
    return result


def derive():
    spec = importlib.util.spec_from_file_location(
        "walk_native", ROOT / "industrial/tools/build_financials.py"
    )
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    tables = {}
    with tempfile.TemporaryDirectory() as folder:
        native.build(Path(folder))
        for name in [
            "aru_2026_journal",
            "aru_2026_trial_balance",
            "aru_acquisition_opening_trial_balance",
            "red_wash_2026_journal",
            "red_wash_2026_trial_balance",
            "financial_statements",
        ]:
            tables[name] = csvread(Path(folder) / (name + ".csv"))
    tables["financial_statements"] = [
        r for r in tables["financial_statements"] if r["year"] == "2026"
    ]
    close = ROOT / "docs/finance/evidence/close/source"
    tables["ff_journal"] = [
        r
        for r in csvread(close / "journal.csv")
        if r["unit"] == "foundry-field" and r["scenario"] == "base" and r["year"] == "2027"
    ]
    tables["ff_statements"] = [
        r
        for r in csvread(close / "monthly_statements.csv")
        if r["unit"] == "foundry-field" and r["scenario"] == "base" and r["year"] == "2027"
    ]
    packet = json.loads((ROOT / "docs/finance/evidence/SH-FIN-HUMAN-001/source.json").read_text())
    tables["ff_invoice"] = packet["rows"]["invoices"]
    tables["ff_packet_journal"] = packet["rows"]["journal"]
    tables["ff_contract_trace"] = [r for r in tables["ff_journal"] if "FF-003" in r["source_id"]]
    checks = []

    def check(case, label, left, right, tolerance="0.02"):
        delta = D(left) - D(right)
        checks.append(
            dict(
                case=case,
                check=label,
                left_usd=str(left),
                right_usd=str(right),
                difference_usd=str(delta),
                tolerance_usd=tolerance,
                status="PASS" if abs(delta) <= D(tolerance) else "FAIL",
            )
        )

    tx = json.loads((ROOT / "industrial/source/finance.json").read_text())["transaction"]
    check(
        "ARU",
        "Stock price + debt payoff = debt + parent equity before fees",
        tx["buyer_consideration"] + tx["existing_term_revolver_refinance"],
        tx["new_debt"] + tx["parent_equity_before_fees"],
    )
    aru = tables["aru_2026_journal"]
    opening = aggregate([r for r in aru if r["month"] == "0"], "account")
    if set(opening) != {r["account"] for r in tables["aru_acquisition_opening_trial_balance"]}:
        raise ValueError("Opening account coverage differs")
    for row in tables["aru_acquisition_opening_trial_balance"]:
        check(
            "ARU",
            "Opening account " + row["account"],
            opening[row["account"]],
            D(row["debit_balance_usd"]) - D(row["credit_balance_usd"]),
        )
    for case, name in [("ARU", "aru_2026"), ("Red Wash", "red_wash_2026")]:
        rows = tables[name + "_journal"]
        balances = aggregate(rows, "account")
        for jid, amount in aggregate(rows, "journal_id").items():
            check(case, "Balanced journal " + jid, amount, 0)
        for row in tables[name + "_trial_balance"]:
            check(
                case,
                "Full-year journal to closing account " + row["account"],
                balances[row["account"]],
                row["signed_usd"],
            )
        types = {r["account"]: r["type"] for r in tables[name + "_trial_balance"]}
        if not set(balances) <= set(types):
            raise ValueError("Journal account absent from closing trial balance")
        entity = "ARU_GROUP" if case == "ARU" else "RWH_PS"
        numeric = [
            r["line_id"]
            for r in tables["financial_statements"]
            if r["entity"] == entity and r["line_id"].isdigit()
        ]
        nonzero = {r["account"] for r in tables[name + "_trial_balance"] if D(r["signed_usd"]) != 0}
        if len(numeric) != len(set(numeric)) or not nonzero <= set(numeric) <= set(types):
            raise ValueError("Numeric statement account coverage differs")
        for row in tables["financial_statements"]:
            if (
                row["entity"] != ("ARU_GROUP" if case == "ARU" else "RWH_PS")
                or row["line_id"] not in balances
            ):
                continue
            a = row["line_id"]
            value = balances[a] * (-1 if types[a] in {"liability", "equity", "revenue"} else 1)
            check(case, "Closing account to statement " + a, value, row["amount_usd"])
    ff = tables["ff_journal"]
    for row in tables["ff_packet_journal"]:
        matches = [
            r
            for r in ff
            if r["journal_id"] == row["journal_id"]
            and r["account"] == row["account"]
            and r["source_id"] == row["source_id"]
        ]
        if len(matches) != 1 or matches[0] != row:
            raise ValueError("Accepted invoice journal differs from close evidence")
    for row in tables["ff_statements"]:
        month = row["month"]
        selected = [r for r in ff if r["month"] == month and r["account"] == "BIZ_REVENUE"]
        check(
            "Foundry Field",
            "Month " + month + " complete unit revenue to statement",
            -sum((D(r["signed_usd"]) for r in selected), D(0)),
            row["revenue_usd"],
        )
        check(
            "Foundry Field",
            "Month " + month + " assets = liabilities + equity",
            row["assets_usd"],
            D(row["liabilities_usd"]) + D(row["equity_usd"]),
        )
    summary = []
    for case, rows in [("ARU", aru), ("Red Wash", tables["red_wash_2026_journal"])]:
        for month in range(13):
            period = [r for r in rows if int(r["month"]) == month]
            summary.append(
                dict(
                    case=case,
                    month=str(month),
                    journal_legs=str(len(period)),
                    debits_usd=str(sum((D(r["debit_usd"]) for r in period), D(0))),
                    credits_usd=str(sum((D(r["credit_usd"]) for r in period), D(0))),
                    cash_change_usd=str(
                        sum((D(r["signed_usd"]) for r in period if r["account"] == "1000"), D(0))
                    ),
                )
            )
    tables["monthly_trace"] = summary
    tables["rw_aro_trace"] = [r for r in tables["red_wash_2026_journal"] if r["account"] == "2200"]
    requests = [
        (
            "WALK-REQ-ARU-01",
            "ARU acquisition",
            "External funding and payoff confirmations",
            "Compare actual cash and creditor discharge to ARU-CL-02/03 and modeled sources/uses.",
            "Cannot conclude funds moved or liens were released.",
            "industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md",
        ),
        (
            "WALK-REQ-ARU-02",
            "ARU acquisition",
            "Filed election evidence and final valuation support",
            "Resolve conditional tax and PPA inputs before treating modeled tax basis as filed.",
            "Cannot conclude IRS filing/acceptance or independently verified fair values.",
            "industrial/transaction/07_ARU_TAX_STRUCTURE_MEMORANDUM.md",
        ),
        (
            "WALK-REQ-ARU-03",
            "ARU acquisition",
            "Actual post-cutoff journals and source vouchers",
            "Replace September–December management scenario with supported actual activity.",
            "Cannot call full-year modeled statements actual 2026 results.",
            "industrial/finance/ASSUMPTIONS_AND_TEMPORAL_CONTROLS.md",
        ),
        (
            "WALK-REQ-FF-01",
            "Foundry Field base 2027",
            "Customer billing identity, executed contract, service acceptance and bank evidence",
            "Corroborate invoice, service, credits and recovery beyond one synthetic release.",
            "Cannot conclude actual billing, earned customer revenue or received cash.",
            "docs/finance/evidence/SH-FIN-HUMAN-001/source.json",
        ),
        (
            "WALK-REQ-RW-01",
            "Red Wash",
            "Independent closure engineering estimate and approved timing",
            "Test ARO cash-flow amount/timing rather than liability-calibrated model.",
            "Cannot conclude independently estimated closure obligation.",
            "industrial/finance/RED_WASH_AND_FUNDING.md",
        ),
        (
            "WALK-REQ-RW-02",
            "Red Wash",
            "Closing escrow confirmation and successor opening rollforward",
            (
                "Connect 2025 acquisition funds to 2026 successor opening with actual "
                "custody and movements."
            ),
            "Cannot treat 2025 escrow as current cash or successor opening as audited history.",
            "red_wash/source/core_operating_data.json",
        ),
    ]
    tables["evidence_requests"] = [
        dict(
            zip(
                ["id", "scope", "missing_record", "purpose", "blocked_conclusion", "source_path"],
                row,
                strict=True,
            )
        )
        for row in requests
    ]
    tables["checks"] = checks
    if any(r["status"] != "PASS" for r in checks):
        raise ValueError([r for r in checks if r["status"] != "PASS"][:10])
    sources = [
        "industrial/source/finance.json",
        "industrial/source/operations.json",
        "red_wash/source/core_operating_data.json",
        "industrial/tools/build_financials.py",
        "industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md",
        "industrial/transaction/07_ARU_TAX_STRUCTURE_MEMORANDUM.md",
        "industrial/finance/TRANSACTION_ACCOUNTING.md",
        "industrial/finance/ASSUMPTIONS_AND_TEMPORAL_CONTROLS.md",
        "industrial/finance/RED_WASH_AND_FUNDING.md",
        "docs/finance/evidence/SH-FIN-HUMAN-001/source.json",
        "docs/finance/evidence/close/source/journal.csv",
        "docs/finance/evidence/close/source/monthly_statements.csv",
        "docs/finance/evidence/close/evidence-register.json",
    ]
    provenance = dict(
        status="DRAFT_FOR_REVIEW",
        classification="PUBLIC_WORKED_EXAMPLE",
        no_new_postings=True,
        internal_consistency_only=True,
        monetary_check_categories={
            category: sum(r["check"].startswith(prefix) for r in checks)
            for category, prefix in {
                "balanced_journals": "Balanced journal ",
                "opening_accounts": "Opening account ",
                "journal_to_trial_balance": "Full-year journal to closing account ",
                "numeric_statement_lines": "Closing account to statement ",
                "funding": "Stock price + debt payoff",
                "monthly_foundry_field": "Month ",
            }.items()
        },
        exact_packet_membership={
            "rows": len(tables["ff_packet_journal"]),
            "full_unit_rows": len(ff),
            "comparison": (
                "Every accepted packet row matches exactly one complete close-extract "
                "row across all original columns."
            ),
            "status": "PASS",
        },
        sources=[dict(path=p, sha256=sha(ROOT / p)) for p in sources],
        scopes={
            "industrial": (
                "Native build_financials.py regeneration, ARU_GROUP and RWH_PS 2026 "
                "only; management scenario cutoff 2026-09-05. No cross-release "
                "aggregate."
            ),
            "foundry_field": (
                "Committed close extract: unit=foundry-field, scenario=base, year=2027."
                " Exact 12 accepted packet journal legs verified against complete unit "
                "population. Contract trace uses literal FF-003 in source_id."
            ),
        },
        tables={k: len(v) for k, v in tables.items()},
    )
    return tables, provenance


def workbook(path, tables):
    book = xlsxwriter.Workbook(path)
    book.set_properties(
        {
            "title": "Sable Harbor | Transaction walkthroughs — draft",
            "created": datetime(2026, 9, 12),  # Fixed naive timestamp required by XLSX metadata.
        }
    )
    header = book.add_format(
        {
            "bold": True,
            "font_color": "white",
            "bg_color": "#172C35",
            "text_wrap": True,
            "valign": "vcenter",
        }
    )
    body = book.add_format(
        {
            "font_name": "Aptos",
            "font_size": 10,
            "text_wrap": True,
            "valign": "top",
            "bottom": 1,
            "bottom_color": "#DCE2E3",
            "indent": 1,
        }
    )
    number = book.add_format(
        {
            "font_name": "Aptos",
            "font_size": 10,
            "num_format": "#,##0.00;[Red](#,##0.00);–",
            "valign": "top",
            "bottom": 1,
            "bottom_color": "#DCE2E3",
            "indent": 1,
        }
    )
    sheets = [
        (
            "Read first",
            [
                {
                    "case": "ARU acquisition",
                    "read": (
                        "Closing record → opening accounts → all monthly journals → closing "
                        "trial balance → annual statements. Full-year results include modeled "
                        "post-cutoff activity."
                    ),
                },
                {
                    "case": "Foundry Field",
                    "read": (
                        "Accepted invoice → exact journal legs → contract service trace → "
                        "complete unit monthly revenue. One invoice is not total unit revenue."
                    ),
                },
                {
                    "case": "Red Wash",
                    "read": (
                        "Successor opening → ARO movements → closing liability. 2025 "
                        "acquisition and 2026 successor are distinct populations."
                    ),
                },
                {
                    "case": "Evidence requests",
                    "read": (
                        "Six missing-evidence requests state the blocked conclusion. All "
                        "designs remain draft. No new transactions or execution claims."
                    ),
                },
                {
                    "case": "Complete evidence",
                    "read": (
                        "The source/ CSV files and walkthroughs.sqlite3 preserve every selected"
                        " native column. checks.csv contains every measured difference; this "
                        "workbook presents readable working views."
                    ),
                },
            ],
        ),
        ("Monthly trace", tables["monthly_trace"]),
        (
            "ARU opening",
            [
                {
                    k: r[k]
                    for k in ["account", "account_name", "debit_balance_usd", "credit_balance_usd"]
                }
                for r in tables["aru_acquisition_opening_trial_balance"]
            ],
        ),
        (
            "ARU closing",
            [
                {k: r[k] for k in ["account", "account_name", "signed_usd"]}
                for r in tables["aru_2026_trial_balance"]
            ],
        ),
        (
            "FF invoice events",
            [
                {k: r[k] for k in ["month", "journal_id", "account", "signed_usd", "description"]}
                for r in tables["ff_packet_journal"]
            ],
        ),
        (
            "FF service trace",
            [
                {k: r[k] for k in ["month", "source_id", "account", "signed_usd"]}
                for r in tables["ff_contract_trace"]
            ],
        ),
        (
            "FF statements",
            [
                {k: r[k] for k in ["month", "revenue_usd", "expense_usd", "net_income_usd"]}
                for r in tables["ff_statements"]
            ],
        ),
        (
            "RW closure liability",
            [
                {k: r[k] for k in ["month", "source_id", "signed_usd", "description"]}
                for r in tables["rw_aro_trace"]
            ],
        ),
        (
            "Evidence requests",
            [
                {k: r[k] for k in ["id", "missing_record", "purpose", "blocked_conclusion"]}
                for r in tables["evidence_requests"]
            ],
        ),
    ]
    for name, rows in sheets:
        sheet = book.add_worksheet(name)
        keys = list(rows[0])
        sheet.merge_range(
            0, 0, 0, len(keys) - 1, "SABLE HARBOR  /  " + name.upper() + "  /  DRAFT", header
        )
        sheet.set_row(0, 30)
        sheet.write_row(2, 0, [k.replace("_", " ").title() for k in keys], header)
        sheet.set_row(2, 32)
        for i, row in enumerate(rows, 3):
            for j, k in enumerate(keys):
                if k.endswith("_usd"):
                    sheet.write_number(i, j, float(row[k]), number)
                else:
                    sheet.write(i, j, str(row[k]), body)
            sheet.set_row(i, 85 if name in {"Read first", "Evidence requests"} else 48)
        for j, k in enumerate(keys):
            sheet.set_column(
                j,
                j,
                60
                if len(keys) == 2
                else 45
                if k == "account_name"
                else 35
                if k
                in {
                    "description",
                    "purpose",
                    "blocked_conclusion",
                    "missing_record",
                    "source_id",
                    "account_name",
                }
                else 22,
            )
        sheet.freeze_panes(3, 0)
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.fit_to_pages(1, 0)
        sheet.repeat_rows(0, 2)
        sheet.print_area(0, 0, len(rows) + 2, len(keys) - 1)
        sheet.set_margins(0.3, 0.3, 0.4, 0.4)
        sheet.set_footer(
            "&LSable Harbor | Public worked example | Draft&RPage &P of &N", {"margin": 0.15}
        )
    book.close()


def build(dest=DEST):
    tables, provenance = derive()
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "source").mkdir(exist_ok=True)
    dbpath = dest / "walkthroughs.sqlite3"
    dbpath.unlink(missing_ok=True)
    with sqlite3.connect(dbpath) as db:
        for name, rows in tables.items():
            fields = list(rows[0])
            with (dest / "source" / f"{name}.csv").open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            db.execute(
                f'CREATE TABLE "{name}" (' + ", ".join('"' + k + '" TEXT' for k in fields) + ")"
            )
            db.executemany(
                f'INSERT INTO "{name}" VALUES (' + ",".join("?" for _ in fields) + ")",
                [[str(r[k]) for k in fields] for r in rows],
            )
    (dest / "source-register.json").write_text(json.dumps(provenance, indent=2) + "\n")
    workbook(dest / "walkthroughs.xlsx", tables)
    return provenance


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    p.add_argument("--output", type=Path, default=DEST)
    a = p.parse_args()
    if a.check:
        with tempfile.TemporaryDirectory() as d:
            expected = Path(d)
            build(expected)
            for file in expected.rglob("*"):
                if (
                    file.is_file()
                    and file.suffix != ".sqlite3"
                    and file.read_bytes() != (a.output / file.relative_to(expected)).read_bytes()
                ):
                    raise ValueError("Stale " + str(file.relative_to(expected)))
            with (
                sqlite3.connect(expected / "walkthroughs.sqlite3") as left,
                sqlite3.connect(a.output / "walkthroughs.sqlite3") as right,
            ):
                if list(left.iterdump()) != list(right.iterdump()):
                    raise ValueError("Stale SQLite contents")
        print("PASS: all walkthrough source selections, calculations and derivatives")
    else:
        print(json.dumps(build(a.output)["tables"], indent=2))


if __name__ == "__main__":
    main()
