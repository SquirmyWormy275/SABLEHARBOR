"""Approved holder precision and voluntary source-bound funding; no ledger postings."""

import hashlib
import json
from collections import defaultdict
from decimal import ROUND_HALF_UP
from decimal import Decimal as D
from fractions import Fraction
from pathlib import Path

from .capital import proportional_request

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name("source") / "capital_register.json"


def build_register():
    source = json.loads(SOURCE.read_text())
    expected = {
        "SH-HOLDER-DM": 33250000,
        "SH-HOLDER-PR": 19950000,
        "SH-HOLDER-JB": 13300000,
        "SH-HOLDER-HV": 18500000,
        "SH-HOLDER-WR": 15000000,
    }
    actual = {r["holder_id"]: r["units"] for r in source["holders"]}
    if actual != expected or len(source["holders"]) != 5 or sum(actual.values()) != 100000000:
        raise ValueError("Holder register differs from exact owner direction")
    subscriptions = source["subscriptions"]
    expected_rounds = {
        "SH-HOLDER-HV": ("2021-06-18", 18500000, D(48000000)),
        "SH-HOLDER-WR": ("2022-10-28", 15000000, D(135000000)),
    }
    if len(subscriptions) != 2 or {r["holder_id"] for r in subscriptions} != set(expected_rounds):
        raise ValueError("Historical subscription population differs")
    for row in subscriptions:
        date, units, amount = expected_rounds[row["holder_id"]]
        if (row["effective_date"], row["units"], D(row["consideration_usd"])) != (
            date,
            units,
            amount,
        ):
            raise ValueError("Historical subscription differs from approved precision")
        if Fraction(row["price_numerator"]) / Fraction(
            row["price_denominator"]
        ) * units != Fraction(amount):
            raise ValueError("Subscription rational price does not reconcile")
        if (
            row["authorization_date"] > row["effective_date"]
            or row["settlement_date"] < row["effective_date"]
        ):
            raise ValueError("Subscription authority/settlement chronology mismatch")
    holders = []
    for row in source["holders"]:
        rights = dict(
            unit_class=row["unit_class"],
            units=row["units"],
            economic_share=str(D(row["units"]) / 100000000),
            ordinary_vote_share=str(D(row["units"]) / 100000000),
            board_rights="EXISTING_ACCEPTED_ROLES_NO_NEW_THRESHOLDS",
        )
        if row["unit_class"] != "EQUAL_PARTICIPATING_COMMON":
            raise ValueError("Unapproved unit class")
        holders.append(
            dict(
                row,
                participation_share=rights["economic_share"],
                participation_basis_source=source["document_id"],
                basis_state="ESTABLISHED",
                rights_before=rights,
            )
        )
    unit_history = []
    for row in holders:
        investor = row["holder_role"] == "REGISTERED_INVESTOR"
        subscription = next((r for r in subscriptions if r["holder_id"] == row["holder_id"]), None)
        unit_history.append(
            dict(
                holder_id=row["holder_id"],
                effective_date=subscription["effective_date"] if investor else "2016",
                date_precision="DAY" if investor else "YEAR",
                opening_units=0,
                issued_units=row["units"],
                closing_units=row["units"],
                authority_source=subscription["subscription_id"]
                if investor
                else source["authority_source"],
                recorded_subscription_cash_usd=subscription["consideration_usd"]
                if investor
                else None,
                founder_consideration_state="NOT_APPLICABLE"
                if investor
                else "SOURCE_RECONSTRUCTION_REQUIRED",
                fact_state="NEWLY_AUTHORED_SYNTHETIC_HISTORY",
            )
        )
    return dict(
        unit_history=unit_history,
        source=source,
        holders=holders,
        verified_subscription_receipts_usd="183000000.00",
        total_units=100000000,
        founder_monetary_basis_complete=False,
    )


def allocate_event(event, receipts=None):
    """Cash cents are allocated once; exact journal precision remains a separate bridge."""
    register = build_register()
    if event["legal_entity"] != "SHI" or event["scenario"] not in {"base", "downside", "expansion"}:
        raise ValueError("Funding event legal entity or scenario invalid")
    if (
        not event.get("source_id")
        or not event.get("event_id")
        or not 1 <= int(event["month"]) <= 12
    ):
        raise ValueError("Funding event identity/period missing")
    if int(event["year"]) < 2026 or int(event["year"]) > 2031:
        raise ValueError("Funding event outside selected scenario horizon")
    amount = D(event["source_amount_usd"])
    if not amount.is_finite() or amount < 0:
        raise ValueError("Invalid funding source amount")
    cash = amount.quantize(D(".01"), rounding=ROUND_HALF_UP)
    rows = proportional_request(cash, register["holders"])
    actual = receipts or {}
    if set(actual) - {r["holder_id"] for r in rows}:
        raise ValueError("Receipt from outside approved holder population")
    for row in rows:
        received = D(actual.get(row["holder_id"], "0"))
        if (
            not received.is_finite()
            or received < 0
            or received > D(row["requested_usd"])
            or received != received.quantize(D(".01"))
        ):
            raise ValueError("Receipt exceeds holder request or cash precision")
        row.update(
            event_id=event["event_id"],
            source_id=event["source_id"],
            scenario=event["scenario"],
            year=int(event["year"]),
            month=int(event["month"]),
            authority_id=event.get("authority_id"),
            approval_state=event.get("approval_state", "SCENARIO_ASSUMPTION_NOT_ACTUAL_CALL"),
            due_date=event.get("due_date"),
            receipt_date=event.get("receipt_date"),
            settlement_reference=event.get("settlement_reference"),
            received_usd=str(received.quantize(D(".01"))),
            shortfall_usd=str(D(row["requested_usd"]) - received),
            event_state=event.get("event_state", "PREPARED_VOLUNTARY_REQUEST"),
            commitment_usd=None,
            capacity_usd=event.get("capacity_usd"),
        )
        if received and row["event_state"] != "CONDITIONAL_FORECAST_MODELED_RECEIPT":
            raise ValueError("Receipt requires explicit modeled-settlement state")
    return dict(
        event=event,
        rows=rows,
        source_amount_usd=str(amount),
        cash_facing_requested_usd=str(cash),
        source_to_cash_rounding_usd=str(cash - amount),
        received_usd=str(sum(D(r["received_usd"]) for r in rows)),
        shortfall_usd=str(sum(D(r["shortfall_usd"]) for r in rows)),
        interests_issued="0",
        additional_ledger_postings="0",
    )


def build(journal_rows):
    """Consume complete SHI MEMBER_EQUITY legs after tax/funding composition."""
    register = build_register()
    grouped = defaultdict(list)
    for row in journal_rows:
        if row["entity"] == "SHI" and row["source_type"] == "MEMBER_EQUITY":
            grouped[row["scenario"], int(row["year"]), int(row["month"]), row["source_id"]].append(
                row
            )
    events = []
    cumulative = defaultdict(D)
    rollforward = []
    for (scenario, year, month, source_id), legs in sorted(grouped.items()):
        cash = [r for r in legs if r["account"] == "1000"]
        equity = [r for r in legs if r["account"] == "3000"]
        if (
            len(legs) != 2
            or len(cash) != 1
            or len(equity) != 1
            or D(cash[0]["signed_usd"]) != -D(equity[0]["signed_usd"])
        ):
            raise ValueError("Member cash source duplicated, reversed or unbalanced")
        event = dict(
            event_id=f"SH-CAP-{scenario}-{year}-{month}-{source_id}",
            source_id=source_id,
            legal_entity="SHI",
            scenario=scenario,
            year=year,
            month=month,
            source_amount_usd=cash[0]["signed_usd"],
            event_state="CONDITIONAL_FORECAST_MODELED_RECEIPT",
            approval_state="MODEL_REQUEST_AND_SETTLEMENT_ASSUMPTION_NOT_BINDING_COMMITMENT",
            authority_id="SH-MEMBER-REGISTER-ADDENDUM-20260915",
            receipt_date=None,
            due_date=None,
            date_precision="MONTH_ONLY_SOURCE_DOES_NOT_PROVE_DAILY_LIQUIDITY",
            settlement_reference="SYN-MODEL-" + source_id,
        )
        prepared = allocate_event(event)
        receipts = {r["holder_id"]: r["requested_usd"] for r in prepared["rows"]}
        result = allocate_event(event, receipts)
        events.append(result)
        for row in result["rows"]:
            key = scenario, row["holder_id"]
            opening = cumulative[key]
            cumulative[key] += D(row["received_usd"])
            rollforward.append(
                dict(
                    event_id=event["event_id"],
                    scenario=scenario,
                    year=year,
                    month=month,
                    holder_id=row["holder_id"],
                    opening_scenario_contributions_usd=str(opening),
                    contribution_usd=row["received_usd"],
                    closing_scenario_contributions_usd=str(cumulative[key]),
                    units_before=row["units"],
                    units_after=row["units"],
                    historical_monetary_opening_usd=None,
                    basis="Cumulative scenario additions; "
                    "not complete historical monetary capital account",
                )
            )
    source_paths = [
        SOURCE,
        Path(__file__),
        Path(__file__).with_name("capital.py"),
        ROOT / "docs/canon/COMPANY_CLOSEOUT_DIRECTIONS_2026-09-15.md",
    ]
    return dict(
        register=register,
        events=events,
        holder_rollforward=rollforward,
        source_hashes={
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source_paths
        },
        limitations=[
            "Historical founder consideration/tax basis remains a separate source reconstruction; "
            "no invented monetary opening.",
            "Monthly conditional modeled receipts do not establish legal commitment, actual calls "
            "or day-level cash sufficiency.",
        ],
    )
