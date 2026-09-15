"""Reperform selected radon, existing bond and benefit administration records."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

DIRECTORY = Path(__file__).parent
ROOT = DIRECTORY.parents[2]


def read(name):
    return json.loads((DIRECTORY / name).read_text())


def validate_environment(data, root=ROOT):
    for path, digest in data["source_hashes"].items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
            raise ValueError("Stale environment source")
    if data["available_on"] < data["authored_on"] or data["event_period"] != "2026-08":
        raise ValueError("Environment availability/period")
    radon = data["radon"]
    cells = radon["cells"]
    if len(cells) != 1 or cells[0]["id"] != "RW-TAILINGS-CELL-1":
        raise ValueError("Selected cell population")
    if (
        radon["other_operating_or_standby_cells"]
        or radon["nonconventional_impoundments"]
        or radon["heap_leach_piles"]
    ):
        raise ValueError("Changed population requires new applicability")
    c = cells[0]
    if c["construction_year"] <= 1989 or c["category"] != "NEW_CONVENTIONAL_PHASED":
        raise ValueError("Wrong radon category")
    if not c["lined"] or not Decimal("0") < Decimal(c["area_acres"]) <= Decimal("40"):
        raise ValueError("Phased liner/area requirement")
    test = radon["liner_compatibility"]
    if (
        Decimal(test["retained_tensile_strength_pct"]) < Decimal(test["design_acceptance_min_pct"])
        or test["visual_cracks"]
    ):
        raise ValueError("Failed compatibility cannot be promoted")
    rows = radon["daily_workpractice"]
    if len(rows) != 31 or {r["on"] for r in rows} != {f"2026-08-{i:02}" for i in range(1, 32)}:
        raise ValueError("Daily radon population missing/duplicate")
    for row in rows:
        if (
            row["cell_id"] != c["id"]
            or row["area_acres"] != c["area_acres"]
            or row["operating_cells"] > 2
        ):
            raise ValueError("Daily area/count mismatch")
        if row["preparer_id"] == row["reviewer_id"] or row["uncontrolled_new_cell"]:
            raise ValueError("Review or unreviewed construction")
    if (
        radon["dispositions"]["method115_result"] is not None
        or radon["dispositions"]["liner_ongoing_performance"]
        != "MW17_UNDERDRAIN_INVESTIGATION_OPEN"
    ):
        raise ValueError("Unsupported emissions/clean pathway assertion")
    bond = data["bond"]
    if (
        bond["instrument_id"] != "BOND-RW-2026"
        or bond["principal"] != "RWH"
        or bond["additional_parent_guarantee"]
    ):
        raise ValueError("Bond identity/new guarantee")
    if any(Decimal(bond[k]) != 0 for k in ["new_cash_collateral_usd", "new_cash_transaction_usd"]):
        raise ValueError("New cash security not authorized")
    b = bond["reconciliation"]
    if Decimal(b["bond_face_usd"]) != Decimal(bond["face_usd"]):
        raise ValueError("Bond face mismatch")
    for target, sub in [
        ("face_less_current_cost_usd", "engineering_current_cost_usd"),
        ("face_less_opening_aro_usd", "opening_accounting_aro_usd"),
    ]:
        if Decimal(b[target]) != Decimal(b["bond_face_usd"]) - Decimal(b[sub]):
            raise ValueError("Bond measurement bridge")
    if Decimal(b["cash_available_from_bond_usd"]) != 0:
        raise ValueError("Surety is not operating cash")
    prior = read("synthetic_permit_instruments_august.json")
    badge = next(e for e in prior["evidence"] if e["id"] == "RW-AUG-EVID-0134")
    if badge["state"] != "MISSING_EVIDENCE":
        raise ValueError("Missing badge result erased")
    return {
        "cells": len(cells),
        "daily_workpractice": len(rows),
        "bond_face_usd": bond["face_usd"],
        "source_missing_badge_preserved": True,
        "mw17_open": True,
    }


def validate_benefits(data, people):
    expected = sorted((p["person_id"], p["legal_employer"]) for p in people)
    digest = hashlib.sha256(json.dumps(expected, separators=(",", ":")).encode()).hexdigest()
    if data["source_population_hash"] != digest:
        raise ValueError("Changed HR population")
    enroll = data["enrollment"]
    actual = [(r["person_id"], r["legal_employer"]) for r in enroll]
    if len(actual) != len(set(actual)) or sorted(actual) != expected:
        raise ValueError("Missing/duplicate benefit population")
    if data["available_on"] < data["authored_on"]:
        raise ValueError("Premature benefit evidence")
    counts = {s: sum(r["state"] == s for r in enroll) for s in ["COVERED", "WAIVED"]}
    if sum(counts.values()) != len(people) or any(r["dependent_count"] for r in enroll):
        raise ValueError("Unsupported enrollment/dependent status")
    review = data["administrative_review"]
    if (
        review["covered"] != counts["COVERED"]
        or review["waived"] != counts["WAIVED"]
        or review["eligibility"] != len(people)
    ):
        raise ValueError("Coverage not eligibility")
    notices = {n["id"] for n in data["notice_documents"]}
    rows = data["distributions"]
    if len(rows) != len(people) or {r["person_id"] for r in rows} != {
        p["person_id"] for p in people
    }:
        raise ValueError("Notice population")
    for r in rows:
        if (
            set(r["document_ids"]) != notices
            or r["preparer_id"] == r["reviewer_id"]
            or r["on"] > "2026-08-31"
        ):
            raise ValueError("Notice content/review/date")
    event = data["september_exit"]
    if event["person_id"] not in {r["person_id"] for r in enroll if r["state"] == "COVERED"}:
        raise ValueError("Exit continuation population")
    notify = date.fromisoformat(event["employer_notice_to_administrator_on"])
    if (notify - date.fromisoformat(event["exit_on"])).days > 30:
        raise ValueError("Late employer notice")
    if (date.fromisoformat(event["election_notice_due"]) - notify).days > 14 or event[
        "election_notice_due"
    ] <= data["authored_on"]:
        raise ValueError("Continuation due classification")
    if event["election_made"] or Decimal(event["cash_received"]):
        raise ValueError("Future election/payment invented")
    if review["diagnosis_fields"] or not data["hipaa"]["no_clinical_claims_at_employer"]:
        raise ValueError("PHI changes applicability")
    return {
        "eligible": len(people),
        **counts,
        "notice_recipients": len(rows),
        "notice_deliveries": len(rows) * len(notices),
        "continuation_notice_state": event["election_notice_state"],
    }


def report(repository=ROOT):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json; from enterprise.operations.completed_period import build; "
            "print(json.dumps(build()['tables']['people']))",
        ],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "environment": validate_environment(read("august_admin_completion.json")),
        "benefits": validate_benefits(
            read("benefit_admin_completion.json"), json.loads(result.stdout)
        ),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--repository", type=Path, default=ROOT)
    print(json.dumps(report(p.parse_args().repository), indent=2))
