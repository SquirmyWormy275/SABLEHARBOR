"""One fictional company-native extraction history, separate from audit collection."""

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

SCHEMA = "SH_FICTIONAL_2027_SELECTED_SOURCE_EXTRACTION_V1"
COMPANY = dataset_source.COMPANY
DATASET = dataset_source.DATASET
AS_OF = "2026-09-29"
OWNER = "AS-P014"
RECORD = "EXTRACT-DAT001-MARKER-METADATA-01"
QUALIFICATION = "FUTURE_COMPANY_SOURCE_QUERY_NO_AUDIT_COLLECTION_OR_APPROVAL"
SOURCE_REF = "enterprise/audit_suite/company_source_extraction_exercise.py"
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
    "enterprise/audit_suite/SOURCE_EXTRACTION_2027_PROPOSAL.md",
    "enterprise/audit_suite/company_source_extraction_exercise.py",
)
CANON_PINS = {
    TRACKED[0]: "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496",
    TRACKED[1]: "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751",
    TRACKED[2]: "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433",
}
SYSTEMS = (
    "extract_request",
    "extract_attempt",
    "extract_reconciliation",
    "extract_correction",
    "review_gate",
)
EXPECTED_SOURCE_SYSTEMS = {
    "CLEAN": (
        "dataset_inventory",
        "classification_review",
        "propagation_request",
        "enforcement_followup",
    ),
    "MESSY": (
        "dataset_inventory",
        "local_label",
        "label_quarantine",
        "classification_review",
        "propagation_request",
        "enforcement_followup",
    ),
}
WINDOWS = {
    "CLEAN": ("2027-07-29T00:00:00+00:00", "2027-07-31T00:00:00+00:00"),
    "MESSY": ("2027-08-11T00:00:00+00:00", "2027-08-13T00:00:00+00:00"),
}
LIMITS = [
    "Only one synthetic marker-metadata dataset in the reviewed DAT001 source DB; "
    "no enterprise population.",
    "Messy first extract omits local_label; correction preserves its history and "
    "all six exact source tuples.",
    "Source count and byte reconciliation do not establish business accuracy or "
    "audit-period completeness.",
    "AS-P014 is a proposed source custodian; independent extraction review and "
    "approval are pending.",
    "No actual PHI, real operation, audit collection, workpaper, task credit, Key or grade.",
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
        raise CompanyStoreError("Ordinary private extraction source required")


def _frozen_db(path: Path) -> tuple:
    _private_file(path)
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen extraction original has active sidecar")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise CompanyStoreError("Frozen extraction original must be regular")
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        _digest(path),
    )


def _source_rows(private_repository: Path, receipt: dict) -> dict:
    path = private_repository / DATASET_REL / "company.sqlite3"
    before = _frozen_db(path)
    sources = {}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Dataset original integrity failure")
        for scenario, branch in (("CLEAN", "DATASET-CLEAN"), ("MESSY", "DATASET-MESSY")):
            rows = db.execute(
                "SELECT * FROM versions WHERE company=? AND branch=? AND record=? "
                "ORDER BY event_at,system,version",
                (COMPANY, branch, DATASET),
            ).fetchall()
            if (
                len(rows) != len(EXPECTED_SOURCE_SYSTEMS[scenario])
                or tuple(row["system"] for row in rows) != EXPECTED_SOURCE_SYSTEMS[scenario]
                or any(row["version"] != 1 for row in rows)
            ):
                raise CompanyStoreError("Selected source dataset population differs")
            expected = {
                (ref["system"], ref["version"]): ref for ref in receipt["records"][scenario]
            }
            if len(expected) != len(rows):
                raise CompanyStoreError("Dataset receipt denominator differs")
            members = []
            start, end = (_time(x) for x in WINDOWS[scenario])
            for row in rows:
                ref = expected.get((row["system"], row["version"]))
                if (
                    ref is None
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or not start <= row["event_at"] < end
                    or row["available_at"] > row["event_at"]
                ):
                    raise CompanyStoreError("Selected source tuple, byte or window differs")
                body = json.loads(row["content"])
                if (
                    body["scenario"] != scenario
                    or body["dataset_id"] != DATASET
                    or body["payload_bytes"] != 0
                    or body["actual_phi_applicability"] != "UNDETERMINED"
                    or body["real_world_processing"] is not False
                    or body["audit_task_credit"] is not False
                ):
                    raise CompanyStoreError("Selected source qualification differs")
                members.append(
                    {
                        key: ref[key]
                        for key in (
                            "company",
                            "branch",
                            "system",
                            "record",
                            "version",
                            "sha256",
                            "event_at",
                            "available_at",
                        )
                    }
                )
            sources[scenario] = members
    if _frozen_db(path) != before:
        raise CompanyStoreError("Frozen extraction original changed during read")
    return sources


def _context(repository: Path, private_repository: Path) -> tuple[dict, dict, dict]:
    pins = {}
    for name in TRACKED:
        path = repository / name
        if not path.is_file() or path.is_symlink():
            raise CompanyStoreError("Tracked extraction source missing or linked")
        pins[f"repo://{name}"] = _digest(path)
    if any(pins[f"repo://{name}"] != digest for name, digest in CANON_PINS.items()):
        raise CompanyStoreError("Bounded canon role/control source differs")
    appointments = (repository / TRACKED[1]).read_text()
    catalog = (repository / TRACKED[2]).read_text()
    if "| AS-P014 | Omar Vale | Data Governance and Records Lead |" not in appointments:
        raise CompanyStoreError("Proposed source custodian differs")
    if (
        "| SH-REC-002 | Evidence extracts used for assurance preserve source, "
        "query/report, parameters, period, timezone, transformations, and "
        "completeness limitations." not in catalog
    ):
        raise CompanyStoreError("Selected extraction control objective differs")
    for relative, digest in PRIVATE_PINS.items():
        path = private_repository / relative
        _private_file(path)
        if _digest(path) != digest:
            raise CompanyStoreError(f"Reviewed private extraction source differs: {relative}")
        pins[f"private://{relative}"] = digest
    if json.loads((private_repository / DATASET_REVIEW).read_text()).get("verdict") != (
        "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW"
    ):
        raise CompanyStoreError("Dataset original lacks independent review")
    if json.loads((private_repository / MATRIX_REVIEW).read_text()).get("verdict") != (
        "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION"
    ):
        raise CompanyStoreError("Discovery matrix lacks independent review")
    dataset_source.verify(
        private_repository / DATASET_REL,
        repository=repository,
        private_repository=private_repository,
    )
    receipt = json.loads((private_repository / DATASET_REL / "RECEIPT.json").read_text())
    source = _source_rows(private_repository, receipt)
    matrix = json.loads((private_repository / MATRIX_REL).read_text())
    routes = {}
    for side in "AB":
        matches = [
            control
            for family in matrix["sides"][side]["families"]
            for control in family["controls"]
            if control["control_id"] == "SH-REC-002"
        ]
        if (
            len(matches) != 1
            or len(matches[0]["tasks"]) != 6
            or matches[0]["candidate_native_source_search_target"]
            != "Evidence extraction workspace"
            or any(
                task["current_status"] != "NOT_STARTED"
                or task["current_conclusion"] != "NOT_RUN"
                or task["task_credit"] is not False
                for task in matches[0]["tasks"]
            )
        ):
            raise CompanyStoreError("Frozen six-route extraction cohort differs")
        routes[side] = [task["task_id"] for task in matches[0]["tasks"]]
    return pins, source, routes


def _steps(scenario: str) -> tuple[tuple[str, str, str], ...]:
    if scenario == "CLEAN":
        return (
            ("extract_request", "2027-08-02T10:00:00+00:00", "LOCAL_QUERY_REQUESTED"),
            ("extract_attempt", "2027-08-02T11:00:00+00:00", "FOUR_SOURCE_ROWS_EXPORTED"),
            ("extract_reconciliation", "2027-08-02T12:00:00+00:00", "FOUR_EXACT_ROWS_RECONCILED"),
            ("review_gate", "2027-08-02T13:00:00+00:00", "INDEPENDENT_REVIEW_PENDING"),
        )
    return (
        ("extract_request", "2027-08-14T10:00:00+00:00", "LOCAL_QUERY_REQUESTED"),
        ("extract_attempt", "2027-08-14T11:00:00+00:00", "INCOMPLETE_FIVE_ROW_EXPORT"),
        ("extract_reconciliation", "2027-08-14T12:00:00+00:00", "MISSING_LOCAL_LABEL_OPEN"),
        ("extract_correction", "2027-08-14T13:00:00+00:00", "SIX_ROW_EXPORT_CORRECTED"),
        ("review_gate", "2027-08-14T14:00:00+00:00", "INDEPENDENT_REVIEW_PENDING"),
    )


def _body(
    scenario: str, step: tuple[str, str, str], source: list[dict], previous: dict | None
) -> dict:
    system, at, status = step
    complete = scenario == "CLEAN" or system in {"extract_correction", "review_gate"}
    returned = source if complete else [row for row in source if row["system"] != "local_label"]
    if scenario == "CLEAN":
        returned = source
    if system == "extract_request":
        returned = []
    missing = [] if system == "extract_request" else [row for row in source if row not in returned]
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "system": system,
        "record": RECORD,
        "status": status,
        "event_at": _time(at),
        "available_at": _time(at),
        "actor_person_id": OWNER,
        "custodian_role_status": "PROPOSED_CURRENT_ASSIGNMENT_NOT_ACCEPTED_EXTRACTION_AUTHORITY",
        "source_database_sha256": PRIVATE_PINS[f"{DATASET_REL}/company.sqlite3"],
        "query": {
            "company": COMPANY,
            "branch": f"DATASET-{scenario}",
            "record": DATASET,
            "systems": "ALL",
            "event_window_start": _time(WINDOWS[scenario][0]),
            "event_window_end_exclusive": _time(WINDOWS[scenario][1]),
            "as_of": _time(at),
            "timezone": "UTC",
            "cursor": "START",
            "page_limit": 32,
            "transformation": "NONE",
        },
        "declared_source_population_count": len(source),
        "source_population_refs": source,
        "returned_count": len(returned),
        "returned_refs": returned,
        "returned_refs_sha256": sha(encoded(returned)),
        "output_kind": "SOURCE_VERSION_INDEX_NO_ORIGINAL_CONTENT_BYTES",
        "source_content_bytes_copied": False,
        "export_page_truncated": False,
        "next_cursor": None,
        "excluded_count": len(missing),
        "excluded_refs": missing,
        "local_query_reconciliation": (
            "NOT_RUN"
            if system == "extract_request"
            else "PASS_EXACT_SELECTED_SOURCE_ONLY"
            if not missing
            else "FAIL_MISSING_LOCAL_LABEL"
        ),
        "initial_omission_preserved": scenario == "MESSY"
        and system in {"extract_correction", "review_gate"},
        "initial_exception_disposition": (
            "OPEN_PENDING_INDEPENDENT_REVIEW" if scenario == "MESSY" else "NONE"
        ),
        "independent_extraction_review": "PENDING",
        "approved_view": False,
        "audit_collection": False,
        "audit_artifact_retained": False,
        "business_accuracy_assessed": False,
        "previous_local_sha256": previous["sha256"] if previous else None,
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
    """Publish a new private company source history; never collect audit evidence."""
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or destination != destination.resolve()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in destination.parents)
    ):
        raise CompanyStoreError("New private extraction destination required")
    pins, source, routes = _context(Path(repository), Path(private_repository))
    branches = {"CLEAN": "EXTRACT-CLEAN", "MESSY": "EXTRACT-MESSY"}
    with tempfile.TemporaryDirectory(prefix=".extraction-stage-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in branches.items():
            for system in SYSTEMS:
                store.register_system(COMPANY, branch, system, OWNER)
            records[scenario], previous = [], None
            for step in _steps(scenario):
                if any(row["available_at"] >= _time(step[1]) for row in source[scenario]):
                    raise CompanyStoreError("Extraction predates selected source")
                body = _body(scenario, step, source[scenario], previous)
                ref = store.append_version(
                    COMPANY,
                    branch,
                    step[0],
                    RECORD,
                    expected_version=0,
                    command_id=f"EX-{branch}-{step[0]}",
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
            "status": "FUTURE_FICTIONAL_COMPANY_EXTRACTION_NO_AUDIT_CREDIT",
            "as_of": AS_OF,
            "company": COMPANY,
            "branches": branches,
            "source_pins": pins,
            "selected_source_population_refs": source,
            "selected_route_task_ids": routes,
            "records": records,
            "local_denominators": {"CLEAN": 4, "MESSY": 6},
            "approval_gate": "INDEPENDENT_EXTRACTION_REVIEW_AND_OWNER_AUTHORITY_PENDING",
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
    """Reperform exact selected original query, omissions and pending review."""
    root = Path(destination).absolute()
    if (
        root != root.resolve()
        or not root.is_dir()
        or root.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in (root, *root.parents))
        or {path.name for path in root.iterdir()}
        != {"MANIFEST.json", "RECEIPT.json", "company.sqlite3"}
    ):
        raise CompanyStoreError("Private ordinary three-file extraction source required")
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
        raise CompanyStoreError("Extraction manifest differs")
    pins, source, routes = _context(Path(repository), Path(private_repository))
    if (
        receipt["schema"] != SCHEMA
        or receipt["status"] != "FUTURE_FICTIONAL_COMPANY_EXTRACTION_NO_AUDIT_CREDIT"
        or receipt["as_of"] != AS_OF
        or receipt["company"] != COMPANY
        or receipt["branches"] != {"CLEAN": "EXTRACT-CLEAN", "MESSY": "EXTRACT-MESSY"}
        or receipt["source_pins"] != pins
        or receipt["selected_source_population_refs"] != source
        or receipt["selected_route_task_ids"] != routes
        or receipt["local_denominators"] != {"CLEAN": 4, "MESSY": 6}
        or receipt["approval_gate"] != "INDEPENDENT_EXTRACTION_REVIEW_AND_OWNER_AUTHORITY_PENDING"
        or receipt["limits"] != LIMITS
        or set(receipt["records"]) != {"CLEAN", "MESSY"}
    ):
        raise CompanyStoreError("Extraction receipt scope differs")
    with closing(
        sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Native extraction DB integrity failure")
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
            raise CompanyStoreError("Extraction native population or access differs")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, OWNER)
            for branch in receipt["branches"].values()
            for system in SYSTEMS
        }:
            raise CompanyStoreError("Extraction system custody differs")
        for scenario, branch in receipt["branches"].items():
            steps, refs, previous = _steps(scenario), receipt["records"][scenario], None
            if len(refs) != len(steps):
                raise CompanyStoreError("Extraction event denominator differs")
            for step, ref in zip(steps, refs, strict=True):
                system, at, _ = step
                route = (COMPANY, branch, system, RECORD, 1)
                if (
                    tuple(ref[key] for key in ("company", "branch", "system", "record", "version"))
                    != route
                ):
                    raise CompanyStoreError("Extraction native route differs")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    route,
                ).fetchone()
                if (
                    row is None
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or row["command_id"] != f"EX-{branch}-{system}"
                    or any(
                        row[key] != ref[key] for key in ("event_at", "available_at", "imported_at")
                    )
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["origin"] != row["origin"]
                ):
                    raise CompanyStoreError("Native extraction row identity differs")
                provenance = {
                    "source_reference": SOURCE_REF,
                    "source_pins": pins,
                    "scenario": scenario,
                    "qualification": QUALIFICATION,
                }
                if json.loads(row["provenance"]) != provenance or ref["provenance"] != provenance:
                    raise CompanyStoreError("Extraction provenance differs")
                if any(item["available_at"] >= _time(at) for item in source[scenario]):
                    raise CompanyStoreError("Extraction source availability differs")
                expected = _body(scenario, step, source[scenario], previous)
                if (
                    json.loads(row["content"]) != expected
                    or row["event_at"] != expected["event_at"]
                    or row["available_at"] != expected["available_at"]
                    or row["imported_at"] >= row["event_at"]
                ):
                    raise CompanyStoreError("Extraction content or future clock differs")
                previous = ref
    return manifest
