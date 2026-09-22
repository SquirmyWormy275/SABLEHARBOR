"""Existing debt and asset source inventory; no rights or accounting postings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POPULATIONS = (
    "facilities",
    "track_segments",
    "structures",
    "locomotives",
    "railcars",
    "road_equipment",
    "handling_equipment",
)
SOURCE_PATHS = (
    "industrial/source/finance.json",
    "industrial/source/operations.json",
    "industrial/planning/source/forecast.json",
    "enterprise/operations/source/debt_host_2026_08.json",
    "enterprise/closeout/source/capital_register.json",
    "docs/canon/COMPANY_CLOSEOUT_DIRECTIONS_2026-09-15.md",
    "docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md",
    "docs/governance/board-records/2021-06-18_harrison-vale-growth-financing-minutes.md",
    "docs/governance/board-records/2022-10-28_wolf-ridge-industrial-financing-minutes.md",
    "docs/legal/gap-instruments/source/financing-documents.md",
    "docs/legal/gap-instruments/source/debt-liens.md",
)


def build(finance=None, operations=None, forecast=None):
    def read(path):
        return json.loads((ROOT / path).read_text())

    finance = finance if finance is not None else read(SOURCE_PATHS[0])
    operations = operations if operations is not None else read(SOURCE_PATHS[1])
    forecast = forecast if forecast is not None else read(SOURCE_PATHS[2])
    evidence = read(SOURCE_PATHS[3])["debt"]
    term = finance["opening_2025"]["term_debt"] - finance["closing_2025_drivers"]["term_principal"]
    revolver = finance["opening_2025"]["revolver"]
    total = finance["transaction"]["existing_term_revolver_refinance"]
    if (
        min(term, revolver) < 0
        or term + revolver != total
        or total != int(evidence["old_debt_payoff_usd"])
    ):
        raise ValueError("Existing payoff principal components do not reconcile")
    rows = []
    seen = set()
    facilities = {r["id"]: r for r in operations["facilities"]}
    for population in POPULATIONS:
        for asset in operations[population]:
            identity = asset["id"]
            if identity in seen:
                raise ValueError("Duplicate asset source identity")
            seen.add(identity)
            explicit = asset.get("owner") == "American Resource Utility, Inc."
            handling = (
                population == "handling_equipment"
                and asset.get("ownership") == "owned"
                and identity.startswith("ARU-")
                and facilities.get(asset.get("facility_id"), {}).get("owner")
                == "American Resource Utility, Inc."
            )
            disposition = (
                "ARU_OWNER_EXPLICIT_SOURCE"
                if explicit
                else "ARU_HANDLING_OWNER_INFERRED_REQUIRE_TITLE"
                if handling
                else "EXCLUDED_FROM_ARU_ONLY_CANDIDATE_SCOPE"
            )
            rows.append(
                {
                    "asset_id": identity,
                    "population": population,
                    "source_pointer": f"industrial/source/operations.json#{population}/{identity}",
                    "source_owner": asset.get("owner"),
                    "source_ownership": asset.get("ownership"),
                    "facility_id": asset.get("facility_id"),
                    "disposition": disposition,
                    "title_evidence": "SOURCE_DESCRIPTION_ONLY_NOT_TITLE_DOCUMENT",
                    "encumbrance_status": "NOT_ESTABLISHED",
                    "pledged": False,
                    "collateral_value_usd": None,
                    "source_period": "2025_BASELINE_WITH_SOURCE_DATED_UPDATES",
                    "source_in_service_date": asset.get("in_service_date"),
                    "source_status": asset.get("status", asset.get("condition")),
                }
            )
    if len(rows) != 149:
        raise ValueError("Declared existing 149-record asset source population incomplete")
    inventory = []
    for path in SOURCE_PATHS[4:]:
        inventory.append(
            {
                "path": path,
                "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                "review_scope": "Capital/governance and financing terms in this exact source population",
                "side_letter_document_identified": False,
                "conclusion": "NO_SIDE_LETTER_DOCUMENT_LOCATED_IN_SELECTED_POPULATION_NOT_HISTORICAL_ABSENCE",
            }
        )
    return {
        "record_id": "SH-FIN-ADMIN-SOURCE-2026-09-22",
        "record_origin": "NEWLY_AUTHORED_ADMINISTRATIVE_COMPLETION_FROM_ACCEPTED_SOURCES",
        "acceptance_status": "PENDING_REPOSITORY_ACCEPTANCE",
        "source_hashes": {
            p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCE_PATHS
        },
        "payoff_components": [
            {
                "component_id": f"SH-DEBT-ARU-LEGACY-{kind}-PAYOFF-20260107",
                "principal_usd": value,
                "borrower": "ARU",
                "effective_on": evidence["old_debt_payoff_on"],
                "parent_instruction_ref": evidence["old_debt_instruction_ref"],
                "parent_internal_settlement_ref": evidence["old_debt_settlement_ref"],
                "settlement_state": "ALLOCATION_OF_EXISTING_MODELED_INTERNAL_SETTLEMENT",
                "independent_creditor_confirmation": "NOT_ESTABLISHED",
                "release_instrument": None,
            }
            for kind, value in [("TERM", term), ("REVOLVER", revolver)]
        ],
        "payoff_total_principal_usd": total,
        "retained_leases_excluded_usd": finance["transaction"]["retained_leases"],
        "maturity": {
            "date": forecast["debt"]["legacy_term_maturity"],
            "state": "ACCEPTED_CONDITIONAL_MODEL_ASSUMPTION_NOT_EXECUTED_TERM",
            "basis": forecast["debt"]["boundary"],
        },
        "secretary_source_inventory": inventory,
        "asset_screen": rows,
        "additional_journal_count": 0,
        "additional_cash_usd": 0,
        "limits": "No new instrument, grant, guarantee, lender receipt, release, title confirmation, asset activation or value assertion. No decision-dependent term adopted.",
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
