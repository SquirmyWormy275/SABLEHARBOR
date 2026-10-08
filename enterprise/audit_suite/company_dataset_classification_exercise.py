"""One fictional 2027 marker-metadata dataset and local classification history."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from pathlib import Path

from . import company_phi_ba_2027_simulation as phi_ba
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_SELECTED_DATASET_CLASSIFICATION_V1"
COMPANY = phi_ba.COMPANY
AS_OF = "2026-09-29"
QUALIFICATION = "PAYLOAD_FREE_FUTURE_LOCAL_CLASSIFICATION_NO_REAL_PHI_OR_AUDIT_CREDIT"
DATASET = "DS-SIM-EHR-MARKER-METADATA-01"
MARKER = "SIM-EHR-MARKER-001"
MARKER_SHA = "3d46bd7349cce0657bd70f3d53cc68cd4fb07a6de0d1ede7ccf75ffeb38910de"
OWNER = "AS-P014"
BA_REL = "enterprise/generated/audit-suite/company-phi-ba-2027-simulation-2026-09-29/run-v1"
BA_REVIEW = (
    "enterprise/generated/audit-suite/company-phi-ba-2027-simulation-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
TRANSITION_REL = "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3"
TRANSITION_REVIEW = (
    "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/"
    "independent-review-v3/REVIEW.json"
)
MATRIX_REL = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/run-v2/MATRIX.json"
)
MATRIX_REVIEW = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/"
    "independent-review-v2/REVIEW.json"
)
PRIVATE_PINS = {
    f"{BA_REL}/MANIFEST.json": "8226ac2031cafe581289afb4c25088c8dfe603e75ac11fc1ababfe2590f2a5f2",
    f"{BA_REL}/RECEIPT.json": "20e3762aabb45fcfa3107d695da37e7eeb677f6c5e98f1bb767fa463fe857d9d",
    f"{BA_REL}/company.sqlite3": "ad252e8cb6b1309b238fbe50daac541d67b5fa89051a0b3d8eab7993d4010449",
    BA_REVIEW: "39bb9b071179ed672c5cf07c2867285d36b2f3e8cdce2106dc4472d17047911e",
    f"{TRANSITION_REL}/MANIFEST.json": (
        "f7c6ec3ab460f204f69cf6b50df66399687034b3b63cb38aaee84841daedcbd4"
    ),
    f"{TRANSITION_REL}/RECEIPT.json": (
        "0a0a448f619e490870f69959d196eb6d5ca3747af0d4fb68056195910ce6cc11"
    ),
    f"{TRANSITION_REL}/company.sqlite3": (
        "428b5c740cb8fc627b38f2aa6847e450fd166e62be52a6309d4f5a7b284988fd"
    ),
    TRANSITION_REVIEW: "f1acaeaea963055f99b0de120fd1b0347ee984edf085d353e7af1e427234d5a9",
    MATRIX_REL: "e9477d2074bebce185e412a3ee7c424ded395c1a1128a7c918a94f6acbd1e327",
    MATRIX_REVIEW: "c4064f6217c0e7f69276adc71004d6da7971867ccf3d844a3e198145cec31ace",
}
TRACKED = (
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md",
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md",
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
    "enterprise/audit_suite/company_data_flow_exercise.py",
    "enterprise/audit_suite/company_data_quality_runtime.py",
    "enterprise/audit_suite/DATASET_CLASSIFICATION_2027_PROPOSAL.md",
    "enterprise/audit_suite/company_dataset_classification_exercise.py",
)
SOURCE_REF = "enterprise/audit_suite/company_dataset_classification_exercise.py"
SYSTEMS = (
    "dataset_inventory",
    "local_label",
    "label_quarantine",
    "classification_review",
    "propagation_request",
    "enforcement_followup",
)
DENOMINATORS = {
    "CLEAN": {
        "selected_markers": 1,
        "inventory_versions": 1,
        "invalid_local_labels": 0,
        "quarantines": 0,
        "local_recommendations": 1,
        "propagation_requests": 1,
        "enforcement_followups": 1,
    },
    "MESSY": {
        "selected_markers": 1,
        "inventory_versions": 1,
        "invalid_local_labels": 1,
        "quarantines": 1,
        "local_recommendations": 1,
        "propagation_requests": 1,
        "enforcement_followups": 1,
    },
}
LIMITS = [
    "2027 event/availability is authored future in-universe as of 2026-09-29; "
    "imported_at is actual insertion.",
    "One payload-free synthetic marker-metadata dataset, not an enterprise dataset population.",
    "Local restricted recommendation is not accepted owner/enterprise classification "
    "or intake control proof.",
    "Propagation is requested; actual downstream enforcement and acknowledgement are NOT_VERIFIED.",
    "Actual PHI applicability, real contract obligations, retention/deletion/hold "
    "authority remain UNDETERMINED.",
    "Messy PUBLIC label is local invalid metadata only, without real exposure or disclosure claim.",
    "No audit grant, collection, workpaper, task, Key or grade.",
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
        raise CompanyStoreError("Ordinary private source file required")


def _frozen_db(path: Path) -> tuple:
    _private_file(path)
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen BA database has active sidecar")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise CompanyStoreError("Frozen BA database must be regular")
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        _digest(path),
    )


def _selected_flow(private_repository: Path, receipt: dict) -> dict:
    db_path = private_repository / BA_REL / "company.sqlite3"
    before = _frozen_db(db_path)
    selected = {}
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("BA dataset source integrity failure")
        for scenario, branch in (("CLEAN", "PHI-CLEAN"), ("MESSY", "PHI-MESSY")):
            expected_names = ["FLOW-RENO-01", "FLOW-BOISE-01", "FLOW-RECON-01"]
            if scenario == "MESSY":
                expected_names.append("EXC-01")
            refs = []
            for name in expected_names:
                matches = [
                    ref
                    for ref in receipt["records"][scenario]
                    if ref["record"] == name and ref["version"] == 1
                ]
                if len(matches) != 1:
                    raise CompanyStoreError("Exact selected BA flow tuple missing")
                ref = matches[0]
                route = tuple(ref[k] for k in ("company", "branch", "system", "record", "version"))
                if route[0] != COMPANY or route[1] != branch or route[3] != name:
                    raise CompanyStoreError("BA branch/source identity differs")
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
                    raise CompanyStoreError("BA native tuple content differs")
                body = json.loads(row["content"])
                if (
                    body["scenario"] != scenario
                    or body["real_world_operation"] is not False
                    or body["actual_legal_applicability"] != "UNDETERMINED"
                    or body["fixture_contains_real_phi"] is not False
                    or body["payload_bytes"] != 0
                ):
                    raise CompanyStoreError("BA flow qualification differs")
                if name == "EXC-01":
                    if (
                        body["exception_open"] is not True
                        or body["exception_id"] != phi_ba.EXCEPTION_ID
                    ):
                        raise CompanyStoreError("Messy BA exception state differs")
                elif (
                    body["flow_marker_id"] != MARKER or body["marker_metadata_sha256"] != MARKER_SHA
                ):
                    raise CompanyStoreError("Selected payload-free marker differs")
                expected_after = {
                    "CLEAN": {
                        "FLOW-RENO-01": "RENO_ADMITTED",
                        "FLOW-BOISE-01": "BOISE_ACKNOWLEDGED",
                        "FLOW-RECON-01": "RECONCILED",
                    },
                    "MESSY": {
                        "FLOW-RENO-01": "RENO_ADMITTED",
                        "FLOW-BOISE-01": "ROUTE_UNVERIFIED",
                        "FLOW-RECON-01": "QUARANTINED",
                    },
                }
                if name != "EXC-01" and body["after"] != expected_after[scenario][name]:
                    raise CompanyStoreError("Selected BA branch chronology differs")
                refs.append(
                    {
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
                )
            selected[scenario] = refs
    if _frozen_db(db_path) != before:
        raise CompanyStoreError("Frozen BA database changed during read")
    return selected


def _context(repository: Path, private_repository: Path) -> tuple[dict, dict, dict]:
    repository, private_repository = repository.resolve(), private_repository.resolve()
    pins = {}
    for relative in TRACKED:
        path = repository / relative
        if not path.is_file() or path.is_symlink():
            raise CompanyStoreError("Required tracked classification source absent")
        pins[f"repo://{relative}"] = _digest(path)
    if pins[f"repo://{TRACKED[0]}"] != (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ):
        raise CompanyStoreError("Fictional scenario owner decision differs")
    if pins[f"repo://{TRACKED[1]}"] != (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ) or pins[f"repo://{TRACKED[2]}"] != (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ):
        raise CompanyStoreError("Bounded canon role/control source differs")
    appointments = (repository / TRACKED[1]).read_text()
    if "| AS-P014 | Omar Vale | Data Governance and Records Lead |" not in appointments:
        raise CompanyStoreError("Canonical proposed Data Governance custodian differs")
    if (
        "| SH-DAT-001 | Data domains and material datasets identify accountable "
        "owners/stewards and classification." not in (repository / TRACKED[2]).read_text()
    ):
        raise CompanyStoreError("Bounded dataset control objective differs")
    for relative, expected in PRIVATE_PINS.items():
        path = private_repository / relative
        _private_file(path)
        if _digest(path) != expected:
            raise CompanyStoreError(f"Reviewed private classification input differs: {relative}")
        pins[f"private://{relative}"] = expected
    if json.loads((private_repository / BA_REVIEW).read_text()).get("verdict") != (
        "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW"
    ):
        raise CompanyStoreError("BA source lacks independent review")
    if json.loads((private_repository / TRANSITION_REVIEW).read_text()).get("verdict") != (
        "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW"
    ):
        raise CompanyStoreError("Transition source lacks independent review")
    if json.loads((private_repository / MATRIX_REVIEW).read_text()).get("verdict") != (
        "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION"
    ):
        raise CompanyStoreError("Frozen route matrix lacks independent review")
    phi_ba.verify(
        private_repository / BA_REL,
        transition_root=private_repository / TRANSITION_REL,
        repository=repository,
    )
    receipt = json.loads((private_repository / BA_REL / "RECEIPT.json").read_text())
    selected = _selected_flow(private_repository, receipt)
    matrix = json.loads((private_repository / MATRIX_REL).read_text())
    routes = {}
    for side in "AB":
        matches = [
            control
            for family in matrix["sides"][side]["families"]
            for control in family["controls"]
            if control["control_id"] == "SH-DAT-001"
        ]
        if (
            len(matches) != 1
            or len(matches[0]["tasks"]) != 4
            or matches[0]["candidate_native_source_search_target"]
            != "Dataset and classification register"
            or any(
                task["current_status"] != "NOT_STARTED"
                or task["current_conclusion"] != "NOT_RUN"
                or task["task_credit"] is not False
                for task in matches[0]["tasks"]
            )
        ):
            raise CompanyStoreError("Frozen four-route dataset cohort differs")
        routes[side] = [task["task_id"] for task in matches[0]["tasks"]]
    return pins, selected, routes


def _steps(scenario: str) -> tuple[tuple, ...]:
    if scenario == "CLEAN":
        return (
            (
                "dataset_inventory",
                "2027-07-29T09:00:00+00:00",
                "ONE_MARKER_METADATA_DATASET_RECORDED",
            ),
            (
                "classification_review",
                "2027-07-29T10:00:00+00:00",
                "LOCAL_RESTRICTED_RECOMMENDATION",
            ),
            ("propagation_request", "2027-07-29T11:00:00+00:00", "REQUESTED_NOT_ACKNOWLEDGED"),
            ("enforcement_followup", "2027-07-30T09:00:00+00:00", "NOT_VERIFIED"),
        )
    return (
        ("dataset_inventory", "2027-08-11T09:00:00+00:00", "ONE_MARKER_METADATA_DATASET_RECORDED"),
        ("local_label", "2027-08-11T10:00:00+00:00", "INVALID_PUBLIC_METADATA_MARKER"),
        ("label_quarantine", "2027-08-11T11:00:00+00:00", "LOCAL_MARKER_QUARANTINED"),
        ("classification_review", "2027-08-11T12:00:00+00:00", "LOCAL_RESTRICTED_RECOMMENDATION"),
        (
            "propagation_request",
            "2027-08-11T13:00:00+00:00",
            "REQUESTED_WITH_STALE_LABEL_EXCEPTION",
        ),
        ("enforcement_followup", "2027-08-12T09:00:00+00:00", "NOT_VERIFIED_STALE_LABEL_OPEN"),
    )


def _body(scenario: str, step: tuple, upstream: list[dict], previous: dict | None) -> dict:
    system, at, status = step
    index = [item[0] for item in _steps(scenario)].index(system)
    classified = index >= [item[0] for item in _steps(scenario)].index("classification_review")
    propagation = index >= [item[0] for item in _steps(scenario)].index("propagation_request")
    invalid = scenario == "MESSY" and index >= 1
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "system": system,
        "record": DATASET,
        "status": status,
        "event_at": _time(at),
        "available_at": _time(at),
        "actor_person_id": "SIM-LOCAL-OPERATOR-01" if system == "local_label" else OWNER,
        "custodian_person_id": OWNER,
        "actor_authority_limit": (
            "IN_UNIVERSE_LOCAL_RECOMMENDATION_PROPOSED_CUSTODIAN_NO_ENTERPRISE_DELEGATION"
        ),
        "accountable_data_owner": "UNDETERMINED",
        "dataset_id": DATASET,
        "data_domain": "SYNTHETIC_CUSTOMER_MARKER_METADATA",
        "source_marker_id": MARKER,
        "marker_metadata_sha256": MARKER_SHA,
        "selected_marker_count": 1,
        "payload_bytes": 0,
        "upstream_flow_refs": upstream,
        "previous_local_sha256": previous["sha256"] if previous else None,
        "classification_recommendation": ("RESTRICTED_SCENARIO_METADATA" if classified else None),
        "classification_decision_state": (
            "LOCAL_RECOMMENDATION_NOT_DATA_OWNER_ACCEPTED"
            if classified
            else "INVALID_LOCAL_LABEL_NOT_CLASSIFICATION_DECISION"
            if system == "local_label"
            else "NOT_REVIEWED"
        ),
        "invalid_public_local_metadata_label": system == "local_label",
        "invalid_label_history_open": invalid,
        "local_label_quarantined": scenario == "MESSY" and index >= 2,
        "upstream_ba_exception_open": scenario == "MESSY",
        "propagation_status": "REQUESTED_NOT_ACKNOWLEDGED" if propagation else "NOT_REQUESTED",
        "enforcement_status": "NOT_VERIFIED" if system == "enforcement_followup" else "NOT_TESTED",
        "intake_control_verified": False,
        "retention_rule_approved": False,
        "deletion_rule_approved": False,
        "legal_hold_disposition": "UNDETERMINED",
        "real_contractual_obligations": "UNDETERMINED",
        "actual_phi_applicability": "UNDETERMINED",
        "real_phi_payload": False,
        "real_world_processing": False,
        "real_world_exposure_or_disclosure": False,
        "enterprise_dataset_completeness": "NOT_ESTABLISHED",
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
    """Publish one private candidate dataset source, without audit collection."""
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or destination != destination.resolve()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in destination.parents)
    ):
        raise CompanyStoreError("New private dataset destination required")
    pins, selected, routes = _context(Path(repository), Path(private_repository))
    branches = {"CLEAN": "DATASET-CLEAN", "MESSY": "DATASET-MESSY"}
    with tempfile.TemporaryDirectory(prefix=".dataset-stage-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in branches.items():
            for system in SYSTEMS:
                store.register_system(COMPANY, branch, system, OWNER)
            records[scenario], previous = [], None
            for system, at, status in _steps(scenario):
                if any(ref["available_at"] >= _time(at) for ref in selected[scenario]):
                    raise CompanyStoreError("Dataset event predates BA source availability")
                body = _body(scenario, (system, at, status), selected[scenario], previous)
                ref = store.append_version(
                    COMPANY,
                    branch,
                    system,
                    DATASET,
                    expected_version=0,
                    command_id=f"DC-{branch}-{system}",
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
            "status": "FUTURE_FICTIONAL_LOCAL_CLASSIFICATION_NO_CREDIT",
            "as_of": AS_OF,
            "company": COMPANY,
            "branches": branches,
            "source_pins": pins,
            "selected_route_task_ids": routes,
            "selected_upstream_refs": selected,
            "records": records,
            "local_denominators": DENOMINATORS,
            "authority_gate": "DATA_OWNER_RETENTION_LEGAL_AND_ENFORCEMENT_UNRESOLVED",
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": 10,
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Reperform exact selected source route and local classification limits."""
    root = Path(destination).absolute()
    if (
        root != root.resolve()
        or not root.is_dir()
        or root.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in (root, *root.parents))
        or {path.name for path in root.iterdir()}
        != {"MANIFEST.json", "RECEIPT.json", "company.sqlite3"}
    ):
        raise CompanyStoreError("Private ordinary three-file dataset source required")
    for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3"):
        _private_file(root / name)
    manifest = json.loads((root / "MANIFEST.json").read_text())
    receipt = json.loads((root / "RECEIPT.json").read_text())
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _digest(root / "RECEIPT.json"),
        "company_db_sha256": _digest(root / "company.sqlite3"),
        "module_sha256": _digest(Path(__file__)),
        "native_version_count": 10,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Dataset manifest pin differs")
    pins, selected, routes = _context(Path(repository), Path(private_repository))
    if (
        receipt["schema"] != SCHEMA
        or receipt["status"] != "FUTURE_FICTIONAL_LOCAL_CLASSIFICATION_NO_CREDIT"
        or receipt["as_of"] != AS_OF
        or receipt["company"] != COMPANY
        or receipt["branches"] != {"CLEAN": "DATASET-CLEAN", "MESSY": "DATASET-MESSY"}
        or receipt["source_pins"] != pins
        or receipt["selected_route_task_ids"] != routes
        or receipt["selected_upstream_refs"] != selected
        or receipt["local_denominators"] != DENOMINATORS
        or receipt["limits"] != LIMITS
        or receipt["authority_gate"] != "DATA_OWNER_RETENTION_LEGAL_AND_ENFORCEMENT_UNRESOLVED"
        or set(receipt["records"]) != {"CLEAN", "MESSY"}
    ):
        raise CompanyStoreError("Dataset receipt scope differs")
    with closing(
        sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Native dataset database integrity failure")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != count
            for table, count in (
                ("versions", 10),
                ("systems", 12),
                ("grants", 0),
                ("collections", 0),
                ("access_events", 0),
            )
        ):
            raise CompanyStoreError("Dataset population/access differs")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, OWNER)
            for branch in receipt["branches"].values()
            for system in SYSTEMS
        }:
            raise CompanyStoreError("Dataset system custody differs")
        for scenario, branch in receipt["branches"].items():
            steps, refs, previous = _steps(scenario), receipt["records"][scenario], None
            if len(refs) != len(steps):
                raise CompanyStoreError("Dataset branch denominator differs")
            for step, ref in zip(steps, refs, strict=True):
                system, at, _status = step
                route = (COMPANY, branch, system, DATASET, 1)
                if (
                    tuple(ref[key] for key in ("company", "branch", "system", "record", "version"))
                    != route
                ):
                    raise CompanyStoreError("Dataset route differs")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    route,
                ).fetchone()
                if (
                    row is None
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or row["command_id"] != f"DC-{branch}-{system}"
                    or any(
                        row[key] != ref[key] for key in ("event_at", "available_at", "imported_at")
                    )
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["origin"] != row["origin"]
                ):
                    raise CompanyStoreError("Native dataset row identity differs")
                provenance = {
                    "source_reference": SOURCE_REF,
                    "source_pins": pins,
                    "scenario": scenario,
                    "qualification": QUALIFICATION,
                }
                if json.loads(row["provenance"]) != provenance or ref["provenance"] != provenance:
                    raise CompanyStoreError("Dataset provenance differs")
                if any(item["available_at"] >= _time(at) for item in selected[scenario]):
                    raise CompanyStoreError("Dataset source availability differs")
                expected = _body(scenario, step, selected[scenario], previous)
                if (
                    json.loads(row["content"]) != expected
                    or row["event_at"] != expected["event_at"]
                    or row["available_at"] != expected["available_at"]
                    or row["imported_at"] >= row["event_at"]
                ):
                    raise CompanyStoreError("Dataset content or future clock differs")
                previous = ref
    return manifest
