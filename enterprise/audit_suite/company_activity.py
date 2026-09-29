"""One pre-audit paired mover lifecycle, never a corporate personnel amendment."""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot


@dataclass(frozen=True)
class TransferRecipe:
    company_id: str
    clean_branch: str
    messy_branch: str
    event_id: str
    employee_id: str
    effective_at: str
    old_role: str
    new_role: str
    old_right: str
    new_right: str
    old_site: str
    new_site: str


def generate_pair(store: CompanyStore, *, repository: Path, recipe: TransferRecipe):
    """Trusted operator API; no engagement, grants, audit requests or answer records.

    The bounded inventory is one directory, one application and one site-access
    system. This does not imply every real company system has been reconciled.
    """
    for name, value in asdict(recipe).items():
        if not isinstance(value, str) or not value.strip() or len(value) > 200:
            raise CompanyStoreError(f"Explicit bounded {name} required")
    for value in (
        recipe.company_id,
        recipe.clean_branch,
        recipe.messy_branch,
        recipe.event_id,
        recipe.employee_id,
    ):
        _id(value)
    if recipe.clean_branch == recipe.messy_branch:
        raise CompanyStoreError("Distinct isolated branch identifiers required")
    if any(
        a == b
        for a, b in [
            (recipe.old_role, recipe.new_role),
            (recipe.old_right, recipe.new_right),
            (recipe.old_site, recipe.new_site),
        ]
    ):
        raise CompanyStoreError("Transfer must change role, rights and site access")
    effective = datetime.fromisoformat(_time(recipe.effective_at))
    org = snapshot(repository, as_of=effective.date().isoformat())
    employees = {p["person_id"]: p for p in org["canonical_people"]}
    if (
        recipe.employee_id not in employees
        or employees[recipe.employee_id]["status"] != "current_employee"
    ):
        raise CompanyStoreError("Existing current canonical employee identity required")
    assignments = {a["control_id"]: a for a in org["control_assignments"]}
    iam, ppl = assignments["SH-IAM-003"], assignments["SH-PPL-002"]
    owner, reviewer, hr = (
        iam["primary_person_id"],
        iam["operating_reviewer_person_id"],
        ppl["primary_person_id"],
    )
    if len({owner, reviewer, hr, recipe.employee_id}) != 4:
        raise CompanyStoreError("Employee and scoped operational actors must be distinct")
    pins = dict(org["source_sha256"])
    for path in [
        "enterprise/ccf/assurance/design_data/control_procedures.json",
        "enterprise/audit_suite/organization.py",
        "enterprise/audit_suite/company_activity.py",
    ]:
        pins[path] = sha((repository / path).read_bytes())
    common = {
        "cause_id": recipe.event_id,
        "person_id": recipe.employee_id,
        "origin": "FICTIONAL_OPERATIONAL_SCENARIO_NOT_CANON_PERSONNEL_CHANGE",
        "control_reference": "SH-IAM-003",
        "assumptions": {
            "roles_and_rights": "Explicit local scenario assignments, not accepted appointments",
            "connected_system_inventory": ["directory", "application", "site_access"],
            "scope_limit": "One mover and three declared access systems only",
            "custody_basis": "Existing scoped contacts, provisional local operational roles",
        },
    }
    provenance = {
        "source_reference": recipe.event_id,
        "source_sha256": pins,
        "source_revision": org["source_revision"],
        "assignment_status": iam["status"],
        "recipe_sha256": sha(encoded(asdict(recipe))),
    }
    system_owners = {
        "hr": hr,
        "directory": owner,
        "application": owner,
        "site_access": owner,
        "access_review": reviewer,
    }
    results = {}
    for branch, omit_old_app in [(recipe.clean_branch, False), (recipe.messy_branch, True)]:
        records = []

        def add(system, offset, payload, *, version=1, records=records):
            timestamp = (effective + timedelta(minutes=offset)).isoformat()
            content = {
                **common,
                "record_id": f"{recipe.event_id}-{system}",
                "recorded_at": timestamp,
                **payload,
            }
            records.append((system, version, timestamp, content))

        add("hr", -1440, {"role": recipe.old_role, "employment_status": "ACTIVE"})
        add("directory", -1440, {"groups": [recipe.old_right], "account_status": "ENABLED"})
        add("application", -1440, {"rights": [recipe.old_right], "account_status": "ENABLED"})
        add("site_access", -1440, {"sites": [recipe.old_site], "credential_status": "ENABLED"})
        approval = {
            "approval_id": f"{recipe.event_id}-APPROVAL",
            "approved_by": reviewer,
            "approved_at": (effective - timedelta(minutes=60)).isoformat(),
            "effective_at": effective.isoformat(),
            "remove_right": recipe.old_right,
            "add_right": recipe.new_right,
            "remove_site": recipe.old_site,
            "add_site": recipe.new_site,
            "requested_by": hr,
        }
        add(
            "hr",
            -60,
            {
                "role": recipe.old_role,
                "employment_status": "ACTIVE",
                "pending_transfer": {"new_role": recipe.new_role, **approval},
            },
            version=2,
        )
        add(
            "hr",
            0,
            {
                "role": recipe.new_role,
                "employment_status": "ACTIVE",
                "transfer_authorization": approval,
            },
            version=3,
        )
        add(
            "directory",
            1,
            {
                "groups": [recipe.new_right],
                "account_status": "ENABLED",
                "authorization_id": approval["approval_id"],
                "performed_by": owner,
            },
            version=2,
        )
        app_rights = [recipe.old_right, recipe.new_right] if omit_old_app else [recipe.new_right]
        add(
            "application",
            2,
            {
                "rights": app_rights,
                "account_status": "ENABLED",
                "authorization_id": approval["approval_id"],
                "performed_by": owner,
            },
            version=2,
        )
        add(
            "site_access",
            3,
            {
                "sites": [recipe.new_site],
                "credential_status": "ENABLED",
                "authorization_id": approval["approval_id"],
                "performed_by": owner,
            },
            version=2,
        )
        add(
            "access_review",
            10,
            {
                "reviewed_by": reviewer,
                "purpose": "Operational post-transfer reconciliation",
                "authorization_id": approval["approval_id"],
                "observed_versions": {"hr": 3, "directory": 2, "application": 2, "site_access": 2},
                "observed_application_rights": app_rights,
                "authorized_rights": [recipe.new_right],
                "unapproved_remaining_rights": sorted(set(app_rights) - {recipe.new_right}),
                "followup_owner": owner if omit_old_app else None,
                "followup_status": "REMOVAL_REQUESTED"
                if omit_old_app
                else "NO_DIFFERENCE_OBSERVED",
            },
        )
        # Build/validate all source content before the first append in this branch.
        for system, _, _, _ in records:
            store.register_system(recipe.company_id, branch, system, system_owners[system])
        receipts = []
        for system, version, timestamp, content in records:
            receipts.append(
                store.append_version(
                    recipe.company_id,
                    branch,
                    system,
                    content["record_id"],
                    expected_version=version - 1,
                    command_id="ACT-"
                    + sha(encoded([recipe.company_id, branch, recipe.event_id, system, version])),
                    event_at=timestamp,
                    available_at=timestamp,
                    content=encoded(content),
                    provenance=provenance,
                )
            )
        results[branch] = receipts
    return {
        "recipe_sha256": provenance["recipe_sha256"],
        "source_sha256": pins,
        "branches": results,
        "audit_created": False,
        "grants_created": False,
        "professional_validation": "NOT_PERFORMED",
    }
