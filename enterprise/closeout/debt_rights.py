"""Approved ARU-only security schedule; execution, filing and priority stay separate."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

from .finance_administration import build as administrative_register

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "enterprise/closeout/source/aru_secured_terms.json"
OPERATIONS = ROOT / "industrial/source/operations.json"


def build(*, as_of="2026-09-22", source=None, operations=None):
    policy = source if source is not None else json.loads(SOURCE.read_text())
    ops = operations if operations is not None else json.loads(OPERATIONS.read_text())
    entities = json.loads((ROOT / "industrial/source/entities.json").read_text())["entities"]
    aru = next(e for e in entities if e["entity_id"] == "ARU")
    if aru["jurisdiction"] != "Wyoming" or aru["legal_form"] != "corporation":
        raise ValueError("Debtor jurisdiction requires new authority analysis")
    native = json.loads((ROOT / "industrial/source/finance.json").read_text())["transaction"]
    forecast = json.loads((ROOT / "industrial/planning/source/forecast.json").read_text())["debt"]
    if (
        policy["effective_date"] != "2026-09-22"
        or policy["synthetic_execution"]["date"] != policy["effective_date"]
    ):
        raise ValueError("Prospective adoption date changed")
    if (
        policy["synthetic_execution"]["real_signature_or_filing_claimed"]
        or policy["filing_states"]["submission"] != "NOT_SUBMITTED"
        or policy["filing_states"]["perfection"] != "NOT_ESTABLISHED"
    ):
        raise ValueError("Unsupported filing/perfection state")
    terms = policy["terms"]
    if (
        terms["original_principal_usd"] != native["new_debt"]
        or terms["quarterly_principal_usd"] != native["new_debt_quarterly_principal"]
        or terms["first_principal_date"] != native["new_debt_first_payment"]
        or terms["maturity"] != forecast["legacy_term_maturity"]
        or terms["ordinary_interest_pct"] != str(native["new_debt_rate_pct"])
    ):
        raise ValueError("Existing debt economics changed")
    if (
        policy["borrower"] != "ARU"
        or terms["guarantors"]
        or terms["cross_entity_collateral"]
        or terms["new_borrowing_usd"]
    ):
        raise ValueError("Approved borrower/guarantee/financing boundary changed")
    if (
        terms["prepayment_premium_pct"] != "0"
        or terms["default_rate_uplift_pct"] != "0"
        or terms["financial_maintenance_covenants"]
    ):
        raise ValueError("Unapproved creditor term")
    admin = administrative_register(operations=ops)
    index = {
        r["id"]: (pop, r)
        for pop in (
            "facilities",
            "track_segments",
            "structures",
            "locomotives",
            "railcars",
            "road_equipment",
            "handling_equipment",
        )
        for r in ops[pop]
    }
    facilities = {r["id"]: r for r in ops["facilities"]}
    ids = policy["collateral_ids"]
    expected = {
        r["id"]
        for pop in ("track_segments", "road_equipment")
        for r in ops[pop]
        if r.get("owner") == aru["legal_name"]
    }
    expected.update(r["id"] for r in ops["handling_equipment"])
    if len(ids) != 64 or len(set(ids)) != 64 or set(ids) != expected:
        raise ValueError("Exact approved collateral population differs")
    confirmations = policy["handling_owner_confirmations"]
    if (
        len(confirmations) != 14
        or {r["asset_id"] for r in confirmations} != {r["id"] for r in ops["handling_equipment"]}
        or any(r["owner"] != "ARU" for r in confirmations)
    ):
        raise ValueError("Handling ownership completion population differs")
    grant_day = date.fromisoformat(policy["effective_date"])
    effective = date.fromisoformat(as_of) >= grant_day
    rows = []
    for identity in ids:
        pop, r = index[identity]
        if r.get("ownership") == "leased":
            raise ValueError("Leased asset cannot be granted")
        if pop == "handling_equipment":
            if (
                r.get("ownership") != "owned"
                or facilities.get(r.get("facility_id"), {}).get("owner") != aru["legal_name"]
            ):
                raise ValueError("Handling source does not support authored ARU ownership")
        elif r.get("owner") != aru["legal_name"]:
            raise ValueError("Other entity collateral")
        service = r.get("in_service_date")
        if service and date.fromisoformat(service) > grant_day:
            raise ValueError("Future asset cannot enter present grant")
        if r.get("model_year", grant_day.year) > grant_day.year:
            raise ValueError("Future equipment cannot enter present grant")
        status = r.get("status", r.get("condition", ""))
        if pop == "road_equipment" and status not in {
            "available",
            "rotating maintenance",
            "serviceable under commodity qualification",
        }:
            raise ValueError("Road equipment present-ownership scope needs review")
        if pop == "handling_equipment" and status != "serviceable; planned replacement reserve":
            raise ValueError("Handling status scope needs review")
        route = {
            "road_equipment": "CANDIDATE_WY_COUNTY_CLERK_ROUTE_SUBJECT_TO_TITLE_JURISDICTION_CONFIRMATION",
            "track_segments": "WY_FIXTURE_REAL_PROPERTY_RECORD_ROUTE_PARCEL_DESCRIPTION_PENDING",
            "handling_equipment": "WY_SECRETARY_OF_STATE_ARTICLE9_GENERAL_FILING_PREPARATION",
        }[pop]
        rows.append(
            {
                "collateral_id": "SH-ARU-COLLATERAL-" + identity,
                "asset_id": identity,
                "grantor": "ARU",
                "population": pop,
                "description": r.get("kind", r.get("name", identity)),
                "facility_id": r.get("facility_id"),
                "source_in_service_date": service,
                "model_year": r.get("model_year"),
                "source_status": status,
                "ownership_origin": "NEWLY_AUTHORED_EXISTING_GOOD_OWNER_CONFIRMATION"
                if pop == "handling_equipment"
                else "ACCEPTED_SOURCE_OWNER",
                "grant_effective_date": policy["effective_date"],
                "grant_state": "SYNTHETIC_LIMITED_GRANT_EXECUTED"
                if effective
                else "NOT_YET_EFFECTIVE",
                "filing_route": route,
                "filing_submission": "NOT_SUBMITTED",
                "filing_acknowledgement": None,
                "perfection": "NOT_ESTABLISHED",
                "priority": "NOT_ESTABLISHED",
                "collateral_value_usd": None,
                "scope": "Only represented ARU-owned goods/fixture interest; no underlying fee-simple land or building mortgage",
            }
        )
    report = {
        "obligation_id": "SH-ARU-DEBT-REPORT-2026Q3",
        "period_end": "2026-09-30",
        "due_date": str(date(2026, 9, 30) + timedelta(days=terms["quarterly_reporting_days"])),
        "state": "FUTURE_DUE"
        if date.fromisoformat(as_of) < date(2026, 9, 30)
        else "PERFORMANCE_NOT_ASSERTED",
        "evidence": None,
        "owner": "ARU_CONTROLLER_TREASURY",
        "recipient": policy["creditor_party_id"],
    }
    return {
        "record_id": policy["document_id"],
        "effective_date": policy["effective_date"],
        "as_of": as_of,
        "terms": terms,
        "synthetic_execution": dict(
            policy["synthetic_execution"],
            state=policy["synthetic_execution"]["state"] if effective else "NOT_YET_EFFECTIVE",
        ),
        "collateral": rows,
        "context_only_facilities": policy["excluded_context_facilities"],
        "excluded_asset_count": 78,
        "reporting_obligations": [report],
        "event_notice": {
            "trigger": "DISCOVERED_MATERIAL_PAYMENT_OR_COLLATERAL_DISPUTE",
            "business_days": 5,
            "performance": "NO_OCCURRENCE_ASSERTED_BY_THIS_PROVIDER",
        },
        "payoff_components": admin["payoff_components"],
        "old_lien_release": "NOT_ESTABLISHED",
        "additional_journal_count": 0,
        "additional_cash_usd": 0,
        "source_hashes": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (
                SOURCE,
                OPERATIONS,
                ROOT / "industrial/source/entities.json",
                ROOT / "industrial/source/finance.json",
                ROOT / "industrial/planning/source/forecast.json",
            )
        },
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
