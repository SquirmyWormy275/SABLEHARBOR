"""Compose statutory current/deferred tax and source-backed payment allocations."""

from collections import defaultdict
from decimal import Decimal as D

Q = D(".0001")
TYPES = {
    "CO_SUB_TAX_CURRENT": "expense",
    "CO_SUB_TAX_DEFERRED": "expense",
    "CO_SUB_TAX_PAY_FED": "liability",
    "CO_SUB_TAX_PAY_STATE": "liability",
    "CO_SUB_TAX_PREPAID_FED": "asset",
    "CO_SUB_TAX_PREPAID_STATE": "asset",
    "CO_SUB_TAX_DTA": "asset",
    "CO_SUB_TAX_VA": "asset",
    "CO_SUB_TAX_DTL": "liability",
}
TYPES.update({f"CO_SUB_TAX_PAY_{j}": "liability" for j in ("CA", "IL", "WV")})
TYPES.update({f"CO_SUB_TAX_PREPAID_{j}": "asset" for j in ("CA", "IL", "WV")})


def installments(amount, jurisdiction):
    amount = D(amount)
    if jurisdiction == "CA":
        first = min(amount, max(D(800), amount * D(".3"))).quantize(Q)
        second = min(amount - first, amount * D(".4")).quantize(Q)
        return {4: first, 6: second, 12: amount - first - second}
    part = (amount / 4).quantize(Q)
    return {4: part, 6: part, 9: part, 12: amount - 3 * part}


def _part(amount, month):
    part = (D(amount) / 12).quantize(Q)
    return part if month < 12 else D(amount) - 11 * part


def _population(rows, fields, expected, label):
    seen = set()
    for row in rows:
        key = tuple(row[f] for f in fields)
        if key in seen:
            raise ValueError(f"Duplicate statutory {label} input")
        seen.add(key)
    if seen != expected:
        raise ValueError(f"Incomplete or unexpected statutory {label} population")


def _validate_inputs(result, parent, current, deferred, opening, settlement):
    scenarios, years = ("base", "downside", "expansion"), range(2026, 2032)
    members = ("SHI", "SHIH", "PS", "ARU", "BST")
    fields = ("scenario", "taxpayer", "jurisdiction", "year")
    federal = {
        (s, e, "US", y) for s in scenarios for e in ("SHIH", "PS", "ARU", "BST") for y in years
    }
    states = {
        (s, e, j, y) for s in scenarios for e in members for j in ("CA", "IL", "WV") for y in years
    }
    _population(current["federal"], fields, federal, "federal")
    _population(current["states"], fields, states, "state")
    _population(
        parent.rows, ("scenario", "year"), {(s, y) for s in scenarios for y in years}, "parent"
    )
    deferred_keys = states | {
        (s, e, "US", y) for s in scenarios for e in ("SHI", "PS", "ARU", "BST") for y in years
    }
    _population(deferred, fields, deferred_keys, "deferred")
    opening_keys = {
        (s, e, j, 2026)
        for s in scenarios
        for e, j in (("SHI", "US"), ("PS", "US"), ("SHI", "CA"), ("PS", "IL"), ("SHI", "WV"))
    }
    _population(opening, fields, opening_keys, "opening")
    monthly = {
        (s, g, y, m)
        for s in scenarios
        for g in ("ARU_GROUP", "RWH_PS")
        for y in years
        for m in range(1, 13)
    }
    _population(
        settlement["rows"], ("scenario", "source_group", "year", "month"), monthly, "settlement"
    )
    for rows, fields, label in (
        (result["journal_rows"], ("scenario", "journal_id", "line_no"), "journal leg"),
        (
            settlement["payments"],
            ("scenario", "source_group", "year", "month", "source_journal_id"),
            "payment",
        ),
    ):
        seen = set()
        for row in rows:
            key = tuple(row[f] for f in fields)
            if key in seen:
                raise ValueError(f"Duplicate statutory {label} input")
            seen.add(key)
    paid_by_month = defaultdict(D)
    for row in settlement["payments"]:
        key = tuple(row[f] for f in ("scenario", "source_group", "year", "month"))
        value = D(row["paid_usd"])
        if key not in monthly or not value.is_finite() or value <= 0:
            raise ValueError("Invalid statutory payment input")
        paid_by_month[key] += value
    for row in settlement["rows"]:
        key = tuple(row[f] for f in ("scenario", "source_group", "year", "month"))
        value = D(row["gross_source_tax_cash_paid_usd"])
        if not value.is_finite() or value < 0 or value != paid_by_month[key]:
            raise ValueError("Statutory payment detail differs from monthly settlement")
    native = {
        (r["scenario"], r["entity"], int(r["year"]), int(r["month"]))
        for r in result["journal_rows"]
        if r["source_id"].startswith("LEGAL-")
        and r["entity"] in ("ARU", "BST", "PS", "RWH")
        and int(r["month"]) > 0
    }
    expected_native = {
        (s, e, y, m)
        for s in scenarios
        for e in ("ARU", "BST", "PS", "RWH")
        for y in years
        for m in range(1, 13)
    }
    if native != expected_native:
        raise ValueError("Incomplete statutory native legal monthly population")
    for row in deferred + opening:
        for field in ("gross_dta_usd", "valuation_allowance_usd", "gross_dtl_usd"):
            value = D(row[field])
            if not value.is_finite() or value < 0:
                raise ValueError("Invalid statutory gross deferred amount")
        if D(row["valuation_allowance_usd"]) > D(row["gross_dta_usd"]):
            raise ValueError("Statutory valuation allowance exceeds gross DTA")
    for row in current["federal"] + current["states"]:
        if not D(row["current_tax_usd"]).is_finite() or D(row["current_tax_usd"]) < 0:
            raise ValueError("Invalid statutory current tax amount")


class StatutoryPosting:
    def __init__(self, result, parent, current, deferred, opening, settlement):
        _validate_inputs(result, parent, current, deferred, opening, settlement)
        self.parent, self.current, self.deferred, self.opening, self.settlement = (
            parent,
            current,
            deferred,
            opening,
            settlement,
        )
        self.tax = {}
        for r in current["federal"] + current["states"]:
            self.tax[r["scenario"], r["taxpayer"], r["jurisdiction"], r["year"]] = D(
                r["current_tax_usd"]
            )
        for r in parent.rows:
            self.tax[r["scenario"], "SHI", "US", r["year"]] = D(r["federal_current_usd"])
        self.native = defaultdict(lambda: defaultdict(D))
        for r in result["journal_rows"]:
            if r["source_id"].startswith("CO-STAT-"):
                raise ValueError("Statutory posting requires unadjusted source books")
            if r["source_id"].startswith("LEGAL-") and int(r["month"]) > 0:
                self.native[r["scenario"], r["entity"], int(r["year"]), int(r["month"])][
                    r["account"]
                ] += D(r["signed_usd"])
        self.cash = {}
        for r in settlement["rows"]:
            self.cash[r["scenario"], r["source_group"], r["year"], r["month"]] = D(
                r["gross_source_tax_cash_paid_usd"]
            )
        self.annual_override = {}
        self.payment_override = defaultdict(D)
        self.requests = defaultdict(lambda: defaultdict(D))
        self.payment_rows = []
        self.annual_deferred = defaultdict(lambda: defaultdict(D))
        self.opening_deferred = defaultdict(lambda: defaultdict(D))
        for source, target in ((deferred, self.annual_deferred), (opening, self.opening_deferred)):
            for r in source:
                key = (r["scenario"], r["taxpayer"], r["year"])
                for field in ("gross_dta_usd", "valuation_allowance_usd", "gross_dtl_usd"):
                    target[key][field] += D(r[field])
        for scenario in ("base", "downside", "expansion"):
            credit = defaultdict(D)
            for group, entity in (("ARU_GROUP", "ARU"), ("RWH_PS", "PS")):
                paid = sum(self.cash[scenario, group, 2026, m] for m in range(1, 13))
                credit[entity, "US"] = max(
                    paid - self.tax.get((scenario, entity, "US", 2026), D(0)), D(0)
                )
            for year in range(2027, 2032):
                for group, entities in (("ARU_GROUP", ("ARU", "BST")), ("RWH_PS", ("PS",))):
                    annual = D(0)
                    for entity in entities:
                        for jurisdiction in ("US", "CA", "IL", "WV"):
                            amount = self.tax.get((scenario, entity, jurisdiction, year), D(0))
                            annual += amount
                            for month, due in installments(amount, jurisdiction).items():
                                used = min(credit[entity, jurisdiction], due)
                                credit[entity, jurisdiction] -= used
                                requested = due - used
                                self.requests[scenario, group, year, month][
                                    entity, jurisdiction
                                ] += requested
                    self.annual_override[f"{scenario}/{group}/{year}"] = str(annual)
                    for month in range(1, 13):
                        self.payment_override[f"{scenario}/{group}/{year}/{month}"] = sum(
                            self.requests[scenario, group, year, month].values(), D(0)
                        )
        self.payment_override = {k: str(v) for k, v in self.payment_override.items()}

    @staticmethod
    def _post(books, entity, year, month, entries, identifier, description):
        entries = [(account, amount) for account, amount in entries if amount]
        if not entries:
            return
        if any(r["source_id"] == identifier for r in books.rows):
            raise ValueError("Duplicate statutory tax adjustment")
        books.post(
            entity,
            year,
            month,
            entries,
            identifier,
            description,
            kind="COMPANY_STATUTORY_TAX_SUCCESSOR",
            segment="CORPORATE",
        )

    def post_opening(self, books):
        amount = self.parent.history["historical_tax_cash"]
        self._post(
            books,
            "SHI",
            2026,
            0,
            [("3100", amount), ("1000", -amount)],
            "CO-TAX-HISTORICAL-PAYMENTS",
            "Preserved authored historical tax cash correction",
        )
        for (scenario, entity, year), r in self.opening_deferred.items():
            if scenario != books.scenario:
                continue
            dta, va, dtl = (
                r[f] for f in ("gross_dta_usd", "valuation_allowance_usd", "gross_dtl_usd")
            )
            self._post(
                books,
                entity,
                year,
                0,
                [
                    ("CO_SUB_TAX_DTA", dta),
                    ("CO_SUB_TAX_VA", -va),
                    ("CO_SUB_TAX_DTL", -dtl),
                    ("3100", va + dtl - dta),
                ],
                f"CO-STAT-OPEN-{entity}",
                "Historical gross deferred differences and full valuation allowance; no acquisition goodwill adjustment",
            )

    def _allocate_cash(self, books, year, month, group, amount):
        payer = "ARU" if group == "ARU_GROUP" else "RWH"
        if year == 2026:
            allocation = {("ARU" if group == "ARU_GROUP" else "PS", "US"): amount}
        else:
            allocation = defaultdict(D)
            payments = [
                r
                for r in self.settlement["payments"]
                if (r["scenario"], r["source_group"], r["year"], r["month"])
                == (books.scenario, group, year, month)
            ]
            for payment in payments:
                due = payment["source_id"].removeprefix("TAX-CASH-")
                plan = self.requests[books.scenario, group, int(due[:4]), int(due[4:6])]
                total = sum(plan.values(), D(0))
                if total <= 0:
                    raise ValueError("Paid industrial tax has no statutory request allocation")
                allocated = D(0)
                positive = [(k, v) for k, v in sorted(plan.items()) if v]
                for index, (key, value) in enumerate(positive):
                    share = (
                        (D(payment["paid_usd"]) * value / total).quantize(Q)
                        if index < len(positive) - 1
                        else D(payment["paid_usd"]) - allocated
                    )
                    allocation[key] += share
                    allocated += share
        if sum(allocation.values(), D(0)) != amount:
            raise ValueError("Statutory cash allocation does not reconcile source payments")
        payer_entries = []
        for (entity, jurisdiction), paid in allocation.items():
            if paid:
                self.payment_rows.append(
                    dict(
                        scenario=books.scenario,
                        taxpayer=entity,
                        jurisdiction=jurisdiction,
                        year=year,
                        month=month,
                        paid_usd=str(paid),
                        payer=payer,
                        state="MODELED_SOURCE_SETTLEMENT",
                        source_group=group,
                    )
                )
            account = (
                "CO_SUB_TAX_PREPAID_FED"
                if jurisdiction == "US"
                else f"CO_SUB_TAX_PREPAID_{jurisdiction}"
            )
            if entity == payer:
                payer_entries.append((account, paid))
            else:
                payer_entries.append(("1150", paid))
                self._post(
                    books,
                    entity,
                    year,
                    month,
                    [(account, paid), ("2150", -paid)],
                    f"CO-STAT-PAID-AGENT-{group}-{entity}-{jurisdiction}-{year}-{month}",
                    "Source-paid estimate allocated to separate taxpayer; payer current account, no additional cash",
                )
        return payer_entries

    def post_month(self, books, year, month):
        scenario = books.scenario
        for group, payer in (("ARU_GROUP", "ARU"), ("RWH_PS", "RWH")):
            paid = self.cash[scenario, group, year, month]
            lines = self._allocate_cash(books, year, month, group, paid)
            native = self.native[scenario, payer, year, month]
            lines += [("5500", -native["5500"]), ("2700", -native["2700"])]
            self._post(
                books,
                payer,
                year,
                month,
                lines,
                f"CO-STAT-CURRENT-REPLACE-{payer}-{year}-{month}",
                "Replace native planning tax provision; preserve original payment as gross taxpayer prepayment",
            )
        for entity in ("ARU", "BST", "RWH", "PS"):
            n = self.native[scenario, entity, year, month]
            lines = [
                ("5501", -n["5501"]),
                ("2250", -n["2250"]),
                ("1800", -n["1800"]),
                ("1801", -n["1801"]),
            ]
            residual = -sum(v for _, v in lines)
            if residual:
                acquired = (year, month) == (2026, 1) and entity in ("ARU", "BST")
                # Native forecast assigns the group's deferred expense to ARU,
                # while an acquired BST DTA can be written off in BST's asset
                # allocation. Reverse that exact cross-entity presentation via
                # each entity's expense; the counterpart must independently net.
                pair = [self.native[scenario, e, year, month] for e in ("ARU", "BST")]
                pair_residual = sum(
                    sum(n[a] for a in ("5501", "2250", "1800", "1801")) for n in pair
                )
                bst = pair[1]
                allocated_writeoff = (
                    entity in ("ARU", "BST")
                    and year >= 2027
                    and pair_residual == 0
                    and bst["1800"] < 0
                    and bst["5501"] == bst["2250"] == bst["1801"] == 0
                    and abs(residual) == -bst["1800"]
                )
                if not (acquired or allocated_writeoff):
                    raise ValueError(
                        f"Unexplained native deferred-tax replacement difference: {scenario}/{entity}/{year}/{month}: {residual}"
                    )
                lines.append(("CO_SUB_TAX_DEFERRED", residual))
            self._post(
                books,
                entity,
                year,
                month,
                lines,
                f"CO-STAT-DEFERRED-REPLACE-{entity}-{year}-{month}",
                "Subsequent valuation successor replaces native deferred balances through expense; original acquisition allocation and goodwill retained",
            )
        for entity in ("SHI", "SHIH", "PS", "ARU", "BST"):
            parts = {
                j: _part(self.tax.get((scenario, entity, j, year), D(0)), month)
                for j in ("US", "CA", "IL", "WV")
            }
            self._post(
                books,
                entity,
                year,
                month,
                [
                    ("CO_SUB_TAX_CURRENT", sum(parts.values(), D(0))),
                ]
                + [(f"CO_SUB_TAX_PAY_{'FED' if j == 'US' else j}", -v) for j, v in parts.items()],
                f"CO-STAT-PROVISION-{entity}-{year}-{month}",
                "Annual statutory management estimate allocated monthly; future assumptions remain conditional and availability-dated",
            )
            final = self.annual_deferred[scenario, entity, year]
            previous = (
                self.opening_deferred[scenario, entity, 2026]
                if year == 2026
                else self.annual_deferred[scenario, entity, year - 1]
            )
            dta, va, dtl = (
                _part(final[field] - previous[field], month)
                for field in ("gross_dta_usd", "valuation_allowance_usd", "gross_dtl_usd")
            )
            self._post(
                books,
                entity,
                year,
                month,
                [
                    ("CO_SUB_TAX_DTA", dta),
                    ("CO_SUB_TAX_VA", -va),
                    ("CO_SUB_TAX_DTL", -dtl),
                    ("CO_SUB_TAX_DEFERRED", -dta + va + dtl),
                ],
                f"CO-STAT-DEFERRED-{entity}-{year}-{month}",
                "Gross deferred-tax movement and conservative full valuation allowance; no unsupported realization",
            )
            if entity in ("SHI", "SHIH"):
                # Parent direct quarterly plan; holding-company state tax is
                # paid by parent as a disclosed reciprocal current account.
                for jurisdiction in ("US", "CA", "IL", "WV"):
                    amount = installments(
                        self.tax.get((scenario, entity, jurisdiction, year), D(0)), jurisdiction
                    ).get(month, D(0))
                    if not amount or (entity == "SHIH" and year == 2026):
                        continue
                    account = (
                        "CO_SUB_TAX_PREPAID_FED"
                        if jurisdiction == "US"
                        else f"CO_SUB_TAX_PREPAID_{jurisdiction}"
                    )
                    payer = "SHI"
                    self.payment_rows.append(
                        dict(
                            scenario=scenario,
                            taxpayer=entity,
                            jurisdiction=jurisdiction,
                            year=year,
                            month=month,
                            paid_usd=str(amount),
                            payer=payer,
                            state="AUTHORED_CURRENT_PAYMENT"
                            if year == 2026
                            else "CONDITIONAL_FORECAST_PAYMENT",
                            source_group="PARENT",
                        )
                    )
                    if entity == payer:
                        books.post(
                            payer,
                            year,
                            month,
                            [(account, amount), ("1000", -amount, "OPERATING")],
                            f"CO-STAT-PAYMENT-{entity}-{jurisdiction}-{year}-{month}",
                            "Synthetic scheduled statutory installment; separate payment state and period",
                            kind="COMPANY_STATUTORY_TAX_SUCCESSOR",
                        )
                    else:
                        books.post(
                            payer,
                            year,
                            month,
                            [("1150", amount), ("1000", -amount, "OPERATING")],
                            f"CO-STAT-PAYMENT-AGENT-{entity}-{jurisdiction}-{year}-{month}",
                            "Parent pays holding-company installment as agent",
                            kind="COMPANY_STATUTORY_TAX_SUCCESSOR",
                        )
                        self._post(
                            books,
                            entity,
                            year,
                            month,
                            [(account, amount), ("2150", -amount)],
                            f"CO-STAT-PREPAID-AGENT-{entity}-{jurisdiction}-{year}-{month}",
                            "Holding-company estimate and reciprocal payer current account",
                        )
            for suffix in ("FED", "CA", "IL", "WV"):
                prepaid, payable = "CO_SUB_TAX_PREPAID_" + suffix, "CO_SUB_TAX_PAY_" + suffix
                applied = min(
                    max(books.balances[entity][prepaid], D(0)),
                    max(-books.balances[entity][payable], D(0)),
                )
                self._post(
                    books,
                    entity,
                    year,
                    month,
                    [(payable, applied), (prepaid, -applied)],
                    f"CO-STAT-APPLY-{entity}-{suffix}-{year}-{month}",
                    "Apply taxpayer-specific estimate against accrued current tax; excess stays an asset, no refund inferred",
                )
