"""Company-native supplemental 2027 operations, with immutable history and no audit credit.

This trusted local source operator authors a fictional later operating period. It
never reads an audit result or Key, changes the frozen workrooms, contacts a party,
or asserts that its disposable local model is a deployed enterprise environment.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import hmac
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _time
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .operating_source_bridge import encoded, sha
from .private_publication import publish

MODULE = "enterprise/audit_suite/company_supplemental_operations_2027.py"
SPEC = "enterprise/audit_suite/company_supplemental_operations_2027_spec_v1.json"
SCHEMA = "SH_COMPANY_SUPPLEMENTAL_OPERATIONS_2027_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"A": "SUPPLEMENTAL-CLEAN", "B": "SUPPLEMENTAL-MESSY"}
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}
ROUTE = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V17_2026-10-01.json"
OWNERS = {
    "local_authority": "P001",
    "policy_document": "AS-P003",
    "retention_register": "AS-P014",
    "communication_directory": "AS-P005",
    "communication_event": "AS-P005",
    "privacy_responsibility": "AS-P003",
    "incident_intake": "AS-P008",
    "recovery_operation": "AS-P007",
    "procedure_document": "AS-P005",
    "procedure_calendar": "AS-P005",
    "procedure_operation": "AS-P005",
    "risk_decision": "AS-P008",
    "security_configuration": "AS-P007",
    "integrity_operation": "AS-P008",
    "identity_permission": "AS-P008",
    "key_custody": "AS-P008",
    "access_operation": "AS-P007",
    "workstation_inventory": "AS-P012",
    "facility_maintenance": "AS-P012",
    "media_movement": "AS-P012",
    "workforce_case": "AS-P006",
    "responsibility_feedback": "AS-P006",
    "period_register": "AS-P005",
}
TASK_SYSTEMS = {
    "TASK-SH-POL-001-corporate-ACTION-H-RETENTION": (
        "policy_document",
        "procedure_document",
        "retention_register",
        "incident_intake",
        "communication_event",
        "facility_maintenance",
    ),
    "TASK-SH-POL-001-corporate-ACTION-S-COMMUNICATION": (
        "communication_directory",
        "communication_event",
    ),
    "TASK-SH-POL-001-corporate-CHECK-HIPAA:164.304": (
        "incident_intake",
        "recovery_operation",
        "privacy_responsibility",
    ),
    "TASK-SH-POL-001-corporate-CHECK-HIPAA:164.530": (
        "privacy_responsibility",
        "retention_register",
        "communication_event",
        "workforce_case",
    ),
    "TASK-SH-POL-004-corporate-IMPLEMENTATION": (
        "local_authority",
        "policy_document",
        "procedure_document",
        "procedure_calendar",
        "procedure_operation",
    ),
    "TASK-SH-POL-004-corporate-TOD": ("procedure_document", "procedure_calendar"),
    "TASK-SH-POL-004-corporate-TOE": (
        "procedure_calendar",
        "procedure_operation",
        "period_register",
    ),
    "TASK-SH-SEC-001-corporate-ACTION-H-ADDRESSABLE": (
        "risk_decision",
        "security_configuration",
        "local_authority",
    ),
    "TASK-SH-SEC-001-corporate-ACTION-H-INTEGRITY": (
        "integrity_operation",
        "security_configuration",
        "incident_intake",
    ),
    "TASK-SH-SEC-001-corporate-ACTION-H-PHYSICAL-MOVEMENT": (
        "workstation_inventory",
        "facility_maintenance",
        "media_movement",
        "recovery_operation",
    ),
    "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC6.1": (
        "identity_permission",
        "key_custody",
        "access_operation",
        "security_configuration",
    ),
    "TASK-SH-ETH-001-corporate-ACTION-H-SANCTIONS": (
        "workforce_case",
        "responsibility_feedback",
        "local_authority",
        "identity_permission",
        "access_operation",
    ),
}
REF_FIELDS = (
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


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def private_file(path: Path) -> tuple:
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CompanyStoreError("Private alias forbidden")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1:
        raise CompanyStoreError("Ordinary 0600 single-link source required")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, digest(path)


def add_years(day: date, years: int) -> date:
    year = day.year + years
    return day.replace(year=year, day=min(day.day, calendar.monthrange(year, day.month)[1]))


def retention_decision(
    created: str, last_in_effect: str | None, *, current: bool, requested: str, held: bool = False
) -> dict:
    """Six calendar years from the later known date; current or held records cannot release."""
    if type(current) is not bool or type(held) is not bool:
        raise CompanyStoreError("Boolean current/hold disposition state required")
    born = date.fromisoformat(created)
    end = date.fromisoformat(last_in_effect) if last_in_effect else None
    if end and end < born:
        raise CompanyStoreError("Policy end predates creation")
    floor = add_years(max(born, end or born), 6)
    reasons = []
    if current:
        reasons.append("CURRENT_EFFECTIVE_DOCUMENT_NO_FINAL_END_DATE")
    if held:
        reasons.append("DISPOSITION_HOLD")
    if date.fromisoformat(requested) <= floor:
        reasons.append("BEFORE_OR_ON_SIX_CALENDAR_YEAR_FLOOR")
    return {
        "created_date": created,
        "last_in_effect_date": last_in_effect,
        "current_effective": current,
        "minimum_retain_through": floor.isoformat(),
        "release_eligible_on": (floor + timedelta(days=1)).isoformat(),
        "requested_date": requested,
        "hold": held,
        "decision": "DENY" if reasons else "ELIGIBLE_FOR_SEPARATE_APPROVAL",
        "reasons": reasons,
        "actual_deletion": False,
    }


def integrity_trial(
    original: bytes, received: bytes, key: bytes, expected_tag: str, *, semantic_only: bool = False
) -> dict:
    """Perform a marker-only content-authenticity check independently of semantic validity."""
    if not hmac.compare_digest(hmac.new(key, original, hashlib.sha256).hexdigest(), expected_tag):
        raise CompanyStoreError("Expected authenticator must bind to preserved original")
    try:
        payload = json.loads(received)
        valid = type(payload.get("batch_total")) is int and payload["batch_total"] >= 0
    except (ValueError, AttributeError):
        valid = False
    actual_tag = hmac.new(key, received, hashlib.sha256).hexdigest()
    authentic = hmac.compare_digest(actual_tag, expected_tag)
    accepted = valid and (semantic_only or authentic)
    return {
        "original_sha256": sha(original),
        "received_sha256": sha(received),
        "semantic_valid": valid,
        "content_authentic": authentic,
        "validator": "SEMANTIC_ONLY" if semantic_only else "SEMANTIC_AND_CONTENT_AUTHENTICITY",
        "actual_tag": actual_tag,
        "expected_tag": expected_tag,
        "handling": "ACCEPT" if accepted else "QUARANTINE",
    }


def access_decision(request: dict, policy: dict, *, at: str) -> dict:
    """Evaluate every local model trust boundary, including service identity and privilege."""
    reason = []
    principal = policy["principals"].get(request.get("principal"))
    if not principal:
        reason.append("UNKNOWN_PRINCIPAL")
    if request.get("issuer") != policy["issuer"]:
        reason.append("ISSUER_MISMATCH")
    if request.get("audience") != policy["audience"]:
        reason.append("AUDIENCE_MISMATCH")
    if _time(request.get("expires_at", at)) <= _time(at):
        reason.append("EXPIRED_CREDENTIAL")
    if principal:
        if (
            request.get("resource") not in principal["resources"]
            or request.get("operation") not in principal["operations"]
        ):
            reason.append("RESOURCE_PERMISSION_DENIED")
        if principal["kind"] == "HUMAN" and request.get("mfa") is not True:
            reason.append("MFA_REQUIRED")
        if request.get("privileged"):
            approval = policy.get("privilege_approvals", {}).get(request.get("approval"))
            if not principal["privilege_eligible"] or not approval:
                reason.append("UNAPPROVED_PRIVILEGE")
            elif (
                approval["principal"] != request.get("principal")
                or approval["resource"] != request.get("resource")
                or approval["operation"] != request.get("operation")
                or _time(at) < _time(approval["valid_from"])
                or _time(at) >= _time(approval["valid_until"])
            ):
                reason.append("PRIVILEGE_APPROVAL_SCOPE_MISMATCH")
    restriction = policy.get("temporary_restrictions", {}).get(request.get("principal"))
    if (
        restriction
        and request.get("privileged")
        and (_time(restriction["valid_from"]) <= _time(at) < _time(restriction["valid_until"]))
    ):
        if request.get("initiated_by") not in restriction["permitted_peer_initiators"]:
            reason.append("TEMPORARY_INITIATION_RESTRICTION")
    return {
        "request": request,
        "evaluated_at": _time(at),
        "decision": "DENY" if reason else "ALLOW",
        "reasons": reason,
        "boundaries_evaluated": [
            "issuer",
            "audience",
            "credential_expiry",
            "principal_authentication",
            "resource_permission",
            "privileged_session",
        ],
    }


def _ref(row: dict) -> dict:
    return {k: row[k] for k in REF_FIELDS}


def _exact_native_schema(db: sqlite3.Connection) -> None:
    """Require all five tables, their constraints/indexes and all four exact triggers."""

    def normal(sql: str | None) -> str | None:
        return "".join(sql.split()).lower() if sql is not None else None

    definitions = {
        "systems": "CREATE TABLE systems(company TEXT, branch TEXT, system TEXT, "
        "owner TEXT NOT NULL, PRIMARY KEY(company,branch,system))",
        "versions": "CREATE TABLE versions(company TEXT, branch TEXT, system TEXT, "
        "record TEXT, version INTEGER, event_at TEXT, available_at TEXT NOT NULL, "
        "imported_at TEXT NOT NULL, origin TEXT NOT NULL, provenance TEXT NOT NULL, "
        "content BLOB NOT NULL, sha256 TEXT NOT NULL, command_id TEXT UNIQUE NOT NULL, "
        "input_digest TEXT NOT NULL, PRIMARY KEY(company,branch,system,record,version), "
        "FOREIGN KEY(company,branch,system) REFERENCES systems(company,branch,system))",
        "grants": "CREATE TABLE grants(principal TEXT, engagement TEXT, company TEXT, "
        "branch TEXT, system TEXT, active INTEGER NOT NULL, "
        "PRIMARY KEY(principal,engagement,company,branch,system))",
        "access_events": "CREATE TABLE access_events(id INTEGER PRIMARY KEY, principal TEXT, "
        "engagement TEXT, company TEXT, branch TEXT, system TEXT, "
        "active INTEGER, recorded_at TEXT)",
        "collections": "CREATE TABLE collections(command_id TEXT PRIMARY KEY, "
        "input_digest TEXT NOT NULL, receipt TEXT NOT NULL)",
    }
    expected = {("table", name, name): normal(sql) for name, sql in definitions.items()}
    for table, count in [("systems", 1), ("versions", 2), ("grants", 1), ("collections", 1)]:
        for i in range(1, count + 1):
            expected[("index", f"sqlite_autoindex_{table}_{i}", table)] = None
    for table, label in [("versions", "source"), ("collections", "collection")]:
        for verb in ["UPDATE", "DELETE"]:
            name = f"no_{'version' if table == 'versions' else 'collection'}_{verb.lower()}"
            expected[("trigger", name, table)] = normal(
                f"CREATE TRIGGER {name} BEFORE {verb} ON {table} "
                f"BEGIN SELECT RAISE(ABORT,'Immutable {label}'); END"
            )
    actual = {
        (kind, name, table): normal(sql)
        for kind, name, table, sql in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master")
    }
    if actual != expected:
        raise CompanyStoreError(
            "Exact native table/constraint/index/immutable trigger schema differs"
        )
    if db.execute("PRAGMA user_version").fetchone()[0] != 0 or (
        db.execute("PRAGMA application_id").fetchone()[0] != 0
    ):
        raise CompanyStoreError("Native database application/version metadata differs")


def _read_native(path: Path, *, import_floor: str | None = None) -> list[dict]:
    """No mutable constructor, grants, journals, or SQLite sidecars in predecessor reads."""
    stamp = private_file(path)
    if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise CompanyStoreError("Unsealed native predecessor")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Native database integrity differs")
        _exact_native_schema(db)
        if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise CompanyStoreError("Native foreign-key integrity differs")
        rows = [
            dict(x)
            for x in db.execute(
                "SELECT * FROM versions ORDER BY branch,event_at,system,record,version"
            )
        ]
    ceiling = _time(datetime.now().astimezone().isoformat())
    sequences: dict[tuple, list] = {}
    for row in rows:
        imported = _time(row["imported_at"])
        if (
            imported != row["imported_at"]
            or imported > ceiling
            or (import_floor is not None and imported < _time(import_floor))
        ):
            raise CompanyStoreError("Actual import clock is outside authorized generation window")
        if sha(row["content"]) != row["sha256"] or _time(row["available_at"]) < _time(
            row["event_at"]
        ):
            raise CompanyStoreError("Native original hash or availability differs")
        key = tuple(row[k] for k in ("company", "branch", "system", "record"))
        sequences.setdefault(key, []).append(row["version"])
    if any(sorted(v) != list(range(1, len(v) + 1)) for v in sequences.values()):
        raise CompanyStoreError("Incomplete native version sequence")
    if private_file(path) != stamp:
        raise CompanyStoreError("Native source changed while reading")
    return rows


def _context(repository: Path, private: Path) -> dict:
    spec = json.loads((repository / SPEC).read_bytes())
    authorization = spec.get("source_generation_authorization", {})
    if authorization != {
        "not_before_utc": "2026-10-01T00:00:00+00:00",
        "authorization_reference": (
            "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md"
        ),
        "authorization_scope": (
            "Later local company-source history for the approved fictional 2027 reference "
            "service; commissioned source task dated2026-10-01"
        ),
        "real_clock_separate_from_simulated_events": True,
    }:
        raise CompanyStoreError("Source-generation authorization boundary differs")
    if _p1_inventory(private) != P1_FREEZE:
        raise CompanyStoreError("Frozen 538-file P1 inventory differs")
    canon = {}
    for name, expected in spec["canon_pins"].items():
        p = repository / name
        if p.is_symlink() or digest(p) != expected:
            raise CompanyStoreError(f"Canon pin differs: {name}")
        canon[name] = expected
    licensed = spec["licensed_reference"]
    if digest(Path(licensed["path"])) != licensed["sha256"]:
        raise CompanyStoreError("Licensed SOC2 reference differs")
    stamps, originals = {}, {}
    for name, entry in spec["predecessors"].items():
        for relative, expected in entry["pins"].items():
            p = private / relative
            stamps[relative] = private_file(p)
            if stamps[relative][-1] != expected:
                raise CompanyStoreError(f"Predecessor pin differs: {relative}")
        rows = _read_native(private / entry["root"] / "company.sqlite3")
        originals[name] = {}
        for side, branch in entry["branches"].items():
            selected = [r for r in rows if r["branch"] == branch]
            if not selected:
                raise CompanyStoreError("Predecessor branch empty")
            originals[name][side] = {_key(r): _ref(r) for r in selected}
    matrix = json.loads((repository / ROUTE).read_bytes())
    routes = {}
    for side in "AB":
        selected = [r for r in matrix["rows"] if r["side"] == side and r["task_id"] in TASK_SYSTEMS]
        if (
            len(selected) != 12
            or {r["task_id"] for r in selected} != set(TASK_SYSTEMS)
            or any(
                r["targeted_integrated_source_ids"]
                or r["current_status"] != "NOT_STARTED"
                or r["current_conclusion"] != "NOT_RUN"
                or r["audit_task_credit"]
                for r in selected
            )
        ):
            raise CompanyStoreError("Exact twelve unsupported V17 routes differ")
        routes[side] = selected
    actors = {
        x.get("person_id"): x.get("name")
        for x in json.loads((repository / "docs/organization/source/chartbook.json").read_bytes())[
            "nodes"
        ]
        if x.get("type") == "person"
    }
    expected = {
        "P001": "Daniel Mercer",
        "AS-P003": "Helena Ward",
        "AS-P005": "Martin Ives",
        "AS-P006": "Sofia Hart",
        "AS-P007": "Elliot Tran",
        "AS-P008": "Dana West",
        "AS-P012": "Victor Lane",
        "AS-P013": "Erin Cross",
        "AS-P014": "Omar Vale",
    }
    if any(actors.get(k) != v for k, v in expected.items()):
        raise CompanyStoreError("Canonical actor identity differs")
    if any(private_file(private / p) != old for p, old in stamps.items()):
        raise CompanyStoreError("Pinned predecessors changed during context read")
    return {
        "spec": spec,
        "canon": canon,
        "stamps": stamps,
        "originals": originals,
        "routes": routes,
    }


def _key(row: dict) -> str:
    return f"{row['system']}/{row['record']}/{row['version']}"


def _upstream(
    ctx: dict, side: str, family: str, system: str, record: str, version: int = 1
) -> dict:
    try:
        return ctx["originals"][family][side][f"{system}/{record}/{version}"]
    except KeyError as error:
        raise CompanyStoreError("Exact predecessor original absent") from error


def fixture_material() -> dict[str, bytes]:
    # Explicitly non-secret, nonpersonal marker data. Never a production credential.
    original = encoded(
        {
            "batch_id": "SIM-SUPPLEMENTAL-MARKER-01",
            "batch_total": 120,
            "payload_kind": "NONPERSONAL_SYNTHETIC_MARKER",
        }
    )
    altered = encoded(
        {
            "batch_id": "SIM-SUPPLEMENTAL-MARKER-01",
            "batch_total": 121,
            "payload_kind": "NONPERSONAL_SYNTHETIC_MARKER",
        }
    )
    return {
        "marker-original.json": original,
        "marker-altered.json": altered,
        "verifier-key.bin": hashlib.sha256(
            b"sable-harbor-disposable-nonsecret-test-key-2027"
        ).digest(),
    }


def _settings() -> list[tuple[str, dict, str, str]]:
    """Specification-specific settings, environmental facts, risks and implementation evidence."""
    return [
        (
            "SUPERVISION",
            {"allowed_workforce": ["AS-P007", "AS-P012", "AS-P014"], "supervisor": "AS-P008"},
            (
                "Small named restricted-hosting operator roster; unattended customer-data "
                "handling would bypass accountable oversight."
            ),
            (
                "Supervisor-approved work queue and second-person elevated-action review; "
                "three-person roster can sustain this without continuous employee surveillance."
            ),
        ),
        (
            "CLEARANCE",
            {
                "eligible_roles": ["TECHNOLOGY_OPERATOR", "FACILITY_ESCORT", "RECORDS_OPERATOR"],
                "role_review_days": 30,
            },
            (
                "Different roles encounter different physical or logical boundaries; title "
                "alone does not justify marker-store access."
            ),
            (
                "Compare assignment, training and approved purpose before access; documented "
                "monthly role review is feasible for the selected roster."
            ),
        ),
        (
            "TERMINATION",
            {
                "disable_on_role_end": True,
                "credential_ttl_seconds": 900,
                "revocation_owner": "AS-P008",
            },
            (
                "Access persists after a selected assignment ends unless system permissions and"
                " short-lived credentials are revoked."
            ),
            (
                "Role-end queue revokes logical and cage privileges; short credential lifetime "
                "bounds residual model access without assuming an employment termination."
            ),
        ),
        (
            "AUTHORIZATION",
            {"approver": "AS-P008", "requester_cannot_self_approve": True},
            (
                "Restricted service permission differs from general enterprise role; "
                "self-granting privileges creates concentration risk."
            ),
            (
                "CISO approves named resource and purpose; peer review precedes privileged "
                "permission issuance."
            ),
        ),
        (
            "ACCESS_CHANGE",
            {
                "permissions": ["marker.read", "marker.recover"],
                "default": "DENY",
                "change_record_required": True,
            },
            (
                "A new resource or recovery duty changes necessary permissions; copying a broad"
                " role would admit unrelated records."
            ),
            (
                "Versioned permission matrix and explicit change receipt bind principal, "
                "resource, operation and expiry; executable local model denies missing "
                "resources."
            ),
        ),
        (
            "REMINDERS",
            {
                "monthly_topics": [
                    "protected_reporting",
                    "security_attempt_intake",
                    "no_unapproved_copy",
                ]
            },
            (
                "Named operators work across technology, facilities and records; requirements "
                "can drift after service changes."
            ),
            (
                "Short role-specific monthly reminders accompany the operating review; delivery"
                " and response receipts avoid relying on generic awareness acknowledgments."
            ),
        ),
        (
            "MALWARE",
            {
                "approved_marker_format": "JSON_DATA_ONLY",
                "execution_of_payload": False,
                "unknown_file_handling": "QUARANTINE",
            },
            (
                "Nonpersonal markers remain data-only; unknown executable material would add an"
                " unnecessary execution path."
            ),
            (
                "Local receiving model rejects non-JSON input and quarantines unexpected "
                "format; production endpoint malware controls remain outside this disposable "
                "model."
            ),
        ),
        (
            "LOGIN_MONITOR",
            {
                "capture": [
                    "unknown_principal",
                    "wrong_audience",
                    "expired_credential",
                    "unapproved_privilege",
                ],
                "review_days": 1,
            },
            (
                "Both human and service credentials cross issuer, resource and privileged "
                "boundaries; blocked attempts are security incidents for intake."
            ),
            (
                "Record all model decisions with issuer/audience/resource reasons, inspect "
                "denial feed daily during exercises, escalate attempted unauthorized actions."
            ),
        ),
        (
            "CREDENTIALS",
            {
                "human_mfa": True,
                "service_ttl_seconds": 900,
                "local_verifier_key_id": "MODEL-KEY-01",
                "production_passwords": "NOT_PRESENT",
            },
            (
                "The disposable model contains no real passwords; static verifier material "
                "cannot authenticate a production person."
            ),
            (
                "Human model requests require MFA flag and service requests require "
                "issuer/audience/expiry; test verifier key is local non-secret fixture with "
                "named custody, never a live credential."
            ),
        ),
        (
            "CONTINGENCY_TEST",
            {
                "test_frequency": "MONTHLY_DURING_LOCAL_OPERATING_PERIOD",
                "success_requires": ["exact_bytes", "authorized_retrieval", "usable_JSON"],
            },
            (
                "A stored copy could exist yet be inaccessible or unparsable when an authorized"
                " operator needs recovery."
            ),
            (
                "Recover nonpersonal marker through a permitted role, recompute bytes, parse "
                "and inspect expected batch; revise process after failures rather than counting"
                " an untouched backup."
            ),
        ),
        (
            "CRITICALITY",
            {
                "marker_store": "RECOVERY_PRIORITY_1",
                "local_reporting_copy": "PRIORITY_2",
                "target_minutes": 30,
            },
            (
                "Restricted service marker custody is needed before secondary reporting can "
                "resume; copying every file first delays essential use."
            ),
            (
                "Restore marker custody before derived report, retain dependency and target "
                "rationale; two-resource model supports this ordering at low local cost."
            ),
        ),
        (
            "CONTINGENCY_ACCESS",
            {"sites": ["RNO-CAGE-A", "BOI-CAGE-R"], "escort_required": True, "approval": "AS-P008"},
            (
                "The approved training topology uses Reno primary and Boise recovery, but "
                "operator cage access differs from the provider perimeter."
            ),
            (
                "Use approved escort and temporary badge queue for selected cages; do not infer"
                " provider-wide emergency access from local authority."
            ),
        ),
        (
            "FACILITY_PLAN",
            {
                "zones": ["RNO-CAGE-A", "BOI-CAGE-R"],
                "physical_boundary": "SELECTED_COMPANY_CAGES_ONLY",
            },
            (
                "Portable marker media and workstations move through different cage boundaries;"
                " a generic site label conceals handling risk."
            ),
            (
                "Register custody and escort for each selected zone, require exact copy before "
                "data-bearing movement and link repair logs; provider perimeter remains "
                "unreviewed."
            ),
        ),
        (
            "ACCESS_VALIDATION",
            {"badge_resource_match": True, "role_expiry_check": True, "visitor_escort": "AS-P012"},
            (
                "A valid badge for one resource or a ended technician assignment does not "
                "authorize another cage visit."
            ),
            (
                "Selected zone validation checks role, permitted location and expiry; visitor "
                "work orders require named escort and time-bounded authorization."
            ),
        ),
        (
            "MAINTENANCE",
            {
                "capture_security_repairs": True,
                "ticket_fields": [
                    "zone",
                    "device",
                    "approval",
                    "before",
                    "after",
                    "technician",
                    "verification",
                ],
            },
            (
                "Latch repair temporarily changes the selected physical boundary and could "
                "conceal uncontrolled ingress."
            ),
            (
                "Separate security-maintenance work order retains before/after condition and "
                "independent verification rather than an invoice-only record."
            ),
        ),
        (
            "MOVEMENT",
            {
                "serial_required": True,
                "custodian_required": True,
                "source_destination_required": True,
            },
            (
                "Local workstation and removable marker-media moves can detach custody from an "
                "inventory resource."
            ),
            (
                "Movement ledger reconciles independently approved resource population to "
                "custodian, source, destination and disposition; reused media requires "
                "sanitization receipt."
            ),
        ),
        (
            "PRE_MOVE_COPY",
            {"exact_retrievable_copy_required": True, "release_when_copy_missing": False},
            (
                "A backup that cannot be retrieved before departure offers no protection "
                "against loss during relocation."
            ),
            (
                "Before each data-bearing movement, permitted operator retrieves exact marker, "
                "hashes and parses it; blocked release stays blocked until evidence exists."
            ),
        ),
        (
            "AUTO_LOGOFF",
            {
                "human_idle_seconds": 300,
                "headless_service_session": False,
                "service_ttl_seconds": 900,
                "isolated_process": True,
            },
            (
                "Human interactive sessions need idle lock; the headless service identity has "
                "no interactive desktop to log off."
            ),
            (
                "Implement five-minute idle lock for humans; use expiring purpose-bound service"
                " credential and process isolation as equivalent headless protection, "
                "documenting why desktop logoff cannot operate there."
            ),
        ),
        (
            "STORAGE_ENCRYPTION",
            {
                "required_model_setting": "AES-256-GCM",
                "key_owner": "AS-P008",
                "test_model_scope": "CONFIGURATION_ONLY",
            },
            (
                "Portable-media loss and recovery copies create confidentiality risk even "
                "though this rehearsal carries no personal data."
            ),
            (
                "Local architecture requires storage encryption and separate security key "
                "custody; configuration decision is simulated, cryptographic deployment is not "
                "demonstrated by this source."
            ),
        ),
        (
            "CONTENT_AUTHENTICITY",
            {
                "marker_hmac": "HMAC-SHA256",
                "semantic_validation_separate": True,
                "altered_copy_handling": "QUARANTINE",
            },
            (
                "A numeric marker changed from 120 to 121 remains semantically valid yet lacks "
                "authorization."
            ),
            (
                "Actual local HMAC/content-hash trial distinguishes business validity from "
                "unauthorized alteration and quarantines mismatch; synthetic fixture has no "
                "production trust claim."
            ),
        ),
        (
            "TRANSFER_INTEGRITY",
            {
                "authenticate_received_bytes": True,
                "verify_before_publish": True,
                "failed_copy": "QUARANTINE",
            },
            (
                "A source-only hash cannot detect modification in the receiving copy unless a "
                "protected expected authenticator reaches the verifier."
            ),
            (
                "Retain expected HMAC in named verifier custody, authenticate receiving bytes "
                "before publishing and route mismatch to incident response."
            ),
        ),
        (
            "TRANSFER_ENCRYPTION",
            {
                "required_model_setting": "TLS1.3_PEER_AND_ENDPOINT_VALIDATION",
                "test_model_scope": "CONFIGURATION_ONLY",
            },
            (
                "A wrong endpoint can receive a well-formed payload; encryption without "
                "recipient validation would not enforce purpose."
            ),
            (
                "Architecture requires encrypted peer-validated channel and exact endpoint "
                "authorization; local permission trials enforce endpoint/resource boundary, "
                "while live TLS is outside this data-only model."
            ),
        ),
    ]


def _policy() -> dict:
    return {
        "issuer": "urn:sableharbor:local-model:identity",
        "audience": "urn:sableharbor:restricted-hosting:marker",
        "privilege_approvals": {
            "AS-P008-SUP-ELEVATION-01": {
                "principal": "AS-P007",
                "resource": "marker-store",
                "operation": "read",
                "approved_by": "AS-P008",
                "challenged_by": "AS-P003",
                "valid_from": "2027-09-07T09:00:00+00:00",
                "valid_until": "2027-09-07T09:15:00+00:00",
            }
        },
        "principals": {
            "AS-P007": {
                "kind": "HUMAN",
                "resources": ["marker-store", "marker-recovery"],
                "operations": ["read", "recover"],
                "privilege_eligible": True,
            },
            "SIM-SERVICE-RECOVERY-01": {
                "kind": "SERVICE",
                "resources": ["marker-recovery"],
                "operations": ["recover"],
                "privilege_eligible": False,
            },
        },
    }


def _plan(ctx: dict, side: str) -> list[dict]:
    """Ordered original business records; late corrections append rather than erase."""
    result, counts = [], {}
    fixtures = fixture_material()
    marker, altered, key = (
        fixtures[x] for x in ("marker-original.json", "marker-altered.json", "verifier-key.bin")
    )
    tag = hmac.new(key, marker, hashlib.sha256).hexdigest()

    def put(system, record, at, body, *, deps=(), upstream=()):
        identity = (system, record)
        version = counts.get(identity, 0) + 1
        counts[identity] = version
        result.append(
            {
                "system": system,
                "record": record,
                "version": version,
                "event_at": _time(at),
                "body": body,
                "dependencies": list(deps),
                "upstream": list(upstream),
            }
        )
        return f"{system}/{record}/{version}"

    prior = [
        _upstream(ctx, side, "policy", "policy_baseline", "BASELINE"),
        _upstream(ctx, side, "procedure", "result_register", "FINAL"),
        _upstream(ctx, side, "conduct", "conduct_code", "FICTIONAL-LOCAL-APPROVAL"),
        _upstream(ctx, side, "phi", "contract_register", "BAA-CUST-01"),
        _upstream(ctx, side, "phi", "contract_register", "BAA-SUB-01"),
    ]
    authority = put(
        "local_authority",
        "LOCAL-OPERATING-ORDER-2027",
        "2027-08-23T09:00:00+00:00",
        {
            "issuer": "P001",
            "issuer_role": "Chief Executive Officer",
            "decision": "APPROVE_LOCAL_SUPPLEMENTAL_PROGRAM",
            "service": "SIM-RESTRICTED-HOSTING-01",
            "effective_at": "2027-08-25T00:00:00+00:00",
            "named_responsibilities": {
                "AS-P008": "Assigned local security official and access/risk decision owner",
                "AS-P003": "Contractual privacy coordination and lawful-document interpretation",
                "AS-P005": "Monthly operating review and internal/external communications owner",
                "AS-P006": "Employee-relations case administration with Legal protection review",
                "AS-P014": "Documentation availability and retention operator",
                "AS-P007": "Marker-service operation and recovery",
                "AS-P012": "Selected cage maintenance and media custody",
            },
            "reserved_authority": {
                "AS-P009": (
                    "Internal Audit remains independent and has no source-operation or "
                    "employee-sanction management role"
                ),
                "board": "No Board collective approval asserted",
            },
            "authority_boundary": (
                "Explicit later fictional local appointment; not a 2026 acceptance, enterprise "
                "policy release, or customer privacy-officer appointment"
            ),
            "earlier_status": (
                "2026 future policy and March/May intake/candidate history retained; August "
                "selected attestation is not a workforce enforcement record"
            ),
        },
        upstream=prior,
    )
    accepted = put(
        "local_authority",
        "LOCAL-DELEGATE-ACCEPTANCE",
        "2027-08-23T10:00:00+00:00",
        {
            "order_id": "LOCAL-OPERATING-ORDER-2027",
            "accepted_by": [
                "AS-P003",
                "AS-P005",
                "AS-P006",
                "AS-P007",
                "AS-P008",
                "AS-P012",
                "AS-P014",
            ],
            "acceptance_scope": (
                "Named supplemental program only; prior employment and enterprise appointment "
                "acceptance dates unchanged"
            ),
        },
        deps=[authority],
    )
    doc1 = put(
        "policy_document",
        "SUP-OPERATING-POLICY-2027",
        "2027-08-24T09:00:00+00:00",
        {
            "document_number": "SUP-OPERATING-POLICY-2027",
            "title": "Restricted-hosting local responsibilities, reporting and documentation",
            "owner": "AS-P003",
            "approval": {
                "approver": "P001",
                "decision": "APPROVED",
                "approved_at": "2027-08-24T08:00:00+00:00",
            },
            "effective_at": "2027-08-25T00:00:00+00:00",
            "policy_text": [
                (
                    "Named implementers must receive the current responsibilities and have "
                    "retrievable superseded instructions."
                ),
                (
                    "Receive successful and attempted unauthorized activity; protect a person "
                    "who reports in good faith and evaluate facts before corrective action."
                ),
                (
                    "Keep security policies, procedures and required activity documentation for"
                    " six calendar years after creation or last in effect, whichever is later; "
                    "current instructions have no final disposal date."
                ),
                (
                    "Privacy documentation for contractually performed covered-customer "
                    "functions follows the same local six-year floor; this does not set a "
                    "medical-record retention period."
                ),
                (
                    "Do not release marker media without retrievable exact copy, permission and"
                    " named destination custody."
                ),
                (
                    "Escalate unknown or missing records; a late correction cannot erase the "
                    "earlier operational lapse."
                ),
            ],
            "audience": [
                "AS-P003",
                "AS-P005",
                "AS-P006",
                "AS-P007",
                "AS-P008",
                "AS-P012",
                "AS-P013",
                "AS-P014",
            ],
            "relationship_to_prior_policy": (
                "Separate local supplement; the May candidate and locked2026 future enterprise "
                "policy are not superseded or retroactively approved"
            ),
        },
        deps=[accepted],
    )
    procedure = put(
        "procedure_document",
        "SUP-MONTHLY-OPERATING-REVIEW",
        "2027-08-24T10:00:00+00:00",
        {
            "procedure_number": "SUP-MONTHLY-OPERATING-REVIEW",
            "owner": "AS-P005",
            "approver": "AS-P003",
            "approved_at": "2027-08-24T09:30:00+00:00",
            "effective_at": "2027-08-25T00:00:00+00:00",
            "objective": (
                "Keep named service responsibilities, active security decisions and "
                "documentation availability aligned as the restricted-hosting model changes"
            ),
            "boundary": (
                "This local supplemental program, its eight implementers and nonpersonal marker"
                " resources; no all-company assertion"
            ),
            "frequency_and_trigger": (
                "First day each Sep-Dec month at 09:00 UTC; due third day 17:00 UTC. Material "
                "changes and new concerns trigger an additional review."
            ),
            "inputs": [
                "Current/superseded policy originals",
                "Required implementer directory",
                "Delivery and concern receipt ledgers",
                "22 specification-specific risk/configuration records",
                "Required activity retention index",
                "Incident and movement receipts",
            ],
            "steps": [
                "Resolve exact effective instruction and confirm named owners",
                "Reconcile required recipients against actual delivery and contact address",
                "Confirm each retained document can be retrieved unchanged",
                "Check every applicable local risk decision and retain exceptions",
                (
                    "Sign factual result and assign correction with due date; do not declare "
                    "complete when an input is missing"
                ),
            ],
            "decision_criteria": {
                "required_recipient_difference": 0,
                "unretrievable_required_originals": 0,
                "risk_decisions_expected": 22,
                "unapproved_disposition": 0,
            },
            "outputs": [
                "Dated operator result",
                "Independent Legal challenge where missing or overdue",
                "Corrective action and residual gap",
            ],
            "exception_handling": (
                "Open deficiency with owner, due date and separate effectiveness observation; "
                "latest successful run does not cure missed-period deadline"
            ),
            "performer": "AS-P005",
            "challenge_reviewer": "AS-P003",
            "self_review_permitted": False,
        },
        deps=[doc1],
    )
    calendar_ref = put(
        "procedure_calendar",
        "2027-REVIEW-DUE-REGISTER",
        "2027-08-24T11:00:00+00:00",
        {
            "population_source": "Approved supplemental procedure scheduler",
            "program_started": "2027-08-25T00:00:00+00:00",
            "scheduled": [
                {
                    "trigger_id": f"DUE-2027-{m:02d}",
                    "trigger_at": f"2027-{m:02d}-01T09:00:00+00:00",
                    "due_at": f"2027-{m:02d}-03T17:00:00+00:00",
                }
                for m in range(9, 13)
            ],
            "not_scheduled_interval": {
                "start": "2027-01-01",
                "end": "2027-08-24",
                "reason": (
                    "Supplemental procedure not effective; prior candidate runs remain separate"
                    " unapproved history"
                ),
            },
            "one_off_trigger_rule": (
                "Each directory revision, inbound concern and failed authenticity/movement "
                "attempt creates an additional issue action in its originating ledger"
            ),
        },
        deps=[procedure],
    )
    privacy = put(
        "privacy_responsibility",
        "CUSTOMER-OBLIGATION-BOUNDARY",
        "2027-08-25T09:00:00+00:00",
        {
            "customer_id": "SIM-COVERED-CUSTOMER-01",
            "subcontractor_id": "SIM-RECOVERY-SUPPORT-01",
            "customer_contract": "SIM-BAA-CUST-01",
            "subcontractor_contract": "SIM-BAA-SUB-01",
            "business_role": (
                "Fictional business-associate/subcontractor operating chain; actual legal "
                "status undetermined"
            ),
            "direct_security_responsibilities": [
                "Assigned security official",
                "Risk-specific safeguards and incident handling",
                "Local workforce sanctions for established security-policy noncompliance",
                "Required security-document retention and availability",
            ],
            "covered_customer_retains": [
                "Covered-customer privacy-official and contact designation",
                "Privacy notice content, authorization and issuance",
                "Individual-rights determinations not expressly delegated",
                "Covered-customer workforce sanctions",
            ],
            "delegated_service_steps": [
                "Receive customer privacy concerns in named queue",
                "Preserve marker/supporting record and securely route the concern",
                "Support customer-approved response and return retention/access receipts",
            ],
            "not_delegated": (
                "No independent release of individual records, amendment acceptance, notice "
                "issuance or designation as covered entity"
            ),
            "security_vs_individual_access": (
                "Service permission authorizes a recovery operator to read a marker; it is not "
                "a decision granting an individual privacy request"
            ),
            "legal_review": {
                "actor": "AS-P003",
                "basis_date": "2026-10-01",
                "regulatory_edition": (
                    "2026 text used for training; changes during2027 require fresh review"
                ),
            },
            "prohibited_sanction_bases": [
                "Protected whistleblowing under164.502(j)",
                "Protected reporting under164.530(g)(2), applying160.316 conditions",
                "Good-faith complaint or participation in a proceeding",
            ],
        },
        deps=[accepted],
        upstream=[prior[3], prior[4]],
    )
    directory1 = put(
        "communication_directory",
        "SERVICE-RESPONSIBILITY-DIRECTORY",
        "2027-08-25T10:00:00+00:00",
        {
            "service": "SIM-RESTRICTED-HOSTING-01",
            "required_internal_recipients": [
                "AS-P003",
                "AS-P005",
                "AS-P006",
                "AS-P007",
                "AS-P008",
                "AS-P012",
                "AS-P013",
                "AS-P014",
            ],
            "channels": {
                "internal": "local://supplemental/responsibilities",
                "confidential_failsafe": "local://legal/protected-reporting",
                "external_concerns": "assurance@sableharbor.invalid",
            },
            "response_owner": "AS-P005",
            "legal_escalation": "AS-P003",
            "security_escalation": "AS-P008",
            "customers_receive": [
                "Service boundary",
                "Customer responsibilities",
                "Concern route",
                "Planned material changes",
            ],
            "contact_validation": (
                "Local delivery fixture only; .invalid is intentionally nonroutable and no "
                "external party was contacted"
            ),
        },
        deps=[privacy, doc1],
    )
    put(
        "communication_event",
        "AUGUST-INSTRUCTION-DELIVERY",
        "2027-08-25T11:00:00+00:00",
        {
            "instruction_id": "SUP-OPERATING-POLICY-2027",
            "instruction_version": 1,
            "audience": "NAMED_IMPLEMENTERS",
            "sender": "AS-P005",
            "required_recipients": [
                "AS-P003",
                "AS-P005",
                "AS-P006",
                "AS-P007",
                "AS-P008",
                "AS-P012",
                "AS-P013",
                "AS-P014",
            ],
            "delivery_receipts": [
                {
                    "recipient": p,
                    "channel": "local://supplemental/responsibilities",
                    "received_at": "2027-08-25T10:45:00+00:00",
                    "document_sha_bound": True,
                }
                for p in [
                    "AS-P003",
                    "AS-P005",
                    "AS-P006",
                    "AS-P007",
                    "AS-P008",
                    "AS-P012",
                    "AS-P013",
                    "AS-P014",
                ]
            ],
            "responsibility_change": (
                "New local supplement assigns service reporting, recovery, records and case "
                "duties; earlier enterprise-policy status unchanged"
            ),
        },
        deps=[directory1],
    )
    # Each entry inherits neither a generic waiver nor acceptance from the March intake.
    addr_refs = []
    specs = json.loads(
        (
            ctx["repository"]
            / "enterprise/ccf/assurance/review_data/addressable_specifications.json"
        ).read_bytes()
    )
    for i, (setting, values, environment, treatment) in enumerate(_settings(), 1):
        stamp = f"2027-08-26T{9 + (i - 1) // 6:02d}:{((i - 1) % 6) * 10:02d}:00+00:00"
        decision_at = stamp
        config_at = (datetime.fromisoformat(stamp) + timedelta(minutes=3)).isoformat()
        config = f"security_configuration/SETTING-{i:02d}-{setting}/1"
        entry = {
            "specification": specs[i - 1]["locator"],
            "source_label": specs[i - 1]["source_label"],
            "assessor": "AS-P008",
            "technical_implementer": "AS-P007",
            "legal_challenge": "AS-P003",
            "assessment": {
                "size_complexity_capability": (
                    "Named restricted-hosting local model with two synthetic marker resources "
                    "and three selected operators"
                ),
                "infrastructure": environment,
                "cost": (
                    "Local setting and receipt management fits existing named operators; no "
                    "unbudgeted deployment or real service purchase"
                ),
                "probability_and_criticality": (
                    "Exposure is low in a data-only disposable model; corresponding "
                    "confidentiality, integrity or availability impact would be material in a "
                    "real ePHI service and requires a future environmental review"
                ),
            },
            "decision": "IMPLEMENT_IN_LOCAL_MODEL"
            if i != 18
            else "IMPLEMENT_HUMAN_LOGOFF_AND_EQUIVALENT_HEADLESS_ALTERNATIVE",
            "reasoned_treatment": treatment,
            "planned_configuration_record": config,
            "equivalent_alternative": None
            if i != 18
            else {
                "why_desktop_logoff_inapplicable": (
                    "No interactive session exists for the headless service principal"
                ),
                "alternative": [
                    "900-second purpose-bound service credential",
                    "isolated process",
                    "default-deny resource permission",
                ],
                "equivalence_rationale": (
                    "Limits unattended use without inventing a desktop session; risk assessment"
                    " remains specific to the local headless resource"
                ),
            },
            "approval": {
                "decision_owner": "AS-P008",
                "challenge_owner": "AS-P003",
                "at": decision_at,
            },
            "previous_intake_status": (
                "March environmental decisions were missing; this new dated local decision is "
                "not retrospective acceptance"
            ),
        }
        addr_refs.append(
            put(
                "risk_decision",
                f"ENVIRONMENT-DECISION-{i:02d}",
                decision_at,
                entry,
                deps=[accepted],
                upstream=[
                    _upstream(ctx, side, "addressable", "addressable_candidate", f"SPEC-{i:02d}")
                ],
            )
        )
        config = put(
            "security_configuration",
            f"SETTING-{i:02d}-{setting}",
            config_at,
            {
                "setting_id": setting,
                "specification": specs[i - 1]["locator"],
                "service": "SIM-RESTRICTED-HOSTING-01",
                "operator": "AS-P007",
                "approved_by": "AS-P008",
                "approved_values": values,
                "observed_values": {
                    **values,
                    **(
                        {"configured_validator": "SEMANTIC_ONLY"}
                        if side == "B" and i in {20, 21}
                        else {"configured_validator": "SEMANTIC_AND_CONTENT_AUTHENTICITY"}
                        if i in {20, 21}
                        else {}
                    ),
                },
                "implementation_decision_original": addr_refs[-1],
                "activation_scope": "DISPOSABLE_LOCAL_OPERATING_MODEL",
                "applied_at": config_at,
                "verification_method": (
                    "Retained exact local setting map; actual selected "
                    "hash/authentication/recovery trials are separately recorded"
                ),
            },
            deps=[addr_refs[-1]],
        )
    if side == "B":
        put(
            "risk_decision",
            "SERVICE-LOGOFF-WAIVER-REQUEST",
            "2027-08-27T09:00:00+00:00",
            {
                "requester": "AS-P007",
                "request": (
                    "Reuse general risk exception instead of documenting the headless-service "
                    "assessment"
                ),
                "request_basis": "",
                "disposition": "REJECTED",
                "reviewer": "AS-P003",
                "reason": (
                    "Empty environment reasoning and generic waiver do not decide a security "
                    "implementation specification"
                ),
                "retained_prior_request": True,
            },
            deps=[addr_refs[17]],
        )
    put(
        "retention_register",
        "INITIAL-DOCUMENTATION-AVAILABILITY",
        "2027-08-28T09:00:00+00:00",
        {
            "operator": "AS-P014",
            "class_decision_owner": "AS-P003",
            "classes": {
                "SECURITY_POLICY_PROCEDURE": (
                    "Six-year later-of floor; current effective documents retained without "
                    "final release"
                ),
                "REQUIRED_SECURITY_ACTIVITY": (
                    "Six years from dated activity documentation creation"
                ),
                "DELEGATED_PRIVACY_DOCUMENTATION": (
                    "Six-year later-of floor for performed contractual customer functions; "
                    "customer keeps its own privacy obligations"
                ),
            },
            "implementer_access": [
                "AS-P003",
                "AS-P005",
                "AS-P006",
                "AS-P007",
                "AS-P008",
                "AS-P012",
                "AS-P013",
                "AS-P014",
            ],
            "retrievable_original_refs": [doc1, procedure, *addr_refs],
            "document_availability": "Exact originals remain retrievable in local CompanyStore",
            "scope_exclusion": (
                "No medical-record retention determination and no release of previous "
                "Legal-pending held records"
            ),
        },
        deps=[doc1, procedure, *addr_refs],
    )
    # Monthly operations: record underlying counts, concrete inputs and correction history.
    for month in range(9, 13):
        operation = put(
            "procedure_operation",
            f"REVIEW-2027-{month:02d}",
            f"2027-{month:02d}-02T10:00:00+00:00",
            {
                "trigger_id": f"DUE-2027-{month:02d}",
                "performer": "AS-P005",
                "due_at": f"2027-{month:02d}-03T17:00:00+00:00",
                "input_originals": [doc1, procedure, *addr_refs],
                "steps_performed": [1, 2, 3, 4, 5] if side == "A" or month != 10 else [1, 2, 4, 5],
                "retrieval_count": 24 if side == "A" or month != 10 else 0,
                "risk_decision_count": 22,
                "operator_statement": "Review complete",
                "factual_result": "Required originals resolved and retained"
                if side == "A" or month != 10
                else (
                    "Retention retrieval step not performed; operator completion statement "
                    "lacks that result"
                ),
                "result_owner": "AS-P005",
                "residual_issue": None
                if side == "A" or month != 10
                else "October required-original retrieval missing",
            },
            deps=[calendar_ref, *addr_refs],
        )
        if side == "B" and month == 10:
            challenge = put(
                "procedure_operation",
                "OCTOBER-REVIEW-CHALLENGE",
                "2027-10-05T10:00:00+00:00",
                {
                    "reviewer": "AS-P003",
                    "challenged_operator_statement": "Review complete",
                    "observation": (
                        "No October retained-original retrieval receipt; steps1,2,4,5 cannot "
                        "stand in for step3"
                    ),
                    "decision": "REOPEN",
                    "corrective_due_at": "2027-10-06T17:00:00+00:00",
                    "owner": "AS-P005",
                },
                deps=[operation],
            )
            put(
                "procedure_operation",
                "OCTOBER-RETRIEVAL-CORRECTION",
                "2027-10-06T10:00:00+00:00",
                {
                    "performer": "AS-P014",
                    "retrieved_exact_original_count": 24,
                    "corrective_action": "Perform omitted retrieval and return receipt to owner",
                    "original_due_at": "2027-10-03T17:00:00+00:00",
                    "late_original_requirement": True,
                    "period_gap_status": "OPEN_EFFECTIVENESS_REVIEW",
                    "later_success_does_not_erase_missed_due": True,
                },
                deps=[challenge],
            )
    permission = put(
        "identity_permission",
        "MARKER-SERVICE-PERMISSION-MATRIX",
        "2027-09-06T09:00:00+00:00",
        {
            "owner": "AS-P008",
            "model_policy": _policy(),
            "resource_inventory": {
                "marker-store": "Nonpersonal source fixture",
                "marker-recovery": "Permitted recovery copy",
            },
            "trust_boundaries": [
                "human/service credential issuance",
                "model receiving resource",
                "privileged operator elevation",
                "named marker recovery",
            ],
            "human_credential_proof": (
                "Local model MFA assertion, not an actual identity-provider login"
            ),
            "service_identity_purpose": (
                "Only recover named marker; no wildcard, unrelated records or interactive privilege"
            ),
            "permission_change_approval": "AS-P008 plus AS-P003 challenge",
            "full_enterprise_identity_population": "NOT_ASSERTED",
        },
        deps=[addr_refs[3], addr_refs[4]],
    )
    custody = put(
        "key_custody",
        "MODEL-KEY-01",
        "2027-09-06T10:00:00+00:00",
        {
            "key_id": "MODEL-KEY-01",
            "custodian": "AS-P008",
            "purpose": "Disposable marker-content verifier only",
            "fixture_locator": "fixtures/verifier-key.bin",
            "key_sha256": sha(key),
            "classification": "NONSECRET_SYNTHETIC_TEST_KEY",
            "custody_controls": {
                "file_mode": "0600",
                "directory_mode": "0700",
                "single_link": True,
            },
            "production_use": "PROHIBITED",
            "credential_lifecycle": [
                "Create local fixture",
                "Use scoped verifier",
                "Expire service permission on role/purpose end",
                "Retain fixture for reproducible training only",
            ],
            "private_material_in_receipt": False,
        },
        deps=[permission],
    )
    accessrefs = []
    common = {
        "issuer": _policy()["issuer"],
        "audience": _policy()["audience"],
        "expires_at": "2027-09-07T09:15:00+00:00",
    }
    requests = [
        (
            "HUMAN-READ",
            {
                **common,
                "principal": "AS-P007",
                "resource": "marker-store",
                "operation": "read",
                "mfa": True,
            },
        ),
        (
            "SERVICE-RECOVERY",
            {
                **common,
                "principal": "SIM-SERVICE-RECOVERY-01",
                "resource": "marker-recovery",
                "operation": "recover",
            },
        ),
        (
            "UNKNOWN-PRINCIPAL",
            {**common, "principal": "SIM-UNKNOWN", "resource": "marker-store", "operation": "read"},
        ),
        (
            "WRONG-ISSUER",
            {
                **common,
                "issuer": "urn:untrusted",
                "principal": "AS-P007",
                "resource": "marker-store",
                "operation": "read",
                "mfa": True,
            },
        ),
        (
            "WRONG-AUDIENCE",
            {
                **common,
                "audience": "urn:other-service",
                "principal": "AS-P007",
                "resource": "marker-store",
                "operation": "read",
                "mfa": True,
            },
        ),
        (
            "SERVICE-WRONG-RESOURCE",
            {
                **common,
                "principal": "SIM-SERVICE-RECOVERY-01",
                "resource": "marker-store",
                "operation": "read",
            },
        ),
        (
            "EXPIRED",
            {
                **common,
                "expires_at": "2027-09-07T08:59:00+00:00",
                "principal": "AS-P007",
                "resource": "marker-store",
                "operation": "read",
                "mfa": True,
            },
        ),
        (
            "UNAPPROVED-PRIVILEGE",
            {
                **common,
                "principal": "AS-P007",
                "resource": "marker-store",
                "operation": "read",
                "mfa": True,
                "privileged": True,
            },
        ),
        (
            "APPROVED-PRIVILEGE",
            {
                **common,
                "principal": "AS-P007",
                "resource": "marker-store",
                "operation": "read",
                "mfa": True,
                "privileged": True,
                "approval": "AS-P008-SUP-ELEVATION-01",
            },
        ),
    ]
    for i, (name, req) in enumerate(requests):
        at = f"2027-09-07T09:{i:02d}:00+00:00"
        accessrefs.append(
            put(
                "access_operation",
                name,
                at,
                {
                    "operator": "AS-P007",
                    "operation_scope": "ACTUALLY_EXECUTED_DISPOSABLE_POLICY_MODEL",
                    **access_decision(req, _policy(), at=at),
                },
                deps=[permission, custody],
            )
        )
    intake = put(
        "incident_intake",
        "ATTEMPTED-UNAUTHORIZED-ACCESS-01",
        "2027-09-07T10:00:00+00:00",
        {
            "receiver": "AS-P008",
            "received_at": "2027-09-07T09:30:00+00:00",
            "reported_by": "AS-P007",
            "intake_type": "ATTEMPTED_UNAUTHORIZED_ACCESS",
            "succeeded": False,
            "source_operation_ids": [
                "UNKNOWN-PRINCIPAL",
                "WRONG-ISSUER",
                "WRONG-AUDIENCE",
                "SERVICE-WRONG-RESOURCE",
                "EXPIRED",
                "UNAPPROVED-PRIVILEGE",
            ],
            "triage": (
                "Preserve denial reasons; confirm no published marker bytes and inspect "
                "configuration"
            ),
            "interference_or_data_change": False,
            "response": (
                "No authorization relaxation; preserve model event and notify service/security "
                "owner"
            ),
            "security_incident_definition_includes_attempts": True,
        },
        deps=accessrefs,
    )
    recovery = put(
        "recovery_operation",
        "SEPTEMBER-MARKER-RECOVERY",
        "2027-09-08T10:00:00+00:00",
        {
            "operator": "AS-P007",
            "authorization_operation": "HUMAN-READ",
            "source_fixture": "fixtures/marker-original.json",
            "recovered_fixture": "fixtures/recovered-marker.json",
            "source_sha256": sha(marker),
            "recovered_sha256": sha(marker),
            "exact_bytes": True,
            "usable_JSON": json.loads(marker),
            "authorized_retrieval_decision": "ALLOW",
            "availability_result": (
                "Accessible and usable for permitted operator in the local model"
            ),
            "individual_privacy_request_result": "NOT_DECIDED_BY_RECOVERY_PERMISSION",
        },
        deps=[permission, intake],
    )
    integrityauth = put(
        "integrity_operation",
        "ALTERATION-TEST-AUTHORITY",
        "2027-09-09T09:00:00+00:00",
        {
            "authorizer": "AS-P008",
            "challenger": "AS-P003",
            "operator": "AS-P007",
            "permitted_action": (
                "Change batch_total120 to121 in data-only disposable receiving fixture; "
                "preserve original"
            ),
            "original_fixture": "fixtures/marker-original.json",
            "altered_fixture": "fixtures/marker-altered.json",
            "live_system_or_real_PHI": "NONE",
            "expected_authenticator": tag,
            "expected_source_sha256": sha(marker),
            "test_scope": [
                "Receiving-copy modification",
                "Same altered bytes presented as a transfer receipt",
            ],
            "response_requirement": (
                "Reject publication and preserve incident when authenticator differs"
            ),
        },
        deps=[custody],
    )
    trials = []
    for i, name in enumerate(["RECEIVING-COPY-ALTERATION", "TRANSFER-ALTERATION"]):
        trials.append(
            put(
                "integrity_operation",
                name,
                f"2027-09-09T10:{i * 10:02d}:00+00:00",
                {
                    "operator": "AS-P007",
                    "executed_scope": "ACTUAL_LOCAL_MARKER_VERIFIER",
                    "expected_authenticator_custody": "MODEL-KEY-01",
                    **integrity_trial(marker, altered, key, tag, semantic_only=side == "B"),
                },
                deps=[integrityauth],
            )
        )
    if side == "B":
        challenge = put(
            "integrity_operation",
            "AUTHENTICITY-CHALLENGE",
            "2027-09-10T09:00:00+00:00",
            {
                "reviewer": "AS-P008",
                "observation": (
                    "Changed numeric marker is valid business data but has an unauthorized "
                    "content authenticator; receiving and transfer validators accepted it "
                    "because they only checked shape/value"
                ),
                "root_cause": "SEMANTIC_ONLY_VALIDATOR_CONFIGURED",
                "response": (
                    "Quarantine both derived test copies, revise configuration to verify "
                    "expected protected authenticator before publication"
                ),
                "earlier_acceptance_retained": True,
            },
            deps=trials,
        )
        corrected = []
        for i, setting in [(20, "CONTENT_AUTHENTICITY"), (21, "TRANSFER_INTEGRITY")]:
            corrected.append(
                put(
                    "security_configuration",
                    f"SETTING-{i:02d}-{setting}",
                    "2027-09-10T09:30:00+00:00",
                    {
                        "operator": "AS-P007",
                        "approved_by": "AS-P008",
                        "change": (
                            "Replace semantic-only receiving/transfer"
                            " validator with approved content "
                            "authenticator"
                        ),
                        "configured_validator": "SEMANTIC_AND_CONTENT_AUTHENTICITY",
                        "superseded_configuration_retained": True,
                        "earlier_runtime_receipts_retained": True,
                    },
                    deps=[challenge, addr_refs[i - 1]],
                )
            )
        put(
            "integrity_operation",
            "AUTHENTICITY-RETEST",
            "2027-09-10T10:00:00+00:00",
            {
                "operator": "AS-P007",
                "reviewer": "AS-P008",
                "change": "Enable content authenticator verification",
                "previous_scope_gap": "Receiving/transfer acceptance onSep9 retained for follow-up",
                **integrity_trial(marker, altered, key, tag),
            },
            deps=[challenge, *corrected],
        )
    put(
        "incident_intake",
        "ALTERED-MARKER-RESPONSE",
        "2027-09-10T11:00:00+00:00",
        {
            "receiver": "AS-P008",
            "type": "APPROVED_TEST_UNAUTHORIZED_ALTERATION",
            "receiving_and_transfer_trials": trials,
            "handling": "QUARANTINE_TEST_COPIES",
            "original_preserved": True,
            "followup": "Verify current authenticator guard and retain earlier validator lapse"
            if side == "B"
            else "No altered test payload published; original retained",
            "real_personal_data_present": False,
        },
        deps=trials,
    )
    external = put(
        "communication_event",
        "CUSTOMER-CONCERN-SEP",
        "2027-09-14T10:00:00+00:00",
        {
            "received_via": "assurance@sableharbor.invalid",
            "sender_persona": "SIM-CUSTOMER-SERVICE-OWNER-01",
            "received_at": "2027-09-14T09:00:00+00:00",
            "concern": (
                "Who owns attempted-access notifications and marker recovery responsibility "
                "after the local supplement?"
            ),
            "response_owner": "AS-P005",
            "escalation_to": "AS-P003",
            "response_at": "2027-09-14T09:45:00+00:00",
            "response": (
                "Security attempts route to DanaWest; recovery requires named authorized "
                "operators; individual privacy requests go to customer privacy owner for "
                "determination"
            ),
            "response_audience": ["SIM-CUSTOMER-SERVICE-OWNER-01", "AS-P007", "AS-P008"],
            "customer_confirmation": (
                "Local synthetic concern fixture acknowledged; no message sent to a real customer"
            ),
            "owner_update": (
                "Maintain public-facing role/contact template and internal directory together"
            ),
        },
        deps=[directory1, privacy],
    )
    put(
        "privacy_responsibility",
        "CONCERN-AND-NOTICE-COORDINATION",
        "2027-09-14T11:00:00+00:00",
        {
            "actor": "AS-P003",
            "customer_retained_notice_authority": True,
            "issue": (
                "Local reporting/recovery responsibilities changed; customer must decide "
                "whether its notice or communicated practices require change"
            ),
            "service_action": (
                "Deliver accurate changed responsibility description to synthetic "
                "customer-owner queue"
            ),
            "service_cannot_issue_customer_notice": True,
            "customer_decision": "PENDING_CUSTOMER_NOTICE_ASSESSMENT",
            "nonretaliation": (
                "Preserve complaint, restrict case access and forbid corrective action because "
                "a person reports concern"
            ),
            "regulatory_role_basis": (
                "Direct security duties plus only expressly delegated privacy steps;164.530 "
                "covered-entity duties are not blanket obligations imposed on every business "
                "associate"
            ),
        },
        deps=[external, privacy],
    )
    # Independent asset/work order/movement populations for local physical scope.
    physicalrefs = [
        _upstream(ctx, side, "physical", "site_zoning", x) for x in ["RNO-CAGE-A", "BOI-CAGE-R"]
    ]
    inventory = put(
        "workstation_inventory",
        "SELECTED-WORKSTATION-MEDIA-POPULATION",
        "2027-09-21T09:00:00+00:00",
        {
            "registrar": "AS-P012",
            "approved_by": "AS-P008",
            "resources": [
                {
                    "asset_id": "SIM-WS-RECORDS-01",
                    "serial": "MODEL-WS-0001",
                    "assigned_to": "AS-P014",
                    "location": "RNO-CAGE-A",
                    "use": "Restricted marker-handling workstation",
                    "workstation_guard": [
                        "Five-minute screen lock",
                        "Permitted local marker store only",
                        "No unattended public access",
                    ],
                },
                {
                    "asset_id": "SIM-MEDIA-RECOVERY-01",
                    "serial": "MODEL-MEDIA-0001",
                    "custodian": "AS-P012",
                    "location": "RNO-CAGE-A",
                    "use": "Removable nonpersonal marker copy",
                },
            ],
            "source_of_population": (
                "Local assignment registry created for this supplemental program; separate from"
                " movement and maintenance ledgers"
            ),
            "valid_from": "2027-09-21",
            "scope_exclusion": "No full employee-workstation or provider-equipment census",
        },
        deps=[accepted],
        upstream=physicalrefs,
    )
    maintenance = put(
        "facility_maintenance",
        "RNO-SECURITY-LATCH-REPAIR",
        "2027-09-22T10:00:00+00:00",
        {
            "work_order": "SUP-FAC-WO-01",
            "zone": "RNO-CAGE-A",
            "resource": "CAGE-LATCH-01",
            "reported_condition": "Latch fails to fully seat in selected local-model cage door",
            "approved_by": "AS-P008",
            "technician": "AS-P012",
            "start": "2027-09-22T09:00:00+00:00",
            "finish": "2027-09-22T09:30:00+00:00",
            "temporary_security": (
                "Named escort attends open-cage interval; no provider-perimeter assertion"
            ),
            "replacement": "Adjust local modeled latch and test closure",
            "verified_by": "AS-P007",
            "verification": (
                "Three consecutive closure/check cycles in the selected local physical model"
            ),
            "record_class": "SECURITY_RELATED_FACILITY_MAINTENANCE",
        },
        deps=[inventory],
    )
    moveplan = put(
        "media_movement",
        "MOVEMENT-REQUEST-01",
        "2027-09-23T09:00:00+00:00",
        {
            "requester": "AS-P014",
            "approver": "AS-P008",
            "assets": ["SIM-WS-RECORDS-01", "SIM-MEDIA-RECOVERY-01"],
            "source": "RNO-CAGE-A",
            "destination": "BOI-CAGE-R",
            "reason": "Selected recovery-workstation continuity and marker media recovery exercise",
            "scheduled_at": "2027-09-24T10:00:00+00:00",
            "requirement": (
                "Before release retrieve exact readable copy and retain destination/custodian "
                "receipt"
            ),
        },
        deps=[inventory, maintenance],
    )
    if side == "B":
        put(
            "media_movement",
            "MOVEMENT-RELEASE-ATTEMPT-01",
            "2027-09-24T09:00:00+00:00",
            {
                "operator": "AS-P012",
                "requested_release": "SIM-MEDIA-RECOVERY-01",
                "copy_receipt": "MISSING",
                "decision": "DENY_RELEASE",
                "actual_departure": False,
                "reason": "Exact retrievable copy not established before data-bearing movement",
                "owner": "AS-P014",
            },
            deps=[moveplan],
        )
    precopy = put(
        "recovery_operation",
        "PRE-MOVEMENT-EXACT-COPY-01",
        "2027-09-24T09:30:00+00:00",
        {
            "operator": "AS-P014",
            "authorization_owner": "AS-P008",
            "assets": ["SIM-WS-RECORDS-01", "SIM-MEDIA-RECOVERY-01"],
            "source_fixture": "fixtures/marker-original.json",
            "retrieved_fixture": "fixtures/pre-movement-marker.json",
            "source_sha256": sha(marker),
            "retrieved_sha256": sha(marker),
            "retrieved_before_departure": True,
            "retrieval_at": "2027-09-24T09:25:00+00:00",
            "parse_result": json.loads(marker),
            "exact_bytes": True,
            "permitted_local_model_retrieval": True,
        },
        deps=[moveplan, recovery],
    )
    moved = put(
        "media_movement",
        "MOVEMENT-CUSTODY-01",
        "2027-09-24T12:00:00+00:00",
        {
            "operator": "AS-P012",
            "assets": [
                {"asset_id": "SIM-WS-RECORDS-01", "serial": "MODEL-WS-0001"},
                {"asset_id": "SIM-MEDIA-RECOVERY-01", "serial": "MODEL-MEDIA-0001"},
            ],
            "source": "RNO-CAGE-A",
            "destination": "BOI-CAGE-R",
            "departed_at": "2027-09-24T10:00:00+00:00",
            "received_at": "2027-09-24T11:30:00+00:00",
            "source_custodian": "AS-P012",
            "destination_custodian": "AS-P012",
            "exact_copy_receipt_id": "PRE-MOVEMENT-EXACT-COPY-01",
            "escort": "AS-P012",
            "transport": "Fictional local-model custody transition; no actual hardware moved",
            "status": "RECEIVED",
            "reconcile_to_assignment_registry": True,
        },
        deps=[precopy],
    )
    reuse = put(
        "media_movement",
        "MEDIA-REUSE-AUTHORITY-01",
        "2027-10-23T09:00:00+00:00",
        {
            "requester": "AS-P012",
            "approver": "AS-P008",
            "asset_id": "SIM-MEDIA-RECOVERY-01",
            "preserved_before_reuse_fixture": "fixtures/pre-movement-marker.json",
            "preserved_sha256": sha(marker),
            "sanitization_scope": "Separate disposable working copy only",
            "source_originals_untouched": True,
            "reuse_purpose": "Blank nonpersonal test-media model",
            "required_receipt": (
                "Verify working file contains zero old marker bytes before reassignment"
            ),
        },
        deps=[moved],
    )
    put(
        "media_movement",
        "MEDIA-REUSE-RECEIPT-01",
        "2027-10-23T10:00:00+00:00",
        {
            "operator": "AS-P012",
            "verifier": "AS-P014",
            "asset_id": "SIM-MEDIA-RECOVERY-01",
            "working_fixture": "fixtures/reused-media.bin",
            "before_sha256": sha(marker),
            "after_size": 0,
            "after_sha256": sha(b""),
            "old_marker_present": False,
            "preserved_copy_retrievable": True,
            "new_custodian": "AS-P012",
            "new_location": "BOI-CAGE-R",
            "disposition": "REUSED_LOCAL_DISPOSABLE_WORKING_FILE",
        },
        deps=[reuse],
    )
    # Enforcement follows facts about the new instruction and separate protected-report review.
    report = put(
        "workforce_case",
        "ER-2027-REPORT-01",
        "2027-09-16T09:00:00+00:00",
        {
            "case_id": "SUP-ER-2027-01",
            "reported_by": "AS-P013",
            "received_by": "AS-P006",
            "confidential_channel": "local://legal/protected-reporting",
            "concern": (
                "OperatorAS-P007 attempted unapproved elevated read during local marker test "
                "despite explicit two-person elevated-action requirement"
            ),
            "named_subject": "AS-P007",
            "protected_reporting_review": (
                "Good-faith report; neither reporting nor participation can support an adverse "
                "sanction"
            ),
            "case_access": ["AS-P006", "AS-P003", "AS-P008"],
            "data_kind": "Fictional nonpersonal employee-relations case; no real allegation",
        },
        deps=[doc1, accessrefs[7]],
    )
    investigation = put(
        "workforce_case",
        "ER-2027-FACTS-01",
        "2027-09-17T10:00:00+00:00",
        {
            "investigator": "AS-P008",
            "case_owner": "AS-P006",
            "subject_response": (
                "Acknowledged requesting privileged read before approval; assumed service-owner"
                " title sufficed"
            ),
            "corroboration": [
                "UNAPPROVED-PRIVILEGE denial receipt",
                "August instruction delivery",
                "Named permission matrix",
            ],
            "substantiated_facts": (
                "Unapproved elevated request made and denied; no marker disclosure established"
            ),
            "rule_breached": "Supplement requires approval before elevated read",
            "scope": "Observed selected operator event, not an allegation about all workforce",
            "conclusion": (
                "Security-procedure noncompliance established; good-faith reporter not culpable"
            ),
        },
        deps=[report, permission, accessrefs[7]],
    )
    if side == "B":
        proposed = put(
            "workforce_case",
            "ER-2027-REPORTER-PROPOSAL",
            "2027-09-18T09:00:00+00:00",
            {
                "proposed_by": "AS-P007",
                "subject": "AS-P013",
                "proposed_action": (
                    "Remove reporter from supplier workflow because the report delayed the exercise"
                ),
                "case_owner": "AS-P006",
                "decision": "PROPOSAL_PENDING_LEGAL_REVIEW",
                "action_applied": False,
            },
            deps=[investigation],
        )
        put(
            "workforce_case",
            "ER-2027-PROTECTED-REPORT-REVIEW",
            "2027-09-18T10:00:00+00:00",
            {
                "reviewer": "AS-P003",
                "subject": "AS-P013",
                "decision": "REJECT_ADVERSE_ACTION",
                "reason": (
                    "Good-faith reporting/participation is protected; no independently "
                    "substantiated misconduct by reporter"
                ),
                "protected_disclosures_considered": ["164.502(j)", "164.530(g)(2)", "160.316"],
                "action_applied": False,
                "proposal_original_retained": True,
            },
            deps=[proposed],
        )
    sanction_date = "2027-09-19" if side == "A" else "2027-09-28"
    sanction = put(
        "workforce_case",
        "ER-2027-CORRECTIVE-DECISION",
        sanction_date + "T10:00:00+00:00",
        {
            "decision_owner": "AS-P006",
            "legal_reviewer": "AS-P003",
            "technical_restriction_owner": "AS-P008",
            "subject": "AS-P007",
            "case_id": "SUP-ER-2027-01",
            "substantiated_violation": (
                "Unapproved privileged request after receiving explicit requirement"
            ),
            "considerations": {
                "impact": "Denied request; no demonstrated disclosure",
                "intent": "Operator mistaken assumption rather than evidence of exfiltration",
                "proportionality": (
                    "Documented coaching, approval-practice retraining and temporary "
                    "second-person supervision"
                ),
                "protected_reporting": "Exclude reporter conduct from sanction basis",
            },
            "sanction": (
                "Written corrective coaching and ten-day restriction on self-initiated "
                "privileged sessions"
            ),
            "effective_at": sanction_date + "T10:30:00+00:00",
            "restriction_expiry": ("2027-09-29" if side == "A" else "2027-10-08")
            + "T10:30:00+00:00",
            "decision_target": "2027-09-19T17:00:00+00:00",
            "enforcement_owner": "AS-P008",
            "enforcement_record": (
                "Local elevated-session policy set to require second-person approval; subject "
                "acknowledges coaching"
            ),
            "reporter_adverse_action": False,
            "timeliness_note": "Decision within local target"
            if side == "A"
            else "Decision nine days beyond local target; preserve delay as case exception",
        },
        deps=[investigation],
    )
    restriction_end = ("2027-09-29" if side == "A" else "2027-10-08") + "T10:30:00+00:00"
    enforced_policy = _policy()
    enforced_policy["temporary_restrictions"] = {
        "AS-P007": {
            "valid_from": sanction_date + "T10:30:00+00:00",
            "valid_until": restriction_end,
            "permitted_peer_initiators": ["AS-P008"],
            "case_id": "SUP-ER-2027-01",
        }
    }
    enforced_policy["privilege_approvals"] = {
        "AS-P008-SUP-SUPERVISED-01": {
            "principal": "AS-P007",
            "resource": "marker-store",
            "operation": "read",
            "approved_by": "AS-P008",
            "challenged_by": "AS-P003",
            "valid_from": sanction_date + "T10:30:00+00:00",
            "valid_until": restriction_end,
        }
    }
    applied_restriction = put(
        "identity_permission",
        "MARKER-SERVICE-PERMISSION-MATRIX",
        sanction_date + "T10:30:00+00:00",
        {
            "operator": "AS-P008",
            "legal_reviewer": "AS-P003",
            "reason": (
                "Enforce the proportionate local case decision through "
                "a temporary peer-initiation restriction"
            ),
            "case_id": "SUP-ER-2027-01",
            "model_policy": enforced_policy,
            "subject_not_prohibited_from_reporting": True,
            "reporter_permission_unchanged": "AS-P013",
        },
        deps=[sanction, permission],
    )
    enforced_trials = []
    for i, initiator in enumerate(["AS-P007", "AS-P008"]):
        at = sanction_date + f"T11:{i * 10:02d}:00+00:00"
        request = {
            "principal": "AS-P007",
            "issuer": enforced_policy["issuer"],
            "audience": enforced_policy["audience"],
            "resource": "marker-store",
            "operation": "read",
            "mfa": True,
            "privileged": True,
            "approval": "AS-P008-SUP-SUPERVISED-01",
            "initiated_by": initiator,
            "expires_at": sanction_date + "T11:30:00+00:00",
        }
        enforced_trials.append(
            put(
                "access_operation",
                "CORRECTIVE-RESTRICTION-" + ("SELF" if i == 0 else "PEER"),
                at,
                {
                    "operator": "AS-P007",
                    "observer": "AS-P008",
                    "case_id": "SUP-ER-2027-01",
                    "scope": (
                        "Actual disposable access-policy model trial after restriction activation"
                    ),
                    **access_decision(request, enforced_policy, at=at),
                },
                deps=[applied_restriction],
            )
        )
    follow = put(
        "workforce_case",
        "ER-2027-FOLLOWUP",
        ("2027-09-30" if side == "A" else "2027-10-09") + "T10:00:00+00:00",
        {
            "followup_owner": "AS-P006",
            "technical_observer": "AS-P008",
            "subject": "AS-P007",
            "coaching_completed": True,
            "new_approved_exercise": (
                "Subject submits purpose/resource request and obtains separate authorization "
                "before elevated read"
            ),
            "protected_reporter_followup": (
                "AS-P013 confirms no loss of supplier responsibility or adverse action from "
                "reporting"
            ),
            "case_status": "CLOSED_ACTIONS_COMPLETED"
            if side == "A"
            else "ACTIONS_COMPLETED_LATE_EFFECTIVENESS_REVIEW_OPEN",
            "delay_not_erased": side == "B",
        },
        deps=[sanction, applied_restriction, *enforced_trials],
    )
    put(
        "responsibility_feedback",
        "TECHNOLOGY-RESPONSIBILITY-CHECKIN",
        "2027-10-12T10:00:00+00:00",
        {
            "participant": "AS-P007",
            "manager": "AS-P001",
            "case_admin": "AS-P006",
            "format": "How is work going; what is next; how can support help?",
            "discussion": {
                "responsibility": (
                    "Obtain elevated-action approval and preserve denial/concern records"
                ),
                "what_happened": (
                    "Owner title did not authorize unapproved request; coaching now includes "
                    "two-person request practice"
                ),
                "next_step": "Make approval path visible in service work instructions",
                "pressure": (
                    "Exercise schedule does not justify bypassing security owner or penalizing "
                    "good-faith reporting"
                ),
            },
            "feedback_from_subject": (
                "Approval routing is clearer; asks to shorten the request form while preserving"
                " independent approver"
            ),
            "reward_and_pressure_review": (
                "No throughput reward for bypasses or report suppression; no forced rank or "
                "surprise annual performance file"
            ),
            "followup_owner": "AS-P001",
            "next_check": "2027-11-12",
            "case_link": "SUP-ER-2027-01",
        },
        deps=[follow],
    )
    # A separately approved revision triggers delivery/contact/notice coordination.
    doc2 = put(
        "policy_document",
        "SUP-OPERATING-POLICY-2027",
        "2027-11-01T09:00:00+00:00",
        {
            "document_number": "SUP-OPERATING-POLICY-2027",
            "title": "Restricted-hosting local responsibilities, reporting and documentation",
            "owner": "AS-P003",
            "approval": {
                "approver": "P001",
                "decision": "APPROVED_LOCAL_REVISION",
                "approved_at": "2027-11-01T08:00:00+00:00",
            },
            "effective_at": "2027-11-02T00:00:00+00:00",
            "supersedes_local_version": 1,
            "change": (
                "Records operator receives direct concern-preservation duty; external template "
                "gives updated concern address and customer-retained privacy responsibilities"
            ),
            "policy_text": [
                (
                    "AS-P014 preserves concern records and returns exact-copy receipt to "
                    "service/security owner."
                ),
                (
                    "AS-P005 operates the verified external concern contact; Legal routes "
                    "individual requests to customer owner."
                ),
                (
                    "All original security/retention and protected-reporting requirements "
                    "continue unchanged."
                ),
            ],
            "required_audience": [
                "AS-P003",
                "AS-P005",
                "AS-P006",
                "AS-P007",
                "AS-P008",
                "AS-P012",
                "AS-P013",
                "AS-P014",
            ],
            "prior_enterprise_policy": (
                "2026 future/pending status unchanged; this revision supersedes only this local"
                " supplement"
            ),
        },
        deps=[doc1, external],
    )
    directory2 = put(
        "communication_directory",
        "SERVICE-RESPONSIBILITY-DIRECTORY",
        "2027-11-01T10:00:00+00:00",
        {
            "required_internal_recipients": [
                "AS-P003",
                "AS-P005",
                "AS-P006",
                "AS-P007",
                "AS-P008",
                "AS-P012",
                "AS-P013",
                "AS-P014",
            ],
            "external_concern_address": "assurance@sableharbor.invalid",
            "template_address": "assurance@sableharbor.invalid"
            if side == "A"
            else "legacy-queue@sableharbor.invalid",
            "responsibility_owner": "AS-P014",
            "source_of_contact": "Verified local directory; .invalid contact is fixture only",
            "template_validation": "Matches current local directory"
            if side == "A"
            else "Template still points to retired local queue; directory itself changed",
        },
        deps=[directory1, doc2],
    )
    delivered = ["AS-P003", "AS-P005", "AS-P006", "AS-P007", "AS-P008", "AS-P012", "AS-P013"] + (
        ["AS-P014"] if side == "A" else []
    )
    delivery = put(
        "communication_event",
        "NOVEMBER-REVISION-DELIVERY",
        "2027-11-01T11:00:00+00:00",
        {
            "sender": "AS-P005",
            "revision": 2,
            "required_recipients": [
                "AS-P003",
                "AS-P005",
                "AS-P006",
                "AS-P007",
                "AS-P008",
                "AS-P012",
                "AS-P013",
                "AS-P014",
            ],
            "delivery_receipts": [
                {"recipient": p, "received_at": "2027-11-01T10:45:00+00:00", "document_version": 2}
                for p in delivered
            ],
            "due_at": "2027-11-02T00:00:00+00:00",
            "external_template_contact": "assurance@sableharbor.invalid"
            if side == "A"
            else "legacy-queue@sableharbor.invalid",
            "recipient_reconciliation": "Eight of eight"
            if side == "A"
            else "Seven of eight; records owner lacks receipt",
        },
        deps=[directory2],
    )
    if side == "B":
        challenge = put(
            "communication_event",
            "NOVEMBER-COMMUNICATION-CHALLENGE",
            "2027-11-03T09:00:00+00:00",
            {
                "reviewer": "AS-P003",
                "missing_recipient": "AS-P014",
                "stale_contact": "legacy-queue@sableharbor.invalid",
                "changed_responsibility": (
                    "Records owner must preserve concern records but did not receive revision "
                    "before effective date"
                ),
                "external_concern": (
                    "Local customer fixture tried retired queue and received no receipt"
                ),
                "action": (
                    "Deliver revision, correct template, route captured failed concern and "
                    "retain earlier missed interval"
                ),
                "owner": "AS-P005",
            },
            deps=[delivery],
        )
        put(
            "communication_event",
            "NOVEMBER-COMMUNICATION-CORRECTION",
            "2027-11-03T10:00:00+00:00",
            {
                "sender": "AS-P005",
                "late_recipient": "AS-P014",
                "received_at": "2027-11-03T09:45:00+00:00",
                "corrected_contact": "assurance@sableharbor.invalid",
                "failed_concern_recovered": True,
                "response_audience": ["SIM-CUSTOMER-SERVICE-OWNER-01", "AS-P014", "AS-P008"],
                "owner_acknowledgement": "Records preservation role understood",
                "original_effective_date": "2027-11-02T00:00:00+00:00",
                "earlier_gap_status": "OPEN_MONITORING",
            },
            deps=[challenge],
        )
    put(
        "privacy_responsibility",
        "NOVEMBER-NOTICE-COORDINATION",
        "2027-11-04T10:00:00+00:00",
        {
            "coordinator": "AS-P003",
            "customer_contract": "SIM-BAA-CUST-01",
            "service_responsibility_change": (
                "Records preservation and concern-routing contact revision"
            ),
            "sent_to_persona": "SIM-CUSTOMER-SERVICE-OWNER-01",
            "customer_notice_decision": (
                "Customer retains assessment/authorization; receipt of service summary does not"
                " prove customer issued any revised notice"
            ),
            "customer_notice_issuance": "NOT_ESTABLISHED",
            "direct_service_action": (
                "Preserve delivered summary and concern receipts; no independent "
                "individual-rights decision"
            ),
            "reporting_protection": "No penalty for raising failed-contact concern",
        },
        deps=[doc2, privacy],
    )
    retention = put(
        "retention_register",
        "NOVEMBER-RETENTION-INDEX",
        "2027-11-05T10:00:00+00:00",
        {
            "operator": "AS-P014",
            "reviewer": "AS-P003",
            "required_records": [
                {
                    "id": "SUP-OPERATING-POLICY-2027-v1",
                    "class": "SECURITY_POLICY_PROCEDURE",
                    **retention_decision(
                        "2027-08-24", "2027-11-01", current=False, requested="2028-01-02"
                    ),
                },
                {
                    "id": "SUP-OPERATING-POLICY-2027-v2",
                    "class": "SECURITY_POLICY_PROCEDURE",
                    **retention_decision("2027-11-01", None, current=True, requested="2035-01-02"),
                },
                {
                    "id": "SUP-MONTHLY-OPERATING-REVIEW",
                    "class": "SECURITY_POLICY_PROCEDURE",
                    **retention_decision("2027-08-24", None, current=True, requested="2028-01-02"),
                },
                {
                    "id": "ATTEMPTED-UNAUTHORIZED-ACCESS-01",
                    "class": "REQUIRED_SECURITY_ACTIVITY",
                    **retention_decision("2027-09-07", None, current=False, requested="2028-01-02"),
                },
                {
                    "id": "CUSTOMER-CONCERN-SEP",
                    "class": "DELEGATED_PRIVACY_DOCUMENTATION",
                    **retention_decision("2027-09-14", None, current=False, requested="2028-01-02"),
                },
                {
                    "id": "RNO-SECURITY-LATCH-REPAIR",
                    "class": "REQUIRED_SECURITY_ACTIVITY",
                    **retention_decision("2027-09-22", None, current=False, requested="2028-01-02"),
                },
            ],
            "superseded_original_retrieval": {
                "id": "SUP-OPERATING-POLICY-2027-v1",
                "exact_original_ref": doc1,
                "retrieved": True,
            },
            "earlier_held_records": (
                "Existing Legal-pending hold and retention-classification sources remain "
                "retained and unresolved; not released by local supplement"
            ),
        },
        deps=[doc1, doc2, procedure, intake, maintenance, external],
    )
    put(
        "retention_register",
        "PREMATURE-DISPOSITION-ATTEMPT",
        "2027-11-06T10:00:00+00:00",
        {
            "requester": "AS-P007",
            "requested_record": "SUP-OPERATING-POLICY-2027-v1",
            "workflow": "Evaluate local disposal eligibility before operator approval",
            "reviewer": "AS-P014",
            **retention_decision("2027-08-24", "2027-11-01", current=False, requested="2028-01-02"),
            "superseded_copy_still_retrievable": True,
            "workflow_action": "DENY_BEFORE_ANY_FILE_DELETE",
        },
        deps=[retention],
    )
    history = []
    for family in [
        "policy",
        "procedure",
        "addressable",
        "conduct",
        "physical",
        "transfer",
        "rights",
        "retention",
        "integrity",
        "phi",
    ]:
        history.extend(ctx["originals"][family][side].values())
    put(
        "period_register",
        "2027-LOCAL-CHANNEL-CLOSURE",
        "2028-01-02T10:00:00+00:00",
        {
            "owner": "AS-P005",
            "reviewer": "AS-P003",
            "captured_period": {
                "start": "2027-01-01T00:00:00+00:00",
                "end_exclusive": "2028-01-01T00:00:00+00:00",
            },
            "review_completed_after_period": True,
            "monthly_status": [
                {
                    "month": f"2027-{m:02d}",
                    "local_supplement_status": "NOT_EFFECTIVE"
                    if m < 8
                    else "EFFECTIVE_AUG25_PARTIAL_MONTH"
                    if m == 8
                    else "OPERATING_DECLARED_LOCAL_CHANNELS",
                }
                for m in range(1, 13)
            ],
            "channels": {
                "scheduled_operating_reviews": {
                    "expected": 4,
                    "ids": [f"DUE-2027-{m:02d}" for m in range(9, 13)],
                },
                "security_model_access_trials": {
                    "expected": 9,
                    "scope": "Declared local trial requests; no production login census",
                },
                "corrective_access_trials": {
                    "expected": 2,
                    "ids": ["CORRECTIVE-RESTRICTION-SELF", "CORRECTIVE-RESTRICTION-PEER"],
                },
                "workforce_case": {
                    "expected": 1,
                    "ids": ["SUP-ER-2027-01"],
                    "scope": (
                        "New local case channel only; not enterprise employee-relations census"
                    ),
                },
                "data_bearing_movement": {"expected": 1, "ids": ["MOVEMENT-CUSTODY-01"]},
                "media_reuse": {"expected": 1, "ids": ["MEDIA-REUSE-RECEIPT-01"]},
                "security_facility_repair": {"expected": 1, "ids": ["RNO-SECURITY-LATCH-REPAIR"]},
                "communications": {
                    "scope": (
                        "August and November local instruction revisions and captured "
                        "September/November concern fixtures"
                    )
                },
            },
            "source_reconciliation": (
                "All declared local originals, due triggers, corrections and predecessor "
                "references retained; superseded data never rewritten"
            ),
            "prior_history": (
                "Earlier pending environmental, policy, conduct, integrity, retention, site and"
                " privacy-authority records remain as recorded; later operations do not "
                "retroactively cure them"
            ),
            "open_local_items": []
            if side == "A"
            else [
                "October review missed original deadline",
                "Sept9 semantic-only receiving/transfer validator acceptance",
                "Late workforce corrective decision",
                "Nov2-3 recipient/contact communication gap",
            ],
            "scope_exclusions": [
                "Jan1-Aug24 effective supplemental-program operation",
                "All-company workforce/incident/equipment populations",
                "Provider perimeter safeguards",
                "Live identity provider/network/cryptographic deployment",
                "Customer privacy notice issuance or accepted individual-rights determinations",
                "Actual PHI processing or legal status",
            ],
            "calendar_tail": (
                "This Jan2 record cannot be discovered at Dec31 09:00; full local-year status "
                "requires later fieldwork"
            ),
        },
        deps=[retention],
        upstream=history,
    )
    return sorted(result, key=lambda x: (x["event_at"], x["system"], x["record"], x["version"]))


def _content(item: dict, refs: dict, database: Path) -> bytes:
    dependencies = [refs[x] for x in item["dependencies"]]
    at = item["event_at"]
    upstream = item["upstream"]
    if any(x["available_at"] > at for x in [*dependencies, *upstream]):
        raise CompanyStoreError("Causal original not available at business event")
    body = {
        "schema": SCHEMA,
        "fictional_company_history": True,
        "data_kind": "NONPERSONAL_TRAINING_WORLD_RECORD",
        "event_at": at,
        "available_at": _time((datetime.fromisoformat(at) + timedelta(minutes=1)).isoformat()),
        **item["body"],
        "native_dependencies": dependencies,
        "predecessor_originals": upstream,
    }

    if item["system"] == "procedure_operation" and "input_originals" in item["body"]:
        body["required_original_retrieval"] = _retrieve_required_originals(database, refs, item)

    # Company originals contain business records; audit conclusions belong in auditor workpapers.
    def inspect(value):
        if isinstance(value, dict):
            if any(
                k
                in {
                    "audit_task_credit",
                    "task_id",
                    "expected_answer",
                    "key",
                    "audit_conclusion",
                    "auto_accept",
                    "branch_outcome",
                }
                for k in value
            ):
                raise CompanyStoreError("Audit-layer content forbidden in company original")
            for v in value.values():
                inspect(v)
        elif isinstance(value, list):
            for v in value:
                inspect(v)
        elif isinstance(value, str) and ("TASK-SH-" in value or "FULL_CLAUSE_PASS" in value):
            raise CompanyStoreError("Audit answer label forbidden in native source")

    inspect(body)
    return encoded(body)


def _provenance(ctx: dict, repository: Path) -> dict:
    return {
        "source_reference": SPEC,
        "source_spec_sha256": digest(repository / SPEC),
        "source_module_sha256": digest(repository / MODULE),
        "canon_pins": ctx["canon"],
        "fictional_2027_authorization_reference": (
            "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md"
        ),
        "reference_edition_boundary": ctx["spec"]["primary_legal_basis"]["edition_boundary"],
        "generation_kind": "AUTHORED_LATER_COMPANY_OPERATIONS_NOT_AUDIT_RESULTS",
        "source_generation_authorization": ctx["spec"]["source_generation_authorization"],
    }


def _write(path: Path, content: bytes):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(content)


def exact_marker_copy(source: Path, target: Path) -> dict:
    """Create an independent ordinary-byte copy and verify it is readable and usable."""
    before = private_file(source)
    raw = source.read_bytes()
    payload = json.loads(raw)
    if payload.get("payload_kind") != "NONPERSONAL_SYNTHETIC_MARKER":
        raise CompanyStoreError("Nonpersonal marker fixture required")
    _write(target, raw)
    after = private_file(target)
    if private_file(source) != before or target.read_bytes() != raw or before[:2] == after[:2]:
        raise CompanyStoreError("Independent exact marker copy required")
    return {
        "source_sha256": before[-1],
        "copy_sha256": after[-1],
        "exact_bytes": True,
        "usable_JSON": payload,
        "ordinary_independent_copy": True,
    }


def sanitize_test_media(path: Path, expected_before: str) -> dict:
    """Clear only an explicitly named disposable nonpersonal media working fixture."""
    if path.name != "reused-media.bin" or path.parent.name != "fixtures":
        raise CompanyStoreError("Explicit disposable media working fixture required")
    before = private_file(path)
    payload = json.loads(path.read_bytes())
    if (
        before[-1] != expected_before
        or payload.get("payload_kind") != "NONPERSONAL_SYNTHETIC_MARKER"
    ):
        raise CompanyStoreError("Approved nonpersonal working-copy content required")
    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    with os.fdopen(fd, "r+b") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino) != before[:2] or opened.st_nlink != 1:
            raise CompanyStoreError("Disposable media identity changed")
        handle.truncate(0)
        handle.flush()
        os.fsync(handle.fileno())
    after = private_file(path)
    if after[2] != 0 or after[-1] != sha(b""):
        raise CompanyStoreError("Disposable working-copy clear failed")
    return {
        "before_sha256": before[-1],
        "after_sha256": after[-1],
        "after_size": 0,
        "old_marker_present": False,
        "ordinary_working_fixture_only": True,
    }


def _retrieve_required_originals(database: Path, refs: dict, item: dict) -> list[dict]:
    """Actually read each selected required original for this local operating review."""
    selected = item["body"].get("input_originals", [])
    if item["body"].get("retrieval_count") == 0:
        return []
    records = []
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        for key in selected:
            ref = refs[key]
            row = db.execute(
                "SELECT content,sha256,event_at,available_at FROM versions "
                "WHERE company=? AND branch=? AND system=? AND record=? AND version=?",
                tuple(ref[k] for k in ("company", "branch", "system", "record", "version")),
            ).fetchone()
            if not row or sha(row[0]) != ref["sha256"] or row[1] != ref["sha256"]:
                raise CompanyStoreError("Required original could not be retrieved exactly")
            if row[3] > item["event_at"]:
                raise CompanyStoreError("Required original not yet available to operator")
            payload = json.loads(row[0])
            records.append(
                {
                    "original": ref,
                    "retrieved_sha256": sha(row[0]),
                    "parse_schema": payload["schema"],
                    "usable_JSON": True,
                }
            )
    if len(records) != item["body"].get("retrieval_count"):
        raise CompanyStoreError("Actual required-original retrieval count differs")
    return records


def _ordinary_tree(root: Path) -> dict:
    if root.is_symlink() or stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise CompanyStoreError("0700 private run root required")
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise CompanyStoreError("Private output alias forbidden")
        if p.is_dir():
            if stat.S_IMODE(p.stat().st_mode) != 0o700:
                raise CompanyStoreError("0700 output directory required")
        elif p.is_file():
            out[p.relative_to(root).as_posix()] = private_file(p)[-1]
        else:
            raise CompanyStoreError("Ordinary output file required")
    return out


def _receipt(ctx: dict, repository: Path, destination: Path, originals: dict, counts: dict) -> dict:
    return {
        "schema": SCHEMA + "_SOURCE_RECEIPT",
        "native_originals": originals,
        "native_counts": counts,
        "source_root": str(destination),
        "company": COMPANY,
        "branches": BRANCHES,
        "system_owners": OWNERS,
        "predecessor_inventory": ctx["originals"],
        "predecessor_file_pins": {p: x[-1] for p, x in ctx["stamps"].items()},
        "canon_pins": ctx["canon"],
        "spec_sha256": digest(repository / SPEC),
        "module_sha256": digest(repository / MODULE),
        "p1_freeze": P1_FREEZE,
        "audit_task_credit": False,
        "active_pair_mutated": False,
        "source_complete": False,
        "independent_review_pending": True,
        "limits": [
            "Later local program only; effectiveAug25 and monthlySep-Dec",
            "Full2027 operating assurance not established",
            "Local model is not real deployed service or ePHI processing",
            (
                "Encryption/TLS entries are retained model configuration, not cryptographic"
                " deployment evidence"
            ),
            "Customer notice and privacy-rights decisions retained by customer",
            "Old history remains immutable and unaccepted where recorded",
        ],
        "route_locators": {
            side: [
                {
                    "task_id": r["task_id"],
                    "authored_test_clause": r["authored_test_clause"],
                    "remaining_test_gate": r["remaining_test_gate"],
                    "systems": list(TASK_SYSTEMS[r["task_id"]]),
                    "native_original_refs": [
                        x for x in originals[side] if x["system"] in TASK_SYSTEMS[r["task_id"]]
                    ],
                    "task_credit": False,
                    "status": "NOT_STARTED",
                    "conclusion": "NOT_RUN",
                }
                for r in ctx["routes"][side]
            ]
            for side in "AB"
        },
    }


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Publish fresh native company sources and ordinary marker working copies."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or stat.S_IMODE(destination.parent.stat().st_mode) != 0o700
        or any(p.is_symlink() for p in (destination, *destination.parents))
    ):
        raise CompanyStoreError("Fresh private destination under existing0700 parent required")
    ctx = _context(repository, private)
    ctx["repository"] = repository
    provenance = _provenance(ctx, repository)
    with tempfile.TemporaryDirectory(
        prefix="supplemental-source-stage-", dir=destination.parent
    ) as name:
        stage = Path(name)
        fixtures = stage / "fixtures"
        fixtures.mkdir(mode=0o700)
        for name, content in fixture_material().items():
            _write(fixtures / name, content)
        # Explicit ordinary-byte copy; no hard links, reflinks or shell cp.
        for name in ["recovered-marker.json", "pre-movement-marker.json"]:
            exact_marker_copy(fixtures / "marker-original.json", fixtures / name)
        exact_marker_copy(fixtures / "marker-original.json", fixtures / "reused-media.bin")
        sanitize_test_media(
            fixtures / "reused-media.bin", sha(fixture_material()["marker-original.json"])
        )
        store = CompanyStore(stage)
        originals = {}
        counts = {}
        for side, branch in BRANCHES.items():
            for system, owner in OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            refs = {}
            originals[side] = []
            plan = _plan(ctx, side)
            for item in plan:
                content = _content(item, refs, store.path)
                available = json.loads(content)["available_at"]
                command = "SUP-" + sha(
                    encoded([branch, item["system"], item["record"], item["version"]])
                )
                row = store.append_version(
                    COMPANY,
                    branch,
                    item["system"],
                    item["record"],
                    expected_version=item["version"] - 1,
                    command_id=command,
                    event_at=item["event_at"],
                    available_at=available,
                    content=content,
                    provenance=provenance,
                )
                refs[_key(row)] = _ref(row)
                originals[side].append(_ref(row))
            counts[side] = len(plan)
        receipt = _receipt(ctx, repository, destination, originals, counts)
        _write(stage / "SOURCE_RECEIPT.json", encoded(receipt))
        pins = _ordinary_tree(stage)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "files": pins,
            "module_sha256": digest(repository / MODULE),
            "spec_sha256": digest(repository / SPEC),
            "native_counts": counts,
            "audit_task_credit": False,
            "active_pair_mutated": False,
        }
        _write(stage / "RUN-MANIFEST.json", encoded(manifest))
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    "Read-only reperform native content, full inventory, predecessor/version/clocks and mechanics."
    destination = Path(destination).absolute()
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    before = _ordinary_tree(destination)
    expected_files = {
        "company.sqlite3",
        "SOURCE_RECEIPT.json",
        "RUN-MANIFEST.json",
        *(
            f"fixtures/{n}"
            for n in [
                *fixture_material(),
                "recovered-marker.json",
                "pre-movement-marker.json",
                "reused-media.bin",
            ]
        ),
    }
    if set(before) != expected_files:
        raise CompanyStoreError("Exact private layout differs")
    manifest = json.loads((destination / "RUN-MANIFEST.json").read_bytes())
    if (
        manifest["files"] != {p: h for p, h in before.items() if p != "RUN-MANIFEST.json"}
        or manifest["module_sha256"] != digest(repository / MODULE)
        or manifest["spec_sha256"] != digest(repository / SPEC)
    ):
        raise CompanyStoreError("Output manifest or implementation pin differs")
    ctx = _context(repository, private)
    ctx["repository"] = repository
    rows = _read_native(
        destination / "company.sqlite3",
        import_floor=ctx["spec"]["source_generation_authorization"]["not_before_utc"],
    )
    provenance = _provenance(ctx, repository)
    originals = {}
    counts = {}
    for side, branch in BRANCHES.items():
        refs = {}
        originals[side] = []
        actual = [r for r in rows if r["branch"] == branch]
        plan = _plan(ctx, side)
        counts[side] = len(plan)
        if len(actual) != len(plan):
            raise CompanyStoreError("Native population differs")
        for item, row in zip(plan, actual, strict=True):
            body = _content(item, refs, destination / "company.sqlite3")
            command = "SUP-" + sha(
                encoded([branch, item["system"], item["record"], item["version"]])
            )
            fingerprint = sha(
                json.dumps(
                    [
                        [COMPANY, branch, item["system"], item["record"]],
                        item["version"] - 1,
                        item["event_at"],
                        json.loads(body)["available_at"],
                        "AUTHORED_TRAINING_SOURCE",
                        provenance,
                        sha(body),
                    ],
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode()
            )
            if (
                row["content"] != body
                or row["company"] != COMPANY
                or _key(row) != f"{item['system']}/{item['record']}/{item['version']}"
                or row["event_at"] != item["event_at"]
                or row["available_at"] != json.loads(body)["available_at"]
                or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                or json.loads(row["provenance"]) != provenance
                or row["command_id"] != command
                or row["input_digest"] != fingerprint
                or _time(row["imported_at"]) > _time(datetime.now().astimezone().isoformat())
            ):
                raise CompanyStoreError(
                    "Exact native content, custody, provenance or causal clocks differ"
                )
            refs[_key(row)] = _ref(row)
            originals[side].append(_ref(row))
    if len(rows) != sum(counts.values()):
        raise CompanyStoreError("Foreign native branch detected")
    with closing(
        sqlite3.connect(
            (destination / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
        )
    ) as db:
        expected = {(COMPANY, b, s, o) for b in BRANCHES.values() for s, o in OWNERS.items()}
        if set(db.execute("SELECT * FROM systems")) != expected or any(
            db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in ["grants", "access_events", "collections"]
        ):
            raise CompanyStoreError(
                "Registration custody or unrequested collection journal differs"
            )
    receipt = json.loads((destination / "SOURCE_RECEIPT.json").read_bytes())
    if receipt != _receipt(ctx, repository, destination, originals, counts):
        raise CompanyStoreError("Exact receipt custody, locator or no-credit boundary differs")
    expected_manifest = {
        "schema": SCHEMA + "_MANIFEST",
        "files": {p: h for p, h in before.items() if p != "RUN-MANIFEST.json"},
        "module_sha256": digest(repository / MODULE),
        "spec_sha256": digest(repository / SPEC),
        "native_counts": counts,
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }
    if manifest != expected_manifest:
        raise CompanyStoreError("Exact manifest claim differs")
    material = fixture_material()
    if any((destination / "fixtures" / n).read_bytes() != v for n, v in material.items()):
        raise CompanyStoreError("Marker original/test key differs")
    for name in ["recovered-marker.json", "pre-movement-marker.json"]:
        if (destination / "fixtures" / name).read_bytes() != material["marker-original.json"]:
            raise CompanyStoreError("Exact usable copy differs")
    if (destination / "fixtures/reused-media.bin").read_bytes() != b"":
        raise CompanyStoreError("Disposed working copy contains prior bytes")
    if (
        _ordinary_tree(destination) != before
        or _p1_inventory(private) != P1_FREEZE
        or any(private_file(private / p) != old for p, old in ctx["stamps"].items())
    ):
        raise CompanyStoreError("Output or frozen predecessor changed during verification")
    return {
        "verdict": "PASS_PRIVATE_LATER_LOCAL_COMPANY_SOURCE_MECHANICS_NO_AUDIT_CREDIT",
        "schema": SCHEMA,
        "source_root": str(destination),
        "native_counts": counts,
        "route_locator_count_per_side": 12,
        "receipt_sha256": before["SOURCE_RECEIPT.json"],
        "manifest_sha256": before["RUN-MANIFEST.json"],
        "native_db_sha256": before["company.sqlite3"],
        "fixture_hashes": {p: h for p, h in before.items() if p.startswith("fixtures/")},
        "p1_freeze": P1_FREEZE,
        "audit_task_credit": False,
        "active_pair_mutated": False,
        "source_complete": False,
        "independent_review_pending": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["create", "verify"])
    parser.add_argument("destination", type=Path)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--private-repository", type=Path, required=True)
    args = parser.parse_args()
    result = (create if args.action == "create" else verify)(
        args.destination, repository=args.repository, private_repository=args.private_repository
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
