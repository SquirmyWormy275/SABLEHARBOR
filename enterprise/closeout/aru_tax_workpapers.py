"""ARU/BST source-based annual income before limits; no tax or cash postings."""

import calendar
import csv
import hashlib
import json
from collections import defaultdict
from decimal import ROUND_HALF_UP
from decimal import Decimal as D
from pathlib import Path

from .industrial_tax_assets import build as asset_workpapers

ROOT = Path(__file__).resolve().parents[2]
Q = D(".0001")


def money(value):
    return str(D(value).quantize(Q))


def financing_components(forecast):
    source = json.loads((ROOT / "industrial/source/finance.json").read_text())
    policy = json.loads((ROOT / "industrial/planning/source/forecast.json").read_text())["debt"]
    t = source["transaction"]
    current = list(
        csv.DictReader((ROOT / "industrial/generated/finance/aru_2026_debt_leases.csv").open())
    )
    if len(current) != 12 or {int(r["month"]) for r in current} != set(range(1, 13)):
        raise ValueError("Current debt component population incomplete")
    rows = {}
    for scenario in ("base", "downside", "expansion"):
        for r in current:
            month = int(r["month"])
            days = calendar.monthrange(2026, month)[1] - (6 if month == 1 else 0)
            fee = (
                D(str(t["new_revolver_capacity"]))
                * D(str(t["new_revolver_undrawn_commitment_fee_pct"]))
                / 100
                * days
                / 365
            ).quantize(D(1))
            rows[scenario, 2026, month] = dict(
                loan_and_lease_interest=D(r["term_interest_usd"]) + D(r["lease_interest_usd"]),
                issuance_amortization=D(r["debt_issue_amortization_usd"]),
                unused_commitment_service_fee=fee,
            )
    seen = set()
    for r in forecast["datasets"]["debt"]:
        if r["entity"] != "ARU_GROUP":
            continue
        key = r["scenario"], int(r["year"]), int(r["month"])
        if key in seen or not 2027 <= key[1] <= 2031:
            raise ValueError("Forecast debt component duplicate or wrong period")
        seen.add(key)
        days = calendar.monthrange(key[1], key[2])[1]
        fee = (
            D(str(policy["revolver_capacity_usd"]))
            * D(str(policy["revolver_fee_pct"]))
            / 100
            * days
            / 365
        )
        rows[key] = dict(
            loan_and_lease_interest=D(r["interest_expense_usd"]) - fee,
            issuance_amortization=D(r["issuance_cost_amortization_usd"]),
            unused_commitment_service_fee=fee,
        )
    return rows


def retention_components(forecast):
    from industrial.planning.enterprise import load_anchor

    rows = defaultdict(lambda: defaultdict(D))
    for r in load_anchor():
        if r["entity"] == "ARU_GROUP" and r["source_id"] in {"RETENTION-POOL", "RETENTION-PAYMENT"}:
            for scenario in ("base", "downside", "expansion"):
                key = scenario, 2026
                if r["account"] == "5700":
                    rows[key]["book_accrual"] += D(r["signed_usd"])
                    if int(r["month"]) == 1:
                        rows[key]["january_book_accrual"] += D(r["signed_usd"])
                if r["account"] == "1000":
                    rows[key]["paid"] -= D(r["signed_usd"])
    if forecast["datasets"]["debt"] and "journal" not in forecast["datasets"]:
        raise ValueError("Forecast retention requires source journal population")
    seen = set()
    for r in forecast["datasets"].get("journal", []):
        if r["source_id"] not in {"FINAL-RETENTION-SERVICE", "FINAL-RETENTION-PAYMENT"}:
            continue
        identity = (
            r["scenario"],
            r["entity"],
            r["year"],
            r["month"],
            r["journal_id"],
            r["account"],
        )
        if identity in seen:
            raise ValueError("Duplicate forecast retention journal leg")
        seen.add(identity)
        if r["entity"] != "ARU_GROUP":
            continue
        key = r["scenario"], int(r["year"])
        if r["source_id"] == "FINAL-RETENTION-SERVICE" and r["account"] == "5700":
            rows[key]["book_accrual"] += D(r["signed_usd"])
        if r["source_id"] == "FINAL-RETENTION-PAYMENT" and r["account"] == "1000":
            rows[key]["paid"] -= D(r["signed_usd"])
    return rows


def build(journal_rows, forecast):
    assets = asset_workpapers(forecast)
    debt = financing_components(forecast)
    retention = retention_components(forecast)
    source = json.loads((ROOT / "industrial/source/finance.json").read_text())
    bst_share = D(str(source["legal_book_policy"]["central_financing_cost_to_bst_pct"])) / 100
    monthly = defaultdict(lambda: defaultdict(D))
    types = {}
    identities = set()
    for r in journal_rows:
        if r["entity"] not in {"ARU", "BST"} or int(r["month"]) == 0:
            continue
        key = r["scenario"], r["entity"], int(r["year"]), int(r["month"])
        identity = (*key, r["journal_id"], r["line_no"])
        if identity in identities:
            raise ValueError("Duplicate ARU/BST journal leg")
        identities.add(identity)
        if r["account"].startswith("CO_TAX_") and r["account_type"] == "expense":
            raise ValueError("ARU tax base requires journal before income-tax provider")
        monthly[key][r["account"]] += D(r["signed_usd"])
        types[r["account"]] = r["account_type"]
    groups = sorted({(s, e, y) for s, e, y, m in monthly})
    result, components = [], []
    for scenario, entity, year in groups:
        if {m for s, e, y, m in monthly if (s, e, y) == (scenario, entity, year)} != set(
            range(1, 13)
        ):
            raise ValueError("ARU/BST complete annual monthly book population required")
        annual = defaultdict(D)
        for month in range(1, 13):
            for account, value in monthly[scenario, entity, year, month].items():
                annual[account] += value
        book_net = -sum(v for a, v in annual.items() if types[a] in {"revenue", "expense"})
        native_tax = annual["5500"] + annual["5501"]
        dda = annual["5300"]
        shared = annual["5900"] + annual["SHARED_EXP"]
        excluded_old_day_profit = D(0)
        if year == 2026:
            jan = monthly[scenario, entity, year, 1]
            ordinary = {"4000", "4100", "5000", "5100", "5150", "5200", "5700"}
            excluded_old_day_profit = -sum(v for a, v in jan.items() if a in ordinary) / 25
        share = bst_share if entity == "BST" else 1 - bst_share
        loan, issuance, fee, old_interest = D(0), D(0), D(0), D(0)
        for month in range(1, 13):
            key = scenario, year, month
            if key not in debt:
                raise ValueError("Debt component source missing for annual tax period")
            d = debt[key]
            group_book = sum(
                monthly.get((scenario, e, year, month), {}).get("5400", D(0))
                for e in ("ARU", "BST")
            )
            if group_book != sum(d.values()):
                raise ValueError("Financing components differ from combined legal 5400")
            factor = D(24) / 25 if (year, month) == (2026, 1) else D(1)
            loan += d["loan_and_lease_interest"] * share * factor
            issuance += d["issuance_amortization"] * share * factor
            fee += d["unused_commitment_service_fee"] * share * factor
            old_interest += (
                (
                    d["loan_and_lease_interest"]
                    + d["issuance_amortization"]
                    + d["unused_commitment_service_fee"]
                )
                * share
                * (1 - factor)
            )
            components.append(
                dict(
                    scenario=scenario,
                    legal_entity=entity,
                    year=year,
                    month=month,
                    loan_and_lease_interest_usd=money(
                        d["loan_and_lease_interest"] * share * factor
                    ),
                    debt_issuance_amortization_usd=money(
                        d["issuance_amortization"] * share * factor
                    ),
                    unused_commitment_service_fee_usd=money(
                        d["unused_commitment_service_fee"] * share * factor
                    ),
                    source_group_financing_usd=money(group_book),
                    allocation_share=str(share),
                    old_target_day_excluded=year == 2026 and month == 1,
                )
            )
        # Legal allocation rounds cumulative BST financing to whole USD. Preserve
        # that source residue in interest, never silently add/remove group expense.
        allocation_residue = annual["5400"] - (loan + issuance + fee + old_interest)
        eligible = loan + issuance + allocation_residue
        bonus_share = D(source["transaction"]["retention_allocations"]["Seth Kettering"]) / D(
            source["transaction"]["retention_pool"]
        )
        awards = retention[scenario, year]

        def bonus_owner(value, bonus_share=bonus_share, entity=entity):
            bst = (value * bonus_share).quantize(D(1), rounding=ROUND_HALF_UP)
            return bst if entity == "BST" else value - bst

        book_award = bonus_owner(awards["book_accrual"])
        old_award = bonus_owner(awards["january_book_accrual"]) / 25
        paid_award = bonus_owner(awards["paid"])
        retention_adjustment = book_award - old_award - paid_award
        # Unpaid employer levy is separately recorded July2026, not paid by bonus gross cash.
        levy = D(0)
        for month in range(1, 13):
            rows = [
                r
                for r in journal_rows
                if r["entity"] == entity
                and r["scenario"] == scenario
                and int(r["year"]) == year
                and int(r["month"]) == month
                and r["source_id"].startswith("CO-RETENTION-EMP-TAX-")
                and r["account"] == "5000"
            ]
            levy += sum(D(r["signed_usd"]) for r in rows)
        for jurisdiction in ("US", "CA", "IL", "WV"):
            key = scenario, entity, jurisdiction, year
            if key not in assets["totals"]:
                raise ValueError("Asset tax cost-recovery population missing")
            allowance = assets["totals"][key]["tax_depreciation_usd"]
            goodwill = D(13000000) / 180 * 12 if entity == "ARU" else D(0)
            income = (
                book_net
                + native_tax
                + dda
                + shared
                + annual["5400"]
                - fee
                - allowance
                - goodwill
                - excluded_old_day_profit
                + levy
                + retention_adjustment
            )
            result.append(
                dict(
                    scenario=scenario,
                    taxpayer=entity,
                    jurisdiction=jurisdiction,
                    year=year,
                    book_net_income_usd=money(book_net),
                    native_planning_tax_addback_usd=money(native_tax),
                    book_dda_addback_usd=money(dda),
                    book_only_shared_allocation_addback_usd=money(shared),
                    book_financing_addback_usd=money(annual["5400"]),
                    unused_commitment_fee_deduction_usd=money(fee),
                    eligible_interest_expense_usd=money(eligible),
                    legal_financing_allocation_rounding_usd=money(allocation_residue),
                    excluded_old_target_operating_profit_usd=money(excluded_old_day_profit),
                    excluded_old_target_financing_usd=money(old_interest),
                    unpaid_retention_employer_levy_addback_usd=money(levy),
                    retention_employee_timing_adjustment_usd=money(retention_adjustment),
                    retention_book_accrual_usd=money(book_award),
                    retention_old_target_accrual_usd=money(old_award),
                    retention_fixed_paid_deduction_usd=money(paid_award),
                    tax_depreciation_allowance_usd=money(allowance),
                    tax_goodwill_amortization_usd=money(goodwill),
                    protected_aru_book_goodwill_usd="14762500.0000",
                    protected_aru_tax_goodwill_original_basis_usd="13000000.0000",
                    income_before_interest_limit_usd=money(income),
                    taxable_income_before_nol_after_full_interest_usd=money(income - eligible),
                    state="PRE_LIMIT_WORKPAPER_NOT_RETURN_OR_POSTED_TAX",
                )
            )
    paths = [
        Path(__file__),
        ROOT / "docs/finance/evidence/company-closeout/ARU_BOOK_TO_TAX_METHOD.md",
        ROOT / "enterprise/closeout/industrial_tax_assets.py",
        ROOT / "enterprise/closeout/cost_recovery.py",
        ROOT / "enterprise/closeout/source/industrial_tax_cohorts.json",
        ROOT / "industrial/source/finance.json",
        ROOT / "industrial/planning/source/forecast.json",
        ROOT / "industrial/generated/finance/aru_2026_debt_leases.csv",
    ]
    return dict(
        accounting_basis="Accrual synthetic management books; "
        "separate source-based tax timing bridge",
        election_state="INTENDED_SECTION338H10_NEW_TARGET_JANUARY8_NOT_SUBMISSION_EVIDENCE",
        rows=result,
        financing_components=components,
        source_hashes={
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
        },
    )
