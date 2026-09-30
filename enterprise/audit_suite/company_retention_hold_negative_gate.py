"""Future-fictional held fixture denial; never delete source or audit records."""

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

SCHEMA = "SH_FICTIONAL_2027_SELECTED_RETENTION_HOLD_NEGATIVE_GATE_V1"
COMPANY = dataset_source.COMPANY
DATASET = dataset_source.DATASET
AS_OF = "2026-09-29"
RECORD = "RET-HOLD-DAT001-MARKER-01"
CUSTODIAN = "AS-P014"
LEGAL = "AS-P003"
QUALIFICATION = "FUTURE_LOCAL_HELD_FIXTURE_DENIAL_NO_LEGAL_DECISION_OR_AUDIT_CREDIT"
DAT_REL = "enterprise/generated/audit-suite/company-dataset-classification-2026-09-29/run-v1"
DAT_REVIEW = (
    "enterprise/generated/audit-suite/company-dataset-classification-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
PHI_REL = "enterprise/generated/audit-suite/company-phi-ba-2027-simulation-2026-09-29/run-v1"
PHI_REVIEW = (
    "enterprise/generated/audit-suite/company-phi-ba-2027-simulation-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
DISP_REL = "enterprise/generated/audit-suite/company-disposal-runtime-2026-09-22"
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
    f"{DAT_REL}/MANIFEST.json": "ed670cf671da2f2d20579664807bd9a80b3dd7f0dec6e445a09166555adbfb31",
    f"{DAT_REL}/RECEIPT.json": "7c6e74974bcdb5b516b4a476099061543dbb6570e99942b3d74d9ed60bd9c44a",
    f"{DAT_REL}/company.sqlite3": (
        "d668977b852e83ebdcef95d981e24b8863503bc3931c4eac9744ec182cbfde74"
    ),
    DAT_REVIEW: "4d1cd9c423781bf97ff586075c460c891cc60f621b42a29a22db59df929ff52e",
    f"{PHI_REL}/MANIFEST.json": "8226ac2031cafe581289afb4c25088c8dfe603e75ac11fc1ababfe2590f2a5f2",
    f"{PHI_REL}/RECEIPT.json": "20e3762aabb45fcfa3107d695da37e7eeb677f6c5e98f1bb767fa463fe857d9d",
    f"{PHI_REL}/company.sqlite3": (
        "ad252e8cb6b1309b238fbe50daac541d67b5fa89051a0b3d8eab7993d4010449"
    ),
    PHI_REVIEW: "39bb9b071179ed672c5cf07c2867285d36b2f3e8cdce2106dc4472d17047911e",
    f"{DISP_REL}/root-independent-verification-v1/RECEIPT.json": (
        "11a8420269bfe9d39e23ca8e0ebd92a15a9de9b2560901a8bae23b07d734298b"
    ),
    f"{DISP_REL}/run-v1/a/runtime/company.sqlite3": (
        "42aa67405a645890c54e80312ead74aaaa5c2d898b707440b5cffce810ce4746"
    ),
    f"{DISP_REL}/run-v1/b/runtime/company.sqlite3": (
        "d576bd4b16d117c293a019e0d231f2a871ed0f23b8b030ada45a58d885872ca7"
    ),
    f"{REBASE}/SOURCE-REBASE.json": (
        "8fca1ccbaa287f38c5354ad28b8d25ccc58713ab1972d084a13f013dd271ee63"
    ),
    REBASE_REVIEW: "0a9b8b18096bf576ec555c86d13acb2d5cbbfc0f2588755c24770e55f5c7e291",
    MATRIX: "e9477d2074bebce185e412a3ee7c424ded395c1a1128a7c918a94f6acbd1e327",
    MATRIX_REVIEW: "c4064f6217c0e7f69276adc71004d6da7971867ccf3d844a3e198145cec31ace",
}
TRACKED = (
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md",
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md",
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
    "enterprise/audit_suite/DATA_RECORD_PHI_50_ROUTE_GAP_LEDGER_2026-09-29.json",
    "enterprise/audit_suite/company_dataset_classification_exercise.py",
    "enterprise/audit_suite/RETENTION_HOLD_NEGATIVE_GATE_2027_PROPOSAL.md",
    "enterprise/audit_suite/company_retention_hold_negative_gate.py",
)
CANON_PINS = {
    TRACKED[0]: "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496",
    TRACKED[1]: "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751",
    TRACKED[2]: "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433",
    TRACKED[3]: "ec64be770474024c86cc9dd6876a9fd4c47d13478541f10cf3504688234cde63",
}
SOURCE_REF = "enterprise/audit_suite/company_retention_hold_negative_gate.py"
SYSTEMS = (
    "mapping_draft",
    "hold_review_marker",
    "premature_attempt",
    "disposition_gate",
    "cure_notice",
)
FIXTURE = {
    "CLEAN": b"SABLEHARBOR selected synthetic marker fixture CLEAN; no person data.\n",
    "MESSY": b"SABLEHARBOR selected synthetic marker fixture MESSY; no person data.\n",
}
LIMITS = [
    "One new nonpersonal disposable fixture copy per branch, never a company original.",
    "Class, trigger, obligation, accountable owner and Legal approval remain PENDING.",
    "Local hold-review marker is not an accepted legal hold or release.",
    "Both negative gates deny unlink; Messy attempt/cure remain in immutable native history.",
    "No actual PHI, real operation, secure erasure, audit collection or task credit.",
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
        raise CompanyStoreError("Ordinary private held-fixture source required")


def _frozen_db(path: Path) -> tuple:
    _private_file(path)
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Held-fixture source has active sidecar")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise CompanyStoreError("Held-fixture source must be regular")
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        _digest(path),
    )


def _selected(
    private_repository: Path, relative: str, receipt: dict, scenario: str, system: str, record: str
) -> dict:
    path = private_repository / relative / "company.sqlite3"
    before = _frozen_db(path)
    matches = [
        ref
        for ref in receipt["records"][scenario]
        if ref["system"] == system and ref["record"] == record and ref["version"] == 1
    ]
    if len(matches) != 1:
        raise CompanyStoreError("Selected retention source tuple missing")
    ref = matches[0]
    route = tuple(ref[k] for k in ("company", "branch", "system", "record", "version"))
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Retention source DB integrity failure")
        row = db.execute(
            "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
            "AND record=? AND version=?",
            route,
        ).fetchone()
        if row is None or row["sha256"] != ref["sha256"] or sha(row["content"]) != ref["sha256"]:
            raise CompanyStoreError("Selected retention source original differs")
        body = json.loads(row["content"])
        if (
            body["scenario"] != scenario
            or body["payload_bytes"] != 0
            or body["audit_task_credit"] is not False
            or body.get("real_world_processing", body.get("real_world_operation")) is not False
        ):
            raise CompanyStoreError("Selected retention source qualification differs")
        if system == "classification_review" and (
            body["status"] != "LOCAL_RESTRICTED_RECOMMENDATION"
            or body["actual_phi_applicability"] != "UNDETERMINED"
            or body["retention_rule_approved"] is not False
            or body["deletion_rule_approved"] is not False
        ):
            raise CompanyStoreError("Classification has no approved retention rule")
        if system == "flow_register" and (
            body["actual_legal_applicability"] != "UNDETERMINED"
            or body["fixture_contains_real_phi"] is not False
        ):
            raise CompanyStoreError("PHI/BA flow real-world limit differs")
    if _frozen_db(path) != before:
        raise CompanyStoreError("Retention source changed during read")
    return {
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


def _context(repository: Path, private_repository: Path) -> tuple[dict, dict, dict]:
    pins = {}
    for name in TRACKED:
        path = repository / name
        if not path.is_file() or path.is_symlink():
            raise CompanyStoreError("Tracked held-fixture source missing or linked")
        pins[f"repo://{name}"] = _digest(path)
    if any(pins[f"repo://{name}"] != digest for name, digest in CANON_PINS.items()):
        raise CompanyStoreError("Held-fixture canon/ledger source differs")
    appointments = (repository / TRACKED[1]).read_text()
    if (
        "| AS-P003 | Helena Ward | General Counsel |" not in appointments
        or "| AS-P014 | Omar Vale | Data Governance and Records Lead |" not in appointments
    ):
        raise CompanyStoreError("Legal/custodian role projection differs")
    for name, digest in PRIVATE_PINS.items():
        path = private_repository / name
        _private_file(path)
        if _digest(path) != digest:
            raise CompanyStoreError(f"Reviewed held-fixture source differs: {name}")
        pins[f"private://{name}"] = digest
    dat_review = json.loads((private_repository / DAT_REVIEW).read_text())
    phi_review = json.loads((private_repository / PHI_REVIEW).read_text())
    matrix_review = json.loads((private_repository / MATRIX_REVIEW).read_text())
    disposal_review = json.loads(
        (
            private_repository / DISP_REL / "root-independent-verification-v1/RECEIPT.json"
        ).read_text()
    )
    rebase = json.loads((private_repository / REBASE / "SOURCE-REBASE.json").read_text())
    rebase_review = json.loads((private_repository / REBASE_REVIEW).read_text())
    if (
        dat_review.get("verdict") != "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW"
        or phi_review.get("verdict") != "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW"
        or matrix_review.get("verdict") != "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION"
        or disposal_review["status"] != "PASS"
        or rebase_review["status"]
        != "PASS_INDEPENDENT_PRIVATE_REBASED_PACKET_V4_TECHNICAL_AND_BROWSER"
    ):
        raise CompanyStoreError("Independent source/rebase review gate differs")
    for side in "ab":
        path = private_repository / DISP_REL / "run-v1" / side / "runtime" / "company.sqlite3"
        before = _frozen_db(path)
        rebased = rebase["source_roots"].get(str(path.parent))
        if (
            not isinstance(rebased, dict)
            or rebased["company_sqlite3_sha256"] != before[-1]
            or rebased["business_tables_exactly_match_frozen_receipt"] is not True
        ):
            raise CompanyStoreError("Disposal context lacks current post-journal business pin")
    dataset_source.verify(
        private_repository / DAT_REL,
        repository=repository,
        private_repository=private_repository,
    )
    dat_receipt = json.loads((private_repository / DAT_REL / "RECEIPT.json").read_text())
    phi_receipt = json.loads((private_repository / PHI_REL / "RECEIPT.json").read_text())
    selected = {
        scenario: {
            "classification": _selected(
                private_repository,
                DAT_REL,
                dat_receipt,
                scenario,
                "classification_review",
                DATASET,
            ),
            "phi_ba_flow": _selected(
                private_repository,
                PHI_REL,
                phi_receipt,
                scenario,
                "flow_register",
                "FLOW-RECON-01",
            ),
        }
        for scenario in ("CLEAN", "MESSY")
    }
    matrix = json.loads((private_repository / MATRIX).read_text())
    routes = {}
    for side in "AB":
        routes[side] = {}
        for control_id, expected in (("SH-DAT-003", 6), ("SH-REC-004", 7)):
            matches = [
                control
                for family in matrix["sides"][side]["families"]
                for control in family["controls"]
                if control["control_id"] == control_id
            ]
            if (
                len(matches) != 1
                or len(matches[0]["tasks"]) != expected
                or any(
                    task["current_status"] != "NOT_STARTED"
                    or task["current_conclusion"] != "NOT_RUN"
                    or task["task_credit"] is not False
                    for task in matches[0]["tasks"]
                )
            ):
                raise CompanyStoreError("Frozen retention/disposal route cohort differs")
            routes[side][control_id] = [task["task_id"] for task in matches[0]["tasks"]]
    return pins, selected, routes


def _steps(scenario: str) -> tuple[tuple[str, str, str], ...]:
    if scenario == "CLEAN":
        return (
            ("mapping_draft", "2027-08-05T10:00:00+00:00", "CANDIDATE_MAPPING_PENDING"),
            ("hold_review_marker", "2027-08-05T11:00:00+00:00", "LOCAL_HOLD_REVIEW_OPEN"),
            ("disposition_gate", "2027-08-05T12:00:00+00:00", "DENIED_PENDING_AUTHORITY"),
        )
    return (
        ("mapping_draft", "2027-08-16T10:00:00+00:00", "CANDIDATE_MAPPING_PENDING"),
        ("hold_review_marker", "2027-08-16T11:00:00+00:00", "LOCAL_HOLD_REVIEW_OPEN"),
        ("premature_attempt", "2027-08-16T12:00:00+00:00", "PREMATURE_LOCAL_DISPOSITION_REQUEST"),
        ("disposition_gate", "2027-08-16T13:00:00+00:00", "DENIED_PENDING_AUTHORITY_AND_HOLD"),
        ("cure_notice", "2027-08-16T14:00:00+00:00", "REQUEST_WITHDRAWN_HOLD_REVIEW_STILL_OPEN"),
    )


def _identity(path: Path) -> dict:
    _private_file(path)
    info = path.stat()
    return {
        "sha256": _digest(path),
        "size": info.st_size,
        "device": info.st_dev,
        "inode": info.st_ino,
        "mode": stat.S_IMODE(info.st_mode),
    }


def _body(
    scenario: str, step: tuple[str, str, str], source: dict, fixture: dict, previous: dict | None
) -> dict:
    system, at, status = step
    attempted = scenario == "MESSY" and system in {
        "premature_attempt",
        "disposition_gate",
        "cure_notice",
    }
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "system": system,
        "record": RECORD,
        "status": status,
        "event_at": _time(at),
        "available_at": _time(at),
        "actor_person_id": "SIM-LOCAL-OPERATOR-02" if system == "premature_attempt" else CUSTODIAN,
        "legal_person_id_pending": LEGAL,
        "accountable_data_owner": "UNDETERMINED",
        "selected_source_refs": source,
        "draft_record_class": "SYNTHETIC_MARKER_METADATA_CANDIDATE_ONLY",
        "draft_retention_trigger": "SOURCE_RECORD_CREATION_CANDIDATE_ONLY",
        "draft_obligation_mapping": "BA_FLOW_AND_RECORD_DUTIES_REQUIRE_LEGAL_MAPPING",
        "class_trigger_obligation_accepted": False,
        "legal_decision": "PENDING",
        "data_owner_decision": "PENDING",
        "hold_review_marker": "LOCAL_PENDING_NOT_ACCEPTED_LEGAL_HOLD",
        "legal_hold_release": "NOT_AUTHORIZED",
        "attempted_premature_disposition": attempted,
        "attempt_disposition": "DENIED_OR_WITHDRAWN_WITHOUT_UNLINK" if attempted else "NO_ATTEMPT",
        "fixture_copy": {
            "relative_path": f"copies/{scenario}.bin",
            "sha256": fixture["sha256"],
            "size": fixture["size"],
            "device": fixture["device"],
            "inode": fixture["inode"],
        },
        "fixture_copy_retained": True,
        "unlink_executed": False,
        "deletion_verified": False,
        "secure_erasure_claimed": False,
        "previous_local_sha256": previous["sha256"] if previous else None,
        "actual_phi_applicability": "UNDETERMINED",
        "real_world_operation": False,
        "audit_collection": False,
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
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or destination != destination.resolve()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in destination.parents)
    ):
        raise CompanyStoreError("New private retention gate destination required")
    pins, selected, routes = _context(Path(repository), Path(private_repository))
    branches = {"CLEAN": "HOLD-CLEAN", "MESSY": "HOLD-MESSY"}
    with tempfile.TemporaryDirectory(prefix=".hold-stage-", dir=destination.parent) as name:
        stage = Path(name)
        copies = stage / "copies"
        copies.mkdir(mode=0o700)
        before = {}
        for scenario, raw in FIXTURE.items():
            path = copies / f"{scenario}.bin"
            with path.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            path.chmod(0o600)
            before[scenario] = _identity(path)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in branches.items():
            for system in SYSTEMS:
                store.register_system(COMPANY, branch, system, CUSTODIAN)
            records[scenario], previous = [], None
            for step in _steps(scenario):
                if any(
                    ref["available_at"] >= _time(step[1]) for ref in selected[scenario].values()
                ):
                    raise CompanyStoreError("Retention gate predates selected source")
                if _identity(copies / f"{scenario}.bin") != before[scenario]:
                    raise CompanyStoreError("Disposable held fixture changed before denial")
                body = _body(scenario, step, selected[scenario], before[scenario], previous)
                ref = store.append_version(
                    COMPANY,
                    branch,
                    step[0],
                    RECORD,
                    expected_version=0,
                    command_id=f"HG-{branch}-{step[0]}",
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
        after = {scenario: _identity(copies / f"{scenario}.bin") for scenario in FIXTURE}
        if before != after:
            raise CompanyStoreError("Denied disposition changed disposable fixture")
        receipt = {
            "schema": SCHEMA,
            "status": "FUTURE_FICTIONAL_DENIED_DISPOSITION_NO_CREDIT",
            "as_of": AS_OF,
            "company": COMPANY,
            "branches": branches,
            "source_pins": pins,
            "selected_source_refs": selected,
            "selected_route_task_ids": routes,
            "records": records,
            "fixture_identity_before": before,
            "fixture_identity_after": after,
            "local_denominators": {"CLEAN": 1, "MESSY": 1},
            "authority_gate": "LEGAL_AND_DATA_OWNER_APPROVAL_PENDING_NO_HOLD_RELEASE",
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "fixture_sha256": {
                scenario: _digest(copies / f"{scenario}.bin") for scenario in FIXTURE
            },
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": 8,
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
        or {path.name for path in root.iterdir()}
        != {"MANIFEST.json", "RECEIPT.json", "company.sqlite3", "copies"}
    ):
        raise CompanyStoreError("Private ordinary held-fixture source required")
    for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3"):
        _private_file(root / name)
    copies = root / "copies"
    if (
        not copies.is_dir()
        or copies.is_symlink()
        or copies.stat().st_mode & 0o077
        or {path.name for path in copies.iterdir()} != {"CLEAN.bin", "MESSY.bin"}
    ):
        raise CompanyStoreError("Only two new private disposable held copies allowed")
    actual = {scenario: _identity(copies / f"{scenario}.bin") for scenario in FIXTURE}
    if any((copies / f"{scenario}.bin").read_bytes() != raw for scenario, raw in FIXTURE.items()):
        raise CompanyStoreError("Disposable fixture bytes differ")
    manifest = json.loads((root / "MANIFEST.json").read_text())
    receipt = json.loads((root / "RECEIPT.json").read_text())
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _digest(root / "RECEIPT.json"),
        "company_db_sha256": _digest(root / "company.sqlite3"),
        "fixture_sha256": {scenario: actual[scenario]["sha256"] for scenario in FIXTURE},
        "module_sha256": _digest(Path(__file__)),
        "native_version_count": 8,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Held-fixture manifest pin differs")
    pins, selected, routes = _context(Path(repository), Path(private_repository))
    if (
        receipt["schema"] != SCHEMA
        or receipt["status"] != "FUTURE_FICTIONAL_DENIED_DISPOSITION_NO_CREDIT"
        or receipt["as_of"] != AS_OF
        or receipt["company"] != COMPANY
        or receipt["branches"] != {"CLEAN": "HOLD-CLEAN", "MESSY": "HOLD-MESSY"}
        or receipt["source_pins"] != pins
        or receipt["selected_source_refs"] != selected
        or receipt["selected_route_task_ids"] != routes
        or receipt["fixture_identity_before"] != actual
        or receipt["fixture_identity_after"] != actual
        or receipt["local_denominators"] != {"CLEAN": 1, "MESSY": 1}
        or receipt["authority_gate"] != "LEGAL_AND_DATA_OWNER_APPROVAL_PENDING_NO_HOLD_RELEASE"
        or receipt["limits"] != LIMITS
        or set(receipt["records"]) != {"CLEAN", "MESSY"}
    ):
        raise CompanyStoreError("Held-fixture receipt scope or unchanged copy differs")
    with closing(
        sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Held-fixture native DB integrity failure")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != count
            for table, count in (
                ("versions", 8),
                ("systems", 10),
                ("grants", 0),
                ("collections", 0),
                ("access_events", 0),
            )
        ):
            raise CompanyStoreError("Held-fixture population/access differs")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, CUSTODIAN)
            for branch in receipt["branches"].values()
            for system in SYSTEMS
        }:
            raise CompanyStoreError("Held-fixture source custody differs")
        for scenario, branch in receipt["branches"].items():
            steps, refs, previous = _steps(scenario), receipt["records"][scenario], None
            if len(refs) != len(steps):
                raise CompanyStoreError("Held-fixture event denominator differs")
            for step, ref in zip(steps, refs, strict=True):
                system, at, _ = step
                route = (COMPANY, branch, system, RECORD, 1)
                if (
                    tuple(ref[k] for k in ("company", "branch", "system", "record", "version"))
                    != route
                ):
                    raise CompanyStoreError("Held-fixture native route differs")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    route,
                ).fetchone()
                if (
                    row is None
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or row["command_id"] != f"HG-{branch}-{system}"
                    or any(row[k] != ref[k] for k in ("event_at", "available_at", "imported_at"))
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["origin"] != row["origin"]
                ):
                    raise CompanyStoreError("Held-fixture native identity differs")
                provenance = {
                    "source_reference": SOURCE_REF,
                    "source_pins": pins,
                    "scenario": scenario,
                    "qualification": QUALIFICATION,
                }
                if json.loads(row["provenance"]) != provenance or ref["provenance"] != provenance:
                    raise CompanyStoreError("Held-fixture provenance differs")
                if any(item["available_at"] >= _time(at) for item in selected[scenario].values()):
                    raise CompanyStoreError("Held-fixture event predates selected original")
                expected = _body(scenario, step, selected[scenario], actual[scenario], previous)
                if (
                    json.loads(row["content"]) != expected
                    or row["event_at"] != expected["event_at"]
                    or row["available_at"] != expected["available_at"]
                    or row["imported_at"] >= row["event_at"]
                ):
                    raise CompanyStoreError("Held-fixture negative gate or clock differs")
                previous = ref
    return manifest
