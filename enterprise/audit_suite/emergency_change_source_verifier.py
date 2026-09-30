"""Read-only physical-source and four-route gap check for selected SH-ENG-005.

This is a local future fixture, not emergency authority, deployment, audit
evidence or task performance. It never generates/updates company source rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import stat
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from enterprise.ccf.registry import digest as registry_digest

from .company_emergency_change_activity import BASELINE, CANDIDATE, CONTROL, QUALIFICATION
from .company_store import CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot

SCHEMA = "SH_ENG005_SELECTED_PHYSICAL_SOURCE_GAP_CHECK_V1"
AS_OF = "2026-09-29"
RUN_REL = "enterprise/generated/audit-suite/company-emergency-change-2027-simulation-2026-09-29"
MATRIX_REL = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/run-v2/MATRIX.json"
)
MATRIX_REVIEW_REL = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/"
    "independent-review-v2/REVIEW.json"
)
RAW_REVIEW_REL = f"{RUN_REL}/independent-raw-review-v1/REVIEW.json"
PRIVATE_PINS = {
    f"{RUN_REL}/RECIPE.json": ("5443a2843490e3265ee43b3769baf0aaf4fe9c2544378c283c3f3bc3efc302da"),
    f"{RUN_REL}/run-v1/RUN-MANIFEST.json": (
        "a941aff10990a59bbd964c88e3029006c02b726ec55f2f37a3c44bf6794bd9ad"
    ),
    f"{RUN_REL}/run-v1/SOURCE_RECEIPT.json": (
        "efa67bb2cf9934a62e91ea51b109e61f2954bbb8b83ef84e2c5f1e6f344d78d9"
    ),
    f"{RUN_REL}/run-v1/company.sqlite3": (
        "123599b469c7d5799fd1c068739e76c7e73501c5e2bb8cac6170205ee53a64a0"
    ),
    MATRIX_REL: "e9477d2074bebce185e412a3ee7c424ded395c1a1128a7c918a94f6acbd1e327",
    MATRIX_REVIEW_REL: "c4064f6217c0e7f69276adc71004d6da7971867ccf3d844a3e198145cec31ace",
    RAW_REVIEW_REL: "5d8999d202960af789857c877af03ef8e93e22ce0d59ac09ce5f64ada12e052a",
}
RECIPE_SHA256 = "a670db8d887005ffff7b68c15c80573ef8980b9eb5a9454293a3fd06e08fe8fc"
ORG_MODULE_SHA256 = "1e822632917f739b40c1bd064aac49b633dc643b5930ef74dbc19887bec729d4"
SNAPSHOT_SHA256 = "5753f67ac0509cbc3f0512461a2ec541862c98b55366427bd98215665d38bfaf"
SOURCE_REVISION = "b03ea3867cda05d5493310978d912c82454bfd23"
EXPECTED_RECIPE = {
    "company": "SABLE-HARBOR-REFERENCE",
    "clean_branch": "ENG005-CLEAN",
    "messy_branch": "ENG005-MESSY",
    "exercise_id": "ENG005-SELECTED-2027-001",
    "start_at": "2027-04-10T09:00:00+00:00",
    "local_rule": (
        "Block changes without evidenced emergency authority; preserve any invalid "
        "local bypass, rollback, and open exception without retroactive approval."
    ),
}
COMMON = (
    ("emergency_intake", "DEFINITION", 0),
    ("emergency_intake", "TRIGGER", 5),
    ("emergency_intake", "REQUEST", 10),
    ("emergency_gate", "AUTHORITY-CHECK", 11),
    ("emergency_gate", "GATE", 12),
)
CLEAN_END = (
    ("local_change_state", "BLOCKED-STATE", 14),
    ("retrospective_observation", "REVIEW", 60),
    ("local_change_state", "FINAL", 120),
)
MESSY_END = (
    ("emergency_gate", "INVALID-BYPASS", 13),
    ("local_change_state", "LOCAL-APPLY", 14),
    ("local_change_state", "OBSERVATION", 15),
    ("retrospective_observation", "REVIEW", 60),
    ("local_change_state", "ROLLBACK", 90),
    ("local_change_state", "FINAL", 120),
)
GAP_LIMITS = {
    "ADDITIONAL_DUTY": (
        "Selected local timeout fixture shows request, arithmetic test, blocked authority, "
        "and in Messy an invalid bypass/rollback.",
        "No normal/emergency deployed change population, accepted independent approval, "
        "security test, deployment verification or authorized emergency route.",
    ),
    "IMPLEMENTATION": (
        "Future local in-memory change and negative authority gate only.",
        "No deployed company-native target, accepted service owner, effective control "
        "configuration or operating decision.",
    ),
    "TOD": (
        "One local rule, blocked gate, proposed contacts and exception path "
        "can inform design review.",
        "No accepted corporate emergency authority, implemented service boundary, normal "
        "change path, frequency, independent approver or complete decision criteria.",
    ),
    "TOE": (
        "Exact 8 Clean/11 Messy future local versions have event, availability and import clocks.",
        "No complete period change population/sample, actual execution, ordinary audit "
        "collection or re-performed authorized approval/deployment.",
    ),
}
EXPECTED_TASK_IDS = {
    "TASK-SH-ENG-005-corporate-CHECK-SOC2:CC8.1",
    "TASK-SH-ENG-005-corporate-IMPLEMENTATION",
    "TASK-SH-ENG-005-corporate-TOD",
    "TASK-SH-ENG-005-corporate-TOE",
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private(path: Path, *, directory: bool = False) -> tuple:
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise CompanyStoreError("Emergency source path alias forbidden")
    info = path.stat()
    if info.st_mode & 0o077 or not (
        stat.S_ISDIR(info.st_mode)
        if directory
        else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    ):
        raise CompanyStoreError("Ordinary private emergency source required")
    return (info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode), info.st_size, info.st_mtime_ns)


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise CompanyStoreError("Emergency source JSON object required")
    return value


def _routes(matrix: dict) -> dict:
    result = {}
    for side in "AB":
        controls = [
            c
            for family in matrix["sides"][side]["families"]
            for c in family["controls"]
            if c["control_id"] == CONTROL
        ]
        if len(controls) != 1 or len(controls[0]["tasks"]) != 4:
            raise CompanyStoreError("Frozen four-route SH-ENG-005 cohort differs")
        rows = []
        for task in controls[0]["tasks"]:
            if (
                task["current_status"] != "NOT_STARTED"
                or task["current_conclusion"] != "NOT_RUN"
                or task["task_credit"] is not False
                or task["procedure_type"] not in GAP_LIMITS
            ):
                raise CompanyStoreError("Frozen emergency task gate differs")
            context, limit = GAP_LIMITS[task["procedure_type"]]
            rows.append(
                {
                    "side": side,
                    "task_id": task["task_id"],
                    "procedure_type": task["procedure_type"],
                    "authored_test_clause": task["authored_test_clause"],
                    "remaining_test_gate": task["remaining_test_gate"],
                    "candidate_local_context": context,
                    "unsupported_clause": limit,
                    "current_status": "NOT_STARTED",
                    "current_conclusion": "NOT_RUN",
                    "task_credit": False,
                }
            )
        if {r["task_id"] for r in rows} != EXPECTED_TASK_IDS or sum(
            r["procedure_type"] == "ADDITIONAL_DUTY" for r in rows
        ) != 1:
            raise CompanyStoreError("Exact emergency route IDs differ")
        result[side] = rows
    return result


def _check_bodies(bodies: dict, receipt: dict) -> None:
    clean, messy = receipt["clean_branch"], receipt["messy_branch"]

    def item(branch, record):
        return bodies[(branch, record)]

    baseline, candidate = sha(encoded(BASELINE)), sha(encoded(CANDIDATE))
    for branch in (clean, messy):
        definition = item(branch, "DEFINITION")
        if (
            definition["baseline"] != BASELINE
            or definition["candidate"] != CANDIDATE
            or definition["baseline_sha256"] != baseline
            or definition["candidate_sha256"] != candidate
            or definition["deployment"] is not False
        ):
            raise CompanyStoreError("Emergency fixture definition differs")
        if (
            item(branch, "TRIGGER")["actual_incident"] is not False
            or item(branch, "REQUEST")["emergency_authority"] != "NOT_EVIDENCED"
        ):
            raise CompanyStoreError("Emergency trigger/request claims authority or incident")
        if (
            item(branch, "AUTHORITY-CHECK")["decision"] != "NO_ACCEPTED_EMERGENCY_AUTHORITY_FOUND"
            or item(branch, "AUTHORITY-CHECK")["contact_assignment_is_approval"] is not False
        ):
            raise CompanyStoreError("Emergency authority screening differs")
        if (
            item(branch, "GATE")["decision"] != "BLOCKED_UNVERIFIED_AUTHORITY"
            or item(branch, "GATE")["corporate_approval"] is not False
        ):
            raise CompanyStoreError("Emergency corporate gate was promoted")
        review = item(branch, "REVIEW")
        if (
            review["actor"] != receipt["management_review_contact"]
            or review["decision"] != "LOCAL_RECORD_QUALITY_OBSERVATION_ONLY"
            or review["corporate_retroactive_approval"] is not False
        ):
            raise CompanyStoreError("Local review became corporate approval")
        final = item(branch, "FINAL")
        if (
            final["baseline_restored"] is not True
            or final["deployed"] is not False
            or final["active_sha256"] != baseline
            or final["audit_task_credit"] is not False
        ):
            raise CompanyStoreError("Emergency final state or credit differs")
    if (
        item(clean, "BLOCKED-STATE")["candidate_applied"] is not False
        or item(clean, "FINAL")["open_exception_ids"] != []
    ):
        raise CompanyStoreError("Clean blocked state differs")
    bypass = item(messy, "INVALID-BYPASS")
    if (
        bypass["decision"] != "SIMULATED_INVALID_LOCAL_BYPASS_PENDING_AUTHORITY"
        or bypass["corporate_approval"] is not False
        or bypass["open_exception_id"] != "LOCAL-ENG005-EXC-001"
    ):
        raise CompanyStoreError("Messy invalid bypass was concealed")
    applied, observed, rolled = (
        item(messy, name) for name in ("LOCAL-APPLY", "OBSERVATION", "ROLLBACK")
    )
    if (
        applied["deployed"] is not False
        or applied["fixture_transition"] != {"before_sha256": baseline, "after_sha256": candidate}
        or applied["route"] != "INVALID_BYPASS_IN_MEMORY_ONLY"
        or observed["active_sha256"] != candidate
        or observed["actual_service_observation"] is not False
        or rolled["deployed"] is not False
        or rolled["fixture_transition"] != {"before_sha256": candidate, "after_sha256": baseline}
        or rolled["open_exception_id"] != "LOCAL-ENG005-EXC-001"
        or item(messy, "FINAL")["open_exception_ids"] != ["LOCAL-ENG005-EXC-001"]
    ):
        raise CompanyStoreError("Messy in-memory rollback or open exception differs")


def verify(repository: Path, *, private_repository: Path) -> dict:
    """Reperform frozen native tuples and explicit gaps without any write."""
    repository, private_repository = (
        Path(repository).resolve(strict=True),
        Path(private_repository).resolve(strict=True),
    )
    run = private_repository / RUN_REL / "run-v1"
    _private(private_repository / RUN_REL, directory=True)
    _private(run, directory=True)
    _private(private_repository / RUN_REL / "independent-raw-review-v1", directory=True)
    paths = {name: private_repository / name for name in PRIVATE_PINS}
    identities = {}
    for name, path in paths.items():
        identities[name] = (_private(path), _digest(path))
        if identities[name][1] != PRIVATE_PINS[name]:
            raise CompanyStoreError(f"Pinned emergency input differs: {name}")
    db_path = run / "company.sqlite3"
    if any(
        Path(str(db_path) + suffix).exists() or Path(str(db_path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Emergency native database has SQLite sidecar")
    recipe = _load_json(private_repository / RUN_REL / "RECIPE.json")
    receipt = _load_json(run / "SOURCE_RECEIPT.json")
    manifest = _load_json(run / "RUN-MANIFEST.json")
    if (
        recipe != EXPECTED_RECIPE
        or receipt["recipe"] != recipe
        or sha(encoded(recipe)) != RECIPE_SHA256
        or receipt["recipe_sha256"] != RECIPE_SHA256
    ):
        raise CompanyStoreError("Exact emergency recipe differs")
    start = datetime.fromisoformat(_time(recipe["start_at"]))
    if start.date().isoformat() <= AS_OF:
        raise CompanyStoreError("Emergency source is not future-fictional as authored")
    if _digest(repository / "enterprise/audit_suite/organization.py") != ORG_MODULE_SHA256:
        raise CompanyStoreError("Organization authority interpreter changed")
    source_pins = receipt["source_sha256"]
    if len(source_pins) != 35 or any(
        not (repository / name).is_file()
        or (repository / name).is_symlink()
        or _digest(repository / name) != digest
        for name, digest in source_pins.items()
    ):
        raise CompanyStoreError("Emergency producer/canon source pin differs")
    org = snapshot(repository, as_of=start.date().isoformat())
    assignment = next(a for a in org["control_assignments"] if a["control_id"] == CONTROL)
    org.pop("snapshot_digest")
    org["source_revision"] = SOURCE_REVISION
    if (
        registry_digest(org) != SNAPSHOT_SHA256
        or receipt["organization_snapshot_sha256"] != SNAPSHOT_SHA256
        or not all(source_pins.get(key) == value for key, value in org["source_sha256"].items())
        or receipt["owner_contact"] != assignment["primary_person_id"]
        or receipt["management_review_contact"] != assignment["operating_reviewer_person_id"]
        or assignment["status"] != "PROPOSED_CURRENT_ASSIGNMENT"
        or assignment["reviewer_purpose"] != "INDEPENDENT_ASSURANCE_ONLY"
    ):
        raise CompanyStoreError("Emergency proposed contact authority differs")
    if manifest != {
        "schema": "SH_ENG005_LOCAL_EMERGENCY_CHANGE_RUN_MANIFEST_V1",
        "status": "SEALED_PRIVATE_PROSPECTIVE_SOURCE_ONLY",
        "source_receipt_sha256": PRIVATE_PINS[f"{RUN_REL}/run-v1/SOURCE_RECEIPT.json"],
        "native_db_sha256": PRIVATE_PINS[f"{RUN_REL}/run-v1/company.sqlite3"],
        "source_code_sha256": source_pins[
            "enterprise/audit_suite/company_emergency_change_activity.py"
        ],
        "record_count": 19,
        "audit_task_credit": False,
        "active_A_B_P1_mutated": False,
    }:
        raise CompanyStoreError("Emergency run manifest differs")
    if (
        receipt["schema"] != "SH_ENG005_LOCAL_EMERGENCY_CHANGE_PAIR_V1"
        or receipt["status"] != "SEALED_PROSPECTIVE_COMPANY_NATIVE_PAIR_NO_AUDIT_CREDIT"
        or receipt["record_count"] != 19
        or receipt["clean_branch"] == receipt["messy_branch"]
        or receipt["owner_contact"] == receipt["management_review_contact"]
        or receipt["clean_gate"] != "BLOCKED_UNVERIFIED_AUTHORITY"
        or receipt["messy_exception"] != "LOCAL-ENG005-EXC-001_OPEN_AFTER_IN_MEMORY_ROLLBACK"
        or any(
            receipt[k] is not False
            for k in (
                "actual_2027_operation",
                "deployed_service_change",
                "corporate_emergency_approval_asserted",
                "audit_task_credit",
                "active_A_B_P1_mutated",
            )
        )
    ):
        raise CompanyStoreError("Emergency source receipt claims operation or credit")
    matrix = _load_json(private_repository / MATRIX_REL)
    review = _load_json(private_repository / MATRIX_REVIEW_REL)
    raw_review = _load_json(private_repository / RAW_REVIEW_REL)
    if review.get("verdict") != "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION":
        raise CompanyStoreError("Frozen matrix lacks independent review")
    if (
        raw_review.get("verdict") != "PASS_RAW_PROSPECTIVE_SOURCE_ONLY_NOT_REGISTRY_READY"
        or raw_review.get("recipe_file_sha256") != PRIVATE_PINS[f"{RUN_REL}/RECIPE.json"]
        or raw_review.get("run_sha256")
        != {
            "RUN-MANIFEST.json": PRIVATE_PINS[f"{RUN_REL}/run-v1/RUN-MANIFEST.json"],
            "SOURCE_RECEIPT.json": PRIVATE_PINS[f"{RUN_REL}/run-v1/SOURCE_RECEIPT.json"],
            "company.sqlite3": PRIVATE_PINS[f"{RUN_REL}/run-v1/company.sqlite3"],
        }
    ):
        raise CompanyStoreError("Emergency raw source has no matching independent review")
    routes = _routes(matrix)
    expected = {
        recipe["clean_branch"]: COMMON + CLEAN_END,
        recipe["messy_branch"]: COMMON + MESSY_END,
    }
    bodies = {}
    native_originals = []
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok" or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("Emergency native database integrity or audit access differs")
        rows = db.execute("SELECT * FROM versions ORDER BY rowid").fetchall()
        if len(rows) != 19 or len(receipt["records"]) != 19:
            raise CompanyStoreError("Emergency nineteen-version population differs")
        for branch, plan in expected.items():
            selected = [r for r in rows if r["branch"] == branch]
            reported = [r for r in receipt["records"] if r["branch"] == branch]
            if len(selected) != len(plan) or len(reported) != len(plan):
                raise CompanyStoreError("Emergency branch population differs")
            previous = None
            for row, report_row, (system, record, minute) in zip(
                selected, reported, plan, strict=True
            ):
                at = _time((start + timedelta(minutes=minute)).isoformat())
                if any(
                    (row[k] != value)
                    for k, value in (
                        ("company", recipe["company"]),
                        ("branch", branch),
                        ("system", system),
                        ("record", record),
                        ("version", 1),
                        ("event_at", at),
                        ("available_at", at),
                        ("origin", "AUTHORED_TRAINING_SOURCE"),
                    )
                ):
                    raise CompanyStoreError(
                        "Emergency native identity or event/availability clock differs"
                    )
                if (
                    row["sha256"] != sha(row["content"])
                    or {
                        k: row[k]
                        for k in (
                            "branch",
                            "system",
                            "record",
                            "version",
                            "event_at",
                            "imported_at",
                            "sha256",
                        )
                    }
                    != report_row
                ):
                    raise CompanyStoreError("Emergency receipt/native tuple differs")
                imported = datetime.fromisoformat(row["imported_at"])
                if (
                    imported.tzinfo is None
                    or imported.astimezone(UTC) > datetime.now(UTC)
                    or imported.astimezone(UTC).date().isoformat() < AS_OF
                ):
                    raise CompanyStoreError("Emergency actual import clock differs")
                provenance = json.loads(row["provenance"])
                if provenance != {
                    "source_reference": recipe["exercise_id"],
                    "control_ids": [CONTROL],
                    "classification": QUALIFICATION,
                    "recipe_sha256": RECIPE_SHA256,
                    "source_sha256": source_pins,
                    "operational_fact_status": "LOCAL_FUTURE_FIXTURE_ONLY",
                }:
                    raise CompanyStoreError("Emergency native source provenance differs")
                body = json.loads(row["content"])
                if (
                    body["previous_source"] != previous
                    or body["record_id"] != record
                    or body["recorded_at"] != at
                    or body["classification"] != QUALIFICATION
                    or body["corporate_emergency_authority"] != "UNVERIFIED_NOT_ASSERTED"
                    or body["review_status"]
                    != "LOCAL_MANAGEMENT_RECORD_OBSERVATION_NOT_CORPORATE_APPROVAL"
                    or body["target"] != "IN_MEMORY_REFERENCE_CONFIGURATION_ONLY"
                    or body["service_status"] != "CANONICAL_DESIGN_REFERENCE_NOT_DEPLOYMENT"
                    or body["site_status"] != "RENO_BOISE_REFERENCES_ONLY_NO_SITE_OPERATION"
                ):
                    raise CompanyStoreError("Emergency source claim or predecessor chain differs")
                previous = {
                    "system": system,
                    "record": record,
                    "version": 1,
                    "sha256": row["sha256"],
                }
                bodies[(branch, record)] = body
                native_originals.append(
                    {
                        "company": row["company"],
                        "branch": row["branch"],
                        "system": row["system"],
                        "record": row["record"],
                        "version": row["version"],
                        "event_at": row["event_at"],
                        "available_at": row["available_at"],
                        "imported_at": row["imported_at"],
                        "sha256": row["sha256"],
                    }
                )
        systems = {
            (r["branch"], r["system"], r["owner"]) for r in db.execute("SELECT * FROM systems")
        }
        if systems != {
            (
                branch,
                system,
                receipt["management_review_contact"]
                if system == "retrospective_observation"
                else receipt["owner_contact"],
            )
            for branch in expected
            for system in (
                "emergency_intake",
                "emergency_gate",
                "local_change_state",
                "retrospective_observation",
            )
        }:
            raise CompanyStoreError("Emergency native system custody differs")
    _check_bodies(bodies, receipt)
    if any(
        (_private(paths[name]), _digest(paths[name])) != value for name, value in identities.items()
    ):
        raise CompanyStoreError("Frozen emergency source changed during verification")
    return {
        "schema": SCHEMA,
        "status": "SELECTED_LOCAL_FUTURE_SOURCE_REPERFORMED_INDEPENDENT_REVIEW_REQUIRED",
        "source_sha256": {name: value[1] for name, value in identities.items()},
        "native_versions": 19,
        "native_originals": native_originals,
        "branch_versions": {"CLEAN": 8, "MESSY": 11},
        "physical_company_id": recipe["company"],
        "source_branches": {"CLEAN": recipe["clean_branch"], "MESSY": recipe["messy_branch"]},
        "route_disposition": routes,
        "task_routes_per_side": {"A": 4, "B": 4},
        "corporate_emergency_approval": False,
        "deployed_change": False,
        "source_complete": False,
        "audit_task_credit": False,
        "active_P1_mutated": False,
        "limits": [
            "Prospective in-memory fixture only; no actual 2027 operation or service deployment.",
            "Proposed contacts do not establish corporate emergency approval.",
            "Messy invalid bypass remains an open local exception after rollback.",
            "No normal/emergency full-population audit test, ordinary collection, "
            "task credit, Key or grade.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            verify(args.repository, private_repository=args.private_repository),
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
