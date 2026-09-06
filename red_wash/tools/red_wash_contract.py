"""Shared schema contract for the deterministic Red Wash public package.

This module contains declarations only.  The builder and validator share the file and
column allowlists, but the validator independently recomputes all business
reconciliations so a generator defect cannot bless its own output.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
SOURCE = ROOT / "source"
GENERATED = ROOT / "generated"
DIST = ROOT / "dist"

SOURCE_FILENAMES = frozenset(
    {
        "aru_bst_bridge.json",
        "core_operating_data.json",
        "external_source_register.csv",
    }
)

GENERATED_MARKER = ".red-wash-generated"
DIST_MARKER = ".red-wash-dist"
DATABASE_FILENAME = "red_wash_transaction_operating_record_v1.sqlite3"
MANIFEST_FILENAME = "red_wash_database_manifest.json"

RECORD_ORIGINS = frozenset(
    {
        "EXTERNAL_REALITY_ANCHOR",
        "EXTERNAL_RESEARCH",
        "EXTERNAL_RESEARCH_RETROSPECTIVE",
        "PUBLIC_SYNTHETIC_DIEGETIC",
        "SYNTHETIC_COMPANY_ANALYSIS",
        "SYNTHETIC_COMPANY_EVENT",
        "SYNTHETIC_COMPANY_PLAN",
        "SYNTHETIC_COMPANY_RECORD",
    }
)
FACT_STATES = frozenset(
    {
        "DERIVED",
        "EXTERNAL_RESEARCH",
        "LEGACY_CALIBRATION",
        "LOCKED_CANON",
        "MODEL_PROPOSED",
        "OPEN_CANON",
        "PROVISIONAL_CANON",
        "SCENARIO_INPUT",
        "SYNTHETIC_INSTANCE",
    }
)
EPISTEMIC_STATES = frozenset(
    {
        "CONFLICT",
        "DERIVED",
        "LOCKED",
        "OPEN",
        "PROVISIONAL_ASSUMPTION",
        "SCENARIO",
        "SUPPORTED_ESTIMATE",
        "SUPERSEDED",
    }
)


@dataclass(frozen=True)
class Column:
    name: str
    sqlite_type: str = "TEXT"
    nullable: bool = False


@dataclass(frozen=True)
class Dataset:
    filename: str
    columns: tuple[Column, ...]
    primary_key: tuple[str, ...]
    foreign_keys: tuple[tuple[tuple[str, ...], str, tuple[str, ...]], ...] = ()
    checks: tuple[str, ...] = ()

    @property
    def table(self) -> str:
        return self.filename.removesuffix(".csv")

    @property
    def fieldnames(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)


T = Column
I = lambda name, nullable=False: Column(name, "INTEGER", nullable)  # noqa: E731, E741
R = lambda name, nullable=False: Column(name, "REAL", nullable)  # noqa: E731
N = lambda name: Column(name, "TEXT", True)  # noqa: E731

PROVENANCE_COLUMNS = (
    T("record_origin"),
    T("fact_state"),
    T("epistemic_state"),
    N("source_id"),
)


def dataset(
    filename: str,
    columns: tuple[Column, ...],
    *primary_key: str,
    foreign_keys: tuple[tuple[tuple[str, ...], str, tuple[str, ...]], ...] = (),
    checks: tuple[str, ...] = (),
) -> Dataset:
    return Dataset(filename, columns, primary_key, foreign_keys, checks)


DATASETS = (
    dataset(
        "ownership_history.csv",
        (
            T("owner_id"),
            T("owner_display_name"),
            T("owner_display_name_state"),
            N("owner_legal_name"),
            T("owner_legal_name_state"),
            T("start_date"),
            N("end_date"),
            T("role"),
            *PROVENANCE_COLUMNS,
        ),
        "owner_id",
        checks=(
            "owner_display_name_state IN ('LOCKED','PROVISIONAL','SCENARIO')",
            "owner_legal_name_state IN ('LOCKED','PROVISIONAL','OPEN','SCENARIO')",
            "(owner_legal_name_state = 'OPEN' AND owner_legal_name IS NULL) "
            "OR (owner_legal_name_state <> 'OPEN' AND owner_legal_name IS NOT NULL)",
        ),
    ),
    dataset(
        "drill_collars.csv",
        (
            T("hole_id"),
            I("year_drilled"),
            R("easting_m"),
            R("northing_m"),
            R("elevation_m"),
            T("coordinate_crs"),
            I("epsg_code"),
            T("utm_zone"),
            T("horizontal_datum"),
            R("total_depth_ft"),
            R("azimuth_deg"),
            R("dip_deg"),
            T("geologic_domain"),
            *PROVENANCE_COLUMNS,
        ),
        "hole_id",
        checks=(
            "year_drilled BETWEEN 1900 AND 2100",
            "easting_m BETWEEN 100000 AND 900000",
            "northing_m BETWEEN 0 AND 10000000",
            "coordinate_crs = 'NAD83 / UTM zone 13N'",
            "epsg_code = 26913",
            "utm_zone = '13N'",
            "horizontal_datum = 'NAD83'",
            "total_depth_ft > 0",
        ),
    ),
    dataset(
        "downhole_surveys.csv",
        (
            T("hole_id"),
            R("depth_ft"),
            R("azimuth_deg"),
            R("dip_deg"),
            T("method"),
            *PROVENANCE_COLUMNS,
        ),
        "hole_id",
        "depth_ft",
        foreign_keys=((("hole_id",), "drill_collars", ("hole_id",)),),
        checks=("depth_ft >= 0",),
    ),
    dataset(
        "assays.csv",
        (
            T("sample_id"),
            T("hole_id"),
            R("from_ft"),
            R("to_ft"),
            R("interval_ft"),
            R("u3o8_pct"),
            T("sample_type"),
            T("method"),
            T("qa_qc_status"),
            *PROVENANCE_COLUMNS,
        ),
        "sample_id",
        foreign_keys=((("hole_id",), "drill_collars", ("hole_id",)),),
        checks=("from_ft >= 0", "to_ft > from_ft", "interval_ft > 0", "u3o8_pct >= 0"),
    ),
    dataset(
        "resource_basis.csv",
        (
            T("basis_id"),
            T("classification"),
            I("tons"),
            R("grade_u3o8_pct"),
            I("contained_lb"),
            R("modeled_recovery_pct", True),
            I("recoverable_lb", True),
            I("included_in_base_value"),
            *PROVENANCE_COLUMNS,
        ),
        "basis_id",
        checks=(
            "tons > 0",
            "grade_u3o8_pct > 0",
            "contained_lb > 0",
            "modeled_recovery_pct IS NULL OR modeled_recovery_pct BETWEEN 0 AND 100",
            "included_in_base_value IN (0,1)",
        ),
    ),
    dataset(
        "monthly_production_2026.csv",
        (
            T("month"),
            T("period_role"),
            I("ore_tons"),
            R("head_grade_u3o8_pct"),
            R("recovery_pct"),
            I("contained_u3o8_lb"),
            I("u3o8_produced_lb"),
            I("u3o8_sold_lb"),
            R("modeled_realized_price_usd_lb"),
            I("revenue_usd"),
            *PROVENANCE_COLUMNS,
        ),
        "month",
        checks=(
            "ore_tons >= 0",
            "head_grade_u3o8_pct >= 0",
            "recovery_pct BETWEEN 0 AND 100",
            "contained_u3o8_lb >= 0",
            "u3o8_produced_lb >= 0",
            "u3o8_sold_lb >= 0",
            "revenue_usd >= 0",
        ),
    ),
    dataset(
        "inventory_rollforward_2026.csv",
        (
            T("month"),
            I("opening_finished_u3o8_lb"),
            I("production_u3o8_lb"),
            I("sales_u3o8_lb"),
            I("ending_finished_u3o8_lb"),
            *PROVENANCE_COLUMNS,
        ),
        "month",
        foreign_keys=((("month",), "monthly_production_2026", ("month",)),),
        checks=(
            "opening_finished_u3o8_lb >= 0",
            "production_u3o8_lb >= 0",
            "sales_u3o8_lb >= 0",
            "ending_finished_u3o8_lb >= 0",
            "ending_finished_u3o8_lb = opening_finished_u3o8_lb "
            "+ production_u3o8_lb - sales_u3o8_lb",
        ),
    ),
    dataset(
        "employee_census_2026.csv",
        (
            T("employee_id"),
            T("organization"),
            T("function"),
            T("title"),
            T("home_location"),
            T("status"),
            *PROVENANCE_COLUMNS,
        ),
        "employee_id",
    ),
    dataset(
        "permit_register.csv",
        (
            T("permit_id"),
            T("permit"),
            T("number"),
            T("authority"),
            T("legal_basis"),
            T("status"),
            *PROVENANCE_COLUMNS,
        ),
        "permit_id",
    ),
    dataset(
        "diligence_findings.csv",
        (
            T("finding_id"),
            T("domain"),
            T("severity"),
            T("finding"),
            T("disposition"),
            T("status"),
            *PROVENANCE_COLUMNS,
        ),
        "finding_id",
        checks=("severity IN ('LOW','MEDIUM','HIGH')",),
    ),
    dataset(
        "quality_of_earnings.csv",
        (
            T("line"),
            I("amount_usd"),
            T("line_role"),
            *PROVENANCE_COLUMNS,
        ),
        "line",
    ),
    dataset(
        "transaction_timeline.csv",
        (
            T("event_id"),
            T("period"),
            T("date_precision"),
            T("event"),
            T("category"),
            *PROVENANCE_COLUMNS,
        ),
        "event_id",
        checks=("date_precision IN ('DAY','MONTH','QUARTER','YEAR','PERIOD')",),
    ),
    dataset(
        "uranium_contracts.csv",
        (
            T("contract_id"),
            T("buyer"),
            T("origin"),
            I("committed_lb"),
            T("pricing_type"),
            R("modeled_price_usd_lb"),
            T("delivery_point"),
            T("assignability"),
            *PROVENANCE_COLUMNS,
        ),
        "contract_id",
        checks=("committed_lb > 0", "modeled_price_usd_lb >= 0"),
    ),
    dataset(
        "external_source_register.csv",
        (
            T("source_id"),
            T("organization"),
            T("title"),
            T("url"),
            T("use"),
            N("publication_date"),
            T("accessed_date"),
            T("covered_period"),
            T("geography"),
            T("unit"),
            T("method"),
            T("transformation"),
            T("limitations"),
            T("record_origin"),
            T("fact_state"),
            T("epistemic_state"),
        ),
        "source_id",
    ),
    dataset(
        "purchase_price_allocation.csv",
        (
            T("line_id"),
            T("line"),
            I("amount_usd"),
            T("classification"),
            I("presentation_order"),
            *PROVENANCE_COLUMNS,
        ),
        "line_id",
    ),
    dataset(
        "financial_statements_2026.csv",
        (
            T("statement"),
            T("line_id"),
            T("line"),
            I("amount_usd"),
            I("presentation_order"),
            I("is_subtotal"),
            *PROVENANCE_COLUMNS,
        ),
        "statement",
        "line_id",
        checks=("is_subtotal IN (0,1)",),
    ),
    dataset(
        "environmental_monitoring.csv",
        (
            T("period"),
            T("station"),
            R("uranium_mg_l"),
            R("sulfate_mg_l"),
            R("ph"),
            *PROVENANCE_COLUMNS,
        ),
        "period",
        "station",
        checks=("uranium_mg_l >= 0", "sulfate_mg_l >= 0", "ph BETWEEN 0 AND 14"),
    ),
    dataset(
        "maintenance_backlog.csv",
        (
            T("backlog_id"),
            T("system_id"),
            T("description"),
            I("estimated_cost_usd"),
            T("priority"),
            I("seller_schedule_usd"),
            T("status"),
            *PROVENANCE_COLUMNS,
        ),
        "backlog_id",
        checks=("estimated_cost_usd >= 0", "seller_schedule_usd >= 0"),
    ),
    dataset(
        "virtual_data_room_index.csv",
        (
            T("vdr_id"),
            T("category"),
            T("document"),
            T("effective_date"),
            T("review_status"),
            T("document_sha256"),
            *PROVENANCE_COLUMNS,
        ),
        "vdr_id",
    ),
    dataset(
        "transport_capacity_events.csv",
        (
            T("event_id"),
            T("period"),
            T("date_precision"),
            T("event_type"),
            T("description"),
            T("capacity_effect"),
            I("annual_revenue_impact_usd"),
            *PROVENANCE_COLUMNS,
        ),
        "event_id",
        checks=("annual_revenue_impact_usd = 0",),
    ),
    dataset(
        "shipment_schedule_exceptions.csv",
        (
            T("exception_id"),
            T("capacity_event_id"),
            T("period"),
            T("date_precision"),
            T("original_window"),
            T("revised_window"),
            T("outcome"),
            I("annual_revenue_impact_usd"),
            *PROVENANCE_COLUMNS,
        ),
        "exception_id",
        foreign_keys=((("capacity_event_id",), "transport_capacity_events", ("event_id",)),),
        checks=("annual_revenue_impact_usd = 0",),
    ),
    dataset(
        "carrier_market_scan.csv",
        (
            T("candidate_id"),
            T("candidate_type"),
            I("incumbent_2025"),
            I("qualified_2025"),
            T("finding"),
            T("relationship_to_aru"),
            *PROVENANCE_COLUMNS,
        ),
        "candidate_id",
        checks=("incumbent_2025 IN (0,1)", "qualified_2025 IN (0,1)"),
    ),
    dataset(
        "rail_access_candidates.csv",
        (
            T("candidate_id"),
            I("discovery_sequence"),
            T("asset_name"),
            T("proximity_state"),
            I("direct_mine_connection"),
            I("suitable_transload"),
            I("uranium_capability"),
            T("disposition"),
            *PROVENANCE_COLUMNS,
        ),
        "candidate_id",
        checks=(
            "discovery_sequence > 0",
            "direct_mine_connection IN (0,1)",
            "suitable_transload IN (0,1)",
            "uranium_capability IN (0,1)",
        ),
    ),
    dataset(
        "aru_red_wash_fit_gap.csv",
        (
            T("gap_id"),
            T("domain"),
            T("current_state"),
            T("required_state"),
            T("status"),
            I("blocks_custody"),
            *PROVENANCE_COLUMNS,
        ),
        "gap_id",
        checks=("blocks_custody IN (0,1)",),
    ),
    dataset(
        "aru_red_wash_integration_gates.csv",
        (
            T("gate_id"),
            T("phase"),
            I("earliest_month"),
            I("latest_month"),
            T("gate"),
            T("decision_owner"),
            T("status"),
            I("blocks_service"),
            *PROVENANCE_COLUMNS,
        ),
        "gate_id",
        checks=(
            "earliest_month >= 0",
            "latest_month >= earliest_month",
            "blocks_service IN (0,1)",
        ),
    ),
    dataset(
        "aru_red_wash_preliminary_capex.csv",
        (
            T("component_id"),
            T("component"),
            I("amount_usd", True),
            T("amount_state"),
            I("included_in_envelope"),
            T("notes"),
            *PROVENANCE_COLUMNS,
        ),
        "component_id",
        checks=(
            "amount_usd IS NULL OR amount_usd >= 0",
            "included_in_envelope IN (0,1)",
        ),
    ),
    dataset(
        "custody_authority_matrix.csv",
        (
            T("matrix_id"),
            T("activity"),
            T("current_authority"),
            T("aru_bst_authority"),
            T("required_evidence"),
            T("status"),
            *PROVENANCE_COLUMNS,
        ),
        "matrix_id",
    ),
)

DATASET_BY_FILENAME = {item.filename: item for item in DATASETS}
DATASET_BY_TABLE = {item.table: item for item in DATASETS}
GENERATED_FILENAMES = frozenset(DATASET_BY_FILENAME)
GENERATED_ALLOWED = GENERATED_FILENAMES | {GENERATED_MARKER}
DIST_FILENAMES = frozenset({DATABASE_FILENAME, MANIFEST_FILENAME})
DIST_ALLOWED = DIST_FILENAMES | {DIST_MARKER}

VISUAL_HASHES = {
    "assets/brand/logos/pale_sun__canonical.png": (
        "eedcabfca73460e8ff5ad72864c9f669ba2375097b05daa2912f30c9ff35c025"
    ),
    "assets/brand/logos/red_wash__canonical.png": (
        "7c26b8afd7954045d9dd4b5c691ba820cdce2e3ccb8e41ac6873b103f0c59720"
    ),
    "assets/brand/maps/red_wash__underground_plan.png": (
        "0658de3b7c63ecc9757b545f29895eab51801b2148cb3862935620b6049a7dda"
    ),
    "assets/brand/maps/red_wash__site_overview.png": (
        "8dbb0053c4a563d57d5a24be4f4687dc11e2e00e2b1e62c279d9be945f68d77a"
    ),
}
