"""Selected fictional contract terms and owner triage, without legal acceptance."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from pathlib import Path

from . import company_phi_ba_2027_simulation as phi_source
from . import company_provider_lifecycle_2027_simulation as provider_source
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_SELECTED_CONTRACT_OBLIGATION_TRIAGE_V1"
COMPANY = phi_source.COMPANY
AS_OF = "2026-09-29"
OWNER = "AS-P014"
LEGAL = "AS-P003"
RECORD = "OBL-SELECTED-BA-PROVIDER-2027"
QUALIFICATION = "FUTURE_LOCAL_TERM_ENUMERATION_NO_PROVISION_LEVEL_LEGAL_ACCEPTANCE"
PHI = "enterprise/generated/audit-suite/company-phi-ba-2027-simulation-2026-09-29/run-v1"
PHI_REVIEW = (
    "enterprise/generated/audit-suite/company-phi-ba-2027-simulation-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
PROVIDER = "enterprise/generated/audit-suite/company-provider-lifecycle-2026-09-29/run-v2"
PROVIDER_REVIEW = (
    "enterprise/generated/audit-suite/company-provider-lifecycle-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
TRANSITION = "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3"
ROUTE_MAP = "enterprise/audit_suite/provider_ba_85_candidate_routes_v2.json"
ROUTE_REVIEW = (
    "enterprise/generated/audit-suite/provider-ba-85-route-v2-independent-review-2026-09-29/"
    "REVIEW.json"
)
CONTRACT_SPEC = "enterprise/audit_suite/phi_ba_2027_contract_spec_v1.json"
PRIVATE_PINS = {
    f"{PHI}/MANIFEST.json": "8226ac2031cafe581289afb4c25088c8dfe603e75ac11fc1ababfe2590f2a5f2",
    f"{PHI}/RECEIPT.json": "20e3762aabb45fcfa3107d695da37e7eeb677f6c5e98f1bb767fa463fe857d9d",
    f"{PHI}/company.sqlite3": "ad252e8cb6b1309b238fbe50daac541d67b5fa89051a0b3d8eab7993d4010449",
    PHI_REVIEW: "39bb9b071179ed672c5cf07c2867285d36b2f3e8cdce2106dc4472d17047911e",
    f"{PROVIDER}/MANIFEST.json": "e8a91c7cd2a426acf78155ffe6dc644048280e592c92ff5e3f63d7b46185f851",
    f"{PROVIDER}/RECEIPT.json": "ab530dfffb00574fe446b20b07bb80bcf89f5fbdc23d61a676ac0a4e4cce6025",
    f"{PROVIDER}/company.sqlite3": (
        "b92da45fc00db915cf24bef166c5a092cd6ca5bcc33887998e6b6b414e4e0d0f"
    ),
    PROVIDER_REVIEW: "bde642fd35fd4412bda49867b4d7961289bc97deae216bb56e325a19f371b634",
    ROUTE_REVIEW: "5f74853e540dc819b2fb5313fa9a62a4a984581217ca04027a3d72eda8df0883",
}
TRACKED = (
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md",
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md",
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
    ROUTE_MAP,
    CONTRACT_SPEC,
    "enterprise/audit_suite/CONTRACT_OBLIGATION_TRIAGE_2027_PROPOSAL.md",
    "enterprise/audit_suite/company_contract_obligation_triage.py",
)
CANON_PINS = {
    TRACKED[0]: "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496",
    TRACKED[1]: "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751",
    TRACKED[2]: "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433",
    ROUTE_MAP: "7f4373f0b50d17a0e1b9d0e358cfb2f55b149068d5699916296cb35acea2bea8",
    CONTRACT_SPEC: "557cd3ddf09195207de93be2441710f38be9aa8693de729c07d8cf45e45a081f",
}
SOURCE_REF = "enterprise/audit_suite/company_contract_obligation_triage.py"
SYSTEMS = ("selected_term_inventory", "owner_candidate_triage")
CONTRACTS = ("BAA-CUST-01", "BAA-SUB-01")
CALENDARS = ("CAL-RENO", "CAL-BOISE", "CAL-SUPPORT")
TERM_COUNTS = {"BAA-CUST-01": 8, "BAA-SUB-01": 8, "CAL-RENO": 5, "CAL-BOISE": 5, "CAL-SUPPORT": 8}
LIMITS = [
    "34 term occurrences in five exact selected synthetic source records, not all "
    "contracts or laws.",
    "AS-P014 attests bounded term enumeration and provisional service mapping only.",
    "AS-P003 qualified provision-level legal applicability/acceptance remains pending.",
    "No supplier assurance requested or received; Messy provider omission remains open.",
    "No real agreement, actual PHI/BA status, outside performance, audit collection "
    "or task credit.",
]


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
        raise CompanyStoreError("Ordinary private contract source required")


def _frozen(path: Path) -> tuple:
    _private(path)
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen contract source has active sidecar")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise CompanyStoreError("Frozen contract source must be regular")
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        _digest(path),
    )


def _native(
    private_repository: Path,
    relative: str,
    receipt: dict,
    scenario: str,
    system: str,
    record: str,
    version: int = 1,
) -> tuple[dict, dict]:
    path = private_repository / relative / "company.sqlite3"
    before = _frozen(path)
    refs = [
        ref
        for ref in receipt["records"][scenario]
        if ref["system"] == system and ref["record"] == record and ref["version"] == version
    ]
    if len(refs) != 1:
        raise CompanyStoreError("Selected contract original missing or duplicated")
    ref = refs[0]
    route = tuple(ref[k] for k in ("company", "branch", "system", "record", "version"))
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Selected contract DB integrity failure")
        row = db.execute(
            "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
            "AND record=? AND version=?",
            route,
        ).fetchone()
        if row is None or row["sha256"] != ref["sha256"] or sha(row["content"]) != ref["sha256"]:
            raise CompanyStoreError("Selected contract original bytes differ")
        body = json.loads(row["content"])
        if (
            body["scenario"] != scenario
            or body["audit_task_credit"] is not False
            or body["actual_legal_applicability"] != "UNDETERMINED"
        ):
            raise CompanyStoreError("Selected contract source qualification differs")
    if _frozen(path) != before:
        raise CompanyStoreError("Selected contract original changed during read")
    return (
        {
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
                "imported_at",
            )
        },
        body,
    )


def _routes(route_map: dict) -> dict:
    if route_map["counts"]["controls_per_side"]["SH-LEG-001"] != 72:
        raise CompanyStoreError("Reviewed LEG001 route count differs")
    output = {}
    for side in "AB":
        matches = [
            r for r in route_map["routes"] if r["side"] == side and r["control_id"] == "SH-LEG-001"
        ]
        if len(matches) != 72 or len({r["task_id"] for r in matches}) != 72:
            raise CompanyStoreError("Exact 72 LEG001 route IDs differ")
        rows = []
        for route in matches:
            touch = route["candidate_touch"]
            if touch == "SCENARIO_CONTRACT_OBLIGATION_SUBSET":
                class_ = "TERM_LEVEL_CANDIDATE_CONTEXT_ONLY"
            elif touch == "SCENARIO_ROLE_CONTEXT_ONLY":
                class_ = "ROLE_CONTEXT_ONLY_NOT_TERM_LEVEL"
            elif touch == "NO_DIRECT_SOURCE":
                class_ = "UNSUPPORTED_NO_DIRECT_SOURCE"
            else:
                raise CompanyStoreError("Unexpected reviewed LEG001 route classification")
            if (
                route["current_status"] != "NOT_STARTED"
                or route["current_conclusion"] != "NOT_RUN"
                or route["task_credit"] is not False
                or route["actual_operation_eligibility_as_of_packet"] is not False
            ):
                raise CompanyStoreError("LEG001 route/task state differs")
            rows.append(
                {
                    key: route[key]
                    for key in (
                        "task_id",
                        "authored_title",
                        "authored_test_clause",
                        "requirement_ids",
                        "screen_row_sha256",
                        "exact_clause_limit",
                        "current_status",
                        "current_conclusion",
                        "task_credit",
                    )
                }
                | {"term_inventory_context": class_}
            )
        counts = {
            kind: sum(r["term_inventory_context"] == kind for r in rows)
            for kind in (
                "TERM_LEVEL_CANDIDATE_CONTEXT_ONLY",
                "ROLE_CONTEXT_ONLY_NOT_TERM_LEVEL",
                "UNSUPPORTED_NO_DIRECT_SOURCE",
            )
        }
        if counts != {
            "TERM_LEVEL_CANDIDATE_CONTEXT_ONLY": 3,
            "ROLE_CONTEXT_ONLY_NOT_TERM_LEVEL": 3,
            "UNSUPPORTED_NO_DIRECT_SOURCE": 66,
        }:
            raise CompanyStoreError("Reviewed LEG001 3/3/66 boundary differs")
        output[side] = {"routes": rows, "counts": counts}
    return output


def _context(repository: Path, private_repository: Path) -> tuple[dict, dict, dict]:
    pins = {}
    for name in TRACKED:
        path = repository / name
        if not path.is_file() or path.is_symlink():
            raise CompanyStoreError("Tracked selected contract source missing or linked")
        pins[f"repo://{name}"] = _digest(path)
    if any(pins[f"repo://{name}"] != digest for name, digest in CANON_PINS.items()):
        raise CompanyStoreError("Selected contract canon/route/spec differs")
    appointments = (repository / TRACKED[1]).read_text()
    if (
        "| AS-P003 | Helena Ward | General Counsel |" not in appointments
        or "| AS-P014 | Omar Vale | Data Governance and Records Lead |" not in appointments
    ):
        raise CompanyStoreError("Selected counsel/owner projection differs")
    for name, digest in PRIVATE_PINS.items():
        path = private_repository / name
        _private(path)
        if _digest(path) != digest:
            raise CompanyStoreError(f"Reviewed private contract source differs: {name}")
        pins[f"private://{name}"] = digest
    for review in (PHI_REVIEW, PROVIDER_REVIEW):
        if json.loads((private_repository / review).read_text()).get("verdict") != (
            "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW"
        ):
            raise CompanyStoreError("Selected contract source lacks independent review")
    if json.loads((private_repository / ROUTE_REVIEW).read_text()).get("verdict") != (
        "PASS_READ_ONLY_CANDIDATE_MAP"
    ):
        raise CompanyStoreError("Provider/BA route map lacks independent review")
    transition = private_repository / TRANSITION
    phi_root = private_repository / PHI
    provider_root = private_repository / PROVIDER
    phi_source.verify(phi_root, transition_root=transition, repository=repository)
    provider_source.verify(
        provider_root, repository=repository, transition_root=transition, phi_root=phi_root
    )
    phi_receipt = json.loads((phi_root / "RECEIPT.json").read_text())
    provider_receipt = json.loads((provider_root / "RECEIPT.json").read_text())
    spec = json.loads((repository / CONTRACT_SPEC).read_text())
    if (
        spec["truth_class"] != "TRAINING_SCENARIO_ONLY"
        or spec["terms_status"] != "STRUCTURED_SYNTHETIC_TERMS_NO_REAL_COUNTERPARTY_TEXT"
        or spec["fictional_2027_boundary"]["actual_hipaa_applicability"] != "UNDETERMINED"
    ):
        raise CompanyStoreError("Synthetic contract specification boundary differs")
    selected = {}
    for scenario in ("CLEAN", "MESSY"):
        terms, source_refs = [], {}
        for record in CONTRACTS:
            ref, body = _native(
                private_repository, PHI, phi_receipt, scenario, "contract_register", record
            )
            contract_id = "SIM-" + record
            if (
                body["contract_id"] != contract_id
                or body["contract_executed_in_simulation"] is not True
                or body["real_signature_or_agreement"] is not False
                or body["contract_spec_sha256"] != CANON_PINS[CONTRACT_SPEC]
                or body["synthetic_terms"] != spec["synthetic_terms"][contract_id]
                or len(body["synthetic_terms"]) != TERM_COUNTS[record]
            ):
                raise CompanyStoreError("Reviewed simulated BAA term population differs")
            source_refs[record] = ref
            for term in body["synthetic_terms"]:
                terms.append(
                    {
                        "occurrence_id": record + ":" + term["clause_candidate_id"],
                        "source_kind": "SIMULATED_BAA_TERM",
                        "source_ref": ref,
                        "term_id": term["clause_candidate_id"],
                        "term_value": term["scenario_obligation"],
                        "term_sha256": sha(encoded(term)),
                        "preliminary_service_mapping": "SELECTED_SYNTHETIC_BA_SERVICE_CANDIDATE",
                    }
                )
        for record in CALENDARS:
            ref, body = _native(
                private_repository,
                PROVIDER,
                provider_receipt,
                scenario,
                "obligation_calendar",
                record,
            )
            if (
                len(body["obligations"]) != TERM_COUNTS[record]
                or body["external_assurance_status"] != "NOT_REQUESTED_NOT_RECEIVED"
                or body["external_request_sent"] is not False
                or body["external_response_received"] is not False
                or body["real_world_provider_operation"] is not False
            ):
                raise CompanyStoreError("Reviewed provider calendar/assurance scope differs")
            source_refs[record] = ref
            for term in body["obligations"]:
                terms.append(
                    {
                        "occurrence_id": record + ":" + term["id"],
                        "source_kind": "INTERNAL_PROVIDER_CALENDAR_TERM",
                        "source_ref": ref,
                        "term_id": term["id"],
                        "term_value": term["source_obligation"],
                        "term_sha256": sha(encoded(term)),
                        "preliminary_service_mapping": (
                            "PROVIDER_EPHI_NOT_AUTHORIZED_BY_SITE_CONTRACT"
                            if term["id"] == "ephi_processing"
                            and term["source_obligation"] == "NOT_AUTHORIZED_BY_THIS_CONTRACT"
                            else "SELECTED_SYNTHETIC_PROVIDER_SERVICE_CANDIDATE"
                        ),
                    }
                )
        if len(terms) != 34 or len({term["occurrence_id"] for term in terms}) != 34:
            raise CompanyStoreError("Selected 34 term occurrences differ")
        exception = None
        if scenario == "MESSY":
            if provider_receipt["open_exception_ids"][scenario] != [
                "EXC-SIM-PROVIDER-SUPPORT-OMISSION-01"
            ]:
                raise CompanyStoreError("Messy support omission no longer open")
            exception, body = _native(
                private_repository,
                PROVIDER,
                provider_receipt,
                scenario,
                "exception_register",
                "EXC-SUPPORT-OMISSION",
                version=2,
            )
            if (
                body["status"] != "OPEN"
                or body["historical_omission_not_retroactively_cured"] is not True
            ):
                raise CompanyStoreError("Messy provider omission history differs")
        elif provider_receipt["open_exception_ids"][scenario] != []:
            raise CompanyStoreError("Clean provider exception population differs")
        selected[scenario] = {
            "source_refs": source_refs,
            "term_occurrences": terms,
            "open_provider_exception_ref": exception,
        }
    route_map = json.loads((repository / ROUTE_MAP).read_text())
    return pins, selected, _routes(route_map)


def _steps(scenario: str) -> tuple[tuple[str, str, str], ...]:
    date = "2027-10-22" if scenario == "CLEAN" else "2027-10-24"
    return (
        (
            "selected_term_inventory",
            f"{date}T10:00:00+00:00",
            "SELECTED_34_TERM_OCCURRENCES_ENUMERATED",
        ),
        (
            "owner_candidate_triage",
            f"{date}T11:00:00+00:00",
            "BOUNDED_OWNER_ATTESTATION_LEGAL_PENDING",
        ),
    )


def _body(scenario: str, step: tuple[str, str, str], selected: dict, previous: dict | None) -> dict:
    system, at, status = step
    terms = selected["term_occurrences"]
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "system": system,
        "record": RECORD,
        "status": status,
        "event_at": _time(at),
        "available_at": _time(at),
        "actor_person_id": OWNER,
        "actor_attestation_scope": "SELECTED_FIVE_SOURCE_RECORDS_34_TERM_OCCURRENCES_ONLY",
        "legal_reviewer_person_id_pending": LEGAL,
        "source_refs": selected["source_refs"],
        "term_occurrences": terms,
        "term_occurrence_count": 34,
        "owner_attests_selected_source_enumeration": system == "owner_candidate_triage",
        "owner_attests_preliminary_service_mapping": system == "owner_candidate_triage",
        "qualified_counsel_provision_review": "PENDING",
        "statutory_applicability_decided": False,
        "actual_hipaa_applicability": "UNDETERMINED",
        "real_world_ba_status": "UNDETERMINED",
        "supplier_attestation": "NOT_REQUESTED_NOT_RECEIVED",
        "new_contract_executed": False,
        "existing_upstream_simulated_terms_only": True,
        "open_provider_exception_ref": selected["open_provider_exception_ref"],
        "provider_support_omission_open": scenario == "MESSY",
        "previous_local_sha256": previous["sha256"] if previous else None,
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
        raise CompanyStoreError("New private contract triage destination required")
    pins, selected, routes = _context(Path(repository), Path(private_repository))
    branches = {"CLEAN": "OBL-CLEAN", "MESSY": "OBL-MESSY"}
    with tempfile.TemporaryDirectory(prefix=".obligation-stage-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in branches.items():
            for system in SYSTEMS:
                store.register_system(COMPANY, branch, system, OWNER)
            records[scenario], previous = [], None
            for step in _steps(scenario):
                source_refs = list(selected[scenario]["source_refs"].values())
                exception = selected[scenario]["open_provider_exception_ref"]
                if exception is not None:
                    source_refs.append(exception)
                if any(ref["available_at"] >= _time(step[1]) for ref in source_refs):
                    raise CompanyStoreError("Contract triage predates selected source")
                body = _body(scenario, step, selected[scenario], previous)
                ref = store.append_version(
                    COMPANY,
                    branch,
                    step[0],
                    RECORD,
                    expected_version=0,
                    command_id=f"OB-{branch}-{step[0]}",
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
            "status": "FUTURE_FICTIONAL_SELECTED_TERMS_LEGAL_PENDING_NO_CREDIT",
            "as_of": AS_OF,
            "company": COMPANY,
            "branches": branches,
            "source_pins": pins,
            "selected_source_terms": selected,
            "separate_read_only_72_route_disposition": routes,
            "records": records,
            "selected_denominators": {"CLEAN": 34, "MESSY": 34},
            "authority_gate": "OWNER_ENUMERATION_ONLY_QUALIFIED_COUNSEL_PENDING",
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": 4,
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
        != {"MANIFEST.json", "RECEIPT.json", "company.sqlite3"}
    ):
        raise CompanyStoreError("Private ordinary three-file contract source required")
    for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3"):
        _private(root / name)
    manifest = json.loads((root / "MANIFEST.json").read_text())
    receipt = json.loads((root / "RECEIPT.json").read_text())
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _digest(root / "RECEIPT.json"),
        "company_db_sha256": _digest(root / "company.sqlite3"),
        "module_sha256": _digest(Path(__file__)),
        "native_version_count": 4,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Contract triage manifest differs")
    pins, selected, routes = _context(Path(repository), Path(private_repository))
    if (
        receipt["schema"] != SCHEMA
        or receipt["status"] != "FUTURE_FICTIONAL_SELECTED_TERMS_LEGAL_PENDING_NO_CREDIT"
        or receipt["as_of"] != AS_OF
        or receipt["company"] != COMPANY
        or receipt["branches"] != {"CLEAN": "OBL-CLEAN", "MESSY": "OBL-MESSY"}
        or receipt["source_pins"] != pins
        or receipt["selected_source_terms"] != selected
        or receipt["separate_read_only_72_route_disposition"] != routes
        or receipt["selected_denominators"] != {"CLEAN": 34, "MESSY": 34}
        or receipt["authority_gate"] != "OWNER_ENUMERATION_ONLY_QUALIFIED_COUNSEL_PENDING"
        or receipt["limits"] != LIMITS
        or set(receipt["records"]) != {"CLEAN", "MESSY"}
    ):
        raise CompanyStoreError("Contract triage receipt scope differs")
    with closing(
        sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Contract triage DB integrity failure")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != count
            for table, count in (
                ("versions", 4),
                ("systems", 4),
                ("grants", 0),
                ("collections", 0),
                ("access_events", 0),
            )
        ):
            raise CompanyStoreError("Contract triage native population/access differs")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, OWNER)
            for branch in receipt["branches"].values()
            for system in SYSTEMS
        }:
            raise CompanyStoreError("Contract triage native custody differs")
        for scenario, branch in receipt["branches"].items():
            steps, refs, previous = _steps(scenario), receipt["records"][scenario], None
            if len(refs) != len(steps):
                raise CompanyStoreError("Contract triage event denominator differs")
            for step, ref in zip(steps, refs, strict=True):
                system, at, _ = step
                route = (COMPANY, branch, system, RECORD, 1)
                if (
                    tuple(ref[k] for k in ("company", "branch", "system", "record", "version"))
                    != route
                ):
                    raise CompanyStoreError("Contract triage native route differs")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    route,
                ).fetchone()
                if (
                    row is None
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or row["command_id"] != f"OB-{branch}-{system}"
                    or any(row[k] != ref[k] for k in ("event_at", "available_at", "imported_at"))
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["origin"] != row["origin"]
                ):
                    raise CompanyStoreError("Contract triage native identity differs")
                provenance = {
                    "source_reference": SOURCE_REF,
                    "source_pins": pins,
                    "scenario": scenario,
                    "qualification": QUALIFICATION,
                }
                if json.loads(row["provenance"]) != provenance or ref["provenance"] != provenance:
                    raise CompanyStoreError("Contract triage provenance differs")
                selected_refs = list(selected[scenario]["source_refs"].values())
                exception = selected[scenario]["open_provider_exception_ref"]
                if exception is not None:
                    selected_refs.append(exception)
                if any(item["available_at"] >= _time(at) for item in selected_refs):
                    raise CompanyStoreError("Contract triage predates source availability")
                expected = _body(scenario, step, selected[scenario], previous)
                if (
                    json.loads(row["content"]) != expected
                    or row["event_at"] != expected["event_at"]
                    or row["available_at"] != expected["available_at"]
                    or row["imported_at"] >= row["event_at"]
                ):
                    raise CompanyStoreError("Contract triage content or future clock differs")
                previous = ref
    return manifest
