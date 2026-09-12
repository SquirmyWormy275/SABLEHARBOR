"""Authenticated local command boundary and append-only, replayable assessment history.

Credential holders receive only configured workflow permissions. These local grants
are not corporate appointments. The database/filesystem administrator remains trusted.
"""

import copy
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from enterprise.ccf.registry import canonical, digest

from . import testing
from .testing import instant, nonempty

PERMISSIONS = {"prepare", "review", "admin"}


def now():
    return datetime.now(timezone.utc).isoformat()


def implementation_digest():
    return digest(
        {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__), Path(testing.__file__))
        }
    )


def connect(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise ValueError("Workflow database must be an existing private regular file")
    db = sqlite3.connect(path, isolation_level=None)
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=5000")
    db.row_factory = sqlite3.Row
    return db


def initialize(path, plans, principals):
    """Exclusive creation; return random credentials once for private delivery."""
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise ValueError("Use a new database path")
    if not plans or not principals or len({p["id"] for p in principals}) != len(principals):
        raise ValueError("Plans and unique principals required")
    for p in principals:
        nonempty(p["id"])
        if not p["permissions"] or not set(p["permissions"]) <= PERMISSIONS or not p["boundaries"]:
            raise ValueError("Invalid principal permissions/boundaries")
        if instant(p["valid_from"]) >= instant(p["expires_at"]):
            raise ValueError("Invalid principal interval")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    db = sqlite3.connect(path)
    tokens = {}
    try:
        db.executescript("""
            CREATE TABLE config (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
            CREATE TABLE principal (id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE, payload TEXT NOT NULL);
            CREATE TABLE event (seq INTEGER PRIMARY KEY, case_id TEXT NOT NULL, revision INTEGER NOT NULL,
                action TEXT NOT NULL, actor TEXT NOT NULL REFERENCES principal(id), at TEXT NOT NULL,
                payload TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE,
                UNIQUE(case_id, revision));
            CREATE TABLE revocation (principal_id TEXT PRIMARY KEY REFERENCES principal(id), actor TEXT NOT NULL REFERENCES principal(id), at TEXT NOT NULL);
        """)
        db.execute(
            "INSERT INTO config VALUES (1,?)",
            (
                canonical(
                    dict(
                        schema_version=1, implementation_digest=implementation_digest(), plans=plans
                    )
                ),
            ),
        )
        for p in principals:
            token = secrets.token_urlsafe(32)
            tokens[p["id"]] = token
            db.execute(
                "INSERT INTO principal VALUES (?,?,?)",
                (p["id"], hashlib.sha256(token.encode()).hexdigest(), canonical(p)),
            )
        for table in ("config", "principal", "event", "revocation"):
            for verb in ("UPDATE", "DELETE"):
                db.execute(
                    f"CREATE TRIGGER immutable_{table}_{verb} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable workflow history'); END"
                )
        db.commit()
    finally:
        db.close()
    return tokens


def configuration(db):
    result = json.loads(db.execute("SELECT payload FROM config WHERE id=1").fetchone()[0])
    if result["schema_version"] != 1 or result["implementation_digest"] != implementation_digest():
        raise ValueError("Workflow implementation changed; explicit history migration required")
    return result


def principal(db, actor, permission, boundary, at):
    row = db.execute("SELECT payload FROM principal WHERE id=?", (actor,)).fetchone()
    if row is None:
        raise ValueError("Unknown principal")
    p = json.loads(row[0])
    revoked = db.execute("SELECT at FROM revocation WHERE principal_id=?", (actor,)).fetchone()
    if (
        permission not in p["permissions"]
        or boundary not in p["boundaries"]
        or not instant(p["valid_from"]) <= instant(at) < instant(p["expires_at"])
        or (revoked and instant(revoked[0]) <= instant(at))
    ):
        raise ValueError("Principal lacks current scoped permission")
    return p


def authenticate(db, token):
    if not isinstance(token, str) or len(token) < 32:
        raise ValueError("Invalid credential")
    wanted = hashlib.sha256(token.encode()).hexdigest()
    for row in db.execute("SELECT id,token_hash FROM principal"):
        if hmac.compare_digest(row["token_hash"], wanted):
            return row["id"]
    raise ValueError("Invalid credential")


def transition(db, states, config, case_id, action, actor, at, payload):
    states = copy.deepcopy(states)
    s = states.get(case_id)
    if action == "create":
        if s is not None:
            raise ValueError("Case already exists")
        nonempty(case_id)
        p = config["plans"][payload["plan_id"]]
        principal(db, actor, "prepare", p["boundary_id"], at)
        scope = copy.deepcopy(payload["scope"])
        for field in ("period_start", "period_end"):
            scope[field] = instant(scope[field]).isoformat()
        if scope["origin"] not in {"SYNTHETIC", "OPERATOR_SUPPLIED"}:
            raise ValueError("Explicit evidence origin required")
        if instant(scope["period_start"]) > instant(scope["period_end"]):
            raise ValueError("Invalid assessment period")
        for k in ("service", "implementation_version", "criteria_authority"):
            nonempty(scope[k])
        states[case_id] = dict(
            id=case_id,
            revision=1,
            plan_id=p["id"],
            scope=scope,
            assignee=actor,
            preparers=[actor],
            population=None,
            submissions=[],
            reviews=[],
            remediation=[],
            state="AWAITING_POPULATION",
            original_outcome=None,
            historical_failure=False,
            created_at=at,
            mapping_acceptance="NOT_ASSERTED",
            operating_effectiveness="NOT_ASSERTED",
        )
        return states
    if s is None:
        raise ValueError("Unknown case")
    p = config["plans"][s["plan_id"]]
    permission = "prepare" if action in {"intake", "remediate"} else "review"
    principal(db, actor, permission, p["boundary_id"], at)
    if permission == "review" and actor in s["preparers"]:
        raise ValueError("Independent reviewer cannot be a case preparer/remediator")
    if permission == "prepare" and actor != s["assignee"]:
        raise ValueError("Only the assigned preparer can submit")
    if action == "assign":
        if s["state"] not in {"AWAITING_POPULATION", "READY", "FINDING_OPEN"}:
            raise ValueError("Assignment is not allowed in this state")
        principal(db, payload["assignee"], "prepare", p["boundary_id"], at)
        if payload["assignee"] in [r["actor"] for r in s["reviews"]] or (
            s["population"] and payload["assignee"] == s["population"]["registered_by"]
        ):
            raise ValueError("A prior reviewer cannot become the preparer")
        s["assignee"] = payload["assignee"]
        s["preparers"] = sorted(set(s["preparers"] + [payload["assignee"]]))
    elif action == "population":
        if s["state"] != "AWAITING_POPULATION":
            raise ValueError("Population is immutable after independent registration")
        ids = payload["expected_ids"]
        exclusions = payload["excluded_ids"]
        if (
            not isinstance(ids, list)
            or not ids
            or not all(isinstance(x, str) and x for x in ids)
            or len(set(ids)) != len(ids)
        ):
            raise ValueError(
                "Unique nonempty expected IDs required; empty populations need a separate manual applicability decision"
            )
        if (
            not isinstance(exclusions, list)
            or not all(isinstance(x, str) and x for x in exclusions)
            or len(set(exclusions)) != len(exclusions)
            or set(ids) & set(exclusions)
        ):
            raise ValueError("Invalid excluded IDs")
        if type(payload["source_count"]) is not int or payload["source_count"] != len(ids) + len(
            exclusions
        ):
            raise ValueError("Source count does not reconcile with included and excluded IDs")
        for k in (
            "source_system",
            "query",
            "reconciliation",
            "criteria_review",
            "source_export_sha256",
        ):
            nonempty(payload[k])
        if len(payload["source_export_sha256"]) != 64 or any(
            c not in "0123456789abcdef" for c in payload["source_export_sha256"]
        ):
            raise ValueError("Expected source-export SHA256")
        census = json.loads(payload["census_json"])
        if (
            not isinstance(census, list)
            or not all(isinstance(x, str) for x in census)
            or len(census) != len(set(census))
            or set(census) != set(ids) | set(exclusions)
            or hashlib.sha256(payload["census_json"].encode()).hexdigest()
            != payload["source_export_sha256"]
        ):
            raise ValueError(
                "Retained population export differs from declared source IDs or digest"
            )
        if exclusions:
            nonempty(payload["exclusion_rationale"])
        if not instant(s["scope"]["period_end"]) <= instant(payload["captured_at"]) <= instant(at):
            raise ValueError("Population capture must follow period end and not be in future")
        s["population"] = dict(payload, registered_by=actor, registered_at=at)
        s["state"] = "READY"
    elif action == "intake":
        if s["state"] not in {"READY", "REMEDIATION_SUBMITTED"}:
            raise ValueError("Intake requires a registered population or submitted remediation")
        result = testing.evaluate(p, s["scope"], s["population"], payload, at)
        submission = dict(payload=payload, result=result, actor=actor, at=at)
        submission["id"] = digest(submission)
        s["historical_failure"] = s["historical_failure"] or result["outcome"] == "FAIL"
        s["submissions"].append(submission)
        s["state"] = "AWAITING_REVIEW"
    elif action == "review":
        if s["state"] != "AWAITING_REVIEW":
            raise ValueError("No submission awaiting review")
        latest = s["submissions"][-1]
        if payload["submission_id"] != latest["id"]:
            raise ValueError("Review must bind the current submission")
        nonempty(payload["rationale"])
        if payload["decision"] not in {"ACCEPT", "REJECT"}:
            raise ValueError("Invalid review decision")
        if payload["decision"] == "ACCEPT" and instant(at) >= instant(
            latest["payload"]["expires_at"]
        ):
            raise ValueError("Evidence expired before review")
        s["reviews"].append(dict(payload, actor=actor, at=at))
        result = latest["result"]["outcome"] if payload["decision"] == "ACCEPT" else "NOT_RUN"
        if s["original_outcome"] is None:
            # A rejected review must not conceal a computed historical failure.
            s["original_outcome"] = "FAIL" if latest["result"]["outcome"] == "FAIL" else result
        if result != "PASS":
            s["state"] = "FINDING_OPEN"
        elif not s["remediation"]:
            s["state"] = "REVIEWED_PASS"
        elif s["historical_failure"]:
            s["state"] = "RETEST_PASSED_HISTORICAL_FAILURE"
        else:
            s["state"] = "CLOSED_CORRECTED_EVIDENCE"
    elif action == "remediate":
        if s["state"] not in {"FINDING_OPEN", "RETEST_PASSED_HISTORICAL_FAILURE"}:
            raise ValueError("Remediation requires a finding")
        for k in ("change_reference", "action", "due_at"):
            nonempty(payload[k])
        if instant(payload["due_at"]) < instant(at):
            raise ValueError("Remediation due date already passed")
        s["remediation"].append(dict(payload, actor=actor, at=at))
        s["state"] = "REMEDIATION_SUBMITTED"
    elif action == "close_prospectively":
        if (
            s["state"] not in {"REMEDIATION_SUBMITTED", "RETEST_PASSED_HISTORICAL_FAILURE"}
            or not s["historical_failure"]
        ):
            raise ValueError(
                "Prospective closure requires submitted remediation for a historical failure"
            )
        other = states.get(payload["validation_case_id"])
        if (
            other is None
            or other["state"] != "REVIEWED_PASS"
            or other["plan_id"] != s["plan_id"]
            or other["scope"]["origin"] != s["scope"]["origin"]
            or other["scope"]["service"] != s["scope"]["service"]
            or instant(other["scope"]["period_start"]) <= instant(s["scope"]["period_end"])
            or instant(other["created_at"]) < instant(s["remediation"][-1]["at"])
            or instant(other["scope"]["period_start"]) < instant(s["remediation"][-1]["at"])
            or other["scope"]["criteria_authority"] != s["scope"]["criteria_authority"]
            or instant(other["submissions"][-1]["payload"]["expires_at"]) <= instant(at)
        ):
            raise ValueError(
                "Need a fresh independently passed prospective case for the same plan, service and origin"
            )
        if actor in other["preparers"]:
            raise ValueError("Prospective preparer cannot close finding")
        nonempty(payload["rationale"])
        s["closure"] = dict(payload, actor=actor, at=at)
        s["state"] = "CLOSED_PROSPECTIVE_VALIDATION"
    else:
        raise ValueError("Unknown workflow action")
    s["revision"] += 1
    return states


def replay(db):
    config, states, previous = configuration(db), {}, "0" * 64
    last_at = None
    for row in db.execute("SELECT * FROM event ORDER BY seq"):
        body = {
            k: row[k]
            for k in ("seq", "case_id", "revision", "action", "actor", "at", "previous_hash")
        }
        body["payload"] = json.loads(row["payload"])
        if row["previous_hash"] != previous or digest(body) != row["event_hash"]:
            raise ValueError("Workflow event chain changed")
        if last_at is not None and instant(row["at"]) < instant(last_at):
            raise ValueError("Workflow chronology reversed")
        states = transition(
            db,
            states,
            config,
            row["case_id"],
            row["action"],
            row["actor"],
            row["at"],
            body["payload"],
        )
        if states[row["case_id"]]["revision"] != row["revision"]:
            raise ValueError("Workflow revision mismatch")
        previous, last_at = row["event_hash"], row["at"]
    return states


def command(db, token, case_id, action, payload, expected_revision):
    """Credentials determine actor; callers cannot supply actor, clock or result."""
    db.execute("BEGIN IMMEDIATE")
    try:
        actor, at = authenticate(db, token), now()
        states, config = replay(db), configuration(db)
        current = states.get(case_id, {}).get("revision", 0)
        if type(expected_revision) is not int or current != expected_revision:
            raise ValueError("Stale workflow revision; reload before submitting")
        last = db.execute(
            "SELECT seq,at,event_hash FROM event ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        if last and instant(at) < instant(last["at"]):
            raise ValueError("Clock moved before recorded history")
        updated = transition(db, states, config, case_id, action, actor, at, copy.deepcopy(payload))
        body = dict(
            seq=last["seq"] + 1 if last else 1,
            case_id=case_id,
            revision=current + 1,
            action=action,
            actor=actor,
            at=at,
            payload=payload,
            previous_hash=last["event_hash"] if last else "0" * 64,
        )
        db.execute(
            "INSERT INTO event VALUES (?,?,?,?,?,?,?,?,?)",
            (
                body["seq"],
                case_id,
                body["revision"],
                action,
                actor,
                at,
                canonical(payload),
                body["previous_hash"],
                digest(body),
            ),
        )
        db.execute("COMMIT")
        return updated[case_id]
    except Exception:
        db.execute("ROLLBACK")
        raise


def revoke(db, token, subject):
    db.execute("BEGIN IMMEDIATE")
    try:
        actor, at = authenticate(db, token), now()
        row = db.execute("SELECT payload FROM principal WHERE id=?", (subject,)).fetchone()
        if not row:
            raise ValueError("Unknown principal")
        for boundary in json.loads(row[0])["boundaries"]:
            principal(db, actor, "admin", boundary, at)
        latest = db.execute("SELECT MAX(at) FROM event").fetchone()[0]
        if latest and instant(at) <= instant(latest):
            raise ValueError("Revocation must follow recorded history")
        db.execute("INSERT INTO revocation VALUES (?,?,?)", (subject, actor, at))
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise


def report(db, token):
    actor, at = authenticate(db, token), now()
    states, config = replay(db), configuration(db)
    visible = {}
    for cid, state in states.items():
        boundary = config["plans"][state["plan_id"]]["boundary_id"]
        for permission in ("prepare", "review", "admin"):
            try:
                principal(db, actor, permission, boundary, at)
                break
            except ValueError:
                continue
        else:
            continue
        state["evidence_fresh"] = bool(state["submissions"]) and instant(
            state["submissions"][-1]["payload"]["expires_at"]
        ) > instant(at)
        state["remediation_overdue"] = (
            bool(state["remediation"])
            and not state["state"].startswith("CLOSED")
            and instant(state["remediation"][-1]["due_at"]) < instant(at)
        )
        visible[cid] = state
    periods = {}
    for cid, state in visible.items():
        key = digest(
            {
                "plan_id": state["plan_id"],
                **{
                    k: state["scope"][k]
                    for k in ("origin", "service", "period_start", "period_end")
                },
            }
        )
        group = periods.setdefault(
            key,
            dict(
                plan_id=state["plan_id"],
                scope={
                    k: state["scope"][k]
                    for k in ("origin", "service", "period_start", "period_end")
                },
                case_ids=[],
                result="PASS",
            ),
        )
        group["case_ids"].append(cid)
        if state["historical_failure"]:
            group["result"] = "FAIL"
        elif group["result"] != "FAIL" and (
            state["state"] not in {"REVIEWED_PASS", "CLOSED_CORRECTED_EVIDENCE"}
            or not state["evidence_fresh"]
        ):
            group["result"] = "NOT_RUN"
    return dict(
        period_results=periods,
        as_of=at,
        cases=visible,
        scope="LOCAL_WORKFLOW_ONLY_NO_FRAMEWORK_ACCEPTANCE",
        verified_history=True,
    )
