"""Persistent local event intake; no enterprise incident, breach or closure assertion."""

import tempfile
from pathlib import Path

from .company_backup_runtime import (
    FIELDS,
    checked_bytes,
    database,
    exact_pin,
    native,
    private,
    require,
)
from .company_lifecycle_activity import _source_stamp
from .company_security_logging_activity import QUALIFICATION as LOG_QUALIFICATION
from .company_store import CompanyStore, _id, _json, _now, _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

QUALIFICATION = "LOCAL_SECURITY_EVENT_WORKFLOW_NOT_ENTERPRISE_INCIDENT_OR_BREACH"
RULES = {
    "BLOCKED": "INFORMATIONAL",
    "ALLOWED": "NO_LOCAL_FOLLOWUP",
    "OVERRIDE_USED": "LOCAL_RESPONSE_REQUIRED",
    "LOCAL-COLLECTION-GAP": "LOCAL_COLLECTION_RESPONSE_REQUIRED",
}
SYSTEMS = (
    "security_event_definition",
    "security_event_operation",
    "security_event_state",
    "security_event_reconciliation",
)
SOURCE_SYSTEMS = {
    "source_inventory",
    "publisher_originals",
    "publisher_events",
    "collector_configuration",
    "ingestion_journal",
    "publisher_checkpoints",
    "coverage_reconciliation",
    "detection_alerts",
    "response_tickets",
    "review_records",
}
LIMIT = 4 * 1024 * 1024
TOTAL_LIMIT = 64 * 1024 * 1024


def _code_pins():
    return {
        name: sha((Path(__file__).parent / name).read_bytes())
        for name in (
            "company_security_event_runtime.py",
            "company_backup_runtime.py",
            "company_lifecycle_activity.py",
            "company_store.py",
            "organization.py",
            "inference.py",
            "operating_source_bridge.py",
            "private_publication.py",
        )
    }


def _identity(ref):
    return tuple(ref[k] for k in FIELDS[:-1])


def _pin(row):
    return {k: row[k] for k in FIELDS}


def _equal(left, right):
    return encoded(left) == encoded(right)


def read_sources(source_root, source_pins, as_of):
    """Exact complete bounded branch, one RO snapshot; caller must pin returned metadata."""
    source_root = private(Path(source_root), True)
    before = _source_stamp(source_root / "company.sqlite3")
    require(
        isinstance(source_pins, list) and 8 <= len(source_pins) <= 32,
        "Bounded explicit original set required",
    )
    for ref in source_pins:
        exact_pin(ref)
    require(
        len({_identity(r) for r in source_pins}) == len(source_pins), "Duplicate source identity"
    )
    owners = {(r["company"], r["branch"]) for r in source_pins}
    require(len(owners) == 1, "One original company and branch required")
    at, rows = _time(as_of), []
    with database(source_root) as db:
        company, branch = next(iter(owners))
        identities = db.execute(
            "SELECT company,branch,system,record,version FROM versions "
            "WHERE company=? AND branch=? LIMIT 33",
            (company, branch),
        ).fetchall()
        require(
            {tuple(r) for r in identities} == {_identity(r) for r in source_pins},
            "Complete declared logging branch required",
        )
        size = db.execute(
            "SELECT COALESCE(SUM(length(content)+length(CAST(provenance AS BLOB))),0) "
            "FROM versions WHERE company=? AND branch=?",
            (company, branch),
        ).fetchone()[0]
        require(type(size) is int and size <= LIMIT, "Source byte bound exceeded")
        for ref in source_pins:
            row = native(db, ref, at)
            require(row["event_at"] <= row["available_at"], "Invalid source chronology")
            rows.append(
                {
                    k: row[k]
                    for k in (
                        *FIELDS,
                        "event_at",
                        "available_at",
                        "origin",
                        "provenance",
                        "content",
                    )
                }
            )
    require(
        _source_stamp(source_root / "company.sqlite3") == before,
        "Source privacy or identity changed",
    )
    require(
        sum(len(r["content"]) + len(r["provenance"].encode()) for r in rows) <= LIMIT,
        "Source byte bound exceeded",
    )
    rows.sort(key=_identity)
    return rows, sha(encoded([{k: v for k, v in r.items() if k != "content"} for r in rows]))


def _validate(rows):
    by_id = {_identity(r): r for r in rows}
    bodies = {_identity(r): decode(r["content"]) for r in rows}
    require({r["system"] for r in rows} == SOURCE_SYSTEMS, "Logging source systems differ")
    require(all(isinstance(b, dict) for b in bodies.values()), "Native source objects required")
    for row in rows:
        body = bodies[_identity(row)]
        if row["system"] != "publisher_originals":
            require(
                body.get("classification") == LOG_QUALIFICATION,
                "Qualified logging originals required",
            )

    def linked(value, dependent):
        require(
            isinstance(value, dict) and set(value) == set(FIELDS) | {"available_at"},
            "Exact source link required",
        )
        ref = {k: value[k] for k in FIELDS}
        exact_pin(ref)
        target = by_id.get(_identity(ref))
        require(target is not None and _equal(_pin(target), ref), "Source link pin differs")
        require(
            _time(value["available_at"]) == target["available_at"] <= dependent["event_at"],
            "Linked source unavailable at dependent event",
        )
        return bodies[_identity(target)]

    def group(system):
        return [r for r in rows if r["system"] == system]

    def check_links(value, dependent):
        if isinstance(value, dict):
            if set(value) == set(FIELDS) | {"available_at"}:
                linked(value, dependent)
            else:
                for child in value.values():
                    check_links(child, dependent)
        elif isinstance(value, list):
            for child in value:
                check_links(child, dependent)

    for row in rows:
        if row["system"] != "publisher_originals":
            check_links(bodies[_identity(row)], row)
    inventories, checkpoints = group("source_inventory"), group("publisher_checkpoints")
    require(
        len(inventories) == len(checkpoints) == 1,
        "One independent inventory and checkpoint required",
    )
    inventory = bodies[_identity(inventories[0])]
    checkpoint = bodies[_identity(checkpoints[0])]
    events, previous = [], ""
    event_rows = sorted(
        group("publisher_events"),
        key=lambda r: bodies[_identity(r)].get("event", {}).get("sequence", 0),
    )
    require(1 <= len(event_rows) <= 8, "Bounded event denominator required")
    for index, row in enumerate(event_rows, 1):
        event = bodies[_identity(row)].get("event")
        require(
            isinstance(event, dict)
            and type(event.get("sequence")) is int
            and event["sequence"] == index,
            "Exact publisher sequence required",
        )
        require(
            event.get("previous_event_sha256") == previous
            and sha(encoded({k: v for k, v in event.items() if k != "event_sha256"}))
            == event.get("event_sha256"),
            "Publisher chain differs",
        )
        require(
            event.get("authorization_decision") in ("BLOCKED", "ALLOWED", "OVERRIDE_USED"),
            "Supported native authorization required",
        )
        require(
            _time(event["source_event_at"]) == row["event_at"]
            and row["available_at"] <= checkpoints[0]["event_at"],
            "Publisher checkpoint chronology differs",
        )
        upstream = event.get("upstream")
        require(isinstance(upstream, dict), "Original gate link required")
        exact_pin({k: upstream[k] for k in FIELDS})
        copies = [
            r
            for r in group("publisher_originals")
            if r["record"] == upstream["record"] and r["sha256"] == upstream["sha256"]
        ]
        require(len(copies) == 1, "Exact original gate copy required")
        gate = bodies[_identity(copies[0])]
        copy_provenance = decode(copies[0]["provenance"])
        require(
            upstream["company"] == row["company"]
            and upstream.get("source_store_id") == copy_provenance.get("source_store_id")
            and isinstance(upstream.get("source_store_id"), str),
            "Original publisher company or producer label differs",
        )
        require(
            gate.get("classification")
            == "LOCAL_SYNTHETIC_CONFIG_RELEASE_EXERCISE_NOT_LIVE_DEPLOYMENT",
            "Qualified original gate required",
        )
        require(
            copies[0]["event_at"] == row["event_at"]
            and _time(upstream["available_at"]) <= row["event_at"],
            "Original gate chronology differs",
        )
        require(
            event.get("local_source_id") == inventory.get("local_source_id")
            and any(
                item.get("source_id") == event.get("local_source_id")
                and item.get("upstream_branch") == upstream["branch"]
                and item.get("upstream_system") == upstream["system"]
                for item in inventory.get("required_sources", [])
                if isinstance(item, dict)
            ),
            "Publisher outside declared source inventory",
        )
        require(
            gate.get("decision") == event["authorization_decision"]
            and _time(gate["recorded_at"]) == row["event_at"],
            "Native gate decision differs",
        )
        require(
            _equal(
                event.get("source_support"),
                {k: gate.get(k) for k in ("artifact", "peer_review", "tests")},
            ),
            "Native gate support differs",
        )
        previous = event["event_sha256"]
        events.append(event)
    require(
        _equal(checkpoint.get("sequences"), list(range(1, len(events) + 1)))
        and _equal(checkpoint.get("event_hashes"), [e["event_sha256"] for e in events])
        and checkpoint.get("head_sha256") == previous,
        "Independent checkpoint membership differs",
    )
    require(
        len(group("publisher_originals")) == len(events), "Original publisher denominator differs"
    )
    ingested = {}
    for row in group("ingestion_journal"):
        b = bodies[_identity(row)]
        e = b.get("event")
        require(any(_equal(e, x) for x in events), "Ingestion event differs")
        require(e["sequence"] not in ingested, "Duplicate ingestion sequence")
        cfg = linked(b.get("collector_configuration"), row)
        require(
            e["authorization_decision"] not in cfg.get("excluded_authorization_decisions", []),
            "Ingestion contradicts filter",
        )
        require(
            _time(b["received_at"]) == row["event_at"] >= _time(e["source_event_at"]),
            "Ingestion chronology differs",
        )
        ingested[e["sequence"]] = row
    require(
        set(ingested) == set(range(1, len(events) + 1)), "Final ingestion population incomplete"
    )
    reports = {}
    for row in group("coverage_reconciliation"):
        b = bodies[_identity(row)]
        if "publisher_checkpoint" in b:
            linked(b["publisher_checkpoint"], row)
        else:
            prior_report = linked(b.get("prior_coverage_report"), row)
            require("publisher_checkpoint" in prior_report, "Direct original checkpoint required")
        observed = sorted(n for n, r in ingested.items() if r["available_at"] <= row["event_at"])
        require(
            _equal(b.get("publisher_sequences"), list(range(1, len(events) + 1)))
            and _equal(b.get("collector_sequences"), observed)
            and _equal(
                b.get("missing_sequences"), sorted(set(range(1, len(events) + 1)) - set(observed))
            ),
            "Coverage membership differs",
        )
        require(
            b.get("hash_mismatches") == [] and b.get("unexpected_sequences") == [],
            "Unsupported contradictory source coverage",
        )
        reports[_identity(row)] = b
    alerts, subjects = {}, {}
    for row, event in zip(event_rows, events, strict=True):
        subjects["EVENT-" + str(event["sequence"])] = {
            "source": _pin(row),
            "basis": event["authorization_decision"],
            "event_sha256": event["event_sha256"],
        }
    for row in group("detection_alerts"):
        b = bodies[_identity(row)]
        rule = b.get("rule_id")
        require(
            rule in inventory.get("required_detections", []),
            "Alert outside declared detection inventory",
        )
        if rule == "LOCAL-COLLECTION-GAP":
            report = linked(b.get("coverage_report"), row)
            require(
                bool(report.get("missing_sequences"))
                and _equal(b.get("missing_sequences"), report["missing_sequences"]),
                "Gap alert differs",
            )
            basis = rule
        else:
            arrival = linked(b.get("ingestion"), row)
            event = arrival["event"]
            expected_rule = {
                "BLOCKED": "LOCAL-AUTHORIZATION-BLOCKED",
                "OVERRIDE_USED": "LOCAL-AUTHORIZATION-OVERRIDE",
            }.get(event["authorization_decision"])
            require(
                rule == expected_rule and b.get("source_event_sha256") == event["event_sha256"],
                "Alert publisher correlation differs",
            )
            basis = event["authorization_decision"]
        key = "ALERT-" + row["record"]
        subjects[key] = {"source": _pin(row), "basis": basis}
        alerts[_identity(row)] = row
    # Required detection population is computed independently of supplied alert counts.
    for event in events:
        if event["authorization_decision"] != "ALLOWED":
            require(
                sum(bodies[i].get("source_event_sha256") == event["event_sha256"] for i in alerts)
                == 1,
                "Expected event detection missing or duplicated",
            )
    gaps = [
        r for r in group("coverage_reconciliation") if bodies[_identity(r)].get("missing_sequences")
    ]
    require(
        sum(bodies[i].get("rule_id") == "LOCAL-COLLECTION-GAP" for i in alerts) == len(gaps),
        "Expected collection-gap detection differs",
    )
    acked = []
    for row in group("response_tickets"):
        b = bodies[_identity(row)]
        linked(b.get("alert"), row)
        require(b.get("status") == "ACKNOWLEDGED", "Original acknowledgment required")
        identity = _identity(b["alert"])
        require(identity in alerts, "Acknowledgment source is not alert")
        acked.append(identity)
    require(
        len(acked) == len(set(acked)) and set(acked) == set(alerts),
        "Original acknowledgment population differs",
    )
    require(inventory.get("owner_id"), "Declared source owner required")
    return subjects, inventory["owner_id"]


def _write(root, name, raw):
    path = root / name
    with path.open("xb") as stream:
        stream.write(raw)
    path.chmod(0o600)


def _insert(db, cfg, system, record, body, at, command):
    raw = encoded(body)
    require(
        len(raw) <= LIMIT and db.execute("SELECT count(*) FROM versions").fetchone()[0] < 20000,
        "Runtime quota exceeded",
    )
    key = [cfg["company"], cfg["branch"], system, record]
    provenance = {
        "classification": QUALIFICATION,
        "control_ids": ["SH-SEC-006"],
        "runtime_id": cfg["runtime_id"],
        "runtime_sha256": sha(encoded(cfg)),
        "source_metadata_sha256": cfg["source_metadata_sha256"],
    }
    require(
        db.execute("SELECT COALESCE(SUM(length(content)),0) FROM versions").fetchone()[0] + len(raw)
        <= TOTAL_LIMIT,
        "Runtime total byte quota exceeded",
    )
    digest = sha(raw)
    fingerprint = sha(
        _json([key, 0, at, at, "AUTHORED_TRAINING_SOURCE", provenance, digest]).encode()
    )
    db.execute(
        "INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            *key,
            1,
            at,
            at,
            _now(),
            "AUTHORED_TRAINING_SOURCE",
            _json(provenance),
            raw,
            digest,
            command,
            fingerprint,
        ),
    )
    return dict(zip(FIELDS, (*key, 1, digest), strict=True))


def initialize(
    destination,
    *,
    repository,
    source_root,
    source_pins,
    expected_source_metadata_sha256,
    as_of,
    runtime_id,
    period_start,
    period_end,
    local_rules,
):
    """Initialize only declared native inputs, without intake, handoff or implicit actions."""
    destination = Path(destination)
    private(destination.parent, True)
    source_root = private(Path(source_root), True)
    require(
        destination.is_absolute()
        and destination == destination.resolve()
        and not destination.exists()
        and not destination.is_relative_to(source_root)
        and not source_root.is_relative_to(destination),
        "New separate private runtime required",
    )
    _id(runtime_id)
    at, start, end = map(_time, (as_of, period_start, period_end))
    require(start <= at < end, "Initialization outside declared period")
    require(_equal(local_rules, RULES), "Explicit bounded local rules required")
    source_pins = decode(encoded(source_pins))
    rows, pin = read_sources(source_root, source_pins, at)
    require(pin == expected_source_metadata_sha256, "Selected source metadata differs")
    subjects, owner = _validate(rows)
    org = snapshot(Path(repository), as_of=at[:10])
    assignment = next(a for a in org["control_assignments"] if a["control_id"] == "SH-SEC-006")
    require(owner == assignment["primary_person_id"], "Source owner and scoped route differ")
    reviewer = assignment["operating_reviewer_person_id"]
    require(reviewer != owner, "Distinct local handoff identity required")
    code = _code_pins()
    cfg = {
        "schema": "LOCAL_SECURITY_EVENT_RUNTIME_V1",
        "company": rows[0]["company"],
        "branch": runtime_id,
        "runtime_id": runtime_id,
        "initialized_at": at,
        "period_start": start,
        "period_end": end,
        "operator_id": owner,
        "local_handoff_person_id": reviewer,
        "assignment": assignment,
        "organization_source_sha256": org["source_sha256"],
        "source_metadata_sha256": pin,
        "source_metadata": [{k: v for k, v in row.items() if k != "content"} for row in rows],
        "source_location_sha256": sha(str(source_root).encode()),
        "upstream_identity_basis": (
            "PUBLISHER_DECLARED_NATIVE_IDENTITY_WITH_EXACT_RETAINED_GATE_COPY_"
            "NOT_DIRECT_UPSTREAM_DATABASE_VERIFICATION"
        ),
        "source_pins": [_pin(r) for r in rows],
        "subjects": subjects,
        "local_rules": RULES,
        "qualification": QUALIFICATION,
        "implementation_sha256": code,
        "whole_period_coverage": False,
        "incident_closed": False,
        "assignment_basis": "EXPLICIT_LOCAL_EXERCISE_NOT_CORPORATE_COMMAND_APPOINTMENT",
    }
    digest = sha(encoded(cfg))
    state = {
        "revision": 0,
        "event_at": at,
        "subjects": {},
        "incident_closed": False,
        "whole_period_coverage": False,
    }
    with tempfile.TemporaryDirectory(
        dir=destination.parent, prefix="security-event-stage-"
    ) as folder:
        stage = Path(folder)
        store = CompanyStore(stage)
        for system in SYSTEMS:
            store.register_system(cfg["company"], cfg["branch"], system, owner)
        (stage / "sources").mkdir(mode=0o700)
        for i, row in enumerate(rows):
            _write(stage / "sources", f"{i}.json", row["content"])
        _write(stage, "RUNTIME.json", encoded(cfg))
        with database(stage, True) as db:
            db.execute(
                "CREATE TABLE security_state(id INTEGER PRIMARY KEY,"
                "body BLOB NOT NULL,digest TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE security_commands(command TEXT PRIMARY KEY,"
                "digest TEXT NOT NULL,result BLOB NOT NULL)"
            )
            for op in ("UPDATE", "DELETE"):
                db.execute(
                    f"CREATE TRIGGER security_commands_no_{op.lower()} BEFORE {op} "
                    "ON security_commands BEGIN SELECT RAISE(ABORT,'Immutable command'); END"
                )
            db.execute(
                "INSERT INTO security_state VALUES(1,?,?)", (encoded(state), sha(encoded(state)))
            )
            _insert(db, cfg, SYSTEMS[0], runtime_id, cfg, at, "INITIALIZE")
        require(
            read_sources(source_root, source_pins, at)[1] == pin,
            "Source changed before publication",
        )
        require(
            _code_pins() == code
            and snapshot(Path(repository), as_of=at[:10])["source_sha256"] == org["source_sha256"],
            "Implementation or organization changed before publication",
        )
        publish(stage, destination)
    return {
        "runtime_sha256": digest,
        "revision": 0,
        "state_sha256": sha(encoded(state)),
        "qualification": QUALIFICATION,
    }


def _config(root, expected):
    raw = checked_bytes(Path(root) / "RUNTIME.json", LIMIT)
    require(sha(raw) == expected, "Runtime definition differs")
    cfg = decode(raw)
    require(cfg.get("schema") == "LOCAL_SECURITY_EVENT_RUNTIME_V1", "Runtime schema differs")
    require(
        sha(encoded(cfg["source_metadata"])) == cfg["source_metadata_sha256"],
        "Retained metadata differs",
    )
    for i, ref in enumerate(cfg["source_pins"]):
        require(
            sha(checked_bytes(Path(root) / "sources" / f"{i}.json", LIMIT)) == ref["sha256"],
            "Retained original differs",
        )
    return cfg


def _state(db, cfg):
    row = db.execute("SELECT body,digest FROM security_state WHERE id=1").fetchone()
    require(row is not None and sha(row["body"]) == row["digest"], "Runtime state pin differs")
    state = decode(row["body"])
    require(
        type(state.get("revision")) is int and 0 <= state["revision"] <= 9999,
        "Bounded exact state revision required",
    )
    definition = db.execute(
        "SELECT content,sha256 FROM versions WHERE system=?", (SYSTEMS[0],)
    ).fetchall()
    require(
        len(definition) == 1
        and definition[0]["content"] == encoded(cfg)
        and definition[0]["sha256"] == sha(encoded(cfg)),
        "Native definition differs",
    )
    history = db.execute("SELECT * FROM versions WHERE system=?", (SYSTEMS[2],)).fetchall()
    require(
        len(history) == state["revision"]
        and db.execute("SELECT count(*) FROM security_commands").fetchone()[0] == state["revision"],
        "Native state history count differs",
    )
    previous = {
        "revision": 0,
        "event_at": cfg["initialized_at"],
        "subjects": {},
        "incident_closed": False,
        "whole_period_coverage": False,
    }
    ordered = []
    for native_state in history:
        require(sha(native_state["content"]) == native_state["sha256"], "Native state bytes differ")
        body = decode(native_state["content"])
        require(
            isinstance(body.get("state"), dict) and type(body["state"].get("revision")) is int,
            "Exact native state revision required",
        )
        ordered.append((body["state"]["revision"], native_state, body))
    for index, (_, native_state, body) in enumerate(sorted(ordered, key=lambda x: x[0]), 1):
        operation = native(db, body["operation"])
        op = decode(operation["content"])
        require(
            body["state"]["revision"] == index
            and op.get("prior_state_sha256") == sha(encoded(previous))
            and op.get("state_sha256") == sha(encoded(body["state"]))
            and op.get("runtime_sha256") == sha(encoded(cfg)),
            "Native history chain differs",
        )
        command = db.execute(
            "SELECT result FROM security_commands WHERE command=?", (op["command_id"],)
        ).fetchone()
        require(command is not None, "Native command receipt missing")
        result = decode(command["result"])
        require(
            _equal(result.get("state"), _pin(native_state))
            and _equal(result.get("operation"), body["operation"])
            and result.get("state_sha256") == op["state_sha256"],
            "Native command receipt differs",
        )
        previous = body["state"]
    require(_equal(previous, state), "Current state differs from immutable native history")
    return state, row["digest"]


def inspect(runtime, *, expected_runtime_sha256):
    cfg = _config(runtime, expected_runtime_sha256)
    with database(runtime) as db:
        state, pin = _state(db, cfg)
    require(
        _equal(_config(runtime, expected_runtime_sha256), cfg), "Runtime changed during inspection"
    )
    return {
        "runtime_sha256": expected_runtime_sha256,
        "state_sha256": pin,
        "state": state,
        "declared_subjects": cfg["subjects"],
        "qualification": QUALIFICATION,
    }


def execute(
    runtime,
    *,
    expected_runtime_sha256,
    expected_revision,
    expected_state_sha256,
    command_id,
    operator_id,
    event_at,
    action,
    payload,
):
    """Explicit local state transitions; reconciliation never performs response or closure."""
    require(type(expected_revision) is int and expected_revision >= 0, "Exact revision required")
    _id(command_id)
    _id(operator_id)
    require(
        action in ("INTAKE", "TRIAGE", "HANDOFF", "RECORD_ACTION", "RECONCILE"),
        "Unknown local action",
    )
    require(isinstance(payload, dict), "Explicit action payload required")
    payload = decode(encoded(payload))
    cfg = _config(runtime, expected_runtime_sha256)
    require(operator_id == cfg["operator_id"], "Scoped local operator required")
    at = _time(event_at)
    require(cfg["period_start"] <= at < cfg["period_end"], "Action outside declared period")
    command = {
        "runtime_sha256": expected_runtime_sha256,
        "expected_revision": expected_revision,
        "expected_state_sha256": expected_state_sha256,
        "command_id": command_id,
        "operator_id": operator_id,
        "event_at": at,
        "action": action,
        "payload": payload,
    }
    digest = sha(encoded(command))
    code = _code_pins()
    with database(runtime, True) as db:
        state, prior = _state(db, cfg)
        old = db.execute(
            "SELECT digest,result FROM security_commands WHERE command=?", (command_id,)
        ).fetchone()
        if old:
            require(old["digest"] == digest, "Command replay differs")
            require(
                _equal(_config(runtime, expected_runtime_sha256), cfg) and _code_pins() == code,
                "Runtime changed during replay",
            )
            return decode(old["result"])
        require(
            state["revision"] == expected_revision and prior == expected_state_sha256,
            "Runtime revision or state conflict",
        )
        require(at >= state["event_at"], "Action precedes current state")
        outcome = {}
        if action == "RECONCILE":
            require(payload == {}, "Reconciliation takes no claimed outcome")
            outcome = {
                "missing_intake": sorted(set(cfg["subjects"]) - set(state["subjects"])),
                "missing_triage": sorted(
                    k for k, v in state["subjects"].items() if "triage" not in v
                ),
                "missing_handoff": sorted(
                    k
                    for k, v in state["subjects"].items()
                    if v.get("triage")
                    in ("LOCAL_RESPONSE_REQUIRED", "LOCAL_COLLECTION_RESPONSE_REQUIRED")
                    and "handoff" not in v
                ),
                "missing_source_inspection": sorted(
                    k
                    for k, v in state["subjects"].items()
                    if v.get("triage")
                    in ("LOCAL_RESPONSE_REQUIRED", "LOCAL_COLLECTION_RESPONSE_REQUIRED")
                    and "inspection" not in v
                ),
                "declared_subject_count": len(cfg["subjects"]),
            }
        else:
            keys = {
                "INTAKE": {"subject_id"},
                "TRIAGE": {"subject_id"},
                "HANDOFF": {"subject_id", "person_id"},
                "RECORD_ACTION": {"subject_id", "source_pins"},
            }[action]
            require(set(payload) == keys, "Exact action fields required")
            subject = payload["subject_id"]
            require(isinstance(subject, str) and subject in cfg["subjects"], "Undeclared subject")
            entry = state["subjects"].get(subject)
            if action == "INTAKE":
                require(entry is None, "Subject already received")
                state["subjects"][subject] = {"intake_at": at}
            else:
                require(entry is not None, "Intake required")
                if action == "TRIAGE":
                    require("triage" not in entry, "Subject already triaged")
                    entry["triage"] = cfg["local_rules"][cfg["subjects"][subject]["basis"]]
                    entry["triage_at"] = at
                    outcome = {"classification": entry["triage"]}
                elif action == "HANDOFF":
                    require(
                        entry.get("triage")
                        in ("LOCAL_RESPONSE_REQUIRED", "LOCAL_COLLECTION_RESPONSE_REQUIRED")
                        and "handoff" not in entry,
                        "Required local response and new handoff required",
                    )
                    require(
                        payload["person_id"] == cfg["local_handoff_person_id"],
                        "Supported local handoff identity required",
                    )
                    entry["handoff"] = {
                        "person_id": payload["person_id"],
                        "event_at": at,
                        "basis": cfg["assignment_basis"],
                    }
                else:
                    require(
                        "handoff" in entry and "inspection" not in entry,
                        "Explicit prior handoff and new inspection required",
                    )
                    refs = payload["source_pins"]
                    require(
                        isinstance(refs, list) and 1 <= len(refs) <= 8,
                        "Bounded exact inspection sources required",
                    )
                    for ref in refs:
                        exact_pin(ref)
                        require(
                            any(_equal(ref, r) for r in cfg["source_pins"]),
                            "Inspection source outside retained originals",
                        )
                    require(
                        len({_identity(r) for r in refs}) == len(refs)
                        and any(_equal(r, cfg["subjects"][subject]["source"]) for r in refs),
                        "Unique inspection must include subject original",
                    )
                    # Reading and hashing bytes is the performed operation; no claimed remediation.
                    outcome = {
                        "inspection": "EXACT_RETAINED_BYTES_REHASHED",
                        "source_pins": refs,
                        "company_remediation_performed": False,
                    }
                    entry["inspection"] = {"event_at": at, **outcome}
        state["revision"] += 1
        state["event_at"] = at
        current = sha(encoded(state))
        body = {
            **command,
            "prior_state_sha256": prior,
            "state_sha256": current,
            "outcome": outcome,
            "qualification": QUALIFICATION,
            "incident_closed": False,
            "whole_period_coverage": False,
            "execution_implementation_sha256": code,
        }
        record = "OP-" + sha(encoded([cfg["runtime_id"], command_id]))
        operation = _insert(
            db,
            cfg,
            SYSTEMS[3] if action == "RECONCILE" else SYSTEMS[1],
            record,
            body,
            at,
            command_id,
        )
        state_ref = _insert(
            db,
            cfg,
            SYSTEMS[2],
            record,
            {"operation": operation, "state": state},
            at,
            "STATE-" + sha(command_id.encode()),
        )
        result = {
            "revision": state["revision"],
            "state_sha256": current,
            "operation": operation,
            "state": state_ref,
            "outcome": outcome,
            "incident_closed": False,
        }
        require(
            _equal(_config(runtime, expected_runtime_sha256), cfg) and _code_pins() == code,
            "Sources or implementation changed before commit",
        )
        db.execute(
            "UPDATE security_state SET body=?,digest=? WHERE id=1", (encoded(state), current)
        )
        db.execute(
            "INSERT INTO security_commands VALUES(?,?,?)", (command_id, digest, encoded(result))
        )
    return result
