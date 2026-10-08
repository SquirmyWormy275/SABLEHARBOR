"""Bounded fictional 2027 ERM-003/004 source, independent of the active audit.

This produces future in-universe activity for one selected Boise recovery change.
It never accepts residual risk, grants audit access, or changes a P1 task.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from pathlib import Path

from . import company_runtime_transition_exercise as transition
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_ERM_STAGEGATE_V1"
COMPANY = transition.COMPANY
AS_OF = "2026-09-29"
QUALIFICATION = "AUTHORED_FUTURE_IN_UNIVERSE_LOCAL_RISK_SOURCE_NO_AUDIT_CREDIT"
TRANSITION_REL = "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3"
TRANSITION_REVIEW_REL = (
    "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/"
    "independent-review-v3/REVIEW.json"
)
MATRIX_REL = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/run-v2/MATRIX.json"
)
MATRIX_REVIEW_REL = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/"
    "independent-review-v2/REVIEW.json"
)
ERM001_REL = (
    "enterprise/generated/audit-suite/company-risk-assessment-2026-09-14/"
    "aligned-v2/company/company.sqlite3"
)
PRIVATE_PINS = {
    f"{TRANSITION_REL}/MANIFEST.json": (
        "f7c6ec3ab460f204f69cf6b50df66399687034b3b63cb38aaee84841daedcbd4"
    ),
    f"{TRANSITION_REL}/RECEIPT.json": (
        "0a0a448f619e490870f69959d196eb6d5ca3747af0d4fb68056195910ce6cc11"
    ),
    f"{TRANSITION_REL}/company.sqlite3": (
        "428b5c740cb8fc627b38f2aa6847e450fd166e62be52a6309d4f5a7b284988fd"
    ),
    TRANSITION_REVIEW_REL: "f1acaeaea963055f99b0de120fd1b0347ee984edf085d353e7af1e427234d5a9",
    MATRIX_REL: "e9477d2074bebce185e412a3ee7c424ded395c1a1128a7c918a94f6acbd1e327",
    MATRIX_REVIEW_REL: "c4064f6217c0e7f69276adc71004d6da7971867ccf3d844a3e198145cec31ace",
    ERM001_REL: "13ce64ca63a6325b47a260776f41c9b8278e0cb02bf3b6967ef9c0b685c5f557",
}
TRACKED_PATHS = (
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md",
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md",
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
    "enterprise/ccf/assurance/design_data/control_procedures.json",
    "enterprise/audit_suite/RISK_GOVERNANCE_STAGEGATE_PROPOSAL.md",
    "enterprise/audit_suite/company_risk_governance_stagegate_exercise.py",
)
SOURCE_REF = "enterprise/audit_suite/company_risk_governance_stagegate_exercise.py"
ACTORS = {
    "TECHNOLOGY": "AS-P007",
    "SECURITY": "AS-P008",
    "PROCUREMENT": "AS-P013",
    "LEGAL": "AS-P003",
}
OWNERS = {
    "stage_input": "AS-P005",
    "stage_assessment": "AS-P005",
    "stage_reassessment": "AS-P005",
    "technical_gate": "AS-P007",
    "residual_request": "AS-P005",
}
DENOMINATORS = {
    "CLEAN": {
        "selected_changed_services": 1,
        "cross_functional_input_versions": 4,
        "stage_assessment_versions": 1,
        "stage_reassessment_versions": 1,
        "technical_gate_versions": 1,
        "pending_residual_request_versions": 1,
    },
    "MESSY": {
        "selected_changed_services": 1,
        "cross_functional_input_versions": 4,
        "stage_assessment_versions": 1,
        "stage_reassessment_versions": 2,
        "technical_gate_versions": 2,
        "pending_residual_request_versions": 2,
    },
}
LIMITS = [
    "2027 events are authored future in-universe as of 2026-09-29; "
    "imported_at is actual insertion.",
    "ERM001 is separate bounded method context, not same-branch evidence or acceptance.",
    "One selected Boise change, not complete 2027 enterprise-risk population.",
    "No enterprise approval, real operation, PHI processing, audit grant, "
    "collection, workpaper, task, Key or grade.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_file(path: Path) -> None:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_nlink != 1
        or path.stat().st_mode & 0o077
        or any(p.is_symlink() for p in path.parents)
    ):
        raise CompanyStoreError("Ordinary private source file required")


def _frozen_db_identity(path: Path) -> tuple[int, int, int, int, int, str]:
    """Reject SQLite sidecars and detect replacement/change across immutable reads."""
    _private_file(path)
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen ERM001 database has active sidecar")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise CompanyStoreError("Frozen ERM001 database must be regular")
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        _digest(path),
    )


def _context(repository: Path, private_repository: Path) -> tuple[dict, dict, dict, dict]:
    repository, private_repository = repository.resolve(), private_repository.resolve()
    tracked = {}
    for relative in TRACKED_PATHS:
        path = repository / relative
        if not path.is_file() or path.is_symlink():
            raise CompanyStoreError("Required tracked risk source missing")
        tracked[f"repo://{relative}"] = _digest(path)
    decision = TRACKED_PATHS[0]
    if tracked[f"repo://{decision}"] != transition.DECISION_SHA256:
        raise CompanyStoreError("Fictional 2027 owner decision differs")
    appointments = (repository / TRACKED_PATHS[1]).read_text()
    if any(actor not in appointments for actor in ("AS-P005", *ACTORS.values())):
        raise CompanyStoreError("Required canonical role absent")
    for relative, expected in PRIVATE_PINS.items():
        path = private_repository / relative
        _private_file(path)
        if _digest(path) != expected:
            raise CompanyStoreError(f"Reviewed private input differs: {relative}")
    review = json.loads((private_repository / TRANSITION_REVIEW_REL).read_text())
    if review.get("verdict") != "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW":
        raise CompanyStoreError("Transition lacks independent private-source review")
    matrix_review = json.loads((private_repository / MATRIX_REVIEW_REL).read_text())
    if matrix_review.get("verdict") != "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION":
        raise CompanyStoreError("Discovery matrix lacks independent review")
    transition_root = private_repository / TRANSITION_REL
    transition.verify(transition_root, repository=repository)
    trans = json.loads((transition_root / "RECEIPT.json").read_text())
    matrix = json.loads((private_repository / MATRIX_REL).read_text())
    routes = {}
    for side in "AB":
        selected = [
            c
            for f in matrix["sides"][side]["families"]
            for c in f["controls"]
            if c["control_id"] in {"SH-ERM-003", "SH-ERM-004"}
        ]
        if (
            len(selected) != 2
            or {c["control_id"]: len(c["tasks"]) for c in selected}
            != {"SH-ERM-003": 5, "SH-ERM-004": 4}
            or any(
                t["current_status"] != "NOT_STARTED"
                or t["current_conclusion"] != "NOT_RUN"
                or t["task_credit"] is not False
                for c in selected
                for t in c["tasks"]
            )
        ):
            raise CompanyStoreError("Frozen nine-route cohort differs")
        routes[side] = {c["control_id"]: [t["task_id"] for t in c["tasks"]] for c in selected}
    risk = {}
    risk_path = private_repository / ERM001_REL
    frozen_before = _frozen_db_identity(risk_path)
    if frozen_before[-1] != PRIVATE_PINS[ERM001_REL]:
        raise CompanyStoreError("Frozen ERM001 database pin changed before read")
    with closing(sqlite3.connect(risk_path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("ERM001 context source corrupt")
        for scenario, branch in (("CLEAN", "risk-a"), ("MESSY", "risk-b")):
            row = db.execute(
                "SELECT * FROM versions WHERE company='SABLEHARBOR' AND branch=? "
                "AND system='risk_assessments' AND record='ASSESSMENT' AND version=2",
                (branch,),
            ).fetchone()
            if row is None or sha(row["content"]) != row["sha256"]:
                raise CompanyStoreError("Bounded ERM001 context route differs")
            body = json.loads(row["content"])
            if (
                body["classification"]
                != "LOCAL_QUARTERLY_RISK_ASSESSMENT_NOT_ACCEPTANCE_OR_OPERATING_ASSURANCE"
                or body["appetite_status"] != "NOT_ESTABLISHED"
                or body["risk_acceptance"] != "NOT_PERFORMED"
                or body["coverage"]
                != "TWO_SELECTED_LOCAL_INPUTS_NOT_ENTERPRISE_RISK_UNIVERSE_COMPLETENESS"
            ):
                raise CompanyStoreError("ERM001 context claims authority or completeness")
            risk[scenario] = {
                k: row[k]
                for k in (
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
    if _frozen_db_identity(risk_path) != frozen_before:
        raise CompanyStoreError("Frozen ERM001 database changed during read")
    pins = {**tracked, **{f"private://{name}": digest for name, digest in PRIVATE_PINS.items()}}
    return pins, trans, risk, routes


def _transition_refs(trans: dict, scenario: str, names: tuple[tuple[str, int], ...]) -> list[dict]:
    refs = []
    for record, version in names:
        matches = [
            r
            for r in trans["records"][scenario]
            if r["record"] == record and r["version"] == version
        ]
        if len(matches) != 1:
            raise CompanyStoreError("Exact transition dependency unavailable")
        refs.append(
            {
                k: matches[0][k]
                for k in (
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
    return refs


def _steps(scenario: str) -> tuple[tuple, ...]:
    base = tuple(
        (
            "stage_input",
            f"INPUT-{role}",
            1,
            f"2027-06-{day}T10:00:00+00:00",
            "OBSERVED_SIMULATED",
            (("C-BOISE", 1), ("I-BOISE", 1)),
        )
        for day, role in ((10, "TECHNOLOGY"), (11, "SECURITY"), (12, "PROCUREMENT"), (13, "LEGAL"))
    )
    assessment = (
        (
            "stage_assessment",
            "BOISE-RECOVERY",
            1,
            "2027-07-01T10:00:00+00:00",
            "LOCAL_ASSESSED_NOT_APPROVED",
            (("I-BOISE", 1),),
        ),
    )
    if scenario == "CLEAN":
        later = (
            (
                "stage_reassessment",
                "BOISE-RECOVERY",
                1,
                "2027-07-23T10:00:00+00:00",
                "TECHNICAL_CRITERIA_OBSERVED_PASS",
                (("CM-BOISE", 1), ("RX-BOISE", 1)),
            ),
            (
                "technical_gate",
                "BOISE-RECOVERY",
                1,
                "2027-07-25T10:00:00+00:00",
                "LOCAL_TECHNICAL_RECOMMENDATION",
                (("CM-BOISE", 1), ("RX-BOISE", 1)),
            ),
            (
                "residual_request",
                "BOISE-RECOVERY",
                1,
                "2027-07-29T10:00:00+00:00",
                "PENDING_AUTHORITY_DECISION",
                (("RL-BOISE", 1),),
            ),
        )
    else:
        later = (
            (
                "stage_reassessment",
                "BOISE-RECOVERY",
                1,
                "2027-07-23T10:00:00+00:00",
                "KEY_DEPENDENCY_FAILED_EXCEPTION_OPEN",
                (("CM-BOISE", 1), ("EX-BOISE", 1), ("RX-BOISE", 1), ("EX-BOISE", 2)),
            ),
            (
                "technical_gate",
                "BOISE-RECOVERY",
                1,
                "2027-07-24T10:00:00+00:00",
                "LOCAL_HOLD_NO_WAIVER",
                (("CM-BOISE", 1), ("RX-BOISE", 1)),
            ),
            (
                "residual_request",
                "BOISE-RECOVERY",
                1,
                "2027-07-25T10:00:00+00:00",
                "PENDING_AUTHORITY_DECISION",
                (("EX-BOISE", 2),),
            ),
            (
                "stage_reassessment",
                "BOISE-RECOVERY",
                2,
                "2027-08-07T10:00:00+00:00",
                "TECHNICAL_RETRY_PASS_EXCEPTION_OPEN",
                (("CM-BOISE", 2), ("RX-BOISE", 2), ("EX-BOISE", 2)),
            ),
            (
                "technical_gate",
                "BOISE-RECOVERY",
                2,
                "2027-08-09T10:00:00+00:00",
                "LOCAL_CONDITIONAL_RECOMMENDATION_EXCEPTION_OPEN",
                (("CM-BOISE", 2), ("RX-BOISE", 2)),
            ),
            (
                "residual_request",
                "BOISE-RECOVERY",
                2,
                "2027-08-11T10:00:00+00:00",
                "PENDING_AUTHORITY_DECISION",
                (("RL-BOISE", 1), ("EX-BOISE", 2)),
            ),
        )
    return base + assessment + later


def _body(scenario: str, step: tuple, refs: list[dict], risk: dict, own: dict) -> dict:
    system, record, version, at, status, _ = step
    actor = ACTORS[record.removeprefix("INPUT-")] if system == "stage_input" else OWNERS[system]
    own_refs = {
        k: v["sha256"]
        for k, v in own.items()
        if k
        in ([f"INPUT-{r}" for r in ACTORS] if system == "stage_assessment" else ["BOISE-RECOVERY"])
    }
    exception_open = (
        scenario == "MESSY"
        and system != "stage_input"
        and (
            (system == "stage_reassessment" and version >= 1)
            or (system in {"technical_gate", "residual_request"})
        )
    )
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "system": system,
        "record": record,
        "version": version,
        "status": status,
        "event_at": _time(at),
        "available_at": _time(at),
        "actor_person_id": actor,
        "system_custodian_person_id": OWNERS[system],
        "selected_changed_service": "RUNTIME-BOISE-DR-INDEPENDENT-RECOVERY",
        "control_context": ["SH-ERM-003", "SH-ERM-004"],
        "transition_source_refs": refs,
        "local_prior_source_sha256": own_refs,
        "erm001_method_context": risk if system == "stage_assessment" else None,
        "erm001_context_limit": (
            "SEPARATE_BOUNDED_ASSESSMENT_NOT_SAME_BRANCH_TRANSITION_OR_AUTHORITY"
        ),
        "risk_statement": (
            "Boise recovery may depend on common keys or facility/carrier paths; "
            "independent recovery requires a passed technical gate."
        ),
        "assessment_basis": "FOUR_ROLE_INPUTS_AND_SELECTED_TRANSITION_V3_RECORDS_ONLY"
        if system == "stage_assessment"
        else None,
        "technical_decision_scope": "LOCAL_RECOMMENDATION_ONLY_SEPARATE_TRANSITION_OWNS_RELEASE"
        if system == "technical_gate"
        else None,
        "residual_risk_request": "PROVIDER_CONCENTRATION_AND_RECOVERY_DEPENDENCY"
        if system == "residual_request"
        else None,
        "risk_acceptance_authority": "P001_PROPOSED_UNRESOLVED"
        if system == "residual_request"
        else None,
        "risk_acceptance": "NOT_PERFORMED",
        "appetite_status": "NOT_ESTABLISHED",
        "enterprise_approval": False,
        "board_ratification": False,
        "historical_bypass_exception_open": exception_open,
        "real_world_operation": False,
        "real_world_actor_action": False,
        "actual_phi_processing": False,
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
    """Publish one new private source; no grants, collections or active-audit writes."""
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or destination != destination.resolve()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in destination.parents)
    ):
        raise CompanyStoreError("New private destination and parent required")
    pins, trans, risk, routes = _context(Path(repository), Path(private_repository))
    branches = {"CLEAN": "RISK-CLEAN", "MESSY": "RISK-MESSY"}
    with tempfile.TemporaryDirectory(prefix=".risk-stage-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in branches.items():
            for system, owner in OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            own, records[scenario] = {}, []
            for step in _steps(scenario):
                system, record, version, at, _status, names = step
                refs = _transition_refs(trans, scenario, names)
                if any(ref["available_at"] >= _time(at) for ref in refs):
                    raise CompanyStoreError("Stage risk source precedes transition availability")
                if system == "stage_assessment" and risk[scenario]["available_at"] >= _time(at):
                    raise CompanyStoreError("Stage assessment precedes ERM001 method context")
                body = _body(scenario, step, refs, risk[scenario], own)
                ref = store.append_version(
                    COMPANY,
                    branch,
                    system,
                    record,
                    expected_version=version - 1,
                    command_id=f"RG-{branch}-{system}-{record}-V{version}",
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
                own[record] = ref
                records[scenario].append(ref)
        receipt = {
            "schema": SCHEMA,
            "status": "FUTURE_FICTIONAL_LOCAL_RISK_ACTIVITY_NO_CREDIT",
            "as_of": AS_OF,
            "company": COMPANY,
            "branches": branches,
            "source_pins": pins,
            "selected_route_task_ids": routes,
            "records": records,
            "local_denominators": DENOMINATORS,
            "authority_gate": "RESIDUAL_RISK_ACCEPTANCE_DELEGATION_UNRESOLVED",
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": sum(map(len, records.values())),
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Reperform input pins, exact native rows, chronology and no-credit limits."""
    root = Path(destination).absolute()
    if (
        root != root.resolve()
        or not root.is_dir()
        or root.stat().st_mode & 0o077
        or any(p.is_symlink() for p in (root, *root.parents))
        or {p.name for p in root.iterdir()} != {"RECEIPT.json", "MANIFEST.json", "company.sqlite3"}
    ):
        raise CompanyStoreError("Private ordinary three-file risk source required")
    for name in ("RECEIPT.json", "MANIFEST.json", "company.sqlite3"):
        _private_file(root / name)
    manifest = json.loads((root / "MANIFEST.json").read_text())
    receipt = json.loads((root / "RECEIPT.json").read_text())
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _digest(root / "RECEIPT.json"),
        "company_db_sha256": _digest(root / "company.sqlite3"),
        "module_sha256": _digest(Path(__file__)),
        "native_version_count": 19,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Risk source manifest differs")
    pins, trans, risk, routes = _context(Path(repository), Path(private_repository))
    if (
        receipt["schema"] != SCHEMA
        or receipt["as_of"] != AS_OF
        or receipt["company"] != COMPANY
        or receipt["status"] != "FUTURE_FICTIONAL_LOCAL_RISK_ACTIVITY_NO_CREDIT"
        or receipt["branches"] != {"CLEAN": "RISK-CLEAN", "MESSY": "RISK-MESSY"}
        or receipt["source_pins"] != pins
        or receipt["selected_route_task_ids"] != routes
        or receipt["local_denominators"] != DENOMINATORS
        or receipt["authority_gate"] != "RESIDUAL_RISK_ACCEPTANCE_DELEGATION_UNRESOLVED"
        or receipt["limits"] != LIMITS
        or set(receipt["records"]) != {"CLEAN", "MESSY"}
    ):
        raise CompanyStoreError("Risk source scope differs")
    with closing(
        sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Risk native DB integrity failure")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != count
            for table, count in (
                ("versions", 19),
                ("systems", 10),
                ("grants", 0),
                ("collections", 0),
                ("access_events", 0),
            )
        ):
            raise CompanyStoreError("Risk population or access differs")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, owner)
            for branch in receipt["branches"].values()
            for system, owner in OWNERS.items()
        }:
            raise CompanyStoreError("Risk system custody differs")
        for scenario, branch in receipt["branches"].items():
            steps, refs, own = _steps(scenario), receipt["records"][scenario], {}
            if len(refs) != len(steps):
                raise CompanyStoreError("Risk source branch denominator differs")
            for step, ref in zip(steps, refs, strict=True):
                system, record, version, at, _status, names = step
                route = (COMPANY, branch, system, record, version)
                if (
                    tuple(ref[k] for k in ("company", "branch", "system", "record", "version"))
                    != route
                ):
                    raise CompanyStoreError("Risk source route differs")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    route,
                ).fetchone()
                if (
                    row is None
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or row["command_id"] != f"RG-{branch}-{system}-{record}-V{version}"
                    or any(row[k] != ref[k] for k in ("event_at", "available_at", "imported_at"))
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["origin"] != row["origin"]
                ):
                    raise CompanyStoreError("Risk native row identity differs")
                expected_provenance = {
                    "source_reference": SOURCE_REF,
                    "source_pins": pins,
                    "scenario": scenario,
                    "qualification": QUALIFICATION,
                }
                if (
                    json.loads(row["provenance"]) != expected_provenance
                    or ref["provenance"] != expected_provenance
                ):
                    raise CompanyStoreError("Risk provenance differs")
                external = _transition_refs(trans, scenario, names)
                if any(x["available_at"] >= _time(at) for x in external):
                    raise CompanyStoreError("Risk source used unavailable transition event")
                expected = _body(scenario, step, external, risk[scenario], own)
                if (
                    json.loads(row["content"]) != expected
                    or row["event_at"] != expected["event_at"]
                    or row["available_at"] != expected["available_at"]
                    or row["imported_at"] >= row["event_at"]
                ):
                    raise CompanyStoreError("Risk source content or future clock differs")
                own[record] = ref
    return manifest
