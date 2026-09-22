"""Explicit personal visit baselines; neither reading acknowledgment nor audit work."""

import os
import re
from datetime import UTC, datetime
from pathlib import Path

from .inference import _json
from .personal_views import PersonalViews, _reference, _text
from .store import DomainError, canonical, digest
from .workspace_context import COLLECTIONS, _resolve

MAX_PINS = 10000
MAX_BYTES = 2 * 1024 * 1024
MAX_HISTORY = 100
QUALIFICATION = "SIX_SUPPORTED_RECORD_TYPES_ONLY_NOT_READ_INSPECTED_TESTED_OR_ACCEPTED"


def require(value, message, code="CHECKPOINT_INVALID", status=400):
    if not value:
        raise DomainError(message, code=code, status=status)


def _inventory(state):
    """Only current authorized projection metadata, never original bytes or private stores."""
    result = []
    for kind, collection in COLLECTIONS.items():
        rows = state.get(collection, [])
        require(isinstance(rows, list), "Record inventory unavailable", "INPUT_DATA_UNAVAILABLE")
        require(len(rows) <= MAX_PINS, "Record limit exceeded", "INPUT_LIMIT_EXCEEDED")
        seen = set()
        for row in rows:
            require(isinstance(row, dict), "Malformed record", "INPUT_DATA_UNAVAILABLE")
            ident = row.get("id")
            require(
                isinstance(ident, str) and ident and ident not in seen,
                "Ambiguous record identity",
                "INPUT_DATA_UNAVAILABLE",
            )
            seen.add(ident)
            if kind == "artifact" and (
                row.get("status") != "AVAILABLE" or row.get("audience", "LEARNER") != "LEARNER"
            ):
                continue
            if kind == "artifact":
                available = row.get("available_at") or row.get("source", {}).get("receipt", {}).get(
                    "source", {}
                ).get("available_at")
                if available is not None:
                    try:
                        at = datetime.fromisoformat(available.replace("Z", "+00:00"))
                        cutoff = datetime.fromisoformat(
                            state["simulated_at"].replace("Z", "+00:00")
                        )
                        require(
                            at.tzinfo is not None and cutoff.tzinfo is not None,
                            "Explicit source time required",
                            "INPUT_DATA_UNAVAILABLE",
                        )
                    except (AttributeError, TypeError, ValueError, KeyError) as exc:
                        raise DomainError(
                            "Source time unavailable", code="INPUT_DATA_UNAVAILABLE"
                        ) from exc
                    if at > cutoff:
                        continue
            if kind == "task" and row.get("status") in {"EXCLUDED", "NOT_APPLICABLE"}:
                continue
            versions = row.get("versions", []) if kind == "workpaper" else [row]
            require(
                isinstance(versions, list) and len(versions) <= MAX_PINS,
                "Version limit exceeded",
                "INPUT_LIMIT_EXCEEDED",
            )
            version_ids = set()
            for record in versions:
                require(isinstance(record, dict), "Malformed version", "INPUT_DATA_UNAVAILABLE")
                version = record.get("version")
                require(
                    version is None or type(version) is int,
                    "Invalid version",
                    "INPUT_DATA_UNAVAILABLE",
                )
                require(version not in version_ids, "Ambiguous version", "INPUT_DATA_UNAVAILABLE")
                version_ids.add(version)
                try:
                    ref, _ = _resolve(state, kind, ident, version)
                    _reference(state, ref)
                except DomainError:
                    # Out-of-scope records are never copied from a legacy projected row.
                    continue
                result.append({"reference": ref, "record_sha256": digest(record)})
                require(len(result) <= MAX_PINS, "Record limit exceeded", "INPUT_LIMIT_EXCEEDED")
    result.sort(key=lambda r: canonical(r["reference"]))
    require(
        len(canonical(result).encode()) <= MAX_BYTES,
        "Checkpoint byte limit exceeded",
        "INPUT_LIMIT_EXCEEDED",
    )
    return result


def inventory(state):
    try:
        return _inventory(state)
    except DomainError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError, OverflowError) as exc:
        raise DomainError(
            "Authorized record inventory unavailable", code="INPUT_DATA_UNAVAILABLE"
        ) from exc


def _key(row):
    r = row["reference"]
    # Non-workpaper versions describe the same record changing, never a latest replacement.
    return (r["kind"], r["id"], r["version"] if r["kind"] == "workpaper" else None)


class VisitCheckpoints(PersonalViews):
    """Reuse personal-view authority/private IO guards with an independent new schema."""

    def __init__(self, private_root, engine):
        self.root = Path(private_root).absolute()
        self.engine = engine
        self.path = self.root / "visit-checkpoints.sqlite3"
        self._private(self.root, True)
        if self.path.exists():
            self._private(self.path)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with self._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS checkpoints(actor TEXT,engagement TEXT,version INTEGER,
              PRIMARY KEY(actor,engagement));
            CREATE TABLE IF NOT EXISTS checkpoint_history(actor TEXT,engagement TEXT,
              version INTEGER,content TEXT,sha256 TEXT,PRIMARY KEY(actor,engagement,version));
            CREATE TABLE IF NOT EXISTS checkpoint_commands(actor TEXT,engagement TEXT,
              command_id TEXT,fingerprint TEXT,version INTEGER,
              PRIMARY KEY(actor,engagement,command_id));
            CREATE TRIGGER IF NOT EXISTS checkpoints_history_no_update
              BEFORE UPDATE ON checkpoint_history
              BEGIN SELECT RAISE(ABORT,'Immutable history'); END;
            CREATE TRIGGER IF NOT EXISTS checkpoints_history_no_delete
              BEFORE DELETE ON checkpoint_history
              BEGIN SELECT RAISE(ABORT,'Immutable history'); END;
            CREATE TRIGGER IF NOT EXISTS checkpoints_commands_no_update
              BEFORE UPDATE ON checkpoint_commands
              BEGIN SELECT RAISE(ABORT,'Immutable command'); END;
            CREATE TRIGGER IF NOT EXISTS checkpoints_commands_no_delete
              BEFORE DELETE ON checkpoint_commands
              BEGIN SELECT RAISE(ABORT,'Immutable command'); END;
            """)

    def _load(self, db, actor, engagement):
        _preflight(db, actor, engagement)
        head = db.execute(
            "SELECT version FROM checkpoints WHERE actor=? AND engagement=?", (actor, engagement)
        ).fetchone()
        rows = db.execute(
            "SELECT * FROM checkpoint_history WHERE actor=? AND engagement=? "
            "ORDER BY version LIMIT ?",
            (actor, engagement, MAX_HISTORY + 1),
        ).fetchall()
        require(
            len(rows) <= MAX_HISTORY and (head[0] if head else 0) == len(rows),
            "Checkpoint history mismatch",
            "INTEGRITY",
            500,
        )
        previous = None
        documents = []
        for version, row in enumerate(rows, 1):
            require(
                len(row["content"].encode()) <= MAX_BYTES + 16384,
                "Checkpoint history exceeds bound",
                "INTEGRITY",
                500,
            )
            try:
                body = _json(row["content"])
                _document(body)
                valid = (
                    body["actor_id"] == actor
                    and body["engagement_id"] == engagement
                    and body["version"] == row["version"] == version
                    and body["predecessor_sha256"] == previous
                    and digest(body) == row["sha256"]
                    and isinstance(body["inventory"], list)
                    and len(body["inventory"]) <= MAX_PINS
                )
            except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
                raise DomainError(
                    "Checkpoint integrity failure", code="INTEGRITY", status=500
                ) from exc
            require(valid, "Checkpoint integrity failure", "INTEGRITY", 500)
            documents.append(body)
            previous = row["sha256"]
        commands = db.execute(
            "SELECT * FROM checkpoint_commands WHERE actor=? AND engagement=? LIMIT ?",
            (actor, engagement, MAX_HISTORY + 1),
        ).fetchall()
        require(
            len(commands) == len(documents), "Checkpoint command history differs", "INTEGRITY", 500
        )
        versions = set()
        for command in commands:
            version = command["version"]
            require(
                type(version) is int and 1 <= version <= len(documents) and version not in versions,
                "Checkpoint command version differs",
                "INTEGRITY",
                500,
            )
            require(
                command["fingerprint"]
                == digest([version - 1, documents[version - 1]["engagement_revision"]]),
                "Checkpoint command pin differs",
                "INTEGRITY",
                500,
            )
            versions.add(version)
        return documents

    def _metadata(self, state, basis, body):
        output = {
            "engagement_id": state["id"],
            "current_engagement_revision": state["revision"],
            "version": body["version"] if body else 0,
            "status": "NO_CHECKPOINT" if body is None else "CURRENT",
            "formal_work_mutated": False,
            "qualification": QUALIFICATION,
            "supported_kinds": list(COLLECTIONS),
            "backup_status": "SNAPSHOT_AVAILABLE_INERT_ARCHIVE_ONLY",
        }
        if body:
            output.update(
                saved_at=body["saved_at"],
                checkpoint_engagement_revision=body["engagement_revision"],
            )
            if basis != body["context_basis_sha256"]:
                output["status"] = "CONTEXT_CHANGED"
        return output

    def status(self, actor, engagement):
        state, basis = self._state(actor, engagement)
        with self._db() as db:
            docs = self._load(db, actor, engagement)
        output = self._metadata(state, basis, docs[-1] if docs else None)
        self._recheck(actor, engagement, state, basis)
        return output

    def history(self, actor, engagement):
        state, basis = self._state(actor, engagement)
        with self._db() as db:
            docs = self._load(db, actor, engagement)
        output = {
            "engagement_id": engagement,
            "current_engagement_revision": state["revision"],
            "checkpoints": [self._metadata(state, basis, b) for b in docs],
        }
        self._recheck(actor, engagement, state, basis)
        return output

    def compare(self, actor, engagement, *, expected_version, expected_engagement_revision):
        state, basis = self._state(actor, engagement)
        with self._db() as db:
            docs = self._load(db, actor, engagement)
        body = docs[-1] if docs else None
        output = self._metadata(state, basis, body)
        require(
            type(expected_version) is int
            and expected_version == output["version"]
            and type(expected_engagement_revision) is int
            and expected_engagement_revision == state["revision"],
            "Checkpoint or engagement changed",
            "CHECKPOINT_CONFLICT",
            409,
        )
        if output["status"] == "CURRENT":
            try:
                current = inventory(state)
                old = {_key(r): r for r in body["inventory"]}
                new = {_key(r): r for r in current}
                if not old.keys() <= new.keys():
                    output["status"] = "TARGET_UNAVAILABLE"
                else:
                    changes = [
                        {
                            "change": "ADDED" if key not in old else "CHANGED",
                            "prior": old.get(key),
                            "current": value,
                        }
                        for key, value in new.items()
                        if old.get(key) != value
                    ]
                    output.update(
                        changes=changes,
                        counts={
                            "added": sum(r["change"] == "ADDED" for r in changes),
                            "changed": sum(r["change"] == "CHANGED" for r in changes),
                            "unchanged": len(new) - len(changes),
                        },
                    )
            except DomainError as exc:
                if exc.code not in {"INPUT_LIMIT_EXCEEDED", "INPUT_DATA_UNAVAILABLE"}:
                    raise
                output["status"] = exc.code
        self._recheck(actor, engagement, state, basis)
        return output

    def capture(
        self, actor, engagement, *, expected_version, expected_engagement_revision, command_id
    ):
        state, basis = self._state(actor, engagement)
        _text(command_id, 128, nonempty=True)
        require(
            type(expected_version) is int
            and expected_version >= 0
            and type(expected_engagement_revision) is int,
            "Exact revisions required",
        )
        fingerprint = digest([expected_version, expected_engagement_revision])
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            docs = self._load(db, actor, engagement)
            old = db.execute(
                "SELECT * FROM checkpoint_commands WHERE actor=? AND engagement=? AND command_id=?",
                (actor, engagement, command_id),
            ).fetchone()
            if old:
                require(
                    old["fingerprint"] == fingerprint and old["version"] == len(docs),
                    "Checkpoint command reused",
                    "CHECKPOINT_CONFLICT",
                    409,
                )
            else:
                require(
                    expected_version == len(docs)
                    and expected_engagement_revision == state["revision"],
                    "Checkpoint or engagement changed",
                    "CHECKPOINT_CONFLICT",
                    409,
                )
                require(len(docs) < MAX_HISTORY, "Checkpoint history quota reached", status=429)
                body = {
                    "actor_id": actor,
                    "engagement_id": engagement,
                    "version": len(docs) + 1,
                    "engagement_revision": state["revision"],
                    "saved_at": datetime.now(UTC).isoformat(),
                    "context_basis_sha256": basis,
                    "predecessor_sha256": digest(docs[-1]) if docs else None,
                    "inventory": inventory(state),
                }
                _document(body)
                require(
                    db.execute("SELECT COUNT(*) FROM checkpoint_history").fetchone()[0] < 10000,
                    "Global checkpoint row quota reached",
                    status=429,
                )
                raw = canonical(body)
                size = db.execute(
                    "SELECT COALESCE(SUM(length(CAST(content AS BLOB))),0) FROM checkpoint_history"
                ).fetchone()[0]
                require(
                    size + len(raw.encode()) <= 64 * 1024 * 1024,
                    "Checkpoint storage quota reached",
                    status=429,
                )
                self._recheck(actor, engagement, state, basis)
                db.execute(
                    "INSERT INTO checkpoint_history VALUES(?,?,?,?,?)",
                    (actor, engagement, body["version"], raw, digest(body)),
                )
                db.execute(
                    "INSERT INTO checkpoints VALUES(?,?,?) ON CONFLICT(actor,engagement) "
                    "DO UPDATE SET version=excluded.version",
                    (actor, engagement, body["version"]),
                )
                db.execute(
                    "INSERT INTO checkpoint_commands VALUES(?,?,?,?,?)",
                    (actor, engagement, command_id, fingerprint, body["version"]),
                )
                docs.append(body)
            output = self._metadata(state, basis, docs[-1])
            self._recheck(actor, engagement, state, basis)
        return output

    def snapshot(self):
        """Trusted companion backup only; sensitive actor-specific pins, inert archive."""
        with self._db() as db:
            db.execute("BEGIN")
            _preflight(db)
            tables = {}
            for table in ARCHIVE_TABLES:
                rows = db.execute(
                    "SELECT * FROM " + table + " ORDER BY 1,2,3 LIMIT 10001"
                ).fetchall()
                require(len(rows) <= 10000, "Checkpoint archive row limit")
                tables[table] = [dict(row) for row in rows]
            value = {"format": "PRIVATE_VISIT_CHECKPOINT_ARCHIVE_V1", "tables": tables}
            validate_snapshot(value)
            return value


ARCHIVE_TABLES = {
    "checkpoints": {"actor", "engagement", "version"},
    "checkpoint_history": {"actor", "engagement", "version", "content", "sha256"},
    "checkpoint_commands": {"actor", "engagement", "command_id", "fingerprint", "version"},
}


def _preflight(db, actor=None, engagement=None):
    """SQL-only size/type checks before materializing any private row fields."""
    where = " WHERE actor=? AND engagement=?" if actor is not None else ""
    args = (actor, engagement) if actor is not None else ()
    for table, fields in ARCHIVE_TABLES.items():
        limit = (1 if table == "checkpoints" else MAX_HISTORY) if actor is not None else 10000
        count = db.execute("SELECT COUNT(*) FROM " + table + where, args).fetchone()[0]
        require(count <= limit, "Checkpoint SQL row bound exceeded", "INTEGRITY", 500)
        conditions = ["typeof(version)='integer' AND version BETWEEN 1 AND 100"]
        for field in fields - {"version"}:
            maximum = (
                MAX_BYTES + 16384
                if field == "content"
                else 64
                if field in {"sha256", "fingerprint"}
                else 512
                if field == "command_id"
                else 1024
            )
            conditions.append(
                "typeof("
                + field
                + ")='text' AND length(CAST("
                + field
                + " AS BLOB)) BETWEEN 1 AND "
                + str(maximum)
            )
        valid = " AND ".join("(" + c + ")" for c in conditions)
        invalid = db.execute(
            "SELECT COALESCE(SUM(CASE WHEN "
            + valid
            + " THEN 0 ELSE 1 END),0) FROM "
            + table
            + where,
            args,
        ).fetchone()[0]
        require(invalid == 0, "Checkpoint SQL field bound/type failure", "INTEGRITY", 500)
        metadata = " + ".join(
            "length(CAST(" + field + " AS BLOB))" for field in fields - {"content"}
        )
        size = db.execute(
            "SELECT COALESCE(SUM(" + metadata + "),0) FROM " + table + where, args
        ).fetchone()[0]
        require(
            size <= (256 * 1024 if actor is not None else 24 * 1024 * 1024),
            "Checkpoint SQL metadata bound exceeded",
            "INTEGRITY",
            500,
        )
        if table == "checkpoint_history":
            size = db.execute(
                "SELECT COALESCE(SUM(length(CAST(content AS BLOB))),0) FROM " + table + where, args
            ).fetchone()[0]
            require(
                size <= 64 * 1024 * 1024, "Checkpoint SQL content bound exceeded", "INTEGRITY", 500
            )


def _hash(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def _document(body):
    require(
        isinstance(body, dict)
        and set(body)
        == {
            "actor_id",
            "engagement_id",
            "version",
            "engagement_revision",
            "saved_at",
            "context_basis_sha256",
            "predecessor_sha256",
            "inventory",
        },
        "Exact checkpoint document required",
        "INTEGRITY",
        500,
    )
    require(
        all(
            isinstance(body[k], str) and 0 < len(body[k]) <= 256
            for k in ("actor_id", "engagement_id", "saved_at")
        )
        and type(body["version"]) is int
        and 1 <= body["version"] <= MAX_HISTORY
        and type(body["engagement_revision"]) is int
        and body["engagement_revision"] >= 0
        and _hash(body["context_basis_sha256"])
        and (body["predecessor_sha256"] is None or _hash(body["predecessor_sha256"]))
        and isinstance(body["inventory"], list)
        and len(body["inventory"]) <= MAX_PINS,
        "Invalid checkpoint document",
        "INTEGRITY",
        500,
    )
    keys = set()
    for row in body["inventory"]:
        require(
            isinstance(row, dict)
            and set(row) == {"reference", "record_sha256"}
            and _hash(row["record_sha256"]),
            "Invalid checkpoint pin",
            "INTEGRITY",
            500,
        )
        ref = row["reference"]
        require(
            isinstance(ref, dict)
            and set(ref) == {"kind", "id", "version", "sha256"}
            and isinstance(ref["kind"], str)
            and ref["kind"] in COLLECTIONS
            and isinstance(ref["id"], str)
            and 0 < len(ref["id"]) <= 256
            and _hash(ref["sha256"])
            and (ref["version"] is None or type(ref["version"]) is int)
            and (ref["kind"] != "workpaper" or type(ref["version"]) is int and ref["version"] >= 1),
            "Invalid exact reference",
            "INTEGRITY",
            500,
        )
        key = _key(row)
        require(key not in keys, "Duplicate checkpoint reference", "INTEGRITY", 500)
        keys.add(key)


def validate_snapshot(value):
    """Validate an inert logical archive; never installs principals or active checkpoints."""
    try:
        require(
            isinstance(value, dict)
            and set(value) == {"format", "tables"}
            and value["format"] == "PRIVATE_VISIT_CHECKPOINT_ARCHIVE_V1"
            and isinstance(value["tables"], dict)
            and set(value["tables"]) == set(ARCHIVE_TABLES),
            "Exact checkpoint archive required",
        )
        tables = value["tables"]
        for name, fields in ARCHIVE_TABLES.items():
            require(
                isinstance(tables[name], list) and len(tables[name]) <= 10000,
                "Bounded archive table required",
            )
            for row in tables[name]:
                require(
                    isinstance(row, dict)
                    and set(row) == fields
                    and all(
                        isinstance(row[k], str) and 0 < len(row[k]) <= 256
                        for k in ("actor", "engagement")
                    )
                    and type(row["version"]) is int
                    and 1 <= row["version"] <= MAX_HISTORY,
                    "Invalid archive row",
                )
        total = 0
        for row in tables["checkpoint_history"]:
            require(
                isinstance(row["content"], str)
                and len(row["content"]) <= MAX_BYTES + 16384
                and _hash(row["sha256"]),
                "Bounded archive history required",
            )
            total += len(row["content"].encode())
            require(total <= 64 * 1024 * 1024, "Archive content limit exceeded")
        for row in tables["checkpoint_commands"]:
            _text(row["command_id"], 128, nonempty=True)
            require(_hash(row["fingerprint"]), "Invalid archive command pin")
        require(len(canonical(value).encode()) <= 72 * 1024 * 1024, "Archive byte limit exceeded")
        chains = {}
        for row in tables["checkpoint_history"]:
            require(
                isinstance(row["content"], str)
                and len(row["content"].encode()) <= MAX_BYTES + 16384,
                "Bounded checkpoint history required",
            )
            body = _json(row["content"])
            _document(body)
            key = (row["actor"], row["engagement"])
            chain = chains.setdefault(key, {})
            require(
                row["version"] not in chain
                and body["actor_id"] == key[0]
                and body["engagement_id"] == key[1]
                and body["version"] == row["version"]
                and row["sha256"] == digest(body),
                "Archive history integrity failure",
            )
            chain[row["version"]] = body
        heads = {}
        for row in tables["checkpoints"]:
            key = (row["actor"], row["engagement"])
            require(key not in heads, "Duplicate archive head")
            heads[key] = row["version"]
        require(set(heads) == set(chains), "Archive head/history mismatch")
        for key, count in heads.items():
            chain = chains[key]
            require(set(chain) == set(range(1, count + 1)), "Archive history gap")
            previous = None
            for version in range(1, count + 1):
                require(chain[version]["predecessor_sha256"] == previous, "Archive chain mismatch")
                previous = digest(chain[version])
        commands = set()
        versions = set()
        for row in tables["checkpoint_commands"]:
            key = (row["actor"], row["engagement"])
            _text(row["command_id"], 128, nonempty=True)
            command = (*key, row["command_id"])
            version = (*key, row["version"])
            require(
                command not in commands
                and version not in versions
                and _hash(row["fingerprint"])
                and key in chains
                and row["version"] in chains[key]
                and row["fingerprint"]
                == digest([row["version"] - 1, chains[key][row["version"]]["engagement_revision"]]),
                "Archive command mismatch",
            )
            commands.add(command)
            versions.add(version)
        require(len(versions) == sum(heads.values()), "Archive command history incomplete")
        return value
    except (KeyError, TypeError, ValueError, AttributeError, UnicodeError, RecursionError) as exc:
        raise DomainError("Invalid private checkpoint archive") from exc
