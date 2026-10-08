"""One fictional controlled-record pointer to a reviewed company-native original."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from pathlib import Path

from . import company_dataset_classification_exercise as dataset_source
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_SELECTED_CONTROLLED_RECORD_V1"
COMPANY = dataset_source.COMPANY
AS_OF = "2026-09-29"
QUALIFICATION = "FUTURE_LOCAL_CONTROLLED_SOURCE_POINTER_NOT_AUDIT_EVIDENCE_OR_POLICY_ACCEPTANCE"
RECORD_ID = "REC-DAT001-LOCAL-CLASSIFICATION-01"
OWNER = "AS-P014"
DATASET_REL = "enterprise/generated/audit-suite/company-dataset-classification-2026-09-29/run-v1"
DATASET_REVIEW = (
    "enterprise/generated/audit-suite/company-dataset-classification-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
MATRIX_REL = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/run-v2/MATRIX.json"
)
MATRIX_REVIEW = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/"
    "independent-review-v2/REVIEW.json"
)
PRIVATE_PINS = {
    f"{DATASET_REL}/MANIFEST.json": (
        "ed670cf671da2f2d20579664807bd9a80b3dd7f0dec6e445a09166555adbfb31"
    ),
    f"{DATASET_REL}/RECEIPT.json": (
        "7c6e74974bcdb5b516b4a476099061543dbb6570e99942b3d74d9ed60bd9c44a"
    ),
    f"{DATASET_REL}/company.sqlite3": (
        "d668977b852e83ebdcef95d981e24b8863503bc3931c4eac9744ec182cbfde74"
    ),
    DATASET_REVIEW: "4d1cd9c423781bf97ff586075c460c891cc60f621b42a29a22db59df929ff52e",
    MATRIX_REL: "e9477d2074bebce185e412a3ee7c424ded395c1a1128a7c918a94f6acbd1e327",
    MATRIX_REVIEW: "c4064f6217c0e7f69276adc71004d6da7971867ccf3d844a3e198145cec31ace",
}
TRACKED = (
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md",
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md",
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
    "enterprise/audit_suite/company_dataset_classification_exercise.py",
    "enterprise/audit_suite/CONTROLLED_RECORD_2027_PROPOSAL.md",
    "enterprise/audit_suite/company_controlled_record_exercise.py",
)
SOURCE_REF = "enterprise/audit_suite/company_controlled_record_exercise.py"
SYSTEMS = (
    "local_alias_marker",
    "record_registration",
    "source_integrity",
    "controlled_retrieval",
    "disposition_screen",
)
DENOMINATORS = {
    "CLEAN": {
        "selected_records": 1,
        "invalid_alias_markers": 0,
        "registrations": 1,
        "integrity_checks": 1,
        "retrievals": 1,
        "disposition_deferrals": 1,
    },
    "MESSY": {
        "selected_records": 1,
        "invalid_alias_markers": 1,
        "registrations": 1,
        "integrity_checks": 1,
        "retrievals": 1,
        "disposition_deferrals": 1,
    },
}
LIMITS = [
    "Future 2027 event/availability is authored in-universe as of 2026-09-29; "
    "imported_at is actual insertion.",
    "One selected local classification recommendation, not complete company records "
    "or full-period operation.",
    "The original stays in company-native dataset source; this record contains a "
    "locator, not copied audit evidence.",
    "Messy unqualified alias remains in history and cannot be used as an "
    "authoritative source pointer.",
    "No approved retention/deletion/hold disposition, record-owner acceptance, "
    "real PHI or deployment claim.",
    "No P1 grant, collection, workpaper, task credit, Key or grade.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_file(path: Path) -> None:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_nlink != 1
        or path.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in path.parents)
    ):
        raise CompanyStoreError("Ordinary private controlled-record source required")


def _frozen_db(path: Path) -> tuple:
    _private_file(path)
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen dataset source has active sidecar")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise CompanyStoreError("Frozen dataset source must be regular")
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        _digest(path),
    )


def _selected_original(private_repository: Path, receipt: dict) -> dict:
    path = private_repository / DATASET_REL / "company.sqlite3"
    before = _frozen_db(path)
    selected = {}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Dataset original integrity failure")
        for scenario, branch in (("CLEAN", "DATASET-CLEAN"), ("MESSY", "DATASET-MESSY")):
            names = ["classification_review", "enforcement_followup"]
            if scenario == "MESSY":
                names.append("local_label")
            refs = {}
            for system in names:
                matches = [
                    ref
                    for ref in receipt["records"][scenario]
                    if ref["system"] == system and ref["version"] == 1
                ]
                if len(matches) != 1:
                    raise CompanyStoreError("Selected dataset tuple missing")
                ref = matches[0]
                route = tuple(
                    ref[key] for key in ("company", "branch", "system", "record", "version")
                )
                if route[0] != COMPANY or route[1] != branch or route[3] != dataset_source.DATASET:
                    raise CompanyStoreError("Dataset branch or record identity differs")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    route,
                ).fetchone()
                if (
                    row is None
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                ):
                    raise CompanyStoreError("Selected source-native bytes differ")
                body = json.loads(row["content"])
                if (
                    body["scenario"] != scenario
                    or body["dataset_id"] != dataset_source.DATASET
                    or body["payload_bytes"] != 0
                    or body["actual_phi_applicability"] != "UNDETERMINED"
                    or body["real_world_processing"] is not False
                    or body["audit_task_credit"] is not False
                ):
                    raise CompanyStoreError("Selected record qualification differs")
                expected_status = {
                    "classification_review": "LOCAL_RESTRICTED_RECOMMENDATION",
                    "enforcement_followup": "NOT_VERIFIED"
                    if scenario == "CLEAN"
                    else "NOT_VERIFIED_STALE_LABEL_OPEN",
                    "local_label": "INVALID_PUBLIC_METADATA_MARKER",
                }
                if body["status"] != expected_status[system]:
                    raise CompanyStoreError("Selected record history differs")
                refs[system] = {
                    key: ref[key]
                    for key in (
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "event_at",
                        "available_at",
                        "sha256",
                    )
                }
            selected[scenario] = refs
    if _frozen_db(path) != before:
        raise CompanyStoreError("Frozen dataset original changed during read")
    return selected


def _context(repository: Path, private_repository: Path) -> tuple[dict, dict, dict]:
    repository, private_repository = repository.resolve(), private_repository.resolve()
    pins = {}
    for relative in TRACKED:
        path = repository / relative
        if not path.is_file() or path.is_symlink():
            raise CompanyStoreError("Required tracked records source unavailable")
        pins[f"repo://{relative}"] = _digest(path)
    expected_tracked = {
        TRACKED[0]: "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496",
        TRACKED[1]: "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751",
        TRACKED[2]: "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433",
    }
    if any(pins[f"repo://{name}"] != expected for name, expected in expected_tracked.items()):
        raise CompanyStoreError("Bounded canon role/control source differs")
    appointments = (repository / TRACKED[1]).read_text()
    catalog = (repository / TRACKED[2]).read_text()
    if "| AS-P014 | Omar Vale | Data Governance and Records Lead |" not in appointments:
        raise CompanyStoreError("Proposed records custodian differs")
    if (
        "| SH-REC-001 | Material control, approval, transaction, incident, and "
        "decision records identify actor, time, scope, and outcome." not in catalog
    ):
        raise CompanyStoreError("Selected control objective differs")
    for relative, expected in PRIVATE_PINS.items():
        path = private_repository / relative
        _private_file(path)
        if _digest(path) != expected:
            raise CompanyStoreError(f"Reviewed private record source differs: {relative}")
        pins[f"private://{relative}"] = expected
    if json.loads((private_repository / DATASET_REVIEW).read_text()).get("verdict") != (
        "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW"
    ):
        raise CompanyStoreError("Dataset original lacks independent review")
    if json.loads((private_repository / MATRIX_REVIEW).read_text()).get("verdict") != (
        "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION"
    ):
        raise CompanyStoreError("Frozen discovery matrix lacks independent review")
    dataset_source.verify(
        private_repository / DATASET_REL,
        repository=repository,
        private_repository=private_repository,
    )
    receipt = json.loads((private_repository / DATASET_REL / "RECEIPT.json").read_text())
    selected = _selected_original(private_repository, receipt)
    matrix = json.loads((private_repository / MATRIX_REL).read_text())
    routes = {}
    for side in "AB":
        matches = [
            control
            for family in matrix["sides"][side]["families"]
            for control in family["controls"]
            if control["control_id"] == "SH-REC-001"
        ]
        if (
            len(matches) != 1
            or len(matches[0]["tasks"]) != 3
            or matches[0]["candidate_native_source_search_target"]
            != "Controlled records repository"
            or any(
                task["current_status"] != "NOT_STARTED"
                or task["current_conclusion"] != "NOT_RUN"
                or task["task_credit"] is not False
                for task in matches[0]["tasks"]
            )
        ):
            raise CompanyStoreError("Frozen three-route record cohort differs")
        routes[side] = [task["task_id"] for task in matches[0]["tasks"]]
    return pins, selected, routes


def _steps(scenario: str) -> tuple[tuple, ...]:
    if scenario == "CLEAN":
        return (
            ("record_registration", "2027-07-30T10:00:00+00:00", "EXACT_NATIVE_POINTER_REGISTERED"),
            ("source_integrity", "2027-07-30T11:00:00+00:00", "SELECTED_ORIGINAL_REPERFORMED"),
            (
                "controlled_retrieval",
                "2027-08-01T10:00:00+00:00",
                "EXACT_ORIGINAL_RETRIEVED_LOCALLY",
            ),
            (
                "disposition_screen",
                "2027-08-01T11:00:00+00:00",
                "DEFER_NO_APPROVED_RETENTION_OR_HOLD",
            ),
        )
    return (
        ("local_alias_marker", "2027-08-12T10:00:00+00:00", "INVALID_UNQUALIFIED_ALIAS_NOT_SOURCE"),
        (
            "record_registration",
            "2027-08-12T11:00:00+00:00",
            "EXACT_NATIVE_POINTER_REGISTERED_ALIAS_PRESERVED",
        ),
        (
            "source_integrity",
            "2027-08-12T12:00:00+00:00",
            "SELECTED_ORIGINAL_REPERFORMED_ALIAS_OPEN",
        ),
        (
            "controlled_retrieval",
            "2027-08-13T10:00:00+00:00",
            "EXACT_ORIGINAL_RETRIEVED_ALIAS_UNUSED",
        ),
        ("disposition_screen", "2027-08-13T11:00:00+00:00", "DEFER_NO_APPROVED_RETENTION_OR_HOLD"),
    )


def _body(scenario: str, step: tuple, refs: dict, previous: dict | None) -> dict:
    system, at, status = step
    alias = scenario == "MESSY"
    exact = system != "local_alias_marker"
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "system": system,
        "record": RECORD_ID,
        "status": status,
        "event_at": _time(at),
        "available_at": _time(at),
        "actor_person_id": "SIM-LOCAL-OPERATOR-02" if not exact else OWNER,
        "custodian_person_id": OWNER,
        "accountable_record_owner": "UNDETERMINED",
        "selected_record_kind": "LOCAL_DATASET_CLASSIFICATION_RECOMMENDATION",
        "selected_record_count": 1,
        "source_original_locator": refs["classification_review"] if exact else None,
        "source_context_refs": refs,
        "previous_local_sha256": previous["sha256"] if previous else None,
        "invalid_alias_marker": "LOCAL_UNQUALIFIED_CLASSIFICATION_ALIAS" if not exact else None,
        "invalid_alias_has_source_version_or_hash": False if not exact else None,
        "invalid_alias_history_open": alias,
        "source_integrity_state": (
            "EXACT_SOURCE_BYTES_REPERFORMED_LOCAL_SIMULATION"
            if system in {"source_integrity", "controlled_retrieval", "disposition_screen"}
            else "NOT_YET_REPERFORMED"
        ),
        "retrieval_uses_authoritative_original": system == "controlled_retrieval",
        "copied_source_bytes_as_audit_pack": False,
        "classification_authority": "LOCAL_RECOMMENDATION_NOT_OWNER_ACCEPTED",
        "technical_enforcement": "NOT_VERIFIED",
        "approved_retention_schedule": "UNDETERMINED",
        "deletion_authority": "UNDETERMINED",
        "legal_hold_disposition": "UNDETERMINED",
        "disposition_executed": False,
        "actual_phi_applicability": "UNDETERMINED",
        "real_world_operation": False,
        "audit_task_credit": False,
        "qualification": QUALIFICATION,
    }


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Publish one private source-index history without audit access or task writes."""
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or destination != destination.resolve()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in destination.parents)
    ):
        raise CompanyStoreError("New private controlled-record destination required")
    pins, selected, routes = _context(Path(repository), Path(private_repository))
    branches = {"CLEAN": "RECORD-CLEAN", "MESSY": "RECORD-MESSY"}
    with tempfile.TemporaryDirectory(prefix=".record-stage-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in branches.items():
            for system in SYSTEMS:
                store.register_system(COMPANY, branch, system, OWNER)
            records[scenario], previous = [], None
            for step in _steps(scenario):
                if any(
                    ref["available_at"] >= _time(step[1]) for ref in selected[scenario].values()
                ):
                    raise CompanyStoreError("Controlled record predates selected original")
                body = _body(scenario, step, selected[scenario], previous)
                ref = store.append_version(
                    COMPANY,
                    branch,
                    step[0],
                    RECORD_ID,
                    expected_version=0,
                    command_id=f"CR-{branch}-{step[0]}",
                    event_at=body["event_at"],
                    available_at=body["available_at"],
                    content=encoded(body),
                    provenance={
                        "source_reference": SOURCE_REF,
                        "source_pins": pins,
                        "scenario": scenario,
                        "qualification": QUALIFICATION,
                    },
                )
                records[scenario].append(ref)
                previous = ref
        receipt = {
            "schema": SCHEMA,
            "status": "FUTURE_FICTIONAL_SELECTED_RECORD_POINTER_NO_CREDIT",
            "as_of": AS_OF,
            "company": COMPANY,
            "branches": branches,
            "source_pins": pins,
            "selected_route_task_ids": routes,
            "selected_source_refs": selected,
            "records": records,
            "local_denominators": DENOMINATORS,
            "authority_gate": "RECORD_OWNER_RETENTION_DELETION_AND_HOLD_UNDETERMINED",
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": 9,
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Reperform exact source-original linkage, local chronology and authority limits."""
    root = Path(destination).absolute()
    if (
        root != root.resolve()
        or not root.is_dir()
        or root.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in (root, *root.parents))
        or {path.name for path in root.iterdir()}
        != {"MANIFEST.json", "RECEIPT.json", "company.sqlite3"}
    ):
        raise CompanyStoreError("Private ordinary three-file record source required")
    for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3"):
        _private_file(root / name)
    manifest = json.loads((root / "MANIFEST.json").read_text())
    receipt = json.loads((root / "RECEIPT.json").read_text())
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _digest(root / "RECEIPT.json"),
        "company_db_sha256": _digest(root / "company.sqlite3"),
        "module_sha256": _digest(Path(__file__)),
        "native_version_count": 9,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Controlled record manifest pin differs")
    pins, selected, routes = _context(Path(repository), Path(private_repository))
    if (
        receipt["schema"] != SCHEMA
        or receipt["status"] != "FUTURE_FICTIONAL_SELECTED_RECORD_POINTER_NO_CREDIT"
        or receipt["as_of"] != AS_OF
        or receipt["company"] != COMPANY
        or receipt["branches"] != {"CLEAN": "RECORD-CLEAN", "MESSY": "RECORD-MESSY"}
        or receipt["source_pins"] != pins
        or receipt["selected_route_task_ids"] != routes
        or receipt["selected_source_refs"] != selected
        or receipt["local_denominators"] != DENOMINATORS
        or receipt["limits"] != LIMITS
        or receipt["authority_gate"] != "RECORD_OWNER_RETENTION_DELETION_AND_HOLD_UNDETERMINED"
        or set(receipt["records"]) != {"CLEAN", "MESSY"}
    ):
        raise CompanyStoreError("Controlled record receipt scope differs")
    with closing(
        sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Native controlled-record DB integrity failure")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != count
            for table, count in (
                ("versions", 9),
                ("systems", 10),
                ("grants", 0),
                ("collections", 0),
                ("access_events", 0),
            )
        ):
            raise CompanyStoreError("Controlled-record population/access differs")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, OWNER)
            for branch in receipt["branches"].values()
            for system in SYSTEMS
        }:
            raise CompanyStoreError("Controlled-record system custody differs")
        for scenario, branch in receipt["branches"].items():
            steps, refs, previous = _steps(scenario), receipt["records"][scenario], None
            if len(refs) != len(steps):
                raise CompanyStoreError("Controlled-record branch denominator differs")
            for step, ref in zip(steps, refs, strict=True):
                system, at, _status = step
                route = (COMPANY, branch, system, RECORD_ID, 1)
                if (
                    tuple(ref[key] for key in ("company", "branch", "system", "record", "version"))
                    != route
                ):
                    raise CompanyStoreError("Controlled-record route differs")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    route,
                ).fetchone()
                if (
                    row is None
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or row["command_id"] != f"CR-{branch}-{system}"
                    or any(
                        row[key] != ref[key] for key in ("event_at", "available_at", "imported_at")
                    )
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["origin"] != row["origin"]
                ):
                    raise CompanyStoreError("Native controlled-record row identity differs")
                provenance = {
                    "source_reference": SOURCE_REF,
                    "source_pins": pins,
                    "scenario": scenario,
                    "qualification": QUALIFICATION,
                }
                if json.loads(row["provenance"]) != provenance or ref["provenance"] != provenance:
                    raise CompanyStoreError("Controlled-record provenance differs")
                if any(item["available_at"] >= _time(at) for item in selected[scenario].values()):
                    raise CompanyStoreError("Original source availability differs")
                expected = _body(scenario, step, selected[scenario], previous)
                if (
                    json.loads(row["content"]) != expected
                    or row["event_at"] != expected["event_at"]
                    or row["available_at"] != expected["available_at"]
                    or row["imported_at"] >= row["event_at"]
                ):
                    raise CompanyStoreError("Controlled-record content or future clock differs")
                previous = ref
    return manifest
