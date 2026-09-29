"""Reproduce a conditional 2027 reference boundary without inventing due events.

Only accepted 2026 legal/service/site design facts are imported. The five CCF
procedures become scoped conditions, not operated company control populations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

SOURCE = Path("enterprise/operations/source/portal_2027_common_boundary_2026_09_29.json")
CONTROL_IDS = {
    "SH-IAM-006",
    "SH-BCM-002",
    "SH-BCM-003",
    "SH-IAM-005",
    "SH-REC-004",
}
SERVICE_IDS = {"SVC-identity", "SVC-backup", "SVC-compute"}
SITE_IDS = {"RUNTIME-RENO-COLO", "RUNTIME-BOISE-DR", "RUNTIME-NN-OWNED-DC"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def indexed(rows: list[dict], key: str) -> dict[str, dict]:
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate {key}")
    return result


def derive(source: dict, inputs: dict[str, object], source_sha256: str) -> dict:
    boundary = source["boundary"]
    calendar = source["calendar"]
    if not datetime.fromisoformat(
        source["authored_at"].replace("Z", "+00:00")
    ) < datetime.fromisoformat(calendar["start"].replace("Z", "+00:00")):
        raise ValueError("Prospective source authored after the selected period began")
    if (
        source["state"] != "PROVISIONAL_PROSPECTIVE_COMPANY_SOURCE"
        or source["fact_status"] != "2026_DESIGN_FACTS_WITH_UNVERIFIED_2027_ACTIVATION"
        or source["repository_available_at"] is not None
        or source["repository_acceptance_at"] is not None
        or source["accepted_source_commit"] != "17c1e02b531436f2e698efeddec63552b69e0475"
    ):
        raise ValueError("Provisional source or acceptance boundary changed")
    entity = indexed(inputs["industrial_entities"]["entities"], "entity_id")["SHI"]
    if (
        entity["legal_name"] != "Sable Harbor, LLC"
        or entity["legal_form"] != "LLC"
        or entity["jurisdiction"] != "Delaware"
        or boundary["legal_entity_id"] != "SHI"
    ):
        raise ValueError("SHI legal entity boundary differs")
    service_source = inputs["services"]
    columns = service_source["columns"]
    services = indexed(
        [dict(zip(columns, row, strict=True)) for row in service_source["services"]], "id"
    )
    if set(boundary["service_ids"]) != SERVICE_IDS or any(s not in services for s in SERVICE_IDS):
        raise ValueError("Selected service IDs differ")
    if (
        services["SVC-identity"]["accountable_owner"] != "TEAM-identity"
        or services["SVC-backup"]["accountable_owner"] != "TEAM-reliability"
        or services["SVC-compute"]["accountable_owner"] != "TEAM-platform"
        or service_source["default_decision_state"] != "OWNER_APPROVED_PENDING_ACCEPTANCE"
    ):
        raise ValueError("Service responsibility or source state differs")
    sites = indexed(inputs["runtime_sites"]["sites"], "id")
    if set(boundary["runtime_site_ids"]) != SITE_IDS or any(s not in sites for s in SITE_IDS):
        raise ValueError("Selected site IDs differ")
    if any(sites[s]["entity_id"] != "SHI" or sites[s]["operating"] is not False for s in SITE_IDS):
        raise ValueError("2026 site ownership or operation state differs")
    for sid in ("RUNTIME-RENO-COLO", "RUNTIME-BOISE-DR"):
        site = sites[sid]
        if (
            site["status"] != "PROVIDER_SELECTED_PROCUREMENT_PENDING"
            or site["contract_status"] != "DRAFT"
            or site["contract_executed"] is not False
        ):
            raise ValueError("Selected provider promoted to contracted or operating")
    if sites["RUNTIME-NN-OWNED-DC"]["status"] != "LAND_ACQUIRED_PRECONSTRUCTION":
        raise ValueError("Owned site activation differs")
    procedures = indexed(inputs["ccf_procedures"], "control_id")
    if not CONTROL_IDS <= procedures.keys():
        raise ValueError("Required CCF procedure missing")
    if (
        not procedures["SH-IAM-006"]["procedure"].endswith(
            "review quarterly and on ownership change."
        )
        or "quarterly privilege population" not in procedures["SH-IAM-005"]["procedure"]
        or "approved RPO" not in procedures["SH-BCM-002"]["procedure"]
        or "BIA" not in procedures["SH-BCM-003"]["procedure"]
        or "retention and holds" not in procedures["SH-REC-004"]["procedure"]
    ):
        raise ValueError("CCF conditional procedure changed")
    rules = calendar["duty_rules"]
    if len(rules) != 5 or len(indexed(rules, "rule_id")) != 5:
        raise ValueError("Five conditional duty rules required")
    if {cid for row in rules for cid in row["control_ids"]} != CONTROL_IDS:
        raise ValueError("Duty/control boundary differs")
    for rule in rules:
        if len(rule["control_ids"]) != 1 or rule["service_id"] not in SERVICE_IDS:
            raise ValueError("Duty service/control join differs")
        service = services[rule["service_id"]]
        if rule["owner_team"] is not None and rule["owner_team"] != service["accountable_owner"]:
            raise ValueError("Unapproved owner team")
        if rule["specific_due_dates_state"] == "KNOWN":
            raise ValueError("Unsupported company due calendar")
    unknown_boundary_fields = (
        "confirmed_2027_operating_systems",
        "confirmed_2027_contracts",
        "confirmed_2027_data_sets",
        "confirmed_2027_human_accounts",
        "confirmed_2027_nonhuman_accounts",
        "confirmed_2027_privileged_accounts",
        "confirmed_2027_disposal_targets",
    )
    if any(boundary[field] is not None for field in unknown_boundary_fields):
        raise ValueError("Unverified 2027 inventory promoted to fact")
    if boundary["company_2027_opening_complete"] is not False:
        raise ValueError("2027 opening completeness unsupported")
    if (
        calendar["start"] != "2027-01-01T00:00:00Z"
        or calendar["end_exclusive"] != "2028-01-01T00:00:00Z"
        or calendar["timezone"] != "UTC"
        or calendar["rule_state"] != "CONDITIONAL_DESIGN_RULES_NOT_ACCEPTED_COMPANY_DUE_EVENTS"
        or any(
            calendar[key] is not None
            for key in ("company_due_count", "company_observed_count", "company_missing_count")
        )
        or calendar["supplied_2027_company_performance_source_ids"] != []
    ):
        raise ValueError("Company due or performance population invented")
    if set(source["case_branches"]) != {"A", "B"} or any(
        branch != {"source_role": "COMMON_BOUNDARY_ONLY", "company_delta_state": "NOT_AUTHORED"}
        for branch in source["case_branches"].values()
    ):
        raise ValueError("Public A/B case delta invented")

    selected_sites = [
        {
            "id": sid,
            "legal_entity_id": sites[sid]["entity_id"],
            "site_status_at_2026_source": sites[sid]["status"],
            "provider": sites[sid].get("provider"),
            "contract_id": sites[sid].get("contract_id"),
            "contract_status": sites[sid].get("contract_status"),
            "contract_executed": sites[sid].get("contract_executed"),
            "operating_at_2026_source": sites[sid]["operating"],
            "operating_at_2027_opening": None,
        }
        for sid in sorted(SITE_IDS)
    ]
    selected_services = [
        {
            "id": sid,
            "name": services[sid]["name"],
            "accountable_team_at_design": services[sid]["accountable_owner"],
            "sourcing": services[sid]["sourcing"],
            "decision_state_at_source": service_source["default_decision_state"],
            "operating_at_2027_opening": None,
        }
        for sid in sorted(SERVICE_IDS)
    ]
    duty_rules = [
        {
            **row,
            "ccf_procedure": procedures[row["control_ids"][0]]["procedure"],
            "company_due_count": None,
            "company_observed_count": None,
            "company_missing_count": None,
            "evidence_state": "NO_ACCEPTED_2027_COMPANY_POPULATION_OR_PERFORMANCE_SOURCE",
        }
        for row in rules
    ]
    return {
        "record_id": "SH-PORTAL-2027-COMMON-BOUNDARY-v0.1",
        "source_record_id": source["record_id"],
        "source_sha256": source_sha256,
        "source_commit": source["accepted_source_commit"],
        "source_pins": source["source_pins"],
        "state": source["state"],
        "authored_at": source["authored_at"],
        "repository_available_at": None,
        "repository_acceptance_at": None,
        "known_on_state": "PENDING_REPOSITORY_ACCEPTANCE_NOT_QUERYABLE_AS_COMPANY_EVIDENCE",
        "scenario": source["scenario"],
        "fact_status": source["fact_status"],
        "access_scope": source["access_scope"],
        "period": {key: calendar[key] for key in ("start", "end_exclusive", "timezone")},
        "boundary": {
            **boundary,
            "legal_entity": {
                "id": "SHI",
                "legal_name": entity["legal_name"],
                "jurisdiction": entity["jurisdiction"],
                "legal_form": entity["legal_form"],
                "headquarters": entity["headquarters"],
            },
            "selected_service_designs": selected_services,
            "selected_site_designs": selected_sites,
        },
        "calendar": {
            "rule_state": calendar["rule_state"],
            "company_due_count": None,
            "company_observed_count": None,
            "company_missing_count": None,
            "supplied_2027_company_performance_source_ids": [],
            "conditional_rules": duty_rules,
        },
        "case_branches": source["case_branches"],
        "limits": source["limits"],
    }


def load(root: Path) -> dict:
    source_path = root / SOURCE
    source = json.loads(source_path.read_text())
    inputs = {}
    for key, pin in source["source_pins"].items():
        path = root / pin["path"]
        if sha256(path) != pin["sha256"]:
            raise ValueError(f"Source pin changed: {key}")
        if path.suffix == ".json":
            inputs[key] = json.loads(path.read_text())
    return derive(source, inputs, sha256(source_path))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = (json.dumps(load(args.source_root), indent=2, sort_keys=True) + "\n").encode()
    if args.check:
        if args.output.read_bytes() != rendered:
            raise ValueError("Stale 2027 common boundary export")
    else:
        if args.output.exists():
            raise ValueError("Output exists; use --check or a new version")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rendered)
    print("PASS conditional 2027 common company boundary")


if __name__ == "__main__":
    main()
