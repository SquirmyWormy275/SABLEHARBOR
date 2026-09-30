"""Selected fictional IAM005 emergency marker history; no real access or audit credit."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path

from . import company_bcm_shared_runtime_exercise as bcm
from . import company_phi_ba_2027_simulation as phi
from . import company_sec005_operated_2027 as sec
from .company_store import CompanyStore, CompanyStoreError, _time
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_IAM005_EMERGENCY_MARKER_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"CLEAN": "IAM005-EMERGENCY-CLEAN", "MESSY": "IAM005-EMERGENCY-MESSY"}
SPEC = "enterprise/audit_suite/iam005_emergency_marker_spec_v1.json"
SPEC_SHA256 = "989c998f33cfd1a82638951eac715e29a427f4d61bb31e275752f08c4c429083"
SOURCE_REFERENCE = "enterprise/audit_suite/company_iam005_emergency_marker_2027.py"
MARKER_BYTES = b"SABLEHARBOR:SIM-EPHI-RECOVERY-MARKER-01:NONPERSONAL:2027"
MARKER_SHA256 = "fb5a872ccff0e97081593ba6338b2bbb40556168999a253dc9d0df402638870a"
TRANSITION = "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3"
SOURCES = {
    "phi_ba": {
        "folder": "company-phi-ba-2027-simulation-2026-09-29",
        "run": "run-v1",
        "review": "independent-review-v1",
        "hashes": {
            "MANIFEST.json": "8226ac2031cafe581289afb4c25088c8dfe603e75ac11fc1ababfe2590f2a5f2",
            "RECEIPT.json": "20e3762aabb45fcfa3107d695da37e7eeb677f6c5e98f1bb767fa463fe857d9d",
            "company.sqlite3": "ad252e8cb6b1309b238fbe50daac541d67b5fa89051a0b3d8eab7993d4010449",
            "REVIEW.json": "39bb9b071179ed672c5cf07c2867285d36b2f3e8cdce2106dc4472d17047911e",
        },
    },
    "bcm": {
        "folder": "company-bcm-shared-runtime-2026-09-29",
        "run": "run-v2",
        "review": "independent-review-v2",
        "hashes": {
            "MANIFEST.json": "ea52c6c0210da3840a94a922c122b43b3e054d986cd02650a9ff70adb316d3a1",
            "RECEIPT.json": "3cd0b62de445cde7c1a76f61a156fb0fd5fa9c443cf3255ca85876b6f2c4de9a",
            "company.sqlite3": "9227da660fb2bf910c877fa7abbe71f119a468040c0447092d0dee8b6da64b8e",
            "REVIEW.json": "bff0e70bf1f8e72e2e94bf9c2fa91c4adec811a13d2a53f85788b57d967d9476",
        },
    },
    "sec005": {
        "folder": "company-sec005-operated-2026-09-30",
        "run": "main-run-v1",
        "review": "independent-review-main-v2",
        "hashes": {
            "MANIFEST.json": "37b170a7e6688d1bbab4022ff8a239eb3b2e5c44fff76af381a9872c0b84aa32",
            "RECEIPT.json": "157495f5e98d9475f2c88b01954b6e192049183105fe35475350c20885681968",
            "company.sqlite3": "4c258e73de8084b20c65fcad24a96e7f0e3fbb771de431c6e079fc6500d7fd1f",
            "REVIEW.json": "4c163ff06dda410b05a83a45f0135d9b3a80e8fd38801704df481d999b2772b6",
        },
    },
}
SYSTEM_OWNERS = {
    "emergency_scope": "AS-P014",
    "emergency_authority": "AS-P008",
    "access_request": "AS-P007",
    "access_decision": "AS-P008",
    "access_activity": "AS-P007",
    "service_activity": "AS-P007",
    "access_reconciliation": "AS-P005",
    "exception_register": "AS-P005",
    "access_review": "AS-P008",
}
LIMITS = [
    "Fictional 2027 selected marker exercise authored in 2026; no actual PHI or patient data.",
    "No real identity provider, account, usable credential, token, packet, session, "
    "deployment or external send.",
    "AS-P008 later reviews an exercise AS-P008 approved; this is management "
    "self-review, not independent assurance.",
    "Messy October SEC005 telemetry omission prevents complete access-log "
    "assurance and remains open.",
    "One selected marker/path does not establish every trust boundary, emergency "
    "ePHI availability, period population or task sufficiency.",
    "No P1 audit pair, grant, collection, workpaper, Key, Atlas or audit task credit is changed.",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def _source_ref(receipt: dict, side: str, system: str, record: str) -> dict:
    rows = [
        row
        for row in receipt["records"][side]
        if row["system"] == system and row["record"] == record
    ]
    if not rows:
        raise CompanyStoreError("Required upstream native record missing")
    # Messy BCM has a later retest under the same record: preserve first exercise.
    row = rows[0]
    if row["version"] != 1:
        raise CompanyStoreError("First upstream version differs")
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
        )
    }


def _context(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    spec_path = repository / SPEC
    if _sha(spec_path) != SPEC_SHA256:
        raise CompanyStoreError("Selected IAM005 spec bytes differ")
    spec = json.loads(spec_path.read_text())
    if (
        spec.get("schema") != "SH_FICTIONAL_2027_IAM005_EMERGENCY_MARKER_SPEC_V1"
        or spec.get("truth_class") != "TRAINING_SCENARIO_ONLY"
        or spec.get("marker_bytes_utf8") != MARKER_BYTES.decode()
        or spec.get("marker_byte_count") != len(MARKER_BYTES)
        or spec.get("marker_sha256") != MARKER_SHA256
        or hashlib.sha256(MARKER_BYTES).hexdigest() != MARKER_SHA256
        or spec.get("expected")
        != {
            "CLEAN": {"native_versions": 9, "open_exceptions": 0},
            "MESSY": {"native_versions": 16, "open_exceptions": 1},
        }
    ):
        raise CompanyStoreError("Selected IAM005 spec/denominator differs")
    receipts = {}
    pins = {}
    for name, source in SOURCES.items():
        folder = private_repository / "enterprise/generated/audit-suite" / source["folder"]
        run = folder / source["run"]
        review = folder / source["review"] / "REVIEW.json"
        paths = {
            "MANIFEST.json": run / "MANIFEST.json",
            "RECEIPT.json": run / "RECEIPT.json",
            "company.sqlite3": run / "company.sqlite3",
            "REVIEW.json": review,
        }
        for directory in (folder, run, review.parent):
            sec._private(directory, directory=True)
        before = sec._frozen(paths)
        if {key: item[-1] for key, item in before.items()} != source["hashes"]:
            raise CompanyStoreError(f"Reviewed {name} native source bytes differ")
        review_data = json.loads(review.read_text())
        if not str(review_data.get("verdict", "")).startswith("PASS"):
            raise CompanyStoreError(f"Reviewed {name} source is not PASS")
        if name == "phi_ba":
            phi.verify(run, transition_root=private_repository / TRANSITION, repository=repository)
        elif name == "bcm":
            bcm.verify(run, repository=repository, private_repository=private_repository)
        else:
            sec.verify(
                run,
                repository=repository,
                private_repository=private_repository,
                transition_root=private_repository / TRANSITION,
            )
        if sec._frozen(paths) != before:
            raise CompanyStoreError(f"Reviewed {name} changed during source verification")
        receipts[name] = json.loads(paths["RECEIPT.json"].read_text())
        pins[name] = source["hashes"]
    refs = {}
    late_refs = {"CLEAN": {}, "MESSY": {}}
    for side in BRANCHES:
        refs[side] = {
            "phi_ba_customer_contract": _source_ref(
                receipts["phi_ba"], side, "contract_register", "BAA-CUST-01"
            ),
            "phi_ba_boise_flow": _source_ref(
                receipts["phi_ba"], side, "flow_register", "FLOW-BOISE-01"
            ),
            "bcm_original_exercise": _source_ref(
                receipts["bcm"], side, "exercise_result", "MARKER-RECOVERY"
            ),
            "sec_selected_application": _source_ref(
                receipts["sec005"], side, "security_application", "APPLY-BASELINE-01"
            ),
            "sec_october_reconciliation": _source_ref(
                receipts["sec005"], side, "security_reconciliation", "RECON-OCT-01"
            ),
        }
        if any(
            _time(row["available_at"]) >= _time(spec["chronology"][side]["scope_at"])
            for row in refs[side].values()
        ):
            raise CompanyStoreError("Upstream source unavailable before IAM005 scope")
    late_refs["MESSY"] = {
        "sec_november_recheck": _source_ref(
            receipts["sec005"],
            "MESSY",
            "security_reconciliation",
            "SECURITY-RECHECK-NOV-01",
        ),
        "sec_open_exception": _source_ref(
            receipts["sec005"], "MESSY", "security_exception", "EXC-SEC005-Q4-01"
        ),
    }
    if any(
        _time(row["available_at"]) >= _time(spec["chronology"]["MESSY"]["review_at"])
        for row in late_refs["MESSY"].values()
    ):
        raise CompanyStoreError("SEC005 November source unavailable before IAM005 review")
    return {"spec": spec, "refs": refs, "late_refs": late_refs, "pins": pins}


def _rows(context: dict, scenario: str) -> list[dict]:
    spec = context["spec"]
    branch = BRANCHES[scenario]
    clock = spec["chronology"][scenario]
    marker = spec["marker_id"]
    rows: list[dict] = []

    def add(
        system: str,
        record: str,
        at: str,
        actor: str,
        action: str,
        decision: str,
        *,
        detail: dict | None = None,
    ) -> None:
        event = _time(at)
        body = {
            "schema": SCHEMA + "_NATIVE_EVENT",
            "branch": branch,
            "marker_id": marker,
            "marker_sha256": MARKER_SHA256,
            "marker_byte_count": len(MARKER_BYTES),
            "service_id": spec["selected_service_id"],
            "customer_service_id": spec["selected_customer_service_id"],
            "actor_person_or_inert_identity_id": actor,
            "action": action,
            "decision": decision,
            "event_at": event,
            "previous_source": (
                {"record": rows[-1]["record"], "sha256": rows[-1]["sha256"]} if rows else None
            ),
            "upstream_source_refs": context["refs"][scenario] if not rows else None,
            "detail": detail or {},
            "truth_class": "TRAINING_SCENARIO_ONLY",
        }
        content = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        rows.append(
            {
                "system": system,
                "record": record,
                "event_at": event,
                "available_at": event,
                "content": content,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )

    add(
        "emergency_scope",
        "SCOPE-BOISE-MARKER-01",
        clock["scope_at"],
        spec["data_owner_person_id"],
        "SELECT_ONE_NONPERSONAL_BOISE_RECOVERY_MARKER",
        "SELECTED_SCOPE_ONLY",
        detail={
            "selected_site": spec["selected_site"],
            "population_count": 1,
            "marker_bytes_utf8": MARKER_BYTES.decode(),
        },
    )
    add(
        "emergency_authority",
        "APPROVE-EMERGENCY-EXERCISE-01",
        clock["approval_at"],
        spec["security_approver_person_id"],
        "APPROVE_FICTIONAL_BOUNDED_EXERCISE",
        "TRAINING_WORLD_APPROVED_NO_REAL_GRANT",
        detail={
            "human": spec["human_operator_person_id"],
            "service": spec["inert_service_identity_id"],
        },
    )
    day = clock["exercise_at"][:10]
    add(
        "access_request",
        "REQUEST-EMERGENCY-01",
        day + "T09:00:00+00:00",
        "AS-P007",
        "REQUEST_20_MINUTE_BOISE_MARKER_LEASE",
        "REQUESTED",
        detail={"local_lease_state": "VALID" if scenario == "CLEAN" else "EXPIRED"},
    )
    if scenario == "CLEAN":
        add(
            "access_decision",
            "LEASE-DECISION-01",
            day + "T09:01:00+00:00",
            "AS-P008",
            "EVALUATE_SCOPED_EMERGENCY_LEASE",
            "ALLOW_20_MINUTES",
        )
        add(
            "access_activity",
            "HUMAN-MARKER-READ-01",
            day + "T09:02:00+00:00",
            "AS-P007",
            "SIMULATE_EXACT_MARKER_READ",
            "ALLOWED_NO_BYTES_EMITTED",
        )
        add(
            "service_activity",
            "SERVICE-MARKER-READ-01",
            day + "T09:03:00+00:00",
            spec["inert_service_identity_id"],
            "SIMULATE_READ_ONLY_RECOVERY_IDENTITY",
            "ALLOWED_NO_BYTES_EMITTED",
        )
        add(
            "access_decision",
            "REVOKE-LEASE-01",
            day + "T09:20:00+00:00",
            "AS-P008",
            "EXPIRE_SELECTED_LEASE",
            "REVOKED",
        )
        add(
            "access_reconciliation",
            "RECON-ACCESS-01",
            day + "T11:00:00+00:00",
            "AS-P005",
            "COMPARE_SELECTED_REQUEST_DECISION_AND_ACTIVITY",
            "SELECTED_LOCAL_ROWS_MATCH",
        )
        add(
            "access_review",
            "REVIEW-ACCESS-01",
            clock["review_at"],
            "AS-P008",
            "MANAGEMENT_SELF_REVIEW_OF_OWN_APPROVAL",
            "SELECTED_TRACE_REVIEWED_NO_INDEPENDENT_ASSURANCE",
        )
    else:
        add(
            "access_decision",
            "LEASE-DENY-EXPIRED-01",
            day + "T09:01:00+00:00",
            "AS-P008",
            "EVALUATE_EXPIRED_LOCAL_LEASE",
            "DENY",
        )
        add(
            "access_request",
            "REQUEST-OVERRIDE-01",
            day + "T09:02:00+00:00",
            "AS-P007",
            "REQUEST_UNBOUNDED_OVERRIDE",
            "REQUESTED",
        )
        add(
            "access_decision",
            "OVERRIDE-DENY-01",
            day + "T09:03:00+00:00",
            "AS-P008",
            "EVALUATE_UNBOUNDED_OVERRIDE",
            "DENY_NO_BYPASS",
        )
        add(
            "exception_register",
            "EXC-IAM005-EMERGENCY-01",
            day + "T10:00:00+00:00",
            "AS-P005",
            "OPEN_EXPIRED_LEASE_AND_OVERRIDE_EXCEPTION",
            "OPEN",
        )
        add(
            "emergency_authority",
            "APPROVE-NARROW-LEASE-01",
            "2027-10-21T09:00:00+00:00",
            "AS-P008",
            "APPROVE_CORRECTED_SCOPED_LEASE",
            "TRAINING_WORLD_APPROVED",
        )
        add(
            "access_decision",
            "LEASE-NARROW-01",
            "2027-10-21T09:05:00+00:00",
            "AS-P008",
            "ISSUE_20_MINUTE_MARKER_ONLY_LEASE",
            "ALLOW",
        )
        add(
            "access_activity",
            "HUMAN-MARKER-READ-01",
            "2027-10-21T09:06:00+00:00",
            "AS-P007",
            "SIMULATE_EXACT_MARKER_READ",
            "ALLOWED_NO_BYTES_EMITTED",
        )
        add(
            "service_activity",
            "STALE-SERVICE-VERSION-DENY-01",
            "2027-10-21T09:07:00+00:00",
            spec["inert_service_identity_id"],
            "SIMULATE_STALE_VERSION_READ",
            "DENY_NO_BYTES_EMITTED",
        )
        add(
            "service_activity",
            "ROTATE-INERT-VERSION-01",
            "2027-10-21T09:08:00+00:00",
            "AS-P007",
            "ADVANCE_INERT_CREDENTIAL_VERSION",
            "VERSION_2_NO_USABLE_SECRET",
        )
        add(
            "service_activity",
            "SERVICE-MARKER-READ-01",
            "2027-10-21T09:09:00+00:00",
            spec["inert_service_identity_id"],
            "SIMULATE_READ_ONLY_RECOVERY_IDENTITY",
            "ALLOWED_NO_BYTES_EMITTED",
        )
        add(
            "access_reconciliation",
            "RECON-ACCESS-01",
            "2027-10-22T10:00:00+00:00",
            "AS-P005",
            "COMPARE_SELECTED_LOCAL_ROWS_WITH_BOUNDARY_COVERAGE",
            "LOCAL_ROWS_MATCH_BOUNDARY_COVERAGE_UNVERIFIED",
        )
        add(
            "access_review",
            "REVIEW-ACCESS-01",
            clock["review_at"],
            "AS-P008",
            "LATE_MANAGEMENT_SELF_REVIEW_AFTER_SEC005_RECHECK",
            "NO_INDEPENDENT_ASSURANCE",
            detail={"reviewed_sec005_native_refs": context["late_refs"]["MESSY"]},
        )
        add(
            "exception_register",
            "EXC-IAM005-EMERGENCY-STATUS-01",
            "2027-11-11T11:00:00+00:00",
            "AS-P005",
            "RETAIN_ORIGINAL_DENIAL_AND_COVERAGE_EXCEPTION",
            "OPEN",
        )
    if len(rows) != spec["expected"][scenario]["native_versions"]:
        raise CompanyStoreError("Selected IAM005 native version denominator differs")
    return rows


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    sec._private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("Fresh private IAM005 destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(
        prefix=".iam005-emergency-stage-", dir=destination.parent
    ) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        refs = {}
        for scenario, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            refs[scenario] = []
            for row in _rows(context, scenario):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    row["system"],
                    row["record"],
                    expected_version=0,
                    command_id=f"IAM5E-{branch}-{row['record']}",
                    event_at=row["event_at"],
                    available_at=row["available_at"],
                    content=row["content"],
                    provenance={
                        "source_reference": SOURCE_REFERENCE,
                        "truth_class": "TRAINING_SCENARIO_ONLY",
                    },
                )
                if ref["sha256"] != row["sha256"]:
                    raise CompanyStoreError("IAM005 native content differs")
                refs[scenario].append(ref)
        receipt = {
            "schema": SCHEMA,
            "company": COMPANY,
            "branches": BRANCHES,
            "records": refs,
            "spec_sha256": SPEC_SHA256,
            "reviewed_upstream_sha256": context["pins"],
            "upstream_selected_refs": context["refs"],
            "upstream_late_refs": context["late_refs"],
            "selected_population": {
                "marker_count": 1,
                "human_identity_count": 1,
                "inert_service_identity_count": 1,
                "site": "BOISE",
            },
            "native_version_counts": {side: len(rows) for side, rows in refs.items()},
            "open_exception_counts": {"CLEAN": 0, "MESSY": 1},
            "external_bytes_or_packets": 0,
            "actual_phi_processing": False,
            "actual_operation_eligibility_as_of_2026_09_30": False,
            "authored_iam005_clause_satisfied": False,
            "source_complete": False,
            "audit_task_credit": False,
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _sha(stage / "RECEIPT.json"),
            "db_sha256": _sha(stage / "company.sqlite3"),
            "module_sha256": _sha(Path(__file__)),
            "native_version_count": 25,
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = sec._private(destination, directory=True)
    paths = {name: root / name for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3")}
    if {child.name for child in root.iterdir()} != set(paths):
        raise CompanyStoreError("Exact three-file IAM005 source required")
    before = sec._frozen(paths)
    context = _context(repository, private_repository)
    manifest = json.loads(paths["MANIFEST.json"].read_text())
    receipt = json.loads(paths["RECEIPT.json"].read_text())
    if (
        manifest
        != {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _sha(paths["RECEIPT.json"]),
            "db_sha256": _sha(paths["company.sqlite3"]),
            "module_sha256": _sha(Path(__file__)),
            "native_version_count": 25,
            "audit_task_credit": False,
        }
        or receipt.get("schema") != SCHEMA
        or receipt.get("company") != COMPANY
        or receipt.get("branches") != BRANCHES
        or receipt.get("spec_sha256") != SPEC_SHA256
        or receipt.get("reviewed_upstream_sha256") != context["pins"]
        or receipt.get("upstream_selected_refs") != context["refs"]
        or receipt.get("upstream_late_refs") != context["late_refs"]
        or receipt.get("native_version_counts") != {"CLEAN": 9, "MESSY": 16}
        or receipt.get("open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("external_bytes_or_packets") != 0
        or receipt.get("actual_phi_processing") is not False
        or receipt.get("actual_operation_eligibility_as_of_2026_09_30") is not False
        or receipt.get("authored_iam005_clause_satisfied") is not False
        or receipt.get("source_complete") is not False
        or receipt.get("audit_task_credit") is not False
        or receipt.get("limits") != LIMITS
        or receipt.get("selected_population")
        != {
            "marker_count": 1,
            "human_identity_count": 1,
            "inert_service_identity_count": 1,
            "site": "BOISE",
        }
    ):
        raise CompanyStoreError("IAM005 source qualification differs")
    with sqlite3.connect(
        paths["company.sqlite3"].as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("IAM005 source integrity differs")
        for table in ("grants", "collections", "access_events"):
            if db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
                raise CompanyStoreError("IAM005 source has audit access journal")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("IAM005 source systems differ")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 25:
            raise CompanyStoreError("IAM005 source version count differs")
        for scenario, branch in BRANCHES.items():
            expected = _rows(context, scenario)
            refs = receipt["records"][scenario]
            if len(refs) != len(expected):
                raise CompanyStoreError("IAM005 branch receipt count differs")
            for row, ref in zip(expected, refs, strict=True):
                native = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (COMPANY, branch, row["system"], row["record"]),
                ).fetchone()
                if native is None or native["content"] != row["content"]:
                    raise CompanyStoreError("IAM005 raw content differs")
                if (
                    native["sha256"] != row["sha256"]
                    or native["event_at"] != row["event_at"]
                    or native["available_at"] != row["available_at"]
                    or native["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or native["command_id"] != f"IAM5E-{branch}-{row['record']}"
                    or json.loads(native["provenance"])
                    != {
                        "source_reference": SOURCE_REFERENCE,
                        "truth_class": "TRAINING_SCENARIO_ONLY",
                    }
                    or native["imported_at"] >= "2027-01-01"
                    or _time(native["imported_at"]) != native["imported_at"]
                    or ref != CompanyStore._metadata(native)
                ):
                    raise CompanyStoreError("IAM005 raw clocks/provenance/receipt differs")
    if sec._frozen(paths) != before:
        raise CompanyStoreError("IAM005 source changed during verification")
    return {
        "status": "VERIFIED_FICTIONAL_SELECTED_IAM005_SOURCE_NO_AUDIT_CREDIT",
        "native_version_counts": {"CLEAN": 9, "MESSY": 16},
        "audit_task_credit": False,
    }
