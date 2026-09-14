"""Source-pinned fictional identities and explicitly proposed training assignments.

This projection never mutates accepted rosters, financial releases or site occupancy.
Committee contacts are not substitutes for collective approval or delegations.
"""

import ast
import copy
import hashlib
import json
import subprocess
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

from enterprise.ccf.registry import ROOT, compile_registry, digest

PROPOSAL = "docs/structured/enterprise_leadership_2026-09-13.json"
CHART = "docs/organization/source/chartbook.json"
POPULATION = "geospatial/facilities/population/REGISTER.json"
# Primary contact, evidence custodian. Every assignment remains a branch proposal.
DOMAIN_CONTACTS = {
    "GOV": ("AS-P004", "AS-P004"),
    "ERM": ("AS-P005", "AS-P005"),
    "ETH": ("AS-P005", "AS-P006"),
    "POL": ("AS-P005", "AS-P014"),
    "LEG": ("AS-P003", "AS-P004"),
    "PPL": ("AS-P006", "AS-P006"),
    "TRN": ("AS-P006", "AS-P006"),
    "IAM": ("AS-P007", "AS-P007"),
    "SEC": ("AS-P008", "AS-P008"),
    "DAT": ("AS-P014", "AS-P014"),
    "REC": ("AS-P014", "AS-P014"),
    "ENG": ("P005", "P005"),
    "CFG": ("AS-P007", "AS-P007"),
    "OPS": ("AS-P007", "AS-P007"),
    "INC": ("AS-P008", "AS-P008"),
    "BCM": ("AS-P004", "AS-P007"),
    "TPR": ("AS-P013", "AS-P013"),
    "PRD": ("P002", "P004"),
    "FND": ("P005", "P017"),
    "AIM": ("P002", "P005"),
    "RND": ("P010", "P006"),
    "FLD": ("P007", "P007"),
    "ENV": ("AS-P015", "AS-P015"),
    "FIN": ("AS-P011", "AS-P011"),
    "REV": ("AS-P011", "P004"),
    "PRC": ("AS-P013", "AS-P011"),
    "PAY": ("AS-P006", "AS-P011"),
    "TRY": ("AS-P002", "AS-P011"),
    "AST": ("AS-P011", "AS-P012"),
    "TAX": ("AS-P002", "AS-P003"),
    "MNA": ("AS-P002", "AS-P003"),
    "ARU": ("P029", "P031"),
    "PSN": ("P022", "P023"),
    "CRD": ("P025", "P028"),
    "ADV": ("AS-P010", "AS-P010"),
    "ASS": ("AS-P005", "AS-P014"),
}
OVERRIDES = {
    "SH-GOV-003": ("P001", "AS-P004"),
    "SH-GOV-004": ("P043", "AS-P004"),
    "SH-ERM-002": ("P001", "AS-P005"),
    "SH-ERM-003": ("P001", "AS-P005"),
    "SH-ETH-001": ("AS-P003", "AS-P006"),
    "SH-PPL-004": ("AS-P004", "AS-P006"),
    "SH-TRN-004": ("P007", "P006"),
    "SH-IAM-004": ("AS-P007", "AS-P006"),
    "SH-DAT-002": ("AS-P003", "AS-P014"),
    "SH-DAT-003": ("AS-P003", "AS-P014"),
    "SH-DAT-005": ("AS-P003", "P002"),
    "SH-REC-004": ("AS-P003", "AS-P014"),
    "SH-INC-005": ("P007", "P007"),
    "SH-BCM-002": ("AS-P007", "AS-P007"),
    "SH-BCM-003": ("AS-P007", "AS-P007"),
    "SH-TPR-003": ("AS-P003", "AS-P013"),
    "SH-PRD-003": ("P004", "P004"),
    "SH-PRD-004": ("P004", "P005"),
    "SH-AIM-002": ("P006", "P005"),
    "SH-FIN-006": ("AS-P002", "AS-P011"),
    "SH-PRC-003": ("AS-P011", "AS-P013"),
    "SH-PAY-003": ("AS-P003", "AS-P011"),
    "SH-MNA-002": ("P001", "AS-P004"),
    "SH-ARU-002": ("P036", "P031"),
    "SH-ARU-003": ("P035", "P037"),
    "SH-PSN-003": ("P022", "AS-P015"),
    "SH-PSN-004": ("AS-P002", "P022"),
    "SH-PSN-005": ("AS-P008", "AS-P003"),
    "SH-CRD-004": ("AS-P003", "P025"),
    "SH-ASS-003": ("AS-P009", "AS-P009"),
    "SH-ASS-004": ("AS-P009", "AS-P009"),
}
# Fictional management quality-review routes, separate from independent assurance.
# A named reviewer checks the operating record; reserved committee decisions still
# require the source body's collective record and cannot be signed by this contact.
OPERATING_REVIEWERS = {
    "AS-P001": "P001",
    "AS-P002": "P001",
    "AS-P003": "P001",
    "AS-P004": "AS-P003",
    "AS-P005": "AS-P003",
    "AS-P006": "AS-P001",
    "AS-P007": "AS-P008",
    "AS-P008": "AS-P007",
    "AS-P009": "P044",
    "AS-P010": "P001",
    "AS-P011": "AS-P002",
    "AS-P012": "AS-P001",
    "AS-P013": "AS-P002",
    "AS-P014": "AS-P007",
    "AS-P015": "AS-P001",
    "P001": "P043",
    "P002": "P001",
    "P004": "P002",
    "P005": "P002",
    "P006": "P010",
    "P007": "P001",
    "P010": "P001",
    "P022": "P001",
    "P025": "P001",
    "P029": "P001",
    "P035": "P029",
    "P036": "P035",
    "P043": "P044",
}

ASSERTIONS = {
    "existence_occurrence": "Existence or occurrence",
    "completeness": "Completeness",
    "valuation_allocation": "Valuation or allocation",
    "rights_obligations": "Rights and obligations",
    "presentation_disclosure": "Presentation and disclosure",
}
PROCESS_DOMAINS = {
    "close": ["FIN"],
    "revenue": ["REV", "FIN"],
    "treasury": ["TRY", "FIN"],
    "inventory": ["AST", "FIN"],
    "fixed_assets": ["AST", "FIN"],
    "procure_pay": ["PRC", "FIN"],
    "payroll": ["PAY", "PPL", "FIN"],
    "capital_integration": ["MNA", "TRY", "FIN"],
    "recovery": ["CRD", "REV", "FIN"],
    "tax": ["TAX", "FIN"],
}
ACCOUNT_PROCESS = {
    "1000": "treasury",
    "1100": "revenue",
    "1200": "inventory",
    "1500": "fixed_assets",
    "1590": "fixed_assets",
    "1600": "capital_integration",
    "2000": "procure_pay",
    "2100": "procure_pay",
    "2200": "revenue",
    "2300": "fixed_assets",
    "2500": "treasury",
    "2510": "treasury",
    "3000": "capital_integration",
    "4000": "revenue",
    "4010": "revenue",
    "4020": "revenue",
    "4030": "revenue",
    "4040": "revenue",
    "4050": "recovery",
    "4060": "revenue",
    "4090": "close",
    "5000": "inventory",
    "5050": "inventory",
    "6000": "procure_pay",
    "6100": "payroll",
    "6110": "procure_pay",
    "6200": "procure_pay",
    "6300": "fixed_assets",
    "6400": "close",
    "7100": "treasury",
    "9000": "close",
    "BIZ_AR": "revenue",
    "BIZ_ALLOWANCE": "revenue",
    "BIZ_INVENTORY": "inventory",
    "BIZ_PPE": "fixed_assets",
    "BIZ_ACCUM": "fixed_assets",
    "BIZ_AP": "procure_pay",
    "BIZ_DEFERRED": "revenue",
    "BIZ_HOST_AP": "recovery",
    "BIZ_REVENUE": "revenue",
    "BIZ_PAYROLL": "payroll",
    "BIZ_DELIVERY": "procure_pay",
    "BIZ_RESEARCH": "procure_pay",
    "BIZ_PROCESSING": "recovery",
    "BIZ_COGS": "inventory",
    "BIZ_HOST_SHARE": "recovery",
    "BIZ_DDA": "fixed_assets",
    "BIZ_SUPPORT": "procure_pay",
    "BIZ_CREDIT_LOSS": "revenue",
    "BIZ_INVENTORY_LOSS": "inventory",
    "BIZ_UNIT_CLEARING": "close",
    "BIZ_CAPITAL_UNPAID": "capital_integration",
    "BIZ_DEBT_UNPAID": "treasury",
}


def _read(root, path):
    return json.loads((root / path).read_text())


def _literal(root, path, name):
    """Read literal source constants without executing the finance application."""
    for node in ast.parse((root / path).read_text()).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise ValueError("Missing source constant: " + name)


def financial_model(repository=ROOT, native=None):
    root = Path(repository)
    native = native or compile_registry(root)
    source_sets = [
        (
            "enterprise_successor",
            "enterprise/business/model.py",
            _literal(root, "enterprise/business/model.py", "ACCOUNTS"),
        ),
        (
            "historical_calibration",
            "src/sable_harbor/generation.py",
            _literal(root, "src/sable_harbor/generation.py", "ACCOUNTS"),
        ),
    ]
    accounts = []
    for model, source, values in source_sets:
        rows = (
            [(code, code, kind, None) for code, kind in values.items()]
            if isinstance(values, dict)
            else values
        )
        for code, label, kind, normal in rows:
            if code not in ACCOUNT_PROCESS:
                raise ValueError("Unmapped financial source account: " + code)
            assertions = list(ASSERTIONS)
            if kind.lower() in {"expense", "other_expense", "revenue"}:
                assertions.remove("rights_obligations")
            accounts.append(
                dict(
                    id=f"{model}:{code}",
                    account_code=code,
                    name=label,
                    account_type=kind,
                    normal_balance=normal,
                    source_path=source,
                    source_constant="ACCOUNTS",
                    model=model,
                    process_id=ACCOUNT_PROCESS[code],
                    candidate_assertions=assertions,
                    assertion_acceptance="REQUIRES_ENGAGEMENT_RISK_ASSESSMENT",
                    materiality=None,
                )
            )
    services = [r for r in native["records"] if r["kind"] == "service"]
    controls = [r for r in native["records"] if r["kind"] == "control"]
    processes = []
    for pid, domains in PROCESS_DOMAINS.items():
        ids = [r["id"] for r in controls if r["data"]["domain_id"] in domains]
        linked = [s for s in services if set(s["data"]["control_ids"]) & set(ids)]
        processes.append(
            dict(
                id=pid,
                candidate_control_ids=ids,
                account_ids=[a["id"] for a in accounts if a["process_id"] == pid],
                source_service_ids=[s["id"] for s in linked],
                source_component_ids=sorted(
                    {
                        c
                        for s in linked
                        for c in [s["data"]["owner_component_id"], *s["data"]["component_ids"]]
                    }
                ),
                relationship_status="SOURCE_CONTROL_SERVICE_LINK_WITH_PROPOSED_ACCOUNT_PROCESS_ROUTE",
                deployed_system_ids=[],
                deployed_system_status="NOT_ESTABLISHED_BY_SERVICE_DESIGN",
            )
        )
    return dict(
        accounts=accounts,
        processes=processes,
        assertion_taxonomy=ASSERTIONS,
        taxonomy_reference=(
            "PCAOB AS 1105.11-.12; reference vocabulary, not automatic jurisdiction selection"
        ),
        taxonomy_url="https://pcaobus.org/oversight/standards/auditing-standards/details/AS1105",
        selected_professional_basis=None,
        selected_reporting_basis=None,
        source_model_boundary=(
            "Successor forecast and historical calibration remain separate; "
            "neither is observed financial history"
        ),
        mapping_status="PROPOSED_TRAINING_RELATIONSHIPS_NOT_PROFESSIONALLY_VALIDATED",
    )


def snapshot(repository=ROOT, *, as_of="2026-09-13", scenario_overlay=None):
    root = Path(repository)
    when = date.fromisoformat(as_of)
    native = compile_registry(root)
    chart = _read(root, CHART)
    population = _read(root, POPULATION)
    proposal = _read(root, PROPOSAL)
    policy = _read(root, "enterprise/business/source/policy.json")
    cards = {}
    for n in chart["nodes"]:
        if n["type"] == "person":
            cards.setdefault(n["person_id"], []).append(n)
    canonical = []
    pending_ids = {p["person_id"] for p in proposal["people"]}
    for p in population["people"]:
        if p["person_id"] in pending_ids:
            continue
        record = copy.deepcopy(p)
        record.update(
            identity_authority="ACCEPTED_SOURCE_IDENTITY",
            effective_from=None,
            effective_to=None,
            effective_date_status="EXACT_APPOINTMENT_INTERVAL_NOT_ESTABLISHED",
            titles=[
                dict(title=n["title"], status=n["title_state"], source_refs=n["sources"])
                for n in cards[p["person_id"]]
            ],
            reporting_line=None,
            location=None,
        )
        canonical.append(record)
    proposed = []
    groups = Counter()
    for person in proposal["people"]:
        groups[person["forecast_group"]] += 1
        p = copy.deepcopy(person)
        p.update(
            identity_authority="DATED_DELEGATED_SOURCE_IDENTITY_PENDING_ACCEPTED_MERGE",
            effective_from=proposal["effective_from"],
            effective_to=None,
            employment_start=None,
            appointment_basis=proposal["record_id"],
            workplace_assignment=None,
            workplace_status="UNASSIGNED_NOT_OCCUPIED",
            location=None,
            employer_entity_id="SHI",
            forecast_position_id=f"SYN-{person['forecast_group'].upper()}-{groups[person['forecast_group']]:03}",
            forecast_position_binding_status="DATED_ALIAS_WITHIN_CONDITIONAL_2027_OCCUPIED_ROSTER",
            status="PROPOSED_OFFICE_OCCUPANT",
            compensation_assumption=dict(
                annual_loaded_usd=policy["workforce"][p["forecast_group"]]["annual_loaded_usd"],
                source="enterprise/business/source/policy.json",
                status="2027_GROUP_MODEL_RATE_NOT_PERSON_SALARY",
            ),
        )
        proposed.append(p)
    people = {p["person_id"]: p for p in canonical + proposed}
    if len(people) != len(canonical) + len(proposed):
        raise ValueError("Duplicate canonical/proposed person ID")
    roles = {r["id"]: r["data"]["title"] for r in native["records"] if r["kind"] == "role"}
    assignments = []
    for c in (r for r in native["records"] if r["kind"] == "control"):
        cid, domain = c["id"], c["data"]["domain_id"]
        owner, custodian = OVERRIDES.get(cid, DOMAIN_CONTACTS[domain])
        reviewer = "P043" if owner == "AS-P009" else "AS-P009"
        active = when >= date.fromisoformat(proposal["effective_from"])
        assignments.append(
            dict(
                id="AS-OWN:" + cid,
                control_id=cid,
                control_statement=c["data"]["statement"],
                owner_role_id=c["data"]["owner_role_id"],
                source_role_title=roles[c["data"]["owner_role_id"]],
                primary_person_id=owner if active else None,
                custodian_person_id=custodian if active else None,
                reviewer_person_id=reviewer if active else None,
                reviewer_purpose="INDEPENDENT_ASSURANCE_ONLY",
                operating_reviewer_person_id=OPERATING_REVIEWERS[owner] if active else None,
                operating_review_purpose=(
                    "MANAGEMENT_RECORD_QUALITY_REVIEW; no substitute for collective "
                    "reserved approval"
                ),
                operating_approval_authority=roles[c["data"]["owner_role_id"]],
                collective_approval_required=any(
                    word in roles[c["data"]["owner_role_id"]].lower()
                    for word in ("committee", "board")
                ),
                proposed_contact_ids=[owner, custodian, reviewer],
                effective_from=proposal["effective_from"],
                effective_to=None,
                status="PROPOSED_CURRENT_ASSIGNMENT"
                if active
                else "HISTORICAL_ASSIGNMENT_REQUIRED",
                source_refs=c["source_refs"],
                boundary_ids=[],
                boundary_status=(
                    "CONTROL_LEVEL_COORDINATION_ROUTE; local implementation scope and "
                    "delegation must be separately bound"
                ),
                authority_limit=(
                    "Contact and custody do not grant collective Board approval, "
                    "operating command, professional certification or source "
                    "acceptance"
                ),
                assignment_authority=proposal["record_id"],
                workload_fte=None,
            )
        )
    overlay = (
        copy.deepcopy(scenario_overlay) if scenario_overlay is not None else {"assignments": []}
    )
    if (
        not isinstance(overlay, dict)
        or set(overlay) != {"assignments"}
        or not isinstance(overlay["assignments"], list)
    ):
        raise ValueError("Scenario overlay must contain assignment records only")
    by_id = {a["control_id"]: a for a in assignments}
    seen = set()
    for change in overlay["assignments"]:
        allowed = {
            "control_id",
            "primary_person_id",
            "custodian_person_id",
            "reviewer_person_id",
            "effective_from",
            "effective_to",
            "rationale",
        }
        if (
            not isinstance(change, dict)
            or set(change) not in (allowed, allowed | {"operating_reviewer_person_id"})
            or change["control_id"] in seen
        ):
            raise ValueError("Invalid or duplicate scenario assignment")
        seen.add(change["control_id"])
        if (
            change["control_id"] not in by_id
            or not isinstance(change["rationale"], str)
            or not change["rationale"].strip()
        ):
            raise ValueError("Unknown control or missing overlay rationale")
        start = date.fromisoformat(change["effective_from"])
        end = date.fromisoformat(change["effective_to"]) if change["effective_to"] else None
        if end and end <= start:
            raise ValueError("Invalid overlay interval")
        for field in ("primary_person_id", "custodian_person_id", "reviewer_person_id") + (
            ("operating_reviewer_person_id",) if "operating_reviewer_person_id" in change else ()
        ):
            person = people.get(change[field])
            if person is None or person["status"] in {
                "former_employee",
                "historical_employee_current_status_unconfirmed",
            }:
                raise ValueError("Unknown or unavailable overlay person")
            years = [
                r["year"] for r in person.get("joining_records", []) if r.get("year") is not None
            ]
            if years and start.year < min(years):
                raise ValueError("Person predates earliest sourced joining record")
            if person.get("effective_from") and start < date.fromisoformat(
                person["effective_from"]
            ):
                raise ValueError("Future proposed occupant cannot sign historical records")
        if start <= when and (end is None or when < end):
            by_id[change["control_id"]].update(
                {
                    **copy.deepcopy(change),
                    "operating_reviewer_person_id": change.get("operating_reviewer_person_id"),
                },
                status="SCENARIO_ONLY_ASSIGNMENT",
                assignment_authority="EXPLICIT_RUN_OVERLAY",
            )
    for group, count in groups.items():
        if count > policy["workforce"][group]["occupied"]:
            raise ValueError("Proposed naming exceeds occupied forecast positions")
    source_paths = {ref for record in native["records"] for ref in record["source_refs"]} | {
        CHART,
        POPULATION,
        PROPOSAL,
        proposal["canonical_source"],
        "docs/governance/ENTERPRISE_COORDINATION_2026-09-13.md",
        "enterprise/business/source/policy.json",
        "enterprise/business/model.py",
        "src/sable_harbor/generation.py",
        "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
        "enterprise/services/source/services.json",
    }
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    result = dict(
        schema_version=1,
        as_of=as_of,
        source_revision=revision,
        source_sha256={
            p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in sorted(source_paths)
        },
        owner_design_status=proposal["owner_design_status"],
        repository_acceptance_status=proposal["repository_acceptance_status"],
        control_inventory_ids=sorted(a["control_id"] for a in assignments),
        canonical_people=canonical,
        proposed_people=proposed,
        proposed_appointments=[
            dict(
                person_id=p["person_id"],
                role_id=p["org_role_id"],
                effective_from=p["effective_from"],
                effective_to=None,
                status="PROPOSED_NOT_ACCEPTED_CANON",
                authority_record=proposal["record_id"],
            )
            for p in proposed
        ],
        control_assignments=assignments,
        scenario_overlay=overlay,
        financial_model=financial_model(root, native),
        reconciliation=dict(
            accepted_named_employee_count=sum(p["status"] == "current_employee" for p in canonical),
            accepted_nonemployee_directors=sum(
                p["status"] == "current_nonemployee_director" for p in canonical
            ),
            proposed_new_named_identities=len(proposed),
            branch_current_named_employees=sum(p["status"] == "current_employee" for p in canonical)
            + len(proposed),
            pending_acceptance_named_identities=len(proposed),
            actual_enterprise_headcount=None,
            actual_2026_payroll_delta_usd=None,
            current_seat_occupancy_delta=None,
            forecast_groups=[
                dict(
                    group=g,
                    proposed_named_slots=n,
                    occupied_before=policy["workforce"][g]["occupied"],
                    occupied_after=policy["workforce"][g]["occupied"],
                    authorized_before=policy["workforce"][g]["authorized"],
                    authorized_after=policy["workforce"][g]["authorized"],
                    incremental_forecast_fte=0,
                    incremental_forecast_payroll_usd="0.00",
                    named_slot_loaded_cost_usd=str(
                        Decimal(n) * Decimal(policy["workforce"][g]["annual_loaded_usd"])
                    ),
                )
                for g, n in sorted(groups.items())
            ],
            forecast_assumption=(
                "Proposed names substitute for existing synthetic occupied 2027 "
                "positions; no additional forecast FTE or payroll, and no claim "
                "those people occupied 2026 seats"
            ),
            assigned_new_physical_seats=0,
            seat_basis="No current workplace assigned; facility occupancy remains unestablished",
            j2_authorized_billets=237,
            j2_incremental_billets=0,
            dependency_status=(
                "DATED_SOURCE_AND_VECTOR_SUCCESSOR_RECONCILED_PENDING_ACCEPTED_MERGE; "
                "preserved predecessor and pinned finance unchanged"
            ),
        ),
    )
    result["validation"] = validate(result)
    result["snapshot_digest"] = digest(result)
    return result


def validate(value):
    people = {p["person_id"]: p for p in value["canonical_people"] + value["proposed_people"]}
    assignments = value["control_assignments"]
    if len({a["control_id"] for a in assignments}) != len(assignments):
        raise ValueError("Duplicate control assignment")
    if set(value["control_inventory_ids"]) != {a["control_id"] for a in assignments}:
        raise ValueError("Control assignment inventory is incomplete")
    resolved = 0
    for a in assignments:
        if a["status"] == "HISTORICAL_ASSIGNMENT_REQUIRED":
            continue
        fields = [a[k] for k in ("primary_person_id", "custodian_person_id", "reviewer_person_id")]
        if any(p not in people for p in fields):
            raise ValueError("Orphan assignment person")
        if fields[2] in fields[:2]:
            raise ValueError("Reviewer cannot prepare or own the reviewed work")
        if fields[2] in {"P063", "P064", "P065", "P066", "P067", "P068"}:
            raise ValueError("J2 is not the independent audit function")
        if (
            a["control_id"] == "SH-ASS-003"
            and people[fields[0]].get("department") != "Internal Audit"
        ):
            raise ValueError("Independent audit must retain its separate function")
        operating = a.get("operating_reviewer_person_id")
        if operating is not None:
            if operating not in people or operating in fields[:2]:
                raise ValueError(
                    "Operating reviewer must be an available person distinct from "
                    "preparer and custodian"
                )
            if operating == fields[2]:
                raise ValueError("Assurance reviewer cannot review their own operating approval")
            if operating == "AS-P009" or people[operating].get("department") == "Internal Audit":
                raise ValueError("Internal Audit cannot approve management operating records")
        resolved += 1
    model = value["financial_model"]
    if len({a["id"] for a in model["accounts"]}) != len(model["accounts"]):
        raise ValueError("Duplicate financial account identity")
    if any(
        not a["candidate_assertions"] or set(a["candidate_assertions"]) - set(ASSERTIONS)
        for a in model["accounts"]
    ):
        raise ValueError("Invalid financial assertion route")
    return dict(
        control_count=len(assignments),
        resolved_current_proposal_count=resolved,
        historical_unresolved_count=len(assignments) - resolved,
        financial_account_count=len(model["accounts"]),
        source_acceptance="NOT_PROMOTED",
        qualified_review="NOT_ASSERTED",
    )
