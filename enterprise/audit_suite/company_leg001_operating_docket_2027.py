"""Bounded fictional LEG001 counsel docket over one reviewed synthetic chain."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from pathlib import Path

from . import company_contract_obligation_triage as triage
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_LEG001_SELECTED_OPERATING_DOCKET_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
SOURCE = "enterprise/audit_suite/company_leg001_operating_docket_2027.py"
SPEC = "enterprise/audit_suite/leg001_operating_docket_spec_v1.json"
SPEC_SHA256 = "c780754e55788c54edb62cf140e921319e723afaeb9bb2d95837d93b9c34da5a"
PROPOSAL = "enterprise/audit_suite/LEG001_SELECTED_OPERATING_DOCKET_2027_PROPOSAL.md"
APPOINTMENTS = "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md"
APPOINTMENTS_SHA256 = "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
ROUTE_MAP = triage.ROUTE_MAP
ROUTE_SHA256 = "7f4373f0b50d17a0e1b9d0e358cfb2f55b149068d5699916296cb35acea2bea8"
TRIAGE_RUN = "enterprise/generated/audit-suite/company-contract-obligation-triage-2026-09-29/run-v1"
TRIAGE_REVIEW = (
    "enterprise/generated/audit-suite/company-contract-obligation-triage-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
PRIVATE_PINS = {
    TRIAGE_REVIEW: "ae4d988c15edec4ecba009244535ad53827b53e681aa82527dbe9a02e2ea970c",
    f"{TRIAGE_RUN}/MANIFEST.json": "0cc28e7b939bd3e725482c817a9b9551164355cb5e5b5171b1ff21663424e7fd",  # noqa: E501
    f"{TRIAGE_RUN}/RECEIPT.json": "9e413b4f14912ad2034e8b4df7b0cf250378c2b4958238277222cd35d7b30d7e",  # noqa: E501
    f"{TRIAGE_RUN}/company.sqlite3": "8528778b155989f937978a33018496b4fa8cd69de725a8189982532564ae95e5",  # noqa: E501
    triage.PHI_REVIEW: "39bb9b071179ed672c5cf07c2867285d36b2f3e8cdce2106dc4472d17047911e",
    f"{triage.PHI}/RECEIPT.json": "20e3762aabb45fcfa3107d695da37e7eeb677f6c5e98f1bb767fa463fe857d9d",  # noqa: E501
    f"{triage.PHI}/company.sqlite3": "ad252e8cb6b1309b238fbe50daac541d67b5fa89051a0b3d8eab7993d4010449",  # noqa: E501
    triage.PROVIDER_REVIEW: "bde642fd35fd4412bda49867b4d7961289bc97deae216bb56e325a19f371b634",
    f"{triage.PROVIDER}/RECEIPT.json": "ab530dfffb00574fe446b20b07bb80bcf89f5fbdc23d61a676ac0a4e4cce6025",  # noqa: E501
    f"{triage.PROVIDER}/company.sqlite3": "b92da45fc00db915cf24bef166c5a092cd6ca5bcc33887998e6b6b414e4e0d0f",  # noqa: E501
}
SYSTEMS = (
    "scope_decision",
    "provision_status",
    "term_status",
    "matter_watch",
    "change_watch",
    "reconciliation",
)
PROVISION_IDS = (
    "45-CFR-160.102",
    "45-CFR-160.103",
    "45-CFR-164.502(e)",
    "45-CFR-164.504(e)",
    "45-CFR-164.314(a)",
    "45-CFR-164.410",
    "45-CFR-160.306",
    "45-CFR-160.504",
)
TERM_IDS = {
    "permitted_uses_and_disclosures",
    "safeguards_and_security",
    "incident_and_breach_reporting",
    "subcontractor_flowdown",
    "rights_request_support",
    "regulator_records_access",
    "return_or_destruction_and_continuing_protection",
    "material_breach_cure_and_termination",
    "facility_service",
    "site_incident_notice_hours",
    "security_report_frequency",
    "exit_notice_days",
    "ephi_processing",
}
OPEN_EXCEPTIONS = ["EXC-SIM-BA-FLOWDOWN-01", "EXC-SIM-PROVIDER-SUPPORT-OMISSION-01"]
HISTORICAL_FLOWDOWN_TERMS = {
    "BAA-SUB-01:subcontractor_flowdown",
    "CAL-SUPPORT:subcontractor_flowdown",
}
REFERENCE_FIELDS = (
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
)
LIMITS = [
    "One synthetic customer/service/BA/subcontractor chain and 34 selected term occurrences per branch.",  # noqa: E501
    "AS-P003 decisions are fictional 2027 scenario records; real HIPAA and contract status remain undetermined.",  # noqa: E501
    "The 2026-09-29 official-reference snapshot is not proof of 2027 law or all real matters.",
    "Conditional breach, complaint and hearing paths are intake triggers, not recurring controls or N/A findings.",  # noqa: E501
    "All 66 unsupported authored LEG001 routes per side still need population and audit procedures.",  # noqa: E501
    "No real contracts, PHI, outside messages, legal advice, audit task credit, Atlas or P1 writes.",  # noqa: E501
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pairs(items: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            raise CompanyStoreError("Duplicate JSON field in selected LEG001 source")
        result[key] = value
    return result


def _json(path: Path) -> dict:
    result = json.loads(path.read_bytes(), object_pairs_hook=_pairs)
    if not isinstance(result, dict):
        raise CompanyStoreError("Expected LEG001 JSON object")
    return result


def _private(path: Path, *, directory: bool = False) -> tuple:
    path = path.absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise CompanyStoreError("Private LEG001 path alias forbidden")
    info = path.stat()
    mode = stat.S_IMODE(info.st_mode)
    if directory:
        if not stat.S_ISDIR(info.st_mode) or mode != 0o700:
            raise CompanyStoreError("Private LEG001 0700 directory required")
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or mode != 0o600:
        raise CompanyStoreError("Private LEG001 0600 regular file required")
    return (
        info.st_dev,
        info.st_ino,
        mode,
        info.st_size,
        info.st_mtime_ns,
        None if directory else _sha(path),
    )


def _no_sidecars(path: Path) -> None:
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen LEG001 source has SQLite sidecar")


def _native(path: Path, receipt: dict, scenario: str, selected: dict) -> tuple[dict, dict]:
    """Match every receipt field and content byte for a selected original version."""
    before = _private(path)
    _no_sidecars(path)
    refs = [
        row
        for row in receipt["records"][scenario]
        if all(row[k] == selected[k] for k in ("company", "branch", "system", "record", "version"))
    ]
    if len(refs) != 1:
        raise CompanyStoreError("Selected LEG001 upstream receipt tuple missing or duplicated")
    ref = refs[0]
    if {k: ref[k] for k in selected} != selected:
        raise CompanyStoreError("Selected LEG001 upstream identity/clock differs")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Selected LEG001 upstream SQLite integrity differs")
        rows = db.execute(
            "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
            "AND record=? AND version=?",
            tuple(ref[k] for k in ("company", "branch", "system", "record", "version")),
        ).fetchall()
        if len(rows) != 1:
            raise CompanyStoreError("Selected LEG001 native version missing or duplicated")
        row = rows[0]
        native = {k: json.loads(row[k]) if k == "provenance" else row[k] for k in REFERENCE_FIELDS}
        if native != ref or sha(row["content"]) != ref["sha256"]:
            raise CompanyStoreError("Selected LEG001 full native receipt/content tuple differs")
        body = json.loads(row["content"])
    _no_sidecars(path)
    if _private(path) != before:
        raise CompanyStoreError("Selected LEG001 upstream changed during native read")
    return ref, body


def _context(repository: Path, private_repository: Path) -> dict:
    repo = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    tracked = {APPOINTMENTS: APPOINTMENTS_SHA256, ROUTE_MAP: ROUTE_SHA256, SPEC: SPEC_SHA256}
    for name, digest in tracked.items():
        path = repo / name
        if path.is_symlink() or _sha(path) != digest:
            raise CompanyStoreError(f"Tracked LEG001 canon/spec differs: {name}")
    if "| AS-P003 | Helena Ward | General Counsel |" not in (repo / APPOINTMENTS).read_text():
        raise CompanyStoreError("AS-P003 counsel authority projection differs")
    spec = _json(repo / SPEC)
    if (
        spec.get("schema") != SCHEMA.replace("OPERATING_DOCKET_V1", "OPERATING_DOCKET_SPEC_V1")
        or spec.get("truth_class") != "TRAINING_SCENARIO_ONLY"
        or spec.get("company") != COMPANY
        or spec.get("branches") != {"CLEAN": "LEG-CLEAN", "MESSY": "LEG-MESSY"}
        or spec.get("source_record_ids") != list(triage.CONTRACTS + triage.CALENDARS)
        or spec.get("term_occurrences_per_branch") != 34
        or spec.get("counsel_person_id") != "AS-P003"
        or set(spec.get("owner_by_term_id", {})) != TERM_IDS
        or tuple(row["id"] for row in spec.get("legal_provisions", [])) != PROVISION_IDS
        or any(row["real_status"] != "UNDETERMINED" for row in spec["legal_provisions"])
        or spec.get("real_hipaa_applicability") != "UNDETERMINED"
        or any(
            spec.get(k) is not False
            for k in (
                "actual_personal_data",
                "actual_phi",
                "real_contract_executed",
                "outside_message_sent",
                "audit_task_credit",
                "source_complete",
            )
        )
    ):
        raise CompanyStoreError("LEG001 selected legal spec/claim boundary differs")
    states = {}
    for name, digest in PRIVATE_PINS.items():
        path = private / name
        state = _private(path)
        if state[-1] != digest:
            raise CompanyStoreError(f"Reviewed LEG001 private source differs: {name}")
        if path.name == "company.sqlite3":
            _no_sidecars(path)
        states[path] = state
    review = _json(private / TRIAGE_REVIEW)
    if review.get(
        "verdict"
    ) != "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW" or review.get("run_sha256") != {
        "MANIFEST.json": PRIVATE_PINS[f"{TRIAGE_RUN}/MANIFEST.json"],
        "RECEIPT.json": PRIVATE_PINS[f"{TRIAGE_RUN}/RECEIPT.json"],
        "company.sqlite3": PRIVATE_PINS[f"{TRIAGE_RUN}/company.sqlite3"],
    }:
        raise CompanyStoreError("Selected LEG001 triage independent review differs")
    triage_root = private / TRIAGE_RUN
    triage.verify(triage_root, repository=repo, private_repository=private)
    triage_receipt = _json(triage_root / "RECEIPT.json")
    _, selected, routes = triage._context(repo, private)
    if (
        triage_receipt.get("selected_source_terms") != selected
        or triage_receipt.get("separate_read_only_72_route_disposition") != routes
        or triage_receipt.get("authority_gate")
        != "OWNER_ENUMERATION_ONLY_QUALIFIED_COUNSEL_PENDING"
    ):
        raise CompanyStoreError("LEG001 predecessor term/route scope differs")
    phi_receipt = _json(private / triage.PHI / "RECEIPT.json")
    provider_receipt = _json(private / triage.PROVIDER / "RECEIPT.json")
    source_refs = {}
    exceptions = {}
    for scenario in ("CLEAN", "MESSY"):
        terms = selected[scenario]
        if len(terms["term_occurrences"]) != 34 or len(terms["source_refs"]) != 5:
            raise CompanyStoreError("LEG001 selected five-record/34-occurrence denominator differs")
        native_refs = {}
        for record, short_ref in terms["source_refs"].items():
            if record in triage.CONTRACTS:
                db, upstream = private / triage.PHI / "company.sqlite3", phi_receipt
            else:
                db, upstream = private / triage.PROVIDER / "company.sqlite3", provider_receipt
            full, _ = _native(db, upstream, scenario, short_ref)
            native_refs[record] = full
        for occurrence in terms["term_occurrences"]:
            if (
                occurrence["source_ref"]
                != terms["source_refs"][occurrence["occurrence_id"].split(":")[0]]
            ):
                raise CompanyStoreError("LEG001 selected term occurrence/source reference differs")
        source_refs[scenario] = native_refs
        triage_refs = triage_receipt["records"][scenario]
        if len(triage_refs) != 2:
            raise CompanyStoreError("LEG001 predecessor native docket denominator differs")
        for ref in triage_refs:
            _native(triage_root / "company.sqlite3", triage_receipt, scenario, ref)
        if scenario == "MESSY":
            phi_ref = next(
                ref
                for ref in phi_receipt["records"][scenario]
                if (ref["system"], ref["record"]) == ("exception_register", "EXC-01")
            )
            _, phi_body = _native(
                private / triage.PHI / "company.sqlite3", phi_receipt, scenario, phi_ref
            )
            provider_refs = [
                ref
                for ref in provider_receipt["records"][scenario]
                if (ref["system"], ref["record"]) == ("exception_register", "EXC-SUPPORT-OMISSION")
            ]
            if len(provider_refs) != 2 or phi_body.get("action") != "LATE_FLOWDOWN_DETECTION":
                raise CompanyStoreError("LEG001 Messy BA/provider exception history differs")
            provider_history = []
            for ref in sorted(provider_refs, key=lambda row: row["version"]):
                full, body = _native(
                    private / triage.PROVIDER / "company.sqlite3", provider_receipt, scenario, ref
                )
                provider_history.append((full, body))
            if (
                phi_receipt["open_exception_ids"][scenario] != [OPEN_EXCEPTIONS[0]]
                or provider_receipt["open_exception_ids"][scenario] != [OPEN_EXCEPTIONS[1]]
                or provider_history[0][1]["status"] != "OPEN"
                or provider_history[1][1]["status"] != "OPEN"
                or provider_history[1][1]["historical_omission_not_retroactively_cured"] is not True
                or terms["open_provider_exception_ref"]
                != {k: provider_history[1][0][k] for k in terms["open_provider_exception_ref"]}
            ):
                raise CompanyStoreError("LEG001 Messy support correction/open exception differs")
            exceptions[scenario] = {
                "ba_flowdown": phi_ref,
                "provider_support_initial": provider_history[0][0],
                "provider_support_current": provider_history[1][0],
            }
        else:
            if (
                phi_receipt["open_exception_ids"][scenario]
                or provider_receipt["open_exception_ids"][scenario]
                or terms["open_provider_exception_ref"] is not None
            ):
                raise CompanyStoreError("LEG001 Clean selected exception scope differs")
            exceptions[scenario] = {}
        if routes["A" if scenario == "CLEAN" else "B"]["counts"] != {
            "TERM_LEVEL_CANDIDATE_CONTEXT_ONLY": 3,
            "ROLE_CONTEXT_ONLY_NOT_TERM_LEVEL": 3,
            "UNSUPPORTED_NO_DIRECT_SOURCE": 66,
        }:
            raise CompanyStoreError("LEG001 authored 3/3/66 route boundary differs")
    if any(_private(path) != state for path, state in states.items()):
        raise CompanyStoreError("LEG001 reviewed source changed during context read")
    return {
        "spec": spec,
        "pins": {"repo://" + key: value for key, value in tracked.items()}
        | {"private://" + key: value for key, value in PRIVATE_PINS.items()},
        "selected": selected,
        "routes": routes,
        "source_refs": source_refs,
        "triage_refs": triage_receipt["records"],
        "exception_refs": exceptions,
        "source_states": states,
    }


def _term_provisions(occurrence: dict) -> list[str]:
    if occurrence["source_kind"] == "INTERNAL_PROVIDER_CALENDAR_TERM":
        return []
    term = occurrence["term_id"]
    if term == "safeguards_and_security":
        return ["45-CFR-164.504(e)", "45-CFR-164.314(a)"]
    if term == "subcontractor_flowdown":
        return ["45-CFR-164.502(e)", "45-CFR-164.504(e)"]
    if term == "incident_and_breach_reporting":
        return ["45-CFR-164.504(e)", "45-CFR-164.410"]
    return ["45-CFR-164.504(e)"]


def _steps(context: dict, scenario: str) -> list[tuple[str, str, str, dict]]:
    spec = context["spec"]
    selected = context["selected"][scenario]
    side = "A" if scenario == "CLEAN" else "B"
    day = "2027-10-25" if scenario == "CLEAN" else "2027-10-26"
    open_ids = [] if scenario == "CLEAN" else OPEN_EXCEPTIONS
    base = {
        "schema": SCHEMA,
        "scenario": scenario,
        "truth_class": "TRAINING_SCENARIO_ONLY",
        "counsel_person_id": "AS-P003",
        "real_hipaa_applicability": "UNDETERMINED",
        "real_world_ba_status": "UNDETERMINED",
        "actual_phi": False,
        "real_contract_executed": False,
        "outside_message_sent": False,
        "audit_task_credit": False,
        "source_complete": False,
    }
    steps = []

    def add(system: str, record: str, at: str, detail: dict) -> None:
        body = base | {
            "system": system,
            "record": record,
            "event_at": _time(at),
            "available_at": _time(at),
            "detail": detail,
        }
        steps.append((system, record, at, body))

    route_rows = context["routes"][side]["routes"]
    unsupported = [
        row["task_id"]
        for row in route_rows
        if row["term_inventory_context"] == "UNSUPPORTED_NO_DIRECT_SOURCE"
    ]
    add(
        "scope_decision",
        "LEG001-SCOPE-01",
        day + "T10:00:00+00:00",
        {
            "chain": spec["selected_chain"],
            "counsel_decision": "TRAINING_CHAIN_ONLY_REAL_STATUS_UNDETERMINED",
            "source_records": context["source_refs"][scenario],
            "predecessor_triage_refs": context["triage_refs"][scenario],
            "selected_occurrences": 34,
            "unsupported_authored_task_ids": unsupported,
            "unsupported_authored_routes": 66,
            "open_historical_exception_ids": open_ids,
            "scope_excludes_other_customers_services_and_all_real_matters": True,
        },
    )
    for index, provision in enumerate(spec["legal_provisions"], 1):
        add(
            "provision_status",
            f"PROVISION-{index:02d}",
            day + "T11:00:00+00:00",
            {
                "provision": provision,
                "decision": provision["scenario_status"],
                "real_status": "UNDETERMINED",
                "conditional_event_not_recurring_control": index >= 6,
                "not_applicable_conclusion": False,
            },
        )
    for index, occurrence in enumerate(selected["term_occurrences"], 1):
        historical_gap = (
            scenario == "MESSY" and occurrence["occurrence_id"] in HISTORICAL_FLOWDOWN_TERMS
        )
        add(
            "term_status",
            f"TERM-{index:03d}",
            day + "T12:00:00+00:00",
            {
                "occurrence": occurrence,
                "operating_owner_person_id": spec["owner_by_term_id"][occurrence["term_id"]],
                "counsel_decision": "SELECTED_SCENARIO_TERM_AND_OWNER_RECORDED",
                "status": (
                    "CURRENT_TERM_INDEXED_HISTORICAL_GAP_OPEN"
                    if historical_gap
                    else "SELECTED_SCENARIO_OWNER_ASSIGNED"
                ),
                "legal_provision_ids": _term_provisions(occurrence),
                "provider_calendar_is_contractual_only": (
                    occurrence["source_kind"] == "INTERNAL_PROVIDER_CALENDAR_TERM"
                ),
                "historical_gap_not_retroactively_cured": historical_gap,
                "real_term_or_legal_acceptance": "UNDETERMINED",
            },
        )
    for date in spec["simulated_period"]["watch_dates"]:
        add(
            "matter_watch",
            "MATTER-" + date,
            date + "T10:00:00+00:00",
            {
                "internal_selected_feed": [
                    "PHI_BA_V1",
                    "PROVIDER_LIFECYCLE_V2",
                    "CONTRACT_TRIAGE_V1",
                ],
                "known_selected_matter_ids": open_ids,
                "known_selected_matter_refs": context["exception_refs"][scenario],
                "provider_support_backfill_current_term_indexed": scenario == "MESSY",
                "historical_exception_open": scenario == "MESSY",
                "all_company_or_external_matters_reconciled": False,
                "outside_complaint_or_notice_nonoccurrence_asserted": False,
                "conditional_paths": ["45-CFR-164.410", "45-CFR-160.306", "45-CFR-160.504"],
                "conditional_paths_treated_as_recurring_controls": False,
            },
        )
        add(
            "change_watch",
            "CHANGE-" + date,
            date + "T11:00:00+00:00",
            {
                "legal_reference_checked_as_of": spec["legal_reference_checked_as_of"],
                "legal_reference_urls": [row["url"] for row in spec["legal_provisions"]],
                "selected_internal_change_items": (
                    [] if scenario == "CLEAN" else ["SUPPORT_FLOWDOWN_BACKFILL_WITH_OPEN_HISTORY"]
                ),
                "actual_2027_law_status": "NOT_VERIFIED",
                "2027_official_source_recheck_claimed": False,
                "all_contract_changes_reconciled": False,
            },
        )
    add(
        "reconciliation",
        "LEG001-SELECTED-RECON",
        "2027-12-31T17:00:00+00:00",
        {
            "status": (
                "SELECTED_SCOPE_RECONCILED_TRAINING_ONLY"
                if scenario == "CLEAN"
                else "SELECTED_SCOPE_RECONCILED_WITH_OPEN_HISTORICAL_EXCEPTIONS"
            ),
            "selected_scope_complete": scenario == "CLEAN",
            "term_owner_decisions": 34,
            "provision_classifications": 8,
            "matter_watch_periods": 3,
            "change_watch_periods": 3,
            "open_historical_exception_ids": open_ids,
            "unsupported_authored_routes": 66,
            "authored_task_status": "NOT_STARTED",
            "authored_task_conclusion": "NOT_RUN",
            "blanket_no_event_or_na_accepted": False,
            "real_world_legal_conclusion": "UNDETERMINED",
        },
    )
    if len(steps) != 50 or len({(system, record) for system, record, _, _ in steps}) != 50:
        raise CompanyStoreError("LEG001 exact selected docket event denominator differs")
    return steps


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("Fresh private LEG001 destination required")
    _private(destination.parent, directory=True)
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(prefix=".leg001-stage-", dir=destination.parent) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in context["spec"]["branches"].items():
            for system in SYSTEMS:
                store.register_system(COMPANY, branch, system, "AS-P003")
            records[scenario] = []
            for system, record, at, body in _steps(context, scenario):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    system,
                    record,
                    expected_version=0,
                    command_id=f"LEG001-{branch}-{system}-{record}",
                    event_at=at,
                    available_at=at,
                    content=encoded(body),
                    provenance={
                        "source_reference": SOURCE,
                        "scenario": scenario,
                        "source_pins": context["pins"],
                        "qualification": "FUTURE_TRAINING_SELECTED_LEGAL_DOCKET_NO_REAL_STATUS",
                    },
                )
                records[scenario].append(ref)
        receipt = {
            "schema": SCHEMA,
            "status": "FUTURE_FICTIONAL_SELECTED_LEG001_OPERATING_DOCKET_NO_AUDIT_CREDIT",
            "company": COMPANY,
            "branches": context["spec"]["branches"],
            "source_pins": context["pins"],
            "selected_chain": context["spec"]["selected_chain"],
            "selected_source_refs": context["source_refs"],
            "predecessor_triage_refs": context["triage_refs"],
            "source_exception_refs": context["exception_refs"],
            "selected_term_occurrences_per_branch": 34,
            "selected_scope_complete": {"CLEAN": True, "MESSY": False},
            "unsupported_authored_routes_per_side": 66,
            "real_hipaa_applicability": "UNDETERMINED",
            "actual_phi": False,
            "outside_message_sent": False,
            "source_complete": False,
            "audit_task_credit": False,
            "records": records,
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        _write(
            stage / "MANIFEST.json",
            {
                "schema": SCHEMA + "_MANIFEST",
                "receipt_sha256": _sha(stage / "RECEIPT.json"),
                "company_db_sha256": _sha(stage / "company.sqlite3"),
                "module_sha256": _sha(Path(__file__)),
                "spec_sha256": _sha(Path(repository) / SPEC),
                "native_version_count": 100,
                "audit_task_credit": False,
            },
        )
        if any(_private(path) != state for path, state in context["source_states"].items()):
            raise CompanyStoreError("LEG001 source changed during native docket build")
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    _private(root, directory=True)
    if {path.name for path in root.iterdir()} != {
        "RECEIPT.json",
        "MANIFEST.json",
        "company.sqlite3",
    }:
        raise CompanyStoreError("Exact private LEG001 three-file source required")
    paths = {name: root / name for name in ("RECEIPT.json", "MANIFEST.json", "company.sqlite3")}
    before = {name: _private(path) for name, path in paths.items()}
    _no_sidecars(paths["company.sqlite3"])
    context = _context(repository, private_repository)
    receipt, manifest = _json(paths["RECEIPT.json"]), _json(paths["MANIFEST.json"])
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": before["RECEIPT.json"][-1],
        "company_db_sha256": before["company.sqlite3"][-1],
        "module_sha256": _sha(Path(__file__)),
        "spec_sha256": _sha(Path(repository) / SPEC),
        "native_version_count": 100,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("LEG001 native manifest differs")
    expected = {
        "schema": SCHEMA,
        "status": "FUTURE_FICTIONAL_SELECTED_LEG001_OPERATING_DOCKET_NO_AUDIT_CREDIT",
        "company": COMPANY,
        "branches": context["spec"]["branches"],
        "source_pins": context["pins"],
        "selected_chain": context["spec"]["selected_chain"],
        "selected_source_refs": context["source_refs"],
        "predecessor_triage_refs": context["triage_refs"],
        "source_exception_refs": context["exception_refs"],
        "selected_term_occurrences_per_branch": 34,
        "selected_scope_complete": {"CLEAN": True, "MESSY": False},
        "unsupported_authored_routes_per_side": 66,
        "real_hipaa_applicability": "UNDETERMINED",
        "actual_phi": False,
        "outside_message_sent": False,
        "source_complete": False,
        "audit_task_credit": False,
        "records": receipt.get("records"),
        "limits": LIMITS,
    }
    if receipt != expected:
        raise CompanyStoreError("LEG001 native receipt/qualification differs")
    if set(receipt["records"]) != {"CLEAN", "MESSY"}:
        raise CompanyStoreError("LEG001 exact scenario receipt population differs")
    with closing(
        sqlite3.connect(paths["company.sqlite3"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("LEG001 SQLite integrity differs")
        counts = {
            name: db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in ("systems", "versions", "grants", "collections", "access_events")
        }
        if counts != {
            "systems": 12,
            "versions": 100,
            "grants": 0,
            "collections": 0,
            "access_events": 0,
        }:
            raise CompanyStoreError("LEG001 native population/access differs")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, "AS-P003")
            for branch in context["spec"]["branches"].values()
            for system in SYSTEMS
        }:
            raise CompanyStoreError("LEG001 native counsel custody differs")
        seen = set()
        for scenario, branch in context["spec"]["branches"].items():
            steps, refs = _steps(context, scenario), receipt["records"][scenario]
            if len(refs) != 50:
                raise CompanyStoreError("LEG001 scenario docket denominator differs")
            for (system, record, at, body), ref in zip(steps, refs, strict=True):
                route = (COMPANY, branch, system, record, 1)
                if (
                    tuple(ref[k] for k in ("company", "branch", "system", "record", "version"))
                    != route
                ):
                    raise CompanyStoreError("LEG001 native route differs")
                rows = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    route,
                ).fetchall()
                if len(rows) != 1:
                    raise CompanyStoreError("LEG001 native version missing or duplicated")
                row = rows[0]
                native = {
                    k: json.loads(row[k]) if k == "provenance" else row[k] for k in REFERENCE_FIELDS
                }
                if (
                    native != ref
                    or sha(row["content"]) != ref["sha256"]
                    or json.loads(row["content"]) != body
                    or ref["event_at"] != _time(at)
                    or ref["available_at"] != _time(at)
                    or ref["imported_at"] >= _time("2027-01-01T00:00:00+00:00")
                    or ref["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["provenance"]
                    != {
                        "source_reference": SOURCE,
                        "scenario": scenario,
                        "source_pins": context["pins"],
                        "qualification": "FUTURE_TRAINING_SELECTED_LEGAL_DOCKET_NO_REAL_STATUS",
                    }
                ):
                    raise CompanyStoreError("LEG001 native content/clock/provenance differs")
                seen.add(route)
        if len(seen) != 100:
            raise CompanyStoreError("LEG001 exact native route count differs")
    _no_sidecars(paths["company.sqlite3"])
    if {name: _private(path) for name, path in paths.items()} != before:
        raise CompanyStoreError("LEG001 docket changed during read-only verification")
    if any(_private(path) != state for path, state in context["source_states"].items()):
        raise CompanyStoreError("LEG001 reviewed upstream changed during verification")
    return receipt
