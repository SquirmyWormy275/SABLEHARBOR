"""Build the deterministic public Red Wash transaction and operating package.

The three files under ``red_wash/source`` are immutable build inputs. This
builder never reads the legacy mutable ``red_wash/data`` directory. It emits a
strictly allowlisted CSV corpus under ``red_wash/generated`` and a typed,
constraint-backed SQLite database plus manifest under ``red_wash/dist``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import sqlite3
import subprocess
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from red_wash_contract import (
    DATABASE_FILENAME,
    DATASET_BY_FILENAME,
    DATASETS,
    DIST,
    DIST_ALLOWED,
    DIST_MARKER,
    EPISTEMIC_STATES,
    FACT_STATES,
    GENERATED,
    GENERATED_ALLOWED,
    GENERATED_FILENAMES,
    GENERATED_MARKER,
    MANIFEST_FILENAME,
    RECORD_ORIGINS,
    REPOSITORY_ROOT,
    ROOT,
    SOURCE,
    SOURCE_FILENAMES,
    VISUAL_HASHES,
    Dataset,
)

SEED = 20250718
GENERATOR_VERSION = "1.1.0"
SCENARIO_ID = "red-wash-2025-2026"
INPUT_VERSION = "red-wash-public-source/1.1.0"
EFFECTIVE_PERIOD = {
    "from": "2024-08-19",
    "through": "2026-12-31",
    "synthetic_calibration_through": "2026-08-31",
}
BUILT_AT_SEMANTICS = "DETERMINISTIC_CANON_PREPARED_DATE_AT_00_00_00Z_NOT_WALL_CLOCK"

CORE_TOP_LEVEL_FIELDS = frozenset(
    {
        "canon_effective_through",
        "classification",
        "closure",
        "contract_book_2026",
        "dd_and_a_model_2026",
        "diligence_findings",
        "epistemic_mode",
        "finance_2026",
        "inventory_cost_assumptions_2026",
        "location",
        "mine_2026",
        "ownership_history",
        "permit_register",
        "prepared_at",
        "quality_of_earnings",
        "record_id",
        "resource_basis",
        "synthetic_calibration_through",
        "transaction",
        "transaction_timeline",
        "version",
        "workforce_2026",
    }
)

EXTERNAL_SOURCE_FIELDS = (
    "source_id",
    "organization",
    "title",
    "url",
    "use",
    "state",
    "publication_date",
    "accessed_date",
    "covered_period",
    "geography",
    "unit",
    "method",
    "transformation",
    "limitations",
)

BRIDGE_ARRAY_FILES = {
    "transport_capacity_events": "transport_capacity_events.csv",
    "shipment_schedule_exceptions": "shipment_schedule_exceptions.csv",
    "carrier_market_scan": "carrier_market_scan.csv",
    "rail_access_candidates": "rail_access_candidates.csv",
    "fit_gaps": "aru_red_wash_fit_gap.csv",
    "integration_gates": "aru_red_wash_integration_gates.csv",
    "preliminary_capex": "aru_red_wash_preliminary_capex.csv",
    "custody_authority_matrix": "custody_authority_matrix.csv",
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def derive_dd_and_a_usd(core: dict[str, Any]) -> int:
    """Derive selected-case DD&A from controlled cross-record drivers.

    The composite basis deliberately avoids inventing an unsupported asset-class
    allocation: it is the approved aggregate operating-asset amount plus the
    approved capitalized rehabilitation amount. Production is applied against
    the controlled recoverable-pound denominator under the disclosed
    units-of-production model.
    """

    basis = Decimal(core["transaction"]["operating_assets_usd"]) + Decimal(
        core["transaction"]["capitalized_rehabilitation_usd"]
    )
    recoverable_units = Decimal(core["resource_basis"]["recoverable_lb"])
    production_units = Decimal(core["mine_2026"]["produced_u3o8_lb"])
    if basis <= 0 or recoverable_units <= 0 or production_units < 0:
        raise ValueError(
            "DD&A units-of-production drivers must be non-negative with positive basis"
        )
    return int(
        (basis * production_units / recoverable_units).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def require_fields(value: dict[str, Any], expected: set[str] | frozenset[str], label: str) -> None:
    actual = set(value)
    if actual != set(expected):
        missing = sorted(set(expected) - actual)
        unexpected = sorted(actual - set(expected))
        raise ValueError(f"{label} schema mismatch; missing={missing}, unexpected={unexpected}")


def load_inputs() -> tuple[
    dict[str, Any], dict[str, Any], list[dict[str, str]], list[dict[str, object]]
]:
    if not SOURCE.is_dir():
        raise ValueError(f"immutable source directory does not exist: {SOURCE}")
    actual = {entry.name for entry in SOURCE.iterdir()}
    if actual != SOURCE_FILENAMES:
        raise ValueError(
            "source filename allowlist mismatch; "
            f"missing={sorted(SOURCE_FILENAMES - actual)}, "
            f"unexpected={sorted(actual - SOURCE_FILENAMES)}"
        )
    if any(not (SOURCE / name).is_file() for name in SOURCE_FILENAMES):
        raise ValueError("every source allowlist member must be a regular file")

    source_manifest: list[dict[str, object]] = []
    for name in sorted(SOURCE_FILENAMES):
        path = SOURCE / name
        source_manifest.append(
            {
                "path": f"red_wash/source/{name}",
                "bytes": path.stat().st_size,
                "sha256": sha256_path(path),
            }
        )

    core = json.loads((SOURCE / "core_operating_data.json").read_text(encoding="utf-8"))
    bridge = json.loads((SOURCE / "aru_bst_bridge.json").read_text(encoding="utf-8"))
    if not isinstance(core, dict) or not isinstance(bridge, dict):
        raise ValueError("JSON source roots must be objects")
    require_fields(core, CORE_TOP_LEVEL_FIELDS, "core_operating_data")

    external_path = SOURCE / "external_source_register.csv"
    with external_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != EXTERNAL_SOURCE_FIELDS:
            raise ValueError(
                "external_source_register schema mismatch; "
                f"expected={EXTERNAL_SOURCE_FIELDS}, actual={tuple(reader.fieldnames or ())}"
            )
        external = list(reader)
    if not external:
        raise ValueError("external_source_register.csv must not be empty")
    for index, row in enumerate(external, 2):
        if None in row:
            raise ValueError(f"external_source_register.csv row {index} has missing columns")
        for field in EXTERNAL_SOURCE_FIELDS:
            if field != "publication_date" and not (row[field] or "").strip():
                raise ValueError(f"external_source_register.csv row {index} has blank {field}")
        if row["state"] not in {
            "EXTERNAL_RESEARCH",
            "EXTERNAL_RESEARCH_RETROSPECTIVE",
        }:
            raise ValueError(f"external source row {index} has invalid state {row['state']!r}")

    validate_core(core)
    validate_bridge_source(bridge)
    return core, bridge, external, source_manifest


def validate_core(core: dict[str, Any]) -> None:
    if core["record_id"] != "SH-PS-RW-TOR-001":
        raise ValueError("unexpected Red Wash record_id")
    if core["classification"] != "PUBLIC_SYNTHETIC_DIEGETIC":
        raise ValueError("Red Wash package must remain PUBLIC_SYNTHETIC_DIEGETIC")
    if "actual_through" in core:
        raise ValueError("deprecated actual_through field is prohibited")

    def validate_array(name: str, fields: set[str]) -> None:
        value = core[name]
        if not isinstance(value, list) or not value:
            raise ValueError(f"{name} must be a non-empty array")
        for index, row in enumerate(value, 1):
            if not isinstance(row, dict):
                raise ValueError(f"{name}[{index}] must be an object")
            require_fields(row, fields, f"{name}[{index}]")

    require_fields(
        core["location"],
        {
            "county",
            "disturbance_acres",
            "elevation_ft",
            "latitude",
            "longitude",
            "property_acres",
            "state",
        },
        "location",
    )
    require_fields(
        core["transaction"],
        {
            "aro_assumed_usd",
            "capitalized_rehabilitation_usd",
            "cash_consideration_usd",
            "close_date",
            "current_assets_usd",
            "environmental_title_escrow_usd",
            "goodwill_usd",
            "h2_2025_stabilization_usd",
            "holdback_usd",
            "operating_assets_usd",
            "other_liabilities_usd",
            "repair_stabilization_expense_usd",
            "seller_display_name",
            "seller_display_name_state",
            "seller_jurisdiction",
            "seller_jurisdiction_state",
            "seller_legal_name",
            "seller_legal_name_state",
            "transaction_debt_usd",
        },
        "transaction",
    )
    transaction = core["transaction"]
    if any(transaction[field] != value for field, value in {
        "seller_display_name": "Northstar Minerals, Inc.",
        "seller_display_name_state": "LOCKED",
        "seller_legal_name": "Northstar Minerals, Inc.",
        "seller_legal_name_state": "LOCKED",
        "seller_jurisdiction": "Wyoming",
        "seller_jurisdiction_state": "LOCKED",
    }.items()):
        raise ValueError("seller identity must match the approved NMI Wyoming corporation")
    if core["location"]["county"] != "Sweetwater County" or (
        core["location"]["latitude"], core["location"]["longitude"]
    ) != (42.22, -108.18):
        raise ValueError("selected geography must use the approved Great Divide Basin anchor")
    if (
        transaction["operating_assets_usd"]
        + transaction["current_assets_usd"]
        - transaction["aro_assumed_usd"]
        - transaction["other_liabilities_usd"]
        != transaction["cash_consideration_usd"]
    ):
        raise ValueError(
            "transaction value, assumed liabilities, and cash consideration do not tie"
        )
    if (
        transaction["capitalized_rehabilitation_usd"]
        + transaction["repair_stabilization_expense_usd"]
        != transaction["h2_2025_stabilization_usd"]
    ):
        raise ValueError("H2 2025 stabilization capital and expense do not tie")
    if transaction["transaction_debt_usd"] != 0 or transaction["goodwill_usd"] != 0:
        raise ValueError("transaction debt and goodwill must remain zero")
    require_fields(
        core["resource_basis"],
        {
            "base_value_includes_inferred",
            "contained_lb",
            "grade_u3o8_pct",
            "indicated_tons",
            "inferred_grade_u3o8_pct",
            "inferred_tons",
            "modeled_recovery_pct",
            "recoverable_lb",
        },
        "resource_basis",
    )

    require_fields(
        core["mine_2026"],
        {
            "contained_u3o8_lb",
            "ending_finished_inventory_lb",
            "head_grade_u3o8_pct",
            "method",
            "nameplate_tpd",
            "opening_finished_inventory_lb",
            "ore_tons",
            "planned_depth_ft",
            "produced_u3o8_lb",
            "recovery_pct",
            "sold_u3o8_lb",
        },
        "mine_2026",
    )
    require_fields(
        core["workforce_2026"],
        {"pale_sun_business_layer", "red_wash_site", "site_functions", "total_fte"},
        "workforce_2026",
    )
    require_fields(
        core["workforce_2026"]["site_functions"],
        {
            "environmental_permitting",
            "geology_resource_control",
            "maintenance_reliability",
            "mill_metallurgy",
            "safety_radiation",
            "security_medical_emergency",
            "site_finance_people_administration",
            "site_general_management",
            "supply_warehouse",
            "underground_operations",
        },
        "workforce_2026.site_functions",
    )
    require_fields(
        core["inventory_cost_assumptions_2026"],
        {
            "epistemic_state",
            "fact_state",
            "income_tax_rate_pct",
            "opening_finished_inventory_cash_cost_usd_lb",
            "opening_finished_inventory_dd_and_a_usd_lb",
            "other_working_capital_use_usd",
        },
        "inventory_cost_assumptions_2026",
    )
    require_fields(
        core["dd_and_a_model_2026"],
        {
            "asset_basis_component_paths",
            "boundary",
            "epistemic_state",
            "fact_state",
            "method",
            "production_units_source_path",
            "recoverable_units_source_path",
            "rounding",
        },
        "dd_and_a_model_2026",
    )
    dd_and_a_model = core["dd_and_a_model_2026"]
    if dd_and_a_model != {
        "method": "COMPOSITE_UNITS_OF_PRODUCTION",
        "asset_basis_component_paths": [
            "transaction.operating_assets_usd",
            "transaction.capitalized_rehabilitation_usd",
        ],
        "recoverable_units_source_path": "resource_basis.recoverable_lb",
        "production_units_source_path": "mine_2026.produced_u3o8_lb",
        "rounding": "ROUND_HALF_UP_TO_WHOLE_USD",
        "fact_state": "MODEL_PROPOSED",
        "epistemic_state": "SUPPORTED_ESTIMATE",
        "boundary": (
            "Simplified selected-case composite units-of-production model; it does not "
            "allocate purchase-price classes or establish audited GAAP useful lives, tax "
            "basis, or DD&A."
        ),
    }:
        raise ValueError("DD&A model must preserve its explicit controlled drivers and boundary")
    require_fields(
        core["finance_2026"],
        {
            "aro_accretion_usd",
            "cash_production_cost_incurred_usd",
            "freight_assay_handling_usd",
            "pale_sun_site_g_and_a_usd",
            "production_mineral_taxes_usd",
            "rehabilitation_capex_usd",
            "revenue_usd",
            "royalties_usd",
            "sustaining_capex_usd",
            "weighted_realized_price_usd_lb",
        },
        "finance_2026",
    )
    require_fields(
        core["closure"],
        {
            "cash_flow_years",
            "current_cost_usd",
            "discount_pct",
            "inflation_pct",
            "opening_aro_usd",
            "scopes",
        },
        "closure",
    )
    validate_array(
        "ownership_history",
        {
            "end",
            "epistemic_state",
            "fact_state",
            "owner_display_name",
            "owner_display_name_state",
            "owner_legal_name",
            "owner_legal_name_state",
            "role",
            "start",
        },
    )
    validate_array(
        "contract_book_2026",
        {
            "assignability",
            "buyer",
            "contract_id",
            "delivery_point",
            "origin",
            "pounds",
            "price_usd_lb",
            "structure",
        },
    )
    validate_array(
        "permit_register",
        {"authority", "legal_basis", "number", "permit", "permit_id", "status"},
    )
    validate_array(
        "diligence_findings",
        {"disposition", "domain", "finding", "id", "severity"},
    )
    validate_array("quality_of_earnings", {"amount_usd", "line"})
    validate_array(
        "transaction_timeline",
        {
            "category",
            "date_precision",
            "epistemic_state",
            "event",
            "event_id",
            "fact_state",
            "period",
            "record_origin",
            "source_id",
        },
    )
    assumption = core["inventory_cost_assumptions_2026"]
    if assumption["fact_state"] != "SCENARIO_INPUT":
        raise ValueError("inventory-cost assumptions must remain SCENARIO_INPUT")
    if assumption["epistemic_state"] != "SUPPORTED_ESTIMATE":
        raise ValueError("inventory-cost assumptions must remain SUPPORTED_ESTIMATE")

    ownership = core["ownership_history"]
    for index, row in enumerate(ownership, 1):
        if row["owner_display_name_state"] not in {"LOCKED", "PROVISIONAL", "SCENARIO"}:
            raise ValueError(f"ownership_history[{index}] has invalid display-name state")
        if row["owner_legal_name_state"] not in {"LOCKED", "PROVISIONAL", "OPEN", "SCENARIO"}:
            raise ValueError(f"ownership_history[{index}] has invalid legal-name state")
        if (row["owner_legal_name_state"] == "OPEN") != (row["owner_legal_name"] is None):
            raise ValueError(f"ownership_history[{index}] legal name and OPEN state must agree")
        if row["fact_state"] not in FACT_STATES or row["epistemic_state"] not in EPISTEMIC_STATES:
            raise ValueError(f"ownership_history[{index}] has invalid row provenance")
    northstar = next(row for row in ownership if row["owner_display_name"] == "Northstar Minerals, Inc.")
    current_owner = next(row for row in ownership if row["end"] is None)
    for row, expected in ((northstar, "Northstar Minerals, Inc."), (current_owner, "Pale Sun Inc.")):
        if row["owner_legal_name"] != expected or any(
            row[field] != "LOCKED" for field in ("owner_display_name_state", "owner_legal_name_state")
        ):
            raise ValueError("ownership must preserve the approved separate legal entities")

    mine = core["mine_2026"]
    resource = core["resource_basis"]
    resource_contained = (
        Decimal(resource["indicated_tons"])
        * Decimal(2000)
        * Decimal(str(resource["grade_u3o8_pct"]))
        / Decimal(100)
    )
    resource_recoverable = (
        resource_contained * Decimal(str(resource["modeled_recovery_pct"])) / Decimal(100)
    )
    mine_contained = (
        Decimal(mine["ore_tons"])
        * Decimal(2000)
        * Decimal(str(mine["head_grade_u3o8_pct"]))
        / Decimal(100)
    )
    mine_produced = mine_contained * Decimal(str(mine["recovery_pct"])) / Decimal(100)
    if resource_contained != Decimal(resource["contained_lb"]):
        raise ValueError("resource tons and grade do not reconcile to contained pounds")
    if resource_recoverable != Decimal(resource["recoverable_lb"]):
        raise ValueError(
            "resource contained pounds and recovery do not reconcile to recoverable pounds"
        )
    if mine_contained != Decimal(mine["contained_u3o8_lb"]):
        raise ValueError("mine tons and head grade do not reconcile to contained pounds")
    if mine_produced != Decimal(mine["produced_u3o8_lb"]):
        raise ValueError("mine contained pounds and recovery do not reconcile to production")
    if (
        mine["opening_finished_inventory_lb"] + mine["produced_u3o8_lb"] - mine["sold_u3o8_lb"]
        != mine["ending_finished_inventory_lb"]
    ):
        raise ValueError("core finished-inventory pounds do not roll forward")
    workforce = core["workforce_2026"]
    if workforce["pale_sun_business_layer"] + workforce["red_wash_site"] != workforce["total_fte"]:
        raise ValueError("Pale Sun and Red Wash FTE do not reconcile")
    if sum(workforce["site_functions"].values()) != workforce["red_wash_site"]:
        raise ValueError("Red Wash site functions do not reconcile to site FTE")
    finance = core["finance_2026"]
    contracts = core["contract_book_2026"]
    pounds = sum(item["pounds"] for item in contracts)
    revenue = sum(item["pounds"] * item["price_usd_lb"] for item in contracts)
    if pounds != mine["sold_u3o8_lb"] or revenue != finance["revenue_usd"]:
        raise ValueError("contract book does not reconcile to sales and revenue")
    if Decimal(revenue) / Decimal(pounds) != Decimal(
        str(finance["weighted_realized_price_usd_lb"])
    ):
        raise ValueError("contract book weighted price does not reconcile")
    if derive_dd_and_a_usd(core) != 3_500_000:
        raise ValueError(
            "DD&A controlled drivers do not derive the approved approximate $3.5M output"
        )


def validate_bridge_source(bridge: dict[str, Any]) -> None:
    expected = {
        "boundaries",
        "canon_effective_through",
        "carrier_market_scan",
        "classification",
        "custody_authority_matrix",
        "decision_date",
        "fit_gaps",
        "integration_gates",
        "names",
        "open_aru_fields",
        "preliminary_capex",
        "prepared_at",
        "rail_access_candidates",
        "record_id",
        "shipment_schedule_exceptions",
        "source_commit_state",
        "title",
        "transport_capacity_events",
        "version",
    }
    require_fields(bridge, expected, "aru_bst_bridge")
    if bridge["classification"] != "PUBLIC_SYNTHETIC_DIEGETIC":
        raise ValueError("bridge classification must remain PUBLIC_SYNTHETIC_DIEGETIC")
    if bridge["source_commit_state"] != "REQUIRES_EXACT_RELEASE_MANIFEST_BINDING":
        raise ValueError("public bridge source must require exact release-manifest binding")
    boundaries = bridge["boundaries"]
    require_fields(
        boundaries,
        {
            "annual_2025_revenue_impact_usd",
            "direct_uranium_custody_authorized",
            "full_aru_case_authorized",
            "interface_envelope_booked",
            "pre_existing_relationship",
            "preliminary_interface_envelope_usd",
            "red_wash_2025_carrier",
        },
        "aru_bst_bridge.boundaries",
    )
    require_fields(
        bridge["names"],
        {"aru", "aru_abbreviation", "bst", "bst_abbreviation"},
        "aru_bst_bridge.names",
    )
    if bridge["names"] != {
        "aru": "American Resource Utility, Inc.",
        "aru_abbreviation": "ARU",
        "bst": "Blood, Sweat & Tears Railway Company",
        "bst_abbreviation": "BS&T",
    }:
        raise ValueError("unexpected ARU/BS&T names")
    if boundaries["pre_existing_relationship"] is not False:
        raise ValueError("bridge must preserve no pre-existing ARU relationship")
    if boundaries["red_wash_2025_carrier"] != "qualified external carriers":
        raise ValueError("qualified external carriers must remain authoritative throughout 2025")
    if boundaries["annual_2025_revenue_impact_usd"] != 0:
        raise ValueError("bridge must not change annual 2025 Red Wash revenue")
    if boundaries["preliminary_interface_envelope_usd"] != 15_000_000:
        raise ValueError("ARU interface screen must remain a $15 million preliminary envelope")
    if boundaries["interface_envelope_booked"] is not False:
        raise ValueError("preliminary interface envelope must not be booked")
    if boundaries["direct_uranium_custody_authorized"] is not False:
        raise ValueError("direct ARU/BS&T uranium custody must remain unauthorized")
    if boundaries["full_aru_case_authorized"] is not True:
        raise ValueError("the industrial successor implements the authorized full ARU case")
    open_fields = bridge["open_aru_fields"]
    if (
        not isinstance(open_fields, list)
        or set(open_fields) != {"whether BS&T ultimately takes direct uranium custody", "future direct mine spur", "Red Wash expansion commissioning dates"}
        or any(not isinstance(field, str) or not field.strip() for field in open_fields)
        or len(set(open_fields)) != len(open_fields)
    ):
        raise ValueError("the bridge must preserve the three specifically gated future decisions")
    for array_name in BRIDGE_ARRAY_FILES:
        if not isinstance(bridge[array_name], list) or not bridge[array_name]:
            raise ValueError(f"bridge array {array_name} must be a non-empty list")


def prepare_owned_directory(path: Path, marker: str, allowed: frozenset[str]) -> None:
    if path.is_symlink():
        raise ValueError(f"owned output root must not be a symlink: {path}")
    controlled_root = ROOT.resolve(strict=True)
    resolved_path = path.resolve(strict=False)
    try:
        relative = resolved_path.relative_to(controlled_root)
    except ValueError as error:
        raise ValueError(
            f"owned output root must resolve beneath {controlled_root}: {path} -> {resolved_path}"
        ) from error
    if not relative.parts:
        raise ValueError(f"owned output root must be below, not equal to, {controlled_root}")
    if path.exists() and not path.is_dir():
        raise ValueError(f"owned output path is not a directory: {path}")
    if not path.exists():
        path.mkdir(parents=True)
        (path / marker).write_text(
            "Owned by red_wash/tools/build_red_wash_package.py\n", encoding="utf-8"
        )
    actual = {entry.name for entry in path.iterdir()}
    unexpected = actual - allowed
    if unexpected:
        raise ValueError(f"unexpected file(s) in owned output {path}: {sorted(unexpected)}")
    if actual and marker not in actual:
        raise ValueError(f"refusing to clean unmarked output directory: {path}")
    marker_path = path / marker
    if marker_path.is_symlink():
        raise ValueError(f"owned output marker must not be a symlink: {marker_path}")
    if not marker_path.exists():
        marker_path.write_text(
            "Owned by red_wash/tools/build_red_wash_package.py\n", encoding="utf-8"
        )
    for entry in path.iterdir():
        if entry.is_symlink():
            raise ValueError(f"unexpected symlink in owned output: {entry}")
        if entry.name == marker:
            continue
        if not entry.is_file():
            raise ValueError(f"unexpected non-file output member: {entry}")
        entry.unlink()


def distribute(total: int, weights: list[float]) -> list[int]:
    raw = [total * item / sum(weights) for item in weights]
    result = [int(item) for item in raw]
    remainder = total - sum(result)
    order = sorted(
        range(len(raw)), key=lambda item: (raw[item] - result[item], -item), reverse=True
    )
    for index in order[:remainder]:
        result[index] += 1
    return result


def provenance(
    fact_state: str = "SYNTHETIC_INSTANCE",
    epistemic_state: str = "SCENARIO",
    source_id: str | None = "SH-PS-RW-TOR-001",
    record_origin: str = "PUBLIC_SYNTHETIC_DIEGETIC",
) -> dict[str, object]:
    return {
        "record_origin": record_origin,
        "fact_state": fact_state,
        "epistemic_state": epistemic_state,
        "source_id": source_id,
    }


def drill_rows(
    rng: random.Random, core: dict[str, Any],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    domains = ["North Roll", "Central Lens", "East 12", "Lower Channel", "South Limb"]
    factors = {
        "North Roll": 1.08,
        "Central Lens": 1.0,
        "East 12": 1.15,
        "Lower Channel": 0.92,
        "South Limb": 0.84,
    }
    collars: list[dict[str, object]] = []
    surveys: list[dict[str, object]] = []
    assays: list[dict[str, object]] = []
    meta = provenance()
    for sequence in range(1, 241):
        year = 2005 + min(20, (sequence - 1) // 12)
        hole = f"RW-{year}-{sequence:03d}"
        depth = rng.randint(550, 2800)
        azimuth = rng.choice([0, 0, 0, rng.randint(1, 359)])
        dip = -90 if azimuth == 0 else rng.choice([-60, -70, -75, -80])
        domain = rng.choice(domains)
        collars.append(
            {
                "hole_id": hole,
                "year_drilled": year,
                "easting_m": round(732748.781991 + rng.uniform(-2100, 2100), 2),
                "northing_m": round(4678053.610642 + rng.uniform(-1500, 1500), 2),
                "elevation_m": round((core["location"]["elevation_ft"] + rng.uniform(-70, 90)) * 0.3048, 2),
                "coordinate_crs": "NAD83 / UTM zone 12N",
                "epsg_code": 26912,
                "utm_zone": "12N",
                "horizontal_datum": "NAD83",
                "total_depth_ft": depth,
                "azimuth_deg": azimuth,
                "dip_deg": dip,
                "geologic_domain": domain,
                **meta,
            }
        )
        for measured_depth in (0, depth / 2, depth):
            surveys.append(
                {
                    "hole_id": hole,
                    "depth_ft": round(measured_depth, 1),
                    "azimuth_deg": round((azimuth + rng.uniform(-2, 2)) % 360, 2),
                    "dip_deg": round(dip + rng.uniform(-1.5, 1.5), 2),
                    "method": "gyro" if year >= 2018 else "single-shot",
                    **meta,
                }
            )
        center = rng.uniform(depth * 0.35, depth * 0.85)
        start = max(0, center - 25)
        for interval in range(10):
            from_ft = start + interval * 5
            distance = abs(from_ft + 2.5 - center)
            base = max(0.005, 0.22 * math.exp(-((distance / 15) ** 2)) * factors[domain])
            sample_type = "PRIMARY"
            if interval == 2 and sequence % 20 == 0:
                sample_type = "DUPLICATE"
            elif interval == 7 and sequence % 37 == 0:
                sample_type = "BLANK"
            elif interval == 5 and sequence % 31 == 0:
                sample_type = "STANDARD"
            grade = 0.0 if sample_type == "BLANK" else max(0, rng.gauss(base, 0.025))
            assays.append(
                {
                    "sample_id": f"{hole}-{interval + 1:02d}",
                    "hole_id": hole,
                    "from_ft": round(from_ft, 1),
                    "to_ft": round(from_ft + 5, 1),
                    "interval_ft": 5,
                    "u3o8_pct": round(grade, 4),
                    "sample_type": sample_type,
                    "method": "pressed-pellet XRF with check ICP-MS",
                    "qa_qc_status": ("WITHIN_2SD" if sample_type == "STANDARD" else "PASS"),
                    **meta,
                }
            )
    return collars, surveys, assays


def production_and_inventory(
    core: dict[str, Any],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    mine = core["mine_2026"]
    calibration_month = int(core["synthetic_calibration_through"][5:7])
    tons = distribute(mine["ore_tons"], [0.90, 0.95, 1, 1, 1.05, 1.05, 1.05, 1, 1, 1, 1, 1])
    sales = [
        50_000,
        25_000,
        75_000,
        50_000,
        25_000,
        50_000,
        25_000,
        50_000,
        50_000,
        25_000,
        25_000,
        50_000,
    ]
    prices = [61, 61, 61, 72, 72, 72, 72, 80, 80, 80, 87, 87]
    grade_factors = [
        0.970,
        0.982,
        0.994,
        1.006,
        1.018,
        1.012,
        1.000,
        1.006,
        1.012,
        1.006,
        0.994,
        0.988,
    ]
    contained = distribute(
        mine["contained_u3o8_lb"],
        [tons[index] * grade_factors[index] for index in range(12)],
    )
    recovery_factors = [
        0.980,
        0.985,
        0.990,
        0.995,
        1.000,
        1.002,
        1.005,
        1.007,
        1.009,
        1.010,
        1.011,
        1.012,
    ]
    produced = distribute(
        mine["produced_u3o8_lb"],
        [contained[index] * recovery_factors[index] for index in range(12)],
    )
    rows: list[dict[str, object]] = []
    for month in range(1, 13):
        month_contained = contained[month - 1]
        month_produced = produced[month - 1]
        grade = month_contained / (tons[month - 1] * 2000) * 100
        recovery = month_produced / month_contained * 100
        period_role = (
            "SYNTHETIC_CALIBRATION" if month <= calibration_month else "MANAGEMENT_FORECAST"
        )
        rows.append(
            {
                "month": f"2026-{month:02d}-01",
                "period_role": period_role,
                "ore_tons": tons[month - 1],
                "head_grade_u3o8_pct": round(grade, 6),
                "recovery_pct": round(recovery, 6),
                "contained_u3o8_lb": month_contained,
                "u3o8_produced_lb": month_produced,
                "u3o8_sold_lb": sales[month - 1],
                "modeled_realized_price_usd_lb": prices[month - 1],
                "revenue_usd": sales[month - 1] * prices[month - 1],
                **provenance(),
            }
        )
    running = mine["opening_finished_inventory_lb"]
    inventory: list[dict[str, object]] = []
    for row in rows:
        ending = running + int(row["u3o8_produced_lb"]) - int(row["u3o8_sold_lb"])
        inventory.append(
            {
                "month": row["month"],
                "opening_finished_u3o8_lb": running,
                "production_u3o8_lb": row["u3o8_produced_lb"],
                "sales_u3o8_lb": row["u3o8_sold_lb"],
                "ending_finished_u3o8_lb": ending,
                **provenance(),
            }
        )
        running = ending
    return rows, inventory


def workforce_rows(core: dict[str, Any]) -> list[dict[str, object]]:
    workforce = core["workforce_2026"]
    site_names = {
        "site_general_management": "Site General Management",
        "underground_operations": "Underground Operations",
        "maintenance_reliability": "Maintenance and Reliability",
        "mill_metallurgy": "Mill and Metallurgy",
        "geology_resource_control": "Geology and Resource Control",
        "safety_radiation": "Safety and Radiation Protection",
        "environmental_permitting": "Environmental and Permitting",
        "supply_warehouse": "Supply and Warehouse",
        "site_finance_people_administration": "Site Finance, People and Administration",
        "security_medical_emergency": "Security, Medical and Emergency Response",
    }
    rows: list[dict[str, object]] = []
    employee = 1
    groups = [("Pale Sun", "Pale Sun Business Layer", workforce["pale_sun_business_layer"])]
    groups.extend(
        ("Red Wash", site_names[key], count) for key, count in workforce["site_functions"].items()
    )
    for organization, function, count in groups:
        for position in range(1, count + 1):
            rows.append(
                {
                    "employee_id": f"RW-{employee:04d}",
                    "organization": organization,
                    "function": function,
                    "title": f"{function} Position {position:02d}",
                    "home_location": (
                        "Sacramento / Red Wash"
                        if organization == "Pale Sun"
                        else "Red Wash, Wyoming"
                    ),
                    "status": "ACTIVE_SYNTHETIC_RECORD",
                    **provenance(),
                }
            )
            employee += 1
    return rows


def ppa_rows(core: dict[str, Any]) -> list[dict[str, object]]:
    transaction = core["transaction"]
    values = [
        ("PPA-01", "Acquired current assets", transaction["current_assets_usd"], "ASSET"),
        (
            "PPA-02",
            "Operating assets pending asset-class allocation",
            transaction["operating_assets_usd"],
            "ASSET",
        ),
        (
            "PPA-03",
            "Asset retirement obligation",
            -transaction["aro_assumed_usd"],
            "LIABILITY",
        ),
        (
            "PPA-04",
            "Other assumed liabilities",
            -transaction["other_liabilities_usd"],
            "LIABILITY",
        ),
        (
            "PPA-05",
            "Net identifiable assets",
            transaction["cash_consideration_usd"],
            "SUBTOTAL",
        ),
        (
            "PPA-06",
            "Cash consideration",
            -transaction["cash_consideration_usd"],
            "CONSIDERATION",
        ),
        ("PPA-07", "Goodwill / bargain purchase", transaction["goodwill_usd"], "RESULT"),
    ]
    return [
        {
            "line_id": identity,
            "line": line,
            "amount_usd": amount,
            "classification": classification,
            "presentation_order": index,
            **provenance("DERIVED", "DERIVED"),
        }
        for index, (identity, line, amount, classification) in enumerate(values, 1)
    ]


def rounded_usd(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def financial_rows(core: dict[str, Any]) -> list[dict[str, object]]:
    mine = core["mine_2026"]
    finance = core["finance_2026"]
    assumptions = core["inventory_cost_assumptions_2026"]
    opening_lb = Decimal(mine["opening_finished_inventory_lb"])
    produced_lb = Decimal(mine["produced_u3o8_lb"])
    sold_lb = Decimal(mine["sold_u3o8_lb"])
    available_lb = opening_lb + produced_lb
    opening_cash = opening_lb * Decimal(
        str(assumptions["opening_finished_inventory_cash_cost_usd_lb"])
    )
    opening_dda = opening_lb * Decimal(
        str(assumptions["opening_finished_inventory_dd_and_a_usd_lb"])
    )
    cash_available = opening_cash + Decimal(finance["cash_production_cost_incurred_usd"])
    dd_and_a_incurred = Decimal(derive_dd_and_a_usd(core))
    dda_available = opening_dda + dd_and_a_incurred
    cash_cost_of_sales = Decimal(rounded_usd(cash_available * sold_lb / available_lb))
    dda_cost_of_sales = Decimal(rounded_usd(dda_available * sold_lb / available_lb))
    ending_cash = cash_available - cash_cost_of_sales
    ending_dda = dda_available - dda_cost_of_sales

    revenue = Decimal(finance["revenue_usd"])
    production_taxes = Decimal(finance["production_mineral_taxes_usd"])
    royalties = Decimal(finance["royalties_usd"])
    freight = Decimal(finance["freight_assay_handling_usd"])
    g_and_a = Decimal(finance["pale_sun_site_g_and_a_usd"])
    accretion = Decimal(finance["aro_accretion_usd"])
    gross_profit = (
        revenue - cash_cost_of_sales - dda_cost_of_sales - production_taxes - royalties - freight
    )
    operating_income = gross_profit - g_and_a
    pretax_income = operating_income - accretion
    tax_rate = Decimal(str(assumptions["income_tax_rate_pct"])) / Decimal(100)
    income_tax = Decimal(rounded_usd(max(pretax_income, Decimal(0)) * tax_rate))
    net_income = pretax_income - income_tax
    cash_inventory_increase = ending_cash - opening_cash
    working_capital_use = Decimal(assumptions["other_working_capital_use_usd"])
    operating_cash_flow = (
        net_income + dda_cost_of_sales + accretion - cash_inventory_increase - working_capital_use
    )
    total_capex = Decimal(finance["sustaining_capex_usd"] + finance["rehabilitation_capex_usd"])
    free_cash_flow = operating_cash_flow - total_capex

    lines: list[tuple[str, str, str, Decimal, bool]] = [
        (
            "Inventory Cost Bridge",
            "ICB-01",
            "Opening finished inventory cash cost",
            opening_cash,
            False,
        ),
        (
            "Inventory Cost Bridge",
            "ICB-02",
            "2026 cash production cost incurred",
            Decimal(finance["cash_production_cost_incurred_usd"]),
            False,
        ),
        (
            "Inventory Cost Bridge",
            "ICB-03",
            "Cash cost available for sale",
            cash_available,
            True,
        ),
        (
            "Inventory Cost Bridge",
            "ICB-04",
            "Cash cost released to sales",
            -cash_cost_of_sales,
            False,
        ),
        (
            "Inventory Cost Bridge",
            "ICB-05",
            "Ending finished inventory cash cost",
            ending_cash,
            True,
        ),
        (
            "Inventory Cost Bridge",
            "ICB-06",
            "Opening finished inventory DD&A",
            opening_dda,
            False,
        ),
        (
            "Inventory Cost Bridge",
            "ICB-07",
            "2026 DD&A incurred",
            dd_and_a_incurred,
            False,
        ),
        (
            "Inventory Cost Bridge",
            "ICB-08",
            "DD&A available for sale",
            dda_available,
            True,
        ),
        (
            "Inventory Cost Bridge",
            "ICB-09",
            "DD&A released to sales",
            -dda_cost_of_sales,
            False,
        ),
        (
            "Inventory Cost Bridge",
            "ICB-10",
            "Ending finished inventory DD&A",
            ending_dda,
            True,
        ),
        ("Income Statement", "IS-01", "Uranium revenue", revenue, False),
        (
            "Income Statement",
            "IS-02",
            "Cash production cost of sales",
            -cash_cost_of_sales,
            False,
        ),
        (
            "Income Statement",
            "IS-03",
            "DD&A in cost of sales",
            -dda_cost_of_sales,
            False,
        ),
        (
            "Income Statement",
            "IS-04",
            "Production and mineral taxes",
            -production_taxes,
            False,
        ),
        ("Income Statement", "IS-05", "Royalties", -royalties, False),
        (
            "Income Statement",
            "IS-06",
            "Freight, assay and handling",
            -freight,
            False,
        ),
        ("Income Statement", "IS-07", "Gross profit", gross_profit, True),
        (
            "Income Statement",
            "IS-08",
            "Pale Sun business and site G&A",
            -g_and_a,
            False,
        ),
        (
            "Income Statement",
            "IS-09",
            "Operating income",
            operating_income,
            True,
        ),
        ("Income Statement", "IS-10", "ARO accretion", -accretion, False),
        (
            "Income Statement",
            "IS-11",
            "Income before tax",
            pretax_income,
            True,
        ),
        ("Income Statement", "IS-12", "Income tax", -income_tax, False),
        ("Income Statement", "IS-13", "Net income", net_income, True),
        ("Cash Flow", "CF-01", "Net income", net_income, False),
        ("Cash Flow", "CF-02", "DD&A addback", dda_cost_of_sales, False),
        ("Cash Flow", "CF-03", "ARO accretion addback", accretion, False),
        (
            "Cash Flow",
            "CF-04",
            "Increase in finished inventory cash cost",
            -cash_inventory_increase,
            False,
        ),
        (
            "Cash Flow",
            "CF-05",
            "Other working-capital use",
            -working_capital_use,
            False,
        ),
        (
            "Cash Flow",
            "CF-06",
            "Operating cash flow",
            operating_cash_flow,
            True,
        ),
        (
            "Cash Flow",
            "CF-07",
            "Sustaining capital",
            -Decimal(finance["sustaining_capex_usd"]),
            False,
        ),
        (
            "Cash Flow",
            "CF-08",
            "Rehabilitation capital",
            -Decimal(finance["rehabilitation_capex_usd"]),
            False,
        ),
        ("Cash Flow", "CF-09", "Free cash flow", free_cash_flow, True),
    ]
    order: dict[str, int] = {}
    result: list[dict[str, object]] = []
    for statement, line_id, line, amount, subtotal in lines:
        order[statement] = order.get(statement, 0) + 1
        result.append(
            {
                "statement": statement,
                "line_id": line_id,
                "line": line,
                "amount_usd": rounded_usd(amount),
                "presentation_order": order[statement],
                "is_subtotal": int(subtotal),
                **provenance("DERIVED", "DERIVED"),
            }
        )
    return result


def vdr_document_sha256(payload: dict[str, object]) -> str:
    """Hash the complete canonical synthetic VDR record payload."""

    expected = {"vdr_id", "category", "document", "effective_date", "review_status"}
    require_fields(payload, expected, "virtual_data_room_index hash payload")
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def deterministic_evidence(
    rng: random.Random,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    monitoring: list[dict[str, object]] = []
    for year in range(2019, 2027):
        # The record is prepared on 2026-09-05. Q3 was not complete at the
        # synthetic calibration cutoff, so period evidence stops at 2026-Q2.
        last_quarter = 2 if year == 2026 else 4
        for quarter in range(1, last_quarter + 1):
            for station in (
                "MW-04",
                "MW-09",
                "MW-12",
                "MW-17",
                "MW-21",
                "TAIL-UD-1",
            ):
                trend = (
                    (year - 2019) * 0.7 + quarter * 0.12
                    if station == "MW-17"
                    else rng.uniform(-0.3, 0.3)
                )
                monitoring.append(
                    {
                        "period": f"{year}-Q{quarter}",
                        "station": station,
                        "uranium_mg_l": round(
                            max(
                                0.002,
                                0.012 + trend * 0.002 + rng.uniform(-0.002, 0.002),
                            ),
                            4,
                        ),
                        "sulfate_mg_l": round(180 + trend * 18 + rng.uniform(-12, 12), 1),
                        "ph": round(7.2 + rng.uniform(-0.25, 0.25), 2),
                        **provenance(),
                    }
                )

    major = [
        ("UG-VENT", "Main ventilation fan and VFD", 1_450_000, "CRITICAL", 580_000),
        ("UG-GC", "Ground-support rehabilitation", 1_250_000, "CRITICAL", 500_000),
        ("MILL-MCC", "Mill motor-control centers", 1_100_000, "HIGH", 660_000),
        (
            "TAIL-UD",
            "Tailings underdrain pumps and instrumentation",
            900_000,
            "CRITICAL",
            360_000,
        ),
        ("MILL-LEACH", "Leach tanks and agitators", 720_000, "HIGH", 432_000),
        ("UG-DEW", "Dewatering pumps and controls", 680_000, "HIGH", 408_000),
        ("FLEET-LHD", "LHD overhaul program", 640_000, "HIGH", 384_000),
        (
            "POWER-SUB",
            "Substation relay modernization",
            825_000,
            "CRITICAL",
            330_000,
        ),
    ]
    backlog: list[dict[str, object]] = []
    for index, (system, description, cost, priority, seller) in enumerate(major, 1):
        backlog.append(
            {
                "backlog_id": f"MB-{index:03d}",
                "system_id": system,
                "description": description,
                "estimated_cost_usd": cost,
                "priority": priority,
                "seller_schedule_usd": seller,
                "status": "FUNDED_IN_SYNTHETIC_STABILIZATION_PLAN",
                **provenance(),
            }
        )
    for index in range(len(major) + 1, 61):
        cost = rng.randint(35_000, 120_000)
        backlog.append(
            {
                "backlog_id": f"MB-{index:03d}",
                "system_id": rng.choice(
                    ["ENV-WELL", "SURF-BLDG", "OT-NET", "MILL-PUMP", "UG-ELEC"]
                ),
                "description": f"Synthetic deferred corrective work package {index}",
                "estimated_cost_usd": cost,
                "priority": rng.choice(["LOW", "MEDIUM", "HIGH"]),
                "seller_schedule_usd": round(cost * rng.uniform(0.35, 0.8)),
                "status": rng.choice(["SCHEDULED", "MONITORED", "FUNDED"]),
                **provenance(),
            }
        )

    categories = [
        "Corporate",
        "Title",
        "Geology",
        "Resource",
        "Mine Plan",
        "Metallurgy",
        "Permits",
        "Environment",
        "Safety",
        "Commercial",
        "Finance",
        "Tax",
        "People",
        "Insurance",
        "Technology",
        "Transaction",
    ]
    vdr: list[dict[str, object]] = []
    for index in range(1, 177):
        category = categories[(index - 1) % len(categories)]
        identity = f"VDR-{index:04d}"
        document_payload: dict[str, object] = {
            "vdr_id": identity,
            "category": category,
            "document": f"{category} synthetic record {index:03d}",
            "effective_date": (
                f"{2005 + index % 21:04d}-{1 + index % 12:02d}-{1 + index % 27:02d}"
            ),
            "review_status": ("EXCEPTION_NOTED" if index % 7 == 0 else "REVIEWED"),
        }
        vdr.append(
            {
                **document_payload,
                "document_sha256": vdr_document_sha256(document_payload),
                **provenance(),
            }
        )
    return monitoring, backlog, vdr


def source_backed_rows(
    core: dict[str, Any], external: list[dict[str, str]]
) -> dict[str, list[dict[str, object]]]:
    ownership = [
        {
            "owner_id": f"OWN-{index:02d}",
            "owner_display_name": row["owner_display_name"],
            "owner_display_name_state": row["owner_display_name_state"],
            "owner_legal_name": row["owner_legal_name"],
            "owner_legal_name_state": row["owner_legal_name_state"],
            "start_date": row["start"],
            "end_date": row["end"],
            "role": row["role"],
            **provenance(row["fact_state"], row["epistemic_state"]),
        }
        for index, row in enumerate(core["ownership_history"], 1)
    ]
    resource = core["resource_basis"]
    resources = [
        {
            "basis_id": "RW-RESOURCE-INDICATED",
            "classification": "INDICATED_OPERATING_BASIS",
            "tons": resource["indicated_tons"],
            "grade_u3o8_pct": resource["grade_u3o8_pct"],
            "contained_lb": resource["contained_lb"],
            "modeled_recovery_pct": resource["modeled_recovery_pct"],
            "recoverable_lb": resource["recoverable_lb"],
            "included_in_base_value": 1,
            **provenance("SCENARIO_INPUT", "SUPPORTED_ESTIMATE"),
        },
        {
            "basis_id": "RW-RESOURCE-INFERRED",
            "classification": "INFERRED_EXPLORATION_INVENTORY",
            "tons": resource["inferred_tons"],
            "grade_u3o8_pct": resource["inferred_grade_u3o8_pct"],
            "contained_lb": round(
                resource["inferred_tons"] * 2000 * resource["inferred_grade_u3o8_pct"] / 100
            ),
            "modeled_recovery_pct": None,
            "recoverable_lb": None,
            "included_in_base_value": int(resource["base_value_includes_inferred"]),
            **provenance("SCENARIO_INPUT", "SUPPORTED_ESTIMATE"),
        },
    ]
    permits = [
        {
            "permit_id": row["permit_id"],
            "permit": row["permit"],
            "number": row["number"],
            "authority": row["authority"],
            "legal_basis": row["legal_basis"],
            "status": row["status"],
            **provenance(),
        }
        for row in core["permit_register"]
    ]
    diligence = [
        {
            "finding_id": row["id"],
            "domain": row["domain"],
            "severity": row["severity"],
            "finding": row["finding"],
            "disposition": row["disposition"],
            "status": "SYNTHETIC_EXECUTIVE_TRACKING",
            **provenance(),
        }
        for row in core["diligence_findings"]
    ]
    quality = []
    for index, row in enumerate(core["quality_of_earnings"]):
        role = (
            "STARTING_POINT"
            if index == 0
            else "RESULT"
            if index == len(core["quality_of_earnings"]) - 1
            else "ADJUSTMENT"
        )
        quality.append(
            {
                "line": row["line"],
                "amount_usd": row["amount_usd"],
                "line_role": role,
                **(
                    provenance("DERIVED", "DERIVED")
                    if role == "RESULT"
                    else provenance(
                        "SCENARIO_INPUT",
                        "PROVISIONAL_ASSUMPTION"
                        if role == "STARTING_POINT"
                        else "SUPPORTED_ESTIMATE",
                    )
                ),
            }
        )
    contracts = [
        {
            "contract_id": row["contract_id"],
            "buyer": row["buyer"],
            "origin": row["origin"],
            "committed_lb": row["pounds"],
            "pricing_type": row["structure"],
            "modeled_price_usd_lb": row["price_usd_lb"],
            "delivery_point": row["delivery_point"],
            "assignability": row["assignability"],
            **provenance("SCENARIO_INPUT", "SCENARIO"),
        }
        for row in core["contract_book_2026"]
    ]
    timeline = []
    expected_timeline = {
        "category",
        "date_precision",
        "epistemic_state",
        "event",
        "event_id",
        "fact_state",
        "period",
        "record_origin",
        "source_id",
    }
    for index, row in enumerate(core["transaction_timeline"], 1):
        require_fields(row, expected_timeline, f"transaction_timeline[{index}]")
        timeline.append(dict(row))
    sources = [
        {
            "source_id": row["source_id"],
            "organization": row["organization"],
            "title": row["title"],
            "url": row["url"],
            "use": row["use"],
            "publication_date": row["publication_date"] or None,
            "accessed_date": row["accessed_date"],
            "covered_period": row["covered_period"],
            "geography": row["geography"],
            "unit": row["unit"],
            "method": row["method"],
            "transformation": row["transformation"],
            "limitations": row["limitations"],
            "record_origin": row["state"],
            "fact_state": "EXTERNAL_RESEARCH",
            "epistemic_state": "SUPPORTED_ESTIMATE",
        }
        for row in external
    ]
    return {
        "ownership_history.csv": ownership,
        "resource_basis.csv": resources,
        "permit_register.csv": permits,
        "diligence_findings.csv": diligence,
        "quality_of_earnings.csv": quality,
        "transaction_timeline.csv": timeline,
        "uranium_contracts.csv": contracts,
        "external_source_register.csv": sources,
    }


def bridge_rows(bridge: dict[str, Any]) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {}
    for array_name, filename in BRIDGE_ARRAY_FILES.items():
        spec = DATASET_BY_FILENAME[filename]
        normalized: list[dict[str, object]] = []
        for index, source_row in enumerate(bridge[array_name], 1):
            if not isinstance(source_row, dict):
                raise ValueError(f"bridge {array_name}[{index}] is not an object")
            require_fields(source_row, set(spec.fieldnames), f"bridge {array_name}[{index}]")
            row = dict(source_row)
            if "date_precision" in row:
                row["date_precision"] = str(row["date_precision"]).upper()
            for field in (
                "incumbent_2025",
                "qualified_2025",
                "direct_mine_connection",
                "suitable_transload",
                "uranium_capability",
                "blocks_custody",
                "blocks_service",
                "included_in_envelope",
            ):
                if field in row:
                    if row[field] not in (True, False, 0, 1):
                        raise ValueError(f"bridge {array_name}[{index}] {field} must be boolean")
                    row[field] = int(bool(row[field]))
            normalized.append(row)
        result[filename] = normalized
    return result


def all_generated_rows(
    core: dict[str, Any], bridge: dict[str, Any], external: list[dict[str, str]]
) -> dict[str, list[dict[str, object]]]:
    rng = random.Random(SEED)
    collars, surveys, assays = drill_rows(rng, core)
    production, inventory = production_and_inventory(core)
    monitoring, backlog, vdr = deterministic_evidence(rng)
    rows = source_backed_rows(core, external)
    rows.update(
        {
            "drill_collars.csv": collars,
            "downhole_surveys.csv": surveys,
            "assays.csv": assays,
            "monthly_production_2026.csv": production,
            "inventory_rollforward_2026.csv": inventory,
            "employee_census_2026.csv": workforce_rows(core),
            "purchase_price_allocation.csv": ppa_rows(core),
            "financial_statements_2026.csv": financial_rows(core),
            "environmental_monitoring.csv": monitoring,
            "maintenance_backlog.csv": backlog,
            "virtual_data_room_index.csv": vdr,
        }
    )
    rows.update(bridge_rows(bridge))
    if set(rows) != GENERATED_FILENAMES:
        raise AssertionError(
            "internal generated-file contract drift; "
            f"missing={sorted(GENERATED_FILENAMES - set(rows))}, "
            f"unexpected={sorted(set(rows) - GENERATED_FILENAMES)}"
        )
    return rows


def validate_output_row(spec: Dataset, row: dict[str, object], index: int) -> None:
    require_fields(row, set(spec.fieldnames), f"{spec.filename} row {index}")
    for column in spec.columns:
        value = row[column.name]
        if value is None:
            if not column.nullable:
                raise ValueError(f"{spec.filename} row {index} has null {column.name}")
            continue
        if isinstance(value, str) and value.strip().upper() == "ACTUAL":
            raise ValueError(
                f"deprecated ACTUAL label in {spec.filename} row {index} {column.name}"
            )
    if "record_origin" in row and row["record_origin"] not in RECORD_ORIGINS:
        raise ValueError(
            f"invalid record_origin in {spec.filename} row {index}: {row['record_origin']!r}"
        )
    if "fact_state" in row and row["fact_state"] not in FACT_STATES:
        raise ValueError(
            f"invalid fact_state in {spec.filename} row {index}: {row['fact_state']!r}"
        )
    if "epistemic_state" in row and row["epistemic_state"] not in EPISTEMIC_STATES:
        raise ValueError(
            f"invalid epistemic_state in {spec.filename} row {index}: {row['epistemic_state']!r}"
        )


def write_generated(rows_by_file: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    manifest: list[dict[str, object]] = []
    for filename in sorted(rows_by_file):
        rows = rows_by_file[filename]
        if not rows:
            raise ValueError(f"generated dataset must not be empty: {filename}")
        spec = DATASET_BY_FILENAME[filename]
        for index, row in enumerate(rows, 1):
            validate_output_row(spec, row, index)
        path = GENERATED / filename
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=spec.fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        manifest.append(
            {
                "path": f"red_wash/generated/{filename}",
                "table": spec.table,
                "rows": len(rows),
                "columns": list(spec.fieldnames),
                "bytes": path.stat().st_size,
                "sha256": sha256_path(path),
            }
        )
    return manifest


def quote_identifier(value: str) -> str:
    if not value.replace("_", "").isalnum():
        raise ValueError(f"unsafe SQLite identifier: {value!r}")
    return f'"{value}"'


def create_table(connection: sqlite3.Connection, spec: Dataset) -> None:
    clauses: list[str] = []
    for column in spec.columns:
        nullable = "" if column.nullable else " NOT NULL"
        clauses.append(f"{quote_identifier(column.name)} {column.sqlite_type}{nullable}")
    clauses.append(
        f"PRIMARY KEY ({', '.join(quote_identifier(name) for name in spec.primary_key)})"
    )
    for local, foreign_table, foreign in spec.foreign_keys:
        clauses.append(
            f"FOREIGN KEY ({', '.join(quote_identifier(name) for name in local)}) "
            f"REFERENCES {quote_identifier(foreign_table)} "
            f"({', '.join(quote_identifier(name) for name in foreign)})"
        )
    clauses.extend(f"CHECK ({expression})" for expression in spec.checks)
    fieldnames = set(spec.fieldnames)
    enum_checks = {
        "record_origin": RECORD_ORIGINS,
        "fact_state": FACT_STATES,
        "epistemic_state": EPISTEMIC_STATES,
    }
    for field, values in enum_checks.items():
        if field in fieldnames:
            allowed = ",".join(f"'{value}'" for value in sorted(values))
            clauses.append(f"CHECK ({quote_identifier(field)} IN ({allowed}))")
    if "period_role" in fieldnames:
        clauses.append("CHECK (period_role IN ('SYNTHETIC_CALIBRATION','MANAGEMENT_FORECAST'))")
    connection.execute(f"CREATE TABLE {quote_identifier(spec.table)} ({', '.join(clauses)}) STRICT")


def sqlite_value(raw: str, sqlite_type: str, nullable: bool) -> object:
    if raw == "":
        if nullable:
            return None
        raise ValueError("non-nullable generated field is blank")
    if sqlite_type == "INTEGER":
        decimal = Decimal(raw)
        if decimal != decimal.to_integral_value():
            raise ValueError(f"expected integer, got {raw!r}")
        return int(decimal)
    if sqlite_type == "REAL":
        return float(Decimal(raw))
    return raw


def repository_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNAVAILABLE"


def build_database(
    core: dict[str, Any],
    bridge: dict[str, Any],
    source_manifest: list[dict[str, object]],
    generated_manifest: list[dict[str, object]],
    visual_manifest: list[dict[str, object]],
) -> tuple[Path, str]:
    database = DIST / DATABASE_FILENAME
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA page_size = 4096")
    connection.execute("PRAGMA encoding = 'UTF-8'")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA application_id = 0x5257544f")
    connection.execute("PRAGMA user_version = 10000")
    for spec in DATASETS:
        create_table(connection, spec)
        with (GENERATED / spec.filename).open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != spec.fieldnames:
                raise ValueError(f"generated schema drift before SQLite load: {spec.filename}")
            values = [
                tuple(
                    sqlite_value(row[column.name], column.sqlite_type, column.nullable)
                    for column in spec.columns
                )
                for row in reader
            ]
        placeholders = ",".join("?" for _ in spec.columns)
        connection.executemany(
            f"INSERT INTO {quote_identifier(spec.table)} VALUES ({placeholders})",
            values,
        )

    connection.executescript(
        """
        CREATE TABLE package_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        ) STRICT;
        CREATE TABLE source_provenance (
            source_path TEXT PRIMARY KEY,
            byte_count INTEGER NOT NULL CHECK (byte_count > 0),
            sha256 TEXT NOT NULL CHECK (length(sha256) = 64)
        ) STRICT;
        CREATE TABLE generated_file_manifest (
            generated_path TEXT PRIMARY KEY,
            table_name TEXT NOT NULL UNIQUE,
            row_count INTEGER NOT NULL CHECK (row_count > 0),
            byte_count INTEGER NOT NULL CHECK (byte_count > 0),
            sha256 TEXT NOT NULL CHECK (length(sha256) = 64)
        ) STRICT;
        CREATE TABLE visual_asset_manifest (
            canonical_path TEXT PRIMARY KEY,
            byte_count INTEGER NOT NULL CHECK (byte_count > 0),
            sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
            verification_state TEXT NOT NULL
              CHECK (verification_state = 'VERIFIED_EXACT_BYTES')
        ) STRICT;

        CREATE VIEW v_2026_production_reconciliation AS
        SELECT COUNT(*) AS month_count,
               SUM(ore_tons) AS ore_tons,
               SUM(contained_u3o8_lb) AS contained_lb,
               SUM(u3o8_produced_lb) AS produced_lb,
               SUM(u3o8_sold_lb) AS sold_lb,
               SUM(revenue_usd) AS revenue_usd
        FROM monthly_production_2026;

        CREATE VIEW v_2026_inventory_reconciliation AS
        SELECT
          (SELECT opening_finished_u3o8_lb FROM inventory_rollforward_2026
           ORDER BY month LIMIT 1) AS opening_lb,
          SUM(production_u3o8_lb) AS production_lb,
          SUM(sales_u3o8_lb) AS sales_lb,
          (SELECT ending_finished_u3o8_lb FROM inventory_rollforward_2026
           ORDER BY month DESC LIMIT 1) AS ending_lb
        FROM inventory_rollforward_2026;

        CREATE VIEW v_purchase_price_allocation_reconciliation AS
        SELECT
          SUM(CASE WHEN classification IN ('ASSET','LIABILITY')
              THEN amount_usd ELSE 0 END) AS net_identifiable_assets,
          SUM(CASE WHEN classification = 'CONSIDERATION'
              THEN amount_usd ELSE 0 END) AS consideration,
          SUM(CASE WHEN classification = 'RESULT'
              THEN amount_usd ELSE 0 END) AS goodwill_or_bargain_purchase
        FROM purchase_price_allocation;

        CREATE VIEW v_aru_red_wash_bridge_controls AS
        SELECT
          (SELECT COUNT(*) FROM transport_capacity_events) AS capacity_event_count,
          (SELECT COALESCE(SUM(annual_revenue_impact_usd),0)
           FROM transport_capacity_events) AS event_revenue_impact_usd,
          (SELECT COALESCE(SUM(annual_revenue_impact_usd),0)
           FROM shipment_schedule_exceptions) AS exception_revenue_impact_usd,
          (SELECT COALESCE(SUM(amount_usd),0)
           FROM aru_red_wash_preliminary_capex
           WHERE component_id = 'RW-ARU-CAPEX-000') AS preliminary_envelope_usd,
          (SELECT COUNT(*) FROM custody_authority_matrix
           WHERE status = 'OPEN') AS open_custody_gate_count;

        CREATE VIEW v_2026_production AS
        SELECT ore_tons, produced_lb, sold_lb, revenue_usd
        FROM v_2026_production_reconciliation;

        CREATE VIEW v_2026_inventory AS
        SELECT opening_lb, production_lb, sales_lb, ending_lb
        FROM v_2026_inventory_reconciliation;
        """
    )

    source_manifest_digest = hashlib.sha256(canonical_json(source_manifest)).hexdigest()
    open_fields = json.dumps(sorted(bridge["open_aru_fields"]), separators=(",", ":"))
    metadata = {
        "record_id": core["record_id"],
        "version": core["version"],
        "scenario_id": SCENARIO_ID,
        "scenario_version": core["version"],
        "input_version": INPUT_VERSION,
        "effective_period_json": json.dumps(
            EFFECTIVE_PERIOD, sort_keys=True, separators=(",", ":")
        ),
        "built_at": f"{core['prepared_at']}T00:00:00Z",
        "built_at_semantics": BUILT_AT_SEMANTICS,
        "classification": core["classification"],
        "synthetic_calibration_through": core["synthetic_calibration_through"],
        "canon_effective_through": core["canon_effective_through"],
        "prepared_at": core["prepared_at"],
        "epistemic_mode": core["epistemic_mode"],
        "generator_version": GENERATOR_VERSION,
        "seed": str(SEED),
        "source_commit": repository_commit(),
        "source_manifest_sha256": source_manifest_digest,
        "bridge_record_id": bridge["record_id"],
        "bridge_version": bridge["version"],
        "bridge_source_commit_state": bridge["source_commit_state"],
        "no_preexisting_relationship": "true",
        "external_carriers_all_2025": "true",
        "annual_2025_revenue_impact_usd": "0",
        "preliminary_capex_envelope_usd": "15000000",
        "custody_state": "OPEN",
        "full_aru_case_state": "SELECTED_SUCCESSOR",
        "open_aru_fields_json": open_fields,
    }
    connection.executemany(
        "INSERT INTO package_metadata(key,value) VALUES (?,?)", sorted(metadata.items())
    )
    connection.executemany(
        "INSERT INTO source_provenance(source_path,byte_count,sha256) VALUES (?,?,?)",
        [(row["path"], row["bytes"], row["sha256"]) for row in source_manifest],
    )
    connection.executemany(
        """INSERT INTO generated_file_manifest(
             generated_path,table_name,row_count,byte_count,sha256
           ) VALUES (?,?,?,?,?)""",
        [
            (row["path"], row["table"], row["rows"], row["bytes"], row["sha256"])
            for row in generated_manifest
        ],
    )
    connection.executemany(
        """INSERT INTO visual_asset_manifest(
             canonical_path,byte_count,sha256,verification_state
           ) VALUES (?,?,?,'VERIFIED_EXACT_BYTES')""",
        [(row["path"], row["bytes"], row["sha256"]) for row in visual_manifest],
    )
    foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_errors:
        raise ValueError(f"SQLite foreign-key violations: {foreign_key_errors}")
    connection.commit()
    connection.execute("VACUUM")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise ValueError(f"SQLite integrity_check failed: {integrity}")
    schema_rows = connection.execute(
        """SELECT type,name,sql FROM sqlite_schema
           WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"""
    ).fetchall()
    schema_sha256 = hashlib.sha256(canonical_json(schema_rows)).hexdigest()
    connection.close()
    return database, schema_sha256


def verified_visuals() -> list[dict[str, object]]:
    control_path = REPOSITORY_ROOT / "assets/brand/red_wash_visual_manifest.json"
    if not control_path.is_file():
        raise ValueError("required Red Wash visual-control manifest is missing")
    control = json.loads(control_path.read_text(encoding="utf-8"))
    if control.get("binary_ingestion_state") != "COMPLETE":
        raise ValueError("Red Wash visual-control manifest is not COMPLETE")
    controlled_assets = {
        row["canonical_path"]: (row["sha256"], row["bytes"]) for row in control.get("assets", [])
    }
    rows: list[dict[str, object]] = []
    for relative, expected in sorted(VISUAL_HASHES.items()):
        path = REPOSITORY_ROOT / relative
        if not path.is_file():
            raise ValueError(f"required owner-approved visual is missing: {relative}")
        actual = sha256_path(path)
        if actual != expected:
            raise ValueError(
                f"owner-approved visual hash mismatch: {relative}; "
                f"expected={expected}, actual={actual}"
            )
        if controlled_assets.get(relative) != (expected, path.stat().st_size):
            raise ValueError(
                f"visual-control manifest does not match exact asset bytes: {relative}"
            )
        rows.append({"path": relative, "bytes": path.stat().st_size, "sha256": actual})
    if set(controlled_assets) != set(VISUAL_HASHES):
        raise ValueError("visual-control manifest asset allowlist is not exact")
    return rows


def write_manifest(
    core: dict[str, Any],
    bridge: dict[str, Any],
    source_manifest: list[dict[str, object]],
    generated_manifest: list[dict[str, object]],
    visual_manifest: list[dict[str, object]],
    database: Path,
    schema_sha256: str,
) -> dict[str, object]:
    statement_rows = financial_rows(core)
    statement = {(row["statement"], row["line"]): row["amount_usd"] for row in statement_rows}
    repository = "SquirmyWormy275/SABLEHARBOR"
    visual_control_path = REPOSITORY_ROOT / "assets/brand/red_wash_visual_manifest.json"
    source_snapshot_ids = [
        {
            "repository": repository,
            "path": row["path"],
            "revision": f"sha256:{row['sha256']}",
        }
        for row in source_manifest
    ]
    source_snapshot_ids.extend(
        {
            "repository": repository,
            "path": row["path"],
            "revision": f"sha256:{row['sha256']}",
        }
        for row in visual_manifest
    )
    source_snapshot_ids.append(
        {
            "repository": repository,
            "path": "assets/brand/red_wash_visual_manifest.json",
            "revision": f"sha256:{sha256_path(visual_control_path)}",
        }
    )
    source_snapshot_ids.sort(key=lambda row: str(row["path"]))
    output_hashes = {
        str(row["path"]): str(row["sha256"])
        for row in sorted(generated_manifest, key=lambda item: str(item["path"]))
    }
    output_hashes[f"red_wash/dist/{DATABASE_FILENAME}"] = sha256_path(database)
    manifest: dict[str, object] = {
        "scenario_id": SCENARIO_ID,
        "scenario_version": core["version"],
        "generator_version": GENERATOR_VERSION,
        "input_version": INPUT_VERSION,
        "seed": SEED,
        "effective_period": EFFECTIVE_PERIOD,
        "source_snapshot_ids": source_snapshot_ids,
        "built_at": f"{core['prepared_at']}T00:00:00Z",
        "built_at_semantics": BUILT_AT_SEMANTICS,
        "output_hashes": output_hashes,
        "output_hash_scope": "ALL_NON_SELF_GENERATED_OUTPUTS",
        "package": {
            "record_id": core["record_id"],
            "version": core["version"],
            "classification": core["classification"],
            "synthetic_calibration_through": core["synthetic_calibration_through"],
            "canon_effective_through": core["canon_effective_through"],
            "prepared_at": core["prepared_at"],
            "epistemic_mode": core["epistemic_mode"],
            "source_commit": repository_commit(),
        },
        "generator": {
            "entry_point": "red_wash/tools/build_red_wash_package.py",
            "version": GENERATOR_VERSION,
            "seed": SEED,
            "contract_sha256": sha256_path(ROOT / "tools" / "red_wash_contract.py"),
            "builder_sha256": sha256_path(ROOT / "tools" / "build_red_wash_package.py"),
        },
        "source_inputs": source_manifest,
        "generated_files": generated_manifest,
        "ownership_markers": [
            {
                "path": f"red_wash/generated/{GENERATED_MARKER}",
                "bytes": (GENERATED / GENERATED_MARKER).stat().st_size,
                "sha256": sha256_path(GENERATED / GENERATED_MARKER),
            },
            {
                "path": f"red_wash/dist/{DIST_MARKER}",
                "bytes": (DIST / DIST_MARKER).stat().st_size,
                "sha256": sha256_path(DIST / DIST_MARKER),
            },
        ],
        "database": {
            "path": f"red_wash/dist/{DATABASE_FILENAME}",
            "bytes": database.stat().st_size,
            "sha256": sha256_path(database),
            "schema_sha256": schema_sha256,
            "integrity_check": "ok",
            "foreign_key_check": [],
        },
        "visual_assets": visual_manifest,
        "visual_control_manifest": {
            "path": "assets/brand/red_wash_visual_manifest.json",
            "bytes": visual_control_path.stat().st_size,
            "sha256": sha256_path(visual_control_path),
        },
        "controlled_totals": {
            "ore_tons": core["mine_2026"]["ore_tons"],
            "produced_u3o8_lb": core["mine_2026"]["produced_u3o8_lb"],
            "sold_u3o8_lb": core["mine_2026"]["sold_u3o8_lb"],
            "ending_finished_inventory_lb": core["mine_2026"]["ending_finished_inventory_lb"],
            "fte": core["workforce_2026"]["total_fte"],
            "revenue_usd": core["finance_2026"]["revenue_usd"],
            "derived_dd_and_a_incurred_usd": derive_dd_and_a_usd(core),
            "derived_net_income_usd": statement[("Income Statement", "Net income")],
            "derived_operating_cash_flow_usd": statement[("Cash Flow", "Operating cash flow")],
            "derived_free_cash_flow_usd": statement[("Cash Flow", "Free cash flow")],
        },
        "aru_bst_bridge_controls": {
            "record_id": bridge["record_id"],
            "source_commit_state": bridge["source_commit_state"],
            "no_preexisting_relationship": not bridge["boundaries"]["pre_existing_relationship"],
            "external_carriers_all_2025": bridge["boundaries"]["red_wash_2025_carrier"]
            == "qualified external carriers",
            "annual_2025_revenue_impact_usd": bridge["boundaries"][
                "annual_2025_revenue_impact_usd"
            ],
            "preliminary_capex_envelope_usd": bridge["boundaries"][
                "preliminary_interface_envelope_usd"
            ],
            "custody_state": "OPEN",
            "full_aru_case_state": "SELECTED_SUCCESSOR",
            "open_aru_fields": sorted(bridge["open_aru_fields"]),
        },
    }
    path = DIST / MANIFEST_FILENAME
    path.write_bytes(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    )
    return manifest


def build() -> dict[str, object]:
    core, bridge, external, source_manifest = load_inputs()
    source_hashes_before = {row["path"]: row["sha256"] for row in source_manifest}
    visuals = verified_visuals()
    rows_by_file = all_generated_rows(core, bridge, external)
    prepare_owned_directory(GENERATED, GENERATED_MARKER, GENERATED_ALLOWED)
    prepare_owned_directory(DIST, DIST_MARKER, DIST_ALLOWED)
    generated_manifest = write_generated(rows_by_file)
    database, schema_sha256 = build_database(
        core, bridge, source_manifest, generated_manifest, visuals
    )
    manifest = write_manifest(
        core,
        bridge,
        source_manifest,
        generated_manifest,
        visuals,
        database,
        schema_sha256,
    )
    source_hashes_after = {
        f"red_wash/source/{name}": sha256_path(SOURCE / name) for name in sorted(SOURCE_FILENAMES)
    }
    if source_hashes_before != source_hashes_after:
        raise ValueError("immutable source changed during generation")
    return manifest


def main() -> int:
    manifest = build()
    summary = {
        "status": "PASS",
        "record_id": manifest["package"]["record_id"],
        "version": manifest["package"]["version"],
        "generated_files": len(manifest["generated_files"]),
        "database_sha256": manifest["database"]["sha256"],
        "derived_net_income_usd": manifest["controlled_totals"]["derived_net_income_usd"],
        "derived_operating_cash_flow_usd": manifest["controlled_totals"][
            "derived_operating_cash_flow_usd"
        ],
        "derived_free_cash_flow_usd": manifest["controlled_totals"]["derived_free_cash_flow_usd"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
