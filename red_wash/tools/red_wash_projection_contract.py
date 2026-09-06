"""Validate public Red Wash projections against their authoritative source records.

The source JSON files are the machine authority.  The structured records and the
selected canon tables are maintained for people and other systems, so this module
defines the deliberately small, exact projection contract between those surfaces.
It does not validate the generated finance package; that remains the independent
validator's responsibility.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TRANSACTION_PROJECTION_PATH = (
    REPOSITORY_ROOT / "docs/structured/red_wash_transaction_operating_record.json"
)
BRIDGE_PROJECTION_PATH = REPOSITORY_ROOT / "docs/structured/aru_bst_red_wash_bridge.json"
TRANSACTION_CANON_PATH = (
    REPOSITORY_ROOT / "docs/canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md"
)
DECISION_ADDENDUM_PATH = (
    REPOSITORY_ROOT / "docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-05_RED_WASH_R2.md"
)

TRANSACTION_DECISION_IDS = tuple(f"RW-{number:03d}" for number in range(1, 17))
BRIDGE_DECISION_IDS = tuple(f"RW-{number:03d}" for number in range(17, 26))


def _subset(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())


def _normalized_words(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _event_projection(source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "event_id": source["event_id"],
        "period": source["period"],
        "date_precision": str(source["date_precision"]).upper(),
        "fact_state": source["fact_state"],
        "epistemic_state": source["epistemic_state"],
        "annual_financial_impact_usd": source["annual_revenue_impact_usd"],
        "source_ids": str(source["source_id"]).split(";"),
    }


def _derive_dd_and_a(core: Mapping[str, Any]) -> int:
    transaction = core["transaction"]
    resource = core["resource_basis"]
    mine = core["mine_2026"]
    basis = Decimal(transaction["operating_assets_usd"]) + Decimal(
        transaction["capitalized_rehabilitation_usd"]
    )
    amount = basis * Decimal(mine["produced_u3o8_lb"]) / Decimal(resource["recoverable_lb"])
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _decision_rows(markdown: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in markdown.splitlines():
        match = re.match(r"^\| (RW-\d{3}) \|", line)
        if match:
            decision_id = match.group(1)
            if decision_id in rows:
                return {}
            rows[decision_id] = line
    return rows


def _all_fragments(value: str, fragments: Sequence[str]) -> bool:
    return all(fragment in value for fragment in fragments)


def projection_checks(
    core: Mapping[str, Any],
    bridge: Mapping[str, Any],
    transaction_projection: Mapping[str, Any],
    bridge_projection: Mapping[str, Any],
    transaction_canon: str,
    decision_addendum: str,
) -> list[tuple[bool, str]]:
    """Return exact source-to-surface checks without blessing generated outputs."""

    transaction = core["transaction"]
    workforce = core["workforce_2026"]
    mine = core["mine_2026"]
    finance = core["finance_2026"]
    resource = core["resource_basis"]
    closure = core["closure"]
    assumptions = core["inventory_cost_assumptions_2026"]

    expected_transaction_contract = {
        "authoritative_operating_source": "red_wash/source/core_operating_data.json",
        "authoritative_bridge_source": "red_wash/source/aru_bst_bridge.json",
        "decision_addendum": ("docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-05_RED_WASH_R2.md"),
        "decision_record_id": "SH-PS-RW-DR-001",
        "transaction_decision_ids": list(TRANSACTION_DECISION_IDS),
        "bridge_decision_ids": list(BRIDGE_DECISION_IDS),
    }
    expected_bridge_contract = {
        "authoritative_source": "red_wash/source/aru_bst_bridge.json",
        "decision_addendum": ("docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-05_RED_WASH_R2.md"),
        "decision_record_id": "SH-PS-RW-DR-001",
        "decision_ids": list(BRIDGE_DECISION_IDS),
    }

    transaction_expected = {
        "close_date": transaction["close_date"],
        "cash_consideration_usd": transaction["cash_consideration_usd"],
        "operating_asset_fair_value_usd": transaction["operating_assets_usd"],
        "acquired_current_assets_usd": transaction["current_assets_usd"],
        "aro_assumed_usd": transaction["aro_assumed_usd"],
        "other_liabilities_assumed_usd": transaction["other_liabilities_usd"],
        "net_identifiable_assets_usd": (
            transaction["operating_assets_usd"]
            + transaction["current_assets_usd"]
            - transaction["aro_assumed_usd"]
            - transaction["other_liabilities_usd"]
        ),
        "goodwill_usd": transaction["goodwill_usd"],
        "transaction_debt_usd": transaction["transaction_debt_usd"],
        "environmental_title_escrow_usd": transaction["environmental_title_escrow_usd"],
        "holdback_usd": transaction["holdback_usd"],
        "h2_2025_stabilization_usd": transaction["h2_2025_stabilization_usd"],
        "capitalized_rehabilitation_usd": transaction["capitalized_rehabilitation_usd"],
        "repair_stabilization_expense_usd": transaction["repair_stabilization_expense_usd"],
    }
    workforce_expected = {
        "pale_sun_red_wash_total": workforce["total_fte"],
        "pale_sun_business_layer": workforce["pale_sun_business_layer"],
        "red_wash_site": workforce["red_wash_site"],
    }
    mine_expected = {
        "ore_tons": mine["ore_tons"],
        "head_grade_u3o8_pct": mine["head_grade_u3o8_pct"],
        "recovery_pct": mine["recovery_pct"],
        "contained_lb": mine["contained_u3o8_lb"],
        "produced_lb": mine["produced_u3o8_lb"],
        "opening_finished_inventory_lb": mine["opening_finished_inventory_lb"],
        "sold_lb": mine["sold_u3o8_lb"],
        "ending_finished_inventory_lb": mine["ending_finished_inventory_lb"],
        "nameplate_tpd": mine["nameplate_tpd"],
        "planned_depth_ft": mine["planned_depth_ft"],
        "method": mine["method"],
    }
    finance_expected = {
        "modeled_revenue_usd": finance["revenue_usd"],
        "modeled_weighted_realized_price_per_lb": finance["weighted_realized_price_usd_lb"],
        "cash_production_cost_incurred_usd": finance["cash_production_cost_incurred_usd"],
        "sustaining_capex_usd": finance["sustaining_capex_usd"],
        "rehabilitation_capex_usd": finance["rehabilitation_capex_usd"],
        "dd_and_a_incurred_usd": _derive_dd_and_a(core),
        "production_mineral_taxes_usd": finance["production_mineral_taxes_usd"],
        "royalties_usd": finance["royalties_usd"],
        "freight_assay_handling_usd": finance["freight_assay_handling_usd"],
        "pale_sun_site_g_and_a_usd": finance["pale_sun_site_g_and_a_usd"],
        "aro_accretion_usd": finance["aro_accretion_usd"],
        "current_cost_closure_basis_usd": closure["current_cost_usd"],
        "opening_aro_usd": closure["opening_aro_usd"],
    }
    resource_expected = {
        "indicated_including_reserve_tons": resource["indicated_tons"],
        "indicated_grade_pct": resource["grade_u3o8_pct"],
        "contained_lb": resource["contained_lb"],
        "modeled_recovery_pct": resource["modeled_recovery_pct"],
        "recoverable_lb": resource["recoverable_lb"],
        "inferred_tons": resource["inferred_tons"],
        "inferred_grade_pct": resource["inferred_grade_u3o8_pct"],
        "inferred_in_base_value": resource["base_value_includes_inferred"],
    }
    seller_expected = {
        "display_name": transaction["seller_display_name"],
        "display_name_state": transaction["seller_display_name_state"],
        "legal_name": transaction["seller_legal_name"],
        "legal_name_state": transaction["seller_legal_name_state"],
        "jurisdiction": transaction["seller_jurisdiction"],
        "jurisdiction_state": transaction["seller_jurisdiction_state"],
    }

    source_events = [_event_projection(row) for row in bridge["transport_capacity_events"]]
    projected_events = [
        {key: row.get(key) for key in expected}
        for row, expected in zip(bridge_projection.get("events", []), source_events, strict=False)
    ]
    projected_gap_by_id: dict[str, Mapping[str, Any]] = {
        row.get("gap_id"): row for row in bridge_projection.get("current_fit_gaps", [])
    }
    source_gap_by_id = {row["gap_id"]: row for row in bridge["fit_gaps"]}
    expected_gap_text_by_domain = {row["domain"]: row["current_state"] for row in bridge["fit_gaps"]}
    gap_projection_agrees = set(projected_gap_by_id) == set(source_gap_by_id) and all(
        projected_gap_by_id[gap_id].get("state") == source_gap["status"]
        and projected_gap_by_id[gap_id].get("blocks_direct_custody") == source_gap["blocks_custody"]
        and _normalized_words(projected_gap_by_id[gap_id].get("gap", ""))
        == _normalized_words(expected_gap_text_by_domain[source_gap["domain"]])
        for gap_id, source_gap in source_gap_by_id.items()
    )
    quantified_capex = [row for row in bridge["preliminary_capex"] if row["amount_usd"]]
    open_capex = [row for row in bridge["preliminary_capex"] if row["amount_usd"] is None]
    source_physical_custody = next(
        row
        for row in bridge["custody_authority_matrix"]
        if row["activity"] == "Physical custody and transport"
    )
    source_shipper_authority = next(
        row["current_authority"]
        for row in bridge["custody_authority_matrix"]
        if row["activity"] == "Packaging, classification, release, and shipping papers"
    )
    source_gates = bridge["integration_gates"]
    projected_gates = bridge_projection.get("integration_sequence", [])
    integration_sequence_agrees = len(source_gates) == len(projected_gates) and all(
        projected.get("source_gate_id") == source["gate_id"]
        and projected.get("earliest_month") == source["earliest_month"]
        and projected.get("latest_month") == source["latest_month"]
        and projected.get("state") == source["status"]
        for index, (projected, source) in enumerate(zip(projected_gates, source_gates, strict=True))
    )

    decision_rows = _decision_rows(decision_addendum)
    expected_all_decision_ids = TRANSACTION_DECISION_IDS + BRIDGE_DECISION_IDS
    decision_fragments = {
        "RW-001": ("18 July 2025",),
        "RW-002": (transaction["seller_display_name"], "exact legal name", "LOCKED"),
        "RW-003": ("$28.0M", "$3.0M", "$0.5M", "no transaction debt", "no goodwill"),
        "RW-004": ("$42.0M", "$4.5M", "$16.0M ARO", "$2.5M", "$28.0M"),
        "RW-005": ("$11.0M", "$8.0M", "$3.0M"),
        "RW-006": ("140 FTE", "12 Pale Sun", "128 Red Wash"),
        "RW-007": ("175,000", "0.170%", "92%", "547,400 lb"),
        "RW-008": ("500,000 lb", "125,000 lb", "172,400 lb", "$72.95/lb", "$36.475M"),
        "RW-009": ("$27.950M", "$3.500M", "$4.000M", "$5.000M"),
        "RW-010": ("$2.125M", "$729,500", "$600,000"),
        "RW-011": ("2.5M tons", "8.5M contained lb", "7.82M recoverable lb"),
        "RW-012": ("$25.0M", "$16.0M"),
        "RW-017": ("None", "not a Northstar arrangement", "not", "historical"),
        "RW-018": ("Qualified external carriers", "all 2025 movements"),
        "RW-019": ("soft, costly, uneven freight", "sales and revenue do not change"),
        "RW-020": ("Replacement-carrier search", "Whose line is this?", "not a banker pitch"),
        "RW-021": ("no direct mine connection", "secure transload", "uranium capability"),
        "RW-022": ("$15.0M", "$8.5M", "$3.25M", "$5.25M", "unapproved", "not ARU purchase price"),
        "RW-023": ("0–3", "3–6", "month 6", "12–18"),
        "RW-024": ("No automatic", "external carrier remains authoritative", "gate"),
        "RW-025": ("SELECTED_SUCCESSOR", "Acquisition date and terms", "final custody decision"),
    }
    decision_facts_agree = all(
        _all_fragments(decision_rows.get(decision_id, ""), fragments)
        for decision_id, fragments in decision_fragments.items()
    )

    transaction_table_lines = (
        "| Operating assets | $42.000M |",
        "| Acquired current assets | $4.500M |",
        "| Accounting ARO assumed | $(16.000)M |",
        "| Other liabilities assumed | $(2.500)M |",
        "| Net identifiable assets / cash consideration | $28.000M |",
        "| Environmental/title escrow | $3.000M |",
        "| Holdback | $0.500M |",
        "| Transaction debt | $0 |",
        "| Goodwill | $0 |",
        "| Total Pale Sun/Red Wash establishment | 140 FTE | SCENARIO_INPUT |",
        "| Pale Sun business layer | 12 FTE | SCENARIO_INPUT |",
        "| Red Wash site | 128 FTE | SCENARIO_INPUT |",
        "| Ore mined | 175,000 short tons | SCENARIO_INPUT |",
        "| Head grade | approximately 0.170% U3O8 | SUPPORTED_ESTIMATE |",
        "| Recovery | approximately 92.0% | SUPPORTED_ESTIMATE |",
        "| U3O8 produced | 547,400 lb | DERIVED |",
        "| Opening finished inventory | 125,000 lb | SCENARIO_INPUT |",
        "| U3O8 sold | 500,000 lb | SCENARIO_INPUT |",
        "| Ending finished inventory | 172,400 lb | DERIVED |",
        "| Modeled weighted realized price | $72.95/lb | DERIVED |",
        "| Modeled revenue | $36.475M | DERIVED |",
        "| Production cost incurred | $27.950M | SCENARIO_INPUT |",
        "| DD&A incurred | approximately $3.500M | DERIVED |",
        "| Sustaining capital | $4.000M | SCENARIO_INPUT |",
        "| Rehabilitation capital | $5.000M | SCENARIO_INPUT |",
        "| Production/mineral taxes | approximately $2.125M | SUPPORTED_ESTIMATE |",
        "| Royalties | approximately $0.7295M | SUPPORTED_ESTIMATE |",
        "| Freight, assay, and handling | approximately $0.600M | SUPPORTED_ESTIMATE |",
    )
    bridge_canon_fragments = (
        "no\n  pre-existing commercial relationship with Red Wash",
        "qualified external carriers serve every 2025 Red Wash movement",
        "no lost 2025 annual\n  sales and no change to 2025 annual revenue",
        "question “Whose line is this?” surfaces ARU/BS&T through operating analysis",
        (
            "no direct mine connection, suitable secure transload, or\n  demonstrated "
            "uranium-specific ARU/BS&T capability"
        ),
        "$15.0M is an unbooked ceiling; $8.5M Phase 1 is approved",
        "no ARU/BS&T uranium custody or service begins automatically",
        (
            "full ARU/BS&T case is implemented in the industrial successor; direct uranium custody remains OPEN"
        ),
    )

    return [
        (
            _subset(
                transaction_projection,
                {
                    "record_id": core["record_id"],
                    "version": core["version"],
                    "canon_effective_through": core["canon_effective_through"],
                    "synthetic_calibration_through": core["synthetic_calibration_through"],
                    "classification": core["classification"],
                },
            ),
            "structured transaction metadata projects authoritative source",
        ),
        (
            transaction_projection.get("projection_contract") == expected_transaction_contract,
            "structured transaction projection binds exact RW-001 through RW-025 decision sets",
        ),
        (
            transaction_projection.get("actual_layer_present") is False,
            "structured transaction projection preserves no-ACTUAL boundary",
        ),
        (
            transaction_projection.get("seller") == seller_expected,
            "structured seller identity and OPEN legal fields project source exactly",
        ),
        (
            _subset(transaction_projection.get("transaction", {}), transaction_expected),
            "structured transaction economics project source exactly",
        ),
        (
            _subset(transaction_projection.get("workforce_2026", {}), workforce_expected),
            "structured workforce projection agrees with source",
        ),
        (
            _subset(transaction_projection.get("mine_2026", {}), mine_expected),
            "structured mine and inventory projection agrees with source",
        ),
        (
            _subset(transaction_projection.get("finance_2026", {}), finance_expected),
            "structured finance and closure projection agrees with source",
        ),
        (
            transaction_projection.get("dd_and_a_model_2026") == core["dd_and_a_model_2026"],
            "structured DD&A method and boundary project source exactly",
        ),
        (
            _subset(transaction_projection.get("resource_basis", {}), resource_expected),
            "structured resource projection agrees with source",
        ),
        (
            _subset(transaction_projection.get("inventory_cost_assumptions_2026", {}), assumptions),
            "structured inventory assumptions project source exactly",
        ),
        (
            _subset(
                transaction_projection.get("aru_bst_bridge", {}),
                {
                    "record_id": bridge["record_id"],
                    "pre_existing_relationship": bridge["boundaries"]["pre_existing_relationship"],
                    "annual_2025_revenue_impact_usd": bridge["boundaries"][
                        "annual_2025_revenue_impact_usd"
                    ],
                    "preliminary_interface_envelope_usd": bridge["boundaries"][
                        "preliminary_interface_envelope_usd"
                    ],
                    "interface_envelope_booked": bridge["boundaries"]["interface_envelope_booked"],
                    "direct_uranium_custody_authorized": bridge["boundaries"][
                        "direct_uranium_custody_authorized"
                    ],
                },
            ),
            "structured transaction bridge summary projects source boundaries",
        ),
        (
            _subset(
                bridge_projection,
                {
                    "record_id": bridge["record_id"],
                    "version": bridge["version"],
                    "decision_date": bridge["decision_date"],
                    "canon_effective_through": bridge["canon_effective_through"],
                    "classification": bridge["classification"],
                    "source_commit_state": bridge["source_commit_state"],
                },
            ),
            "structured bridge metadata projects authoritative source",
        ),
        (
            bridge_projection.get("projection_contract") == expected_bridge_contract,
            "structured bridge binds exact addendum decisions RW-017 through RW-025",
        ),
        (
            bridge_projection.get("names") == bridge["names"],
            "structured ARU and BS&T names project source exactly",
        ),
        (
            bridge_projection.get("boundaries") == bridge["boundaries"],
            "structured bridge boundaries project source exactly",
        ),
        (
            bridge_projection.get("open_aru_fields") == bridge["open_aru_fields"]
            and len(bridge_projection.get("open_aru_fields", [])) == 3,
            "structured bridge preserves the exact ordered set of three gated ARU fields",
        ),
        (
            projected_events == source_events and len(projected_events) == len(source_events),
            (
                "structured bridge event identities, periods, states, sources, and impacts "
                "project source"
            ),
        ),
        (
            gap_projection_agrees,
            "structured bridge projects all source fit gaps as OPEN and custody-blocking",
        ),
        (
            integration_sequence_agrees,
            "structured bridge projects every source integration gate and 0-18 month horizon",
        ),
        (
            len(quantified_capex) == 4
            and bridge_projection.get("planning_capex", {}).get("amount_usd") == 15_000_000
            and bridge_projection.get("planning_capex", {}).get("booked") is False
            and bridge_projection.get("planning_capex", {}).get("phase_1_approved_usd") == 8_500_000
            and bridge_projection.get("planning_capex", {}).get("red_wash_owned_usd") == 3_250_000
            and bridge_projection.get("planning_capex", {}).get("aru_owned_usd") == 5_250_000
            and bridge_projection.get("planning_capex", {}).get("unapproved_residual_usd") == 6_500_000
            and sum(row["amount_usd"] for row in quantified_capex[1:3]) == 8_500_000,
            "structured interface separates approved capital from unbooked ceiling and residual",
        ),
        (
            bridge_projection.get("custody", {}).get("current_authority")
            == source_physical_custody["current_authority"]
            and bridge_projection.get("custody", {}).get("shipper_authority")
            == source_shipper_authority
            and bridge_projection.get("custody", {}).get("aru_bst_authority")
            == "none unless separately proved and authorized"
            and bridge_projection.get("custody", {}).get("state") == "OPEN"
            and bridge_projection.get("custody", {}).get("automatic_transfer_prohibited") is True,
            "structured custody projection preserves external authority and all gates",
        ),
        (
            tuple(decision_rows) == expected_all_decision_ids,
            "Red Wash addendum contains one ordered row for each RW-001 through RW-025 decision",
        ),
        (
            decision_facts_agree,
            "Red Wash addendum decision rows preserve selected numeric and bridge facts",
        ),
        (
            all(transaction_canon.count(line) == 1 for line in transaction_table_lines),
            "Red Wash canon tables contain one exact projection of each selected case value",
        ),
        (
            all(fragment in transaction_canon for fragment in bridge_canon_fragments),
            "Red Wash canon narrative preserves every limited ARU/BS&T boundary",
        ),
        (
            _all_fragments(
                transaction_canon,
                (
                    "`MODEL_PROPOSED` method supported as a\n`SUPPORTED_ESTIMATE`",
                    (
                        "$42.0M of approved aggregate operating assets plus $8.0M of\n"
                        "approved capitalized rehabilitation produces a $50.0M composite "
                        "modeled basis"
                    ),
                    "547,400 lb produced divided by 7,820,000 recoverable lb produces a 7.0%",
                    "$50.0M multiplied by 7.0% produces $3.500M of 2026\nDD&A incurred",
                    (
                        "not an asset-class\npurchase-price allocation, an audited GAAP "
                        "useful-life "
                        "determination, or tax basis"
                    ),
                ),
            ),
            "Red Wash canon exposes the complete bounded DD&A derivation",
        ),
        (
            "Northstar Resources (Wyoming) LLC" not in transaction_canon
            and "Northstar Resources LLC" not in transaction_canon,
            "Red Wash canon does not invent a seller legal suffix or jurisdiction",
        ),
    ]
