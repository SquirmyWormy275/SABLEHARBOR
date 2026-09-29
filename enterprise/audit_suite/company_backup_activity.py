"""Computed local backup/restore exercise sources, independent of any audit."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot


@dataclass(frozen=True)
class BackupRecipe:
    company_id: str
    clean_branch: str
    messy_branch: str
    exercise_id: str
    service_id: str
    period_start: str
    period_end_exclusive: str
    first_job_at: str


def generate_backup_pair(store: CompanyStore, *, repository: Path, recipe: BackupRecipe):
    """Two daily checkpoints and an isolated restore/retest of actual small JSON bytes.

    A local write-credential expiry causes the second branch's missed checkpoint.
    Dataset versions, copied objects and restored originals are separate source rows.
    No corpus, audit mode, expected answer or audit execution is used.
    """
    for value in (recipe.company_id, recipe.clean_branch, recipe.messy_branch, recipe.exercise_id):
        _id(value)
    if recipe.clean_branch == recipe.messy_branch:
        raise CompanyStoreError("Distinct isolated branches required")
    start, end, first = [
        datetime.fromisoformat(_time(v))
        for v in (recipe.period_start, recipe.period_end_exclusive, recipe.first_job_at)
    ]
    if not start <= first - timedelta(days=1) < first + timedelta(days=2) < end:
        raise CompanyStoreError("Inventory and two-day backup exercise must fit the period")
    service_data = json.loads(
        (repository / "enterprise/services/source/services.json").read_bytes()
    )
    if recipe.service_id != "SVC-compute" or not any(
        row[0] == recipe.service_id for row in service_data["services"]
    ):
        raise CompanyStoreError("Reference exercise requires canonical compute service")
    site_data = json.loads(
        (repository / "enterprise/services/source/runtime_sites_2026-09-11.json").read_bytes()
    )
    sites = {s["id"]: s for s in site_data["sites"]}
    org = snapshot(repository, as_of=start.date().isoformat())
    assignments = {r["control_id"]: r for r in org["control_assignments"]}
    operator = assignments["SH-BCM-003"]["primary_person_id"]
    reviewer = assignments["SH-BCM-003"]["operating_reviewer_person_id"]
    if operator == reviewer:
        raise CompanyStoreError("Separate restore operator and service review contact required")
    pins = dict(org["source_sha256"])
    for path in (
        "enterprise/ccf/assurance/design_data/control_procedures.json",
        "enterprise/services/source/services.json",
        "enterprise/services/source/runtime_sites_2026-09-11.json",
        "docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md",
        "docs/internal/development/CCF_ASSURANCE_SCOPE_PROPOSAL_2026-09-11.md",
        "enterprise/audit_suite/company_backup_activity.py",
    ):
        pins[path] = sha((repository / path).read_bytes())
    common = {
        "exercise_id": recipe.exercise_id,
        "service_id": recipe.service_id,
        "boundary_id": "corporate",
        "classification": "FICTIONAL_REFERENCE_EXERCISE_NOT_DEPLOYMENT",
        "source_period_start": start.isoformat(),
        "source_period_end": end.isoformat(),
        "sites": [
            {
                "id": sites[key]["id"],
                "facility_id": sites[key]["facility_id"],
                "canonical_operating": sites[key]["operating"],
                "canonical_status": sites[key]["status"],
            }
            for key in ("RUNTIME-RENO-COLO", "RUNTIME-BOISE-DR")
        ],
        "data_scope": "Small synthetic nonpersonal application rows; no PHI/ePHI processing",
        "authority_basis": "Scoped exercise contacts; no appointment or deployment acceptance",
        "policy_basis": (
            "Local fictional schedule/retention/targets; not approved corporate BIA/RPO/RTO"
        ),
    }
    dataset_id = recipe.exercise_id + "-DATA"
    records = [{"id": "OBJ-01", "setting": "blue"}, {"id": "OBJ-02", "setting": "green"}]
    # The second source snapshot changes an existing object and introduces a new one.
    first_bytes = encoded({**common, "dataset_id": dataset_id, "records": records})
    second_bytes = encoded(
        {
            **common,
            "dataset_id": dataset_id,
            "records": [
                records[0],
                {"id": "OBJ-02", "setting": "amber"},
                {"id": "OBJ-03", "setting": "silver"},
            ],
        }
    )
    owners = {
        name: operator
        for name in (
            "inventory",
            "schedule",
            "source_dataset",
            "credential_event",
            "backup_job",
            "backup_object",
            "catalogue",
            "failure_ticket",
            "restore_selection",
            "restored_dataset",
            "reconciliation",
            "remediation",
            "review",
        )
    }
    owners["inventory"] = owners["review"] = reviewer
    rows = []

    def build_branch(branch, expires):
        created, versions = {}, {}

        def stamp(minutes):
            return (first + timedelta(minutes=minutes)).isoformat()

        def add(system, minute, body=None, links=(), raw=None):
            version = versions.get(system, 0) + 1
            versions[system] = version
            refs = [
                {
                    "system": s,
                    "record": created[s, v]["record"],
                    "version": v,
                    "sha256": created[s, v]["sha256"],
                }
                for s, v in links
            ]
            content = (
                raw
                if raw is not None
                else encoded({**common, "recorded_at": stamp(minute), "source_refs": refs, **body})
            )
            row = {
                "branch": branch,
                "system": system,
                "record": recipe.exercise_id + "-" + system,
                "version": version,
                "event_at": stamp(minute),
                "content": content,
                "sha256": sha(content),
                "provenance": {
                    **common,
                    "source_sha256": pins,
                    "recipe_sha256": sha(encoded(asdict(recipe))),
                    "source_reference": recipe.exercise_id,
                    "name": system + ".json",
                    "mime": "application/json",
                    "source_refs": refs,
                    "control_ids": ["SH-BCM-002", "SH-BCM-003"],
                },
            }
            created[system, version] = row
            rows.append(row)
            return system, version

        inventory = add(
            "inventory",
            -1440,
            {
                "maintained_by": reviewer,
                "datasets": [
                    {
                        "dataset_id": dataset_id,
                        "criticality": "LOCAL_EXERCISE_RECOVERY_DEPENDENCY",
                        "source_system": "LOCAL-APP",
                        "recovery_path": "LOCAL-ISOLATED-JSON-COPY",
                        "selection_rationale": (
                            "Application requires every configured object and its setting"
                        ),
                    }
                ],
            },
        )
        add(
            "schedule",
            -1439,
            {
                "dataset_id": dataset_id,
                "scheduled_at": [stamp(0), stamp(1440)],
                "cadence_minutes": 1440,
                "local_max_checkpoint_age_minutes": 1440,
                "local_restore_duration_limit_minutes": 30,
                "retention_days": 7,
                "retention_enforcement": "CONFIGURATION_ONLY_NOT_LONG_TERM_TESTED",
                "backup_writer": operator,
                "restore_operator": operator,
                "restore_target": "LOCAL-ISOLATED-RESTORE",
                "network_route_to_production": False,
                "backup_delete_permission": False,
            },
            [inventory],
        )
        source1 = add("source_dataset", -10, raw=first_bytes, links=[inventory])
        latest_object, latest_cutoff = None, None
        credential = add(
            "credential_event",
            -5,
            {
                "principal": operator,
                "operation": "BACKUP_OBJECT_WRITE",
                "permission_state": "GRANTED",
            },
        )

        def job(minute, source, permission, ticket=False):
            nonlocal latest_object, latest_cutoff
            credential_body = json.loads(created[permission]["content"])
            allowed = credential_body["permission_state"] == "GRANTED"
            source_row = created[source]
            job_ref = add(
                "backup_job",
                minute + 2,
                {
                    "job_id": recipe.exercise_id + f"-JOB-{minute}",
                    "dataset_id": dataset_id,
                    "started_at": stamp(minute),
                    "ended_at": stamp(minute + 2),
                    "state": "COMPLETED" if allowed else "FAILED",
                    "error_code": None if allowed else "OBJECT_WRITE_CREDENTIAL_EXPIRED",
                    "source_sha256": source_row["sha256"],
                    "copied_bytes": len(source_row["content"]) if allowed else 0,
                },
                [source, permission, ("schedule", 1)],
            )
            if allowed:
                latest_object = add(
                    "backup_object",
                    minute + 2,
                    raw=bytes(source_row["content"]),
                    links=[job_ref, source],
                )
                latest_cutoff = minute
            add(
                "catalogue",
                minute + 3,
                {
                    "dataset_id": dataset_id,
                    "checkpoint_at": stamp(latest_cutoff),
                    "object_sha256": created[latest_object]["sha256"],
                    "latest_job_state": "COMPLETED" if allowed else "FAILED",
                },
                [job_ref, latest_object, inventory],
            )
            if ticket:
                add(
                    "failure_ticket",
                    minute + 4,
                    {
                        "job_id": recipe.exercise_id + f"-JOB-{minute}",
                        "state": "OPEN" if not allowed else "NO_FAILED_RUN_RECORDED",
                        "assigned_to": operator,
                        "required_action": "Inspect job/credential record before next checkpoint",
                    },
                    [job_ref],
                )

        job(0, source1, credential)
        source2 = add("source_dataset", 1430, raw=second_bytes, links=[source1])
        permission = add(
            "credential_event",
            1435,
            {
                "principal": operator,
                "operation": "BACKUP_OBJECT_WRITE",
                "permission_state": "EXPIRED" if expires else "GRANTED",
                "basis": "Explicit local credential lease event",
            },
            [credential],
        )
        job(1440, source2, permission, ticket=True)

        def restore(minute):
            selected = latest_object
            selected_row = created[selected]
            choice = add(
                "restore_selection",
                minute,
                {
                    "selected_by": operator,
                    "dataset_id": dataset_id,
                    "rule": "Latest successfully catalogued checkpoint available at restore start",
                    "checkpoint_at": stamp(latest_cutoff),
                    "target": "LOCAL-ISOLATED-RESTORE",
                    "reason": (
                        "Exercise full configured object set from independent source inventory"
                    ),
                },
                [inventory, ("catalogue", versions["catalogue"]), selected],
            )
            restored = bytes(selected_row["content"])
            restored_ref = add(
                "restored_dataset", minute + 10, raw=restored, links=[choice, selected]
            )
            expected = {r["id"]: r for r in json.loads(created[source2]["content"])["records"]}
            actual = {r["id"]: r for r in json.loads(restored)["records"]}
            reconciliation = add(
                "reconciliation",
                minute + 11,
                {
                    "performed_by": operator,
                    "started_at": stamp(minute),
                    "finished_at": stamp(minute + 10),
                    "duration_minutes": 10,
                    "checkpoint_age_at_restore_start_minutes": minute - latest_cutoff,
                    "restore_sha256": sha(restored),
                    "selected_object_sha256": selected_row["sha256"],
                    "byte_copy_matches_selected_object": restored == selected_row["content"],
                    "source_row_count": len(expected),
                    "restored_row_count": len(actual),
                    "missing_ids": sorted(expected.keys() - actual.keys()),
                    "unexpected_ids": sorted(actual.keys() - expected.keys()),
                    "changed_ids": sorted(
                        k for k in expected.keys() & actual.keys() if expected[k] != actual[k]
                    ),
                    "usability_check": (
                        "Exact object ID and setting equality only; no "
                        "production application acceptance"
                    ),
                },
                [source2, restored_ref, choice],
            )
            add(
                "review",
                minute + 12,
                {
                    "reviewed_by": reviewer,
                    "procedure": (
                        "Compare source and restored JSON IDs/settings, "
                        "copy hashes and measured times"
                    ),
                    "professional_qualification": "NOT_ASSERTED",
                    "whole_control_effectiveness": "NOT_ASSESSED",
                },
                [reconciliation, inventory],
            )

        restore(1480)
        remediation = add(
            "remediation",
            1550,
            {
                "performed_by": operator,
                "action": (
                    "Reconfirm local write grant and take a new "
                    "checkpoint before repeating isolated restore"
                ),
                "historical_results_superseded": False,
            },
            [("failure_ticket", 1), ("review", 1)],
        )
        repaired = add(
            "credential_event",
            1551,
            {
                "principal": operator,
                "operation": "BACKUP_OBJECT_WRITE",
                "permission_state": "GRANTED",
            },
            [permission, remediation],
        )
        job(1560, source2, repaired)
        restore(1580)

    build_branch(recipe.clean_branch, False)
    build_branch(recipe.messy_branch, True)
    expected = {(r["branch"], r["system"], r["record"], r["version"]): r for r in rows}
    # Validate any resume completely before appending, including content and source pins.
    with store._db() as db:
        for old in db.execute("SELECT * FROM versions"):
            row = expected.get((old["branch"], old["system"], old["record"], old["version"]))
            if (
                old["company"] != recipe.company_id
                or row is None
                or any(
                    (
                        old["content"] != row["content"],
                        old["sha256"] != row["sha256"],
                        old["event_at"] != _time(row["event_at"]),
                        old["available_at"] != _time(row["event_at"]),
                        old["origin"] != "AUTHORED_TRAINING_SOURCE",
                        json.loads(old["provenance"]) != row["provenance"],
                    )
                )
            ):
                raise CompanyStoreError("Dedicated empty or exact-replay source store required")
    for branch in (recipe.clean_branch, recipe.messy_branch):
        for system, owner in owners.items():
            store.register_system(recipe.company_id, branch, system, owner)
    receipts = [
        store.append_version(
            recipe.company_id,
            row["branch"],
            row["system"],
            row["record"],
            expected_version=row["version"] - 1,
            command_id="BCM-"
            + sha(encoded([recipe.company_id, row["branch"], row["record"], row["version"]])),
            event_at=row["event_at"],
            available_at=row["event_at"],
            content=row["content"],
            provenance=row["provenance"],
        )
        for row in rows
    ]
    return {
        "source_versions": len(receipts),
        "receipts": receipts,
        "source_sha256": pins,
        "recipe_sha256": sha(encoded(asdict(recipe))),
        "audit_created": False,
        "grants_created": False,
        "professional_validation": "UNVALIDATED",
        "gaps": [
            "One explicitly inventoried synthetic dataset; no enterprise inventory completeness.",
            (
                "Local JSON copies exercise lineage/reconciliation, not "
                "encryption or physical offsite infrastructure."
            ),
            (
                "Retention configured only; no seven-day expiry, immutable "
                "storage or production restoration tested."
            ),
            "Targets are local assumptions, not approved corporate BIA/RPO/RTO.",
            "No deployment, PHI processing or whole-control effectiveness claim.",
        ],
    }
