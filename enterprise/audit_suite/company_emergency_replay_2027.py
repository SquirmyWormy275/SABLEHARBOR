"""One payload-free fictional Boise emergency replay source, without audit credit."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path

from . import company_iam005_emergency_marker_2027 as iam
from . import company_sec005_operated_2027 as sec
from .company_store import CompanyStore, CompanyStoreError, _time
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_SELECTED_EMERGENCY_REPLAY_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"CLEAN": "EMERGENCY-REPLAY-CLEAN", "MESSY": "EMERGENCY-REPLAY-MESSY"}
SPEC = "enterprise/audit_suite/emergency_replay_2027_spec_v1.json"
SPEC_SHA256 = "16f53c1e1244643e78c1cfcff21aee830bb9254756625a28611987a35a11faf5"
SOURCE_REFERENCE = "enterprise/audit_suite/company_emergency_replay_2027.py"
SOURCE_ROOT = "enterprise/generated/audit-suite"
IAM_FOLDER = "company-iam005-emergency-marker-2026-09-30"
UPSTREAM = {
    "iam": {
        "run": f"{IAM_FOLDER}/main-run-v1",
        "review": f"{IAM_FOLDER}/independent-review-main-v1/REVIEW.json",
        "hashes": {
            "MANIFEST.json": "d21c7aedd1d029ce596db7b158e4c23fd379bc225304c2959537ef8f4a9dba42",
            "RECEIPT.json": "95dcda39d7965d285a585afacadf869b4d7349556452d15051c29433fe5f9185",
            "company.sqlite3": "bd40f886ccd53def3b1cfe716f93422a5aa686e15162b2f90b48e3af5920d433",
            "REVIEW.json": "2d1d0f413e26388dd6f7abff9835bc3a3e80376cd8056f855da7e0d51ba35674",
        },
    },
    "phi_ba": {
        "run": "company-phi-ba-2027-simulation-2026-09-29/run-v1",
        "receipt_sha256": "20e3762aabb45fcfa3107d695da37e7eeb677f6c5e98f1bb767fa463fe857d9d",
    },
    "bcm": {
        "run": "company-bcm-shared-runtime-2026-09-29/run-v2",
        "receipt_sha256": "3cd0b62de445cde7c1a76f61a156fb0fd5fa9c443cf3255ca85876b6f2c4de9a",
    },
    "sec005": {
        "run": "company-sec005-operated-2026-09-30/main-run-v1",
        "receipt_sha256": "157495f5e98d9475f2c88b01954b6e192049183105fe35475350c20885681968",
    },
}
SYSTEM_OWNERS = {
    "replay_scope": "AS-P014",
    "replay_plan": "AS-P007",
    "replay_authority": "AS-P008",
    "replay_request": "AS-P007",
    "replay_decision": "AS-P008",
    "replay_result": "AS-P007",
    "replay_reconciliation": "AS-P014",
    "replay_review": "AS-P005",
    "exception_register": "AS-P005",
}
ORIGINAL_FIELDS = (
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


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def _ref(receipt: dict, side: str, system: str, record: str, version: int = 1) -> dict:
    matches = [
        row
        for row in receipt["records"][side]
        if (row["system"], row["record"], row["version"]) == (system, record, version)
    ]
    if len(matches) != 1:
        raise CompanyStoreError("Selected upstream native version missing or ambiguous")
    return {field: matches[0][field] for field in ORIGINAL_FIELDS}


def _context(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    spec_path = repository / SPEC
    if not spec_path.is_file() or spec_path.is_symlink() or _sha(spec_path) != SPEC_SHA256:
        raise CompanyStoreError("Selected replay specification differs")
    spec = json.loads(spec_path.read_text())
    if (
        spec.get("schema") != "SH_FICTIONAL_2027_SELECTED_EMERGENCY_REPLAY_SPEC_V1"
        or spec.get("truth_class") != "TRAINING_SCENARIO_ONLY"
        or spec.get("service_id") != "SIM-RESTRICTED-HOSTING-01"
        or spec.get("site") != "BOISE"
        or spec.get("marker_id") != "SIM-EPHI-RECOVERY-MARKER-01"
        or spec.get("marker_sha256") != iam.MARKER_SHA256
        or spec.get("selected_population_count") != 1
        or spec.get("chronology") != {"CLEAN": "2027-11-15", "MESSY": "2027-11-16"}
        or spec.get("expected_native_versions") != {"CLEAN": 8, "MESSY": 15}
    ):
        raise CompanyStoreError("Selected replay scope differs")
    source_root = private_repository / SOURCE_ROOT
    source = UPSTREAM["iam"]
    run = source_root / source["run"]
    review = source_root / source["review"]
    paths = {name: run / name for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3")}
    paths["REVIEW.json"] = review
    for folder in (run, review.parent):
        sec._private(folder, directory=True)
    before = sec._frozen(paths)
    if {name: fingerprint[-1] for name, fingerprint in before.items()} != source["hashes"]:
        raise CompanyStoreError("Reviewed IAM source bytes differ")
    if not str(json.loads(review.read_text()).get("verdict", "")).startswith("PASS"):
        raise CompanyStoreError("IAM independent source review is not PASS")
    iam.verify(run, repository=repository, private_repository=private_repository)
    if sec._frozen(paths) != before:
        raise CompanyStoreError("IAM source changed while verified")
    receipts = {"iam": json.loads(paths["RECEIPT.json"].read_text())}
    receipt_paths = {}
    receipt_fingerprints = {}
    for name in ("phi_ba", "bcm", "sec005"):
        setting = UPSTREAM[name]
        receipt_path = source_root / setting["run"] / "RECEIPT.json"
        sec._private(receipt_path, directory=False)
        receipt_paths[name] = receipt_path
        receipt_fingerprints[name] = sec._frozen({"receipt": receipt_path})
        if _sha(receipt_path) != setting["receipt_sha256"]:
            raise CompanyStoreError(f"Reviewed {name} receipt bytes differ")
        receipts[name] = json.loads(receipt_path.read_text())
    refs = {}
    for side in BRANCHES:
        refs[side] = {
            "customer_baa": _ref(receipts["phi_ba"], side, "contract_register", "BAA-CUST-01"),
            "boise_flow": _ref(receipts["phi_ba"], side, "flow_register", "FLOW-BOISE-01"),
            "bcm_original_result": _ref(
                receipts["bcm"], side, "exercise_result", "MARKER-RECOVERY"
            ),
            "iam_human_read": _ref(
                receipts["iam"], side, "access_activity", "HUMAN-MARKER-READ-01"
            ),
            "iam_service_read": _ref(
                receipts["iam"], side, "service_activity", "SERVICE-MARKER-READ-01"
            ),
            "iam_review": _ref(receipts["iam"], side, "access_review", "REVIEW-ACCESS-01"),
        }
        if side == "MESSY":
            refs[side].update(
                {
                    "phi_ba_open_exception": _ref(
                        receipts["phi_ba"], side, "exception_register", "EXC-01"
                    ),
                    "bcm_local_retest": _ref(
                        receipts["bcm"], side, "exercise_result", "MARKER-RECOVERY", 2
                    ),
                    "bcm_open_closure": _ref(
                        receipts["bcm"], side, "closure_gate", "KEY-AND-CAPACITY"
                    ),
                    "iam_open_exception": _ref(
                        receipts["iam"],
                        side,
                        "exception_register",
                        "EXC-IAM005-EMERGENCY-STATUS-01",
                    ),
                    "sec005_open_exception": _ref(
                        receipts["sec005"], side, "security_exception", "EXC-SEC005-Q4-01"
                    ),
                }
            )
        inherited = receipts["iam"]["upstream_selected_refs"][side]
        for key, old in (
            ("customer_baa", inherited["phi_ba_customer_contract"]),
            ("boise_flow", inherited["phi_ba_boise_flow"]),
            ("bcm_original_result", inherited["bcm_original_exercise"]),
        ):
            if any(refs[side][key][field] != old[field] for field in old):
                raise CompanyStoreError("IAM inherited source tuple differs")
        if side == "MESSY":
            old = receipts["iam"]["upstream_late_refs"][side]["sec_open_exception"]
            if any(refs[side]["sec005_open_exception"][field] != old[field] for field in old):
                raise CompanyStoreError("IAM late SEC005 exception tuple differs")
        if any(
            _time(row["available_at"]) >= _time(spec["chronology"][side] + "T09:00:00+00:00")
            for row in refs[side].values()
        ):
            raise CompanyStoreError("Upstream source unavailable before replay scope")
    if sec._frozen(paths) != before or any(
        sec._frozen({"receipt": receipt_paths[name]}) != receipt_fingerprints[name]
        for name in receipt_paths
    ):
        raise CompanyStoreError("Reviewed upstream source changed during replay read")
    return {"spec": spec, "refs": refs, "upstream_hashes": source["hashes"]}


def _plan(side: str) -> list[tuple[str, str, str, str, str, str]]:
    common = [
        (
            "09:00",
            "replay_scope",
            "SCOPE",
            "AS-P014",
            "SELECT_ONE_NONPERSONAL_MARKER",
            "SELECTED_ONLY",
        ),
        ("09:10", "replay_plan", "PLAN", "AS-P007", "PLAN_LOCAL_BOISE_REPLAY", "PENDING_AUTHORITY"),
    ]
    if side == "CLEAN":
        return common + [
            (
                "09:20",
                "replay_authority",
                "AUTHORITY",
                "AS-P008",
                "APPROVE_BOUNDED_FICTIONAL_EXERCISE",
                "APPROVED_LOCAL_ONLY",
            ),
            (
                "09:30",
                "replay_request",
                "REQUEST",
                "AS-P007",
                "REQUEST_MARKER_ONLY_REPLAY",
                "REQUESTED",
            ),
            (
                "09:31",
                "replay_decision",
                "DECISION",
                "AS-P008",
                "CHECK_SELECTED_LEASE_AND_SCOPE",
                "ALLOW_LOCAL_TEST",
            ),
            (
                "09:35",
                "replay_result",
                "RESULT",
                "AS-P007",
                "SIMULATE_BOISE_MARKER_REPLAY",
                "HASH_MATCH_NO_BYTES_SENT",
            ),
            (
                "10:00",
                "replay_reconciliation",
                "RECON",
                "AS-P014",
                "COMPARE_SELECTED_REPLAY_AND_IAM_TRACE",
                "SELECTED_ROWS_MATCH",
            ),
            (
                "11:00",
                "replay_review",
                "REVIEW",
                "AS-P005",
                "REVIEW_SELECTED_LOCAL_RESULT",
                "LOCAL_TRACE_ONLY",
            ),
        ]
    return common + [
        (
            "09:15",
            "replay_request",
            "FASTPATH-REQUEST",
            "AS-P007",
            "REQUEST_PREAUTH_FAST_PATH",
            "INVALID_REQUEST",
        ),
        (
            "09:16",
            "replay_decision",
            "FASTPATH-DENY",
            "AS-P008",
            "DENY_PREAUTH_FAST_PATH",
            "DENY_NO_REPLAY",
        ),
        (
            "09:20",
            "exception_register",
            "EXCEPTION-OPEN",
            "AS-P005",
            "OPEN_REPLAY_PROCESS_EXCEPTION",
            "OPEN",
        ),
        (
            "09:30",
            "replay_authority",
            "AUTHORITY",
            "AS-P008",
            "APPROVE_BOUNDED_FICTIONAL_RETEST",
            "APPROVED_LOCAL_ONLY",
        ),
        (
            "09:35",
            "replay_request",
            "REQUEST",
            "AS-P007",
            "REQUEST_MARKER_ONLY_REPLAY",
            "REQUESTED",
        ),
        (
            "09:36",
            "replay_decision",
            "DECISION",
            "AS-P008",
            "CHECK_SELECTED_LEASE_AND_SCOPE",
            "ALLOW_LOCAL_TEST",
        ),
        (
            "09:40",
            "replay_result",
            "STALE-RESULT",
            "AS-P007",
            "SIMULATE_STALE_CHECKPOINT_REPLAY",
            "HASH_MISMATCH_NO_BYTES_SENT",
        ),
        (
            "09:50",
            "replay_reconciliation",
            "DISCREPANCY",
            "AS-P014",
            "COMPARE_EXPECTED_MARKER_HASH",
            "MISMATCH_ESCALATED",
        ),
        (
            "10:00",
            "replay_plan",
            "CORRECTION",
            "AS-P007",
            "PLAN_SELECTED_CHECKPOINT_CORRECTION",
            "RETEST_PENDING",
        ),
        (
            "10:15",
            "replay_result",
            "RETEST",
            "AS-P007",
            "SIMULATE_CORRECTED_MARKER_REPLAY",
            "HASH_MATCH_NO_BYTES_SENT",
        ),
        (
            "10:30",
            "replay_reconciliation",
            "RECON",
            "AS-P014",
            "COMPARE_SELECTED_RETEST_AND_IAM_TRACE",
            "LOCAL_RETEST_MATCH_COVERAGE_OPEN",
        ),
        (
            "11:00",
            "replay_review",
            "REVIEW",
            "AS-P005",
            "REVIEW_WITH_UPSTREAM_OPEN_GATES",
            "NO_INDEPENDENT_ASSURANCE",
        ),
        (
            "11:10",
            "exception_register",
            "EXCEPTION-STATUS",
            "AS-P005",
            "RETAIN_HISTORICAL_GAP_AND_UPSTREAM_HOLDS",
            "OPEN",
        ),
    ]


def _rows(context: dict, side: str) -> list[dict]:
    spec = context["spec"]
    branch = BRANCHES[side]
    rows = []
    current_marker_hash = hashlib.sha256(iam.MARKER_BYTES).hexdigest()
    stale_checkpoint_hash = hashlib.sha256(iam.MARKER_BYTES + b":STALE-CHECKPOINT").hexdigest()
    if current_marker_hash != spec["marker_sha256"] or stale_checkpoint_hash == current_marker_hash:
        raise CompanyStoreError("Selected marker fixture hashes differ")
    for clock, system, record, actor, action, decision in _plan(side):
        at = _time(spec["chronology"][side] + "T" + clock + ":00+00:00")
        observed_hash = (
            stale_checkpoint_hash
            if record == "STALE-RESULT"
            else current_marker_hash
            if record in {"RESULT", "RETEST"}
            else None
        )
        body = {
            "schema": SCHEMA + "_NATIVE_EVENT",
            "truth_class": "TRAINING_SCENARIO_ONLY",
            "branch": branch,
            "service_id": spec["service_id"],
            "site": spec["site"],
            "marker_id": spec["marker_id"],
            "marker_sha256": spec["marker_sha256"],
            "observed_checkpoint_sha256": observed_hash,
            "selected_population_count": 1,
            "actor_id": actor,
            "action": action,
            "decision": decision,
            "event_at": at,
            "previous_native_content": (
                {"record": rows[-1]["record"], "sha256": rows[-1]["sha256"]} if rows else None
            ),
            "upstream_original_refs": context["refs"][side] if not rows else None,
            "upstream_exception_status": (
                {
                    "bcm_capacity_bia": "OPEN",
                    "iam_coverage": "OPEN",
                    "sec005_telemetry": "OPEN",
                    "phi_ba_flowdown": "OPEN",
                }
                if side == "MESSY"
                else {}
            ),
            "outbound_bytes": 0,
            "outbound_packets": 0,
            "actual_phi_processing": False,
        }
        content = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        rows.append(
            {
                "system": system,
                "record": record,
                "event_at": at,
                "available_at": at,
                "content": content,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    if len(rows) != spec["expected_native_versions"][side]:
        raise CompanyStoreError("Selected replay denominator differs")
    return rows


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    sec._private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("Fresh private replay destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(
        prefix=".emergency-replay-stage-", dir=destination.parent
    ) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        refs = {}
        for side, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            refs[side] = []
            for row in _rows(context, side):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    row["system"],
                    row["record"],
                    expected_version=0,
                    command_id=f"ER-{branch}-{row['record']}",
                    event_at=row["event_at"],
                    available_at=row["available_at"],
                    content=row["content"],
                    provenance={
                        "source_reference": SOURCE_REFERENCE,
                        "truth_class": "TRAINING_SCENARIO_ONLY",
                    },
                )
                if ref["sha256"] != row["sha256"]:
                    raise CompanyStoreError("Replay native content differs")
                refs[side].append(ref)
        receipt = {
            "schema": SCHEMA,
            "company": COMPANY,
            "branches": BRANCHES,
            "records": refs,
            "spec_sha256": SPEC_SHA256,
            "reviewed_iam_source_sha256": context["upstream_hashes"],
            "upstream_original_refs": context["refs"],
            "native_version_counts": {side: len(rows) for side, rows in refs.items()},
            "selected_population_count": 1,
            "local_open_exception_counts": {"CLEAN": 0, "MESSY": 1},
            "messy_upstream_gates_remain_open": True,
            "external_bytes_or_packets": 0,
            "actual_phi_processing": False,
            "deployed_recovery_proven": False,
            "source_complete": False,
            "audit_task_credit": False,
            "limits": context["spec"]["limits"],
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _sha(stage / "RECEIPT.json"),
            "db_sha256": _sha(stage / "company.sqlite3"),
            "module_sha256": _sha(Path(__file__)),
            "native_version_count": 23,
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = sec._private(destination, directory=True)
    paths = {name: root / name for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3")}
    if {child.name for child in root.iterdir()} != set(paths):
        raise CompanyStoreError("Exact three-file replay source required")
    before = sec._frozen(paths)
    context = _context(repository, private_repository)
    manifest = json.loads(paths["MANIFEST.json"].read_text())
    receipt = json.loads(paths["RECEIPT.json"].read_text())
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _sha(paths["RECEIPT.json"]),
        "db_sha256": _sha(paths["company.sqlite3"]),
        "module_sha256": _sha(Path(__file__)),
        "native_version_count": 23,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Replay manifest differs")
    expected = {
        "schema": SCHEMA,
        "company": COMPANY,
        "branches": BRANCHES,
        "records": receipt.get("records"),
        "spec_sha256": SPEC_SHA256,
        "reviewed_iam_source_sha256": context["upstream_hashes"],
        "upstream_original_refs": context["refs"],
        "native_version_counts": {"CLEAN": 8, "MESSY": 15},
        "selected_population_count": 1,
        "local_open_exception_counts": {"CLEAN": 0, "MESSY": 1},
        "messy_upstream_gates_remain_open": True,
        "external_bytes_or_packets": 0,
        "actual_phi_processing": False,
        "deployed_recovery_proven": False,
        "source_complete": False,
        "audit_task_credit": False,
        "limits": context["spec"]["limits"],
    }
    if receipt != expected:
        raise CompanyStoreError("Replay receipt scope or qualification differs")
    with sqlite3.connect(
        paths["company.sqlite3"].as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Replay source integrity differs")
        for table in ("grants", "collections", "access_events"):
            if db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
                raise CompanyStoreError("Replay source has audit access journal")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("Replay source systems differ")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 23:
            raise CompanyStoreError("Replay source native count differs")
        for side, branch in BRANCHES.items():
            rows = _rows(context, side)
            refs = receipt["records"][side]
            if len(refs) != len(rows):
                raise CompanyStoreError("Replay receipt branch count differs")
            for row, ref in zip(rows, refs, strict=True):
                native = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? "
                    "AND system=? AND record=? AND version=1",
                    (COMPANY, branch, row["system"], row["record"]),
                ).fetchone()
                if native is None or native["content"] != row["content"]:
                    raise CompanyStoreError("Replay native bytes differ")
                if (
                    native["sha256"] != row["sha256"]
                    or native["event_at"] != row["event_at"]
                    or native["available_at"] != row["available_at"]
                    or native["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or native["command_id"] != f"ER-{branch}-{row['record']}"
                    or json.loads(native["provenance"])
                    != {
                        "source_reference": SOURCE_REFERENCE,
                        "truth_class": "TRAINING_SCENARIO_ONLY",
                    }
                    or native["imported_at"] >= "2027-01-01"
                    or _time(native["imported_at"]) != native["imported_at"]
                    or ref != CompanyStore._metadata(native)
                ):
                    raise CompanyStoreError("Replay native clocks, provenance or receipt differ")
    if sec._frozen(paths) != before:
        raise CompanyStoreError("Replay source changed during verification")
    return {
        "status": "VERIFIED_FICTIONAL_SELECTED_EMERGENCY_REPLAY_NO_AUDIT_CREDIT",
        "native_version_counts": {"CLEAN": 8, "MESSY": 15},
        "audit_task_credit": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("destination", type=Path)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    args = parser.parse_args()
    command = create if args.action == "create" else verify
    print(
        json.dumps(
            command(
                args.destination,
                repository=args.repository,
                private_repository=args.private_repository,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
