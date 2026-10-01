"""Preserve native source legs and independently reperform derived closes/eliminations.

No source-prefix exclusion authorizes an adjustment. Statutory/source-provider
verification remains a separate prerequisite; this checks its native interfaces.
"""

from collections import Counter, defaultdict
from decimal import Decimal as D

Q = D(".0001")
FIELDS = (
    "scenario",
    "entity",
    "year",
    "month",
    "account",
    "account_type",
    "signed_usd",
    "source_id",
    "source_type",
    "description",
    "cash_flow",
    "segment",
)
SCENARIOS = ("base", "downside", "expansion")


def signature(row):
    return tuple(
        D(row[k]).quantize(Q)
        if k == "signed_usd"
        else int(row[k])
        if k in {"year", "month"}
        else row[k]
        for k in FIELDS
    )


def equal(actual, expected, label):
    a, e = Counter(map(signature, actual)), Counter(map(signature, expected))
    if a != e:
        raise ValueError(
            f"{label} differs: added={list((a - e).items())[:2]}; "
            f"removed={list((e - a).items())[:2]}"
        )
    return sum(a.values())


def derived_row(
    scenario,
    entity,
    year,
    month,
    account,
    kind,
    value,
    source,
    source_type,
    description,
    segment="CORPORATE",
):
    return dict(
        scenario=scenario,
        entity=entity,
        year=year,
        month=month,
        account=account,
        account_type=kind,
        signed_usd=str(value),
        source_id=source,
        source_type=source_type,
        description=description,
        cash_flow="NONCASH_OR_OPENING",
        segment=segment,
    )


def verify_closes(rows):
    """Reconstruct each closing from prior-year source P&L, never closing output."""
    pnl = defaultdict(lambda: defaultdict(D))
    types = {}
    for row in rows:
        if row["source_type"] == "ANNUAL_CLOSE":
            continue
        if row["account_type"] in {"expense", "revenue"}:
            key = row["scenario"], row["entity"], int(row["year"]), row["segment"]
            pnl[key][row["account"]] += D(row["signed_usd"])
            types[row["account"]] = row["account_type"]
    expected = []
    for (scenario, entity, year, segment), accounts in pnl.items():
        if not 2026 <= year < 2031:
            continue
        lines = [(a, -v, types[a]) for a, v in accounts.items() if v]
        equity = -sum((v for _, v, _ in lines), D(0))
        if equity:
            lines.append(("3100", equity, "equity"))
        for account, value, kind in lines:
            expected.append(
                derived_row(
                    scenario,
                    entity,
                    year + 1,
                    0,
                    account,
                    kind,
                    value,
                    f"CLOSE-{year}-{segment}",
                    "ANNUAL_CLOSE",
                    "Close prior-year P&L to retained earnings within its operating segment",
                    segment,
                )
            )
    actual = [r for r in rows if r["source_type"] == "ANNUAL_CLOSE"]
    return equal(actual, expected, "Source-derived annual close")


def verify_eliminations(rows):
    """Reperform reciprocal legal current accounts, including opening movements."""
    movements = defaultdict(lambda: defaultdict(D))
    for row in rows:
        if row["entity"] != "ELIM" and row["account"] in {"1150", "2150"}:
            key = row["scenario"], int(row["year"]), max(int(row["month"]), 1)
            movements[key][row["account"]] += D(row["signed_usd"])
    expected = []
    for (scenario, year, month), accounts in movements.items():
        if sum(accounts.values(), D(0)):
            raise ValueError("Legal payer/beneficiary current accounts are not reciprocal")
        for account, value in accounts.items():
            if value:
                expected.append(
                    derived_row(
                        scenario,
                        "ELIM",
                        year,
                        month,
                        account,
                        "asset" if account == "1150" else "liability",
                        -value,
                        "1150",
                        "BALANCE_ELIMINATION",
                        "Eliminate reciprocal ownership or intercompany balances",
                    )
                )
    actual = [r for r in rows if r["entity"] == "ELIM" and r["source_id"] == "1150"]
    return equal(actual, expected, "Reciprocal current-account elimination")


def verify_2026_payer_delta(predecessor, successor, settlement):
    """Historical change: source-paid RWH tax allocated to PS plus August payroll."""
    source = {}
    for row in settlement["rows"]:
        if int(row["year"]) != 2026 or row["source_group"] != "RWH_PS":
            continue
        key = row["scenario"], int(row["month"])
        if key in source or row["taxpayer"] != "PS":
            raise ValueError("Duplicate or wrong-taxpayer historical settlement workpaper")
        source[key] = D(row["gross_source_tax_cash_paid_usd"])
    if set(source) != {(s, m) for s in SCENARIOS for m in range(1, 13)}:
        raise ValueError("Incomplete historical payer settlement population")
    for s in SCENARIOS:
        if sum(source[s, m] for m in range(1, 13)) != D("131343"):
            raise ValueError("Historical native RWH source tax cash changed")

    def population(rows):
        result = defaultdict(D)
        seen = set()
        for r in rows:
            if r["entity"] == "ELIM" and r["source_id"] == "1150" and int(r["year"]) == 2026:
                key = r["scenario"], int(r["month"]), r["account"]
                if key in seen or r["account"] not in {"1150", "2150"}:
                    raise ValueError("Duplicate or malformed historical elimination")
                seen.add(key)
                result[key] += D(r["signed_usd"])
        return result

    before, after = population(predecessor), population(successor)
    for s in SCENARIOS:
        for m in range(1, 13):
            amount = source[s, m] + (D(78125) if m == 8 else D(0))
            for account, sign in [("1150", -1), ("2150", 1)]:
                if after[s, m, account] - before[s, m, account] != sign * amount:
                    raise ValueError(
                        "Historical elimination differs from source tax payer and payroll bridge"
                    )
    return dict(
        rwh_paid_for_ps_usd="131343.0000",
        august_payroll_paid_for_ps_usd="78125.0000",
        total_incremental_current_account_usd="209468.0000",
        scenarios=3,
    )


def verify(predecessor, successor, settlement, *, reviewed_native_rows=None):
    """Wire with original predecessor, final journal, settlement and final seed journal.

    reviewed_native_rows must be the separately built prestatutory seed using the
    final revised native forecast, never a selection copied from successor.
    """

    def native(row):
        return row["source_id"].startswith("LEGAL-")

    old = [r for r in predecessor if native(r) and int(r["year"]) == 2026]
    actual = [r for r in successor if native(r) and int(r["year"]) == 2026]
    if not old:
        raise ValueError("Missing original native historical source population")
    report = dict(
        native_2026_preserved_legs=equal(actual, old, "Original 2026 native/PPA population"),
        annual_close_legs=verify_closes(successor),
        elimination_legs=verify_eliminations(successor),
        historical_payer_bridge=verify_2026_payer_delta(predecessor, successor, settlement),
        prior_9778_scope="DATED_PRE_STATUTORY_ALL_PERIOD_BOUNDARY;NOT_A_CURRENT_IMMUTABLE_FORECAST_TOTAL",
    )
    if reviewed_native_rows is None:
        report["forecast_native_scope"] = "NOT_RUN;REVISED_PRESTATUTORY_NATIVE_SEED_REQUIRED"
    else:
        expected = [r for r in reviewed_native_rows if native(r) and int(r["year"]) > 2026]
        actual = [r for r in successor if native(r) and int(r["year"]) > 2026]
        if not expected:
            raise ValueError("Missing reviewed native forecast source population")
        report["forecast_native_preserved_legs"] = equal(
            actual, expected, "Reviewed native forecast population"
        )
        report["forecast_native_scope"] = "EXACT_REVISED_NATIVE_SEED;NOT_PRIOR_TAX_CASH_PLAN"
    return report
