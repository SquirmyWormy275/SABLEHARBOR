"""Approved prospective host terms; no permission arises without an accepted order."""

import json
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).parent / "source/host_terms_adoption.json"


def validate(data=None, *, root=ROOT):
    data = json.loads(SOURCE.read_text()) if data is None else data

    def require(value, message):
        if not value:
            raise ValueError(message)

    require(data["approval"]["exact_quote"] == "Adopt B and its common terms", "owner authority")
    proposal = data["proposal"]
    require(
        sha256((root / proposal["path"]).read_bytes()).hexdigest() == proposal["sha256"],
        "proposal bytes",
    )
    terms = data["common_terms"]
    for key, expected in {
        "maximum_order_days": 90,
        "early_exit_received_notice_days": 30,
        "statement_after_month_end_days": 20,
        "undisputed_payment_after_received_statement_days": 30,
        "automatic_renewal": False,
        "continuous_access_between_orders": False,
        "guaranteed_feed": False,
        "permanent_host_rate": None,
        "real_execution": False,
        "mandatory_law_preserved": True,
    }.items():
        require(terms[key] == expected, f"approved term {key}")
    instruments = data["instruments"]
    require(
        len(instruments) == 2 and {i["host_id"] for i in instruments} == {"KGM", "DEMOTTE"},
        "separate hosts",
    )
    indexed = {i["instrument_id"]: i for i in instruments}
    require(len(indexed) == 2, "duplicate instrument")
    for i in instruments:
        require(
            i["SH_legal_entity_id"] == "SHI" and i["SH_legal_party"] == "Sable Harbor, LLC",
            "legal party",
        )
        require(i["SH_representative"]["person_id"] == "P025", "delegated SH representative")
        require(
            i["host_representative"]["person_id"] == f"SYN-HOST-{i['host_id']}-REP-001",
            "host representative",
        )
        require(i["framework_eligible_from"] == "2026-10-01", "prospective eligibility")
        require(
            i["exclusivity"]
            == (
                "Designated Stream 17 run/material during the accepted active work order only"
                if i["host_id"] == "KGM"
                else "No new exclusive grant"
            ),
            "exclusivity scope",
        )
        require(
            i["governing_law"]
            == ("Tasmania, Australia" if i["host_id"] == "KGM" else "West Virginia, United States"),
            "local law",
        )
        require(i["exclusive_forum"] is False, "nonexclusive forum")
    for amount in data["financial_effects"].values():
        require(Decimal(amount) == 0, "framework monetary effect")
    seen = set()
    for order in data["accepted_work_orders"]:
        require(order["order_id"] not in seen, "duplicate order")
        seen.add(order["order_id"])
        require(order["instrument_id"] in indexed, "unknown instrument")
        instrument = indexed[order["instrument_id"]]
        start, end = date.fromisoformat(order["start"]), date.fromisoformat(order["end"])
        require(
            start >= date.fromisoformat(instrument["framework_eligible_from"]), "backdated access"
        )
        require(1 <= (end - start).days + 1 <= 90, "order duration")
        require(
            order["SH_acceptor"] == instrument["SH_representative"]["person_id"]
            and order["host_acceptor"] == instrument["host_representative"]["person_id"],
            "order authority",
        )
        received = datetime.fromisoformat(order["acceptance_received_at"])
        executed = datetime.fromisoformat(instrument["synthetic_execution_recorded_at"])
        require(
            received.tzinfo is not None and executed.tzinfo is not None and received >= executed,
            "acceptance predates instrument and delegation",
        )
        require(
            received.tzinfo is not None
            and received.astimezone(UTC) <= datetime.combine(start, time.min, tzinfo=UTC),
            "acceptance before operation",
        )
        require(order["scope"] and order["interface_revision"], "scope and interface")
        for key in (
            "eligible_proceeds",
            "deductions",
            "currency",
            "host_payment_formula",
            "cost_responsibility",
        ):
            require(
                isinstance(order["economics"].get(key), str) and order["economics"][key].strip(),
                "explicit order economics",
            )
        if instrument["host_id"] == "DEMOTTE" and order["sale_capable"]:
            require(order.get("capture_title_point"), "Demotte commercial title")
        if order.get("early_exit_at"):
            notice = datetime.fromisoformat(order["exit_notice_received_at"])
            exit_at = datetime.fromisoformat(order["early_exit_at"])
            require(
                notice.tzinfo and exit_at.tzinfo and exit_at >= notice + timedelta(days=30),
                "received exit notice",
            )
    return {
        "instruments": 2,
        "accepted_work_orders": len(seen),
        "new_cash_usd": "0",
        "repository_acceptance_claimed": False,
    }
