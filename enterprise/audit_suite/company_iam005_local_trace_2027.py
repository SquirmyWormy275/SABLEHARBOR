"""Separate local human/service ledgers for one nonpersonal IAM-005 object."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_IAM005_LOCAL_SAME_OBJECT_TRACE_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"CLEAN": "IAM005-TRACE-CLEAN", "MESSY": "IAM005-TRACE-MESSY"}
SPEC = "enterprise/audit_suite/iam005_local_same_object_spec_v1.json"
SOURCE_REFERENCE = "enterprise/audit_suite/company_iam005_local_trace_2027.py"
SOURCE_PINS = {
    SPEC: "a36b2705916da868a6aa85fd2988ef0f6fe52e8318fdcc3d0cf7eafc635720aa",
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
    "enterprise/ccf/assurance/design_data/control_procedures.json": (
        "258f5c868e16f3dc197594857dc86a4f2b3ef11e3e5a36dd0a80a9fc6d40c679"
    ),
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "docs/organization/source/chartbook.json": (
        "6ba4f1ed1a14581455a62c3e79a29ca59dbaf1270dfb0db850c0376c15507b49"
    ),
    "enterprise/audit_suite/PRIVILEGED_RUNTIME.md": (
        "2a82d383c44e940a871ec581247db61c00c2fe68b89f652c71cf26bf539dad1c"
    ),
    "enterprise/audit_suite/NONHUMAN_RUNTIME.md": (
        "8bad1889a2217a967155fabb341fc399cb4c21b99e0388917e4687029e2fc057"
    ),
}
ROUTE_AUTHORITY = {
    "matrix_path": (
        "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/"
        "run-v2/MATRIX.json"
    ),
    "matrix_sha256": "e9477d2074bebce185e412a3ee7c424ded395c1a1128a7c918a94f6acbd1e327",
    "review_path": (
        "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/"
        "independent-review-v2/REVIEW.json"
    ),
    "review_sha256": "c4064f6217c0e7f69276adc71004d6da7971867ccf3d844a3e198145cec31ace",
}
AUTHORED = {
    "ACTION-H-EMERGENCY": (
        "Observe an approved emergency-mode exercise; verify necessary ePHI remains "
        "accessible to authorized operators and access decisions and activity survive recovery."
    ),
    "CHECK-SOC2:CC6.1": (
        "Trace a human and service identity through each trust boundary and resource "
        "permission; test unauthorized access, key/credential protection and a privileged path."
    ),
}
SYSTEM_OWNERS = {
    "human": {"local_object": "AS-P007", "human_access": "AS-P007", "human_review": "AS-P008"},
    "service": {
        "local_object": "AS-P007",
        "service_identity": "AS-P007",
        "service_access": "AS-P007",
        "service_review": "AS-P008",
    },
}
LIMITS = [
    "Future local nonpersonal exercise; actual imported_at remains 2026 creation time.",
    "Separate human and inert service native ledgers share one exact local object ID and byte SHA.",
    "No usable secret, host or vendor account, corporate approval, real trust-boundary deployment, "
    "ePHI emergency use, enterprise population, professional review or actual operation.",
    "Both authored IAM-005 clauses remain unsupported; all five paired tasks remain uncredited.",
    "Historical privileged-runtime DB journal drift is not transplanted into this exercise.",
    "No active P1 grant, collection, task, workpaper, Key or Atlas mutation.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private(path: Path, *, directory: bool) -> Path:
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise CompanyStoreError("Private alias forbidden")
    info = path.stat()
    if directory:
        if not path.is_dir() or stat.S_IMODE(info.st_mode) != 0o700:
            raise CompanyStoreError("Private 0700 directory required")
    elif (
        not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise CompanyStoreError("Private 0600 regular file required")
    return path


def _frozen(paths: dict[str, Path]) -> dict[str, tuple]:
    for path in paths.values():
        if path.name == "company.sqlite3" and any(
            Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
            for suffix in ("-wal", "-shm", "-journal")
        ):
            raise CompanyStoreError("Frozen native DB has sidecar")
    result = {}
    for name, path in paths.items():
        _private(path, directory=False)
        info = path.stat()
        result[name] = (
            info.st_dev,
            info.st_ino,
            stat.S_IMODE(info.st_mode),
            info.st_size,
            info.st_mtime_ns,
            _digest(path),
        )
    return result


def _check_routes(matrix: dict) -> dict:
    if matrix.get("counts", {}).get("tasks_per_side") != 283:
        raise CompanyStoreError("Frozen route denominator differs")
    expected_ids = {
        f"TASK-SH-IAM-005-corporate-{suffix}"
        for suffix in (*AUTHORED, "IMPLEMENTATION", "TOD", "TOE")
    }
    output = {}
    for side in "AB":
        found = [
            control
            for family in matrix["sides"][side]["families"]
            for control in family["controls"]
            if control["control_id"] == "SH-IAM-005"
        ]
        if len(found) != 1:
            raise CompanyStoreError("Selected IAM-005 control differs")
        rows = {row["task_id"]: row for row in found[0]["tasks"]}
        if set(rows) != expected_ids or len(rows) != 5:
            raise CompanyStoreError("Exact five selected IAM-005 routes differ")
        for task_id, task in rows.items():
            suffix = task_id.removeprefix("TASK-SH-IAM-005-corporate-")
            authored = suffix in AUTHORED
            if (
                task["procedure_type"] != ("ADDITIONAL_DUTY" if authored else suffix)
                or task["authored_test_clause"] != (AUTHORED[suffix] if authored else None)
                or task["test_gate_basis"]
                != (
                    "AUTHORED_TASK_CLAUSE"
                    if authored
                    else "GENERIC_PROCEDURE_GATE_NOT_AN_AUTHORED_CLAUSE"
                )
                or task["current_status"] != "NOT_STARTED"
                or task["current_conclusion"] != "NOT_RUN"
                or task["task_credit"] is not False
            ):
                raise CompanyStoreError("IAM-005 authored clause/status/credit differs")
        output[side] = {
            "task_ids": sorted(rows),
            "authored_clause_count": 2,
            "inferred_gate_count": 3,
            "task_rows_sha256": sha(encoded({key: rows[key] for key in sorted(rows)})),
        }
    if output["A"] != output["B"]:
        raise CompanyStoreError("Paired IAM-005 task authority differs")
    return output


def _context(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    for name, digest in SOURCE_PINS.items():
        path = repository / name
        if path.is_symlink() or not path.is_file() or _digest(path) != digest:
            raise CompanyStoreError("Pinned canon/spec/design bytes differ")
    spec = json.loads((repository / SPEC).read_text())
    raw = spec["object"]["text"].encode()
    if (
        spec["schema"] != "SH_FICTIONAL_IAM005_LOCAL_SAME_OBJECT_SPEC_V1"
        or spec["object"]["id"] != "LOCAL-IAM005-TRACE-OBJECT"
        or spec["object"]["contains_personal_or_phi_data"] is not False
        or spec["object"]["sha256"] != sha(raw)
        or len(raw) != 59
        or spec["human"]["principal_id"] != "SIM-LOCAL-HUMAN-01"
        or spec["human"]["right"] != "LOCAL_READ_ONLY"
        or spec["human"]["lease_expires_at"] != "2027-05-01T00:10:00+00:00"
        or spec["service"]["identity_id"] != "EXERCISE-SVC-IAM005-01"
        or spec["service"]["credential_kind"] != "INERT_INTEGER_VERSION_NO_USABLE_SECRET"
        or spec["service"]["initial_credential_version"] != 1
        or spec["contacts"] != {"local_operator": "AS-P007", "distinct_local_reviewer": "AS-P008"}
    ):
        raise CompanyStoreError("Selected local object/identity spec differs")
    chart = json.loads((repository / "docs/organization/source/chartbook.json").read_text())
    nodes = {n["id"]: n for n in chart["nodes"] if n.get("id") in {"AS-P007", "AS-P008"}}
    if set(nodes) != {"AS-P007", "AS-P008"} or any(
        n["title_state"] != "DELEGATED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE"
        for n in nodes.values()
    ):
        raise CompanyStoreError("Local actor contacts cannot be treated as approved roles")
    paths = {
        "matrix": private_repository / ROUTE_AUTHORITY["matrix_path"],
        "review": private_repository / ROUTE_AUTHORITY["review_path"],
    }
    before = {}
    for name, path in paths.items():
        _private(path, directory=False)
        info = path.stat()
        before[name] = (
            info.st_dev,
            info.st_ino,
            stat.S_IMODE(info.st_mode),
            info.st_size,
            info.st_mtime_ns,
            _digest(path),
        )
    if (
        before["matrix"][-1] != ROUTE_AUTHORITY["matrix_sha256"]
        or before["review"][-1] != ROUTE_AUTHORITY["review_sha256"]
    ):
        raise CompanyStoreError("Reviewed route authority byte pin differs")
    matrix = json.loads(paths["matrix"].read_text())
    review = json.loads(paths["review"].read_text())
    if (
        review.get("verdict") != "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION"
        or review.get("matrix_sha256") != ROUTE_AUTHORITY["matrix_sha256"]
        or review.get("audit_task_credit") is not False
        or review.get("active_P1_mutated") is not False
    ):
        raise CompanyStoreError("Reviewed route authority status differs")
    selected = _check_routes(matrix)
    for name, path in paths.items():
        info = path.stat()
        after = (
            info.st_dev,
            info.st_ino,
            stat.S_IMODE(info.st_mode),
            info.st_size,
            info.st_mtime_ns,
            _digest(path),
        )
        if after != before[name]:
            raise CompanyStoreError("Reviewed route authority changed during read")
    return {
        "spec": spec,
        "raw": raw,
        "selected_routes": selected,
        "role_states": {key: nodes[key]["title_state"] for key in sorted(nodes)},
    }


def _authorized_human(spec: dict, at: str, principal: str, resource: str) -> bool:
    return (
        principal == spec["human"]["principal_id"]
        and resource == spec["object"]["id"]
        and _time("2027-05-01T00:04:00+00:00")
        <= _time(at)
        < _time(spec["human"]["lease_expires_at"])
    )


def _authorized_service(spec: dict, resource_ids: list[str], version: int, current: int) -> bool:
    return resource_ids == [spec["object"]["id"]] and version == current


def _rows(context: dict, scenario: str, ledger: str) -> list[dict]:
    if scenario not in BRANCHES or ledger not in SYSTEM_OWNERS:
        raise CompanyStoreError("Unknown local trace branch/ledger")
    spec, raw = context["spec"], context["raw"]
    messy = scenario == "MESSY"
    object_id = spec["object"]["id"]
    human_id = spec["human"]["principal_id"]
    service_id = spec["service"]["identity_id"]
    common = {
        "schema": SCHEMA,
        "scenario": scenario,
        "ledger": ledger,
        "truth_class": "FUTURE_NONPERSONAL_LOCAL_EXERCISE_ONLY",
        "object_id": object_id,
        "object_sha256": sha(raw),
        "object_bytes": len(raw),
        "actual_phi_or_personal_data": False,
        "usable_secret_or_host_account": False,
        "real_trust_boundary_or_deployment": False,
        "corporate_approval": False,
        "emergency_ephi_mode": False,
        "enterprise_population_complete": False,
        "professional_review": False,
        "audit_task_credit": False,
        "actor_role_limit": "PROPOSED_CONTACT_LOCAL_EXERCISE_ONLY",
    }
    object_at = "2027-05-01T00:00:00+00:00"
    if ledger == "human":
        events = [
            (
                "human_access",
                "RULE-01",
                "2027-05-01T00:02:00+00:00",
                {
                    "action": "LOCAL_RULE_DECLARED_NOT_CORPORATE_APPROVAL",
                    "principal_id": human_id,
                    "resource_id": object_id,
                    "right": spec["human"]["right"],
                    "lease_expires_at": spec["human"]["lease_expires_at"],
                },
            ),
            (
                "human_access",
                "LEASE-01",
                "2027-05-01T00:04:00+00:00",
                {
                    "action": "LOCAL_LEASE_ISSUED",
                    "principal_id": human_id,
                    "resource_id": object_id,
                    "expires_at": spec["human"]["lease_expires_at"],
                    "approval_status": "LOCAL_RULE_ONLY_NO_CORPORATE_PRIVILEGE_APPROVAL",
                },
            ),
            (
                "human_access",
                "SESSION-01",
                "2027-05-01T00:05:00+00:00",
                {
                    "action": "LOCAL_SESSION_OPENED",
                    "session_id": "SIM-LOCAL-SESSION-01",
                    "principal_id": human_id,
                    "resource_id": object_id,
                    "lease_record_id": "LEASE-01",
                    "host_or_network_session_created": False,
                },
            ),
            (
                "human_access",
                "READ-01",
                "2027-05-01T00:06:00+00:00",
                {
                    "action": "LOCAL_HUMAN_READ",
                    "session_id": "SIM-LOCAL-SESSION-01",
                    "principal_id": human_id,
                    "resource_id": object_id,
                    "result": "AUTHORIZED"
                    if _authorized_human(spec, "2027-05-01T00:06:00+00:00", human_id, object_id)
                    else "DENIED",
                    "read_sha256": sha(raw),
                    "read_bytes": len(raw),
                },
            ),
        ]
        if messy:
            events.append(
                (
                    "human_access",
                    "READ-EXPIRED-01",
                    "2027-05-01T00:20:00+00:00",
                    {
                        "action": "LOCAL_POST_EXPIRY_READ_ATTEMPT",
                        "session_id": "SIM-LOCAL-SESSION-01",
                        "principal_id": human_id,
                        "resource_id": object_id,
                        "result": "DENIED"
                        if not _authorized_human(
                            spec, "2027-05-01T00:20:00+00:00", human_id, object_id
                        )
                        else "AUTHORIZED",
                        "read_sha256": None,
                        "read_bytes": 0,
                        "original_denial_retained": True,
                    },
                )
            )
        events.extend(
            [
                (
                    "human_access",
                    "REVOKE-01",
                    "2027-05-01T00:30:00+00:00" if messy else "2027-05-01T00:08:00+00:00",
                    {
                        "action": "LOCAL_LEASE_REVOKED",
                        "session_id": "SIM-LOCAL-SESSION-01",
                        "local_session_closed": True,
                        "principal_id": human_id,
                        "resource_id": object_id,
                        "post_expiry_attempt_remains": messy,
                    },
                ),
                (
                    "human_review",
                    "REVIEW-01",
                    "2027-05-01T02:00:00+00:00" if messy else "2027-05-01T01:00:00+00:00",
                    {
                        "action": "DISTINCT_LOCAL_CONTACT_REVIEW",
                        "reviewer_id": "AS-P008",
                        "operator_id": "AS-P007",
                        "review_due_at": _time(spec["local_review_due_at"]),
                        "review_timely": not messy,
                        "post_expiry_denial_count": int(messy),
                        "open_timing_exception_id": "EXC-SIM-IAM005-HUMAN-LATE-REVIEW-01"
                        if messy
                        else None,
                    },
                ),
            ]
        )
    else:
        events = [
            (
                "service_identity",
                "IDENTITY-01",
                "2027-05-01T00:02:00+00:00",
                {
                    "action": "INERT_LOCAL_SERVICE_IDENTITY_DEFINED",
                    "identity_id": service_id,
                    "owner_contact_id": "AS-P007",
                    "purpose": spec["service"]["purpose"],
                    "allowed_resource_ids": [object_id],
                    "credential_version": 1,
                    "credential_kind": spec["service"]["credential_kind"],
                },
            ),
        ]
        if messy:
            excessive = [object_id, "LOCAL-OTHER-OBJECT"]
            events.extend(
                [
                    (
                        "service_access",
                        "READ-EXCESS-01",
                        "2027-05-01T00:10:00+00:00",
                        {
                            "action": "EXCESSIVE_LOCAL_SERVICE_READ_REQUEST",
                            "identity_id": service_id,
                            "requested_resource_ids": excessive,
                            "credential_version": 1,
                            "result": "DENIED"
                            if not _authorized_service(spec, excessive, 1, 1)
                            else "AUTHORIZED",
                            "read_sha256": None,
                            "read_bytes": 0,
                        },
                    ),
                    (
                        "service_identity",
                        "SCOPE-CORRECTION-01",
                        "2027-05-01T00:12:00+00:00",
                        {
                            "action": "LOCAL_REQUEST_SCOPE_NARROWED",
                            "identity_id": service_id,
                            "corrected_resource_ids": [object_id],
                            "original_excess_request_retained": True,
                        },
                    ),
                ]
            )
        first_at = "2027-05-01T00:14:00+00:00" if messy else "2027-05-01T00:10:00+00:00"
        events.append(
            (
                "service_access",
                "READ-01",
                first_at,
                {
                    "action": "LOCAL_INERT_SERVICE_READ",
                    "identity_id": service_id,
                    "requested_resource_ids": [object_id],
                    "credential_version": 1,
                    "result": "AUTHORIZED"
                    if _authorized_service(spec, [object_id], 1, 1)
                    else "DENIED",
                    "read_sha256": sha(raw),
                    "read_bytes": len(raw),
                },
            )
        )
        events.extend(
            [
                (
                    "service_identity",
                    "ROTATE-01",
                    "2027-05-01T00:16:00+00:00" if messy else "2027-05-01T00:12:00+00:00",
                    {
                        "action": "INERT_VERSION_ADVANCED",
                        "identity_id": service_id,
                        "old_version": 1,
                        "current_version": 2,
                        "secret_material_generated": False,
                    },
                ),
                (
                    "service_access",
                    "READ-STALE-01",
                    "2027-05-01T00:18:00+00:00" if messy else "2027-05-01T00:14:00+00:00",
                    {
                        "action": "STALE_INERT_VERSION_READ_ATTEMPT",
                        "identity_id": service_id,
                        "requested_resource_ids": [object_id],
                        "credential_version": 1,
                        "result": "DENIED"
                        if not _authorized_service(spec, [object_id], 1, 2)
                        else "AUTHORIZED",
                        "read_sha256": None,
                        "read_bytes": 0,
                        "original_denial_retained": True,
                    },
                ),
                (
                    "service_review",
                    "REVIEW-01",
                    "2027-05-01T02:00:00+00:00" if messy else "2027-05-01T01:00:00+00:00",
                    {
                        "action": "DISTINCT_LOCAL_CONTACT_REVIEW",
                        "reviewer_id": "AS-P008",
                        "operator_id": "AS-P007",
                        "review_due_at": _time(spec["local_review_due_at"]),
                        "review_timely": not messy,
                        "excess_scope_denial_count": int(messy),
                        "stale_version_denial_count": 1,
                        "open_timing_exception_id": "EXC-SIM-IAM005-SERVICE-LATE-REVIEW-01"
                        if messy
                        else None,
                    },
                ),
            ]
        )
    rows = []
    previous = None

    def emit(
        system: str,
        record: str,
        at: str,
        *,
        body: dict | None = None,
        raw_content: bytes | None = None,
    ):
        nonlocal previous
        event = _time(at)
        available = _time((datetime.fromisoformat(at) + timedelta(minutes=1)).isoformat())
        if previous is not None and previous["available_at"] > event:
            raise CompanyStoreError("Local source event predates predecessor availability")
        value = (
            None
            if raw_content is not None
            else {
                **common,
                "system": system,
                "record": record,
                "actor_id": "AS-P008" if system.endswith("review") else "AS-P007",
                "event_at": event,
                "available_at": available,
                "source_previous": previous,
                **(body or {}),
            }
        )
        content = raw_content if raw_content is not None else encoded(value)
        item = {
            "system": system,
            "record": record,
            "version": 1,
            "event_at": event,
            "available_at": available,
            "content": content,
            "body": value,
            "sha256": sha(content),
        }
        rows.append(item)
        previous = {
            key: item[key]
            for key in ("system", "record", "version", "sha256", "event_at", "available_at")
        }

    emit("local_object", object_id, object_at, raw_content=raw)
    for system, record, at, body in events:
        emit(system, record, at, body=body)
    return rows


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    _private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("New private trace destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(prefix=".iam005-stage-", dir=destination.parent) as temp:
        stage = Path(temp)
        records = {side: {ledger: [] for ledger in SYSTEM_OWNERS} for side in BRANCHES}
        for ledger, owners in SYSTEM_OWNERS.items():
            ledger_root = stage / ledger
            ledger_root.mkdir(mode=0o700)
            store = CompanyStore(ledger_root)
            for scenario, branch in BRANCHES.items():
                for system, owner in owners.items():
                    store.register_system(COMPANY, branch, system, owner)
                for item in _rows(context, scenario, ledger):
                    ref = store.append_version(
                        COMPANY,
                        branch,
                        item["system"],
                        item["record"],
                        expected_version=0,
                        command_id=f"I5-{ledger}-{branch}-{item['record']}",
                        event_at=item["event_at"],
                        available_at=item["available_at"],
                        content=item["content"],
                        provenance={
                            "source_reference": SOURCE_REFERENCE,
                            "scenario": scenario,
                            "ledger": ledger,
                            "source_pins": SOURCE_PINS,
                            "route_authority_pins": ROUTE_AUTHORITY,
                            "qualification": "LOCAL_FUTURE_NONPERSONAL_NO_AUDIT_CREDIT",
                        },
                    )
                    if ref["sha256"] != item["sha256"]:
                        raise CompanyStoreError("Local trace source serialization differs")
                    records[scenario][ledger].append(ref)
        selected = context["selected_routes"]
        receipt = {
            "schema": SCHEMA,
            "company": COMPANY,
            "branches": BRANCHES,
            "records": records,
            "source_pins": SOURCE_PINS,
            "route_authority_pins": ROUTE_AUTHORITY,
            "selected_route_authority": selected,
            "object_id": context["spec"]["object"]["id"],
            "object_sha256": sha(context["raw"]),
            "object_byte_count": len(context["raw"]),
            "separate_native_ledgers": ["human", "service"],
            "native_version_counts": {
                side: {ledger: len(refs) for ledger, refs in ledgers.items()}
                for side, ledgers in records.items()
            },
            "authored_iam005_clause_support": False,
            "actual_operation_eligibility_as_of_2026_09_29": False,
            "audit_task_credit": False,
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "human_db_sha256": _digest(stage / "human/company.sqlite3"),
            "service_db_sha256": _digest(stage / "service/company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": sum(
                len(refs) for ledgers in records.values() for refs in ledgers.values()
            ),
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return manifest


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = _private(destination, directory=True)
    _private(root / "human", directory=True)
    _private(root / "service", directory=True)
    paths = {
        "manifest": root / "MANIFEST.json",
        "receipt": root / "RECEIPT.json",
        "human_db": root / "human/company.sqlite3",
        "service_db": root / "service/company.sqlite3",
    }
    before = _frozen(paths)
    manifest = json.loads(paths["manifest"].read_text())
    receipt = json.loads(paths["receipt"].read_text())
    context = _context(repository, private_repository)
    expected_counts = {
        side: {ledger: len(_rows(context, side, ledger)) for ledger in SYSTEM_OWNERS}
        for side in BRANCHES
    }
    total = sum(sum(x.values()) for x in expected_counts.values())
    if (
        manifest.get("schema") != SCHEMA + "_MANIFEST"
        or manifest.get("receipt_sha256") != before["receipt"][-1]
        or manifest.get("human_db_sha256") != before["human_db"][-1]
        or manifest.get("service_db_sha256") != before["service_db"][-1]
        or manifest.get("module_sha256") != _digest(Path(__file__))
        or manifest.get("native_version_count") != total
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != SCHEMA
        or receipt.get("company") != COMPANY
        or receipt.get("branches") != BRANCHES
        or receipt.get("source_pins") != SOURCE_PINS
        or receipt.get("route_authority_pins") != ROUTE_AUTHORITY
        or receipt.get("selected_route_authority") != context["selected_routes"]
        or receipt.get("object_id") != context["spec"]["object"]["id"]
        or receipt.get("object_sha256") != sha(context["raw"])
        or receipt.get("object_byte_count") != len(context["raw"])
        or receipt.get("separate_native_ledgers") != ["human", "service"]
        or receipt.get("native_version_counts") != expected_counts
        or receipt.get("authored_iam005_clause_support") is not False
        or receipt.get("actual_operation_eligibility_as_of_2026_09_29") is not False
        or receipt.get("audit_task_credit") is not False
        or receipt.get("limits") != LIMITS
        or set(receipt.get("records", {})) != set(BRANCHES)
    ):
        raise CompanyStoreError("IAM-005 local trace manifest/receipt scope differs")
    for ledger, owners in SYSTEM_OWNERS.items():
        with closing(
            sqlite3.connect(paths[ledger + "_db"].as_uri() + "?mode=ro&immutable=1", uri=True)
        ) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise CompanyStoreError("IAM-005 local ledger database integrity differs")
            if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != sum(
                expected_counts[s][ledger] for s in BRANCHES
            ) or any(
                db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("grants", "collections", "access_events")
            ):
                raise CompanyStoreError("IAM-005 local native/audit-access count differs")
            expected_systems = {
                (COMPANY, branch, system, owner)
                for branch in BRANCHES.values()
                for system, owner in owners.items()
            }
            if {
                tuple(x) for x in db.execute("SELECT company,branch,system,owner FROM systems")
            } != expected_systems:
                raise CompanyStoreError("IAM-005 local ledger custody differs")
            for scenario, branch in BRANCHES.items():
                rows = _rows(context, scenario, ledger)
                refs = receipt["records"][scenario][ledger]
                if len(rows) != len(refs):
                    raise CompanyStoreError("IAM-005 local branch row count differs")
                provenance = {
                    "source_reference": SOURCE_REFERENCE,
                    "scenario": scenario,
                    "ledger": ledger,
                    "source_pins": SOURCE_PINS,
                    "route_authority_pins": ROUTE_AUTHORITY,
                    "qualification": "LOCAL_FUTURE_NONPERSONAL_NO_AUDIT_CREDIT",
                }
                for ref, item in zip(refs, rows, strict=True):
                    row = db.execute(
                        "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                        "AND record=? AND version=1",
                        (COMPANY, branch, item["system"], item["record"]),
                    ).fetchone()
                    if (
                        row is None
                        or ref["company"] != COMPANY
                        or ref["branch"] != branch
                        or any(
                            ref[k] != item[k]
                            for k in (
                                "system",
                                "record",
                                "version",
                                "sha256",
                                "event_at",
                                "available_at",
                            )
                        )
                        or ref["imported_at"] != row["imported_at"]
                        or ref["origin"] != "AUTHORED_TRAINING_SOURCE"
                        or ref["provenance"] != provenance
                        or json.loads(row["provenance"]) != provenance
                        or row["content"] != item["content"]
                        or row["sha256"] != item["sha256"]
                        or (row["event_at"], row["available_at"])
                        != (item["event_at"], item["available_at"])
                        or row["available_at"] < row["event_at"]
                        or row["imported_at"] >= row["event_at"]
                    ):
                        raise CompanyStoreError("IAM-005 local native row differs")
    if _frozen(paths) != before:
        raise CompanyStoreError("IAM-005 frozen ledger changed during verify")
    return manifest
