"""Explicit local backup schedule scans, independent of audits and model calls.

Shares the backup runtime's transaction, revision and command journal. A ticket is
an unresolved local work item, not a root-cause, severity or effectiveness judgment.
"""

from pathlib import Path

from . import company_backup_runtime as backup
from .company_store import _id
from .operating_source_bridge import encoded, sha

QUALIFICATION = "OPERATOR_TRIGGERED_LOCAL_BACKUP_MONITOR_NOT_CONTINUOUS_OR_DEPLOYED_MONITORING"
SYSTEMS = ("monitor_scan", "monitor_observation", "monitor_ticket")


def _declaration(root, cfg):
    raw = backup.checked_bytes(root / "DECLARATION.json", 2 * 1024 * 1024)
    backup.require(sha(raw) == cfg["declaration_original_sha256"], "Retained declaration changed")
    return sha(raw)


def _capture(db, cfg, as_of):
    backup.require(as_of >= cfg["plan"]["declared_at"], "Declaration not yet available")
    rows = db.execute(
        "SELECT * FROM versions WHERE company=? AND branch=? "
        "AND system IN ('backup_job','restore_job') AND available_at<=? "
        "ORDER BY system,record,version",
        (cfg["plan"]["company_id"], cfg["plan"]["branch_id"], as_of),
    ).fetchall()
    backup.require(
        len(rows) <= 20000 and sum(len(r["content"]) for r in rows) <= 64 * 1024 * 1024,
        "Bounded job inventory required",
    )
    history = {}
    pins = []
    for row in rows:
        job = backup.decode(row["content"])
        backup.require(sha(row["content"]) == row["sha256"], "Job bytes differ")
        backup.require(
            row["event_at"] is not None and row["event_at"] <= as_of,
            "Job event lies after source cutoff",
        )
        backup.require(
            backup.decode(row["provenance"]).get("runtime_id") == cfg["runtime_id"]
            and job.get("runtime_id") == cfg["runtime_id"],
            "Foreign runtime job",
        )
        binding = cfg["bindings"].get(row["record"])
        backup.require(binding is not None, "Job outside declared schedule")
        backup.require(
            job.get("occurrence_id") == row["record"]
            and job.get("operation") == binding["operation"]
            and job.get("dataset_id") == binding["dataset_id"]
            and row["system"]
            == ("backup_job" if binding["operation"] == "BACKUP" else "restore_job"),
            "Job identity differs from declaration",
        )
        backup.require(
            job.get("status") in ("FAILED", "COMPLETED")
            and job.get("business_attempted_at") == row["event_at"],
            "Unsupported job status or timing",
        )
        member = {
            **backup.pin(row),
            "event_at": row["event_at"],
            "available_at": row["available_at"],
            "provenance_sha256": sha(row["provenance"].encode()),
        }
        pins.append(member)
        history.setdefault(row["record"], []).append((member, job))
    source_tickets = {}
    ticket_members = []
    tickets = db.execute(
        "SELECT * FROM versions WHERE company=? AND branch=? AND system='failure_ticket' "
        "AND available_at<=? ORDER BY record,version",
        (cfg["plan"]["company_id"], cfg["plan"]["branch_id"], as_of),
    ).fetchall()
    backup.require(
        len(tickets) <= 20000 and sum(len(r["content"]) for r in tickets) <= 16 * 1024 * 1024,
        "Bounded source tickets required",
    )
    known_jobs = {
        encoded({k: m[k] for k in backup.FIELDS}): j for items in history.values() for m, j in items
    }
    for row in tickets:
        ticket = backup.decode(row["content"])
        backup.exact_pin(ticket.get("job_pin"))
        key = encoded(ticket["job_pin"])
        backup.require(
            sha(row["content"]) == row["sha256"]
            and row["event_at"] is not None
            and row["event_at"] <= as_of
            and backup.decode(row["provenance"]).get("runtime_id") == cfg["runtime_id"],
            "Source failure ticket identity or cutoff differs",
        )
        backup.require(
            key in known_jobs
            and known_jobs[key]["status"] == "FAILED"
            and ticket.get("error_code") == known_jobs[key].get("error_code")
            and ticket.get("status") == "OPEN_RECORDED_FAILURE_NOT_AUTOMATICALLY_CLOSED",
            "Source ticket does not support exact failed attempt",
        )
        backup.require(
            key not in source_tickets, "Ambiguous multiple tickets for one failed attempt"
        )
        source_tickets[key] = backup.pin(row)
        ticket_members.append(
            {
                **backup.pin(row),
                "event_at": row["event_at"],
                "available_at": row["available_at"],
                "provenance_sha256": sha(row["provenance"].encode()),
            }
        )
    observations = []
    due = 0
    for slot in cfg["plan"]["schedule"]:
        jobs = history.get(slot["id"], [])
        is_due = as_of >= slot["due_at"]
        due += is_due
        if is_due and not jobs:
            observations.append(
                {
                    "kind": "MISSING_DECLARED_EXECUTION",
                    "occurrence_id": slot["id"],
                    "due_at": slot["due_at"],
                    "source_job_pin": None,
                    "recorded_error_code": None,
                    "source_ticket_pin": None,
                }
            )
        for member, job in jobs:
            if job["status"] == "FAILED":
                observations.append(
                    {
                        "kind": "FAILED_RECORDED_ATTEMPT",
                        "occurrence_id": slot["id"],
                        "due_at": slot["due_at"],
                        "source_job_pin": {k: member[k] for k in backup.FIELDS},
                        "recorded_error_code": job.get("error_code"),
                        "source_ticket_pin": source_tickets.get(
                            encoded({k: member[k] for k in backup.FIELDS})
                        ),
                    }
                )
    membership = {
        "runtime_id": cfg["runtime_id"],
        "declaration_ref": cfg["declaration_ref"],
        "as_of": as_of,
        "jobs": pins,
        "source_failure_tickets": ticket_members,
    }
    return {
        "membership": membership,
        "jobs_sha256": sha(encoded(membership)),
        "declared_count": len(cfg["plan"]["schedule"]),
        "due_count": due,
        "observations": observations,
        "latest_completed_count": sum(
            items[-1][1]["status"] == "COMPLETED" for items in history.values()
        ),
        "source_validation": "DECLARED_SCHEDULE_AND_RECORDED_JOB_VERSIONS_NOT_CURRENT_COPY_RETEST",
    }


def inspect(runtime, *, expected_runtime_sha256, as_of):
    """Trusted operator read-only single-database snapshot; explicit source cutoff."""
    root = backup.private(Path(runtime), True)
    cfg = backup._config(root, expected_runtime_sha256)
    cutoff = backup._time(as_of)
    declaration_sha = _declaration(root, cfg)
    with backup.database(root) as db:
        backup._bound_config(db, cfg, expected_runtime_sha256)
        revision = db.execute("SELECT revision FROM backup_runtime_state").fetchone()[0]
        result = _capture(db, cfg, cutoff)
        backup.require(
            backup._config(root, expected_runtime_sha256) == cfg
            and _declaration(root, cfg) == declaration_sha,
            "Monitor inputs changed during inspection",
        )
    return {
        **result,
        "runtime_revision": revision,
        "runtime_sha256": expected_runtime_sha256,
        "qualification": QUALIFICATION,
    }


def scan(
    runtime,
    *,
    expected_runtime_sha256,
    expected_revision,
    command_id,
    expected_jobs_sha256,
    as_of,
    recorded_at,
    operator_id,
    rationale,
):
    """Persist scan+observations+deduplicated open tickets in one runtime CAS.

    The caller explicitly chooses this operation; no periodic scheduler, audit
    generation or automatic remediation is implied. All existing originals remain.
    """
    root = backup.private(Path(runtime), True)
    cutoff, event_at = backup._time(as_of), backup._time(recorded_at)
    backup.require(cutoff <= event_at, "Source cutoff cannot be after scan recording")
    _id(operator_id)
    backup.require(
        isinstance(rationale, str) and 0 < len(rationale.strip()) <= 4000,
        "Explicit bounded scan rationale required",
    )
    backup.require(
        isinstance(expected_jobs_sha256, str)
        and len(expected_jobs_sha256) == 64
        and all(c in "0123456789abcdef" for c in expected_jobs_sha256),
        "Explicit inspected job inventory SHA256 required",
    )
    admitted_config = backup._config(root, expected_runtime_sha256)
    admitted_declaration = _declaration(root, admitted_config)
    code_paths = (Path(__file__), Path(backup.__file__))
    code_pins = {p.name: sha(p.read_bytes()) for p in code_paths}
    payload = {
        "operation": "BACKUP_MONITOR_SCAN",
        "as_of": cutoff,
        "operator_id": operator_id,
        "rationale": rationale,
        "expected_jobs_sha256": expected_jobs_sha256,
        "analysis_source_sha256": code_pins,
    }

    def perform(db, cfg, at):
        backup.require(
            operator_id == cfg["operator_id"], "Explicit configured local operator required"
        )
        declaration_sha = _declaration(root, cfg)
        backup.require(
            cfg == admitted_config and declaration_sha == admitted_declaration,
            "Admitted monitor declaration changed",
        )
        captured = _capture(db, cfg, cutoff)
        backup.require(
            captured["jobs_sha256"] == expected_jobs_sha256, "Inspected job inventory changed"
        )
        key = (cfg["plan"]["company_id"], cfg["plan"]["branch_id"])
        for system in SYSTEMS:
            old = db.execute(
                "SELECT owner FROM systems WHERE company=? AND branch=? AND system=?",
                (*key, system),
            ).fetchone()
            backup.require(old is None or old[0] == operator_id, "Monitor system owner conflict")
            db.execute("INSERT OR IGNORE INTO systems VALUES(?,?,?,?)", (*key, system, operator_id))
        scan_id = "SCAN-" + sha(encoded([cfg["runtime_id"], command_id]))[:32]
        common = {
            "runtime_id": cfg["runtime_id"],
            "qualification": QUALIFICATION,
            "operator_id": operator_id,
            "source_cutoff": cutoff,
            "recorded_at": at,
            "root_cause": "NOT_DETERMINED",
            "severity": "NOT_ASSIGNED",
            "whole_period_effectiveness": "NOT_ASSESSED",
            "operating_review": "NOT_PERFORMED",
        }
        observation_pins, ticket_pins, new_ticket_pins = [], [], []

        def insert(system, record, body):
            native_command = "MON-" + sha(encoded([command_id, system, record]))[:40]
            return backup._insert(db, cfg, system, record, encoded(body), at, native_command)

        for index, observation in enumerate(captured["observations"]):
            issue = {k: observation[k] for k in ("kind", "occurrence_id", "source_job_pin")}
            ticket_id = "TICKET-" + sha(encoded([cfg["runtime_id"], issue]))[:32]
            existing = db.execute(
                "SELECT * FROM versions WHERE company=? AND branch=? "
                "AND system='monitor_ticket' AND record=? ORDER BY version",
                (*key, ticket_id),
            ).fetchall()
            backup.require(len(existing) <= 1, "Monitor tickets have no resolution/version API")
            if observation["source_ticket_pin"] is not None:
                ticket = observation["source_ticket_pin"]
            elif existing:
                row = existing[0]
                body = backup.decode(row["content"])
                backup.require(
                    sha(row["content"]) == row["sha256"]
                    and body.get("runtime_id") == cfg["runtime_id"]
                    and encoded(body.get("issue")) == encoded(issue)
                    and body.get("qualification") == QUALIFICATION
                    and body.get("operator_id") == operator_id
                    and row["event_at"] is not None
                    and row["event_at"] <= at
                    and row["available_at"] <= at
                    and body.get("status") == "OPEN",
                    "Existing monitor ticket differs",
                )
                ticket = backup.pin(row)
            else:
                ticket = insert(
                    "monitor_ticket",
                    ticket_id,
                    {
                        **common,
                        "issue": issue,
                        "first_scan_id": scan_id,
                        "status": "OPEN",
                        "resolution": "NOT_RECORDED",
                        "qualification_limit": (
                            "Missing selected execution is not proof of absent company evidence; "
                            "recorded failed attempts remain historical after retry."
                        ),
                    },
                )
                new_ticket_pins.append(ticket)
            ticket_pins.append(ticket)
            observation_pins.append(
                insert(
                    "monitor_observation",
                    scan_id + "-" + str(index),
                    {
                        **common,
                        **observation,
                        "scan_id": scan_id,
                        "ticket_pin": ticket,
                        "status": "RECORDED_OBSERVATION_NOT_INDEPENDENT_REVIEW",
                    },
                )
            )
        scan_pin = insert(
            "monitor_scan",
            scan_id,
            {
                **common,
                "rationale": rationale,
                "declaration_ref": cfg["declaration_ref"],
                "declaration_original_sha256": declaration_sha,
                "runtime_definition_sha256": expected_runtime_sha256,
                "analysis_source_sha256": code_pins,
                "capture": captured,
                "observation_pins": observation_pins,
                "ticket_pins": ticket_pins,
                "new_ticket_pins": new_ticket_pins,
                "automatic_ticket_resolution": False,
            },
        )
        backup.require(
            _declaration(root, cfg) == declaration_sha
            and {p.name: sha(p.read_bytes()) for p in code_paths} == code_pins,
            "Monitor source changed during publication",
        )
        return {
            "operation": "BACKUP_MONITOR_SCAN",
            "monitor_qualification": QUALIFICATION,
            "scan_pin": scan_pin,
            "observation_pins": observation_pins,
            "ticket_pins": ticket_pins,
            "new_ticket_pins": new_ticket_pins,
            "jobs_sha256": expected_jobs_sha256,
            "as_of": cutoff,
            "declared_count": captured["declared_count"],
            "due_count": captured["due_count"],
            "automatic_resolution": False,
        }

    return backup._execute(
        root, expected_runtime_sha256, expected_revision, command_id, event_at, payload, perform
    )
