"""Independently validate the deterministic Red Wash public package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from red_wash_contract import (
    DATABASE_FILENAME,
    DATASETS,
    DIST,
    DIST_ALLOWED,
    DIST_MARKER,
    EPISTEMIC_STATES,
    FACT_STATES,
    GENERATED,
    GENERATED_ALLOWED,
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
from red_wash_projection_contract import (
    BRIDGE_PROJECTION_PATH,
    DECISION_ADDENDUM_PATH,
    TRANSACTION_CANON_PATH,
    TRANSACTION_PROJECTION_PATH,
    projection_checks,
)


class ValidationFailure(RuntimeError):
    def __init__(self, result: dict[str, object]):
        super().__init__(json.dumps(result, indent=2, sort_keys=True))
        self.result = result


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_payload_sha256(payload: dict[str, str]) -> str:
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def csv_rows(spec: Dataset) -> list[dict[str, str]]:
    path = GENERATED / spec.filename
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != spec.fieldnames:
            raise ValueError(
                f"{spec.filename} schema mismatch; expected={spec.fieldnames}, "
                f"actual={tuple(reader.fieldnames or ())}"
            )
        result = list(reader)
    if not result:
        raise ValueError(f"generated dataset is empty: {spec.filename}")
    if any(None in row for row in result):
        raise ValueError(f"generated dataset has malformed rows: {spec.filename}")
    return result


def decimal_total(records: list[dict[str, str]], field: str) -> Decimal:
    return sum((Decimal(record[field]) for record in records), Decimal(0))


def rounded_usd(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def derived_dd_and_a_usd(core: dict[str, Any]) -> Decimal:
    transaction = core["transaction"]
    resource = core["resource_basis"]
    mine = core["mine_2026"]
    if (
        not isinstance(transaction, dict)
        or not isinstance(resource, dict)
        or not isinstance(mine, dict)
    ):
        raise ValueError("DD&A driver records must be objects")
    asset_basis = Decimal(transaction["operating_assets_usd"]) + Decimal(
        transaction["capitalized_rehabilitation_usd"]
    )
    return rounded_usd(
        asset_basis * Decimal(mine["produced_u3o8_lb"]) / Decimal(resource["recoverable_lb"])
    )


def validate(generate: bool = False) -> dict[str, object]:
    if generate:
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / "build_red_wash_package.py")],
            cwd=REPOSITORY_ROOT,
            check=True,
        )

    checks: list[str] = []
    failures: list[str] = []

    def check(condition: bool, label: str) -> None:
        (checks if condition else failures).append(label)

    check(SOURCE.is_dir(), "immutable source directory exists")
    check(
        SOURCE.is_dir() and {entry.name for entry in SOURCE.iterdir()} == SOURCE_FILENAMES,
        "source filename allowlist is exact",
    )
    check(GENERATED.is_dir(), "owned generated directory exists")
    check(DIST.is_dir(), "owned distribution directory exists")
    if GENERATED.is_dir():
        check(
            {entry.name for entry in GENERATED.iterdir()} == GENERATED_ALLOWED,
            "generated filename allowlist is exact",
        )
    if DIST.is_dir():
        check(
            {entry.name for entry in DIST.iterdir()} == DIST_ALLOWED,
            "distribution filename allowlist is exact",
        )

    core = json.loads((SOURCE / "core_operating_data.json").read_text(encoding="utf-8"))
    bridge = json.loads((SOURCE / "aru_bst_bridge.json").read_text(encoding="utf-8"))
    transaction_projection = json.loads(TRANSACTION_PROJECTION_PATH.read_text(encoding="utf-8"))
    bridge_projection = json.loads(BRIDGE_PROJECTION_PATH.read_text(encoding="utf-8"))
    transaction_canon = TRANSACTION_CANON_PATH.read_text(encoding="utf-8")
    decision_addendum = DECISION_ADDENDUM_PATH.read_text(encoding="utf-8")
    all_rows = {spec.filename: csv_rows(spec) for spec in DATASETS}

    for spec in DATASETS:
        records = all_rows[spec.filename]
        required = {column.name for column in spec.columns if not column.nullable}
        check(
            all(all(row[field] != "" for field in required) for row in records),
            f"{spec.filename} has no nulls in required columns",
        )
        check(
            all(value.strip().upper() != "ACTUAL" for row in records for value in row.values()),
            f"{spec.filename} has no deprecated ACTUAL label",
        )
        if "record_origin" in spec.fieldnames:
            check(
                {row["record_origin"] for row in records}.issubset(RECORD_ORIGINS),
                f"{spec.filename} record origins are governed",
            )
        if "fact_state" in spec.fieldnames:
            check(
                {row["fact_state"] for row in records}.issubset(FACT_STATES),
                f"{spec.filename} fact states are governed",
            )
        if "epistemic_state" in spec.fieldnames:
            check(
                {row["epistemic_state"] for row in records}.issubset(EPISTEMIC_STATES),
                f"{spec.filename} epistemic states are governed",
            )

    production = all_rows["monthly_production_2026.csv"]
    inventory = all_rows["inventory_rollforward_2026.csv"]
    contracts = all_rows["uranium_contracts.csv"]
    collars = all_rows["drill_collars.csv"]
    employees = all_rows["employee_census_2026.csv"]
    ownership = all_rows["ownership_history.csv"]
    resources = all_rows["resource_basis.csv"]
    ppa = all_rows["purchase_price_allocation.csv"]
    statements = all_rows["financial_statements_2026.csv"]
    quality = all_rows["quality_of_earnings.csv"]
    vdr = all_rows["virtual_data_room_index.csv"]

    check(len(production) == 12, "12 monthly production records")
    check(decimal_total(production, "ore_tons") == 175_000, "175,000 ore tons")
    check(
        decimal_total(production, "contained_u3o8_lb") == 595_000,
        "595,000 contained U3O8 pounds",
    )
    check(
        decimal_total(production, "u3o8_produced_lb") == 547_400,
        "547,400 U3O8 pounds produced",
    )
    check(
        decimal_total(production, "u3o8_sold_lb") == 500_000,
        "500,000 U3O8 pounds sold",
    )
    check(
        decimal_total(production, "revenue_usd") == 36_475_000,
        "$36.475 million modeled revenue",
    )
    check(
        sum(row["period_role"] == "SYNTHETIC_CALIBRATION" for row in production) == 8,
        "eight synthetic-calibration months",
    )
    check(
        sum(row["period_role"] == "MANAGEMENT_FORECAST" for row in production) == 4,
        "four management-forecast months",
    )
    core_resource = core["resource_basis"]
    core_mine = core["mine_2026"]
    core_resource_contained = (
        Decimal(core_resource["indicated_tons"])
        * Decimal(2000)
        * Decimal(str(core_resource["grade_u3o8_pct"]))
        / Decimal(100)
    )
    core_resource_recoverable = (
        core_resource_contained * Decimal(str(core_resource["modeled_recovery_pct"])) / Decimal(100)
    )
    core_mine_contained = (
        Decimal(core_mine["ore_tons"])
        * Decimal(2000)
        * Decimal(str(core_mine["head_grade_u3o8_pct"]))
        / Decimal(100)
    )
    core_mine_produced = (
        core_mine_contained * Decimal(str(core_mine["recovery_pct"])) / Decimal(100)
    )
    check(
        core_resource_contained == Decimal(core_resource["contained_lb"]),
        "core resource tons times grade equals contained pounds",
    )
    check(
        core_resource_recoverable == Decimal(core_resource["recoverable_lb"]),
        "core resource contained pounds times recovery equals recoverable pounds",
    )
    check(
        core_mine_contained == Decimal(core_mine["contained_u3o8_lb"]),
        "core mine tons times grade equals contained pounds",
    )
    check(
        core_mine_produced == Decimal(core_mine["produced_u3o8_lb"]),
        "core mine contained pounds times recovery equals produced pounds",
    )
    for index, row in enumerate(production, 1):
        calculated_contained = (
            Decimal(row["ore_tons"])
            * Decimal(2000)
            * Decimal(row["head_grade_u3o8_pct"])
            / Decimal(100)
        )
        calculated_produced = (
            Decimal(row["contained_u3o8_lb"]) * Decimal(row["recovery_pct"]) / Decimal(100)
        )
        check(
            abs(calculated_contained - Decimal(row["contained_u3o8_lb"])) <= Decimal("0.25"),
            f"production month {index} tons times grade agrees to contained pounds",
        )
        check(
            abs(calculated_produced - Decimal(row["u3o8_produced_lb"])) <= Decimal("0.001"),
            f"production month {index} contained pounds times recovery agrees to production",
        )
        check(
            Decimal(row["u3o8_sold_lb"]) * Decimal(row["modeled_realized_price_usd_lb"])
            == Decimal(row["revenue_usd"]),
            f"production month {index} sales times price agrees to revenue",
        )

    for row in resources:
        calculated_contained = (
            Decimal(row["tons"]) * Decimal(2000) * Decimal(row["grade_u3o8_pct"]) / Decimal(100)
        )
        check(
            calculated_contained == Decimal(row["contained_lb"]),
            f"resource {row['basis_id']} tons times grade equals contained pounds",
        )
        if row["recoverable_lb"]:
            calculated_recoverable = (
                Decimal(row["contained_lb"]) * Decimal(row["modeled_recovery_pct"]) / Decimal(100)
            )
            check(
                calculated_recoverable == Decimal(row["recoverable_lb"]),
                f"resource {row['basis_id']} recovery agrees to recoverable pounds",
            )
        else:
            check(
                row["modeled_recovery_pct"] == "",
                f"resource {row['basis_id']} has no unsupported recovery input",
            )
    check(
        all(row["epistemic_state"] == "SUPPORTED_ESTIMATE" for row in resources),
        "resource-basis rows retain SUPPORTED_ESTIMATE epistemic state",
    )

    check(len(inventory) == 12, "12 monthly inventory records")
    check(
        Decimal(inventory[0]["opening_finished_u3o8_lb"]) == 125_000,
        "125,000 pound opening inventory",
    )
    check(
        Decimal(inventory[-1]["ending_finished_u3o8_lb"]) == 172_400,
        "172,400 pound ending inventory",
    )
    for index, row in enumerate(inventory):
        opening = Decimal(row["opening_finished_u3o8_lb"])
        produced = Decimal(row["production_u3o8_lb"])
        sold = Decimal(row["sales_u3o8_lb"])
        ending = Decimal(row["ending_finished_u3o8_lb"])
        check(
            opening + produced - sold == ending,
            f"inventory month {index + 1} rolls forward",
        )
        check(
            produced == Decimal(production[index]["u3o8_produced_lb"])
            and sold == Decimal(production[index]["u3o8_sold_lb"]),
            f"inventory month {index + 1} agrees to production",
        )
        if index:
            check(
                opening == Decimal(inventory[index - 1]["ending_finished_u3o8_lb"]),
                f"inventory month {index + 1} carries prior closing balance",
            )

    contract_pounds = decimal_total(contracts, "committed_lb")
    contract_revenue = sum(
        Decimal(row["committed_lb"]) * Decimal(row["modeled_price_usd_lb"]) for row in contracts
    )
    check(contract_pounds == 500_000, "contract book equals modeled sales")
    check(contract_revenue == 36_475_000, "contract book equals modeled revenue")
    check(
        contract_revenue / contract_pounds == Decimal("72.95"),
        "$72.95 weighted modeled realized price",
    )

    check(len(collars) == 240, "240 drill collars")
    check(
        all(
            row["coordinate_crs"] == "NAD83 / UTM zone 13N"
            and row["epsg_code"] == "26913"
            and row["utm_zone"] == "13N"
            and row["horizontal_datum"] == "NAD83"
            for row in collars
        ),
        "drill coordinates declare NAD83 / UTM zone 13N (EPSG:26913)",
    )
    check(
        all(
            Decimal("339560") <= Decimal(row["easting_m"]) <= Decimal("343760")
            and Decimal("4684780") <= Decimal(row["northing_m"]) <= Decimal("4687780")
            for row in collars
        ),
        "drill coordinates remain in the projected Red Wash site envelope",
    )
    check(len(all_rows["downhole_surveys.csv"]) == 720, "720 downhole surveys")
    check(len(all_rows["assays.csv"]) == 2_400, "2,400 assay intervals")
    check(len(employees) == 140, "140 FTE establishment")
    check(
        sum(row["organization"] == "Pale Sun" for row in employees) == 12,
        "12 Pale Sun business-layer FTE",
    )
    check(
        sum(row["organization"] == "Red Wash" for row in employees) == 128,
        "128 Red Wash site FTE",
    )
    check(
        len(vdr) == 176,
        "176 synthetic VDR index records",
    )
    vdr_payload_fields = ("vdr_id", "category", "document", "effective_date", "review_status")
    check(
        all(
            row["document_sha256"]
            == canonical_payload_sha256({field: row[field] for field in vdr_payload_fields})
            for row in vdr
        ),
        "VDR document hashes bind each complete canonical synthetic record payload",
    )
    check(
        all(
            row["document_sha256"] != hashlib.sha256(row["vdr_id"].encode()).hexdigest()
            for row in vdr
        ),
        "VDR document hashes are not identity-only hashes",
    )
    check(len(all_rows["permit_register.csv"]) == 14, "14 synthetic permit records")
    check(
        len(all_rows["diligence_findings.csv"]) == 25,
        "25 synthetic diligence findings",
    )
    check(
        len(all_rows["environmental_monitoring.csv"]) == 180,
        "180 synthetic monitoring records through 2026-Q2",
    )
    check(
        {row["station"] for row in all_rows["environmental_monitoring.csv"]}
        == {"MW-04", "MW-09", "MW-12", "MW-17", "MW-21", "TAIL-UD-1"},
        "monitoring output covers the five named wells and tailings underdrain",
    )
    check(
        max(row["period"] for row in all_rows["environmental_monitoring.csv"]) == "2026-Q2",
        "monitoring evidence does not leak an incomplete or future quarter",
    )
    check(
        len(all_rows["maintenance_backlog.csv"]) == 60,
        "60 synthetic maintenance records",
    )
    check(
        len(all_rows["external_source_register.csv"]) == 23,
        "23 authoritative external-research records",
    )

    quality_amounts = [Decimal(row["amount_usd"]) for row in quality]
    check(
        sum(quality_amounts[:-1], Decimal(0)) == quality_amounts[-1] == 2_400_000,
        "quality-of-earnings adjustments reconcile to $2.4 million",
    )
    quality_by_role = {row["line_role"]: [] for row in quality}
    for row in quality:
        quality_by_role[row["line_role"]].append(row)
    check(
        len(quality_by_role.get("STARTING_POINT", [])) == 1
        and all(
            row["fact_state"] == "SCENARIO_INPUT"
            and row["epistemic_state"] == "PROVISIONAL_ASSUMPTION"
            for row in quality_by_role.get("STARTING_POINT", [])
        ),
        "seller QoE starting point remains a provisional scenario input",
    )
    check(
        len(quality_by_role.get("ADJUSTMENT", [])) == 4
        and all(
            row["fact_state"] == "SCENARIO_INPUT" and row["epistemic_state"] == "SUPPORTED_ESTIMATE"
            for row in quality_by_role.get("ADJUSTMENT", [])
        ),
        "QoE adjustments remain supported scenario inputs",
    )
    check(
        len(quality_by_role.get("RESULT", [])) == 1
        and all(
            row["fact_state"] == "DERIVED" and row["epistemic_state"] == "DERIVED"
            for row in quality_by_role.get("RESULT", [])
        ),
        "only the normalized QoE result is DERIVED",
    )

    ownership_by_display = {row["owner_display_name"]: row for row in ownership}
    northstar = ownership_by_display.get("Northstar Resources", {})
    current_owner = next((row for row in ownership if row["end_date"] == ""), {})
    check(
        northstar.get("owner_display_name_state") == "PROVISIONAL"
        and northstar.get("owner_legal_name") == ""
        and northstar.get("owner_legal_name_state") == "OPEN"
        and northstar.get("fact_state") == "PROVISIONAL_CANON"
        and northstar.get("epistemic_state") == "PROVISIONAL_ASSUMPTION",
        "Northstar display identity remains PROVISIONAL and legal identity OPEN",
    )
    check(
        current_owner.get("owner_display_name") == "Sable Harbor"
        and current_owner.get("owner_display_name_state") == "LOCKED"
        and current_owner.get("owner_legal_name") == ""
        and current_owner.get("owner_legal_name_state") == "OPEN"
        and current_owner.get("fact_state") == "LOCKED_CANON"
        and current_owner.get("epistemic_state") == "LOCKED",
        "current ownership is LOCKED without inventing operator legal identity",
    )
    check(
        all(
            (row["owner_legal_name_state"] == "OPEN") == (row["owner_legal_name"] == "")
            for row in ownership
        ),
        "ownership legal-name values agree with their OPEN state",
    )

    ppa_by_class: dict[str, Decimal] = {}
    ppa_by_line = {row["line"]: Decimal(row["amount_usd"]) for row in ppa}
    for row in ppa:
        ppa_by_class[row["classification"]] = ppa_by_class.get(
            row["classification"], Decimal(0)
        ) + Decimal(row["amount_usd"])
    net_identifiable = ppa_by_class["ASSET"] + ppa_by_class["LIABILITY"]
    check(net_identifiable == 28_000_000, "PPA net identifiable assets equal $28 million")
    check(
        ppa_by_line["Net identifiable assets"] == net_identifiable,
        "PPA subtotal agrees to asset and liability components",
    )
    check(
        net_identifiable + ppa_by_class["CONSIDERATION"] == 0,
        "PPA net assets reconcile to cash consideration",
    )
    check(ppa_by_class["RESULT"] == 0, "PPA has zero goodwill or bargain purchase")
    check(
        ppa_by_line["Asset retirement obligation"] == -16_000_000,
        "PPA carries $16 million accounting ARO",
    )
    check(
        core["closure"]["current_cost_usd"] == 25_000_000
        and core["closure"]["opening_aro_usd"] == 16_000_000,
        "current-cost closure basis remains distinct from accounting ARO",
    )

    dd_and_a_model = core["dd_and_a_model_2026"]
    check(
        dd_and_a_model["method"] == "COMPOSITE_UNITS_OF_PRODUCTION"
        and dd_and_a_model["asset_basis_component_paths"]
        == [
            "transaction.operating_assets_usd",
            "transaction.capitalized_rehabilitation_usd",
        ]
        and dd_and_a_model["recoverable_units_source_path"] == "resource_basis.recoverable_lb"
        and dd_and_a_model["production_units_source_path"] == "mine_2026.produced_u3o8_lb"
        and dd_and_a_model["rounding"] == "ROUND_HALF_UP_TO_WHOLE_USD",
        "DD&A model names every controlled cross-record driver",
    )
    check(
        dd_and_a_model["fact_state"] == "MODEL_PROPOSED"
        and dd_and_a_model["epistemic_state"] == "SUPPORTED_ESTIMATE"
        and "does not allocate purchase-price classes" in dd_and_a_model["boundary"],
        "DD&A model remains a supported model rather than an invented PPA allocation",
    )
    dd_and_a_asset_basis = Decimal(core["transaction"]["operating_assets_usd"]) + Decimal(
        core["transaction"]["capitalized_rehabilitation_usd"]
    )
    check(dd_and_a_asset_basis == 50_000_000, "DD&A composite asset basis reconciles to $50M")
    check(
        Decimal(core["mine_2026"]["produced_u3o8_lb"])
        / Decimal(core["resource_basis"]["recoverable_lb"])
        == Decimal("0.07"),
        "DD&A units-of-production factor reconciles to 7 percent",
    )
    derived_dd_and_a = derived_dd_and_a_usd(core)
    check(derived_dd_and_a == 3_500_000, "controlled drivers derive approximately $3.5M DD&A")

    statement = {(row["statement"], row["line"]): Decimal(row["amount_usd"]) for row in statements}
    check(
        all(row["fact_state"] == "DERIVED" for row in statements),
        "financial outputs are DERIVED rather than locked observations",
    )
    check(
        statement[("Inventory Cost Bridge", "Opening finished inventory cash cost")]
        + statement[("Inventory Cost Bridge", "2026 cash production cost incurred")]
        == statement[("Inventory Cost Bridge", "Cash cost available for sale")],
        "cash inventory costs available reconcile",
    )
    check(
        statement[("Inventory Cost Bridge", "Cash cost available for sale")]
        + statement[("Inventory Cost Bridge", "Cash cost released to sales")]
        == statement[("Inventory Cost Bridge", "Ending finished inventory cash cost")],
        "cash inventory cost rollforward reconciles",
    )
    check(
        statement[("Inventory Cost Bridge", "Opening finished inventory DD&A")]
        + statement[("Inventory Cost Bridge", "2026 DD&A incurred")]
        == statement[("Inventory Cost Bridge", "DD&A available for sale")],
        "DD&A inventory costs available reconcile",
    )
    check(
        statement[("Inventory Cost Bridge", "2026 DD&A incurred")] == derived_dd_and_a,
        "statement DD&A equals the independent units-of-production derivation",
    )
    check(
        statement[("Inventory Cost Bridge", "DD&A available for sale")]
        + statement[("Inventory Cost Bridge", "DD&A released to sales")]
        == statement[("Inventory Cost Bridge", "Ending finished inventory DD&A")],
        "DD&A inventory cost rollforward reconciles",
    )

    income_components = [
        "Uranium revenue",
        "Cash production cost of sales",
        "DD&A in cost of sales",
        "Production and mineral taxes",
        "Royalties",
        "Freight, assay and handling",
    ]
    check(
        sum((statement[("Income Statement", line)] for line in income_components), Decimal(0))
        == statement[("Income Statement", "Gross profit")],
        "income-statement gross profit reconciles",
    )
    check(
        statement[("Income Statement", "Gross profit")]
        + statement[("Income Statement", "Pale Sun business and site G&A")]
        == statement[("Income Statement", "Operating income")],
        "income-statement operating income reconciles",
    )
    check(
        statement[("Income Statement", "Operating income")]
        + statement[("Income Statement", "ARO accretion")]
        == statement[("Income Statement", "Income before tax")],
        "income before tax reconciles",
    )
    check(
        statement[("Income Statement", "Income before tax")]
        + statement[("Income Statement", "Income tax")]
        == statement[("Income Statement", "Net income")],
        "net income reconciles",
    )
    check(
        sum(
            (
                statement[("Cash Flow", line)]
                for line in (
                    "Net income",
                    "DD&A addback",
                    "ARO accretion addback",
                    "Increase in finished inventory cash cost",
                    "Other working-capital use",
                )
            ),
            Decimal(0),
        )
        == statement[("Cash Flow", "Operating cash flow")],
        "operating cash flow reconciles",
    )
    check(
        statement[("Cash Flow", "Operating cash flow")]
        + statement[("Cash Flow", "Sustaining capital")]
        + statement[("Cash Flow", "Rehabilitation capital")]
        == statement[("Cash Flow", "Free cash flow")],
        "free cash flow reconciles",
    )

    assumptions = core["inventory_cost_assumptions_2026"]
    mine = core["mine_2026"]
    finance = core["finance_2026"]
    available_lb = Decimal(mine["opening_finished_inventory_lb"] + mine["produced_u3o8_lb"])
    opening_cash = Decimal(mine["opening_finished_inventory_lb"]) * Decimal(
        str(assumptions["opening_finished_inventory_cash_cost_usd_lb"])
    )
    opening_dda = Decimal(mine["opening_finished_inventory_lb"]) * Decimal(
        str(assumptions["opening_finished_inventory_dd_and_a_usd_lb"])
    )
    expected_cash_cogs = rounded_usd(
        (opening_cash + Decimal(finance["cash_production_cost_incurred_usd"]))
        * Decimal(mine["sold_u3o8_lb"])
        / available_lb
    )
    expected_dda_cogs = rounded_usd(
        (opening_dda + derived_dd_and_a) * Decimal(mine["sold_u3o8_lb"]) / available_lb
    )
    check(
        statement[("Income Statement", "Cash production cost of sales")] == -expected_cash_cogs,
        "cash cost of sales follows weighted-average inventory method",
    )
    check(
        statement[("Income Statement", "DD&A in cost of sales")] == -expected_dda_cogs,
        "DD&A cost of sales follows weighted-average inventory method",
    )

    events = all_rows["transport_capacity_events.csv"]
    exceptions = all_rows["shipment_schedule_exceptions.csv"]
    market_scan = all_rows["carrier_market_scan.csv"]
    rail = all_rows["rail_access_candidates.csv"]
    fit_gaps = all_rows["aru_red_wash_fit_gap.csv"]
    gates = all_rows["aru_red_wash_integration_gates.csv"]
    capex = all_rows["aru_red_wash_preliminary_capex.csv"]
    custody = all_rows["custody_authority_matrix.csv"]
    check(
        all(Decimal(row["annual_revenue_impact_usd"]) == 0 for row in events),
        "every bridge event has zero annual 2025 revenue impact",
    )
    check(
        all(Decimal(row["annual_revenue_impact_usd"]) == 0 for row in exceptions),
        "every shipment exception has zero annual 2025 revenue impact",
    )
    event_types = {row["event_type"] for row in events}
    check(
        {
            "carrier_consolidation",
            "capacity_allocation",
            "replacement_search",
            "rail_mapping_discovery",
        }.issubset(event_types),
        "bridge preserves the consolidation-to-operating-search event chain",
    )
    check(
        any(row["record_origin"] == "EXTERNAL_RESEARCH" for row in events)
        and any(row["record_origin"] == "SYNTHETIC_COMPANY_EVENT" for row in events),
        "external freight backdrop is distinct from synthetic company events",
    )
    external_source_ids = {row["source_id"] for row in all_rows["external_source_register.csv"]}
    referenced_external_ids = {
        source_id
        for row in events
        if row["record_origin"] == "EXTERNAL_RESEARCH"
        for source_id in row["source_id"].split(";")
    }
    check(
        referenced_external_ids and referenced_external_ids.issubset(external_source_ids),
        "external freight backdrop references registered reality anchors",
    )
    check(
        all(row["relationship_to_aru"] in {"none", "future diligence only"} for row in market_scan),
        "carrier scan contains no pre-existing ARU relationship",
    )
    check(
        any(row["incumbent_2025"] == "1" and row["qualified_2025"] == "1" for row in market_scan),
        "qualified external carrier remains represented for 2025",
    )
    check(
        len(rail) == 1
        and rail[0]["direct_mine_connection"] == "0"
        and rail[0]["suitable_transload"] == "0"
        and rail[0]["uranium_capability"] == "0",
        "ARU/BS&T remains an imperfect, non-turnkey interface",
    )
    check(
        len(fit_gaps) == 3
        and all(row["status"] == "OPEN" and row["blocks_custody"] == "1" for row in fit_gaps),
        "all three required ARU fit gaps remain open and custody-blocking",
    )
    check(
        min(int(row["earliest_month"]) for row in gates) == 0
        and max(int(row["latest_month"]) for row in gates) == 18
        and all(row["status"] == "OPEN" for row in gates),
        "integration gates preserve the 0-18 month open planning horizon",
    )
    capex_with_amount = [row for row in capex if row["amount_usd"]]
    check(
        len(capex_with_amount) == 1
        and Decimal(capex_with_amount[0]["amount_usd"]) == 15_000_000
        and capex_with_amount[0]["amount_state"] == "SCENARIO_INPUT",
        "$15 million preliminary screen is the only quantified interface amount",
    )
    check(
        all(
            row["amount_usd"] == ""
            and row["amount_state"] == "OPEN"
            and row["epistemic_state"] == "OPEN"
            for row in capex
            if row not in capex_with_amount
        ),
        "preliminary capex components remain unquantified and OPEN",
    )
    check(
        any(
            row["activity"] == "Physical custody and transport"
            and row["aru_bst_authority"] == "none"
            and row["status"] == "OPEN"
            for row in custody
        ),
        "direct ARU/BS&T uranium custody remains gated and unauthorized",
    )
    check(
        bridge["boundaries"]["pre_existing_relationship"] is False
        and bridge["boundaries"]["red_wash_2025_carrier"] == "qualified external carriers"
        and bridge["boundaries"]["annual_2025_revenue_impact_usd"] == 0,
        "authoritative bridge boundary preserves 2025 relationship and revenue controls",
    )
    check(
        bridge["boundaries"]["preliminary_interface_envelope_usd"] == 15_000_000
        and bridge["boundaries"]["interface_envelope_booked"] is False,
        "authoritative bridge boundary keeps the $15 million screen unbooked",
    )
    check(
        bridge["boundaries"]["direct_uranium_custody_authorized"] is False
        and bridge["boundaries"]["full_aru_case_authorized"] is False,
        "authoritative bridge boundary leaves custody and full ARU case unauthorized",
    )
    check(
        len(bridge["open_aru_fields"]) == 32
        and "whether BS&T ultimately takes direct uranium custody" in bridge["open_aru_fields"],
        "all 32 full-case ARU fields remain explicitly open",
    )
    for condition, label in projection_checks(
        core,
        bridge,
        transaction_projection,
        bridge_projection,
        transaction_canon,
        decision_addendum,
    ):
        check(condition, label)

    manifest_path = DIST / MANIFEST_FILENAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lineage_fields = {
        "scenario_id",
        "scenario_version",
        "generator_version",
        "input_version",
        "seed",
        "effective_period",
        "source_snapshot_ids",
        "built_at",
        "output_hashes",
    }
    check(
        lineage_fields.issubset(manifest),
        "generation manifest carries every constitutional lineage field",
    )
    check(
        manifest["scenario_id"] == "red-wash-2025-2026"
        and manifest["scenario_version"] == core["version"] == "1.0.0"
        and manifest["input_version"] == "red-wash-public-source/1.0.0"
        and manifest["seed"] == 20250718,
        "generation manifest binds the governed scenario, inputs, and seed",
    )
    check(
        manifest["generator_version"] == manifest["generator"]["version"] == "1.0.0"
        and manifest["seed"] == manifest["generator"]["seed"],
        "top-level generator lineage agrees with detailed generator identity",
    )
    check(
        manifest["effective_period"]
        == {
            "from": "2024-08-19",
            "through": "2026-12-31",
            "synthetic_calibration_through": core["synthetic_calibration_through"],
        },
        "generation manifest carries the governed scenario effective period",
    )
    check(
        manifest["built_at"] == f"{core['prepared_at']}T00:00:00Z"
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", manifest["built_at"]) is not None
        and manifest["built_at_semantics"]
        == "DETERMINISTIC_CANON_PREPARED_DATE_AT_00_00_00Z_NOT_WALL_CLOCK",
        "built_at is a deterministic RFC3339 canon-prepared timestamp, never wall-clock time",
    )
    manifest_sources = {row["path"]: row for row in manifest["source_inputs"]}
    for name in SOURCE_FILENAMES:
        relative = f"red_wash/source/{name}"
        path = SOURCE / name
        check(relative in manifest_sources, f"manifest includes source {name}")
        if relative in manifest_sources:
            check(
                manifest_sources[relative]["sha256"] == sha256_path(path)
                and manifest_sources[relative]["bytes"] == path.stat().st_size,
                f"manifest source hash and size agree for {name}",
            )
    manifest_generated = {row["path"]: row for row in manifest["generated_files"]}
    for spec in DATASETS:
        relative = f"red_wash/generated/{spec.filename}"
        path = GENERATED / spec.filename
        check(relative in manifest_generated, f"manifest includes generated {spec.filename}")
        if relative in manifest_generated:
            item = manifest_generated[relative]
            check(
                item["sha256"] == sha256_path(path)
                and item["bytes"] == path.stat().st_size
                and item["rows"] == len(all_rows[spec.filename])
                and tuple(item["columns"]) == spec.fieldnames,
                f"manifest generated contract agrees for {spec.filename}",
            )
    expected_markers = {
        f"red_wash/generated/{GENERATED_MARKER}": GENERATED / GENERATED_MARKER,
        f"red_wash/dist/{DIST_MARKER}": DIST / DIST_MARKER,
    }
    manifest_markers = {row["path"]: row for row in manifest["ownership_markers"]}
    check(
        set(manifest_markers) == set(expected_markers),
        "manifest ownership-marker allowlist is exact",
    )
    for relative, path in expected_markers.items():
        check(
            manifest_markers[relative]["sha256"] == sha256_path(path)
            and manifest_markers[relative]["bytes"] == path.stat().st_size,
            f"manifest binds ownership marker {relative}",
        )
    for relative, expected in VISUAL_HASHES.items():
        path = REPOSITORY_ROOT / relative
        check(path.is_file(), f"approved visual exists: {relative}")
        if path.is_file():
            check(
                sha256_path(path) == expected,
                f"approved visual hash matches: {relative}",
            )
    visual_control_path = REPOSITORY_ROOT / "assets/brand/red_wash_visual_manifest.json"
    visual_control = json.loads(visual_control_path.read_text(encoding="utf-8"))
    controlled_visuals = {
        row["canonical_path"]: (row["sha256"], row["bytes"]) for row in visual_control["assets"]
    }
    check(
        visual_control["binary_ingestion_state"] == "COMPLETE"
        and controlled_visuals
        == {
            relative: (expected, (REPOSITORY_ROOT / relative).stat().st_size)
            for relative, expected in VISUAL_HASHES.items()
        },
        "visual-control manifest is COMPLETE and matches the exact asset allowlist",
    )
    check(
        {row["path"]: row["sha256"] for row in manifest["visual_assets"]} == VISUAL_HASHES,
        "manifest records all exact owner-approved visual hashes",
    )
    expected_snapshot_revisions = {
        **{row["path"]: f"sha256:{row['sha256']}" for row in manifest["source_inputs"]},
        **{row["path"]: f"sha256:{row['sha256']}" for row in manifest["visual_assets"]},
        "assets/brand/red_wash_visual_manifest.json": (
            f"sha256:{sha256_path(visual_control_path)}"
        ),
    }
    snapshot_rows = manifest["source_snapshot_ids"]
    check(
        {row["path"]: row["revision"] for row in snapshot_rows} == expected_snapshot_revisions,
        "constitutional source snapshot IDs bind every controlled source and visual",
    )
    check(
        all(row["repository"] == "SquirmyWormy275/SABLEHARBOR" for row in snapshot_rows),
        "constitutional source snapshot IDs name the public repository",
    )
    check(
        manifest["aru_bst_bridge_controls"]["open_aru_fields"] == sorted(bridge["open_aru_fields"])
        and manifest["aru_bst_bridge_controls"]["full_aru_case_state"] == "OPEN",
        "manifest preserves every unresolved ARU field and OPEN full-case state",
    )
    check(
        manifest["aru_bst_bridge_controls"]["source_commit_state"]
        == "REQUIRES_EXACT_RELEASE_MANIFEST_BINDING",
        "public bridge preserves its exact release-manifest binding requirement",
    )
    check(
        manifest["visual_control_manifest"]["sha256"] == sha256_path(visual_control_path)
        and manifest["visual_control_manifest"]["bytes"] == visual_control_path.stat().st_size,
        "package manifest binds the visual-control manifest",
    )

    database = DIST / DATABASE_FILENAME
    check(database.is_file(), "SQLite database exists")
    if database.is_file():
        expected_output_hashes = {
            **{row["path"]: row["sha256"] for row in manifest["generated_files"]},
            f"red_wash/dist/{DATABASE_FILENAME}": sha256_path(database),
        }
        check(
            manifest["output_hashes"] == expected_output_hashes
            and manifest["output_hash_scope"] == "ALL_NON_SELF_GENERATED_OUTPUTS",
            "constitutional output hashes bind every generated CSV and SQLite output",
        )
        check(
            manifest["database"]["sha256"] == sha256_path(database),
            "manifest SQLite hash agrees",
        )
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        connection.execute("PRAGMA foreign_keys = ON")
        check(
            connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "SQLite integrity_check",
        )
        check(
            connection.execute("PRAGMA foreign_key_check").fetchall() == [],
            "SQLite foreign_key_check",
        )
        for spec in DATASETS:
            info = connection.execute(f'PRAGMA table_info("{spec.table}")').fetchall()
            check(
                tuple(row[1] for row in info) == spec.fieldnames,
                f"SQLite column contract: {spec.table}",
            )
            check(
                tuple(row[2] for row in info)
                == tuple(column.sqlite_type for column in spec.columns),
                f"SQLite type contract: {spec.table}",
            )
            check(
                connection.execute(f'SELECT COUNT(*) FROM "{spec.table}"').fetchone()[0]
                == len(all_rows[spec.filename]),
                f"SQLite row count: {spec.table}",
            )
        production_view = connection.execute(
            """SELECT month_count,ore_tons,contained_lb,produced_lb,sold_lb,revenue_usd
               FROM v_2026_production_reconciliation"""
        ).fetchone()
        check(
            production_view == (12, 175_000, 595_000, 547_400, 500_000, 36_475_000),
            "SQLite production reconciliation view",
        )
        inventory_view = connection.execute(
            """SELECT opening_lb,production_lb,sales_lb,ending_lb
               FROM v_2026_inventory_reconciliation"""
        ).fetchone()
        check(
            inventory_view == (125_000, 547_400, 500_000, 172_400),
            "SQLite inventory reconciliation view",
        )
        ppa_view = connection.execute(
            """SELECT net_identifiable_assets,consideration,goodwill_or_bargain_purchase
               FROM v_purchase_price_allocation_reconciliation"""
        ).fetchone()
        check(
            ppa_view == (28_000_000, -28_000_000, 0),
            "SQLite PPA reconciliation view",
        )
        bridge_view = connection.execute(
            """SELECT event_revenue_impact_usd,exception_revenue_impact_usd,
                      preliminary_envelope_usd,open_custody_gate_count
               FROM v_aru_red_wash_bridge_controls"""
        ).fetchone()
        check(
            bridge_view[0:3] == (0, 0, 15_000_000) and bridge_view[3] > 0,
            "SQLite ARU/BS&T bridge control view",
        )
        metadata = dict(connection.execute("SELECT key,value FROM package_metadata"))
        check(
            metadata["scenario_id"] == manifest["scenario_id"]
            and metadata["scenario_version"] == manifest["scenario_version"]
            and metadata["input_version"] == manifest["input_version"]
            and json.loads(metadata["effective_period_json"]) == manifest["effective_period"]
            and metadata["built_at"] == manifest["built_at"]
            and metadata["built_at_semantics"] == manifest["built_at_semantics"],
            "SQLite metadata preserves constitutional scenario and temporal lineage",
        )
        check(
            metadata["no_preexisting_relationship"] == "true"
            and metadata["external_carriers_all_2025"] == "true"
            and metadata["annual_2025_revenue_impact_usd"] == "0"
            and metadata["preliminary_capex_envelope_usd"] == "15000000"
            and metadata["custody_state"] == "OPEN"
            and metadata["full_aru_case_state"] == "OPEN",
            "SQLite package metadata preserves bridge boundaries",
        )
        check(
            metadata["bridge_source_commit_state"] == "REQUIRES_EXACT_RELEASE_MANIFEST_BINDING",
            "SQLite metadata preserves the exact release-manifest binding requirement",
        )
        check(
            json.loads(metadata["open_aru_fields_json"]) == sorted(bridge["open_aru_fields"]),
            "SQLite metadata preserves every open ARU field",
        )
        check(
            connection.execute("SELECT COUNT(*) FROM source_provenance").fetchone()[0]
            == len(SOURCE_FILENAMES),
            "SQLite source provenance is complete",
        )
        check(
            connection.execute("SELECT COUNT(*) FROM generated_file_manifest").fetchone()[0]
            == len(DATASETS),
            "SQLite generated-file manifest is complete",
        )
        check(
            connection.execute("SELECT COUNT(*) FROM visual_asset_manifest").fetchone()[0]
            == len(VISUAL_HASHES),
            "SQLite visual manifest is complete",
        )
        connection.close()

    check(
        manifest["controlled_totals"]["derived_dd_and_a_incurred_usd"] == int(derived_dd_and_a),
        "manifest derived DD&A agrees",
    )
    check(
        manifest["controlled_totals"]["derived_net_income_usd"]
        == int(statement[("Income Statement", "Net income")]),
        "manifest derived net income agrees",
    )
    check(
        manifest["controlled_totals"]["derived_operating_cash_flow_usd"]
        == int(statement[("Cash Flow", "Operating cash flow")]),
        "manifest derived operating cash flow agrees",
    )
    check(
        manifest["controlled_totals"]["derived_free_cash_flow_usd"]
        == int(statement[("Cash Flow", "Free cash flow")]),
        "manifest derived free cash flow agrees",
    )

    result: dict[str, object] = {
        "status": "PASS" if not failures else "FAIL",
        "checks_passed": len(checks),
        "checks_total": len(checks) + len(failures),
        "failures": failures,
        "derived_financials": {
            "net_income_usd": int(statement[("Income Statement", "Net income")]),
            "operating_cash_flow_usd": int(statement[("Cash Flow", "Operating cash flow")]),
            "free_cash_flow_usd": int(statement[("Cash Flow", "Free cash flow")]),
        },
    }
    if failures:
        raise ValidationFailure(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generate", action="store_true", help="run the canonical builder before validation"
    )
    args = parser.parse_args()
    try:
        result = validate(args.generate)
    except (OSError, ValueError, KeyError, sqlite3.Error, ValidationFailure) as error:
        if isinstance(error, ValidationFailure):
            result = error.result
        else:
            result = {"status": "FAIL", "error": str(error)}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
