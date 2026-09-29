"""Explicit successor populations in the existing enterprise CSV/SQLite contract."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from enterprise.operations import exports
from enterprise.operations.availability import repository_context

ROOT = Path(__file__).resolve().parents[2]
EXTENSION = ROOT / "enterprise/closeout/source/successor_export_extension.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def file_hash(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def contracts():
    """Merge reviewed explicit permissions, never permissions inferred from rows."""
    extension = json.loads(EXTENSION.read_text())
    for kind in ["schema", "scope"]:
        require(
            file_hash(f"enterprise/operations/export_{kind}.json")
            == extension[f"base_{kind}_sha256"],
            "Predecessor contract changed",
        )
    schema, scope = json.loads(exports.SCHEMA.read_text()), json.loads(exports.SCOPE.read_text())
    require(not (set(schema) & set(extension["schema"])), "Successor table name collision")
    require(set(extension["schema"]) == set(extension["scope"]), "Extension scope incomplete")
    schema.update(extension["schema"])
    scope.update(extension["scope"])
    return schema, scope


def collect(context=None):
    from enterprise.ccf.company_closeout import host_terms
    from enterprise.closeout import capital_rights, finance_administration
    from enterprise.operations import j2_administrative_history as j2
    from enterprise.operations import orientation_commissions as oo

    context = context or repository_context(ROOT)
    extension = json.loads(EXTENSION.read_text())
    tables = {name: [] for name in extension["schema"]}
    floor = datetime.fromisoformat(context["repository_source_available_at"])
    require(floor.tzinfo is not None, "Source availability timezone required")

    def add(
        table,
        identifier,
        kind,
        entity,
        unit,
        start,
        end,
        source,
        payload,
        *,
        hashes=None,
        authored="2026-09-22T00:00:00Z",
        status="PENDING_REPOSITORY_ACCEPTANCE",
    ):
        pins = dict(hashes or {})
        pins[source] = file_hash(source)
        for path, expected in pins.items():
            require(file_hash(path) == expected, "Stale provider source: " + path)
        available = (
            max(floor, datetime.fromisoformat(authored))
            .astimezone(UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )
        tables[table].append(
            dict(
                record_id=identifier,
                record_type=kind,
                entity=entity,
                unit=unit,
                effective_from=start,
                effective_to=end or "",
                effective_precision="DAY",
                available_at=available,
                recorded_at=available,
                authored_day=authored[:10],
                fact_state="NEWLY_AUTHORED_SYNTHETIC_SUCCESSOR",
                record_origin="PUBLIC_SYNTHETIC_DIEGETIC",
                scenario="",
                source_path=source,
                source_sha256=pins[source],
                source_hashes_json=canonical(pins),
                source_commit=context["repository_source_commit"],
                publication_state=context["publication_state"],
                acceptance_status=status,
                payload_json=canonical(payload),
                additional_cash_usd="0.00",
            )
        )

    data = j2.build(context)
    for row in data["events"]:
        add(
            "successor_j2_administration",
            row["record_id"],
            "CURRENT_OFFICE_ADMINISTRATIVE_HISTORY",
            "SHI",
            "CORPORATE",
            row["current_office_appointment_date"],
            None,
            j2.SOURCE,
            row,
            hashes=data["source_hashes"],
        )
    data = oo.build(context)
    for row in data["records"]:
        add(
            "successor_orientation_commissions",
            row["record_id"],
            "ORIENTATION_COMMISSION",
            "SHI",
            "CORPORATE",
            row["commission"]["start"],
            row["commission"]["end_exclusive"],
            oo.SOURCE,
            row,
            hashes=data["source_hashes"],
        )
    admin = finance_administration.build()
    admin_source = "enterprise/closeout/finance_administration.py"
    for row in admin["payoff_components"]:
        add(
            "successor_debt_payoff",
            row["component_id"],
            "HISTORICAL_MODELED_PAYOFF_ALLOCATION",
            row["borrower"],
            "american-resource-utility",
            row["effective_on"],
            None,
            admin_source,
            row,
            hashes=admin["source_hashes"],
            status=admin["acceptance_status"],
        )
    owners = {
        "American Resource Utility, Inc.": "ARU",
        "Blood, Sweat & Tears Railway Company": "BST",
        "Red Wash Mining, LLC": "RWH",
    }
    for row in admin["asset_screen"]:
        entity = owners.get(
            row["source_owner"], "EXTERNAL" if row["source_owner"] else "UNRESOLVED"
        )
        unit = "pale-sun" if entity == "RWH" else "american-resource-utility"
        add(
            "successor_asset_screen",
            "SH-ASSET-SCREEN-" + row["asset_id"],
            "ADMINISTRATIVE_ASSET_SOURCE_SCREEN",
            entity,
            unit,
            "2026-09-22",
            None,
            admin_source,
            row,
            hashes=admin["source_hashes"],
            status=admin["acceptance_status"],
        )
    for row in admin["secretary_source_inventory"]:
        add(
            "successor_finance_source_inventory",
            "SH-FIN-SOURCE-" + hashlib.sha256(row["path"].encode()).hexdigest()[:20],
            "SCOPED_SECRETARY_SOURCE_INVENTORY",
            "SHI",
            "CORPORATE",
            "2026-09-22",
            None,
            admin_source,
            row,
            hashes=admin["source_hashes"],
            status=admin["acceptance_status"],
        )
    capital = capital_rights.build()
    source = str(capital_rights.SOURCE.relative_to(ROOT))
    capital_policy = json.loads(capital_rights.SOURCE.read_text())
    for row in capital["rights"]:
        add(
            "successor_capital_rights",
            capital["record_id"] + "/" + row["holder_id"],
            "PROSPECTIVE_DESIGNATION_RIGHT",
            "SHI",
            "CORPORATE",
            capital["effective_date"],
            None,
            source,
            {
                "designation": row,
                "policy": capital_policy,
                "board_director_ids": capital["board_director_ids"],
            },
            hashes=capital["source_hashes"],
        )
    for row in capital["synthetic_assents"]:
        add(
            "successor_capital_assents",
            capital["record_id"] + "/ASSENT/" + row["holder_id"],
            "SYNTHETIC_MEMBER_ASSENT",
            "SHI",
            "CORPORATE",
            row["date"],
            None,
            source,
            row,
            hashes=capital["source_hashes"],
        )
    host = json.loads(host_terms.SOURCE.read_text())
    host_terms.validate(host)
    source = str(host_terms.SOURCE.relative_to(ROOT))
    require(
        host["accepted_work_orders"] == [],
        "Host order population requires reviewed scope successor",
    )
    for row in host["instruments"]:
        add(
            "successor_host_instruments",
            row["instrument_id"],
            "PROSPECTIVE_HOST_FRAMEWORK",
            row["SH_legal_entity_id"],
            "project-cradle",
            row["framework_eligible_from"],
            None,
            source,
            {
                "instrument": row,
                "common_terms": host["common_terms"],
                "accepted_work_orders": [],
                "financial_effects": host["financial_effects"],
            },
            hashes={host["proposal"]["path"]: host["proposal"]["sha256"]},
            authored=host["authored_at"],
            status=host["repository_status"],
        )
    _debt_tables(add)
    _validate_structure(tables, extension)
    return tables


def _debt_tables(add):
    from enterprise.closeout import debt_rights

    data = debt_rights.build()
    source = "enterprise/closeout/source/aru_secured_terms.json"
    require(data["additional_cash_usd"] == 0, "Debt adapter cannot create cash")
    summary = {key: value for key, value in data.items() if key != "collateral"}
    add(
        "successor_debt_instruments",
        data["record_id"],
        "PROSPECTIVE_LIMITED_SECURED_TERMS",
        "ARU",
        "american-resource-utility",
        data["effective_date"],
        None,
        source,
        summary,
        hashes=data["source_hashes"],
    )
    for row in data["collateral"]:
        add(
            "successor_debt_collateral",
            row["collateral_id"],
            "ASSET_IDENTIFIED_LIMITED_GRANT",
            row["grantor"],
            "american-resource-utility",
            row["grant_effective_date"],
            None,
            source,
            row,
            hashes=data["source_hashes"],
        )


def _validate_structure(tables, extension):
    require(set(tables) == set(extension["schema"]), "Successor table population mismatch")
    exports.validate_schema(tables, extension["schema"], extension["scope"])
    for name, count in extension["population_counts"].items():
        require(len(tables[name]) == count, "Successor row population mismatch: " + name)
    for name, rows in tables.items():
        require(
            len({r["record_id"] for r in rows}) == len(rows), "Duplicate successor record: " + name
        )
        for row in rows:
            require(row["additional_cash_usd"] == "0.00", "Administrative export cannot post cash")
            require(
                datetime.fromisoformat(row["available_at"])
                >= datetime.fromisoformat(row["authored_day"] + "T00:00:00Z"),
                "Earlier known-on",
            )
            require(
                canonical(json.loads(row["payload_json"])) == row["payload_json"],
                "Noncanonical payload",
            )


def validate_tables(tables, context=None):
    extension = json.loads(EXTENSION.read_text())
    _validate_structure(tables, extension)
    expected = collect(context)
    for name, rows in tables.items():
        require(
            {r["record_id"]: r for r in rows} == {r["record_id"]: r for r in expected[name]},
            "Stale or incompatible successor source: " + name,
        )
    return {
        "counts": {name: len(rows) for name, rows in tables.items()},
        "additional_cash_usd": "0.00",
    }


def visible(tables, *, effective_on, known_on):
    cutoff = datetime.fromisoformat(known_on)
    require(cutoff.tzinfo is not None, "Known-on timezone required")
    return {
        name: [
            r
            for r in rows
            if r["publication_state"] != "DIRTY_WORKING_COPY_PREVIEW_NOT_PUBLISHABLE"
            and r["effective_from"] <= effective_on
            and (not r["effective_to"] or effective_on < r["effective_to"])
            and datetime.fromisoformat(r["available_at"]) <= cutoff
        ]
        for name, rows in tables.items()
    }
