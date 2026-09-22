"""Dated fictional administrative completion; no new grant or monetary posting."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from enterprise.operations.availability import repository_context

from . import debt_rights

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "enterprise/closeout/source/debt_administration_2026_09_22.json"


def require(value, message):
    if not value:
        raise ValueError(message)


def stamp(value):
    parsed = datetime.fromisoformat(value)
    require(parsed.tzinfo is not None, "Timezone required")
    return parsed.astimezone(UTC)


def build(*, source=None, as_of="2026-09-22T23:59:59Z", context=None):
    data = source if source is not None else json.loads(SOURCE.read_text())
    context = context or repository_context(ROOT)
    predecessor = debt_rights.build()
    approved = {r["asset_id"]: r for r in predecessor["collateral"]}
    for path, expected in data["source_hashes"].items():
        require(
            hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected,
            "Source drift: " + path,
        )
    require(data["grant_id"] == predecessor["record_id"], "Wrong grant")
    require(not data["real_external_action"], "Real action unsupported")
    require(
        stamp(data["grant_executed_at"]).date().isoformat() == predecessor["effective_date"],
        "No grant backdating",
    )
    assets = data["assets"]
    require(
        len(assets) == 64 and {r["asset_id"] for r in assets} == set(approved),
        "Exact collateral population required",
    )
    require(len({r["identifier"] for r in assets}) == 64, "Duplicate asset identifier")
    for row in assets:
        native = approved[row["asset_id"]]
        require(
            row["owner"] == "ARU" and row["facility_id"] == native["facility_id"],
            "Wrong owner or location",
        )
        require(row["source_status"] == native["source_status"], "Changed source condition")
        if row["source_population"] == "road_equipment":
            require(
                row["title_jurisdiction"] == "Wyoming"
                and row["title_id"]
                and row["filing_route"] == "SWEETWATER_TITLES",
                "Title jurisdiction/route",
            )
        elif row["source_population"] == "handling_equipment":
            require(row["filing_route"] == "SOS_GOODS", "Goods filing route")
        else:
            require(
                row["source_population"] == "track_segments"
                and row["filing_route"] == "SWEETWATER_FIXTURES",
                "Fixture route",
            )
    require(
        len(data["fixture_sites"]) == 2
        and {r["facility_id"] for r in data["fixture_sites"]}
        == {"FAC-TAY-TERMINAL", "FAC-TAY-WAREHOUSE"},
        "Fixture-site population",
    )
    for row in data["fixture_sites"]:
        require(
            row["county_geoid"] == "56037"
            and not row["real_cadastral_identity"]
            and row["description"]
            and row["record_owner_name"] == "American Resource Utility, Inc.",
            "Fixture identity/rights",
        )
    routes = {"SOS_GOODS": 14, "SWEETWATER_TITLES": 44, "SWEETWATER_FIXTURES": 6}
    require(
        len(data["filings"]) == 3 and {r["route"] for r in data["filings"]} == set(routes),
        "Filing population",
    )
    for row in data["filings"]:
        expected = {a["asset_id"] for a in assets if a["filing_route"] == row["route"]}
        require(
            len(row["asset_ids"]) == routes[row["route"]] and set(row["asset_ids"]) == expected,
            "Filing collateral scope",
        )
        require(
            stamp(data["grant_executed_at"])
            <= stamp(row["authorized_at"])
            <= stamp(row["submitted_at"])
            <= stamp(row["acknowledged_at"]),
            "Filing authority/chronology",
        )
        require(
            not row["real_filing"] and row["acknowledgement_id"].startswith("SYN-"),
            "Synthetic filing boundary",
        )
        require(
            row["debtor"] == "American Resource Utility, Inc."
            and row["creditor"]
            == predecessor["terms"].get(
                "creditor", json.loads(debt_rights.SOURCE.read_text())["creditor_name"]
            ),
            "Wrong debtor or creditor",
        )
    payoff = {r["component_id"]: r for r in predecessor["payoff_components"]}
    releases = data["payoff_releases"]
    require(
        len(releases) == 2 and {r["payoff_component_id"] for r in releases} == set(payoff),
        "Payoff release population",
    )
    for row in releases:
        expected = payoff[row["payoff_component_id"]]
        require(
            int(row["principal_received_usd"]) == int(expected["principal_usd"]),
            "Existing payoff amount changed",
        )
        require(
            row["original_settlement_date"] == "2026-01-07"
            and stamp(row["release_effective_at"]).date().isoformat() == "2026-09-22",
            "Release is current, not retroactive",
        )
        require(
            row["new_cash_usd"] == row["new_debt_usd"] == "0"
            and row["retained_leases_excluded_usd"] == "2500000",
            "Duplicate payoff/lease",
        )
    fee = data["fee_allocation"]
    finance = json.loads((ROOT / "industrial/source/finance.json").read_text())
    envelope = finance["segment_baseline"]["ARU"]["opex"]
    require(
        envelope == fee["source_annual_opex_usd"] == 200000
        and fee["amount_usd"] == "250.00"
        and fee["additional_journal_usd"] == fee["additional_cash_usd"] == "0.00",
        "Expense allocation must preserve source aggregate",
    )
    boundary = stamp(as_of)
    available = max(stamp(data["authored_at"]), stamp(context["repository_source_available_at"]))
    return dict(
        document_id=data["document_id"],
        assets=assets,
        fixture_sites=data["fixture_sites"],
        filings=[
            r
            | {
                "as_of_state": "SYNTHETIC_ACKNOWLEDGED"
                if stamp(r["acknowledged_at"]) <= boundary
                else "NOT_YET_ACKNOWLEDGED"
            }
            for r in data["filings"]
        ],
        payoff_releases=[
            r
            | {
                "as_of_state": "SYNTHETIC_RELEASE_DELIVERED"
                if stamp(r["release_effective_at"]) <= boundary
                else "NOT_YET_RELEASED"
            }
            for r in releases
        ],
        fee_allocation=fee,
        search=data["search"]
        | {
            "as_of_state": "SYNTHETIC_SEARCH_COMPLETE"
            if stamp(data["search"]["search_at"]) <= boundary
            else "NOT_YET_CONDUCTED"
        },
        priority_policy=data["priority_policy"],
        source_hashes=data["source_hashes"]
        | {str(SOURCE.relative_to(ROOT)): hashlib.sha256(SOURCE.read_bytes()).hexdigest()},
        available_at=available.isoformat().replace("+00:00", "Z"),
        as_of=as_of,
        **context,
        additional_journal_usd="0.00",
        additional_cash_usd="0.00",
    )
