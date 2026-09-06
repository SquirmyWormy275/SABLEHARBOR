"""Versioned enterprise planning integration; legacy and industrial scopes stay explicit."""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import subprocess
import tempfile
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from industrial.planning.legacy_adapter import canonical_bytes, legacy_snapshot

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).parent / "source/enterprise.json"
OUT = ROOT / "industrial/generated/planning/enterprise"
D = Decimal
Q = D("0.0001")


def amount(value):
    return D(str(value)).quantize(Q, rounding=ROUND_HALF_UP)


def money(value):
    return format(amount(value), ".4f")


def read_csv(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("status\nNO_ROWS\n")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class Books:
    def __init__(self, scenario, policy, account_types):
        self.scenario, self.policy = scenario, policy
        self.types = dict(account_types)
        self.rows = []
        self.balances = defaultdict(lambda: defaultdict(D))
        self.sequence = 0

    def unit(self, entity, segment):
        if entity == "ELIM":
            return "eliminations"
        if entity in {"ARU", "BST"}:
            return "american-resource-utility"
        if entity in {"PS", "RWH"}:
            return "pale-sun"
        return self.policy["segment_mapping"].get(segment, "corporate")

    def post(
        self,
        entity,
        year,
        month,
        lines,
        source,
        description,
        kind="DERIVED_PLANNING",
        segment="CORPORATE",
    ):
        """Lines are (account, signed amount[, cash-flow class, segment])."""
        if sum(amount(line[1]) for line in lines):
            raise ValueError(f"Unbalanced enterprise journal: {source}")
        self.sequence += 1
        journal = f"ENT-{self.scenario}-{self.sequence:07}"
        for line in lines:
            account, value = line[:2]
            value = amount(value)
            if not value:
                continue
            if account not in self.types:
                raise ValueError(f"Unclassified account {account}")
            flow = line[2] if len(line) > 2 else "NONCASH_OR_OPENING"
            assigned_segment = line[3] if len(line) > 3 else segment
            self.balances[entity][account] += value
            self.rows.append(
                {
                    "scenario": self.scenario,
                    "entity": entity,
                    "year": year,
                    "month": month,
                    "journal_id": journal,
                    "line_no": len(self.rows) + 1,
                    "account": account,
                    "account_type": self.types[account],
                    "segment": assigned_segment,
                    "unit": self.unit(entity, assigned_segment),
                    "debit_usd": money(max(value, 0)),
                    "credit_usd": money(max(-value, 0)),
                    "signed_usd": money(value),
                    "source_id": source,
                    "source_type": kind,
                    "description": description,
                    "cash_flow": flow,
                    "available_at": self.policy["knowledge_cutoff"],
                    "created_on": self.policy["created_on"],
                    "record_origin": "PUBLIC_SYNTHETIC_PLANNING_MODEL",
                    "effective_period_end": (
                        f"{year}-01-01"
                        if month == 0
                        else f"{year}-{month:02}-{calendar.monthrange(year, month)[1]:02}"
                    ),
                    "fact_state": "CONDITIONAL_FORECAST"
                    if year > 2026
                    else "SYNTHETIC_SUCCESSOR_RECONSTRUCTION",
                    "period_role": "MANAGEMENT_FORECAST"
                    if year > 2026 or month > 8
                    else "SYNTHETIC_CALIBRATION",
                }
            )

    def close_year(self, year):
        # Preserve operating-segment histories when closing legal-book P&L.
        grouped = defaultdict(lambda: defaultdict(D))
        for row in self.rows:
            if row["account_type"] in {"revenue", "expense"}:
                grouped[(row["entity"], row["segment"])][row["account"]] += amount(
                    row["signed_usd"]
                )
        for (entity, segment), balances in sorted(grouped.items()):
            lines = [(account, -value) for account, value in balances.items() if value]
            if lines:
                lines.append(("3100", -sum(value for _, value in lines)))
                self.post(
                    entity,
                    year,
                    0,
                    lines,
                    f"CLOSE-{year - 1}-{segment}",
                    "Close prior-year P&L to retained earnings within its operating segment",
                    "ANNUAL_CLOSE",
                    segment=segment,
                )


def account_contract(legacy_rows, forecast_rows):
    from industrial.tools.build_financials import ACCOUNTS

    types = {key: value[1] for key, value in ACCOUNTS.items()}
    types.update(
        {
            "3100": "equity",
            "1180": "intercompany",
            "1181": "intercompany",
            "SHARED_AR": "asset",
            "SHARED_AP": "liability",
            "SHARED_REV": "revenue",
            "SHARED_EXP": "expense",
            "CORE_UNPAID": "liability",
            "CORE_AR": "asset",
            "CORE_AP": "liability",
            "CORE_PPE": "asset",
            "CORE_ACCUM": "asset",
            "CORE_REVENUE": "revenue",
            "CORE_OPEX": "expense",
            "CORE_DDA": "expense",
            "CORE_INTEREST": "expense",
            "UNIT_CLEARING": "intercompany",
        }
    )
    for row in legacy_rows:
        key = "1000" if row["account"] == "1000" else "LEG_" + row["account"]
        types[key] = "expense" if row["account_type"] == "other_expense" else row["account_type"]
    for row in forecast_rows:
        if row["account"] not in types:
            types[row["account"]] = row["account_type"]
    for child in ("SHIH", "PS", "ARU", "RWH", "BST"):
        types["INV_" + child] = "asset"
    return types


def load_anchor():
    from industrial.tools.build_financials import build

    with tempfile.TemporaryDirectory(prefix="enterprise-anchor-") as directory:
        output = Path(directory)
        build(output=output)
        rows = read_csv(output / "aru_2026_journal.csv") + read_csv(
            output / "red_wash_2026_journal.csv"
        )
        return rows


def legacy_core(books, snapshot):
    opening = defaultdict(D)
    retained = []
    bridge = []
    groups = defaultdict(list)
    for row in snapshot["rows"]:
        keep = row["entity"] == "SHI" and row["book"] == "PRIMARY_USD"
        bridge.append(
            {
                **row,
                "bridge_action": "RETAIN_CORE"
                if keep
                else "REMOVE_SUPERSEDED_INDUSTRIAL_OR_ELIMINATION",
                "successor_scope": "SHI operating segments"
                if keep
                else "Accepted industrial anchor and forecasts replace this entire scope",
            }
        )
        if not keep:
            continue
        account = "1000" if row["account"] == "1000" else "LEG_" + row["account"]
        if row["entry_date"] < "2026-01-01":
            opening[account] += amount(row["signed_usd"])
        else:
            retained.append(row)
            groups[row["journal_id"]].append((row, account))
    previous_income = sum(v for a, v in opening.items() if books.types[a] in {"revenue", "expense"})
    opening = {a: v for a, v in opening.items() if books.types[a] not in {"revenue", "expense"}}
    opening["3100"] = previous_income
    books.post(
        "SHI",
        2026,
        0,
        list(opening.items()),
        "LEGACY-OPEN-2026",
        "Selected legacy SHI opening; prior P&L closed without changing equity",
        "LEGACY_ADAPTER",
    )
    return retained, bridge, groups


def import_core_month(books, groups, month):
    for pairs in groups.values():
        row = pairs[0][0]
        if int(row["entry_date"][5:7]) != month:
            continue
        source = row["source_type"]
        flow = "FINANCING" if source in {"debt_draw", "debt_repayment"} else "OPERATING"
        if source == "vendor_payment":
            flow = "INVESTING"  # accepted causal vendor payments acquire fixed assets
        lines = [
            (a, r["signed_usd"], flow if a == "1000" else "NONCASH_OR_OPENING", r["segment"])
            for r, a in pairs
        ]
        books.post(
            "SHI", 2026, month, lines, row["journal_id"], row["description"], "LEGACY_ADAPTER"
        )


def base_group_snapshots(rows, scenario):
    selected = [r for r in rows if r.get("scenario", scenario) == scenario]
    result = {}
    for year in sorted({int(r["year"]) for r in selected}):
        for entity in ("ARU_GROUP", "RWH_PS"):
            group_rows = [r for r in selected if int(r["year"]) == year and r["entity"] == entity]
            balances = defaultdict(D)
            for month in range(13):
                for row in group_rows:
                    if int(row["month"]) == month:
                        balances[row["account"]] += amount(row["signed_usd"])
                result[(year, month, entity)] = (
                    dict(balances),
                    [r for r in group_rows if 0 < int(r["month"]) <= month],
                )
    return result


def allocate_legal(
    group,
    balances,
    rows,
    policy,
    financial_source,
    bst_capital,
    prior_bst_retained,
    platform_fee,
    prior_bst_ar=0,
):
    """Apply accepted ownership; use an explicit reciprocal treasury financing account."""
    from industrial.tools.build_financials import ACCOUNTS, usd

    if group == "RWH_PS":
        rw = dict(balances)
        rw["5100"] = rw.get("5100", D(0)) - platform_fee
        rw["5150"] = rw.get("5150", D(0)) + platform_fee
        capital = -rw.get("3000", D(0))
        ps = {"INV_RWH": capital, "3000": -capital, "4100": -platform_fee, "5100": platform_fee}
        return {"RWH": rw, "PS": ps}
    owners = {
        "1000": "cash",
        "1100": "receivables",
        "1200": "inventory",
        "1300": "prepaids",
        "1400": "owned_ppe",
        "1410": "owned_ppe",
        "1490": "owned_ppe",
        "1500": "leased_equipment",
        "1590": "leased_equipment",
        "2000": "payables",
        "2100": "operating_accruals",
        "2600": "leased_equipment",
    }
    ratios = {
        a: D(str(policy["bst_balance_allocation_pct"][key])) / 100 for a, key in owners.items()
    }
    ratios.update(
        {
            "2200": D(policy["bst_environment_reserve"])
            / financial_source["transaction"]["environment_reserve"],
            "2300": D(policy["bst_claim_reserve"])
            / financial_source["transaction"]["claim_reserve"],
            "1800": D(policy["bst_deferred_tax_asset"]) / 587500,
        }
    )
    bst = {
        a: D(usd(value * ratios.get(a, 0)))
        for a, value in balances.items()
        if a in ratios or ACCOUNTS.get(a, ("", ""))[1] in {"asset", "liability"}
    }
    for account, (_, kind) in ACCOUNTS.items():
        if kind in {"revenue", "expense"}:
            bst[account] = sum(
                (
                    amount(r["signed_usd"])
                    for r in rows
                    if r["account"] == account and r.get("segment") == "BST"
                ),
                D(0),
            )
    for account, key in (
        ("5300", "central_depreciation_to_bst_pct"),
        ("5400", "central_financing_cost_to_bst_pct"),
    ):
        bst[account] = D(usd(balances.get(account, 0) * D(str(policy[key])) / 100))
    bst["5500"] = bst["5501"] = D(0)
    retention = sum(
        (
            amount(r["signed_usd"])
            for r in rows
            if r["account"] == "5700"
            and r["source_id"] in {"RETENTION-POOL", "FINAL-RETENTION-SERVICE"}
        ),
        D(0),
    )
    bst["5700"] = D(
        usd(
            retention
            * financial_source["transaction"]["retention_allocations"]["Seth Kettering"]
            / financial_source["transaction"]["retention_pool"]
        )
    )
    # Invoice/receipt ownership is carried on the actual source segment.
    bst["1150"] = prior_bst_ar + sum(
        (
            amount(r["signed_usd"])
            for r in rows
            if r["account"] == "1150" and r.get("segment") == "BST"
        ),
        D(0),
    )
    bst["3000"] = -bst_capital
    bst["3100"] = prior_bst_retained
    bst["1180"] = -sum(bst.values())
    aru = {a: value - bst.get(a, 0) for a, value in balances.items()}
    aru["3000"] = balances.get("3000", D(0))
    aru["3100"] = balances.get("3100", D(0)) - prior_bst_retained
    aru["INV_BST"] = bst_capital
    aru["1180"] = -bst["1180"]
    if sum(aru.values()) or sum(bst.values()):
        raise ValueError("Legal allocation does not balance")
    return {"ARU": aru, "BST": bst}


def flow_components(previous, current, types):
    """Indirect management cash flow from exact allocated balances, excluding opening/close."""
    delta = {a: current.get(a, 0) - previous.get(a, 0) for a in set(previous) | set(current)}
    income = -sum(v for a, v in delta.items() if types[a] in {"revenue", "expense"})
    fixed = {"1400", "1410", "1490", "1500", "1590", "1600"}
    financing = {"2400", "2410", "2500", "2600", "3000", "3100", "3200", "1180"}
    investment = {a for a in delta if a.startswith("INV_") or a == "1810"}
    operating = income - sum(
        v
        for a, v in delta.items()
        if types[a] not in {"revenue", "expense"}
        and a not in fixed | financing | investment | {"1000"}
    )
    operating -= delta.get("1490", 0) + delta.get("1590", 0)
    investing = -delta.get("1400", 0) - delta.get("1410", 0) - sum(delta[a] for a in investment)
    finance = -sum(delta.get(a, 0) for a in financing)
    # A new financed lease adds property and an obligation without receiving cash.
    finance -= delta.get("1500", 0)
    difference = delta.get("1000", 0) - operating - investing - finance
    if difference:
        raise ValueError(f"Unexplained legal cash-flow difference: {difference}")
    return {
        "OPERATING": amount(operating),
        "INVESTING": amount(investing),
        "FINANCING": amount(finance),
    }, amount(difference)


def post_snapshot(books, entity, year, month, current, previous, initial=None):
    delta = {a: current.get(a, 0) - previous.get(a, 0) for a in set(current) | set(previous)}
    if month == 0:
        flows = {"NONCASH_OR_OPENING": delta.get("1000", D(0))}
        difference = D(0)
    else:
        flow_previous = initial if initial is not None else previous
        flows, difference = flow_components(flow_previous, current, books.types)
        if initial is not None:
            flows["INVESTING"] += initial.get("1000", D(0))
    lines = [(a, value) for a, value in sorted(delta.items()) if a != "1000"]
    lines += [("1000", value, flow) for flow, value in flows.items()]
    books.post(
        entity,
        year,
        month,
        lines,
        f"LEGAL-{entity}-{year}-{month:02}",
        "Monthly allocated legal book; group source journals and declared ownership control",
        "LEGAL_ALLOCATION",
    )
    return difference


def core_plan(books, retained):
    base = defaultdict(D)
    for row in retained:
        kind = "expense" if row["account_type"] == "other_expense" else row["account_type"]
        if kind in {"revenue", "expense"} and row["account"] not in {"6300", "7100"}:
            base[(int(row["entry_date"][5:7]), row["segment"], kind)] += amount(row["signed_usd"])
    net_ppe = books.balances["SHI"].get("LEG_1500", 0) + books.balances["SHI"].get("LEG_1590", 0)
    return base, net_ppe


def project_core_month(books, base, opening_ppe, year, month):
    config, scenario = books.policy["core"], books.policy["scenarios"][books.scenario]
    elapsed = year - 2026
    if year == 2027 and month == 1:
        for account in ("LEG_1100", "LEG_2000", "LEG_2100"):
            balance = books.balances["SHI"].get(account, D(0))
            if balance:
                books.post(
                    "SHI",
                    year,
                    month,
                    [(account, -balance), ("1000", balance, "OPERATING")],
                    f"CORE-OPEN-SETTLE-{account}",
                    "Settle legacy opening operating receivables/payables in January",
                    "OPENING_WORKING_CAPITAL_SETTLEMENT",
                )
    for (base_month, segment, kind), original in base.items():
        if base_month != month:
            continue
        growth = scenario[
            "core_revenue_growth_pct" if kind == "revenue" else "core_cost_growth_pct"
        ]
        value = amount(abs(original) * (1 + D(str(growth)) / 100) ** elapsed)
        if kind == "revenue":
            lines = [("CORE_AR", value), ("CORE_REVENUE", -value)]
        else:
            lines = [("CORE_OPEX", value), ("CORE_AP", -value)]
        books.post(
            "SHI",
            year,
            month,
            lines,
            f"CORE-{kind}-{segment}-{year}-{month}",
            "Legacy segment envelope projected by explicit annual driver",
            segment=segment,
        )
    # One-month settlement uses the previous month's opening receivables/payables.
    this_month = [
        r
        for r in books.rows
        if r["entity"] == "SHI" and int(r["year"]) == year and int(r["month"]) == month
    ]
    new_ar = sum((amount(r["signed_usd"]) for r in this_month if r["account"] == "CORE_AR"), D(0))
    new_ap = -sum((amount(r["signed_usd"]) for r in this_month if r["account"] == "CORE_AP"), D(0))
    collect = books.balances["SHI"]["CORE_AR"] - new_ar
    pay = -books.balances["SHI"]["CORE_AP"] - new_ap
    if collect:
        books.post(
            "SHI",
            year,
            month,
            [("1000", collect, "OPERATING"), ("CORE_AR", -collect)],
            "CORE-COLLECTION",
            "Collect prior-month modeled invoices",
        )
    if pay:
        books.post(
            "SHI",
            year,
            month,
            [("CORE_AP", pay), ("1000", -pay, "OPERATING")],
            "CORE-PAYMENT",
            "Pay prior-month modeled operating invoices",
        )
    capital = amount(D(config["annual_sustaining_capital_usd"]) / 12)
    books.post(
        "SHI",
        year,
        month,
        [("CORE_PPE", capital), ("1000", -capital, "INVESTING")],
        "CORE-SUSTAIN",
        "Conditional sustaining fixed-asset purchases",
    )
    elapsed_months = (year - 2027) * 12 + month
    existing_dda = min(
        amount(opening_ppe / config["existing_net_ppe_remaining_life_months"]),
        max(
            opening_ppe
            - amount(opening_ppe / config["existing_net_ppe_remaining_life_months"])
            * (elapsed_months - 1),
            0,
        ),
    )
    new_dda = amount(
        capital
        * min(elapsed_months - 1, config["new_capital_life_months"])
        / config["new_capital_life_months"]
    )
    books.post(
        "SHI",
        year,
        month,
        [("CORE_DDA", existing_dda + new_dda), ("CORE_ACCUM", -existing_dda - new_dda)],
        "CORE-DEPRECIATION",
        "Owned asset depreciation; goodwill remains nonamortizing",
    )
    debt = max(-books.balances["SHI"].get("LEG_2500", 0), 0)
    interest = amount(debt * D(str(config["debt_interest_pct"])) / 1200)
    principal = min(debt, amount(D(config["annual_debt_principal_usd"]) / 12))
    books.post(
        "SHI",
        year,
        month,
        [("CORE_INTEREST", interest), ("1000", -interest, "OPERATING")],
        "CORE-INTEREST",
        "Conditional parent debt-rate assumption",
    )
    books.post(
        "SHI",
        year,
        month,
        [("LEG_2500", principal), ("1000", -principal, "FINANCING")],
        "CORE-PRINCIPAL",
        "Conditional parent debt amortization",
    )


def owner_payment(
    books, parent, child, year, month, value, child_already_posted=False, kind="EQUITY_TRANSFER"
):
    value = amount(value)
    if not value:
        return
    source = f"FUND-{parent}-{child}-{year}-{month:02}"
    books.post(
        parent,
        year,
        month,
        [("INV_" + child, value), ("1000", -value, "INVESTING")],
        source,
        "Reciprocal ownership funding",
        kind,
    )
    if not child_already_posted:
        books.post(
            child,
            year,
            month,
            [("1000", value, "FINANCING"), ("3000", -value)],
            source,
            "Reciprocal ownership funding",
            kind,
        )
    if kind == "EXTERNAL_ACQUISITION":
        return
    books.post(
        "ELIM",
        year,
        month,
        [("1000", value, "INVESTING"), ("1000", -value, "FINANCING")],
        source,
        "Remove internal funding from consolidated cash-flow categories",
        "CASH_FLOW_ELIMINATION",
    )


def eliminate_balances(books, year, month, previous):
    targets = {}
    for child, parent in books.policy["owners"].items():
        investment = books.balances[parent].get("INV_" + child, D(0))
        capital = -books.balances[child].get("3000", D(0))
        if investment != capital:
            raise ValueError(f"Ownership mismatch {parent}/{child}: {investment} != {capital}")
        targets[f"OWN-{child}"] = {"INV_" + child: -investment, "3000": capital}
    for asset, liability in (("1150", "2150"), ("SHARED_AR", "SHARED_AP")):
        ar = sum(books.balances[e].get(asset, 0) for e in books.policy["legal_entities"])
        ap = sum(books.balances[e].get(liability, 0) for e in books.policy["legal_entities"])
        if ar + ap:
            raise ValueError(f"Reciprocal intercompany balance mismatch {asset}: {ar} + {ap}")
        targets[asset] = {asset: -ar, liability: -ap}
    for key, target in targets.items():
        prior = previous.get(key, {})
        lines = [(a, v - prior.get(a, 0)) for a, v in target.items()]
        books.post(
            "ELIM",
            year,
            month,
            lines,
            key,
            "Eliminate reciprocal ownership or intercompany balances",
            "BALANCE_ELIMINATION",
        )
    previous.update(targets)


def statement(books, rows, entity, year, month):
    balances = (
        books.balances[entity]
        if entity != "CONSOLIDATED"
        else {a: sum(book.get(a, 0) for book in books.balances.values()) for a in books.types}
    )
    selected = [
        r
        for r in rows
        if (entity == "CONSOLIDATED" or r["entity"] == entity)
        and int(r["year"]) == year
        and int(r["month"]) == month
    ]
    pnl = defaultdict(D)
    flows = defaultdict(D)
    for row in selected:
        value = amount(row["signed_usd"])
        if row["account_type"] in {"revenue", "expense"}:
            pnl[row["account_type"]] += value
        if row["account"] == "1000":
            flows[row["cash_flow"]] += value
    assets = sum(
        v
        for a, v in balances.items()
        if books.types[a] == "asset"
        or (books.types[a] in {"intercompany", "current_settlement"} and v > 0)
    )
    liabilities = -sum(
        v
        for a, v in balances.items()
        if books.types[a] == "liability"
        or (books.types[a] in {"intercompany", "current_settlement"} and v < 0)
    )
    if entity == "CONSOLIDATED":
        # No tax-group or right-of-offset election is assumed. Gross external
        # tax receivables/payables by legal taxpayer instead of netting account2700.
        for account, kind in books.types.items():
            if kind != "current_settlement":
                continue
            net = balances.get(account, D(0))
            gross_asset = sum(
                max(book.get(account, D(0)), D(0)) for book in books.balances.values()
            )
            gross_liability = -sum(
                min(book.get(account, D(0)), D(0)) for book in books.balances.values()
            )
            assets += gross_asset - max(net, D(0))
            liabilities += gross_liability + min(net, D(0))
    equity = -sum(
        v for a, v in balances.items() if books.types[a] in {"equity", "revenue", "expense"}
    )
    if assets != liabilities + equity:
        raise ValueError(f"Enterprise accounting equation fails {entity} {year}/{month}")
    change = sum(flows.values())
    closing_cash = balances.get("1000", D(0))
    return {
        "scenario": books.scenario,
        "entity": entity,
        "year": year,
        "month": month,
        "revenue_usd": money(-pnl["revenue"]),
        "expense_usd": money(pnl["expense"]),
        "net_income_usd": money(-pnl["revenue"] - pnl["expense"]),
        "assets_usd": money(assets),
        "liabilities_usd": money(liabilities),
        "equity_usd": money(equity),
        "opening_cash_usd": money(closing_cash - change),
        "ending_cash_usd": money(closing_cash),
        "operating_cash_flow_usd": money(flows["OPERATING"]),
        "investing_cash_flow_usd": money(flows["INVESTING"]),
        "financing_cash_flow_usd": money(flows["FINANCING"]),
        "opening_or_noncash_cash_bridge_usd": money(flows["NONCASH_OR_OPENING"]),
        "fact_state": "CONDITIONAL_FORECAST"
        if year > 2026
        else "SYNTHETIC_SUCCESSOR_RECONSTRUCTION",
    }


def snapshot_rows(result, anchor_rows, scenario, types):
    snapshots = base_group_snapshots(anchor_rows, scenario)
    journal = [r for r in result["journal_rows"] if r["scenario"] == scenario]
    grouped = defaultdict(dict)
    for row in result["trial_balance_rows"]:
        if row["scenario"] == scenario:
            grouped[(int(row["year"]), int(row["month"]), row["entity"])][row["account"]] = amount(
                row["signed_usd"]
            )
    supplied_openings = defaultdict(dict)
    for row in result["opening_rows"]:
        if row["scenario"] == scenario:
            supplied_openings[(int(row["year"]), row["entity"])][row["account"]] = amount(
                row["signed_usd"]
            )
    for year in range(2027, 2032):
        for entity in ("ARU_GROUP", "RWH_PS"):
            previous = dict(snapshots[(year - 1, 12, entity)][0])
            profit_accounts = [a for a in previous if types[a] in {"revenue", "expense"}]
            previous["3100"] = previous.get("3100", D(0)) + sum(
                previous[a] for a in profit_accounts
            )
            for account in profit_accounts:
                previous[account] = D(0)
            supplied = supplied_openings[(year, entity)]
            if any(previous.get(a, 0) != supplied.get(a, 0) for a in set(previous) | set(supplied)):
                raise ValueError(
                    f"Forecast opening differs from accepted carried balance: {entity}/{year}"
                )
            snapshots[(year, 0, entity)] = (previous, [])
            for month in range(1, 13):
                key = (year, month, entity)
                if key not in grouped:
                    raise ValueError(
                        f"Missing complete monthly aggregate forecast trial balance: {key}"
                    )
                cumulative = [
                    r
                    for r in journal
                    if r["entity"] == entity
                    and int(r["year"]) == year
                    and 0 < int(r["month"]) <= month
                ]
                snapshots[key] = (grouped[key], cumulative)
    return snapshots


def member_funding(books, year, month, subsidiary_cash, used, reserved, funding):
    policy = books.policy
    limit = D(
        policy["core"]["member_equity_2026_limit_usd"]
        if year == 2026
        else policy["scenarios"][books.scenario]["member_equity_annual_limit_usd"]
    )
    if subsidiary_cash > reserved - used["subsidiary"]:
        raise ValueError("Subsidiary draws exceed reserved enterprise equity envelope")
    if subsidiary_cash:
        books.post(
            "SHI",
            year,
            month,
            [("1000", subsidiary_cash, "FINANCING"), ("3000", -subsidiary_cash)],
            f"MEMBER-INDUSTRIAL-{year}-{month}",
            "Conditional member equity earmarked for subsidiary funding",
            "MEMBER_EQUITY",
        )
        used["subsidiary"] += subsidiary_cash
    floor = D(policy["core"]["minimum_cash_usd"])
    opening_arrears = -books.balances["SHI"].get("CORE_UNPAID", D(0))
    required = max(floor + opening_arrears - books.balances["SHI"]["1000"], D(0))
    core_available = max(limit - reserved - used["core"], D(0))
    received = min(required, core_available)
    if received:
        books.post(
            "SHI",
            year,
            month,
            [("1000", received, "FINANCING"), ("3000", -received)],
            f"MEMBER-CORE-{year}-{month}",
            "Finite conditional member support for retained Core operations",
            "MEMBER_EQUITY",
        )
        used["core"] += received
    gap = required - received
    new_deferral = max(floor - books.balances["SHI"]["1000"], D(0))
    if new_deferral:
        paid_operating = -sum(
            amount(r["signed_usd"])
            for r in books.rows
            if r["entity"] == "SHI"
            and int(r["year"]) == year
            and int(r["month"]) == month
            and r["account"] == "1000"
            and r["cash_flow"] == "OPERATING"
            and amount(r["signed_usd"]) < 0
        )
        if new_deferral > paid_operating:
            raise ValueError("Core funding gap exceeds identified deferrable operating payments")
        books.post(
            "SHI",
            year,
            month,
            [("1000", new_deferral, "OPERATING"), ("CORE_UNPAID", -new_deferral)],
            f"CORE-UNPAID-{year}-{month}",
            "Reverse unfunded modeled operating payment; obligation remains unpaid",
            "UNFUNDED_PAYMENT_DEFERRAL",
        )
    arrears = -books.balances["SHI"].get("CORE_UNPAID", D(0))
    repayment = min(arrears, max(books.balances["SHI"]["1000"] - floor, D(0)))
    if repayment:
        books.post(
            "SHI",
            year,
            month,
            [("CORE_UNPAID", repayment), ("1000", -repayment, "OPERATING")],
            f"CORE-ARREARS-PAID-{year}-{month}",
            "Settle previously deferred operating payment from available cash",
        )
    funding.append(
        {
            "scenario": books.scenario,
            "entity": "SHI",
            "year": year,
            "month": month,
            "required_equity_usd": money(required + subsidiary_cash),
            "available_equity_usd": money(received + subsidiary_cash),
            "funding_gap_usd": money(gap),
            "member_annual_limit_usd": money(limit),
            "member_draws_year_to_date_usd": money(used["core"] + used["subsidiary"]),
            "reserved_subsidiary_capacity_remaining_usd": money(reserved - used["subsidiary"]),
            "unpaid_operating_obligations_usd": money(-books.balances["SHI"].get("CORE_UNPAID", 0)),
            "opening_unpaid_operating_obligations_usd": money(opening_arrears),
            "new_payment_deferral_usd": money(new_deferral),
            "arrears_paid_usd": money(repayment),
            "fact_state": "CONDITIONAL_FORECAST",
            "feasibility": "FUNDING_GAP"
            if gap or arrears > repayment
            else "WITHIN_CONDITIONAL_ENVELOPE",
        }
    )


def shared_services(books, year, month):
    if year < 2027:
        return
    config = books.policy["shared_services"]
    growth = (1 + D(str(config["annual_growth_pct"])) / 100) ** (year - 2027)
    for entity, key in (("ARU", "annual_aru_fee_usd"), ("PS", "annual_ps_fee_usd")):
        fee = amount(D(config[key]) * growth / 12)
        source = f"ENTERPRISE-SERVICE-{entity}-{year}-{month}"
        books.post(
            "SHI",
            year,
            month,
            [("SHARED_AR", fee), ("SHARED_REV", -fee)],
            source,
            "Derived enterprise support allocation",
        )
        books.post(
            entity,
            year,
            month,
            [("SHARED_EXP", fee), ("SHARED_AP", -fee)],
            source,
            "Reciprocal enterprise support allocation",
        )
        books.post(
            "ELIM",
            year,
            month,
            [("SHARED_REV", fee), ("SHARED_EXP", -fee)],
            source,
            "Eliminate enterprise support fee",
            "PNL_ELIMINATION",
        )
        if month % 3 == 0:
            due = -books.balances[entity]["SHARED_AP"]
            payment = min(due, max(books.balances[entity].get("1000", 0) - D(2000000), D(0)))
            if payment:
                books.post(
                    entity,
                    year,
                    month,
                    [("SHARED_AP", payment), ("1000", -payment, "OPERATING")],
                    source,
                    "Settle support fee from available legal-book cash",
                )
                books.post(
                    "SHI",
                    year,
                    month,
                    [("1000", payment, "OPERATING"), ("SHARED_AR", -payment)],
                    source,
                    "Receive reciprocal support payment",
                )


def annual_statements(monthly):
    grouped = defaultdict(list)
    for row in monthly:
        grouped[(row["scenario"], row["entity"], row["year"])].append(row)
    result = []
    flow_fields = [
        "revenue_usd",
        "expense_usd",
        "net_income_usd",
        "operating_cash_flow_usd",
        "investing_cash_flow_usd",
        "financing_cash_flow_usd",
        "opening_or_noncash_cash_bridge_usd",
    ]
    for _key, rows in sorted(grouped.items()):
        rows.sort(key=lambda r: r["month"])
        out = dict(rows[-1])
        out.pop("month")
        out["opening_cash_usd"] = rows[0]["opening_cash_usd"]
        for key in flow_fields:
            out[key] = money(sum(amount(row[key]) for row in rows))
        result.append(out)
    return result


def trial_and_unit_rows(books, year, month):
    legal = []
    for entity, balances in sorted(books.balances.items()):
        for account, value in sorted(balances.items()):
            if value:
                legal.append(
                    {
                        "scenario": books.scenario,
                        "entity": entity,
                        "year": year,
                        "month": month,
                        "account": account,
                        "account_type": books.types[account],
                        "signed_usd": money(value),
                        "view_type": "CONSOLIDATION_ELIMINATION_BOOK"
                        if entity == "ELIM"
                        else "ALLOCATED_LEGAL_MANAGEMENT_BOOK",
                    }
                )
    units = defaultdict(lambda: defaultdict(D))
    for row in books.rows:
        units[row["unit"]][row["account"]] += amount(row["signed_usd"])
    extracted = []
    for unit in books.policy["units"]:
        balances = units[unit]
        balances["UNIT_CLEARING"] = -sum(balances.values())
        for account, value in sorted(balances.items()):
            if value:
                extracted.append(
                    {
                        "scenario": books.scenario,
                        "unit": unit,
                        "year": year,
                        "month": month,
                        "account": account,
                        "account_type": books.types[account],
                        "signed_usd": money(value),
                        "view_type": "OPERATING_SEGMENT_WITH_EXPLICIT_REPORTING_CLEARING",
                    }
                )
    if sum(amount(r["signed_usd"]) for r in extracted if r["account"] == "UNIT_CLEARING"):
        raise ValueError("Unit reporting clearing does not eliminate")
    for account in books.types:
        unit_value = sum(amount(r["signed_usd"]) for r in extracted if r["account"] == account)
        book_value = sum(book.get(account, 0) for book in books.balances.values())
        if unit_value != book_value:
            raise ValueError(f"Unit extracts differ from consolidation: {account}")
    return legal, extracted


def unit_statements(books, extracted, year, month):
    """Operating units use signed net reporting clearing for exact line-wise aggregation."""
    from types import SimpleNamespace

    balances = defaultdict(dict)
    for row in extracted:
        balances[row["unit"]][row["account"]] = amount(row["signed_usd"])
    types = dict(books.types)
    # Signed settlement and reporting clearing is included in net unit assets;
    # it is not a new external payable or a fabricated bank account.
    for account, kind in types.items():
        if kind == "intercompany":
            types[account] = "asset"
    view = SimpleNamespace(balances=balances, types=types, scenario=books.scenario)
    rows = [
        {**row, "entity": row["unit"]}
        for row in books.rows
        if int(row["year"]) == year and int(row["month"]) == month
    ]
    result = []
    for unit in books.policy["units"]:
        row = statement(view, rows, unit, year, month)
        row["unit"] = unit
        row["view_type"] = "OPERATING_SEGMENT_SIGNED_NET_REPORTING_CLEARING"
        result.append(row)
    return result


def build(output=OUT, forecast_output=None, forecast_result=None, source=None, legacy_result=None):
    """Build the six-entity successor with explicit legacy selection and finite funding."""
    output = Path(output)
    policy = json.loads(SOURCE.read_text()) if source is None else source
    if (
        policy["core"]["receivable_collection_months"],
        policy["core"]["operating_payable_months"],
    ) != (1, 1):
        raise ValueError("Core settlement currently requires one-month receivables/payables")
    if forecast_result is None and forecast_output is not None:
        directory = Path(forecast_output)
        forecast_result = {
            key: read_csv(directory / name)
            for key, name in {
                "journal_rows": "journal.csv",
                "trial_balance_rows": "trial_balances.csv",
                "opening_rows": "opening_balances.csv",
                "funding_rows": "funding.csv",
            }.items()
        }
    if forecast_result is None:
        from industrial.planning.forecast import build as forecast_build

        forecast_result = forecast_build(output=OUT.parent / "forecast")
    snapshot = legacy_result or legacy_snapshot(policy["seed"])
    anchor = load_anchor()
    financial_source = json.loads((ROOT / "industrial/source/finance.json").read_text())
    legal_policy = financial_source["legal_book_policy"]
    types = account_contract(snapshot["rows"], forecast_result["journal_rows"])
    all_journals, monthly, legal_rows, unit_rows, funding, bridge, cashflow_bridges = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    scenario_summaries = {}
    unit_monthly = []
    tax_bridges = []
    for scenario in policy["scenarios"]:
        books = Books(scenario, policy, types)
        retained, selected_bridge, core_groups = legacy_core(books, snapshot)
        if not bridge:
            bridge = selected_bridge
        snapshots = snapshot_rows(forecast_result, anchor, scenario, types)
        opening_aru = snapshots[(2026, 0, "ARU_GROUP")][0]
        empty_capital = allocate_legal(
            "ARU_GROUP", opening_aru, [], legal_policy, financial_source, D(0), D(0), D(0)
        )
        bst_capital = sum(
            v for a, v in empty_capital["BST"].items() if types[a] in {"asset", "liability"}
        )
        base_previous, elim_previous = {}, {}
        bst_retained, bst_ar = D(0), D(0)
        core_base, core_ppe = {}, D(0)
        previous_ps_fee, previous_ic_revenue = D(0), D(0)
        for year in range(2026, 2032):
            if year > 2026:
                books.close_year(year)
                bst_retained = base_previous["BST"].get("3100", D(0)) + sum(
                    v for a, v in base_previous["BST"].items() if types[a] in {"revenue", "expense"}
                )
                bst_ar = base_previous["BST"].get("1150", D(0))
                for values in base_previous.values():
                    values["3100"] = values.get("3100", D(0)) + sum(
                        v for a, v in values.items() if types[a] in {"revenue", "expense"}
                    )
                    for account in list(values):
                        if types[account] in {"revenue", "expense"}:
                            values[account] = D(0)
            previous_ps_fee = previous_ic_revenue = D(0)
            used = {"core": D(0), "subsidiary": D(0)}
            if year == 2026:
                aru_capital = -snapshots[(2026, 12, "ARU_GROUP")][0]["3000"]
                mine_delta = (
                    -snapshots[(2026, 12, "RWH_PS")][0]["3000"]
                    + snapshots[(2026, 0, "RWH_PS")][0]["3000"]
                )
                reserved = (
                    aru_capital
                    + mine_delta
                    + D(financial_source["transaction"]["transaction_expense"])
                )
            else:
                reserved = D(policy["scenarios"][scenario]["reserved_subsidiary_equity_annual_usd"])
            for month in range(13):
                if month == 0 and year > 2026:
                    continue
                if month:
                    if year == 2026:
                        import_core_month(books, core_groups, month)
                    else:
                        project_core_month(books, core_base, core_ppe, year, month)
                targets = {}
                initial_targets = {}
                ps_fee = D(0)
                for group in ("ARU_GROUP", "RWH_PS"):
                    if group == "ARU_GROUP" and year == 2026 and month == 0:
                        continue
                    balances, raw = snapshots[(year, month, group)]
                    if group == "RWH_PS":
                        if year == 2026:
                            ps_fee = amount(
                                D(legal_policy["pale_sun_annual_platform_service_fee"]) * month / 12
                            )
                        else:
                            ga = sum(
                                (
                                    amount(r["signed_usd"])
                                    for r in raw
                                    if r.get("source_type") == "MINE_PLATFORM_SITE_GA"
                                    and r["account"] == "5100"
                                ),
                                D(0),
                            )
                            ps_fee = amount(
                                ga
                                * D(legal_policy["pale_sun_annual_platform_service_fee"])
                                / D(2800000)
                            )
                    allocation = allocate_legal(
                        group,
                        balances,
                        raw,
                        legal_policy,
                        financial_source,
                        bst_capital,
                        bst_retained,
                        ps_fee if group == "RWH_PS" else D(0),
                        bst_ar,
                    )
                    targets.update(allocation)
                    if year == 2026 and month == 1 and group == "ARU_GROUP":
                        initial_targets = allocate_legal(
                            group,
                            opening_aru,
                            [],
                            legal_policy,
                            financial_source,
                            bst_capital,
                            D(0),
                            D(0),
                        )
                subsidiary_cash = D(0)
                for entity, current in targets.items():
                    old = base_previous.get(entity, {})
                    post_snapshot(
                        books, entity, year, month, current, old, initial_targets.get(entity)
                    )
                    base_previous[entity] = current
                if year > 2026:
                    fee_cash = -sum(
                        amount(r["signed_usd"])
                        for r in snapshots[(year, month, "ARU_GROUP")][1]
                        if int(r["month"]) == month
                        and r["account"] == "1000"
                        and r.get("source_type") == "PAYMENT_DEBT_ISSUANCE_PAYMENT"
                    )
                    books.post(
                        "ARU",
                        year,
                        month,
                        [("1000", fee_cash, "OPERATING"), ("1000", -fee_cash, "FINANCING")],
                        "DEBT-FEE-CASHFLOW",
                        "Classify paid issuance fees as financing",
                        "CASH_FLOW_RECLASSIFICATION",
                    )
                if year == 2026 and month == 0:
                    historical_basis = -targets["PS"]["3000"]
                    books.post(
                        "SHIH",
                        year,
                        month,
                        [("INV_PS", historical_basis), ("3000", -historical_basis)],
                        "OPEN-INDUSTRIAL-BASIS",
                        "Reconstruct omitted historical investment with reciprocal capital",
                    )
                    books.post(
                        "SHI",
                        year,
                        month,
                        [("INV_SHIH", historical_basis), ("3000", -historical_basis)],
                        "OPEN-MEMBER-BASIS",
                        "Explicit additional pre-2026 member capital supports accepted mine basis",
                    )
                    eliminate_balances(books, year, month, elim_previous)
                    continue
                for child in ("ARU", "PS"):
                    required_investment = -books.balances[child].get("3000", D(0))
                    already = books.balances["SHIH"].get("INV_" + child, D(0))
                    value = required_investment - already
                    if value < 0:
                        raise ValueError(
                            "Unmodeled capital distribution requires an explicit bridge"
                        )
                    if value:
                        owner_payment(books, "SHI", "SHIH", year, month, value)
                        acquisition = (
                            -opening_aru["3000"]
                            if child == "ARU" and year == 2026 and month == 1
                            else D(0)
                        )
                        if acquisition:
                            owner_payment(
                                books,
                                "SHIH",
                                child,
                                year,
                                month,
                                acquisition,
                                child_already_posted=True,
                                kind="EXTERNAL_ACQUISITION",
                            )
                        owner_payment(
                            books,
                            "SHIH",
                            child,
                            year,
                            month,
                            value - acquisition,
                            child_already_posted=True,
                        )
                        # PS also passes cash through to the mine in the allocated base view.
                        if child == "PS":
                            books.post(
                                "ELIM",
                                year,
                                month,
                                [("1000", value, "INVESTING"), ("1000", -value, "FINANCING")],
                                "PS-RWH-FLOW",
                                "Eliminate platform-to-mine funding cash-flow categories",
                                "CASH_FLOW_ELIMINATION",
                            )
                        subsidiary_cash += value
                if year == 2026 and month == 1:
                    fees = D(financial_source["transaction"]["transaction_expense"])
                    owner_payment(books, "SHI", "SHIH", year, month, fees)
                    books.post(
                        "SHIH",
                        year,
                        month,
                        [("5800", fees), ("1000", -fees, "OPERATING")],
                        "ARU-ACQUISITION-FEES",
                        "Buyer transaction expense remains outside goodwill",
                    )
                    subsidiary_cash += fees
                    net_external_financing = (
                        D(financial_source["transaction"]["new_debt"])
                        - D(financial_source["transaction"]["existing_term_revolver_refinance"])
                        - D(financial_source["transaction"]["debt_issuance_cost"])
                    )
                    books.post(
                        "ELIM",
                        year,
                        month,
                        [
                            ("1000", -net_external_financing, "INVESTING"),
                            ("1000", net_external_financing, "FINANCING"),
                        ],
                        "ACQUISITION-CASHFLOW-PRESENTATION",
                        (
                            "Present debt, refinance and issuance "
                            "cash separately from stock-investment cash"
                        ),
                        "CASH_FLOW_RECLASSIFICATION",
                    )
                    cashflow_bridges.append(
                        {
                            "scenario": scenario,
                            "year": year,
                            "month": month,
                            "stock_consideration_usd": money(
                                financial_source["transaction"]["buyer_consideration"]
                            ),
                            "cash_acquired_usd": money(opening_aru["1000"]),
                            "acquisition_investing_cash_usd": money(
                                opening_aru["1000"]
                                - D(financial_source["transaction"]["buyer_consideration"])
                            ),
                            "parent_acquisition_capital_usd": money(-opening_aru["3000"]),
                            "transaction_operating_expense_usd": money(fees),
                            "net_external_financing_usd": money(net_external_financing),
                            "net_cash_change_usd": "0.0000",
                            "source": "Accepted acquisition sources and uses",
                        }
                    )
                ic_total = -snapshots[(year, month, "ARU_GROUP")][0].get("4100", D(0))
                ic = ic_total - previous_ic_revenue
                fee = ps_fee - previous_ps_fee
                books.post(
                    "ELIM",
                    year,
                    month,
                    [("4100", ic + fee), ("5150", -ic - fee)],
                    f"IC-PNL-{year}-{month}",
                    "Eliminate mine logistics and platform service revenue/expense once",
                    "PNL_ELIMINATION",
                )
                previous_ic_revenue, previous_ps_fee = ic_total, ps_fee
                shared_services(books, year, month)
                member_funding(books, year, month, subsidiary_cash, used, reserved, funding)
                eliminate_balances(books, year, month, elim_previous)
                for entity in [*policy["legal_entities"], "ELIM", "CONSOLIDATED"]:
                    row = statement(books, books.rows, entity, year, month)
                    monthly.append(row)
                    if entity in policy["legal_entities"]:
                        selected = [
                            r
                            for r in books.rows
                            if r["entity"] == entity
                            and int(r["year"]) == year
                            and int(r["month"]) == month
                        ]
                        fee_expense = sum(
                            amount(r["signed_usd"])
                            for r in selected
                            if r["account"] == "SHARED_EXP"
                        )
                        fee_revenue = -sum(
                            amount(r["signed_usd"])
                            for r in selected
                            if r["account"] == "SHARED_REV"
                        )
                        tax_bridges.append(
                            {
                                "scenario": scenario,
                                "entity": entity,
                                "year": year,
                                "month": month,
                                "preallocation_net_income_usd": money(
                                    amount(row["net_income_usd"]) + fee_expense - fee_revenue
                                ),
                                "book_only_fee_expense_usd": money(fee_expense),
                                "book_only_fee_revenue_usd": money(fee_revenue),
                                "postallocation_net_income_usd": row["net_income_usd"],
                                "current_tax_change_from_allocation_usd": "0.0000",
                                "deferred_tax_change_from_allocation_usd": "0.0000",
                                "tax_treatment": policy["shared_services"]["tax_treatment"],
                            }
                        )
                legal, units = trial_and_unit_rows(books, year, month)
                legal_rows.extend(legal)
                unit_rows.extend(units)
                unit_monthly.extend(unit_statements(books, units, year, month))
                if year == 2026 and month == 12:
                    core_base, core_ppe = core_plan(books, retained)
        all_journals.extend(books.rows)
        scenario_summaries[scenario] = {
            "journal_lines": len(books.rows),
            "closing_cash_usd": money(sum(v.get("1000", 0) for v in books.balances.values())),
            "core_unpaid_usd": money(-books.balances["SHI"].get("CORE_UNPAID", 0)),
        }
    # Preserve each subsidiary's independently calculated funding shortfalls.
    for row in forecast_result["funding_rows"]:
        funding.append({**row, "scope": "INDUSTRIAL_SUBSIDIARY_CONDITIONAL_ENVELOPE"})
    for scenario, details in scenario_summaries.items():
        gaps = defaultdict(D)
        for row in funding:
            if row["scenario"] == scenario:
                gaps[int(row["year"]), int(row["month"])] += amount(row["funding_gap_usd"])
        details["months_with_any_funding_gap"] = sum(value > 0 for value in gaps.values())
        details["maximum_total_monthly_funding_gap_usd"] = money(max(gaps.values(), default=D(0)))
        details["financial_feasibility"] = (
            "MONTHLY_FUNDING_SHORTFALLS" if any(gaps.values()) else "WITHIN_CONDITIONAL_ENVELOPES"
        )
    annual = annual_statements(monthly)
    output.mkdir(parents=True, exist_ok=True)
    tables = {
        "enterprise_journal": all_journals,
        "enterprise_monthly_statements": monthly,
        "enterprise_annual_statements": annual,
        "legal_monthly_trial_balances": legal_rows,
        "unit_monthly_trial_balances": unit_rows,
        "unit_monthly_statements": unit_monthly,
        "unit_annual_statements": annual_statements(unit_monthly),
        "enterprise_funding": funding,
        "enterprise_tax_allocation_bridge": tax_bridges,
        "legacy_replacement_bridge": bridge,
        "acquisition_cashflow_bridge": cashflow_bridges,
    }
    paths = {}
    for name, rows in tables.items():
        for row in rows:
            row.setdefault("available_at", policy["knowledge_cutoff"])
            row.setdefault("created_on", policy["created_on"])
            row.setdefault("record_origin", "PUBLIC_SYNTHETIC_PLANNING_MODEL")
            if "year" in row:
                year = int(row["year"])
                row.setdefault(
                    "fact_state",
                    "CONDITIONAL_FORECAST" if year > 2026 else "SYNTHETIC_SUCCESSOR_RECONSTRUCTION",
                )
                row.setdefault(
                    "period_role",
                    "MANAGEMENT_FORECAST" if year > 2026 else "SYNTHETIC_CALIBRATION_AND_FORECAST",
                )
        path = output / (name + ".csv")
        write_csv(path, rows)
        paths[name] = str(path)
    inputs = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(Path(__file__).parent.rglob("*.py"))
        if "tests" not in p.parts
    }
    inputs.update(
        {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((Path(__file__).parent / "source").glob("*.json"))
        }
    )
    for relative in policy["canonical_sources"]:
        path = ROOT / relative
        inputs[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    for relative in ("industrial/tools/build_financials.py",):
        inputs[relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    identity = {
        "model_id": policy["model_id"],
        "schema_version": policy["schema_version"],
        "seed": policy["seed"],
        "scenarios": list(policy["scenarios"]),
        "source_policy_sha256": hashlib.sha256(canonical_bytes(policy)).hexdigest(),
        "legacy_metadata": snapshot["metadata"],
        "source_inputs": inputs,
        "forecast_rows_sha256": hashlib.sha256(
            canonical_bytes(
                [
                    {key: str(value) for key, value in row.items()}
                    for row in forecast_result["journal_rows"]
                ]
            )
        ).hexdigest(),
    }
    run_id = hashlib.sha256(canonical_bytes(identity)).hexdigest()
    summary = {
        "status": "PASS",
        "run_id": run_id,
        "source_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "identity": identity,
        "scenarios": scenario_summaries,
        "legal_entities": policy["legal_entities"],
        "elimination_book": "ELIM",
        "monthly_statements": len(monthly),
        "unit_extract_reconciliation": "EXACT_BY_ACCOUNT",
        "legacy_engine_executed": True,
        "raw_legacy_database_included": False,
        "limitations": [
            policy["legacy_adapter"]["calibration_boundary"],
            policy["core"]["tax_boundary"],
            (
                "Legal cash flows are allocated management views, including explicit reciprocal "
                "cash-pool financing. These are not observed statutory bank statements."
            ),
            (
                "Funding and shared-service charges are conditional planning assumptions. "
                "Unpaid operating obligations and subsidiary funding gaps remain visible."
            ),
        ],
    }
    (output / "summary.json").write_bytes(canonical_bytes(summary))
    paths["summary"] = str(output / "summary.json")
    return {
        "summary": summary,
        "journal_rows": all_journals,
        "monthly_rows": monthly,
        "annual_rows": annual,
        "legal_trial_balance_rows": legal_rows,
        "funding_rows": funding,
        "unit_rows": unit_rows,
        "unit_monthly_rows": unit_monthly,
        "unit_annual_rows": annual_statements(unit_monthly),
        "paths": paths,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    print(json.dumps(build(output=args.output)["summary"], indent=2))
