"""Selected fictional POL004 due-time procedure trace; no effective policy or credit."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from . import company_policy_exception_2027_exercise as policy
from .company_store import CompanyStore, CompanyStoreError, _time
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_POL004_SELECTED_FICTIONAL_PROCEDURE_TRACE_2027_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
CONTROL = "SH-POL-004"
TASK = "TASK-SH-POL-004-corporate-CHECK-SOC2:CC5.3"
CLAUSE = (
    "Walk one policy into an executable trigger, responsible person, dated result and "
    "correction; reject an approved policy with no execution procedure."
)
BRANCHES = {"CLEAN": "POL004-PROCEDURE-CLEAN", "MESSY": "POL004-PROCEDURE-MESSY"}
SYSTEM_OWNERS = {
    "procedure_candidate": "AS-P005",
    "approval_gate": "AS-P005",
    "due_trigger": "AS-P005",
    "execution_trace": "AS-P005",
    "result_register": "AS-P005",
    "challenge": "AS-P003",
    "correction": "AS-P005",
    "exception_review": "AS-P003",
}
AS_OF = "2026-09-30"
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}
PROPOSAL = "enterprise/audit_suite/POL004_SELECTED_PROCEDURE_TRACE_2027_PROPOSAL.md"
MODULE = "enterprise/audit_suite/company_pol004_procedure_trace_2027.py"
ROUTE = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V11_2026-09-30.json"
ROUTE_REVIEW = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v11-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
SOURCE_RUN = "enterprise/generated/audit-suite/company-policy-exception-2026-09-29/run-v1"
SOURCE_REVIEW = (
    "enterprise/generated/audit-suite/company-policy-exception-2026-09-29/"
    "independent-review-main-v1/REVIEW.json"
)
CANON_PINS = {
    "docs/controls/CCF_POLICY_AND_ARTIFACT_INVENTORY_v0.1.md": (
        "395198400d72211716f26f7376dd362993e538d0c081fdaaee3d148d642ea0dd"
    ),
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
    "docs/controls/CCF_CONTROL_OBJECTIVES_v0.1.md": (
        "db7a189139b86fb51d684b6af3e681002b5e0f3f81c38c5bc15a61c20e4a59a3"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "docs/governance/CORPORATE_DOCUMENT_STANDARD_v0.1.md": (
        "0023bb32d4cac8739bc940a54714e46da936cb6ba30ce727556b219537129bbb"
    ),
    "enterprise/audit_suite/company_policy_exception_2027_exercise.py": (
        "e7a9c291bb735ed3641ffca2734ad97ea98d47a16749df5c4e9811cdedf3c872"
    ),
    PROPOSAL: "81c960abe654bda7d560079f589ee1181cbe29f691ebf1b4f17d9ef853c79bce",
    ROUTE: "41facc0f48c2f0fc4b9144366bb239131e54c1693fde2bcbfa9ded7360792299",
}
PRIVATE_PINS = {
    ROUTE_REVIEW: "5db6205b1afcbd578562345a7ff0af6a212b8cbf1c39139cb71a22590fd394a2",
    SOURCE_REVIEW: "70150ae8307b0ef0ef503d3f4031a72b3c9e36ab8a77d7746c9846464b715087",
    f"{SOURCE_RUN}/MANIFEST.json": (
        "e04fbe2c49d5dd0430f2f98f2180302504547c456fc979c9d494bd932eae2ec8"
    ),
    f"{SOURCE_RUN}/RECEIPT.json": (
        "0e3a5c079b43acbf9dc2e24da7bfddf51ea9a1ea3dcc900ab01316abbdf8d1a1"
    ),
    f"{SOURCE_RUN}/company.sqlite3": (
        "c9ddeec3ccb4d3aada560b07d4dccd68f35a8c713c12cdf95993f3e12ff24552"
    ),
}
SOURCE_FIELDS = (
    "company",
    "branch",
    "system",
    "record",
    "version",
    "event_at",
    "available_at",
    "imported_at",
    "sha256",
)
OWN_FIELDS = SOURCE_FIELDS
PLAN = {
    "CLEAN": (
        ("procedure_candidate", "CANDIDATE", "2027-05-01T09:17:00Z", ("BASELINE", "DRAFT", "PLAN")),
        ("approval_gate", "POLICY-ONLY-REJECT", "2027-05-01T09:19:00Z", ("DRAFT-HOLD",)),
        ("due_trigger", "DUE-TRIGGER", "2027-05-01T09:33:00Z", ("PLAN", "RECONCILE")),
        ("execution_trace", "EXECUTE", "2027-05-01T09:37:00Z", ("RECONCILE",)),
        ("result_register", "RESULT", "2027-05-01T09:39:00Z", ("RECONCILE",)),
        ("challenge", "REVIEW", "2027-05-01T09:50:00Z", ("DRAFT-HOLD", "RECONCILE")),
        ("result_register", "FINAL", "2027-05-01T09:55:00Z", ("RECONCILE",)),
    ),
    "MESSY": (
        ("procedure_candidate", "CANDIDATE", "2027-05-01T09:17:00Z", ("BASELINE", "DRAFT", "PLAN")),
        ("approval_gate", "POLICY-ONLY-REJECT", "2027-05-01T09:19:00Z", ("FALSE-RELEASE",)),
        ("due_trigger", "DUE-TRIGGER", "2027-05-01T09:33:00Z", ("PLAN", "MISSED-AT-DUE")),
        (
            "execution_trace",
            "EXECUTE",
            "2027-05-01T09:37:00Z",
            ("MISSED-AT-DUE", "EXCEPTION-REQUEST"),
        ),
        ("result_register", "FALSE-CLOSE", "2027-05-01T09:39:00Z", ("MISSED-AT-DUE",)),
        ("challenge", "CHALLENGE", "2027-05-01T09:47:00Z", ("MISSED-AT-DUE", "QUARANTINE")),
        ("correction", "CORRECTION", "2027-05-02T10:20:00Z", ("MISSED-AT-DUE", "LATE-RECONCILE")),
        ("exception_review", "EXPIRY-REVIEW", "2027-06-01T10:10:00Z", ("EXPIRY-ESCALATE",)),
        ("result_register", "FINAL", "2027-06-01T10:15:00Z", ("LATE-RECONCILE", "EXPIRY-ESCALATE")),
    ),
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_file(path: Path) -> tuple:
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise CompanyStoreError("Selected POL004 private alias forbidden")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1:
        raise CompanyStoreError("Selected POL004 ordinary 0600 single-link file required")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, _digest(path)


def _ref(row: dict) -> dict:
    return {key: row[key] for key in SOURCE_FIELDS}


def _context(repository: Path, private: Path) -> dict:
    if _p1_inventory(private) != P1_FREEZE:
        raise CompanyStoreError("Frozen P1 inventory differs")
    for name, expected in CANON_PINS.items():
        path = repository / name
        if not path.is_file() or path.is_symlink() or _digest(path) != expected:
            raise CompanyStoreError(f"POL004 canon or reviewed route pin differs: {name}")
    frozen = {}
    for name, expected in PRIVATE_PINS.items():
        path = private / name
        frozen[name] = _private_file(path)
        if frozen[name][-1] != expected:
            raise CompanyStoreError(f"POL004 reviewed private pin differs: {name}")
    catalog = (repository / "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md").read_text()
    inventory = (repository / "docs/controls/CCF_POLICY_AND_ARTIFACT_INVENTORY_v0.1.md").read_text()
    standard = (repository / "docs/governance/CORPORATE_DOCUMENT_STANDARD_v0.1.md").read_text()
    appointments = (repository / "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md").read_text()
    if (
        "SH-POL-004 | Local control variations are documented" not in catalog
        or "control governance/exception standard" not in inventory
        or "remain future or OPEN" not in inventory
        or "**Status:** APPROVED DESIGN STANDARD" not in standard
        or "AS-P005 | Martin Ives | Head of Risk and Compliance" not in appointments
        or "AS-P003 | Helena Ward | General Counsel" not in appointments
    ):
        raise CompanyStoreError("POL004 policy status, roles or design standard differs")
    route = json.loads((repository / ROUTE).read_bytes())
    route_review = json.loads((private / ROUTE_REVIEW).read_bytes())
    if (
        route_review.get("verdict")
        != "PASS_SELECTED_SEC001_CC67_ROUTE_V11_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or route_review.get("main_output_sha256", {}).get("LEDGER.json") != CANON_PINS[ROUTE]
        or route_review.get("p1_freeze") != P1_FREEZE
    ):
        raise CompanyStoreError("POL004 reviewed route boundary differs")
    selected = {}
    for side in "AB":
        rows = [
            row for row in route["rows"] if row["side"] == side and row["control_id"] == CONTROL
        ]
        authored = [row for row in rows if row["task_id"] == TASK]
        if (
            len(rows) != 4
            or len(authored) != 1
            or any(
                row["current_status"] != "NOT_STARTED"
                or row["current_conclusion"] != "NOT_RUN"
                or row["audit_task_credit"] is not False
                for row in rows
            )
            or authored[0]["authored_test_clause"] != CLAUSE
            or authored[0]["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
            or authored[0]["targeted_integrated_source_ids"] != []
        ):
            raise CompanyStoreError("POL004 exact authored route or active status differs")
        selected[side] = {
            "task_id": TASK,
            "classification": "UNSUPPORTED_EXACT_CLAUSE",
            "screen_row_sha256": authored[0]["screen_row_sha256"],
            "authored_test_clause": CLAUSE,
            "current_status": "NOT_STARTED",
            "current_conclusion": "NOT_RUN",
            "audit_task_credit": False,
        }
    review = json.loads((private / SOURCE_REVIEW).read_bytes())
    manifest = json.loads((private / SOURCE_RUN / "MANIFEST.json").read_bytes())
    if (
        review.get("verdict") != "PASS_PRIVATE_MAIN_LOCAL_FICTIONAL_SOURCE"
        or review.get("run_sha256")
        != {
            "MANIFEST.json": PRIVATE_PINS[f"{SOURCE_RUN}/MANIFEST.json"],
            "RECEIPT.json": PRIVATE_PINS[f"{SOURCE_RUN}/RECEIPT.json"],
            "company.sqlite3": PRIVATE_PINS[f"{SOURCE_RUN}/company.sqlite3"],
        }
        or manifest.get("module_sha256")
        != CANON_PINS["enterprise/audit_suite/company_policy_exception_2027_exercise.py"]
        or manifest.get("native_version_count") != 19
        or manifest.get("audit_task_credit") is not False
    ):
        raise CompanyStoreError("Reviewed POL002 native source join differs")
    verified_manifest = policy.verify(
        private / SOURCE_RUN, repository=repository, private_repository=private
    )
    if verified_manifest != manifest:
        raise CompanyStoreError("POL002 source verifier manifest differs")
    source = json.loads((private / SOURCE_RUN / "RECEIPT.json").read_bytes())
    if (
        source.get("counts") != {"CLEAN": 7, "MESSY": 12}
        or source.get("draft_version_status") != "0.2.0_PENDING_AUTHORIZED_APPROVAL"
        or source.get("approved_version_distributed") != "0.1.0"
        or source.get("open_generic_exception_ids") != {"CLEAN": [], "MESSY": ["EXC-POL-DIST-001"]}
        or source.get("audit_task_credit") is not False
    ):
        raise CompanyStoreError("POL002 selected source authority or history differs")
    sources = {}
    for scenario, rows in source["records"].items():
        sources[scenario] = {row["record"]: _ref(row) for row in rows}
        if len(sources[scenario]) != len(rows):
            raise CompanyStoreError("POL002 source record identity collision")
    if any(_private_file(private / name) != before for name, before in frozen.items()):
        raise CompanyStoreError("POL002 or route source changed during read")
    return {"source": sources, "route": selected, "frozen": frozen}


def _detail(scenario: str, record: str) -> dict:
    common = {
        "selected_local_trial_only": True,
        "enterprise_policy_status_2026": "OPEN",
        "document_standard_status": "APPROVED_DESIGN_STANDARD_ONLY",
        "procedure_approval": "PENDING_AUTHORIZED_DECISION",
        "effective_enterprise_procedure": False,
        "actual_operation": False,
    }
    details = {
        "CANDIDATE": {
            "trigger": "TWO_DECLARED_LOCAL_ENDPOINTS_DUE_2027_05_01_0930Z",
            "responsible_person_id": "AS-P005",
            "procedure_scope": "ONE_SELECTED_LOCAL_DISTRIBUTION_VARIANCE_CHECK",
        },
        "POLICY-ONLY-REJECT": {
            "policy_only_sufficiency": "REJECTED",
            "v0_2_release_approved": False,
            "approval_ref": None,
        },
        "DUE-TRIGGER": {
            "trigger_fired": True,
            "due_at": policy.DUE,
            "selected_denominator": list(policy.ENDPOINTS),
        },
        "EXECUTE": {
            "dated_local_execution": True,
            "on_time_endpoint_count": 2 if scenario == "CLEAN" else 1,
            "missing_at_due": [] if scenario == "CLEAN" else ["SECURITY_LOCAL_QUEUE"],
        },
        "RESULT": {"selected_result": "NO_SELECTED_VARIATION", "exception_open": False},
        "REVIEW": {
            "selected_result_reviewed": True,
            "independent_audit_test": False,
            "procedure_authority_approved": False,
        },
        "FALSE-CLOSE": {
            "claimed_no_variation": True,
            "valid": False,
            "contradicted_by_missed_original": True,
        },
        "CHALLENGE": {
            "false_close_rejected": True,
            "missing_at_due_retained": True,
            "exception_open": True,
        },
        "CORRECTION": {
            "backfill_recorded": True,
            "false_close_corrected": True,
            "false_close_erased": False,
            "missed_interval_retained": True,
            "exception_open": True,
        },
        "EXPIRY-REVIEW": {
            "exception_status": "OPEN_EXPIRED_UNAPPROVED",
            "waiver_ever_effective": False,
        },
        "FINAL": {
            "selected_result": "NO_SELECTED_VARIATION_PENDING_PROCEDURE_APPROVAL"
            if scenario == "CLEAN"
            else "CORRECTED_FALSE_CLOSE_HISTORICAL_GAP_OPEN",
            "exception_open": scenario == "MESSY",
            "authored_clause_satisfied": False,
        },
    }
    return {**common, **details[record]}


def _body(
    scenario: str, record: str, source_refs: dict, own_refs: dict, previous: dict | None
) -> dict:
    return {
        "schema": SCHEMA,
        "control_id": CONTROL,
        "selected_task_id": TASK,
        "scenario": scenario,
        "record_id": record,
        "actor_id": "AS-P003" if record in {"REVIEW", "CHALLENGE", "EXPIRY-REVIEW"} else "AS-P005",
        "actor_authority": "CANON_LISTED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE",
        "source_originals": source_refs,
        "previous_original": previous,
        "prior_false_close": own_refs.get("FALSE-CLOSE")
        if record in {"CHALLENGE", "CORRECTION", "FINAL"}
        else None,
        "prior_correction": own_refs.get("CORRECTION")
        if record in {"EXPIRY-REVIEW", "FINAL"}
        else None,
        "detail": _detail(scenario, record),
        "source_complete": False,
        "audit_task_credit": False,
    }


def _provenance(context: dict) -> dict:
    return {
        "source_reference": "SIM-POL004-PROCEDURE-TRACE-2027-001",
        "canon_sha256": CANON_PINS,
        "reviewed_private_sha256": PRIVATE_PINS,
        "policy_source_status": "REVIEWED_FICTIONAL_LOCAL_SOURCE_ONLY",
        "procedure_authority": "PENDING",
        "actual_enterprise_operation": False,
    }


def _input_digest(
    branch: str,
    system: str,
    record: str,
    event: str,
    available: str,
    provenance: dict,
    content: bytes,
) -> str:
    return sha(
        encoded(
            [
                [COMPANY, branch, system, record],
                0,
                event,
                available,
                "AUTHORED_TRAINING_SOURCE",
                provenance,
                sha(content),
            ]
        )
    )


def _receipt(originals: list[dict], context: dict) -> dict:
    return {
        "schema": SCHEMA,
        "status": "SEALED_SELECTED_FICTIONAL_LOCAL_PROCEDURE_TRIAL_NO_AUDIT_CREDIT",
        "control_id": CONTROL,
        "task_id": TASK,
        "selected_authored_clause": CLAUSE,
        "branch_ids": BRANCHES,
        "branch_counts": {scenario: len(rows) for scenario, rows in PLAN.items()},
        "native_originals": originals,
        "native_count": len(originals),
        "route_disposition": context["route"],
        "canon_sha256": CANON_PINS,
        "reviewed_private_sha256": PRIVATE_PINS,
        "selected_trigger": "2027-05-01T09:30:00+00:00_TWO_PRIVATE_ENDPOINTS",
        "clean_result": "SELECTED_ON_TIME_NO_VARIATION_PENDING_PROCEDURE_APPROVAL",
        "messy_false_close_corrected": True,
        "messy_missed_interval_retained": True,
        "messy_exception_open": True,
        "design_standard_approved_only": True,
        "enterprise_policy_status_2026": "OPEN",
        "procedure_authority": "PENDING_AUTHORIZED_DECISION",
        "full_policy_or_procedure_population": False,
        "actual_operation": False,
        "source_complete": False,
        "audit_task_credit": False,
        "active_P1_mutated": False,
    }


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Create an isolated native trace after re-verifying its reviewed source."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(part.is_symlink() for part in (destination, *destination.parents))
    ):
        raise CompanyStoreError("Fresh ordinary private POL004 destination required")
    context = _context(repository, private)
    originals = []
    with tempfile.TemporaryDirectory(
        prefix="pol004-procedure-stage-", dir=destination.parent
    ) as staged:
        stage = Path(staged)
        store = CompanyStore(stage)
        for scenario, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            refs: dict[str, dict] = {}
            previous = None
            for system, record, at, source_names in PLAN[scenario]:
                event = _time(at)
                if event[:10] <= AS_OF:
                    raise CompanyStoreError("POL004 event must be future fiction")
                available = _time(
                    (datetime.fromisoformat(event) + timedelta(minutes=1)).isoformat()
                )
                source_refs = {name: context["source"][scenario][name] for name in source_names}
                if any(ref["available_at"] > event for ref in source_refs.values()) or (
                    previous is not None and previous["available_at"] > event
                ):
                    raise CompanyStoreError("POL004 causal original unavailable at event")
                content = encoded(
                    {
                        **_body(scenario, record, source_refs, refs, previous),
                        "event_at": event,
                        "available_at": available,
                    }
                )
                provenance = _provenance(context)
                command = "POL4-PROC-" + sha(encoded([branch, system, record]))
                original = store.append_version(
                    COMPANY,
                    branch,
                    system,
                    record,
                    expected_version=0,
                    command_id=command,
                    event_at=event,
                    available_at=available,
                    content=content,
                    provenance=provenance,
                )
                originals.append(
                    {
                        **original,
                        "command_id": command,
                        "input_digest": _input_digest(
                            branch, system, record, event, available, provenance, content
                        ),
                    }
                )
                previous = refs[record] = _ref(original)
        receipt = _receipt(originals, context)
        receipt_path = stage / "SOURCE_RECEIPT.json"
        receipt_path.write_bytes(encoded(receipt))
        receipt_path.chmod(0o600)
        database = stage / "company.sqlite3"
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "source_receipt_sha256": _digest(receipt_path),
            "native_db_sha256": _digest(database),
            "module_sha256": _digest(repository / MODULE),
            "proposal_sha256": CANON_PINS[PROPOSAL],
            "native_count": len(originals),
            "audit_task_credit": False,
            "active_P1_mutated": False,
        }
        manifest_path = stage / "RUN-MANIFEST.json"
        manifest_path.write_bytes(encoded(manifest))
        manifest_path.chmod(0o600)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Reperform source joins, causal clocks, native contents and no-credit gates."""
    raw = Path(destination).absolute()
    if any(part.is_symlink() for part in (raw, *raw.parents)):
        raise CompanyStoreError("POL004 output alias forbidden")
    destination = raw.resolve(strict=True)
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    if destination.stat().st_mode & 0o077 or {p.name for p in destination.iterdir()} != {
        "SOURCE_RECEIPT.json",
        "RUN-MANIFEST.json",
        "company.sqlite3",
    }:
        raise CompanyStoreError("Exact private POL004 output layout required")
    paths = {
        name: destination / name
        for name in ("SOURCE_RECEIPT.json", "RUN-MANIFEST.json", "company.sqlite3")
    }
    before = {name: _private_file(path) for name, path in paths.items()}
    db_path = paths["company.sqlite3"]
    if any(Path(str(db_path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise CompanyStoreError("POL004 SQLite sidecar forbidden")
    context = _context(repository, private)
    manifest = json.loads(paths["RUN-MANIFEST.json"].read_bytes())
    receipt = json.loads(paths["SOURCE_RECEIPT.json"].read_bytes())
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "source_receipt_sha256": before["SOURCE_RECEIPT.json"][-1],
        "native_db_sha256": before["company.sqlite3"][-1],
        "module_sha256": _digest(repository / MODULE),
        "proposal_sha256": CANON_PINS[PROPOSAL],
        "native_count": 16,
        "audit_task_credit": False,
        "active_P1_mutated": False,
    }:
        raise CompanyStoreError("POL004 manifest differs")
    expected = []
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("POL004 native database integrity differs")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("POL004 registered system custody differs")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 16 or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("POL004 native version or audit journal count differs")
        for scenario, branch in BRANCHES.items():
            refs: dict[str, dict] = {}
            previous = None
            previous_import = None
            for system, record, at, source_names in PLAN[scenario]:
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (COMPANY, branch, system, record),
                ).fetchone()
                event = _time(at)
                available = _time(
                    (datetime.fromisoformat(event) + timedelta(minutes=1)).isoformat()
                )
                source_refs = {name: context["source"][scenario][name] for name in source_names}
                if any(ref["available_at"] > event for ref in source_refs.values()) or (
                    previous is not None and previous["available_at"] > event
                ):
                    raise CompanyStoreError("POL004 causal source original unavailable")
                content = encoded(
                    {
                        **_body(scenario, record, source_refs, refs, previous),
                        "event_at": event,
                        "available_at": available,
                    }
                )
                provenance = _provenance(context)
                command = "POL4-PROC-" + sha(encoded([branch, system, record]))
                if (
                    row is None
                    or row["event_at"] != event
                    or row["available_at"] != available
                    or not row["imported_at"].startswith("2026-")
                    or _time(row["imported_at"]) != row["imported_at"]
                    or (previous_import is not None and row["imported_at"] < previous_import)
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or row["provenance"]
                    != json.dumps(provenance, sort_keys=True, separators=(",", ":"))
                    or row["content"] != content
                    or row["sha256"] != sha(content)
                    or row["command_id"] != command
                    or row["input_digest"]
                    != _input_digest(branch, system, record, event, available, provenance, content)
                ):
                    raise CompanyStoreError(
                        "POL004 native content, provenance or three clocks differ"
                    )
                original = {
                    key: (json.loads(row[key]) if key == "provenance" else row[key])
                    for key in (
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "event_at",
                        "available_at",
                        "imported_at",
                        "origin",
                        "provenance",
                        "sha256",
                        "command_id",
                        "input_digest",
                    )
                }
                expected.append(original)
                previous = refs[record] = _ref(original)
                previous_import = row["imported_at"]
    if receipt != _receipt(expected, context):
        raise CompanyStoreError("POL004 receipt or exact native original claims differ")
    if any(_private_file(path) != before[name] for name, path in paths.items()) or (
        _p1_inventory(private) != P1_FREEZE
    ):
        raise CompanyStoreError("POL004 output or frozen P1 changed during read")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    result = (
        create(
            args.destination, repository=args.repository, private_repository=args.private_repository
        )
        if args.action == "create"
        else verify(
            args.destination, repository=args.repository, private_repository=args.private_repository
        )
    )
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "native_count": result["native_count"],
                "branch_counts": result["branch_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
