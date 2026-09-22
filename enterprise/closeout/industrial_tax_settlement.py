"""Retain native industrial income-tax cash; filing allocation is a separate step."""

import hashlib
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def amount(value):
    return str(D(value).quantize(D(".0001")))


def build(journal_rows, forecast):
    from industrial.planning.enterprise import load_anchor

    anchor = load_anchor()
    native = [dict(r, scenario=s) for s in ("base", "downside", "expansion") for r in anchor]
    native += forecast["datasets"]["journal"]
    expected = {
        (s, g, y)
        for s in ("base", "downside", "expansion")
        for g in ("ARU_GROUP", "RWH_PS")
        for y in range(2026, 2032)
    }
    groups = defaultdict(list)
    seen_native = set()
    for r in native:
        if r["account"] in {"5500", "5501", "2700"}:
            identity = (
                r["scenario"],
                r["entity"],
                int(r["year"]),
                int(r["month"]),
                r["journal_id"],
                r["account"],
            )
            if identity in seen_native:
                raise ValueError("Duplicate native industrial tax leg")
            seen_native.add(identity)
        groups[r["scenario"], r["entity"], int(r["year"])].append(r)
    if set(groups) != expected:
        raise ValueError("Industrial tax settlement source group population incomplete")
    legal = defaultdict(lambda: defaultdict(D))
    legal_population = set()
    legal_identities = set()
    for r in journal_rows:
        if r["entity"] in {"ARU", "BST", "PS", "RWH"} and r["source_id"].startswith("LEGAL-"):
            scope = (r["scenario"], r["entity"], int(r["year"]), int(r["month"]))
            identity = (*scope, r["journal_id"], r["line_no"])
            if identity in legal_identities:
                raise ValueError("Duplicate successor native legal tax bridge leg")
            legal_identities.add(identity)
            if int(r["month"]) > 0:
                legal_population.add(scope)
            legal[r["scenario"], r["entity"], int(r["year"]), int(r["month"])][r["account"]] += D(
                r["signed_usd"]
            )
    expected_legal = {
        (s, e, y, m)
        for s in ("base", "downside", "expansion")
        for e in ("ARU", "BST", "RWH", "PS")
        for y in range(2026, 2032)
        for m in range(1, 13)
    }
    if legal_population != expected_legal:
        raise ValueError("Successor legal source monthly population incomplete")
    output, payments = [], []
    for (scenario, group, year), source in sorted(groups.items()):
        if {int(r["month"]) for r in source if int(r["month"]) > 0} != set(range(1, 13)):
            raise ValueError("Industrial tax source monthly population incomplete")
        signed = sum(
            D(r["signed_usd"]) for r in source if r["account"] == "2700" and int(r["month"]) == 0
        )
        for month in range(1, 13):
            rows = [r for r in source if int(r["month"]) == month]
            current = sum(D(r["signed_usd"]) for r in rows if r["account"] == "5500")
            deferred = sum(D(r["signed_usd"]) for r in rows if r["account"] == "5501")
            candidate = [
                r
                for r in rows
                if (year == 2026 and r["source_id"] in {"TAX26-PAYMENT", "RW-TAX"})
                or (year >= 2027 and r["source_id"].startswith("TAX-CASH-"))
            ]
            by_entry = defaultdict(list)
            for r in candidate:
                by_entry[r["journal_id"], r["source_id"]].append(r)
            paid = D(0)
            ids = []
            for (journal_id, source_id), legs in sorted(by_entry.items()):
                cash = [r for r in legs if r["account"] == "1000"]
                settlement = [
                    r for r in legs if r["account"] == ("5500" if source_id == "RW-TAX" else "2700")
                ]
                if (
                    len(legs) != 2
                    or len(cash) != 1
                    or len(settlement) != 1
                    or D(cash[0]["signed_usd"]) != -D(settlement[0]["signed_usd"])
                    or D(cash[0]["signed_usd"]) >= 0
                ):
                    raise ValueError("Industrial tax payment duplicated, reversed or unbalanced")
                value = -D(cash[0]["signed_usd"])
                paid += value
                ids.append(source_id)
                payments.append(
                    dict(
                        scenario=scenario,
                        source_group=group,
                        year=year,
                        month=month,
                        source_id=source_id,
                        source_journal_id=journal_id,
                        paid_usd=amount(value),
                        cash_account="1000",
                        native_offset_account=settlement[0]["account"],
                        payment_state="NATIVE_SYNTHETIC_PAYMENT"
                        if year == 2026
                        else "CONDITIONAL_FORECAST_MODELED_PAYMENT",
                        legal_cash_book_owner="RWH"
                        if group == "RWH_PS"
                        else "ARU_BST_ALLOCATED_CASH_POOL",
                        taxpayer="PS"
                        if group == "RWH_PS"
                        else "ARU_BST_ALLOCATION_PENDING_CURRENT_PROVISION",
                        jurisdiction_allocation_state="UNALLOCATED_ESTIMATE_NOT_FILED_FEDERAL_STATE_ASSESSMENT",
                    )
                )
            opening = signed
            movement = sum(D(r["signed_usd"]) for r in rows if r["account"] == "2700")
            signed += movement
            if year == 2026 and group == "RWH_PS":
                if current != paid or signed != 0:
                    raise ValueError("Direct current mine income-tax cash does not reconcile")
            elif movement != paid - current:
                raise ValueError("Native current tax payable/prepaid movement does not reconcile")
            entities = ("ARU", "BST") if group == "ARU_GROUP" else ("RWH", "PS")
            for account, total in (("5500", current), ("5501", deferred), ("2700", movement)):
                native_legal = sum(legal[scenario, e, year, month][account] for e in entities)
                if native_legal != total:
                    raise ValueError("Native tax source differs from successor legal-book bridge")
            output.append(
                dict(
                    scenario=scenario,
                    source_group=group,
                    year=year,
                    month=month,
                    native_current_provision_usd=amount(current),
                    native_deferred_provision_usd=amount(deferred),
                    gross_source_tax_cash_paid_usd=amount(paid),
                    opening_tax_settlement_signed_usd=amount(opening),
                    current_tax_settlement_movement_usd=amount(movement),
                    closing_tax_settlement_signed_usd=amount(signed),
                    native_closing_tax_prepayment_usd=amount(max(signed, D(0))),
                    native_closing_tax_payable_usd=amount(max(-signed, D(0))),
                    payment_source_ids=sorted(ids),
                    native_provision_book_owner="ARU" if group == "ARU_GROUP" else "RWH",
                    taxpayer="PS"
                    if group == "RWH_PS"
                    else "ARU_BST_SEPARATE_RETURNS_ALLOCATION_PENDING",
                    period_state="SOURCE_PAYMENT" if paid else "NO_NATIVE_PAYMENT_OCCURRENCE",
                    replacement_treatment="Retain gross paid amount as unapplied estimate; "
                    "new provision allocates taxpayer/jurisdiction and payable versus "
                    "prepayment without new cash",
                    additional_cash_usd="0.0000",
                )
            )
    paths = [
        Path(__file__),
        ROOT / "docs/finance/evidence/company-closeout/INDUSTRIAL_TAX_SETTLEMENT.md",
        ROOT / "enterprise/operations/availability.py",
        ROOT / "industrial/source/finance.json",
        ROOT / "industrial/planning/source/forecast.json",
    ]
    from enterprise.operations.availability import apply

    for row in output + payments:
        row["available_at"] = "2026-09-22T00:00:00Z"
        row["authored_day"] = "2026-09-22"
        row["record_origin"] = "SOURCE_REPERFORMANCE_NEWLY_AUTHORED_ADAPTER"
    result = dict(
        rows=output,
        payments=payments,
        source_groups=len(groups),
        input_hashes={
            "successor_journal_sha256": hashlib.sha256(
                json.dumps(journal_rows, sort_keys=True, default=str).encode()
            ).hexdigest(),
            "native_forecast_journal_sha256": hashlib.sha256(
                json.dumps(forecast["datasets"]["journal"], sort_keys=True, default=str).encode()
            ).hexdigest(),
            "regenerated_anchor_sha256": hashlib.sha256(
                json.dumps(anchor, sort_keys=True, default=str).encode()
            ).hexdigest(),
        },
        parent_tax_boundary="SHI federal/state CO_TAX payments are separate and excluded "
        "from industrial native payment population",
        source_hashes={
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
        },
    )

    return apply(result)
