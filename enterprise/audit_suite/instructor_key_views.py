"""Private instructor-only saved filters; inert recovery, never audit or Key content edits."""

import hashlib
import json
import os
import re
import sqlite3
import zipfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .bound_instructor import read_binding
from .instructor_access import InstructorAccessLog
from .instructor_key import semantic_search_bundle, semantic_search_matches, verify_archive
from .personal_views import PersonalViews
from .store import DomainError, canonical, digest, identifier
from .workspace_context import _basis

MAX_EVENTS = 4096
MAX_VERSIONS = 200
MAX_ARCHIVE_FILE_BYTES = 256 * 1024 * 1024
MAX_ARCHIVE_TOTAL_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_FILES = 20000
ZERO = "0" * 64


def require(ok, message, status=400):
    if not ok:
        raise DomainError(message, status=status)


def fields(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys), "Exact Key view fields required")


def text(value, maximum, nonempty=False):
    require(
        isinstance(value, str) and len(value) <= maximum and (not nonempty or value.strip()),
        "Bounded Key view text required",
    )
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise DomainError("Valid Unicode required") from error


def integer(value, maximum=1000000000):
    require(type(value) is int and 0 <= value <= maximum, "Exact bounded integer required")


def pin(value):
    require(
        isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value), "Exact Key pin required"
    )


def validate_user(kind, user):
    common = {"title", "query", "page"}
    require(isinstance(kind, str) and kind in {"BOUND", "ARCHIVE"}, "Unknown Key view kind")
    fields(
        user,
        common
        | (
            {"issue_id", "scope_to_issue", "source"}
            | ({"issue_index"} if isinstance(user, dict) and "issue_index" in user else set())
            | ({"source_filters"} if isinstance(user, dict) and "source_filters" in user else set())
            if kind == "BOUND"
            else {"selector", "option", "review", "scenario"}
            | ({"review_facets"} if isinstance(user, dict) and "review_facets" in user else set())
        ),
    )
    text(user["title"], 120, True)
    text(user["query"], 1000)
    integer(user["page"], 100000)
    if kind == "BOUND":
        if "source_filters" in user:
            fields(user["source_filters"], ("system", "visibility"))
            for value in user["source_filters"].values():
                if value is not None:
                    text(value, 256, True)
        if "issue_index" in user:
            index = user["issue_index"]
            fields(index, ("query", "control_id", "page"))
            text(index["query"], 1000)
            integer(index["page"], 100000)
            if index["control_id"] is not None:
                text(index["control_id"], 128, True)
        require(type(user["scope_to_issue"]) is bool, "Explicit issue scope required")
        if user["issue_id"] is not None:
            text(user["issue_id"], 128, True)
        require(not user["scope_to_issue"] or user["issue_id"] is not None, "Scoped issue required")
        if user["source"] is not None:
            fields(user["source"], ("id", "version", "sha256"))
            text(user["source"]["id"], 128, True)
            integer(user["source"]["version"])
            require(user["source"]["version"] > 0, "Positive source version required")
            pin(user["source"]["sha256"])
    else:
        if "review_facets" in user:
            fields(user["review_facets"], ("causal_validation", "grading"))
            for value in user["review_facets"].values():
                if value is not None:
                    text(value, 128, True)
        for key in ("selector", "option", "review"):
            text(user[key], 128, True)
        if user["scenario"] is not None:
            fields(user["scenario"], ("id", "key_sha256"))
            text(user["scenario"]["id"], 128, True)
            pin(user["scenario"]["key_sha256"])
    return user


def _validate_archive(value):
    fields(value, ("schema", "restoration", "events"))
    require(
        value["schema"] == "PRIVATE_INSTRUCTOR_KEY_VIEWS_V1"
        and value["restoration"] == "INERT_ONLY_NO_ACTIVE_REHYDRATION",
        "Unsupported Key view archive",
    )
    require(
        isinstance(value["events"], list)
        and len(value["events"]) <= MAX_EVENTS
        and len(canonical(value).encode()) <= 32 * 1024 * 1024,
        "Key view archive limit",
    )
    previous, latest, commands = ZERO, {}, set()
    for number, row in enumerate(value["events"], 1):
        fields(row, ("seq", "content", "sha256"))
        require(type(row["seq"]) is int and row["seq"] == number, "Key view sequence differs")
        body = json.loads(row["content"])
        fields(
            body,
            (
                "actor_id",
                "engagement_id",
                "id",
                "kind",
                "version",
                "status",
                "saved_at",
                "saved_engagement_revision",
                "basis_sha256",
                "key_pin",
                "bound_pins",
                "user",
                "previous_sha256",
                "command_id",
                "request_sha256",
            ),
        )
        require(
            canonical(body) == row["content"]
            and digest(body) == row["sha256"]
            and body["previous_sha256"] == previous,
            "Key view history differs",
        )
        for key in ("actor_id", "engagement_id", "id", "command_id"):
            text(body[key], 128, True)
        for key in ("basis_sha256", "key_pin", "request_sha256"):
            pin(body[key])
        integer(body["saved_engagement_revision"])
        integer(body["version"], 201)
        require(body["status"] in {"ACTIVE", "DELETED"}, "Key view status differs")
        validate_user(body["kind"], body["user"])
        require(
            datetime.fromisoformat(body["saved_at"]).tzinfo is not None,
            "Saved timestamp timezone required",
        )
        if body["kind"] == "BOUND":
            fields(body["bound_pins"], ("revision", "state_sha256", "history_sha256"))
            integer(body["bound_pins"]["revision"])
            pin(body["bound_pins"]["state_sha256"])
            pin(body["bound_pins"]["history_sha256"])
        else:
            require(body["bound_pins"] is None, "Archive cannot claim bound history")
        old = latest.get(body["id"])
        require(body["version"] == (old["version"] + 1 if old else 1), "Key view version gap")
        if old:
            require(
                old["status"] == "ACTIVE"
                and all(old[k] == body[k] for k in ("actor_id", "engagement_id", "kind")),
                "Key view ownership/status changed",
            )
        require(body["status"] != "DELETED" or old is not None, "Orphan tombstone")
        require(
            body["version"] <= 200 or body["status"] == "DELETED",
            "Final version reserved for deletion",
        )
        command = (body["actor_id"], body["engagement_id"], body["command_id"])
        require(command not in commands, "Duplicate Key view command")
        commands.add(command)
        latest[body["id"]] = body
        previous = row["sha256"]
    return value


def validate_archive(value):
    try:
        return _validate_archive(value)
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as error:
        raise DomainError("Invalid private Key view archive") from error


class InstructorKeyViews:
    def __init__(self, private_root, engine, bindings, archive_root=None):
        self.root = Path(private_root)
        self.path = self.root / "key-views.sqlite3"
        self.engine, self.bindings = engine, bindings
        self.archive_root = Path(archive_root) if archive_root is not None else None
        self._semantic_index = None
        PersonalViews._private(self.root, True)
        if not self.path.exists():
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            os.close(fd)
        self.archive_identity = self._archive()[0] if self.archive_root is not None else None
        with self._db(validate=False) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,content TEXT,sha256 TEXT);
                CREATE TRIGGER IF NOT EXISTS key_views_no_update BEFORE UPDATE ON events
                  BEGIN SELECT RAISE(ABORT,'Immutable Key view history'); END;
                CREATE TRIGGER IF NOT EXISTS key_views_no_delete BEFORE DELETE ON events
                  BEGIN SELECT RAISE(ABORT,'Immutable Key view history'); END;
            """)

    @contextmanager
    def _db(self, validate=True):
        root_pin = PersonalViews._private(self.root, True)
        before = PersonalViews._private(self.path)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            if validate:
                self._archive_rows(db)
            yield db
            require(
                PersonalViews._private(self.root, True) == root_pin
                and PersonalViews._private(self.path) == before,
                "Key view storage identity changed",
                409,
            )
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _archive_rows(db):
        size, count = db.execute(
            "SELECT coalesce(sum(length(CAST(content AS BLOB))),0),count(*) FROM events"
        ).fetchone()
        require(size <= 16 * 1024 * 1024 and count <= MAX_EVENTS, "Key view storage limit")
        archive = {
            "schema": "PRIVATE_INSTRUCTOR_KEY_VIEWS_V1",
            "restoration": "INERT_ONLY_NO_ACTIVE_REHYDRATION",
            "events": [dict(r) for r in db.execute("SELECT * FROM events ORDER BY seq")],
        }
        validate_archive(archive)
        return archive

    def _state(self, actor, eid):
        require(
            self.engine.store.membership(actor, eid) == "instruct",
            "Instructor membership required",
            403,
        )
        return self.engine.store.get(actor, eid)

    def _archive(self):
        require(self.archive_root is not None, "Protected archive unavailable", 503)
        root = self.archive_root
        PersonalViews._private(root, True)
        fingerprints = {}
        paths, total = [], 0
        for path in root.rglob("*"):
            PersonalViews._private(path, path.is_dir())
            require(len(paths) < MAX_ARCHIVE_FILES, "Protected archive file limit", 503)
            paths.append(path)
            if path.is_file():
                size = path.stat().st_size
                total += size
                require(
                    size <= MAX_ARCHIVE_FILE_BYTES and total <= MAX_ARCHIVE_TOTAL_BYTES,
                    "Protected archive byte limit",
                    503,
                )
        index_path = root / "index.json"
        require(index_path.stat().st_size <= 8 * 1024 * 1024, "Protected index byte limit", 503)
        with index_path.open("rb") as stream:
            index_raw = stream.read(8 * 1024 * 1024 + 1)
        require(len(index_raw) <= 8 * 1024 * 1024, "Protected index byte limit", 503)
        index_value = json.loads(index_raw)
        entries = index_value.get("entries")
        require(
            isinstance(entries, list) and len(entries) <= (MAX_ARCHIVE_FILES - 4) // 2,
            "Protected index entry limit",
            503,
        )
        expected = {"index.json", "receipt.json", "instructor-keys.zip", "verification.json"}
        for entry in entries:
            require(
                isinstance(entry, dict)
                and isinstance(entry.get("id"), str)
                and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", entry["id"]),
                "Protected archive identifier differs",
                503,
            )
            for field, directory in (("source", "sources"), ("key", "keys")):
                name = directory + "/" + entry["id"] + ".json"
                require(
                    entry.get(field) == name and name not in expected,
                    "Protected archive member differs",
                    503,
                )
                expected.add(name)
        actual = {p.relative_to(root).as_posix() for p in paths if p.is_file()}
        require(
            actual <= expected and expected - {"verification.json"} <= actual,
            "Unexpected protected archive member",
            503,
        )
        for path in paths:
            if path.is_file():
                before = path.stat()
                with path.open("rb") as stream:
                    raw = stream.read(MAX_ARCHIVE_FILE_BYTES + 1)
                require(len(raw) <= MAX_ARCHIVE_FILE_BYTES, "Protected archive byte limit", 503)
                after = path.stat()
                require(
                    (
                        before.st_dev,
                        before.st_ino,
                        before.st_ctime_ns,
                        before.st_size,
                        before.st_mode,
                    )
                    == (
                        after.st_dev,
                        after.st_ino,
                        after.st_ctime_ns,
                        after.st_size,
                        after.st_mode,
                    ),
                    "Protected archive changed during read",
                    503,
                )
                fingerprints[path.relative_to(root).as_posix()] = hashlib.sha256(raw).hexdigest()
        with zipfile.ZipFile(root / "instructor-keys.zip") as bundle:
            members = bundle.infolist()
            require(
                len(members) <= MAX_ARCHIVE_FILES
                and sum(m.file_size for m in members) <= MAX_ARCHIVE_TOTAL_BYTES
                and all(m.file_size <= MAX_ARCHIVE_FILE_BYTES for m in members),
                "Protected archive expanded limit",
                503,
            )
        verify_archive(root)
        index = json.loads((root / "index.json").read_bytes())
        receipt = json.loads((root / "receipt.json").read_bytes())
        identity = digest(fingerprints)
        if self._semantic_index is None:
            self._semantic_index = (identity, *semantic_search_bundle(root, index))
        require(self._semantic_index[0] == identity, "Protected archive changed", 503)
        return identity, receipt["archive_sha256"], self._semantic_index[1]

    def _context(self, actor, eid, kind):
        require(isinstance(kind, str) and kind in {"BOUND", "ARCHIVE"}, "Unknown Key view kind")
        state = self._state(actor, eid)
        key, data, bound_pins, error = None, None, None, None
        try:
            if kind == "BOUND":
                response = read_binding(self.engine, {"id": actor}, eid, self.bindings)
                data = response["snapshot"]
                key = response["binding"]["manifest_sha256"]
                bound_pins = {
                    k: data["engagement"][k] for k in ("revision", "state_sha256", "history_sha256")
                }
            else:
                identity, key, data = self._archive()
                require(identity == self.archive_identity, "Protected archive changed", 503)
                InstructorAccessLog(self.engine.store.root / "instructor-key-access").append(
                    actor=actor,
                    engagement=eid,
                    target=None,
                    operation="INDEX",
                    outcome="SUCCESS",
                    http_status=200,
                    archive_sha256=key,
                )
        except (DomainError, OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
            if isinstance(exc, DomainError) and exc.status == 403:
                raise
            if kind == "ARCHIVE":
                InstructorAccessLog(self.engine.store.root / "instructor-key-access").append(
                    actor=actor,
                    engagement=eid,
                    target=None,
                    operation="INDEX",
                    outcome="UNAVAILABLE",
                    http_status=503,
                )
            error = "KEY_UNAVAILABLE"
        self._state(actor, eid)
        return {
            "state": state,
            "kind": kind,
            "key": key if error is None else None,
            "data": data if error is None else None,
            "bound_pins": bound_pins,
            "basis": digest(
                {"actor_id": actor, "engagement_id": eid, "permission": "instruct", **_basis(state)}
            ),
            "error": error,
            "authored_matching_texts": (
                self._semantic_index[2] if kind == "ARCHIVE" and error is None else None
            ),
        }

    def _finish(self, actor, eid, context):
        current = self._context(actor, eid, context["kind"])
        require(
            current["basis"] == context["basis"]
            and current["key"] == context["key"]
            and current["error"] == context["error"]
            and digest(current["state"]) == digest(context["state"]),
            "Key view context changed",
            409,
        )

    @staticmethod
    def _selection(context, user):
        kind = context["kind"]
        validate_user(kind, user)
        require(context["error"] is None, "Protected Key unavailable", 503)
        data = context["data"]
        query = user["query"].strip().lower()
        if kind == "BOUND":
            sources, issues = data["sources"], data["authored"]["issues"]
            require(
                len({r["id"] for r in sources}) == len(sources)
                and len({r["id"] for r in issues}) == len(issues),
                "Ambiguous Key IDs",
                409,
            )
            selected_issue = next((r for r in issues if r["id"] == user["issue_id"]), None)
            require(
                user["issue_id"] is None or selected_issue is not None,
                "Saved issue unavailable",
                409,
            )
            if "issue_index" in user:
                index = user["issue_index"]
                control = index["control_id"]
                require(
                    control is None or any(control in r["control_ids"] for r in issues),
                    "Saved issue-index control unavailable",
                    409,
                )
                issue_query = index["query"].strip().lower()
                issue_count = sum(
                    (control is None or control in r["control_ids"])
                    and issue_query
                    in " ".join(
                        [r["id"], *r["control_ids"], r["claim"], r["uncertainty"]]
                        + [
                            str(value)
                            for expectation in data["authored"]["expectations"]
                            if r["id"] in expectation["issue_ids"]
                            for value in [
                                expectation["id"],
                                *expectation.get("task_ids", []),
                                expectation["procedure"],
                                *expectation["acceptable_alternatives"],
                            ]
                        ]
                        + [
                            str(value)
                            for source in sources
                            if source["id"] in r["source_ids"]
                            for value in [
                                source["id"],
                                source["company"],
                                source["branch"],
                                source["system"],
                                source["record"],
                                source["version"],
                                source["sha256"],
                            ]
                        ]
                    ).lower()
                    for r in issues
                )
                require(
                    index["page"] < max(1, (issue_count + 19) // 20),
                    "Saved issue page outside exact results",
                    409,
                )
            if user["source"] is not None:
                require(
                    any(all(r.get(k) == v for k, v in user["source"].items()) for r in sources),
                    "Saved source differs",
                    409,
                )
            if user["scope_to_issue"]:
                sources = [r for r in sources if r["id"] in selected_issue["source_ids"]]
            source_filters = user.get("source_filters", {"system": None, "visibility": None})
            for name, field in (
                ("system", "system"),
                ("visibility", "actor_visibility_at_binding"),
            ):
                require(
                    source_filters[name] is None
                    or any(r[field] == source_filters[name] for r in data["sources"]),
                    "Saved source facet unavailable",
                    409,
                )
            count = sum(
                (source_filters["system"] is None or r["system"] == source_filters["system"])
                and (
                    source_filters["visibility"] is None
                    or r["actor_visibility_at_binding"] == source_filters["visibility"]
                )
                and query
                in " ".join(
                    str(r.get(k) or "")
                    for k in (
                        "id",
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "sha256",
                        "source_store_id",
                        "source_system_alias",
                        "registry_sha256",
                        "actor_visibility_at_binding",
                    )
                ).lower()
                for r in sources
            )
            page_size = 10
        else:
            rows = data["entries"]
            matching_ids = set(
                semantic_search_matches(context["authored_matching_texts"], user["query"])
            )
            require(len({r["id"] for r in rows}) == len(rows), "Ambiguous scenario IDs", 409)

            def selector(row):
                return row["id"].split(".")[0]

            def option(row):
                return re.sub(r"\.V\d+$", "", row["id"])

            for field, choices in (
                ("selector", {selector(r) for r in rows}),
                (
                    "option",
                    {
                        option(r)
                        for r in rows
                        if user["selector"] == "all" or selector(r) == user["selector"]
                    },
                ),
                ("review", {r["review"]["professional"] for r in rows}),
            ):
                require(
                    user[field] == "all" or user[field] in choices, "Saved filter unavailable", 409
                )
            if user["scenario"] is not None:
                require(
                    any(all(r.get(k) == v for k, v in user["scenario"].items()) for r in rows),
                    "Saved scenario differs",
                    409,
                )
            review_facets = user.get("review_facets", {"causal_validation": None, "grading": None})
            for name in ("causal_validation", "grading"):
                require(
                    review_facets[name] is None
                    or any(r["review"][name] == review_facets[name] for r in rows),
                    "Saved review facet unavailable",
                    409,
                )
            count = sum(
                (user["selector"] == "all" or selector(r) == user["selector"])
                and (user["option"] == "all" or option(r) == user["option"])
                and (user["review"] == "all" or r["review"]["professional"] == user["review"])
                and all(
                    review_facets[name] is None or r["review"][name] == review_facets[name]
                    for name in ("causal_validation", "grading")
                )
                and r["id"] in matching_ids
                for r in rows
            )
            page_size = 25
        require(
            user["page"] < max(1, (count + page_size - 1) // page_size),
            "Saved page outside exact results",
            409,
        )

    @staticmethod
    def _latest(db, actor, eid):
        result = {}
        for row in db.execute("SELECT content FROM events ORDER BY seq"):
            value = json.loads(row["content"])
            if value["actor_id"] == actor and value["engagement_id"] == eid:
                result[value["id"]] = value
        return result

    def _dto(self, value, context, restore=False):
        status = context["error"] or (
            "KEY_CHANGED"
            if value["key_pin"] != context["key"]
            else "CONTEXT_CHANGED"
            if value["basis_sha256"] != context["basis"]
            else "CURRENT"
        )
        visible = status == "CURRENT" and value["status"] == "ACTIVE"
        if visible:
            try:
                self._selection(context, value["user"])
            except DomainError:
                status, visible = "CONTEXT_CHANGED", False
        result = {
            "id": value["id"],
            "engagement_id": value["engagement_id"],
            "kind": value["kind"],
            "version": value["version"],
            "status": value["status"],
            "saved_engagement_revision": value["saved_engagement_revision"],
            "current_engagement_revision": context["state"]["revision"],
            "context_status": status,
            "revision_status": "MATCHING_REVISION"
            if value["saved_engagement_revision"] == context["state"]["revision"]
            else "ENGAGEMENT_ADVANCED",
            "restorable": visible,
            "personal_content_visible": visible,
            "navigation": value["user"] if restore and visible else None,
            "backup_status": "INERT_ARCHIVE_ONLY",
        }
        if visible:
            result.update(user=value["user"], key_pin=value["key_pin"])
        return result

    def listing(self, actor, eid, kind):
        context = self._context(actor, eid, kind)
        with self._db() as db:
            views = [
                self._dto(v, context)
                for v in self._latest(db, actor, eid).values()
                if v["kind"] == kind and v["status"] == "ACTIVE"
            ]
            self._finish(actor, eid, context)
        return {
            "engagement_id": eid,
            "current_engagement_revision": context["state"]["revision"],
            "kind": kind,
            "views": views,
        }

    def read(self, actor, eid, view_id):
        self._state(actor, eid)
        with self._db() as db:
            value = self._latest(db, actor, eid).get(view_id)
            require(value is not None, "Saved Key view unavailable", 404)
            context = self._context(actor, eid, value["kind"])
            result = self._dto(value, context)
            self._finish(actor, eid, context)
            return result

    def restore(self, actor, eid, view_id, payload):
        fields(payload, ("expected_version", "expected_engagement_revision", "expected_key_pin"))
        for key in ("expected_version", "expected_engagement_revision"):
            integer(payload[key])
        pin(payload["expected_key_pin"])
        self._state(actor, eid)
        with self._db() as db:
            value = self._latest(db, actor, eid).get(view_id)
            require(value is not None, "Saved Key view unavailable", 404)
            context = self._context(actor, eid, value["kind"])
            require(
                value["version"] == payload["expected_version"]
                and context["state"]["revision"] == payload["expected_engagement_revision"]
                and context["key"] == payload["expected_key_pin"],
                "Saved Key view changed",
                409,
            )
            result = self._dto(value, context, True)
            require(result["restorable"], "Saved Key context unavailable", 409)
            self._finish(actor, eid, context)
            return result

    def save(self, actor, eid, payload):
        fields(
            payload,
            (
                "view_id",
                "kind",
                "key_pin",
                "user",
                "expected_version",
                "expected_engagement_revision",
                "command_id",
            ),
        )
        return self._write(actor, eid, payload, False)

    def delete(self, actor, eid, view_id, payload):
        fields(payload, ("expected_version", "expected_engagement_revision", "command_id"))
        return self._write(actor, eid, {**payload, "view_id": view_id}, True)

    def _write(self, actor, eid, payload, deleting):
        p = json.loads(canonical(payload))
        self._state(actor, eid)
        text(p["command_id"], 128, True)
        integer(p["expected_version"])
        integer(p["expected_engagement_revision"])
        if p["view_id"] is not None:
            text(p["view_id"], 128, True)
        with self._db() as db:
            latest = self._latest(db, actor, eid)
            old = latest.get(p["view_id"]) if p["view_id"] is not None else None
            if p["view_id"] is not None:
                require(old is not None, "Saved Key view unavailable", 404)
            kind = old["kind"] if deleting else p["kind"]
            context = self._context(actor, eid, kind)
            request_sha = digest({"operation": "DELETE" if deleting else "SAVE", "payload": p})
            replay = next(
                (
                    json.loads(r[0])
                    for r in db.execute("SELECT content FROM events ORDER BY seq")
                    if (
                        lambda v: (
                            v["actor_id"] == actor
                            and v["engagement_id"] == eid
                            and v["command_id"] == p["command_id"]
                        )
                    )(json.loads(r[0]))
                ),
                None,
            )
            if replay is not None:
                require(
                    replay["request_sha256"] == request_sha,
                    "Command already used for different saved view",
                    409,
                )
                require(
                    latest[replay["id"]]["version"] == replay["version"],
                    "Saved view command was superseded",
                    409,
                )
                result = self._dto(replay, context)
                self._finish(actor, eid, context)
                return result
            require(
                context["state"]["revision"] == p["expected_engagement_revision"]
                and p["expected_version"] == (old["version"] if old else 0),
                "Saved Key view version conflict",
                409,
            )
            require(old is None or old["status"] == "ACTIVE", "Saved Key view deleted", 409)
            if not deleting:
                pin(p["key_pin"])
                require(p["key_pin"] == context["key"], "Key pin changed", 409)
                require(old is None or old["kind"] == kind, "Saved Key view kind immutable")
                self._selection(context, p["user"])
                require(
                    old is not None or sum(v["status"] == "ACTIVE" for v in latest.values()) < 16,
                    "Active saved Key view limit",
                    409,
                )
                require(
                    old is None or old["version"] < MAX_VERSIONS, "Saved Key view edit limit", 409
                )
            body = {
                "actor_id": actor,
                "engagement_id": eid,
                "id": old["id"] if old else identifier("KEYVIEW"),
                "kind": kind,
                "version": old["version"] + 1 if old else 1,
                "status": "DELETED" if deleting else "ACTIVE",
                "saved_at": datetime.now(UTC).isoformat(),
                "saved_engagement_revision": context["state"]["revision"],
                "basis_sha256": old["basis_sha256"] if deleting else context["basis"],
                "key_pin": old["key_pin"] if deleting else context["key"],
                "bound_pins": old["bound_pins"] if deleting else context["bound_pins"],
                "user": old["user"] if deleting else p["user"],
                "previous_sha256": ZERO,
                "command_id": p["command_id"],
                "request_sha256": request_sha,
            }
            last = db.execute("SELECT seq,sha256 FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            seq = last["seq"] + 1 if last else 1
            body["previous_sha256"] = last["sha256"] if last else ZERO
            all_latest = {}
            for event_row in db.execute("SELECT content FROM events ORDER BY seq"):
                event_body = json.loads(event_row[0])
                all_latest[event_body["id"]] = event_body
            all_latest[body["id"]] = body
            active_count = sum(v["status"] == "ACTIVE" for v in all_latest.values())
            used = db.execute(
                "SELECT coalesce(sum(length(CAST(content AS BLOB))),0) FROM events"
            ).fetchone()[0]
            require(
                seq + active_count <= MAX_EVENTS
                and used + len(canonical(body).encode()) + active_count * 16384 <= 16 * 1024 * 1024,
                "Key view history limit; remaining capacity reserved for deletion",
                409,
            )
            db.execute("INSERT INTO events VALUES(?,?,?)", (seq, canonical(body), digest(body)))
            self._archive_rows(db)
            self._finish(actor, eid, context)
            return self._dto(body, context)

    def snapshot(self):
        with self._db() as db:
            return self._archive_rows(db)
