"""Independent exported-data acceptance for the planning successor."""

from __future__ import annotations

import calendar
import csv
import hashlib
import json
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CUTOFF = "2026-09-06T23:59:59-07:00"
D = Decimal


def instant(value):
    if not isinstance(value, str) or not value:
        raise ValueError("missing dated availability")
    if len(value) == 4:
        value += "-12-31T23:59:59-07:00"
    elif len(value) == 7:
        year, month = map(int, value.split("-"))
        value += f"-{calendar.monthrange(year, month)[1]:02}T23:59:59-07:00"
    elif len(value) == 10:
        value += "T23:59:59-07:00"
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp lacks timezone")
    return result.astimezone(UTC)


def temporal(value, inherited=None):
    """Reject completed future results even beneath a prospective file label."""
    inherited = inherited or {}
    if isinstance(value, dict):
        labels = [
            str(value.get(k, "")).upper()
            for k in ("fact_state", "period_role", "state", "status", "record_origin")
        ]
        completed = any(
            label
            in {
                "ACTUAL",
                "SYNTHETIC_ACTUAL",
                "COMPLETE",
                "COMPLETED",
                "CLOSED",
                "COMPLETE_SYNTHETIC",
                "CLOSED_SYNTHETIC",
                "SYNTHETIC_CALIBRATION",
                "SYNTHETIC_HISTORICAL_CASE",
            }
            for label in labels
        )
        forecast = any(
            any(
                word in label
                for word in (
                    "FORECAST",
                    "SCENARIO",
                    "COMMITMENT",
                    "OPTION",
                    "SIMULATION",
                    "PROVISIONAL",
                )
            )
            for label in labels
        )
        context = {**inherited, **value}
        if not forecast:
            forecast = any(
                any(
                    word in str(inherited.get(k, "")).upper()
                    for word in (
                        "FORECAST",
                        "SCENARIO",
                        "COMMITMENT",
                        "OPTION",
                        "SIMULATION",
                        "PROVISIONAL",
                    )
                )
                for k in ("fact_state", "period_role", "temporal_mode")
            )
        for key in ("available_at", "available_on"):
            if value.get(key) and instant(str(value[key])) > instant(CUTOFF):
                raise ValueError("record unavailable at planning cutoff")
        dates = []
        for key in (
            "date",
            "event_date",
            "effective_period_end",
            "posting_date",
            "invoice_date",
            "due_date",
            "clearing_date",
            "received_on",
            "ordered_on",
            "conditional_service_month",
        ):
            if value.get(key):
                dates.append(str(value[key]))
        if value.get("year") and value.get("month") not in (None, "", 0, "0"):
            year, month = int(value["year"]), int(value["month"])
            if not 1 <= month <= 12:
                raise ValueError("invalid dated record month")
            dates.append(f"{year}-{month:02}-{calendar.monthrange(year, month)[1]:02}")
        if value.get("year") and value.get("month") in (None, ""):
            dates.append(f"{int(value['year'])}-12-31")
        elif value.get("year") and value.get("month") in (0, "0"):
            dates.append(f"{int(value['year'])}-01-01")
        for day in dates:
            if instant(day) > instant(CUTOFF) and (completed or not forecast):
                raise ValueError("future completed or unclassified record")
        for child in value.values():
            temporal(child, context)
    elif isinstance(value, list):
        for child in value:
            temporal(child, inherited)
    elif isinstance(value, str) and value.startswith(("{", "[")):
        try:
            child = json.loads(value)
        except json.JSONDecodeError:
            return
        temporal(child, inherited)


def preservation(root=ROOT):
    source = json.loads((root / "industrial/planning/source/preservation.json").read_text())
    for item in source["artifacts"]:
        path = root / item["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"accepted v1 member changed: {item['path']}")
    return len(source["artifacts"])


def source_fingerprint(root=ROOT):
    """Bind acceptance to exact planning implementation and policy bytes."""
    paths = list((root / "industrial/planning").glob("*.py"))
    paths += list((root / "industrial/planning/source").glob("*.json"))
    paths += [root / "industrial/planning/browser_template.html", root / "uv.lock"]
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
    }


def acceptance_binding(output, root=ROOT):
    catalog = json.loads((root / "industrial/planning/source/participant_catalog.json").read_text())
    prefix = "industrial/generated/planning/"
    paths = [
        entry["path"][len(prefix) :]
        for entry in catalog["artifacts"]
        if entry["path"].startswith(prefix) and entry["path"] != prefix + "acceptance.json"
    ]
    return {
        "source_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "source_inputs": source_fingerprint(root),
        "output_sha256": {
            name: hashlib.sha256((Path(output) / name).read_bytes()).hexdigest()
            for name in sorted(paths)
        },
    }


def verify_acceptance_binding(output, root=ROOT):
    report = json.loads((Path(output) / "acceptance.json").read_text())
    if report.get("status") != "PASS" or report.get("binding") != acceptance_binding(output, root):
        raise ValueError("Acceptance is stale or altered; rebuild the complete planning pipeline")
    return report


def producer_pins(output, root=ROOT):
    """Do not rebind stale producer outputs to a newer acceptance report."""
    output = Path(output)
    count = 0
    for scope in ("operations", "capital", "forecast"):
        manifest = json.loads((output / scope / "manifest.json").read_text())
        if scope in {"operations", "capital"}:
            for key in ("operating_plan", "capital_options"):
                policy = json.loads((root / f"industrial/planning/source/{key}.json").read_text())
                digest = hashlib.sha256(
                    json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                if manifest["effective_input_sha256"].get(key) != digest:
                    raise ValueError(f"noncanonical effective producer policy: {scope} {key}")
                count += 1
        for name, expected in manifest.get("dependency_sha256", {}).items():
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
                raise ValueError(f"stale producer source: {scope} {name}")
            count += 1
        artifacts = manifest["artifacts"]
        if isinstance(artifacts, list):
            artifacts = {item["path"]: item["sha256"] for item in artifacts}
        for name, expected in artifacts.items():
            if hashlib.sha256((output / scope / name).read_bytes()).hexdigest() != expected:
                raise ValueError(f"producer output changed: {scope} {name}")
            count += 1
        if scope == "forecast":
            policy = json.loads((root / "industrial/planning/source/forecast.json").read_text())
            if (
                hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()
                != manifest["source_sha256"]
            ):
                raise ValueError("forecast effective policy differs from canonical release policy")
    enterprise = json.loads((output / "enterprise/summary.json").read_text())
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if (
        enterprise.get("source_revision") != revision
        or enterprise["identity"].get("legacy_metadata", {}).get("source_revision") != revision
    ):
        raise ValueError("Enterprise and legacy execution must bind to the same source revision")
    for name, expected in enterprise["identity"]["source_inputs"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"stale enterprise input: {name}")
        count += 1
    return count


def csv_rows(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def journals(rows):
    totals = defaultdict(D)
    balances = defaultdict(D)
    cash = defaultdict(D)
    for row in rows:
        amount = D(row["signed_usd"])
        if D(row["debit_usd"]) - D(row["credit_usd"]) != amount:
            raise ValueError("exported posting sign discrepancy")
        scenario, entity, year = row["scenario"], row["entity"], int(row["year"])
        month = int(row["month"])
        totals[(scenario, entity, row["journal_id"])] += amount
        balances[(scenario, entity, year, str(row["account"]))] += amount
        if str(row["account"]) == "1000":
            cash[(scenario, entity, year, month)] += amount
    if any(totals.values()):
        raise ValueError("exported journal is unbalanced")
    return {"journal_count": len(totals), "balances": dict(balances), "cash": dict(cash)}


def trial_balances(rows):
    totals = defaultdict(D)
    for row in rows:
        scenario = row["scenario"]
        entity = row.get("entity", row.get("legal_entity"))
        key = (scenario, entity, row["year"], row.get("month", "12"))
        amount = D(row["signed_usd"])
        totals[key] += amount
        if (
            "debit_balance_usd" in row
            and D(row["debit_balance_usd"]) - D(row["credit_balance_usd"]) != amount
        ):
            raise ValueError("trial balance debit/credit discrepancy")
    if any(totals.values()):
        raise ValueError("exported trial balance does not balance")
    return len(totals)


def forecast_statements(journal_rows, statement_rows, tb_rows):
    """Recompute every exported monthly statement and TB from posting lines."""
    grouped = defaultdict(list)
    for row in journal_rows:
        grouped[(row["scenario"], row["entity"], int(row["year"]))].append(row)
    statements = {
        (r["scenario"], r["entity"], int(r["year"]), int(r["month"])): r for r in statement_rows
    }
    tb = {
        (r["scenario"], r["entity"], int(r["year"]), int(r["month"]), str(r["account"])): D(
            r["signed_usd"]
        )
        for r in tb_rows
    }
    if len(statements) != len(statement_rows) or len(tb) != len(tb_rows):
        raise ValueError("duplicate exported statement or trial balance")
    count = 0
    for (scenario, entity, year), rows in grouped.items():
        balance = defaultdict(D)
        account_types = {str(r["account"]): r["account_type"] for r in rows}
        opening = sum(
            (
                D(r["signed_usd"])
                for r in rows
                if int(r["month"]) == 0 and str(r["account"]) == "1000"
            ),
            D(0),
        )
        for row in rows:
            if int(row["month"]) == 0:
                balance[str(row["account"])] += D(row["signed_usd"])
        cf_ytd = defaultdict(D)
        for month in range(1, 13):
            current = [r for r in rows if int(r["month"]) == month]
            cf = defaultdict(D)
            month_pnl = defaultdict(D)
            for r in current:
                amount = D(r["signed_usd"])
                balance[str(r["account"])] += amount
                month_pnl[r["account_type"]] += amount
                if str(r["account"]) == "1000":
                    cf[r["cash_flow"]] += amount
                    cf_ytd[r["cash_flow"]] += amount
            types = defaultdict(D)
            for account, amount in balance.items():
                kind = account_types[account]
                if kind in ("intercompany", "current_settlement"):
                    kind = "asset" if amount >= 0 else "liability"
                types[kind] += amount
            income = -types["revenue"] - types["expense"]
            expected = {
                "assets_usd": types["asset"],
                "liabilities_usd": -types["liability"],
                "equity_including_current_income_usd": -types["equity"] + income,
                "net_income_ytd_usd": income,
                "net_income_usd": -month_pnl["revenue"] - month_pnl["expense"],
                "revenue_usd": -month_pnl["revenue"],
                "opening_year_cash_usd": opening,
                "ending_cash_usd": balance["1000"],
                "operating_cash_flow_usd": cf["OPERATING"],
                "investing_cash_flow_usd": cf["INVESTING"],
                "financing_cash_flow_usd": cf["FINANCING"],
                "operating_cash_flow_ytd_usd": cf_ytd["OPERATING"],
                "investing_cash_flow_ytd_usd": cf_ytd["INVESTING"],
                "financing_cash_flow_ytd_usd": cf_ytd["FINANCING"],
            }
            key = (scenario, entity, year, month)
            if key not in statements:
                raise ValueError("missing forecast month")
            for name, value in expected.items():
                if D(statements[key][name]) != value:
                    raise ValueError(f"exported statement differs from journal: {key} {name}")
            if types["asset"] != -types["liability"] - types["equity"] + income:
                raise ValueError("independently recomputed balance sheet fails")
            if opening + sum(cf_ytd.values()) != balance["1000"]:
                raise ValueError("independently recomputed cash flow fails")
            expected_accounts = {a for a, v in balance.items() if v}
            actual_accounts = {k[-1] for k in tb if k[:4] == key and tb[k]}
            if expected_accounts != actual_accounts:
                raise ValueError("trial balance account population differs from ledger")
            for account in expected_accounts:
                if tb[(*key, account)] != balance[account]:
                    raise ValueError("trial balance amount differs from journal")
            count += 1
    if count != len(statement_rows):
        raise ValueError("unexpected statement scope")
    return count


def bank_reconciliations(rows):
    for row in rows:

        def n(name, record=row):
            return D(record[name])

        bank = n("opening_bank_cash_usd") + n("cleared_receipts_usd") - n("cleared_payments_usd")
        book = (
            n("closing_bank_cash_usd")
            + n("deposits_in_transit_usd")
            - n("outstanding_payments_usd")
        )
        if bank != n("closing_bank_cash_usd") or book != n("ledger_cash_usd"):
            raise ValueError("exported bank reconciliation failed")
    return len(rows)


def enterprise_exports(directory):
    """Rebuild legal, eliminated and unit statements from four-decimal postings."""
    directory = Path(directory)
    rows = csv_rows(directory / "enterprise_journal.csv")
    statements = csv_rows(directory / "enterprise_monthly_statements.csv")
    units = csv_rows(directory / "unit_monthly_trial_balances.csv")
    unit_statements = csv_rows(directory / "unit_monthly_statements.csv")
    legal = csv_rows(directory / "legal_monthly_trial_balances.csv")
    types = {r["account"]: r["account_type"] for r in rows}
    types["UNIT_CLEARING"] = "intercompany"
    expected_statements = {}
    expected_legal = {}
    expected_units = {}
    expected_unit_statements = {}

    def calculate(balance, current, net_clearing=False, settlement_books=None):
        totals = defaultdict(D)
        for account, value in balance.items():
            kind = types[account]
            if kind == "current_settlement" and settlement_books is not None:
                # Tax balances of distinct legal taxpayers have no assumed
                # enforceable offset right. Classify each taxpayer separately.
                for book in settlement_books.values():
                    amount = book.get(account, D(0))
                    totals["asset" if amount >= 0 else "liability"] += amount
                continue
            if kind in {"intercompany", "current_settlement"}:
                kind = (
                    "asset"
                    if (net_clearing and kind == "intercompany") or value >= 0
                    else "liability"
                )
            totals[kind] += value
        pnl = defaultdict(D)
        cf = defaultdict(D)
        for row in current:
            value = D(row["signed_usd"])
            pnl[row["account_type"]] += value
            if row["account"] == "1000":
                cf[row["cash_flow"]] += value
        result = {
            "assets_usd": totals["asset"],
            "liabilities_usd": -totals["liability"],
            "equity_usd": -totals["equity"] - totals["revenue"] - totals["expense"],
            "revenue_usd": -pnl["revenue"],
            "expense_usd": pnl["expense"],
            "net_income_usd": -pnl["revenue"] - pnl["expense"],
            "opening_cash_usd": balance.get("1000", D(0)) - sum(cf.values()),
            "ending_cash_usd": balance.get("1000", D(0)),
            "operating_cash_flow_usd": cf["OPERATING"],
            "investing_cash_flow_usd": cf["INVESTING"],
            "financing_cash_flow_usd": cf["FINANCING"],
            "opening_or_noncash_cash_bridge_usd": cf["NONCASH_OR_OPENING"],
        }
        if result["assets_usd"] != result["liabilities_usd"] + result["equity_usd"]:
            raise ValueError("recomputed enterprise balance sheet failed")
        return result

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["scenario"], int(row["year"]), int(row["month"]))].append(row)
    for scenario in sorted({r["scenario"] for r in rows}):
        balances = defaultdict(lambda: defaultdict(D))
        unit_balances = defaultdict(lambda: defaultdict(D))
        scopes = sorted({r["entity"] for r in rows if r["scenario"] == scenario})
        unit_scopes = sorted({r["unit"] for r in units if r["scenario"] == scenario})
        for year in range(2026, 2032):
            for month in range(13):
                current = grouped[(scenario, year, month)]
                for row in current:
                    amount = D(row["signed_usd"])
                    balances[row["entity"]][row["account"]] += amount
                    unit_balances[row["unit"]][row["account"]] += amount
                if month == 0:
                    continue
                consolidated = defaultdict(D)
                for entity in scopes:
                    key = (scenario, entity, str(year), str(month))
                    expected_statements[key] = calculate(
                        balances[entity], [r for r in current if r["entity"] == entity]
                    )
                    for account, value in balances[entity].items():
                        consolidated[account] += value
                        if value:
                            expected_legal[(*key, account)] = value
                expected_statements[(scenario, "CONSOLIDATED", str(year), str(month))] = calculate(
                    consolidated, current, settlement_books=balances
                )
                unit_sums = defaultdict(D)
                for unit in unit_scopes:
                    balance = dict(unit_balances[unit])
                    balance["UNIT_CLEARING"] = -sum(balance.values())
                    key = (scenario, unit, str(year), str(month))
                    expected_unit_statements[key] = calculate(
                        balance, [r for r in current if r["unit"] == unit], True
                    )
                    for account, value in balance.items():
                        unit_sums[account] += value
                        if value:
                            expected_units[(*key, account)] = value
                if any(unit_sums[a] != consolidated[a] for a in set(unit_sums) | set(consolidated)):
                    raise ValueError("unit account aggregation differs from consolidation")
                for field, total in expected_statements[
                    (scenario, "CONSOLIDATED", str(year), str(month))
                ].items():
                    if (
                        sum(
                            expected_unit_statements[(scenario, u, str(year), str(month))][field]
                            for u in unit_scopes
                        )
                        != total
                    ):
                        raise ValueError(
                            f"unit aggregation differs: {scenario} {year}/{month} {field}: "
                            + str(
                                sum(
                                    expected_unit_statements[(scenario, u, str(year), str(month))][
                                        field
                                    ]
                                    for u in unit_scopes
                                )
                            )
                            + " != "
                            + str(total)
                        )
    for table, expected, scope in (
        (statements, expected_statements, "entity"),
        (unit_statements, expected_unit_statements, "unit"),
    ):
        seen = set()
        for row in table:
            key = (row["scenario"], row[scope], row["year"], row["month"])
            if key in seen or key not in expected:
                raise ValueError("duplicate or unexpected enterprise statement")
            seen.add(key)
            for field, value in expected[key].items():
                if D(row[field]) != value:
                    raise ValueError(f"enterprise statement differs from journal: {key} {field}")
        if seen != set(expected):
            raise ValueError("missing enterprise statements")
    for table, expected, scope in (
        (legal, expected_legal, "entity"),
        (units, expected_units, "unit"),
    ):
        actual = {
            (r["scenario"], r[scope], r["year"], r["month"], r["account"]): D(r["signed_usd"])
            for r in table
        }
        if len(actual) != len(table) or actual != expected:
            raise ValueError("enterprise trial balance differs from journal")
    return {
        "monthly_statements": len(statements),
        "unit_monthly_statements": len(unit_statements),
        "legal_account_balances": len(legal),
        "unit_account_balances": len(units),
    }


def validate(output=ROOT / "industrial/generated/planning"):
    output = Path(output)
    checks = {"preserved_v1_members": preservation()}
    checks["producer_input_and_output_pins"] = producer_pins(output)
    for name in ("forecast", "enterprise"):
        path = output / name / ("journal.csv" if name == "forecast" else "enterprise_journal.csv")
        if not path.exists():
            raise ValueError(f"missing {name} journal export")
        result = journals(csv_rows(path))
        checks[name + "_journals"] = result["journal_count"]
        if name == "forecast":
            checks["forecast_monthly_statement_recalculations"] = forecast_statements(
                csv_rows(path),
                csv_rows(output / name / "monthly_statements.csv"),
                csv_rows(output / name / "trial_balances.csv"),
            )
        candidates = [
            output / name / f for f in ("trial_balances.csv", "legal_monthly_trial_balances.csv")
        ]
        for candidate in candidates:
            if candidate.exists():
                checks[name + "_" + candidate.stem] = trial_balances(csv_rows(candidate))
    checks["enterprise_recalculations"] = enterprise_exports(output / "enterprise")
    bank = output / "transactions/bank_reconciliations.csv"
    if not bank.exists():
        raise ValueError("missing linked bank/book evidence")
    checks["bank_reconciliations"] = bank_reconciliations(csv_rows(bank))
    statements = {
        (r["scenario"], r["entity"], r["year"], r["month"]): D(r["ending_cash_usd"])
        for r in csv_rows(output / "forecast/monthly_statements.csv")
    }
    for r in csv_rows(bank):
        if (
            D(r["ledger_cash_usd"])
            != statements[(r["scenario"], r["entity"], r["year"], r["month"])]
        ):
            raise ValueError("bank evidence differs from forecast statement cash")
    for file in sorted(output.rglob("*.csv")):
        if any(p.startswith(".") for p in file.relative_to(output).parts):
            raise ValueError("hidden planning dataset")
        for row in csv_rows(file):
            temporal(row, {"period_role": "FORECAST", "fact_state": "FORECAST"})
    report = {
        "status": "PASS",
        "checks": checks,
        "cutoff": CUTOFF,
        "scope": (
            "Independent exported journal, trial balance, bank timing, preservation and "
            "temporal checks; producer suites add physical, valuation, funding and "
            "accounting controls."
        ),
        "binding": acceptance_binding(output),
    }
    (output / "acceptance.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report
