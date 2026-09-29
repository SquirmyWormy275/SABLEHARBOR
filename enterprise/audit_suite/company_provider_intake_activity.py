"""Paired planned-provider intake exercise; no vendor representations or onboarding acceptance."""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

CONTROLS = ["SH-TPR-001", "SH-TPR-002", "SH-TPR-004"]
SITES_PATH = "enterprise/services/source/runtime_sites_2026-09-11.json"
QUALIFICATION = (
    "LOCAL_PLANNED_PROVIDER_INTAKE_EXERCISE_NOT_VENDOR_ACCEPTANCE_OR_OPERATING_MONITORING"
)
REQUIREMENTS = (
    "assurance_report_scope_period_exceptions_and_customer_controls",
    "privacy_data_access_and_subcontractor_roles",
    "continuity_and_carrier_administrative_independence",
    "financial_exposure_and_concentration",
)
SITE_ROLES = {"RUNTIME-RENO-COLO": "PRIMARY", "RUNTIME-BOISE-DR": "RECOVERY"}


@dataclass(frozen=True)
class ProviderIntakeRecipe:
    company_id: str
    complete_branch: str
    omission_branch: str
    cycle_id: str
    source_sites_sha256: str
    start_at: str
    review_due_at: str
    backfill_at: str
    local_review_cadence_basis: str


def import_inventory(dependencies, *, included_roles):
    if (
        not isinstance(included_roles, list)
        or len(included_roles) != len(set(included_roles))
        or set(included_roles) - {"PRIMARY", "RECOVERY"}
    ):
        raise CompanyStoreError("Explicit distinct local dependency role filter required")
    return [dict(d) for d in dependencies if d["planned_dependency_role"] in included_roles]


def tier(provider):
    if provider.get("planned_dependency_role") not in {"PRIMARY", "RECOVERY"}:
        raise CompanyStoreError("Explicit planned dependency role required")
    return {
        "tier": "LOCAL_PROVISIONAL_CRITICAL_DEPENDENCY",
        "basis": (
            "Local rule: planned primary or recovery dependency requires the "
            "full diligence checklist"
        ),
        "inputs": {
            "planned_dependency_role": provider["planned_dependency_role"],
            "dependency_id": provider["dependency_id"],
            "operating": provider["operating"],
        },
        "accepted_enterprise_tier": False,
        "data_access_exposure": "UNDETERMINED",
        "phi_role": "UNDETERMINED_NO_PROCESSING_ASSERTED",
        "assessment_dimensions": {
            "criticality": "PLANNED_PRIMARY_OR_RECOVERY_DEPENDENCY",
            "data_access": "UNDETERMINED",
            "operational": "NOT_OPERATING",
            "legal": "DRAFT_CONTRACT_NOT_EVALUATED",
            "financial": "UNKNOWN_NO_VENDOR_SOURCE",
            "concentration": "NOMINALLY_DISTINCT_PROVIDERS_INDEPENDENCE_UNVERIFIED",
        },
    }


def reconcile(dependencies, inventory, diligence, reviews):
    expected = {d["provider_id"] for d in dependencies}
    observed = {d["provider_id"] for d in inventory}
    if len(observed) != len(inventory) or len(expected) != len(dependencies):
        raise CompanyStoreError("Duplicate provider in declared dependency/source inventory")
    required = {(p, r) for p in expected for r in REQUIREMENTS}
    supplied = {(d["provider_id"], d["requirement_id"]) for d in diligence}
    if len(supplied) != len(diligence):
        raise CompanyStoreError("Duplicate diligence work item")
    reviewed = {r["provider_id"] for r in reviews}
    if len(reviewed) != len(reviews):
        raise CompanyStoreError("Duplicate review occurrence")
    return {
        "declared_dependency_providers": sorted(expected),
        "registered_providers": sorted(observed),
        "missing_provider_ids": sorted(expected - observed),
        "unexpected_provider_ids": sorted(observed - expected),
        "missing_diligence_work_items": [
            {"provider_id": p, "requirement_id": r} for p, r in sorted(required - supplied)
        ],
        "missing_due_review_provider_ids": sorted(expected - reviewed),
        "late_review_provider_ids": sorted(
            r["provider_id"] for r in reviews if r.get("late_seconds", 0) > 0
        ),
        "outstanding_diligence_support_items": [
            {"provider_id": d["provider_id"], "requirement_id": d["requirement_id"]}
            for d in diligence
            if d.get("support_status") != "OBTAINED"
        ],
        "diligence_support_obtained": sum(d.get("support_status") == "OBTAINED" for d in diligence),
        "basis": (
            "Declared planned dependencies versus internal work queues, not "
            "provider evidence completeness"
        ),
    }


def generate_pair(destination, *, repository, recipe: ProviderIntakeRecipe):
    destination, repository = Path(destination).absolute(), Path(repository)
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in (destination, *destination.parents))
    ):
        raise CompanyStoreError("New private nonsymlink destination required")
    for value in (
        recipe.company_id,
        recipe.complete_branch,
        recipe.omission_branch,
        recipe.cycle_id,
    ):
        _id(value)
    if recipe.complete_branch == recipe.omission_branch:
        raise CompanyStoreError("Distinct exercise branches required")
    start, due, backfill = [
        datetime.fromisoformat(_time(v))
        for v in (recipe.start_at, recipe.review_due_at, recipe.backfill_at)
    ]
    if not timedelta(days=80) <= due - start <= timedelta(days=100) or not timedelta(
        days=1
    ) <= backfill - due <= timedelta(days=30):
        raise CompanyStoreError(
            "Explicit bounded local quarterly review and later backfill dates required"
        )
    if (
        not isinstance(recipe.local_review_cadence_basis, str)
        or not 1 <= len(recipe.local_review_cadence_basis.strip()) <= 2000
    ):
        raise CompanyStoreError("Explicit local provisional cadence assumption required")
    source_path = repository / SITES_PATH
    if destination.is_relative_to(source_path.absolute().parent) or any(
        p.is_symlink() for p in (source_path, *source_path.parents)
    ):
        raise CompanyStoreError("Output must be outside source tree; source aliases forbidden")
    raw = source_path.read_bytes()
    if sha(raw) != recipe.source_sites_sha256:
        raise CompanyStoreError("Pinned provider/site source changed")
    sites = json.loads(raw)
    selected = [s for s in sites["sites"] if s["id"] in SITE_ROLES]
    if len(selected) != 2 or {s["id"] for s in selected} != set(SITE_ROLES):
        raise CompanyStoreError("Exact primary and recovery planning sources required")
    dependencies = []
    for site in selected:
        if (
            site["status"] != "PROVIDER_SELECTED_PROCUREMENT_PENDING"
            or site["operating"] is not False
            or site["contract_executed"] is not False
            or site["contract_status"] != "DRAFT"
            or site["provider_legal_name"] is not None
        ):
            raise CompanyStoreError(
                "Source states changed; explicit new exercise reconciliation required"
            )
        if site["id"] == "RUNTIME-BOISE-DR" and (
            site.get("independence_verified") is not False
            or site.get("independence_evidence") != []
        ):
            raise CompanyStoreError("Recovery independence source state changed")
        dependencies.append(
            {
                **site,
                "planned_dependency_role": SITE_ROLES[site["id"]],
                "source_locator": SITES_PATH + "#/sites/" + str(sites["sites"].index(site)),
                "source_sha256": sha(raw),
            }
        )
    org = snapshot(repository, as_of=start.date().isoformat())
    assignments = [
        next(a for a in org["control_assignments"] if a["control_id"] == c) for c in CONTROLS
    ]
    owner = assignments[0]["primary_person_id"]
    reviewer = assignments[0]["operating_reviewer_person_id"]
    if (
        not owner
        or not reviewer
        or owner == reviewer
        or any(
            a["primary_person_id"] != owner or a["operating_reviewer_person_id"] != reviewer
            for a in assignments
        )
    ):
        raise CompanyStoreError("Consistent distinct scoped TPR contacts required")
    pins = dict(org["source_sha256"])
    for path in (
        SITES_PATH,
        "docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md",
        "docs/canon/THIRD_PARTY_SERVICES_SOURCING_DECISIONS_2026-09-09.md",
        "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
        "enterprise/ccf/assurance/design_data/control_procedures.json",
        "enterprise/audit_suite/company_provider_intake_activity.py",
    ):
        pins[path] = sha((repository / path).read_bytes())
    recipe_pin = sha(encoded(asdict(recipe)))
    common = {
        "cycle_id": recipe.cycle_id,
        "classification": QUALIFICATION,
        "control_ids": CONTROLS,
        "boundary_id": "corporate",
        "source_sites_sha256": sha(raw),
        "supplier_decisions": "NO_NEW_SELECTION_OR_ONBOARDING_ACCEPTANCE",
        "policy_status": "LOCAL_PROVISIONAL_RULE_NOT_ACCEPTED_ENTERPRISE_POLICY",
        "appointment_status": "SCOPED_EXERCISE_CONTACTS_NOT_NEW_EMPLOYMENT_OR_BOARD_APPOINTMENT",
        "monitoring_basis": "PRE_OPERATING_INTERNAL_DILIGENCE_REVIEW_QUEUE_ONLY",
        "vendor_performance": "NOT_APPLICABLE_NOT_OPERATING",
        "phi_role": "UNDETERMINED_NO_PROCESSING_ASSERTED",
        "contract_execution": "NOT_ASSERTED_SOURCE_DRAFT_UNCHANGED",
        "source_repository_acceptance": sites.get("repository_acceptance"),
        "source_recorded_on": sites.get("recorded_on"),
    }
    receipts, summaries = [], []
    with tempfile.TemporaryDirectory(prefix="provider-intake-", dir=destination.parent) as temp:
        store = CompanyStore(Path(temp))
        for branch in (recipe.complete_branch, recipe.omission_branch):
            for system in (
                "planned_dependency_inventory",
                "import_configuration",
                "vendor_register",
                "tier_assessments",
                "diligence_work_items",
                "review_schedule",
                "monitoring_reviews",
                "coverage_reconciliation",
                "internal_actions",
            ):
                store.register_system(
                    recipe.company_id,
                    branch,
                    system,
                    reviewer if system == "monitoring_reviews" else owner,
                )
            versions = {}

            def emit(
                system, identity, at, body, *, branch=branch, versions=versions, controls=CONTROLS
            ):
                stamp = _time(at.isoformat())
                version = versions.get((system, identity), 0)
                content = encoded(
                    {
                        **common,
                        "control_ids": controls,
                        "record_id": identity,
                        "recorded_at": stamp,
                        **body,
                    }
                )
                row = store.append_version(
                    recipe.company_id,
                    branch,
                    system,
                    identity,
                    expected_version=version,
                    command_id="TPR-"
                    + sha(encoded([recipe_pin, branch, system, identity, version])),
                    event_at=stamp,
                    available_at=stamp,
                    content=content,
                    provenance={
                        "name": identity + ".json",
                        "source_reference": identity,
                        "control_ids": controls,
                        "classification": QUALIFICATION,
                        "operational_fact_status": "LOCAL_PRE_OPERATING_WORKFLOW_EXERCISE",
                        "source_sha256": pins,
                        "recipe_sha256": recipe_pin,
                        "scoped_assignments": assignments,
                        "qualification": (
                            "Vendor support remains absent; source "
                            "selection/contract/operation states unchanged"
                        ),
                    },
                )
                versions[system, identity] = version + 1
                receipts.append(row)
                return {
                    k: row[k]
                    for k in (
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "sha256",
                        "available_at",
                    )
                }

            inventory_ref = emit(
                "planned_dependency_inventory",
                "DEPENDENCIES",
                start,
                {
                    "dependencies": dependencies,
                    "inventory_basis": (
                        "EXPLICIT_TWO_PLANNED_PROVIDER_DEPENDENCIES_NOT_ENTERPRISE_VENDOR_CENSUS"
                    ),
                },
                controls=["SH-TPR-001"],
            )
            roles = ["PRIMARY"] if branch == recipe.omission_branch else ["PRIMARY", "RECOVERY"]
            config = emit(
                "import_configuration",
                "IMPORT-CONFIG",
                start + timedelta(minutes=1),
                {"included_dependency_roles": roles, "owner_id": owner},
                controls=["SH-TPR-001"],
            )
            inventory = import_inventory(dependencies, included_roles=roles)
            diligence = []
            reviews = []

            def prepare(
                provider,
                at,
                config_ref,
                diligence=diligence,
                emit=emit,
                inventory_ref=inventory_ref,
            ):
                pid = provider["provider_id"]
                vendor = emit(
                    "vendor_register",
                    pid,
                    at,
                    {
                        "provider": provider,
                        "source_inventory": inventory_ref,
                        "import_configuration": config_ref,
                        "register_entry_state": "LOCAL_DILIGENCE_TRACKING_ONLY_NOT_ACCEPTED_VENDOR",
                    },
                    controls=["SH-TPR-001"],
                )
                assessed = tier(provider)
                assessed_ref = emit(
                    "tier_assessments",
                    pid + "-TIER",
                    at + timedelta(minutes=1),
                    {
                        "provider_id": pid,
                        "assessment": assessed,
                        "vendor_record": vendor,
                        "assessor_id": owner,
                    },
                    controls=["SH-TPR-001"],
                )
                for index, requirement in enumerate(REQUIREMENTS, 1):
                    item = {
                        "provider_id": pid,
                        "requirement_id": requirement,
                        "support_status": "NOT_OBTAINED",
                        "external_request_status": "NOT_SENT_LOCAL_WORK_ITEM_ONLY",
                        "received_document_sha256": None,
                        "report_scope": None,
                        "report_period": None,
                        "exceptions": None,
                        "customer_controls": None,
                        "financial_condition": "UNKNOWN_NO_SOURCE",
                        "subcontractor_changes": "UNKNOWN_NO_SOURCE",
                        "tier_assessment": assessed_ref,
                        "owner_id": owner,
                    }
                    emit(
                        "diligence_work_items",
                        pid + f"-REQ-{index}",
                        at + timedelta(minutes=2),
                        item,
                        controls=["SH-TPR-002"],
                    )
                    diligence.append(item)
                emit(
                    "review_schedule",
                    pid + "-REVIEW-DUE",
                    at + timedelta(minutes=3),
                    {
                        "provider_id": pid,
                        "due_at": _time(due.isoformat()),
                        "cadence_basis": recipe.local_review_cadence_basis,
                        "reviewer_id": reviewer,
                        "schedule_status": "OVERDUE_AT_REGISTRATION" if at > due else "SCHEDULED",
                        "monitoring_scope": (
                            "INTERNAL_DILIGENCE_GAPS_NOT_SUPPLIER_SLA_OR_INCIDENT_MONITORING"
                        ),
                    },
                    controls=["SH-TPR-004"],
                )

            for provider in inventory:
                prepare(provider, start + timedelta(minutes=5), config)

            def review(provider, at, reviews=reviews, emit=emit):
                row = {
                    "provider_id": provider["provider_id"],
                    "reviewer_id": reviewer,
                    "owner_id": owner,
                    "original_due_at": _time(due.isoformat()),
                    "late_seconds": int(max(0, (at - due).total_seconds())),
                    "review_result": "EVIDENCE_GAPS_REMAIN_ONBOARDING_NOT_ACCEPTED",
                    "evidence_requirements": list(REQUIREMENTS),
                    "support_status": "NOT_OBTAINED",
                    "incident_history": "UNKNOWN_NO_VENDOR_SOURCE",
                    "financial_health": "UNKNOWN_NO_VENDOR_SOURCE",
                    "planned_recovery_independence": "UNVERIFIED"
                    if provider["planned_dependency_role"] == "RECOVERY"
                    else "REQUIRES_SEPARATE_RECOVERY_PROVIDER_EVIDENCE",
                    "performance_data": "NOT_APPLICABLE_NOT_OPERATING",
                }
                emit(
                    "monitoring_reviews",
                    provider["provider_id"] + "-REVIEW",
                    at,
                    row,
                    controls=["SH-TPR-004"],
                )
                reviews.append(row)

            for provider in inventory:
                review(provider, due)
            initial = reconcile(dependencies, inventory, diligence, reviews)
            gap_ref = emit(
                "coverage_reconciliation",
                "COVERAGE-INITIAL",
                due + timedelta(minutes=5),
                {**initial, "source_inventory": inventory_ref, "owner_id": owner},
            )
            emit(
                "internal_actions",
                "RECONCILE-INTAKE",
                due + timedelta(minutes=6),
                {
                    "coverage_report": gap_ref,
                    "owner_id": owner,
                    "status": "OPEN",
                    "action": (
                        "Reconcile local dependency import and absent evidence; no "
                        "vendor decision or external communication"
                    ),
                },
            )
            fixed = emit(
                "import_configuration",
                "IMPORT-CONFIG",
                backfill,
                {
                    "included_dependency_roles": ["PRIMARY", "RECOVERY"],
                    "previous_configuration": config,
                    "owner_id": owner,
                },
                controls=["SH-TPR-001"],
            )
            missing = [
                p for p in dependencies if p["provider_id"] in initial["missing_provider_ids"]
            ]
            for provider in missing:
                prepare(provider, backfill + timedelta(minutes=1), fixed)
                review(provider, backfill + timedelta(minutes=5))
            inventory = import_inventory(dependencies, included_roles=["PRIMARY", "RECOVERY"])
            final = reconcile(dependencies, inventory, diligence, reviews)
            emit(
                "coverage_reconciliation",
                "COVERAGE-BACKFILL",
                backfill + timedelta(minutes=6),
                {
                    **final,
                    "initial_report": gap_ref,
                    "backfilled_provider_ids": [p["provider_id"] for p in missing],
                    "historical_gap_retained": True,
                    "third_party_evidence_gaps_closed": False,
                },
            )
            emit(
                "internal_actions",
                "RECONCILE-INTAKE",
                backfill + timedelta(minutes=7),
                {
                    "coverage_report": gap_ref,
                    "owner_id": owner,
                    "status": "LOCAL_QUEUE_RECONCILED_VENDOR_SUPPORT_STILL_PENDING",
                    "onboarding_accepted": False,
                    "remaining_support_status": "NOT_OBTAINED",
                },
            )
            summaries.append(
                {
                    "branch": branch,
                    "initial_registered_providers": initial["registered_providers"],
                    "initial_missing_provider_ids": initial["missing_provider_ids"],
                    "initial_missing_due_review_provider_ids": initial[
                        "missing_due_review_provider_ids"
                    ],
                    "backfilled_provider_ids": [p["provider_id"] for p in missing],
                    "later_missing_provider_ids": final["missing_provider_ids"],
                    "support_obtained": final["diligence_support_obtained"],
                    "onboarding_accepted": False,
                }
            )
        result = {
            "schema": "LOCAL_PLANNED_PROVIDER_INTAKE_PAIR_V1",
            "recipe": asdict(recipe),
            "source_sha256": pins,
            "recipe_sha256": recipe_pin,
            "assignments": assignments,
            "qualification": QUALIFICATION,
            "records": receipts,
            "summaries": summaries,
        }
        path = Path(temp) / "SOURCE_RECEIPT.json"
        path.write_bytes(encoded(result))
        path.chmod(0o600)
        publish(Path(temp), destination)
    return result
