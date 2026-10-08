"""Prospective SH-ENG-005 emergency-change exercise in a new private CompanyStore.

Only inert in-memory configuration changes. No corporate emergency authority,
deployed target, actual 2027 operation, audit command, or task credit is implied.
"""

from __future__ import annotations

import sqlite3
import tempfile
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .company_change_activity import evaluate
from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

CONTROL = "SH-ENG-005"
QUALIFICATION = "FUTURE_LOCAL_EMERGENCY_CHANGE_FIXTURE_NOT_DEPLOYED_OR_AUTHORIZED_OPERATION"
BASELINE = {"timeout_ms": 30, "attempts": 3, "max_total_ms": 120}
CANDIDATE = {"timeout_ms": 40, "attempts": 3, "max_total_ms": 120}


@dataclass(frozen=True)
class EmergencyRecipe:
    company: str
    clean_branch: str
    messy_branch: str
    exercise_id: str
    start_at: str
    local_rule: str


class LocalFixture:
    """In-memory state only; applying it is not a service deployment."""

    def __init__(self):
        self.config = dict(BASELINE)

    def apply_simulated_invalid_bypass(self, config: dict) -> dict:
        if not evaluate(config)["within_local_limit"]:
            raise CompanyStoreError("Inert candidate failed its local arithmetic test")
        before = sha(encoded(self.config))
        self.config = dict(config)
        return {"before_sha256": before, "after_sha256": sha(encoded(self.config))}

    def rollback(self) -> dict:
        before = sha(encoded(self.config))
        self.config = dict(BASELINE)
        return {"before_sha256": before, "after_sha256": sha(encoded(self.config))}


def _recipe(recipe: EmergencyRecipe) -> tuple[datetime, str]:
    if not isinstance(recipe, EmergencyRecipe):
        raise CompanyStoreError("EmergencyRecipe required")
    for value in (recipe.company, recipe.clean_branch, recipe.messy_branch, recipe.exercise_id):
        _id(value)
    if recipe.clean_branch == recipe.messy_branch:
        raise CompanyStoreError("Distinct Clean and Messy source branches required")
    if not isinstance(recipe.local_rule, str) or not 1 <= len(recipe.local_rule.strip()) <= 1000:
        raise CompanyStoreError("Bounded explicit local rule required")
    start = datetime.fromisoformat(_time(recipe.start_at))
    if start.date() <= datetime.now(UTC).date():
        raise CompanyStoreError("This fixture must remain prospective, not historical operation")
    return start, sha(encoded(asdict(recipe)))


def _destination(destination: Path) -> Path:
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in [destination, *destination.parents])
    ):
        raise CompanyStoreError("New source root under private nonsymlink parent required")
    return destination


def generate_pair(destination: Path, *, repository: Path, recipe: EmergencyRecipe) -> dict:
    """Generate separate Clean/Messy native originals before any audit collection."""
    destination = _destination(destination)
    repository = Path(repository)
    start, recipe_sha = _recipe(recipe)
    org = snapshot(repository, as_of=start.date().isoformat())
    assignment = next(a for a in org["control_assignments"] if a["control_id"] == CONTROL)
    operator, reviewer = assignment["primary_person_id"], assignment["operating_reviewer_person_id"]
    if not operator or not reviewer or operator == reviewer:
        raise CompanyStoreError("Distinct scoped contact and management review contact required")
    if (
        assignment["status"] != "PROPOSED_CURRENT_ASSIGNMENT"
        or assignment["reviewer_purpose"] != "INDEPENDENT_ASSURANCE_ONLY"
    ):
        raise CompanyStoreError("Canonical contact qualification changed")
    pins = dict(org["source_sha256"])
    for name in (
        "enterprise/audit_suite/company_emergency_change_activity.py",
        "enterprise/audit_suite/company_change_activity.py",
        "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
        "enterprise/services/source/services.json",
        "enterprise/services/source/runtime_sites_2026-09-11.json",
    ):
        pins[name] = sha((repository / name).read_bytes())
    common = {
        "exercise_id": recipe.exercise_id,
        "boundary_id": "corporate",
        "control_ids": [CONTROL],
        "classification": QUALIFICATION,
        "local_rule": recipe.local_rule,
        "assignment_status": "PROPOSED_CONTACTS_NOT_EMERGENCY_APPROVAL_AUTHORITY",
        "corporate_emergency_authority": "UNVERIFIED_NOT_ASSERTED",
        "review_status": "LOCAL_MANAGEMENT_RECORD_OBSERVATION_NOT_CORPORATE_APPROVAL",
        "target": "IN_MEMORY_REFERENCE_CONFIGURATION_ONLY",
        "service_reference": "SVC-developer",
        "service_status": "CANONICAL_DESIGN_REFERENCE_NOT_DEPLOYMENT",
        "site_status": "RENO_BOISE_REFERENCES_ONLY_NO_SITE_OPERATION",
        "event_clock_status": "FUTURE_AUTHORED_SCENARIO_NOT_ACTUAL_2027_OPERATION_AS_OF_2026_09_29",
    }
    records: list[dict] = []
    with tempfile.TemporaryDirectory(
        prefix="emergency-change-stage-", dir=destination.parent
    ) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        for branch, messy in ((recipe.clean_branch, False), (recipe.messy_branch, True)):
            for system, owner in (
                ("emergency_intake", operator),
                ("emergency_gate", operator),
                ("local_change_state", operator),
                ("retrospective_observation", reviewer),
            ):
                store.register_system(recipe.company, branch, system, owner)
            fixture = LocalFixture()
            previous: dict | None = None

            def emit(system: str, record: str, minute: int, body: dict, branch=branch) -> dict:
                nonlocal previous
                at = (start + timedelta(minutes=minute)).isoformat(timespec="microseconds")
                content = encoded(
                    {
                        **common,
                        "record_id": record,
                        "recorded_at": at,
                        "previous_source": previous,
                        **body,
                    }
                )
                row = store.append_version(
                    recipe.company,
                    branch,
                    system,
                    record,
                    expected_version=0,
                    command_id="EMG-" + sha(encoded([recipe_sha, branch, system, record])),
                    event_at=at,
                    available_at=at,
                    content=content,
                    provenance={
                        "source_reference": recipe.exercise_id,
                        "control_ids": [CONTROL],
                        "classification": QUALIFICATION,
                        "recipe_sha256": recipe_sha,
                        "source_sha256": pins,
                        "operational_fact_status": "LOCAL_FUTURE_FIXTURE_ONLY",
                    },
                )
                previous = {
                    "system": system,
                    "record": record,
                    "version": row["version"],
                    "sha256": row["sha256"],
                }
                records.append(
                    {
                        "branch": branch,
                        "system": system,
                        "record": record,
                        "version": row["version"],
                        "event_at": row["event_at"],
                        "imported_at": row["imported_at"],
                        "sha256": row["sha256"],
                    }
                )
                return row

            emit(
                "emergency_intake",
                "DEFINITION",
                0,
                {
                    "actor": operator,
                    "subject": "LOCAL-TIMEOUT-FIXTURE",
                    "baseline": BASELINE,
                    "candidate": CANDIDATE,
                    "baseline_sha256": sha(encoded(BASELINE)),
                    "candidate_sha256": sha(encoded(CANDIDATE)),
                    "test": evaluate(CANDIDATE),
                    "deployment": False,
                },
            )
            emit(
                "emergency_intake",
                "TRIGGER",
                5,
                {
                    "actor": operator,
                    "trigger": "LOCAL_SIMULATED_TIMEOUT_ALERT",
                    "incident_id": "LOCAL-TRIGGER-001",
                    "actual_incident": False,
                    "source_status": "SELF_CONTAINED_FIXTURE_NO_INCIDENT_QUEUE_CLAIM",
                },
            )
            emit(
                "emergency_intake",
                "REQUEST",
                10,
                {
                    "actor": operator,
                    "incident_id": "LOCAL-TRIGGER-001",
                    "candidate_sha256": sha(encoded(CANDIDATE)),
                    "proposed_window_minutes": 120,
                    "emergency_authority": "NOT_EVIDENCED",
                },
            )
            emit(
                "emergency_gate",
                "AUTHORITY-CHECK",
                11,
                {
                    "actor": operator,
                    "evidence": [],
                    "decision": "NO_ACCEPTED_EMERGENCY_AUTHORITY_FOUND",
                    "contact_assignment_is_approval": False,
                },
            )
            emit(
                "emergency_gate",
                "GATE",
                12,
                {
                    "actor": operator,
                    "decision": "BLOCKED_UNVERIFIED_AUTHORITY",
                    "candidate_local_test_passed": True,
                    "corporate_approval": False,
                },
            )
            if messy:
                emit(
                    "emergency_gate",
                    "INVALID-BYPASS",
                    13,
                    {
                        "actor": operator,
                        "decision": "SIMULATED_INVALID_LOCAL_BYPASS_PENDING_AUTHORITY",
                        "temporary_window_minutes": 120,
                        "corporate_approval": False,
                        "open_exception_id": "LOCAL-ENG005-EXC-001",
                    },
                )
                transition = fixture.apply_simulated_invalid_bypass(CANDIDATE)
                emit(
                    "local_change_state",
                    "LOCAL-APPLY",
                    14,
                    {
                        "actor": operator,
                        "fixture_transition": transition,
                        "applied_config": fixture.config,
                        "deployed": False,
                        "route": "INVALID_BYPASS_IN_MEMORY_ONLY",
                    },
                )
                emit(
                    "local_change_state",
                    "OBSERVATION",
                    15,
                    {
                        "actor": operator,
                        "active_sha256": sha(encoded(fixture.config)),
                        "local_test": evaluate(fixture.config),
                        "actual_service_observation": False,
                    },
                )
                emit(
                    "retrospective_observation",
                    "REVIEW",
                    60,
                    {
                        "actor": reviewer,
                        "finding": "INVALID_BYPASS_BEFORE_AUTHORITY",
                        "decision": "LOCAL_RECORD_QUALITY_OBSERVATION_ONLY",
                        "corporate_retroactive_approval": False,
                        "open_exception_id": "LOCAL-ENG005-EXC-001",
                    },
                )
                rollback = fixture.rollback()
                emit(
                    "local_change_state",
                    "ROLLBACK",
                    90,
                    {
                        "actor": operator,
                        "fixture_transition": rollback,
                        "restored_config": fixture.config,
                        "deployed": False,
                        "open_exception_id": "LOCAL-ENG005-EXC-001",
                    },
                )
            else:
                emit(
                    "local_change_state",
                    "BLOCKED-STATE",
                    14,
                    {
                        "actor": operator,
                        "active_sha256": sha(encoded(fixture.config)),
                        "candidate_applied": False,
                        "deployed": False,
                    },
                )
                emit(
                    "retrospective_observation",
                    "REVIEW",
                    60,
                    {
                        "actor": reviewer,
                        "finding": "LOCAL_GATE_BLOCKED_UNVERIFIED_AUTHORITY",
                        "decision": "LOCAL_RECORD_QUALITY_OBSERVATION_ONLY",
                        "corporate_retroactive_approval": False,
                    },
                )
            emit(
                "local_change_state",
                "FINAL",
                120,
                {
                    "actor": operator,
                    "active_sha256": sha(encoded(fixture.config)),
                    "baseline_restored": fixture.config == BASELINE,
                    "open_exception_ids": ["LOCAL-ENG005-EXC-001"] if messy else [],
                    "deployed": False,
                    "audit_task_credit": False,
                },
            )
        receipt = {
            "schema": "SH_ENG005_LOCAL_EMERGENCY_CHANGE_PAIR_V1",
            "status": "SEALED_PROSPECTIVE_COMPANY_NATIVE_PAIR_NO_AUDIT_CREDIT",
            "recipe": asdict(recipe),
            "recipe_sha256": recipe_sha,
            "source_sha256": pins,
            "organization_snapshot_sha256": org["snapshot_digest"],
            "owner_contact": operator,
            "management_review_contact": reviewer,
            "records": records,
            "record_count": len(records),
            "clean_branch": recipe.clean_branch,
            "messy_branch": recipe.messy_branch,
            "clean_gate": "BLOCKED_UNVERIFIED_AUTHORITY",
            "messy_exception": "LOCAL-ENG005-EXC-001_OPEN_AFTER_IN_MEMORY_ROLLBACK",
            "actual_2027_operation": False,
            "deployed_service_change": False,
            "corporate_emergency_approval_asserted": False,
            "audit_task_credit": False,
            "active_A_B_P1_mutated": False,
        }
        path = stage / "SOURCE_RECEIPT.json"
        path.write_bytes(encoded(receipt))
        path.chmod(0o600)
        with closing(
            sqlite3.connect(
                (stage / "company.sqlite3").resolve().as_uri() + "?mode=ro&immutable=1", uri=True
            )
        ) as db:
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise CompanyStoreError("Staged native store integrity failed")
            if db.execute("SELECT count(*) FROM versions").fetchone()[0] != len(records):
                raise CompanyStoreError("Staged native source count differs")
            if any(
                db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("grants", "collections")
            ):
                raise CompanyStoreError("Source exercise must not grant or collect")
        manifest = {
            "schema": "SH_ENG005_LOCAL_EMERGENCY_CHANGE_RUN_MANIFEST_V1",
            "status": "SEALED_PRIVATE_PROSPECTIVE_SOURCE_ONLY",
            "source_receipt_sha256": sha(path.read_bytes()),
            "native_db_sha256": sha((stage / "company.sqlite3").read_bytes()),
            "source_code_sha256": pins[
                "enterprise/audit_suite/company_emergency_change_activity.py"
            ],
            "record_count": len(records),
            "audit_task_credit": False,
            "active_A_B_P1_mutated": False,
        }
        manifest_path = stage / "RUN-MANIFEST.json"
        manifest_path.write_bytes(encoded(manifest))
        manifest_path.chmod(0o600)
        publish(stage, destination)
    return receipt
