"""Explicit personal coordination between authorized workspace members; never audit work."""

import os
import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .inference import _json as decode
from .personal_views import PersonalViews, _reference
from .store import DomainError, canonical, digest
from .workspace_context import COLLECTIONS, _basis, _resolve

FORMAT = "PRIVATE_INVESTIGATION_HANDOFF_ARCHIVE_V1"
LIMIT = 64 * 1024 * 1024
MAX_DOCUMENTS = 4096
TRANSITIONS = {
    "ACCEPT": ("OFFERED", "ACCEPTED", "RECIPIENT"),
    "DECLINE": ("OFFERED", "DECLINED", "RECIPIENT"),
    "WITHDRAW": ("OFFERED", "WITHDRAWN", "SENDER"),
    "COMPLETE": ("ACCEPTED", "COMPLETED", "RECIPIENT"),
}
DOC_FIELDS = {
    "id",
    "version",
    "engagement_id",
    "sender_id",
    "recipient_id",
    "author_id",
    "action",
    "status",
    "recorded_at",
    "engagement_revision",
    "basis",
    "user",
    "response",
    "previous_sha256",
    "command_id",
}


def require(value, message, *, status=400, code="INVALID_HANDOFF"):
    if not value:
        raise DomainError(message, status=status, code=code)


def text(value, maximum, *, nonempty=False):
    require(
        isinstance(value, str) and len(value) <= maximum and (not nonempty or value.strip()),
        "Bounded explicit handoff text required",
    )
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise DomainError("Valid Unicode handoff text required") from exc


def sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def freeze(value):
    try:
        return decode(canonical(value))
    except (ValueError, TypeError, RecursionError) as exc:
        raise DomainError("Strict finite handoff data required") from exc


def links_shape(links):
    require(isinstance(links, list) and len(links) <= 8, "At most eight explicit links required")
    seen = set()
    for ref in links:
        require(
            isinstance(ref, dict) and set(ref) == {"kind", "id", "version", "sha256"},
            "Exact reference required",
        )
        require(
            isinstance(ref["kind"], str) and ref["kind"] in COLLECTIONS,
            "Supported reference kind required",
        )
        text(ref["id"], 256, nonempty=True)
        require(
            ref["version"] is None or type(ref["version"]) is int and ref["version"] > 0,
            "Exact positive reference version required",
        )
        require(sha(ref["sha256"]), "Exact reference hash required")
        key = (ref["kind"], ref["id"], ref["version"])
        require(key not in seen, "Duplicate handoff reference")
        seen.add(key)


def user_shape(user):
    require(
        isinstance(user, dict) and set(user) == {"title", "question", "next_step", "links"},
        "Exact authored handoff fields required",
    )
    text(user["title"], 120, nonempty=True)
    text(user["question"], 2000, nonempty=True)
    text(user["next_step"], 1000, nonempty=True)
    links_shape(user["links"])


def _chain(rows):
    prior = None
    for row in rows:
        require(
            isinstance(row, dict)
            and set(row)
            == {"id", "version", "engagement", "sender", "recipient", "content", "sha256"},
            "Exact handoff document row required",
        )
        require(
            isinstance(row["content"], str) and len(row["content"].encode()) <= 32768,
            "Bounded handoff document required",
        )
        try:
            value = decode(row["content"])
        except (ValueError, TypeError) as exc:
            raise DomainError("Invalid retained handoff document") from exc
        require(
            isinstance(value, dict) and set(value) == DOC_FIELDS and digest(value) == row["sha256"],
            "Handoff document integrity failure",
            code="INTEGRITY",
            status=500,
        )
        for key in ("id", "engagement_id", "sender_id", "recipient_id", "author_id", "command_id"):
            text(value[key], 256, nonempty=True)
        require(value["sender_id"] != value["recipient_id"], "Distinct participants required")
        require(
            type(value["version"]) is int
            and value["version"] == (prior["version"] + 1 if prior else 1),
            "Contiguous handoff versions required",
        )
        require(
            type(value["engagement_revision"]) is int and value["engagement_revision"] >= 0,
            "Exact engagement revision required",
        )
        require(
            (row["id"], row["version"], row["engagement"], row["sender"], row["recipient"])
            == (
                value["id"],
                value["version"],
                value["engagement_id"],
                value["sender_id"],
                value["recipient_id"],
            ),
            "Handoff routing integrity failure",
        )
        require(type(row["version"]) is int, "Exact document row version required")
        require(
            isinstance(value["basis"], dict)
            and set(value["basis"]) == {value["sender_id"], value["recipient_id"]}
            and all(sha(x) for x in value["basis"].values()),
            "Exact participant basis pins required",
        )
        try:
            stamp = datetime.fromisoformat(value["recorded_at"])
            require(stamp.tzinfo is not None, "Aware handoff timestamp required")
        except (ValueError, TypeError) as exc:
            raise DomainError("Valid handoff timestamp required") from exc
        user_shape(value["user"])
        text(value["response"], 4000)
        if prior is None:
            require(
                value["action"] == "OFFER"
                and value["status"] == "OFFERED"
                and value["author_id"] == value["sender_id"]
                and value["previous_sha256"] is None
                and value["response"] == "",
                "Invalid initial handoff",
            )
        else:
            action = value["action"]
            require(isinstance(action, str) and action in TRANSITIONS, "Invalid handoff action")
            old, new, role = TRANSITIONS[action]
            require(
                prior["status"] == old
                and value["status"] == new
                and value["author_id"]
                == value["sender_id" if role == "SENDER" else "recipient_id"],
                "Invalid handoff transition",
            )
            require(value["previous_sha256"] == digest(prior), "Handoff history chain differs")
            for key in ("id", "engagement_id", "sender_id", "recipient_id", "basis", "user"):
                require(
                    canonical(value[key]) == canonical(prior[key]),
                    "Original handoff content changed",
                )
            require(
                value["engagement_revision"] >= prior["engagement_revision"],
                "Handoff revision regressed",
            )
            if action == "COMPLETE":
                text(value["response"], 4000, nonempty=True)
        prior = value
    require(prior is not None, "Handoff history missing", status=404)
    return prior


def validate_snapshot(body):
    """Validate a bounded logical inert archive; does not authorize live restore or principals."""
    body = freeze(body)
    require(
        isinstance(body, dict)
        and set(body) == {"format", "documents", "commands"}
        and body["format"] == FORMAT,
        "Exact handoff archive required",
    )
    require(
        isinstance(body["documents"], list)
        and isinstance(body["commands"], list)
        and len(body["documents"]) <= MAX_DOCUMENTS
        and len(body["commands"]) <= MAX_DOCUMENTS,
        "Bounded handoff archive required",
    )
    require(len(canonical(body).encode()) <= LIMIT, "Handoff archive byte limit exceeded")
    groups = {}
    documents = {}
    for row in body["documents"]:
        require(
            isinstance(row, dict)
            and isinstance(row.get("id"), str)
            and type(row.get("version")) is int,
            "Typed document identity required",
        )
        key = (row["id"], row["version"])
        require(key not in documents, "Duplicate archived handoff document")
        documents[key] = row
        groups.setdefault(row["id"], []).append(row)
    for rows in groups.values():
        _chain(sorted(rows, key=lambda r: r["version"]))
    seen = set()
    matched = set()
    for command in body["commands"]:
        require(
            isinstance(command, dict)
            and set(command)
            == {"actor", "engagement", "command_id", "digest", "handoff_id", "version"},
            "Exact archived command required",
        )
        for key in ("actor", "engagement", "command_id", "handoff_id"):
            text(command[key], 256, nonempty=True)
        require(
            type(command["version"]) is int and sha(command["digest"]),
            "Exact archived receipt identity required",
        )
        key = (command["actor"], command["engagement"], command["command_id"])
        target = (command["handoff_id"], command["version"])
        require(
            key not in seen and target in documents and target not in matched,
            "Duplicate or missing command target",
        )
        value = decode(documents[target]["content"])
        require(
            (value["author_id"], value["engagement_id"], value["command_id"]) == key,
            "Command author association differs",
        )
        seen.add(key)
        matched.add(target)
    require(matched == set(documents), "Document command receipt missing")
    return body


class InvestigationHandoffs:
    def __init__(self, private_root, engine, *, max_active=16):
        self.root = Path(private_root).absolute()
        self.path = self.root / "handoffs.sqlite3"
        self.engine = engine
        require(
            type(max_active) is int and 1 <= max_active <= 32, "Active handoff quota must be1–32"
        )
        self.max_active = max_active
        self._private(self.root, True)
        if self.path.exists():
            self._private(self.path)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with self._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS documents(id TEXT,version INTEGER,engagement TEXT,
              sender TEXT,recipient TEXT,content TEXT NOT NULL,sha256 TEXT NOT NULL,
              PRIMARY KEY(id,version));
            CREATE TABLE IF NOT EXISTS commands(actor TEXT,engagement TEXT,command_id TEXT,
              digest TEXT,handoff_id TEXT,version INTEGER,
              PRIMARY KEY(actor,engagement,command_id));
            CREATE TRIGGER IF NOT EXISTS handoff_documents_no_update BEFORE UPDATE ON documents
              BEGIN SELECT RAISE(ABORT,'Immutable handoff history'); END;
            CREATE TRIGGER IF NOT EXISTS handoff_documents_no_delete BEFORE DELETE ON documents
              BEGIN SELECT RAISE(ABORT,'Immutable handoff history'); END;
            CREATE TRIGGER IF NOT EXISTS handoff_commands_no_update BEFORE UPDATE ON commands
              BEGIN SELECT RAISE(ABORT,'Immutable handoff command'); END;
            CREATE TRIGGER IF NOT EXISTS handoff_commands_no_delete BEFORE DELETE ON commands
              BEGIN SELECT RAISE(ABORT,'Immutable handoff command'); END;
            """)

    _private = staticmethod(PersonalViews._private)

    @contextmanager
    def _db(self):
        self._private(self.root, True)
        before = self._private(self.path)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
                require(self._private(self.path) == before, "Handoff database identity changed")
                self._private(self.root, True)
        finally:
            db.close()

    def _state(self, actor, eid):
        permission = self.engine.store.membership(actor, eid)
        require(
            permission in {"learn", "review", "instruct"},
            "Current workspace membership required",
            status=403,
        )
        state = self.engine.get(actor, eid)
        return state, digest({**_basis(state), "membership": permission})

    def _recheck(self, actor, eid, state, basis):
        current, current_basis = self._state(actor, eid)
        require(
            current["revision"] == state["revision"] and current_basis == basis,
            "Workspace changed during handoff",
            code="HANDOFF_CONTEXT_CONFLICT",
            status=409,
        )

    def _row(self, db, actor, eid, identifier):
        rows = [
            dict(row)
            for row in db.execute(
                "SELECT * FROM documents WHERE id=? AND engagement=? "
                "AND (sender=? OR recipient=?) ORDER BY version",
                (identifier, eid, actor, actor),
            )
        ]
        value = _chain(rows)
        commands = [
            dict(row)
            for row in db.execute(
                "SELECT * FROM commands WHERE handoff_id=? ORDER BY version", (identifier,)
            )
        ]
        validate_snapshot({"format": FORMAT, "documents": rows, "commands": commands})
        return value

    def _shared(self, content):
        states = {}
        for actor in (content["sender_id"], content["recipient_id"]):
            try:
                state, basis = self._state(actor, content["engagement_id"])
            except DomainError as exc:
                if exc.status in {401, 403, 404}:
                    return "PARTICIPANT_UNAVAILABLE", states
                raise
            states[actor] = (state, basis)
            if basis != content["basis"][actor]:
                return "CONTEXT_CHANGED", states
        try:
            for state, _ in states.values():
                for ref in content["user"]["links"]:
                    _reference(state, ref)
        except DomainError:
            return "TARGET_UNAVAILABLE", states
        return "CURRENT", states

    def _projection(self, content, actor, state):
        context, states = self._shared(content)
        role = "SENDER" if actor == content["sender_id"] else "RECIPIENT"
        allowed = []
        for action, (prior, _, owner) in TRANSITIONS.items():
            if (
                prior == content["status"]
                and owner == role
                and (action in {"WITHDRAW", "DECLINE"} or context == "CURRENT")
            ):
                allowed.append(action)
        output = {
            key: content[key]
            for key in (
                "id",
                "version",
                "status",
                "engagement_id",
                "sender_id",
                "recipient_id",
                "engagement_revision",
                "recorded_at",
                "author_id",
            )
        }
        output.update(
            current_engagement_revision=state["revision"],
            acting_role=role,
            context_status=context,
            shared_content_visible=context == "CURRENT",
            allowed_actions=allowed,
            coordination_only=True,
            formal_work_mutated=False,
            backup_status="EXPLICIT_INERT_ARCHIVE_SUPPORTED_NOT_AUTOMATICALLY_BACKED_UP",
        )
        if context == "CURRENT":
            output["content"] = {
                **content["user"],
                "response": content["response"],
                "response_author_id": content["author_id"] if content["response"] else None,
            }
        for principal, (current, basis) in states.items():
            self._recheck(principal, content["engagement_id"], current, basis)
        return output

    def directory(self, actor, engagement):
        state, basis = self._state(actor, engagement)
        with self.engine.store.connect() as db:
            members = [
                dict(row)
                for row in db.execute(
                    "SELECT p.id,p.name AS display_name,m.permission FROM principals p "
                    "JOIN members m ON m.principal=p.id WHERE m.engagement=? AND p.id!=? "
                    "AND m.permission IN ('learn','review','instruct') "
                    "AND p.revoked=0 AND p.expires>? ORDER BY p.id",
                    (engagement, actor, time.time()),
                )
            ]
            require(len(members) <= 200, "Workspace directory bound exceeded", status=429)
            for row in members:
                self.engine.store._principal(db, row["id"])
        for member in members:
            require(
                self.engine.store.membership(member["id"], engagement) == member["permission"],
                "Workspace directory changed",
                status=409,
            )
        self._recheck(actor, engagement, state, basis)
        return {
            "engagement_id": engagement,
            "engagement_revision": state["revision"],
            "members": members,
        }

    def make_reference(self, actor, engagement, *, recipient_id, kind, record_id, version=None):
        require(actor != recipient_id, "Choose another workspace member")
        first, basis = self._state(actor, engagement)
        second, other_basis = self._state(recipient_id, engagement)
        ref, _ = _resolve(first, kind, record_id, version)
        _reference(first, ref)
        _reference(second, ref)
        self._recheck(actor, engagement, first, basis)
        self._recheck(recipient_id, engagement, second, other_basis)
        return ref

    def read(self, actor, engagement, handoff_id):
        state, basis = self._state(actor, engagement)
        with self._db() as db:
            db.execute("BEGIN")
            content = self._row(db, actor, engagement, handoff_id)
            output = self._projection(content, actor, state)
            self._recheck(actor, engagement, state, basis)
        return output

    def listing(self, actor, engagement):
        state, basis = self._state(actor, engagement)
        with self._db() as db:
            db.execute("BEGIN")
            ids = [
                row[0]
                for row in db.execute(
                    "SELECT DISTINCT id FROM documents WHERE engagement=? "
                    "AND (sender=? OR recipient=?) ORDER BY id",
                    (engagement, actor, actor),
                )
            ]
            require(len(ids) <= 128, "Handoff listing bound exceeded", status=429)
            results = [
                self._projection(self._row(db, actor, engagement, identifier), actor, state)
                for identifier in ids
            ]
            self._recheck(actor, engagement, state, basis)
        return results

    def offer(self, actor, engagement, payload, *, expected_engagement_revision, command_id):
        return self._write(
            actor,
            engagement,
            None,
            payload,
            action="OFFER",
            response="",
            expected_version=None,
            expected_engagement_revision=expected_engagement_revision,
            command_id=command_id,
        )

    def transition(
        self,
        actor,
        engagement,
        handoff_id,
        *,
        action,
        response,
        expected_version,
        expected_engagement_revision,
        command_id,
    ):
        require(
            isinstance(action, str) and action in TRANSITIONS,
            "Supported explicit handoff transition required",
        )
        return self._write(
            actor,
            engagement,
            handoff_id,
            None,
            action=action,
            response=response,
            expected_version=expected_version,
            expected_engagement_revision=expected_engagement_revision,
            command_id=command_id,
        )

    def _write(
        self,
        actor,
        engagement,
        identifier,
        payload,
        *,
        action,
        response,
        expected_version,
        expected_engagement_revision,
        command_id,
    ):
        payload = freeze(payload)
        text(command_id, 128, nonempty=True)
        text(response, 4000)
        require(
            type(expected_engagement_revision) is int and expected_engagement_revision >= 0,
            "Exact engagement revision required",
        )
        state, basis = self._state(actor, engagement)
        fingerprint = digest(
            {
                "id": identifier,
                "payload": payload,
                "action": action,
                "response": response,
                "expected_version": expected_version,
                "expected_engagement_revision": expected_engagement_revision,
            }
        )
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT * FROM commands WHERE actor=? AND engagement=? AND command_id=?",
                (actor, engagement, command_id),
            ).fetchone()
            if old:
                require(
                    old["digest"] == fingerprint,
                    "Handoff command reused with changed input",
                    status=409,
                )
                value = self._row(db, actor, engagement, old["handoff_id"])
            else:
                require(
                    state["revision"] == expected_engagement_revision,
                    "Workspace changed before handoff",
                    status=409,
                    code="HANDOFF_CONTEXT_CONFLICT",
                )
                if action == "OFFER":
                    require(
                        isinstance(payload, dict)
                        and set(payload)
                        == {"recipient_id", "title", "question", "next_step", "links"},
                        "Exact handoff offer required",
                    )
                    recipient = payload["recipient_id"]
                    text(recipient, 256, nonempty=True)
                    require(recipient != actor, "Choose another workspace member")
                    user = {
                        key: payload[key] for key in ("title", "question", "next_step", "links")
                    }
                    user_shape(user)
                    other, other_basis = self._state(recipient, engagement)
                    for ref in user["links"]:
                        _reference(state, ref)
                        _reference(other, ref)
                    for participant in (actor, recipient):
                        ids = [
                            row[0]
                            for row in db.execute(
                                "SELECT DISTINCT id FROM documents WHERE engagement=? "
                                "AND (sender=? OR recipient=?)",
                                (engagement, participant, participant),
                            )
                        ]
                        require(
                            len(ids) < 64, "Participant lifetime handoff quota reached", status=429
                        )
                        active = sum(
                            self._row(db, participant, engagement, item)["status"]
                            in {"OFFERED", "ACCEPTED"}
                            for item in ids
                        )
                        require(
                            active < self.max_active,
                            "Participant active handoff quota reached",
                            status=429,
                        )
                    identifier = "HANDOFF-" + digest([actor, engagement, command_id])[:32]
                    value = {
                        "id": identifier,
                        "version": 1,
                        "engagement_id": engagement,
                        "sender_id": actor,
                        "recipient_id": recipient,
                        "basis": {actor: basis, recipient: other_basis},
                        "user": user,
                        "status": "OFFERED",
                        "previous_sha256": None,
                    }
                    self._recheck(recipient, engagement, other, other_basis)
                else:
                    prior = self._row(db, actor, engagement, identifier)
                    require(
                        type(expected_version) is int and prior["version"] == expected_version,
                        "Handoff version changed",
                        status=409,
                        code="HANDOFF_CONFLICT",
                    )
                    before, after, role = TRANSITIONS[action]
                    require(
                        prior["status"] == before
                        and actor == prior["sender_id" if role == "SENDER" else "recipient_id"],
                        "Handoff action unavailable to this participant",
                        status=403,
                    )
                    if action not in {"WITHDRAW", "DECLINE"}:
                        current = self._projection(prior, actor, state)
                        require(
                            current["shared_content_visible"],
                            "Shared handoff context or exact target unavailable",
                            status=409,
                        )
                    if action == "COMPLETE":
                        text(response, 4000, nonempty=True)
                    value = {
                        **prior,
                        "version": prior["version"] + 1,
                        "status": after,
                        "previous_sha256": digest(prior),
                    }
                value.update(
                    author_id=actor,
                    action=action,
                    response=response,
                    command_id=command_id,
                    engagement_revision=state["revision"],
                    recorded_at=datetime.now(UTC).isoformat(),
                )
                raw = canonical(value)
                require(len(raw.encode()) <= 32768, "Handoff document byte limit exceeded")
                count, size = db.execute(
                    "SELECT count(*),COALESCE(sum(length(CAST(content AS BLOB))),0) FROM documents"
                ).fetchone()
                require(
                    count < MAX_DOCUMENTS and size + len(raw.encode()) <= LIMIT,
                    "Private handoff storage quota reached",
                    status=429,
                )
                self._recheck(actor, engagement, state, basis)
                db.execute(
                    "INSERT INTO documents VALUES(?,?,?,?,?,?,?)",
                    (
                        identifier,
                        value["version"],
                        engagement,
                        value["sender_id"],
                        value["recipient_id"],
                        raw,
                        digest(value),
                    ),
                )
                db.execute(
                    "INSERT INTO commands VALUES(?,?,?,?,?,?)",
                    (actor, engagement, command_id, fingerprint, identifier, value["version"]),
                )
                self._row(db, actor, engagement, identifier)
            output = self._projection(value, actor, state)
            if old is None and action not in {"WITHDRAW", "DECLINE"}:
                require(
                    output["shared_content_visible"],
                    "Shared handoff context changed before commit",
                    status=409,
                )
            self._recheck(actor, engagement, state, basis)
        return output

    def snapshot(self):
        with self._db() as db:
            db.execute("BEGIN")
            body = {
                "format": FORMAT,
                "documents": [
                    dict(row) for row in db.execute("SELECT * FROM documents ORDER BY id,version")
                ],
                "commands": [
                    dict(row)
                    for row in db.execute(
                        "SELECT * FROM commands ORDER BY actor,engagement,command_id"
                    )
                ],
            }
            return validate_snapshot(body)
