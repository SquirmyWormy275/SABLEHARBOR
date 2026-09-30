"""One-marker fictional processing-purpose case sourced from reviewed company originals."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from . import company_dataset_classification_exercise as dataset
from . import company_phi_ba_2027_simulation as phi_ba
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_SELECTED_PROCESSING_PURPOSE_V1"
COMPANY = phi_ba.COMPANY
MARKER = "SIM-EHR-MARKER-001"
DATASET = dataset.DATASET
BRANCHES = {"CLEAN": "PURPOSE-CLEAN", "MESSY": "PURPOSE-MESSY"}
PHI_REL = "enterprise/generated/audit-suite/company-phi-ba-2027-simulation-2026-09-29"
DATASET_REL = "enterprise/generated/audit-suite/company-dataset-classification-2026-09-29"
TRANSITION_REL = "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3"
SOURCE_REFERENCE = "enterprise/audit_suite/company_processing_purpose_2027_simulation.py"
PURPOSE_TERM = (
    "SHI may receive, maintain and route only the payload-free scenario marker for "
    "customer-directed hosting and recovery; no other scenario use or disclosure is permitted."
)
SOURCE_PINS = {
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "enterprise/audit_suite/phi_ba_2027_contract_spec_v1.json": (
        "557cd3ddf09195207de93be2441710f38be9aa8693de729c07d8cf45e45a081f"
    ),
    "enterprise/ccf/assurance/design_data/control_procedures.json": (
        "258f5c868e16f3dc197594857dc86a4f2b3ef11e3e5a36dd0a80a9fc6d40c679"
    ),
}
UPSTREAM = {
    "PHI": {
        "rel": PHI_REL,
        "run": "run-v1",
        "review": "independent-review-v1/REVIEW.json",
        "manifest": "8226ac2031cafe581289afb4c25088c8dfe603e75ac11fc1ababfe2590f2a5f2",
        "receipt": "20e3762aabb45fcfa3107d695da37e7eeb677f6c5e98f1bb767fa463fe857d9d",
        "database": "ad252e8cb6b1309b238fbe50daac541d67b5fa89051a0b3d8eab7993d4010449",
        "review_sha256": "39bb9b071179ed672c5cf07c2867285d36b2f3e8cdce2106dc4472d17047911e",
        "schema": "SH_FICTIONAL_2027_PHI_BA_FLOW_V1",
        "branches": {"CLEAN": "PHI-CLEAN", "MESSY": "PHI-MESSY"},
    },
    "DATASET": {
        "rel": DATASET_REL,
        "run": "run-v1",
        "review": "independent-review-v1/REVIEW.json",
        "manifest": "ed670cf671da2f2d20579664807bd9a80b3dd7f0dec6e445a09166555adbfb31",
        "receipt": "7c6e74974bcdb5b516b4a476099061543dbb6570e99942b3d74d9ed60bd9c44a",
        "database": "d668977b852e83ebdcef95d981e24b8863503bc3931c4eac9744ec182cbfde74",
        "review_sha256": "4d1cd9c423781bf97ff586075c460c891cc60f621b42a29a22db59df929ff52e",
        "schema": "SH_FICTIONAL_2027_SELECTED_DATASET_CLASSIFICATION_V1",
        "branches": {"CLEAN": "DATASET-CLEAN", "MESSY": "DATASET-MESSY"},
    },
}
SYSTEM_OWNERS = {
    "purpose_request": "AS-P014",
    "purpose_review": "AS-P003",
    "privacy_case_queue": "AS-P003",
    "purpose_reconciliation": "AS-P014",
}
EXCEPTION_ID = "EXC-SIM-PURPOSE-REUSE-01"
LIMITS = [
    "Future 2027 training-world source events; imported_at is actual insertion time.",
    "Upstream synthetic contract permits customer-directed marker hosting/recovery only; "
    "dataset owner acceptance and enforcement remain pending even in Clean.",
    "Messy AI-training reuse is a refused request, not executed processing or transfer.",
    "No real PHI, HIPAA applicability, actual contract, rights response, external request, "
    "payload, deployment or audit task credit.",
    "No P1 grant, collection, workpaper, task, Key or Atlas mutation.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private(path: Path, *, directory: bool) -> Path:
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CompanyStoreError("Private nonsymlink path required")
    info = path.stat()
    if directory:
        if not path.is_dir() or info.st_mode & 0o077:
            raise CompanyStoreError("Private directory required")
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
        raise CompanyStoreError("Private regular source file required")
    return path


def _frozen(paths: dict[str, Path]) -> dict[str, tuple]:
    db = paths["database"]
    if any(
        Path(str(db) + suffix).exists() or Path(str(db) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen company database has sidecar")
    result = {}
    for key, path in paths.items():
        _private(path, directory=False)
        info = path.stat()
        result[key] = (
            info.st_dev,
            info.st_ino,
            stat.S_IMODE(info.st_mode),
            info.st_size,
            info.st_mtime_ns,
            _digest(path),
        )
    return result


def _read_upstream(private_repository: Path, config: dict) -> dict:
    parent = _private(private_repository / config["rel"], directory=True)
    root = _private(parent / config["run"], directory=True)
    paths = {
        "manifest": root / "MANIFEST.json",
        "receipt": root / "RECEIPT.json",
        "database": root / "company.sqlite3",
        "review_sha256": parent / config["review"],
    }
    before = _frozen(paths)
    if any(before[key][-1] != config[key] for key in paths):
        raise CompanyStoreError("Independently reviewed upstream bytes differ")
    manifest = json.loads(paths["manifest"].read_text())
    receipt = json.loads(paths["receipt"].read_text())
    review = json.loads(paths["review_sha256"].read_text())
    if (
        manifest.get("schema") != config["schema"] + "_MANIFEST"
        or manifest.get("receipt_sha256") != config["receipt"]
        or manifest.get("company_db_sha256") != config["database"]
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != config["schema"]
        or receipt.get("branches") != config["branches"]
        or not str(review.get("verdict", "")).startswith("PASS")
    ):
        raise CompanyStoreError("Upstream review/scope differs")
    selected = {s: {} for s in BRANCHES}
    needed = {
        "PHI": {
            "CLEAN": {
                ("contract_register", "BAA-CUST-01"),
                ("contract_register", "BAA-SUB-01"),
                ("flow_register", "FLOW-RECON-01"),
            },
            "MESSY": {
                ("contract_register", "BAA-CUST-01"),
                ("contract_register", "BAA-SUB-01"),
                ("flow_register", "FLOW-RECON-01"),
                ("exception_register", "EXC-01"),
            },
        },
        "DATASET": {
            "CLEAN": {
                ("dataset_inventory", DATASET),
                ("classification_review", DATASET),
                ("enforcement_followup", DATASET),
            },
            "MESSY": {
                ("dataset_inventory", DATASET),
                ("label_quarantine", DATASET),
                ("classification_review", DATASET),
                ("enforcement_followup", DATASET),
            },
        },
    }
    source_id = "PHI" if config["schema"] == UPSTREAM["PHI"]["schema"] else "DATASET"
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Upstream source integrity failed")
        for scenario, branch in config["branches"].items():
            refs = {
                (r["system"], r["record"]): r
                for r in receipt["records"][scenario]
                if r["version"] == 1
            }
            if not needed[source_id][scenario] <= set(refs):
                raise CompanyStoreError("Required upstream native tuple missing")
            for system, record in needed[source_id][scenario]:
                ref = refs[system, record]
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (ref["company"], branch, system, record),
                ).fetchone()
                if (
                    row is None
                    or ref["branch"] != branch
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or (row["event_at"], row["available_at"], row["imported_at"])
                    != (ref["event_at"], ref["available_at"], ref["imported_at"])
                ):
                    raise CompanyStoreError("Upstream native receipt tuple differs")
                selected[scenario][system, record] = {
                    "ref": ref,
                    "body": json.loads(row["content"]),
                }
    if _frozen(paths) != before:
        raise CompanyStoreError("Upstream source changed during read")
    return selected


def _input_context(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    for name, expected in SOURCE_PINS.items():
        path = repository / name
        if path.is_symlink() or not path.is_file() or _digest(path) != expected:
            raise CompanyStoreError("Tracked scenario source pin differs")
    phi_root = private_repository / PHI_REL / "run-v1"
    ds_root = private_repository / DATASET_REL / "run-v1"
    phi_ba.verify(
        phi_root,
        transition_root=private_repository / TRANSITION_REL,
        repository=repository,
    )
    dataset.verify(ds_root, repository=repository, private_repository=private_repository)
    contract_spec = json.loads(
        (repository / "enterprise/audit_suite/phi_ba_2027_contract_spec_v1.json").read_text()
    )
    terms = contract_spec["synthetic_terms"]["SIM-BAA-CUST-01"]
    permitted = [
        x["scenario_obligation"]
        for x in terms
        if x["clause_candidate_id"] == "permitted_uses_and_disclosures"
    ]
    if permitted != [PURPOSE_TERM]:
        raise CompanyStoreError("Exact synthetic permitted purpose differs")
    phi = _read_upstream(private_repository, UPSTREAM["PHI"])
    ds = _read_upstream(private_repository, UPSTREAM["DATASET"])
    for scenario in BRANCHES:
        contract = phi[scenario]["contract_register", "BAA-CUST-01"]
        downstream = phi[scenario]["contract_register", "BAA-SUB-01"]
        flow = phi[scenario]["flow_register", "FLOW-RECON-01"]
        classification = ds[scenario]["classification_review", DATASET]
        followup = ds[scenario]["enforcement_followup", DATASET]
        body = contract["body"]
        if (
            body["contract_id"] != "SIM-BAA-CUST-01"
            or body["contract_executed_in_simulation"] is not True
            or body["real_signature_or_agreement"] is not False
            or body["reviewed_synthetic_terms_sha256"] != sha(encoded(terms))
            or body["synthetic_terms"] != terms
            or body["actual_legal_applicability"] != "UNDETERMINED"
            or body["fixture_contains_real_phi"] is not False
            or not set(body["authorization_gate_refs"])
            >= {"ROLE-01", "DA-PHI-BA-2027", "VA-CUST-01", "AP-CUST-LEGAL", "AP-CUST-DATA"}
            or downstream["body"]["real_signature_or_agreement"] is not False
            or classification["body"]["classification_decision_state"]
            != "LOCAL_RECOMMENDATION_NOT_DATA_OWNER_ACCEPTED"
            or classification["body"]["accountable_data_owner"] != "UNDETERMINED"
            or followup["body"]["enforcement_status"] != "NOT_VERIFIED"
            or followup["body"]["payload_bytes"] != 0
            or flow["body"]["payload_bytes"] != 0
            or flow["body"]["flow_marker_id"] != MARKER
            or flow["body"]["marker_metadata_sha256"] != dataset.MARKER_SHA
        ):
            raise CompanyStoreError("Upstream purpose/classification gate differs")
        if scenario == "CLEAN":
            if (
                flow["body"]["after"] != "RECONCILED"
                or followup["body"]["invalid_label_history_open"] is not False
                or downstream["body"]["contract_executed_in_simulation"] is not True
            ):
                raise CompanyStoreError("Clean upstream branch differs")
        else:
            exception = phi[scenario]["exception_register", "EXC-01"]["body"]
            if (
                flow["body"]["after"] != "QUARANTINED"
                or exception["exception_open"] is not True
                or exception["exception_id"] != phi_ba.EXCEPTION_ID
                or followup["body"]["invalid_label_history_open"] is not True
                or followup["body"]["local_label_quarantined"] is not True
            ):
                raise CompanyStoreError("Messy upstream branch differs")
        if contract["ref"]["available_at"] > followup["ref"]["available_at"]:
            raise CompanyStoreError("Synthetic contract unavailable before dataset follow-up")
    return {"phi": phi, "dataset": ds, "terms_sha256": sha(encoded(terms))}


def _ref(selected: dict, scenario: str, system: str, record: str) -> dict:
    ref = selected[scenario][system, record]["ref"]
    return {
        k: ref[k]
        for k in (
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


def _expected_rows(context: dict, scenario: str) -> list[dict]:
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown processing-purpose branch")
    messy = scenario == "MESSY"
    follow = context["dataset"][scenario]["enforcement_followup", DATASET]["ref"]
    base = datetime.fromisoformat(follow["available_at"]) + timedelta(hours=1)
    refs = {
        "upstream_contract": _ref(context["phi"], scenario, "contract_register", "BAA-CUST-01"),
        "downstream_contract": _ref(context["phi"], scenario, "contract_register", "BAA-SUB-01"),
        "upstream_flow": _ref(context["phi"], scenario, "flow_register", "FLOW-RECON-01"),
        "dataset_inventory": _ref(context["dataset"], scenario, "dataset_inventory", DATASET),
        "classification_review": _ref(
            context["dataset"], scenario, "classification_review", DATASET
        ),
        "classification_followup": _ref(
            context["dataset"], scenario, "enforcement_followup", DATASET
        ),
    }
    if messy:
        refs["upstream_flowdown_exception"] = _ref(
            context["phi"], scenario, "exception_register", "EXC-01"
        )
        refs["label_quarantine"] = _ref(context["dataset"], scenario, "label_quarantine", DATASET)
    common = {
        "schema": SCHEMA,
        "scenario": scenario,
        "control_id": "SH-DAT-002",
        "boundary_id": "corporate",
        "actor_authority_limit": "PROPOSED_CONTACT_TRAINING_SCENARIO_ONLY_NO_ACTUAL_DELEGATION",
        "marker_id": MARKER,
        "dataset_id": DATASET,
        "marker_metadata_sha256": dataset.MARKER_SHA,
        "payload_bytes": 0,
        "real_phi_payload": False,
        "real_world_processing_or_transfer": False,
        "actual_hipaa_applicability": "UNDETERMINED",
        "actual_customer_or_contract_status": "UNDETERMINED",
        "rights_request_or_response": "NONE_IN_THIS_SELECTED_FIXTURE_NOT_ENTERPRISE_NONOCCURRENCE",
        "task_credit": False,
        "truth_class": "FUTURE_TRAINING_SCENARIO_ONLY",
    }
    request_kind = "AI_MODEL_TRAINING_REUSE" if messy else "CUSTOMER_DIRECTED_HOSTING_RECOVERY"
    items = [
        (
            "purpose_request",
            "REQ-01",
            base,
            {
                "action": "LOCAL_PURPOSE_REQUEST_RECORDED",
                "requested_purpose": request_kind,
                "requested_recipient": "SIM-AI-TRAINING-USE-01"
                if messy
                else "SIM-RESTRICTED-HOSTING-01",
                "attempted_request_only": True,
                "upstream_refs": refs,
            },
        ),
        (
            "purpose_review",
            "DEC-01",
            base + timedelta(hours=1),
            {
                "action": "CONTRACT_PURPOSE_SCREEN",
                "requested_purpose": request_kind,
                "contract_purpose_match": not messy,
                "contract_purpose_basis": PURPOSE_TERM,
                "reviewed_synthetic_terms_sha256": context["terms_sha256"],
                "decision": "SCENARIO_CONTRACT_PURPOSE_MATCH_EXECUTION_PENDING"
                if not messy
                else "REFUSED_UNAPPROVED_AI_REUSE",
                "execution_gate": "PENDING_DATA_OWNER_CLASSIFICATION_AND_ENFORCEMENT"
                if not messy
                else "DENIED_PURPOSE_OUTSIDE_SIMULATED_TERMS",
                "real_world_legal_approval": False,
                "data_owner_acceptance": "PENDING",
                "downstream_enforcement": "NOT_VERIFIED",
                "new_flow_executed": False,
            },
        ),
        (
            "privacy_case_queue",
            "CASE-01",
            base + timedelta(hours=2),
            {
                "action": "ROUTE_CASE_WITHOUT_EXECUTION",
                "case_status": "QUARANTINED_REFUSED_REQUEST"
                if messy
                else "PENDING_OWNER_AND_ENFORCEMENT_GATE",
                "purpose_exception_id": EXCEPTION_ID if messy else None,
                "upstream_ba_exception_id": phi_ba.EXCEPTION_ID if messy else None,
                "stale_label_exception_open": messy,
                "payload_copied_or_transferred": False,
                "external_request_or_response_sent": False,
                "legal_and_data_owner_review": "PENDING_FOR_ANY_ACTUAL_PROCESSING",
            },
        ),
        (
            "purpose_reconciliation",
            "RECON-01",
            base + timedelta(days=1),
            {
                "action": "RECONCILE_REQUEST_DECISION_AND_CASE",
                "selected_request_count": 1,
                "approved_execution_count": 0,
                "refused_request_count": int(messy),
                "pending_request_count": int(not messy),
                "purpose_exception_open": messy,
                "unresolved_authority_gate": "DATA_OWNER_AND_ENFORCEMENT"
                if not messy
                else "PURPOSE_REFUSAL_AND_UPSTREAM_EXCEPTIONS",
                "rights_response_count": 0,
                "actual_transfer_count": 0,
            },
        ),
    ]
    rows = []
    prior = None
    for system, record, at, body in items:
        event = _time(at.isoformat())
        available = _time((at + timedelta(minutes=10)).isoformat())
        value = {
            **common,
            "record": record,
            "actor_person_id": SYSTEM_OWNERS[system],
            "event_at": event,
            "available_at": available,
            "source_previous": prior,
            **body,
        }
        item = {
            "system": system,
            "record": record,
            "version": 1,
            "event_at": event,
            "available_at": available,
            "body": value,
            "sha256": sha(encoded(value)),
        }
        rows.append(item)
        prior = {
            k: item[k]
            for k in ("system", "record", "version", "sha256", "event_at", "available_at")
        }
    return rows


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2)
        stream.write("\n")
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    _private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("New private processing-purpose destination required")
    context = _input_context(repository, private_repository)
    with tempfile.TemporaryDirectory(prefix=".purpose-stage-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            records[scenario] = []
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            for item in _expected_rows(context, scenario):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    item["system"],
                    item["record"],
                    expected_version=0,
                    command_id=f"PUR-{branch}-{item['system']}-{item['record']}",
                    event_at=item["event_at"],
                    available_at=item["available_at"],
                    content=encoded(item["body"]),
                    provenance={
                        "source_reference": SOURCE_REFERENCE,
                        "scenario": scenario,
                        "source_pins": SOURCE_PINS,
                        "upstream_pins": {
                            s: {
                                k: v[k]
                                for k in ("manifest", "receipt", "database", "review_sha256")
                            }
                            for s, v in UPSTREAM.items()
                        },
                        "qualification": "FUTURE_FICTIONAL_NO_AUDIT_CREDIT",
                    },
                )
                if ref["sha256"] != item["sha256"]:
                    raise CompanyStoreError("Processing-purpose native serialization differs")
                records[scenario].append(ref)
        receipt = {
            "schema": SCHEMA,
            "company": COMPANY,
            "branches": BRANCHES,
            "records": records,
            "source_pins": SOURCE_PINS,
            "upstream_pins": {
                s: {k: v[k] for k in ("manifest", "receipt", "database", "review_sha256")}
                for s, v in UPSTREAM.items()
            },
            "selected_marker_count_per_branch": 1,
            "purpose_request_count_per_branch": 1,
            "approved_execution_count_per_branch": {"CLEAN": 0, "MESSY": 0},
            "refused_request_count_per_branch": {"CLEAN": 0, "MESSY": 1},
            "pending_request_count_per_branch": {"CLEAN": 1, "MESSY": 0},
            "open_purpose_exception_ids": {"CLEAN": [], "MESSY": [EXCEPTION_ID]},
            "actual_operation_eligibility_as_of_2026_09_29": False,
            "audit_task_credit": False,
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": 8,
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return manifest


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = _private(destination, directory=True)
    paths = {
        "manifest": root / "MANIFEST.json",
        "receipt": root / "RECEIPT.json",
        "database": root / "company.sqlite3",
    }
    before = _frozen(paths)
    manifest = json.loads(paths["manifest"].read_text())
    receipt = json.loads(paths["receipt"].read_text())
    context = _input_context(repository, private_repository)
    upstream_pins = {
        s: {k: v[k] for k in ("manifest", "receipt", "database", "review_sha256")}
        for s, v in UPSTREAM.items()
    }
    if (
        manifest.get("schema") != SCHEMA + "_MANIFEST"
        or manifest.get("receipt_sha256") != before["receipt"][-1]
        or manifest.get("company_db_sha256") != before["database"][-1]
        or manifest.get("module_sha256") != _digest(Path(__file__))
        or manifest.get("native_version_count") != 8
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != SCHEMA
        or receipt.get("company") != COMPANY
        or receipt.get("branches") != BRANCHES
        or receipt.get("source_pins") != SOURCE_PINS
        or receipt.get("upstream_pins") != upstream_pins
        or receipt.get("selected_marker_count_per_branch") != 1
        or receipt.get("purpose_request_count_per_branch") != 1
        or receipt.get("approved_execution_count_per_branch") != {"CLEAN": 0, "MESSY": 0}
        or receipt.get("refused_request_count_per_branch") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("pending_request_count_per_branch") != {"CLEAN": 1, "MESSY": 0}
        or receipt.get("open_purpose_exception_ids") != {"CLEAN": [], "MESSY": [EXCEPTION_ID]}
        or receipt.get("actual_operation_eligibility_as_of_2026_09_29") is not False
        or receipt.get("audit_task_credit") is not False
        or receipt.get("limits") != LIMITS
        or set(receipt.get("records", {})) != set(BRANCHES)
    ):
        raise CompanyStoreError("Processing-purpose manifest/receipt scope differs")
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Processing-purpose database integrity failed")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 8 or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("Processing-purpose source count/audit access differs")
        if {tuple(r) for r in db.execute("SELECT company,branch,system,owner FROM systems")} != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("Processing-purpose source custody differs")
        for scenario, branch in BRANCHES.items():
            expected = _expected_rows(context, scenario)
            refs = receipt["records"][scenario]
            provenance = {
                "source_reference": SOURCE_REFERENCE,
                "scenario": scenario,
                "source_pins": SOURCE_PINS,
                "upstream_pins": upstream_pins,
                "qualification": "FUTURE_FICTIONAL_NO_AUDIT_CREDIT",
            }
            if len(refs) != 4:
                raise CompanyStoreError("Processing-purpose branch incomplete")
            for ref, item in zip(refs, expected, strict=True):
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (COMPANY, branch, item["system"], item["record"]),
                ).fetchone()
                if (
                    row is None
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
                    or ref["company"] != COMPANY
                    or ref["branch"] != branch
                    or ref["imported_at"] != row["imported_at"]
                    or ref["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["provenance"] != provenance
                    or row["origin"] != ref["origin"]
                    or json.loads(row["provenance"]) != provenance
                    or row["sha256"] != item["sha256"]
                    or row["content"] != encoded(item["body"])
                    or row["event_at"] != item["event_at"]
                    or row["available_at"] != item["available_at"]
                    or row["available_at"] < row["event_at"]
                    or datetime.fromisoformat(row["imported_at"])
                    >= datetime.fromisoformat(row["event_at"])
                ):
                    raise CompanyStoreError("Processing-purpose native tuple differs")
    if _frozen(paths) != before:
        raise CompanyStoreError("Processing-purpose source changed during verification")
    return manifest
