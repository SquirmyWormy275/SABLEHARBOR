"""Selected September custody successor; August source history stays intact."""

import argparse
import hashlib
import json
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path

from .completed_period import ROOT, SOURCE, money, read
from .completed_period import build as august_build

SEPTEMBER_SOURCE = "enterprise/operations/source/september_custody_2026.json"
OUTPUT = ROOT / "enterprise/generated/september-custody-2026"


def build(source=None, qualification=None, august=None):
    from enterprise.ccf.company_closeout.shipment import validate as validate_qualification

    source = source or read(SEPTEMBER_SOURCE)
    qualification = qualification or read(source["qualification_path"])
    validate_qualification(qualification)
    august = august or august_build()
    quantity = D(source["quantity_lb_u3o8"])
    origins = {r["chain_id"]: r for r in august["tables"]["operating_quantities"]}
    opening = origins[source["opening_chain_id"]]
    failed = origins[source["failed_chain_id"]]
    if D(opening["closing_quantity"]) != quantity or D(failed["closing_quantity"]) != quantity:
        raise ValueError("September lot does not reconcile to retained August held quantities")
    for field in ("qualification_id", "shipment_id", "lot_id", "carrier_id", "receiver_id"):
        if qualification[field] != source[field]:
            raise ValueError("Qualification identity does not match selected shipment")
    if (
        source["ready_at"] != qualification["ready_at"]
        or source["released_at"] != qualification["events"][1]["event_at"]
        or source["received_at"] != qualification["events"][2]["event_at"]
        or source["available_at"] != qualification["available_at"]
        or source["drum_id"] != qualification["drum_id"]
        or quantity != D(qualification["material"]["contained_u3o8_lb"])
    ):
        raise ValueError("Custody events differ from qualified operating evidence")
    if qualification["state"] != "QUALIFIED_SELECTED_SYNTHETIC_SHIPMENT":
        raise ValueError("Selected shipment qualification has not passed")
    checks = qualification["checks"]
    if len(checks) != 8 or {c["check_id"] for c in checks} != {
        f"RW-SHIP-CHECK-{n:02d}" for n in range(1, 9)
    }:
        raise ValueError("Missing or duplicate qualification check population")
    if any(c["outcome"] != "PASS" or not c["evidence_id"] for c in checks):
        raise ValueError("Selected shipment has failed or missing qualification evidence")
    moments = [
        datetime.fromisoformat(v)
        for v in (
            qualification["ready_at"],
            source["released_at"],
            source["received_at"],
            source["freight_paid_at"],
            source["available_at"],
        )
    ]
    if any(m.tzinfo is None for m in moments) or moments != sorted(moments):
        raise ValueError("Qualification release receipt payment availability chronology invalid")
    if source["released_at"][:10] <= "2026-09-06":
        raise ValueError("Shipment overwrites earlier OPEN source boundary")
    if source["legal_owner"] != "RWH" or source["carrier_id"] in {"ARU", "BST"}:
        raise ValueError("Custody successor changes title or prohibited carrier authority")
    total = D(source["expense_parent"]["amount_usd"])
    freight = D(source["freight_amount_usd"])
    if freight < 0 or freight > total:
        raise ValueError("Selected freight exceeds retained monthly source envelope")
    events = []
    for event, at, owner, custodian in (
        ("QUALIFICATION_READY", qualification["ready_at"], "RWH", "RWH"),
        ("RELEASED_TO_EXTERNAL_CARRIER", source["released_at"], "RWH", source["carrier_id"]),
        ("CONVERTER_CUSTODIAL_RECEIPT", source["received_at"], "RWH", source["receiver_id"]),
    ):
        events.append(
            dict(
                event_id=source["shipment_id"] + "-" + event,
                event=event,
                effective_at=at,
                available_at=source["available_at"],
                qualification_id=source["qualification_id"],
                lot_id=source["lot_id"],
                drum_id=source["drum_id"],
                quantity_lb_u3o8=money(quantity),
                legal_owner=owner,
                custodian_id=custodian,
                fact_state=source["fact_state"],
                acceptance_state=source["acceptance_state"],
            )
        )
    return dict(
        record_id=source["record_id"],
        source=source,
        qualification=qualification,
        events=events,
        lot_rollforward=dict(
            opening_mine_held_lb_u3o8=money(quantity),
            released_lb_u3o8=money(quantity),
            closing_mine_passed_lb_u3o8="0.00",
            closing_converter_custody_lb_u3o8=money(quantity),
            rejected_mine_quarantine_lb_u3o8=money(quantity),
            title_owner="RWH",
            new_revenue_usd="0.00",
            inventory_valuation_delta_usd="0.00",
        ),
        expense_bridge=dict(
            selected_freight_paid_usd=money(freight),
            unallocated_monthly_source_remainder_usd=money(total - freight),
            retained_monthly_source_usd=money(total),
            additional_journal_usd="0.00",
            parent=source["expense_parent"],
        ),
    )


def as_of(result, *, effective_at, known_on):
    cutoff, known = datetime.fromisoformat(effective_at), datetime.fromisoformat(known_on)
    if cutoff.tzinfo is None or known.tzinfo is None:
        raise ValueError("Effective and knowledge timestamps require timezone")
    visible = [
        r
        for r in result["events"]
        if datetime.fromisoformat(r["effective_at"]) <= cutoff
        and datetime.fromisoformat(r["available_at"]) <= known
    ]
    return visible[-1] if visible else None


def verify_source_expense(result, anchor_rows):
    parent = result["expense_bridge"]["parent"]
    rows = [
        r
        for r in anchor_rows
        if r["journal_id"] == parent["journal_id"]
        and r["source_id"] == parent["source_id"]
        and r["account"] == parent["source_account"]
    ]
    if sum(D(r["signed_usd"]) for r in rows) != D(parent["amount_usd"]):
        raise ValueError("September expense envelope does not match retained independent journal")
    return {"reconciled_parent_usd": parent["amount_usd"], "additional_journal_usd": "0.00"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build()
    sources = (
        SOURCE,
        SEPTEMBER_SOURCE,
        result["source"]["qualification_path"],
        "enterprise/operations/september_custody.py",
        "enterprise/ccf/company_closeout/shipment.py",
    )
    result["source_hashes"] = {
        p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources
    }
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    target = args.output / "records.json"
    if args.check:
        if not target.exists() or target.read_text() != payload:
            raise SystemExit("Stale September custody derivative")
    else:
        args.output.mkdir(parents=True, exist_ok=True)
        target.write_text(payload)
    print(json.dumps(result["expense_bridge"], indent=2))


if __name__ == "__main__":
    main()
