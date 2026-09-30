"""One disposable nonpersonal integrity/transform chain from frozen DQ originals."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

from . import company_data_quality_runtime as dq
from . import rec003_lineage_gap as rec003
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_NONPERSONAL_INTEGRITY_CHAIN_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"CLEAN": "INTEGRITY-CLEAN", "MESSY": "INTEGRITY-MESSY"}
AS_OF = "2026-09-29"
SOURCE_REF = "enterprise/audit_suite/company_integrity_chain_2027_exercise.py"
QUALIFICATION = "FUTURE_NONPERSONAL_DISPOSABLE_LOCAL_TEST_NO_AUDIT_CREDIT"
DQ_ROOT = "enterprise/generated/audit-suite/company-data-quality-runtime-2026-09-22"
REBASE = (
    "enterprise/generated/audit-suite/acceptance-audit-2026-09-22/"
    "integrated-review-packet-refresh-run-post-original-journals-a1939-b2066-v4"
)
REBASE_REVIEW = REBASE + "-independent-v1/FINAL-REVIEW.json"
REC003_REVIEW = (
    "enterprise/generated/audit-suite/rec003-lineage-gap-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
PRIVATE_PINS = {
    f"{DQ_ROOT}/run-v1/PLAN.json": (
        "5df6114f83dfea0b94fffaf1a8005d67d6dd7f90cf4a1a693d5204fb89e79b63"
    ),
    f"{DQ_ROOT}/run-v1/RECEIPT.json": (
        "4b80e195d016592a4778caf2cebc312634d9c9ff4f09e02459cba752389415f9"
    ),
    f"{DQ_ROOT}/run-v1/a/RUNTIME.json": (
        "6b44973baf02f93f293d1ec40ccfd8dadf1142e1009e5b6bbdde995e62ee303d"
    ),
    f"{DQ_ROOT}/run-v1/a/OPERATOR_RECEIPT.json": (
        "526e96a8da948efa01ec9fcd5b0aac67f0acf867ec4898fe7b5a78b8f82c4c12"
    ),
    f"{DQ_ROOT}/run-v1/a/company.sqlite3": (
        "9b5489db2643b728fd8df846fd07af6928d6607958bd3857c46b6c9720e980ab"
    ),
    f"{DQ_ROOT}/root-independent-verification-v1/RECEIPT.json": (
        "d3454eff457eebdb22328029e78cbdce2edef770ba4a73a8f1d25aa545441f57"
    ),
    f"{REBASE}/SOURCE-REBASE.json": (
        "8fca1ccbaa287f38c5354ad28b8d25ccc58713ab1972d084a13f013dd271ee63"
    ),
    REBASE_REVIEW: ("0a9b8b18096bf576ec555c86d13acb2d5cbbfc0f2588755c24770e55f5c7e291"),
    REC003_REVIEW: ("f162bf84513163be4c21479c85ab986b20c62d026870bd9741a8e1285470844e"),
}
TRACKED_PINS = {
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "enterprise/audit_suite/DATA_RECORD_PHI_50_ROUTE_GAP_LEDGER_2026-09-29.md": (
        "a6c74e36e39990690024f7f8ca37c3e09e973e8ef7fd1ec122dd5cbdf7c543f5"
    ),
    "enterprise/audit_suite/DATA_RECORD_PHI_50_ROUTE_GAP_LEDGER_2026-09-29.json": (
        "ec64be770474024c86cc9dd6876a9fd4c47d13478541f10cf3504688234cde63"
    ),
    "enterprise/audit_suite/DATA_QUALITY_RUNTIME.md": (
        "c19297d201ba148d4fe13300273df62ddbb6c682dc2eba135edf8597f691b5f8"
    ),
    "enterprise/audit_suite/company_data_quality_runtime.py": (
        "358fbf812e6203b4c1351e93449413d9efa45bb8a743b47d7562c6642461cbf2"
    ),
    "enterprise/audit_suite/rec003_lineage_gap.py": (
        "96e928ee54c3bdfa4d967be1f8397ced1cfe7e04927fb4cdf0220815e1228ae1"
    ),
    "enterprise/audit_suite/INTEGRITY_CHAIN_2027_PROPOSAL.md": (
        "7e830310a333b3cf715ad3cc828e7eafe6a0edd3b1d72a2a53e1d5e2a1effc77"
    ),
}
SOURCE_NATIVE = {
    "raw": (
        "quality_raw",
        "LOCAL-WORK-UNITS",
        2,
        "a75c39161828f39294aba20c505dcdab03699f8028d455bedca663958995d363",
    ),
    "reference": (
        "quality_reference",
        "REFERENCE",
        1,
        "3cbea3ed8344a84a6b663665716c3c70b89f94b400baa42d4947439aad21f297",
    ),
    "definition": (
        "quality_definition",
        "LOCAL-QUALITY-A",
        1,
        "6b44973baf02f93f293d1ec40ccfd8dadf1142e1009e5b6bbdde995e62ee303d",
    ),
}
SYSTEM_OWNERS = {
    "extract_request": "AS-P014",
    "test_copy": "AS-P014",
    "alteration_plan": "AS-P008",
    "integrity_check": "AS-P008",
    "copy_quarantine": "AS-P008",
    "transform_report": "AS-P014",
    "derived_report": "AS-P014",
    "aggregate_report": "AS-P014",
    "internal_visibility": "AS-P014",
    "correction_lineage": "AS-P014",
    "local_test_review": "AS-P008",
}
LIMITS = [
    "Both branches derive from the same four-row corrected DQ A fixture; "
    "A is not an audit side pairing.",
    "The one R3 type alteration is a predeclared disposable-copy test, "
    "not a real unauthorized access event.",
    "Messy partial output remains visibly unreliable and immutable after later correction.",
    "Local rule passing and local test review do not establish source truth, "
    "enterprise deployment, complete population or professional assurance acceptance.",
    "No personal data, actual 2027 operation, audit collection, task credit, "
    "Key, Atlas or external communication.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_file(path: Path, *, db: bool = False) -> tuple:
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise CompanyStoreError("Source alias forbidden")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
        raise CompanyStoreError("Private regular nlink-one file required")
    if db and any(os.path.lexists(str(path) + suffix) for suffix in ("-wal", "-shm", "-journal")):
        raise CompanyStoreError("Frozen DQ source has active SQLite sidecar")
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        _digest(path),
    )


def _native_ref(row: sqlite3.Row) -> dict:
    return {
        key: row[key]
        for key in (
            "company",
            "branch",
            "system",
            "record",
            "version",
            "sha256",
            "event_at",
            "available_at",
            "imported_at",
        )
    }


def _context(repository: Path, private_repository: Path) -> dict:
    repository, private_repository = (
        Path(repository).absolute(),
        Path(private_repository).absolute(),
    )
    if any(path.is_symlink() for path in (repository, private_repository)):
        raise CompanyStoreError("Canonical repositories required")
    pins = {}
    for relative, expected in TRACKED_PINS.items():
        path = repository / relative
        if not path.is_file() or path.is_symlink() or _digest(path) != expected:
            raise CompanyStoreError("Tracked C3/canon source differs")
        pins[f"repo://{relative}"] = expected
    frozen = {}
    for relative, expected in PRIVATE_PINS.items():
        path = private_repository / relative
        fingerprint = _private_file(path, db=path.suffix == ".sqlite3")
        if fingerprint[-1] != expected:
            raise CompanyStoreError("Pinned DQ source bytes differ")
        frozen[relative] = fingerprint
        pins[f"private://{relative}"] = expected
    run = private_repository / DQ_ROOT / "run-v1"
    run_receipt = json.loads((run / "RECEIPT.json").read_bytes())
    independent = json.loads(
        (
            private_repository / DQ_ROOT / "root-independent-verification-v1/RECEIPT.json"
        ).read_bytes()
    )
    operator = json.loads((run / "a/OPERATOR_RECEIPT.json").read_bytes())
    rebase = json.loads((private_repository / REBASE / "SOURCE-REBASE.json").read_bytes())
    rebase_review = json.loads((private_repository / REBASE_REVIEW).read_bytes())
    rec003_review = json.loads(
        (
            private_repository / "enterprise/generated/audit-suite/rec003-lineage-gap-2026-09-29/"
            "independent-review-v1/REVIEW.json"
        ).read_bytes()
    )
    source_path = run / "a/company.sqlite3"
    rebased_root = rebase.get("source_roots", {}).get(str(source_path.parent))
    if (
        run_receipt.get("status") != "PASS"
        or independent.get("status") != "PASS"
        or independent.get("all_run_files_unchanged") is not True
        or rebase_review.get("status")
        != "PASS_INDEPENDENT_PRIVATE_REBASED_PACKET_V4_TECHNICAL_AND_BROWSER"
        or not rec003_review.get("verdict", "").startswith("PASS")
        or not isinstance(rebased_root, dict)
        or rebased_root.get("company_sqlite3_sha256")
        != PRIVATE_PINS[f"{DQ_ROOT}/run-v1/a/company.sqlite3"]
        or rebased_root.get("business_tables_exactly_match_frozen_receipt") is not True
        or rebased_root.get("stable_table_pins", {}).get("versions", {}).get("count") != 11
    ):
        raise CompanyStoreError("Reviewed post-journal DQ source rebase absent")
    rec003._native(private_repository, "a", operator, rebase)
    with closing(sqlite3.connect(source_path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("DQ source DB integrity failure")
        rows = {}
        for name, (system, record, version, expected_sha) in SOURCE_NATIVE.items():
            row = db.execute(
                "SELECT * FROM versions WHERE company='SABLEHARBOR' "
                "AND branch='local-data-quality-a' "
                "AND system=? AND record=? AND version=?",
                (system, record, version),
            ).fetchone()
            if row is None or row["sha256"] != expected_sha or sha(row["content"]) != expected_sha:
                raise CompanyStoreError("Exact DQ native source differs")
            rows[name] = {"ref": _native_ref(row), "content": row["content"]}
        journal_counts = {
            table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        }
        if journal_counts != rebased_root["journal_row_counts_current"]:
            raise CompanyStoreError("Post-journal DQ access differs from reviewed rebase")
    definition = json.loads(rows["definition"]["content"])
    raw = json.loads(rows["raw"]["content"])
    reference = json.loads(rows["reference"]["content"])
    if (
        rows["definition"]["content"] != (run / "a/RUNTIME.json").read_bytes()
        or definition["plan"]["expected_record_ids"] != ["R1", "R2", "R3", "R4"]
        or definition["plan"]["reference_rows"] != reference
        or len(raw) != 4
        or [row.get("record_id") for row in raw] != ["R1", "R2", "R3", "R4"]
        or any(set(row) != {"record_id", "entity_id", "units", "observed_at"} for row in raw)
        or [row["units"] for row in raw] != [5, 7, 9, 2]
        or any(row["entity_id"] not in {"LOCAL-E1", "LOCAL-E2"} for row in raw)
    ):
        raise CompanyStoreError("Bounded nonpersonal DQ fixture definition differs")
    report, _derived, aggregate = dq._transform(definition, raw, _time("2027-06-03T09:00:00Z"))
    if (
        report["status"] != "LOCAL_RULES_PASSED_NOT_SOURCE_ACCEPTANCE"
        or aggregate["accepted_rows_only_total"] != 23
    ):
        raise CompanyStoreError("DQ source baseline no longer passes local rules")
    gap = json.loads(
        (
            repository
            / "enterprise/audit_suite/DATA_RECORD_PHI_50_ROUTE_GAP_LEDGER_2026-09-29.json"
        ).read_bytes()
    )
    selected = [
        r
        for r in gap["task_rows"]
        if r["control_id"] in {"SH-DAT-004", "SH-REC-001", "SH-REC-002", "SH-REC-003"}
    ]
    if len(selected) != 17 or any(
        r["task_status_at_frozen_matrix"] != "NOT_STARTED"
        or r["task_conclusion_at_frozen_matrix"] != "NOT_RUN"
        or r["audit_task_credit"] is not False
        for r in selected
    ):
        raise CompanyStoreError("C3 task-route scope differs")
    task_ids = {side: sorted(r["task_ids"][side] for r in selected) for side in "AB"}
    if any(len(set(ids)) != 17 for ids in task_ids.values()):
        raise CompanyStoreError("C3 task denominator differs")
    for relative, before in frozen.items():
        if _private_file(private_repository / relative, db=relative.endswith(".sqlite3")) != before:
            raise CompanyStoreError("DQ source changed during bounded read")
    return {
        "pins": pins,
        "frozen": frozen,
        "source_refs": {k: v["ref"] for k, v in rows.items()},
        "raw_bytes": rows["raw"]["content"],
        "definition": definition,
        "raw_rows": raw,
        "task_ids": task_ids,
        "source_db_path": source_path,
    }


def _when(hour: int, minute: int = 0) -> str:
    return _time(f"2027-06-03T{hour:02d}:{minute:02d}:00Z")


def _available(event_at: str) -> str:
    return _time((datetime.fromisoformat(event_at) + timedelta(minutes=1)).isoformat())


def _expected_rows(context: dict, scenario: str) -> list[dict]:
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown integrity branch")
    branch = BRANCHES[scenario]
    original = context["raw_bytes"]
    altered_rows = deepcopy(context["raw_rows"])
    altered_rows[2]["units"] = "9"
    altered = encoded(altered_rows)
    if sha(altered) == sha(original) or altered_rows[2]["record_id"] != "R3":
        raise CompanyStoreError("Predeclared single-row alteration differs")
    report_bad, derived_bad, aggregate_bad = dq._transform(
        context["definition"], altered_rows, _when(9, 30)
    )
    report_good, derived_good, aggregate_good = dq._transform(
        context["definition"], context["raw_rows"], _when(11, 20)
    )
    if (
        report_bad["status"] != "PARTIAL_UNRELIABLE"
        or report_bad["failed_rows"] != 1
        or aggregate_bad["accepted_rows_only_total"] != 14
        or report_good["status"] != "LOCAL_RULES_PASSED_NOT_SOURCE_ACCEPTANCE"
        or aggregate_good["accepted_rows_only_total"] != 23
    ):
        raise CompanyStoreError("DQ transform causal outcome differs")
    rows: list[dict] = []
    by_name: dict[str, dict] = {}
    prior = None

    def add(
        name: str,
        system: str,
        record: str,
        version: int,
        at: str,
        data: dict | bytes,
        *,
        actor: str | None = None,
        copy_file: str | None = None,
    ) -> None:
        nonlocal prior
        event = _when(*map(int, at.split(":")))
        available = _available(event)
        responsible = actor or SYSTEM_OWNERS[system]
        if isinstance(data, bytes):
            content = data
        else:
            body = {
                "schema": SCHEMA,
                "scenario": scenario,
                "branch": branch,
                "system": system,
                "record": record,
                "version": version,
                "event_at": event,
                "available_at": available,
                "actor_person_id": responsible,
                "actor_authority_limit": "PROPOSED_LOCAL_TEST_ROLE_NO_ENTERPRISE_ACCEPTANCE",
                "source_previous": prior,
                "source_refs": context["source_refs"],
                "expected_record_ids": ["R1", "R2", "R3", "R4"],
                "payload_class": "NONPERSONAL_LOCAL_FIXTURE_ONLY",
                "real_world_personal_data": False,
                "real_world_operation": False,
                "audit_task_credit": False,
                "qualification": QUALIFICATION,
                **data,
            }
            content = encoded(body)
        ref = {
            "company": COMPANY,
            "branch": branch,
            "system": system,
            "record": record,
            "version": version,
            "sha256": sha(content),
            "event_at": event,
            "available_at": available,
        }
        provenance = {
            "source_reference": SOURCE_REF,
            "source_pins": context["pins"],
            "scenario": scenario,
            "qualification": QUALIFICATION,
            "actor_person_id": responsible,
            "source_previous": prior,
            "copy_file": copy_file,
        }
        rows.append(
            {
                "name": name,
                "ref": ref,
                "content": content,
                "provenance": provenance,
                "copy_file": copy_file,
            }
        )
        by_name[name] = ref
        prior = ref

    add(
        "extract",
        "extract_request",
        "EXTRACT-01",
        1,
        "09:00",
        {
            "action": "DECLARE_SELECTED_SOURCE_EXTRACT",
            "source_population_count": 4,
            "source_raw_ref": context["source_refs"]["raw"],
            "reference_ref": context["source_refs"]["reference"],
            "definition_ref": context["source_refs"]["definition"],
            "query_window": context["definition"]["plan"]["event_window"],
            "independent_local_denominator_only": True,
        },
    )
    add(
        "copy_v1",
        "test_copy",
        "COPY-01",
        1,
        "09:05",
        original,
        copy_file=f"copies/{scenario}/v1-original.json",
    )
    add(
        "plan",
        "alteration_plan",
        "PLAN-01",
        1,
        "09:10",
        {
            "action": "PREDECLARE_SYNTHETIC_UNAUTHORIZED_ALTERATION",
            "target_record_id": "R3",
            "target_index": 2,
            "field": "units",
            "old_value": 9,
            "new_value": "9",
            "before_row_sha256": sha(encoded(context["raw_rows"][2])),
            "after_row_sha256": sha(encoded(altered_rows[2])),
            "source_copy_sha256": sha(original),
            "expected_altered_sha256": sha(altered),
            "simulated_unauthorized_actor": "SIM-UNAUTHORIZED-TEST-01",
            "actual_intrusion_asserted": False,
        },
    )
    add(
        "copy_v2",
        "test_copy",
        "COPY-01",
        2,
        "09:20",
        altered,
        copy_file=f"copies/{scenario}/v2-altered.json",
    )

    def transform(tag: str, version: int, at: tuple[str, str, str], *, bad: bool) -> None:
        report, derived, aggregate = (
            (report_bad, derived_bad, aggregate_bad)
            if bad
            else (report_good, derived_good, aggregate_good)
        )
        add(
            f"{tag}_report",
            "transform_report",
            "REPORT-01",
            version,
            at[0],
            {
                "action": "RUN_PINNED_LOCAL_DQ_TRANSFORM",
                "input_copy_ref": by_name["copy_v2" if bad else "copy_v3"],
                "integrity_check_ref": None if bad else by_name["check_v2"],
                "integrity_state_at_transform": "NOT_CHECKED"
                if bad
                else "CORRECTED_COPY_MATCHES_SOURCE",
                "dq_report": report,
                "source_acceptance": "NOT_ESTABLISHED",
            },
        )
        add(
            f"{tag}_derived",
            "derived_report",
            "REPORT-01",
            version,
            at[1],
            {
                "action": "RETAIN_DERIVED_ROWS",
                "transform_report_ref": by_name[f"{tag}_report"],
                "dq_derived": derived,
                "reliance": "NOT_RELIABLE" if bad else "LOCAL_TEST_ONLY_NOT_SOURCE_ACCEPTANCE",
            },
        )
        add(
            f"{tag}_aggregate",
            "aggregate_report",
            "REPORT-01",
            version,
            at[2],
            {
                "action": "RETAIN_ACCEPTED_ROWS_ONLY_AGGREGATE",
                "transform_report_ref": by_name[f"{tag}_report"],
                "derived_report_ref": by_name[f"{tag}_derived"],
                "dq_aggregate": aggregate,
                "reliance": "NOT_RELIABLE" if bad else "LOCAL_TEST_ONLY_NOT_SOURCE_ACCEPTANCE",
            },
        )

    if scenario == "MESSY":
        transform("partial", 1, ("09:30", "09:32", "09:34"), bad=True)
        add(
            "visible",
            "internal_visibility",
            "VISIBILITY-01",
            1,
            "09:40",
            {
                "action": "EXPOSE_PARTIAL_REPORT_INTERNAL_ONLY",
                "status": "PARTIAL_UNRELIABLE",
                "partial_report_ref": by_name["partial_report"],
                "partial_derived_ref": by_name["partial_derived"],
                "partial_aggregate_ref": by_name["partial_aggregate"],
                "external_distribution": False,
                "qualified_reliance": False,
            },
        )
        check_at = "10:00"
    else:
        check_at = "09:30"
    add(
        "check_v1",
        "integrity_check",
        "CHECK-01",
        1,
        check_at,
        {
            "action": "INDEPENDENT_COPY_HASH_CHECK",
            "checked_copy_ref": by_name["copy_v2"],
            "expected_source_raw_sha256": sha(original),
            "observed_copy_sha256": sha(altered),
            "result": "MISMATCH_DETECTED",
            "checked_before_first_transform": scenario == "CLEAN",
        },
    )
    add(
        "quarantine",
        "copy_quarantine",
        "QUARANTINE-01",
        1,
        "09:35" if scenario == "CLEAN" else "10:05",
        {
            "action": "REJECT_ALTERED_COPY",
            "check_ref": by_name["check_v1"],
            "altered_copy_ref": by_name["copy_v2"],
            "historical_partial_report_ref": by_name.get("partial_report"),
            "status": "REJECTED_PRESERVED",
        },
    )
    add(
        "copy_v3",
        "test_copy",
        "COPY-01",
        3,
        "10:00" if scenario == "CLEAN" else "11:00",
        original,
        copy_file=f"copies/{scenario}/v3-corrected.json",
    )
    add(
        "check_v2",
        "integrity_check",
        "CHECK-01",
        2,
        "10:10" if scenario == "CLEAN" else "11:10",
        {
            "action": "INDEPENDENT_CORRECTED_COPY_HASH_CHECK",
            "checked_copy_ref": by_name["copy_v3"],
            "expected_source_raw_sha256": sha(original),
            "observed_copy_sha256": sha(original),
            "result": "MATCH_AFTER_CORRECTION",
            "historical_mismatch_ref": by_name["check_v1"],
        },
    )
    if scenario == "CLEAN":
        transform("corrected", 1, ("10:20", "10:22", "10:24"), bad=False)
    else:
        transform("corrected", 2, ("11:20", "11:22", "11:24"), bad=False)
        add(
            "lineage",
            "correction_lineage",
            "LINEAGE-01",
            1,
            "11:30",
            {
                "action": "LINK_HISTORICAL_PARTIAL_TO_CORRECTED_REPORT",
                "old_partial_report_ref": by_name["partial_report"],
                "old_partial_derived_ref": by_name["partial_derived"],
                "old_partial_aggregate_ref": by_name["partial_aggregate"],
                "corrected_report_ref": by_name["corrected_report"],
                "corrected_derived_ref": by_name["corrected_derived"],
                "corrected_aggregate_ref": by_name["corrected_aggregate"],
                "historical_partial_still_unreliable": True,
                "retroactive_rewrite": False,
            },
        )
    add(
        "review",
        "local_test_review",
        "REVIEW-01",
        1,
        "10:30" if scenario == "CLEAN" else "11:40",
        {
            "action": "ACCEPT_CORRECTED_LOCAL_TEST_TRANSFORM_ONLY",
            "corrected_check_ref": by_name["check_v2"],
            "corrected_report_ref": by_name["corrected_report"],
            "corrected_aggregate_ref": by_name["corrected_aggregate"],
            "historical_partial_report_ref": by_name.get("partial_report"),
            "status": "LOCAL_TEST_RESULT_ACCEPTED_NOT_SOURCE_ACCEPTANCE",
            "enterprise_data_accuracy_approved": False,
            "audit_reliance_approved": False,
        },
    )
    return rows


def _write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def _write_copy(path: Path, content: bytes) -> dict:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    path.parent.parent.chmod(0o700)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    info = path.stat()
    return {
        "path": str(path.relative_to(path.parents[2])),
        "sha256": sha(content),
        "size": len(content),
        "inode": info.st_ino,
        "mode": stat.S_IMODE(info.st_mode),
    }


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Create isolated company originals; never open an engagement or audit store."""
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or destination != destination.resolve()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in destination.parents)
    ):
        raise CompanyStoreError("New canonical private destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(prefix=".integrity-stage-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records, copies = {}, {}
        for scenario, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            records[scenario], copies[scenario] = [], []
            for item in _expected_rows(context, scenario):
                ref = item["ref"]
                if item["copy_file"] is not None:
                    copy = _write_copy(stage / item["copy_file"], item["content"])
                    if (
                        copy["sha256"] != ref["sha256"]
                        or copy["inode"]
                        == context["frozen"][f"{DQ_ROOT}/run-v1/a/company.sqlite3"][1]
                    ):
                        raise CompanyStoreError("Disposable copy not isolated from DQ original")
                    copies[scenario].append(copy)
                native = store.append_version(
                    COMPANY,
                    branch,
                    ref["system"],
                    ref["record"],
                    expected_version=ref["version"] - 1,
                    command_id=f"IC-{branch}-{item['name']}",
                    event_at=ref["event_at"],
                    available_at=ref["available_at"],
                    content=item["content"],
                    provenance=item["provenance"],
                )
                if any(native[k] != ref[k] for k in ref):
                    raise CompanyStoreError("Native integrity chain differs during creation")
                records[scenario].append(native)
        receipt = {
            "schema": SCHEMA,
            "status": "FUTURE_FICTIONAL_DISPOSABLE_INTEGRITY_CHAIN_NO_CREDIT",
            "as_of": AS_OF,
            "company": COMPANY,
            "branches": BRANCHES,
            "source_pins": context["pins"],
            "source_original_db_fingerprint": context["frozen"][
                f"{DQ_ROOT}/run-v1/a/company.sqlite3"
            ],
            "source_native_refs": context["source_refs"],
            "selected_route_task_ids": context["task_ids"],
            "records": records,
            "copies": copies,
            "counts": {"CLEAN": len(records["CLEAN"]), "MESSY": len(records["MESSY"])},
            "limits": LIMITS,
            "audit_task_credit": False,
        }
        _write_json(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": sum(map(len, records.values())),
            "copy_file_count": 6,
            "audit_task_credit": False,
        }
        _write_json(stage / "MANIFEST.json", manifest)
        if (
            _private_file(context["source_db_path"], db=True)
            != context["frozen"][f"{DQ_ROOT}/run-v1/a/company.sqlite3"]
        ):
            raise CompanyStoreError("DQ original changed during C3 creation")
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Recompute DQ outcomes and all immutable company/copy/source joins."""
    root = Path(destination).absolute()
    if (
        root != root.resolve()
        or not root.is_dir()
        or root.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in (root, *root.parents))
        or {p.name for p in root.iterdir()}
        != {"MANIFEST.json", "RECEIPT.json", "company.sqlite3", "copies"}
    ):
        raise CompanyStoreError("Private ordinary integrity source required")
    before = {
        name: _private_file(root / name, db=name == "company.sqlite3")
        for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3")
    }
    manifest = json.loads((root / "MANIFEST.json").read_bytes())
    receipt = json.loads((root / "RECEIPT.json").read_bytes())
    context = _context(repository, private_repository)
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": before["RECEIPT.json"][-1],
        "company_db_sha256": before["company.sqlite3"][-1],
        "module_sha256": _digest(Path(__file__)),
        "native_version_count": 29,
        "copy_file_count": 6,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Integrity manifest differs")
    if receipt != {
        "schema": SCHEMA,
        "status": "FUTURE_FICTIONAL_DISPOSABLE_INTEGRITY_CHAIN_NO_CREDIT",
        "as_of": AS_OF,
        "company": COMPANY,
        "branches": BRANCHES,
        "source_pins": context["pins"],
        "source_original_db_fingerprint": list(
            context["frozen"][f"{DQ_ROOT}/run-v1/a/company.sqlite3"]
        ),
        "source_native_refs": context["source_refs"],
        "selected_route_task_ids": context["task_ids"],
        "records": receipt.get("records"),
        "copies": receipt.get("copies"),
        "counts": {"CLEAN": 12, "MESSY": 17},
        "limits": LIMITS,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Integrity receipt scope differs")
    copy_root = root / "copies"
    if (
        not copy_root.is_dir()
        or copy_root.is_symlink()
        or stat.S_IMODE(copy_root.stat().st_mode) != 0o700
        or {p.name for p in copy_root.iterdir()} != set(BRANCHES)
    ):
        raise CompanyStoreError("Exactly two private disposable copies required")
    seen_inodes = {context["frozen"][f"{DQ_ROOT}/run-v1/a/company.sqlite3"][1]}
    copy_before = {}
    for scenario in BRANCHES:
        folder = copy_root / scenario
        if (
            not folder.is_dir()
            or folder.is_symlink()
            or stat.S_IMODE(folder.stat().st_mode) != 0o700
            or {p.name for p in folder.iterdir()}
            != {"v1-original.json", "v2-altered.json", "v3-corrected.json"}
        ):
            raise CompanyStoreError("Disposable copy versions differ")
        expected_copy_items = [row for row in _expected_rows(context, scenario) if row["copy_file"]]
        if len(receipt["copies"][scenario]) != 3:
            raise CompanyStoreError("Copy receipt denominator differs")
        for item, metadata in zip(expected_copy_items, receipt["copies"][scenario], strict=True):
            path = root / item["copy_file"]
            fingerprint = _private_file(path)
            copy_before[item["copy_file"]] = fingerprint
            if (
                metadata
                != {
                    "path": item["copy_file"],
                    "sha256": item["ref"]["sha256"],
                    "size": len(item["content"]),
                    "inode": fingerprint[1],
                    "mode": 0o600,
                }
                or path.read_bytes() != item["content"]
                or fingerprint[1] in seen_inodes
            ):
                raise CompanyStoreError("Disposable copy bytes/inode/lineage differ")
            seen_inodes.add(fingerprint[1])
    with closing(
        sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Integrity native DB failed quick check")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != count
            for table, count in (
                ("versions", 29),
                ("systems", 22),
                ("grants", 0),
                ("collections", 0),
                ("access_events", 0),
            )
        ):
            raise CompanyStoreError("Integrity source/access denominator differs")
        if {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        } != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("Integrity source owners differ")
        expected_keys = set()
        for scenario, branch in BRANCHES.items():
            expected = _expected_rows(context, scenario)
            refs = receipt["records"][scenario]
            if len(refs) != len(expected):
                raise CompanyStoreError("Integrity branch denominator differs")
            prior_import = None
            for item, ref in zip(expected, refs, strict=True):
                target = item["ref"]
                key = tuple(target[k] for k in ("company", "branch", "system", "record", "version"))
                expected_keys.add(key)
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    key,
                ).fetchone()
                if (
                    row is None
                    or row["content"] != item["content"]
                    or row["sha256"] != target["sha256"]
                    or sha(row["content"]) != target["sha256"]
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or json.loads(row["provenance"]) != item["provenance"]
                    or row["command_id"] != f"IC-{branch}-{item['name']}"
                    or any(row[k] != target[k] for k in ("event_at", "available_at"))
                    or any(ref[k] != target[k] for k in target)
                    or any(ref[k] != row[k] for k in ("imported_at", "origin", "sha256"))
                    or ref["provenance"] != item["provenance"]
                    or row["imported_at"] >= row["event_at"]
                    or (prior_import is not None and row["imported_at"] < prior_import)
                ):
                    raise CompanyStoreError(
                        "Integrity native content, hash, provenance or clocks differ"
                    )
                prior_import = row["imported_at"]
        if {
            tuple(row)
            for row in db.execute("SELECT company,branch,system,record,version FROM versions")
        } != expected_keys:
            raise CompanyStoreError("Unexpected integrity native row")
    if {
        name: _private_file(root / name, db=name == "company.sqlite3") for name in before
    } != before:
        raise CompanyStoreError("Integrity run changed during read")
    if {name: _private_file(root / name) for name in copy_before} != copy_before:
        raise CompanyStoreError("Disposable copy changed during read")
    if (
        _private_file(context["source_db_path"], db=True)
        != context["frozen"][f"{DQ_ROOT}/run-v1/a/company.sqlite3"]
    ):
        raise CompanyStoreError("DQ original changed during verification")
    return manifest
