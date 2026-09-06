#!/usr/bin/env python3
"""Independently reconcile emitted industrial evidence and publication provenance."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from build_package import CUTOFF, digest, reviewed_entries, run_builders, validate_row_time

ROOT = Path(__file__).resolve().parents[2]
FIN = ROOT / "industrial/generated/finance"


def rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def validate(*, generate=False):
    if generate:
        run_builders()
    checks = []

    def check(label, condition):
        if not condition:
            raise ValueError(label)
        checks.append(label)

    for name in ("aru_2025", "aru_2026", "red_wash_2026"):
        journal = rows(FIN / f"{name}_journal.csv")
        balances = defaultdict(int)
        entry_balances = defaultdict(int)
        for row in journal:
            amount = int(row["debit_usd"]) - int(row["credit_usd"])
            check(f"{name} signed amount {len(checks)}", amount == int(row["signed_usd"]))
            balances[row["account"]] += amount
            entry_balances[row["journal_id"]] += amount
            validate_row_time(row, name)
        check(
            name + " every independent journal balances",
            all(value == 0 for value in entry_balances.values()),
        )
        trial = rows(FIN / f"{name}_trial_balance.csv")
        check(
            name + " journal totals reconcile to trial balance",
            {row["account"]: int(row["signed_usd"]) for row in trial if int(row["signed_usd"])}
            == {key: value for key, value in balances.items() if value},
        )
        statements = rows(FIN / f"{name}_monthly_statements.csv")
        for row in statements:
            check(
                name + " monthly accounting equation",
                int(row["assets_usd"])
                == int(row["liabilities_usd"]) + int(row["equity_including_current_income_usd"]),
            )
            check(
                name + " cash flow reaches cash",
                int(row["opening_cash_usd"]) + sum(json.loads(row["cash_flow"]).values())
                == int(row["ending_cash_usd"]),
            )
            validate_row_time(row, name)

    invoices = rows(FIN / "intercompany_invoices_2026.csv")
    aru = rows(FIN / "aru_2026_journal.csv")
    mine = rows(FIN / "red_wash_2026_journal.csv")
    for invoice in invoices:
        amount = int(invoice["revenue_usd"])
        key = invoice["invoice_id"]
        revenue = -sum(
            int(row["signed_usd"])
            for row in aru
            if row["source_id"] == key and row["account"] == "4100"
        )
        expense = sum(
            int(row["signed_usd"])
            for row in mine
            if row["source_id"] == "IC-RECIPROCAL:" + key and row["account"] == "5150"
        )
        check("reciprocal invoice " + key, revenue == expense == amount)
    elimination = {
        row["entry_id"]: int(row["amount_usd"])
        for row in rows(FIN / "intercompany_eliminations.csv")
    }
    check(
        "all intercompany invoice revenue eliminates",
        elimination["ELIM-IC-PNL"] == sum(int(row["revenue_usd"]) for row in invoices),
    )
    check(
        "year-end intercompany balances eliminate",
        elimination["ELIM-IC-BS"]
        == sum(int(row["revenue_usd"]) for row in invoices if int(row["month"]) == 12),
    )

    funding = rows(FIN / "parent_equity_funding_2026.csv")
    summary = json.loads((FIN / "financial_summary.json").read_text())
    check(
        "ARU funding register totals",
        sum(int(row["amount_usd"]) for row in funding if row["recipient"] == "ARU")
        == summary["funding"]["aru_postclose_equity_usd"],
    )
    check(
        "mine funding register totals",
        sum(int(row["amount_usd"]) for row in funding if row["recipient"] == "RWH_VIA_PS")
        == summary["funding"]["mine_2026_equity_usd"],
    )
    check(
        "acquisition sources equal uses",
        summary["acquisition"]["close_sources_before_fees_usd"]
        == summary["acquisition"]["close_uses_before_fees_usd"],
    )
    consolidation = summary["industrial_operating_consolidation"]
    check(
        "industrial operating consolidation equation",
        consolidation["assets_after_intercompany_receivable_elimination_usd"]
        == consolidation["liabilities_after_intercompany_payable_elimination_usd"]
        + consolidation["equity_before_parent_transaction_expense_usd"],
    )

    catalog = json.loads((ROOT / "industrial/source/participant_catalog.json").read_text())
    selected = reviewed_entries(catalog)
    for entry in selected:
        if entry["path"].endswith(".csv"):
            for row in rows(ROOT / entry["path"]):
                validate_row_time(row, entry["path"], CUTOFF)
    check("selected corpus categories and dates", bool(selected))

    ingestion = json.loads(
        (ROOT / "docs/handoffs/industrial_r2/repository_ingestion.json").read_text()
    )
    for entry in ingestion["entries"]:
        check(
            "preserved source " + entry["original_member"],
            digest(ROOT / entry["repository_path"]) == entry["sha256"],
        )
    for relative, list_key, path_key in (
        ("red_wash/history/v1.0.0/manifest.json", "files", "path"),
        ("docs/organization/history/v0.3.0/manifest.json", "artifacts", "preserved_path"),
    ):
        for artifact in json.loads((ROOT / relative).read_text())[list_key]:
            if path_key in artifact:
                check(
                    "preserved historical " + artifact[path_key],
                    digest(ROOT / artifact[path_key]) == artifact["sha256"],
                )

    visual = ROOT / "industrial/visuals/manifest.json"
    for artifact in json.loads(visual.read_text())["artifacts"]:
        check(
            "current map hash " + artifact["path"],
            digest(ROOT / artifact["path"]) == artifact["sha256"],
        )
        check(
            "current map rebuild " + artifact["path"],
            digest(ROOT / artifact["path"]) == digest(ROOT / artifact["generated_from"]),
        )
    return {
        "status": "PASS",
        "checks_passed": len(checks),
        "selected_artifacts": len(selected),
        "cutoff": CUTOFF,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()
    print(json.dumps(validate(generate=args.generate), indent=2))


if __name__ == "__main__":
    main()
