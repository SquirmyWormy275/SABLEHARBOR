"""Executed synthetic sponsor plan, empty current award census, prospective grant gate."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from enterprise.operations.availability import repository_context

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "enterprise/closeout/source/advisory_carry_execution_2026_09_22.json"


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_grant(grant, *, outstanding_units=0):
    policy = json.loads(SOURCE.read_text())
    require(
        isinstance(outstanding_units, int)
        and not isinstance(outstanding_units, bool)
        and 0 <= outstanding_units <= 10000,
        "Invalid outstanding units",
    )
    require(set(policy["required_grant_fields"]) <= set(grant), "Incomplete grant documentation")
    require(
        date.fromisoformat(grant["former_j2_end"])
        < date.fromisoformat(grant["participant_initiated_contact"])
        <= date.fromisoformat(grant["grant_date"]),
        "Serving-J2 or backdated contact",
    )
    require(grant["no_serving_promise_attestation"] is True, "No serving promise required")
    require(
        grant["eligibility_gate"] in {"Orientation", "Judgment", "Contact", "Education"},
        "Headquarters alone is not a gate",
    )
    require(grant["eligibility_evidence"], "Missing qualifying service evidence")
    require(
        all(
            isinstance(grant[k], str) and grant[k].strip()
            for k in ["participant_id", "service_start", "employment_classification"]
        ),
        "Missing participant or employment facts",
    )
    require(
        date.fromisoformat(grant["service_start"]) >= date.fromisoformat(grant["grant_date"]),
        "Backdated grant vesting service",
    )
    require(
        isinstance(grant["units"], int)
        and not isinstance(grant["units"], bool)
        and 0 < grant["units"] <= 10000 - outstanding_units,
        "Pool overgrant",
    )
    require(
        Decimal("0") <= Decimal(str(grant["holdback_fraction"])) <= Decimal("1"),
        "Holdback must be fixed before grant",
    )
    require(grant["payment_schedule_acknowledged"] is True, "Fixed payment terms required")
    for field in [
        "legal_review",
        "people_review",
        "finance_review",
        "sponsor_authority",
        "participant_assent",
        "residence_work_jurisdictions",
        "tax_document_reference",
    ]:
        require(grant[field], "Missing approval or jurisdiction: " + field)
    return {
        "status": "DOCUMENTARY_GATE_ONLY",
        "units": grant["units"],
        "qualification_reperformance_required": True,
        "grant_issued": False,
    }


def build(*, source=None, context=None):
    p = source if source is not None else json.loads(SOURCE.read_text())
    context = context or repository_context(ROOT)
    for path, expected in p["source_hashes"].items():
        require(
            hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected,
            "Controlling carry source drift",
        )
    require(p["sponsor"] == "SHI" and p["legal_party"] == "Sable Harbor, LLC", "Wrong sponsor")
    require(
        (
            p["units_authorized"],
            p["unallocated_units"],
            p["pool_pct"],
            p["annual_hurdle_pct"],
            p["default_vesting_years"],
            p["annual_vesting_pct"],
        )
        == (10000, 10000, "20", "10", 5, "20"),
        "Accepted economics changed",
    )
    require(
        not p["issued_grants"] and not p["applications"] and not p["participant_distributions"],
        "Current zero-award census requires scoped successor",
    )
    require(not p["synthetic_execution"]["real_signature_or_counsel_opinion"], "Real execution")
    require(
        p["rights_excluded"]
        == [
            "equity",
            "vote",
            "board_seat",
            "management_authority",
            "anti_dilution",
            "J2_access",
            "IP_title",
            "matter_fee_percentage",
        ],
        "Rights amplification",
    )
    require(all(Decimal(str(v)) == 0 for v in p["financial_effects"].values()), "New economics")
    floor = max(
        datetime.fromisoformat(p["authored_at"]),
        datetime.fromisoformat(context["repository_source_available_at"]),
    )
    return (
        p
        | context
        | {
            "available_at": floor.isoformat().replace("+00:00", "Z"),
            "source_path": str(SOURCE.relative_to(ROOT)),
            "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "participant_count": 0,
            "issued_units": 0,
        }
    )
