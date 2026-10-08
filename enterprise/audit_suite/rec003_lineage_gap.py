"""Read-only SH-REC-003 source lineage; no company or audit operation."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from pathlib import Path

from .company_store import CompanyStoreError
from .operating_source_bridge import sha
from .private_publication import publish

SCHEMA = "SH_REC003_EXISTING_LOCAL_TRANSFORMATION_LINEAGE_GAP_V1"
DQ = "enterprise/generated/audit-suite/company-data-quality-runtime-2026-09-22"
REBASE = (
    "enterprise/generated/audit-suite/acceptance-audit-2026-09-22/"
    "integrated-review-packet-refresh-run-post-original-journals-a1939-b2066-v4"
)
REBASE_REVIEW = REBASE + "-independent-v1/FINAL-REVIEW.json"
MATRIX = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/run-v2/MATRIX.json"
)
MATRIX_REVIEW = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/"
    "independent-review-v2/REVIEW.json"
)
PRIVATE_PINS = {
    f"{DQ}/run-v1/PLAN.json": "5df6114f83dfea0b94fffaf1a8005d67d6dd7f90cf4a1a693d5204fb89e79b63",
    f"{DQ}/run-v1/RECEIPT.json": "4b80e195d016592a4778caf2cebc312634d9c9ff4f09e02459cba752389415f9",
    f"{DQ}/root-independent-verification-v1/RECEIPT.json": (
        "d3454eff457eebdb22328029e78cbdce2edef770ba4a73a8f1d25aa545441f57"
    ),
    f"{DQ}/run-v1/a/RUNTIME.json": (
        "6b44973baf02f93f293d1ec40ccfd8dadf1142e1009e5b6bbdde995e62ee303d"
    ),
    f"{DQ}/run-v1/b/RUNTIME.json": (
        "5d5b9708ca60bad76e3f008ee8b8045e320c54de14b6a4188227f5f14e4664f2"
    ),
    f"{DQ}/run-v1/a/OPERATOR_RECEIPT.json": (
        "526e96a8da948efa01ec9fcd5b0aac67f0acf867ec4898fe7b5a78b8f82c4c12"
    ),
    f"{DQ}/run-v1/b/OPERATOR_RECEIPT.json": (
        "c04bf9f63ac6bc764458a1a4de507773417a04b2509870ab2e0e159e2bf2baf8"
    ),
    f"{DQ}/run-v1/a/company.sqlite3": (
        "9b5489db2643b728fd8df846fd07af6928d6607958bd3857c46b6c9720e980ab"
    ),
    f"{DQ}/run-v1/b/company.sqlite3": (
        "14af2e579591f0460eb3fe7c549d4c5b12ad3ac0548599de7f7ca5d3d30def12"
    ),
    f"{REBASE}/SOURCE-REBASE.json": (
        "8fca1ccbaa287f38c5354ad28b8d25ccc58713ab1972d084a13f013dd271ee63"
    ),
    REBASE_REVIEW: "0a9b8b18096bf576ec555c86d13acb2d5cbbfc0f2588755c24770e55f5c7e291",
    MATRIX: "e9477d2074bebce185e412a3ee7c424ded395c1a1128a7c918a94f6acbd1e327",
    MATRIX_REVIEW: "c4064f6217c0e7f69276adc71004d6da7971867ccf3d844a3e198145cec31ace",
}
TRACKED = (
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md",
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
    "enterprise/audit_suite/REC003_LINEAGE_GAP_PROPOSAL.md",
    "enterprise/audit_suite/rec003_lineage_gap.py",
)
CANON_PINS = {
    TRACKED[0]: "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751",
    TRACKED[1]: "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433",
}
EXPECTED_DB = {
    "a": PRIVATE_PINS[f"{DQ}/run-v1/a/company.sqlite3"],
    "b": PRIVATE_PINS[f"{DQ}/run-v1/b/company.sqlite3"],
}
EXPECTED_FINAL = {
    "a": ("LOCAL_RULES_PASSED_NOT_SOURCE_ACCEPTANCE", 23, []),
    "b": ("PARTIAL_UNRELIABLE", 21, ["R4"]),
}
GAPS = {
    "CHECK-SOC2:CC2.1": (
        "Reconcile originating system, transformation logic, excluded records and "
        "data-quality exceptions; local count alone does not establish accuracy."
    ),
    "IMPLEMENTATION": "Accepted deployed scope, owner and effective date remain unverified.",
    "TOD": (
        "Qualified design review of boundary, frequency, inputs, decisions and "
        "exception path remains open."
    ),
    "TOE": (
        "Complete selected-period population, sample, independent re-performance "
        "and exceptions remain open."
    ),
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private(path: Path) -> None:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_nlink != 1
        or path.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in path.parents)
    ):
        raise CompanyStoreError("Ordinary private REC003 source required")


def _frozen(path: Path) -> tuple:
    _private(path)
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen REC003 source has active sidecar")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise CompanyStoreError("Frozen REC003 source must be regular")
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        _digest(path),
    )


def _native(private_repository: Path, side: str, operator: dict, rebase: dict) -> dict:
    db_path = private_repository / DQ / "run-v1" / side / "company.sqlite3"
    before = _frozen(db_path)
    branch = f"local-data-quality-{side}"
    rebase_row = rebase["source_roots"].get(str(db_path.parent))
    if (
        before[-1] != EXPECTED_DB[side]
        or not isinstance(rebase_row, dict)
        or rebase_row["company_sqlite3_sha256"] != EXPECTED_DB[side]
        or rebase_row["business_tables_exactly_match_frozen_receipt"] is not True
        or rebase_row["stable_table_pins"]["versions"]["count"] != 11
    ):
        raise CompanyStoreError("Post-journal source rebase does not bind current DQ business rows")
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("DQ source integrity failure")
        rows = db.execute("SELECT * FROM versions ORDER BY system,record,version").fetchall()
        if (
            len(rows) != 11
            or db.execute("SELECT COUNT(*) FROM quality_commands").fetchone()[0] != 3
        ):
            raise CompanyStoreError("DQ business history denominator differs")
        if db.execute("SELECT COUNT(*) FROM quality_state").fetchone()[0] != 1:
            raise CompanyStoreError("DQ current state denominator differs")
        pins = {}
        bodies = {}
        for row in rows:
            route = (row["company"], row["branch"], row["system"], row["record"], row["version"])
            if route[:2] != ("SABLEHARBOR", branch) or sha(row["content"]) != row["sha256"]:
                raise CompanyStoreError("DQ original route or bytes differ")
            if row["imported_at"] >= row["event_at"] or row["available_at"] != row["event_at"]:
                raise CompanyStoreError("DQ future event/availability/import chronology differs")
            pin = {
                "company": row["company"],
                "branch": row["branch"],
                "system": row["system"],
                "record": row["record"],
                "version": row["version"],
                "sha256": row["sha256"],
                "event_at": row["event_at"],
                "available_at": row["available_at"],
                "imported_at": row["imported_at"],
            }
            pins[(row["system"], row["record"], row["version"])] = pin
            if row["system"] in {"quality_aggregate", "quality_derived", "quality_operation"}:
                bodies[(row["system"], row["record"])] = json.loads(row["content"])
        expected = {
            (ref["system"], ref["record"], ref["version"]): ref for ref in operator["native_pins"]
        }
        if len(expected) != 11 or set(expected) != set(pins):
            raise CompanyStoreError("DQ operator receipt does not enumerate every original")
        for key, pin in pins.items():
            if any(
                pin[field] != expected[key][field]
                for field in ("company", "branch", "system", "record", "version", "sha256")
            ):
                raise CompanyStoreError("DQ native pin differs from operator receipt")
        if {key[0] for key in pins} != {
            "quality_definition",
            "quality_reference",
            "quality_raw",
            "quality_derived",
            "quality_aggregate",
            "quality_operation",
        }:
            raise CompanyStoreError("DQ source family differs")
        for revision, raw_version, status, total, missing in (
            (1, 1, "PARTIAL_UNRELIABLE", 5, ["R2", "R3", "R4"]),
            (3, 2, *EXPECTED_FINAL[side]),
        ):
            record = f"TRANSFORM-{revision}"
            derived = bodies[("quality_derived", record)]
            aggregate = bodies[("quality_aggregate", record)]
            operation = bodies[("quality_operation", f"OP-{revision}")]
            source_ref = pins[("quality_raw", "LOCAL-WORK-UNITS", raw_version)]
            if (
                derived["status"] != status
                or aggregate["status"] != status
                or aggregate["accepted_rows_only_total"] != total
                or aggregate["missing_usable_expected_ids"] != missing
                or operation["observation"]["input_pin"]["sha256"] != source_ref["sha256"]
                or operation["observation"]["report"]["status"] != status
            ):
                raise CompanyStoreError("DQ original-to-transform lineage or limitation differs")
        correction = bodies[("quality_operation", "OP-2")]
        if (
            correction["observation"]["approval"]
            != "LOCAL_OPERATOR_ASSERTION_NOT_MANAGER_ACCEPTANCE"
            or correction["observation"]["prior_input_pin"]["sha256"]
            != pins[("quality_raw", "LOCAL-WORK-UNITS", 1)]["sha256"]
            or correction["observation"]["corrected_input_pin"]["sha256"]
            != pins[("quality_raw", "LOCAL-WORK-UNITS", 2)]["sha256"]
        ):
            raise CompanyStoreError("DQ local correction authority or raw lineage differs")
        journals = {
            name: db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in ("grants", "collections", "access_events")
        }
        if journals != rebase_row["journal_row_counts_current"]:
            raise CompanyStoreError("Post-journal DQ source shape differs")
    if _frozen(db_path) != before:
        raise CompanyStoreError("DQ source changed during read")
    return {
        "branch": branch,
        "source_original_count": 11,
        "native_original_refs": list(pins.values()),
        "initial_transform": {
            "status": "PARTIAL_UNRELIABLE",
            "accepted_rows_only_total": 5,
            "missing_usable_expected_ids": ["R2", "R3", "R4"],
        },
        "successor_transform": {
            "status": EXPECTED_FINAL[side][0],
            "accepted_rows_only_total": EXPECTED_FINAL[side][1],
            "missing_usable_expected_ids": EXPECTED_FINAL[side][2],
        },
        "audit_journal_counts_excluded_from_company_lineage": journals,
    }


def render(*, repository: Path, private_repository: Path) -> dict:
    """Reperform existing native bytes and route joins without writes."""
    pins = {}
    for name in TRACKED:
        path = repository / name
        if not path.is_file() or path.is_symlink():
            raise CompanyStoreError("Tracked REC003 source missing or linked")
        pins[f"repo://{name}"] = _digest(path)
    if any(pins[f"repo://{name}"] != digest for name, digest in CANON_PINS.items()):
        raise CompanyStoreError("REC003 bounded canon role/control differs")
    if (
        "| AS-P014 | Omar Vale | Data Governance and Records Lead |"
        not in (repository / TRACKED[0]).read_text()
    ):
        raise CompanyStoreError("Proposed DQ steward differs")
    if (
        "| SH-REC-003 | Material transformed evidence keeps source"
        not in (repository / TRACKED[1]).read_text()
    ):
        raise CompanyStoreError("REC003 control objective differs")
    for name, digest in PRIVATE_PINS.items():
        path = private_repository / name
        _private(path)
        if _digest(path) != digest:
            raise CompanyStoreError(f"Private REC003 source differs: {name}")
        pins[f"private://{name}"] = digest
    original_review = json.loads(
        (private_repository / DQ / "root-independent-verification-v1/RECEIPT.json").read_text()
    )
    rebase = json.loads((private_repository / REBASE / "SOURCE-REBASE.json").read_text())
    rebase_review = json.loads((private_repository / REBASE_REVIEW).read_text())
    matrix_review = json.loads((private_repository / MATRIX_REVIEW).read_text())
    if (
        original_review["status"] != "PASS"
        or rebase_review["status"]
        != "PASS_INDEPENDENT_PRIVATE_REBASED_PACKET_V4_TECHNICAL_AND_BROWSER"
        or rebase["status"]
        != "AUTHOR_SEALED_POST_BIND_SOURCE_REBASE_PENDING_INDEPENDENT_PACKET_REVIEW"
        or matrix_review["verdict"] != "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION"
    ):
        raise CompanyStoreError("Required original, post-journal and matrix reviews differ")
    matrix = json.loads((private_repository / MATRIX).read_text())
    routes = {}
    for side in "AB":
        controls = [
            control
            for family in matrix["sides"][side]["families"]
            for control in family["controls"]
            if control["control_id"] == "SH-REC-003"
        ]
        if (
            len(controls) != 1
            or len(controls[0]["tasks"]) != 4
            or controls[0]["candidate_native_source_search_target"]
            != "Evidence transformation workspace"
            or any(
                task["current_status"] != "NOT_STARTED"
                or task["current_conclusion"] != "NOT_RUN"
                or task["task_credit"] is not False
                for task in controls[0]["tasks"]
            )
        ):
            raise CompanyStoreError("Frozen four-route REC003 cohort differs")
        routes[side] = [
            {"task_id": task["task_id"], "remaining_gate": task["remaining_test_gate"]}
            for task in controls[0]["tasks"]
        ]
    branches = {}
    for side in "ab":
        operator = json.loads(
            (private_repository / DQ / "run-v1" / side / "OPERATOR_RECEIPT.json").read_text()
        )
        if operator["authority_counts"] != {"access_events": 0, "collections": 0, "grants": 0}:
            raise CompanyStoreError("Original DQ pre-audit authority scope differs")
        branches[side.upper()] = _native(private_repository, side, operator, rebase)
    return {
        "schema": SCHEMA,
        "status": "EXISTING_LOCAL_SOURCE_LINEAGE_ONLY_NO_AUDIT_CREDIT",
        "as_of": "2026-09-29",
        "control_id": "SH-REC-003",
        "source_pins": pins,
        "routes": routes,
        "branches": branches,
        "qualification": "LOCAL_NONPERSONAL_DATA_RULES_NOT_BUSINESS_TRUTH_OR_SOURCE_ACCEPTANCE",
        "new_company_operation": False,
        "audit_collection": False,
        "audit_task_credit": False,
        "remaining_limits": list(GAPS.values())
        + [
            "No DAT001 marker-metadata transformation: numeric work-unit semantics do not apply.",
            "Later audit journals are excluded from company transformation activity "
            "and task credit.",
            "2027 event/availability clocks are future simulation; imported_at records "
            "2026 insertion.",
        ],
    }


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or destination != destination.resolve()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in destination.parents)
    ):
        raise CompanyStoreError("New private REC003 packet destination required")
    packet = render(repository=Path(repository), private_repository=Path(private_repository))
    with tempfile.TemporaryDirectory(prefix=".rec003-stage-", dir=destination.parent) as name:
        stage = Path(name)
        _write(stage / "LINEAGE.json", packet)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "lineage_sha256": _digest(stage / "LINEAGE.json"),
            "module_sha256": _digest(Path(__file__)),
            "source_original_count": 22,
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    if (
        root != root.resolve()
        or not root.is_dir()
        or root.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in (root, *root.parents))
        or {path.name for path in root.iterdir()} != {"LINEAGE.json", "MANIFEST.json"}
    ):
        raise CompanyStoreError("Private ordinary two-file REC003 packet required")
    for name in ("LINEAGE.json", "MANIFEST.json"):
        _private(root / name)
    manifest = json.loads((root / "MANIFEST.json").read_text())
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "lineage_sha256": _digest(root / "LINEAGE.json"),
        "module_sha256": _digest(Path(__file__)),
        "source_original_count": 22,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("REC003 packet manifest differs")
    if json.loads((root / "LINEAGE.json").read_text()) != render(
        repository=Path(repository), private_repository=Path(private_repository)
    ):
        raise CompanyStoreError("REC003 packet source lineage or gap differs")
    return manifest
