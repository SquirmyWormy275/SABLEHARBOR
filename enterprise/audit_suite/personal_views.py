"""Personal navigation only; separate private store, never audit work or hidden Key content."""

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .store import DomainError, canonical, digest
from .workspace_context import COLLECTIONS, _basis, _resolve

SECTIONS = frozenset(
    (
        "kickoff",
        "controls",
        "pbc",
        "meetings",
        "people",
        "populations",
        "notes",
        "calendar",
        "findings",
        "review",
    )
)
TABLES = {
    "procedures": ("controls", "id title control_id owner_id test_type status conclusion note"),
    "controls": ("controls", "id title owner_ids frameworks"),
    "requests": ("pbc", "id title control_id owner_id due_at status round"),
    "artifacts": ("pbc", "name request_id version covered_period received_at id"),
    "people": ("people", "name title department location control_ids effective_from"),
    "populations": ("populations", "id title count version parent_selection_id status artifact_id"),
    "selections": (
        "populations",
        "id population_id method selected_ids purpose parent_selection_id",
    ),
    "events": ("calendar", "id kind simulated_at recorded_at actor_id summary"),
    "calendar": ("calendar", "id title scheduled_at status request_id"),
    "findings": ("findings", "id title control_id classification status due_at original_result"),
    "workpapers": ("review", "id title section version status artifact_id"),
    "reviews": ("review", "id kind status comment workpaper_version evidence_ids experimental"),
    "exports": ("review", "name edition created_at id"),
}
REFERENCE_SECTIONS = {
    "control": "controls",
    "task": "controls",
    "artifact": "pbc",
    "population": "populations",
    "selection": "populations",
    "workpaper": "review",
}
FIELDS = {"title", "section", "query", "framework", "reference", "table", "scroll_top"}


def require(value, message, *, code="INVALID_SAVED_VIEW", status=400):
    if not value:
        raise DomainError(message, code=code, status=status)


def _text(value, maximum, *, nonempty=False):
    require(
        isinstance(value, str) and len(value) <= maximum and (not nonempty or value.strip()),
        "Bounded explicit text required",
    )
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise DomainError("Valid Unicode text required") from exc


def _integer(value, maximum):
    require(type(value) is int and 0 <= value <= maximum, "Bounded exact integer required")


def _reference(state, ref):
    require(
        isinstance(ref, dict) and set(ref) == {"kind", "id", "version", "sha256"},
        "Exact saved reference required",
    )
    kind = ref["kind"]
    require(isinstance(kind, str) and kind in COLLECTIONS, "Supported saved reference required")
    _text(ref["id"], 256, nonempty=True)
    require(
        isinstance(ref["sha256"], str) and re.fullmatch("[0-9a-f]{64}", ref["sha256"]),
        "Exact reference SHA256 required",
    )
    rows = [r for r in state.get(COLLECTIONS[kind], []) if r.get("id") == ref["id"]]
    require(len(rows) == 1, "Saved target unavailable", code="TARGET_UNAVAILABLE", status=409)
    if kind == "artifact":
        require(
            rows[0].get("status") == "AVAILABLE",
            "Saved original unavailable",
            code="TARGET_UNAVAILABLE",
            status=409,
        )
    if kind == "task":
        require(
            rows[0].get("status") not in ("EXCLUDED", "NOT_APPLICABLE"),
            "Procedure unavailable",
            code="TARGET_UNAVAILABLE",
            status=409,
        )
    if kind == "workpaper":
        require(
            type(ref["version"]) is int
            and sum(
                type(v.get("version")) is int and v["version"] == ref["version"]
                for v in rows[0].get("versions", [])
            )
            == 1,
            "Exact workpaper version unavailable",
            code="TARGET_UNAVAILABLE",
            status=409,
        )
    current, historical = _resolve(state, kind, ref["id"], ref["version"])
    require(
        canonical(current) == canonical(ref),
        "Saved target pin changed",
        code="TARGET_CHANGED",
        status=409,
    )
    return "HISTORICAL_VERSION_AVAILABLE" if historical else "EXACT_PIN_AVAILABLE"


class PersonalViews:
    def __init__(self, private_root, engine, *, max_active=16):
        self.root = Path(private_root).absolute()
        self.path = self.root / "saved-views.sqlite3"
        self.engine = engine
        require(type(max_active) is int and 1 <= max_active <= 32, "Active view quota must be1–32")
        self.max_active = max_active
        self._private(self.root, True)
        if self.path.exists():
            self._private(self.path)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with self._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS views(id TEXT PRIMARY KEY,actor TEXT NOT NULL,
              engagement TEXT NOT NULL,version INTEGER NOT NULL,status TEXT NOT NULL,
              content TEXT NOT NULL,sha256 TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS history(view_id TEXT,version INTEGER,content TEXT,
              sha256 TEXT,PRIMARY KEY(view_id,version));
            CREATE TABLE IF NOT EXISTS ownership_history(view_id TEXT,version INTEGER,
              content TEXT,sha256 TEXT,PRIMARY KEY(view_id,version));
            CREATE TRIGGER IF NOT EXISTS view_owners_no_update BEFORE UPDATE ON ownership_history
              BEGIN SELECT RAISE(ABORT,'Immutable view ownership'); END;
            CREATE TRIGGER IF NOT EXISTS view_owners_no_delete BEFORE DELETE ON ownership_history
              BEGIN SELECT RAISE(ABORT,'Immutable view ownership'); END;
            CREATE TABLE IF NOT EXISTS commands(actor TEXT,engagement TEXT,command_id TEXT,
              digest TEXT,view_id TEXT,version INTEGER,PRIMARY KEY(actor,engagement,command_id));
            CREATE TRIGGER IF NOT EXISTS view_history_no_update BEFORE UPDATE ON history
              BEGIN SELECT RAISE(ABORT,'Immutable saved view history'); END;
            CREATE TRIGGER IF NOT EXISTS view_history_no_delete BEFORE DELETE ON history
              BEGIN SELECT RAISE(ABORT,'Immutable saved view history'); END;
            CREATE TRIGGER IF NOT EXISTS view_commands_no_update BEFORE UPDATE ON commands
              BEGIN SELECT RAISE(ABORT,'Immutable saved view command'); END;
            CREATE TRIGGER IF NOT EXISTS view_commands_no_delete BEFORE DELETE ON commands
              BEGIN SELECT RAISE(ABORT,'Immutable saved view command'); END;
            """)

    @staticmethod
    def _private(path, directory=False):
        require(
            path == path.resolve() and not any(p.is_symlink() for p in (path, *path.parents)),
            "Private view aliases forbidden",
        )
        st = path.stat()
        require(
            st.st_uid == os.getuid()
            and not st.st_mode & 0o077
            and (path.is_dir() if directory else path.is_file() and st.st_nlink == 1),
            "Owned private view storage required",
        )
        return st.st_dev, st.st_ino

    @contextmanager
    def _db(self):
        self._private(self.root, True)
        before = self._private(self.path)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
                require(self._private(self.path) == before, "View database identity changed")
        finally:
            db.close()

    def _state(self, actor, engagement):
        membership = self.engine.store.membership(actor, engagement)
        require(
            membership in {"learn", "review", "instruct"},
            "Current engagement access required",
            status=403,
        )
        state = self.engine.get(actor, engagement)
        require(state.get("id") == engagement, "Engagement context differs", status=403)
        return state, digest({**_basis(state), "membership": membership})

    def _recheck(self, actor, engagement, state, basis):
        current, pin = self._state(actor, engagement)
        require(
            current["revision"] == state["revision"] and pin == basis,
            "Engagement changed; reload saved views",
            code="VIEW_CONTEXT_CONFLICT",
            status=409,
        )

    def make_reference(self, actor, engagement, *, kind, record_id, version=None):
        state, basis = self._state(actor, engagement)
        ref, _ = _resolve(state, kind, record_id, version)
        _reference(state, ref)
        self._recheck(actor, engagement, state, basis)
        return ref

    def _payload(self, state, payload):
        require(
            isinstance(payload, dict) and set(payload) == FIELDS,
            "Exact personal view fields required",
        )
        _text(payload["title"], 120, nonempty=True)
        _text(payload["query"], 1000)
        section = payload["section"]
        require(
            isinstance(section, str) and section in SECTIONS, "Supported workspace section required"
        )
        _integer(payload["scroll_top"], 1000000)
        framework = payload["framework"]
        _text(framework, 256, nonempty=True)
        require(
            isinstance(framework, str)
            and framework in ["all", *state["scope"].get("programs", [])],
            "Program filter outside current scope",
            code="TARGET_UNAVAILABLE",
            status=409,
        )
        table = payload["table"]
        if table is not None:
            require(
                isinstance(table, dict) and set(table) == {"id", "query", "sort", "page"},
                "Exact table state required",
            )
            require(
                isinstance(table["id"], str)
                and table["id"] in TABLES
                and TABLES[table["id"]][0] == section,
                "Table outside selected section",
            )
            _text(table["query"], 1000)
            _integer(table["page"], 10000)
            require(
                isinstance(table["sort"], str)
                and table["sort"] in ["", *TABLES[table["id"]][1].split()],
                "Unsupported table sort",
            )
        if payload["reference"] is not None:
            _reference(state, payload["reference"])
            require(
                REFERENCE_SECTIONS[payload["reference"]["kind"]] == section,
                "Reference outside saved section",
            )
        return json.loads(canonical(payload))

    @staticmethod
    def _row(db, actor, engagement, view_id):
        row = db.execute(
            "SELECT * FROM views WHERE id=? AND actor=? AND engagement=?",
            (view_id, actor, engagement),
        ).fetchone()
        require(row is not None, "Saved view unavailable", code="MISSING", status=404)
        content = json.loads(row["content"])
        from .personal_views_recovery import owner_chain

        mapping = [
            dict(r)
            for r in db.execute(
                "SELECT * FROM ownership_history WHERE view_id=? ORDER BY version", (view_id,)
            )
        ]
        first = db.execute(
            "SELECT content FROM history WHERE view_id=? AND version=1", (view_id,)
        ).fetchone()
        require(
            first is not None, "Saved view original owner unavailable", code="INTEGRITY", status=500
        )
        original = json.loads(first["content"])
        owner = owner_chain(mapping, view_id, original["actor_id"], engagement)
        valid_owners = {
            original["actor_id"],
            *[json.loads(m["content"])["to_actor"] for m in mapping],
        }

        history = db.execute(
            "SELECT content,sha256 FROM history WHERE view_id=? AND version=?",
            (view_id, row["version"]),
        ).fetchone()
        require(
            history is not None
            and row["content"] == history["content"]
            and row["sha256"] == history["sha256"] == digest(content)
            and owner == actor
            and content["actor_id"] in valid_owners
            and content["engagement_id"] == engagement
            and content["id"] == view_id
            and content["version"] == row["version"]
            and content["status"] == row["status"],
            "Saved view integrity failure",
            code="INTEGRITY",
            status=500,
        )
        return content

    def _view(self, content, state, basis):
        same = basis == content["context_basis_sha256"]
        output = {
            k: content[k] for k in ("id", "version", "status", "saved_at", "engagement_revision")
        }
        output.update(
            engagement_id=state["id"],
            context_status="CURRENT" if same else "CONTEXT_CHANGED",
            current_engagement_revision=state["revision"],
            revision_status="CURRENT"
            if state["revision"] == content["engagement_revision"]
            else "ENGAGEMENT_ADVANCED",
            personal_content_visible=same and content["status"] == "ACTIVE",
            navigation=None,
            restorable=False,
            formal_work_mutated=False,
            backup_status="EXPLICIT_COMPANION_SUPPORTED_NOT_AUTOMATICALLY_BACKED_UP",
        )
        if not output["personal_content_visible"]:
            return output
        user = content["user"]
        output["user"] = user
        try:
            self._payload(state, user)
            output["target_status"] = (
                _reference(state, user["reference"]) if user["reference"] else "NO_SELECTED_TARGET"
            )
            output["restorable"] = True
        except DomainError as exc:
            output["target_status"] = exc.code
        return output

    def read(self, actor, engagement, view_id):
        state, basis = self._state(actor, engagement)
        with self._db() as db:
            content = self._row(db, actor, engagement, view_id)
        output = self._view(content, state, basis)
        self._recheck(actor, engagement, state, basis)
        return output

    def listing(self, actor, engagement):
        state, basis = self._state(actor, engagement)
        with self._db() as db:
            ids = [
                r[0]
                for r in db.execute(
                    "SELECT id FROM views WHERE actor=? AND engagement=? "
                    "AND status='ACTIVE' ORDER BY id",
                    (actor, engagement),
                )
            ]
            values = [self._view(self._row(db, actor, engagement, i), state, basis) for i in ids]
        self._recheck(actor, engagement, state, basis)
        return values

    def restore(
        self, actor, engagement, view_id, *, expected_version, expected_engagement_revision
    ):
        state, basis = self._state(actor, engagement)
        require(
            type(expected_engagement_revision) is int
            and state["revision"] == expected_engagement_revision,
            "Engagement changed before restore",
            code="VIEW_CONTEXT_CONFLICT",
            status=409,
        )
        with self._db() as db:
            content = self._row(db, actor, engagement, view_id)
        require(
            type(expected_version) is int and content["version"] == expected_version,
            "View changed before restore",
            code="VIEW_CONFLICT",
            status=409,
        )
        output = self._view(content, state, basis)
        require(
            output["restorable"],
            "Saved view needs explicit review before restoration",
            code="VIEW_NOT_RESTORABLE",
            status=409,
        )
        output["navigation"] = {k: v for k, v in content["user"].items() if k != "title"}
        self._recheck(actor, engagement, state, basis)
        return output

    def _write(
        self,
        actor,
        engagement,
        view_id,
        payload,
        *,
        expected_version,
        expected_engagement_revision,
        command_id,
        clear=False,
    ):
        state, basis = self._state(actor, engagement)
        _text(command_id, 128, nonempty=True)
        require(type(expected_engagement_revision) is int, "Exact engagement revision required")
        envelope = {
            "view_id": view_id,
            "expected_version": expected_version,
            "expected_engagement_revision": expected_engagement_revision,
            "payload": payload,
            "clear": clear,
        }
        fingerprint = digest(envelope)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT * FROM commands WHERE actor=? AND engagement=? AND command_id=?",
                (actor, engagement, command_id),
            ).fetchone()
            if old:
                require(
                    old["digest"] == fingerprint,
                    "Saved view command reused",
                    code="VIEW_CONFLICT",
                    status=409,
                )
                content = self._row(db, actor, engagement, old["view_id"])
            else:
                require(
                    state["revision"] == expected_engagement_revision,
                    "Engagement changed before save",
                    code="VIEW_CONTEXT_CONFLICT",
                    status=409,
                )
                if view_id is None:
                    require(expected_version is None and not clear, "Explicit new view required")
                    counts = db.execute(
                        "SELECT COUNT(*),SUM(status='ACTIVE') FROM views "
                        "WHERE actor=? AND engagement=?",
                        (actor, engagement),
                    ).fetchone()
                    require(
                        counts[0] < 32 and (counts[1] or 0) < self.max_active,
                        "Personal view quota reached",
                        status=429,
                    )
                    view_id = "VIEW-" + digest([actor, engagement, command_id])[:32]
                    version = 1
                else:
                    prior = self._row(db, actor, engagement, view_id)
                    require(
                        type(expected_version) is int and prior["version"] == expected_version,
                        "View changed; reload before saving",
                        code="VIEW_CONFLICT",
                        status=409,
                    )
                    require(
                        prior["status"] == "ACTIVE",
                        "Cleared views cannot be resurrected",
                        code="VIEW_CLEARED",
                        status=409,
                    )
                    require(
                        prior["version"] < 200 or (clear and prior["version"] == 200),
                        "Personal view version quota reached",
                        status=429,
                    )
                    version = prior["version"] + 1
                user = None if clear else self._payload(state, payload)
                content = {
                    "id": view_id,
                    "actor_id": actor,
                    "engagement_id": engagement,
                    "version": version,
                    "status": "CLEARED" if clear else "ACTIVE",
                    "user": user,
                    "saved_at": datetime.now(UTC).isoformat(),
                    "engagement_revision": state["revision"],
                    "context_basis_sha256": basis,
                }
                raw = canonical(content)
                require(len(raw.encode()) <= 16384, "Saved view byte limit exceeded")
                require(
                    db.execute(
                        "SELECT COALESCE(SUM(length(CAST(content AS BLOB))),0) FROM history"
                    ).fetchone()[0]
                    + len(raw.encode())
                    <= 64 * 1024 * 1024,
                    "Private view storage quota reached",
                    status=429,
                )
                pin = digest(content)
                self._recheck(actor, engagement, state, basis)
                db.execute(
                    "INSERT INTO views VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                    "version=excluded.version,status=excluded.status,"
                    "content=excluded.content,sha256=excluded.sha256",
                    (view_id, actor, engagement, version, content["status"], raw, pin),
                )
                db.execute("INSERT INTO history VALUES(?,?,?,?)", (view_id, version, raw, pin))
                db.execute(
                    "INSERT INTO commands VALUES(?,?,?,?,?,?)",
                    (actor, engagement, command_id, fingerprint, view_id, version),
                )
            output = self._view(content, state, basis)
            self._recheck(actor, engagement, state, basis)
        return output

    def create(self, actor, engagement, payload, *, expected_engagement_revision, command_id):
        return self._write(
            actor,
            engagement,
            None,
            payload,
            expected_version=None,
            expected_engagement_revision=expected_engagement_revision,
            command_id=command_id,
        )

    def save(
        self,
        actor,
        engagement,
        view_id,
        payload,
        *,
        expected_version,
        expected_engagement_revision,
        command_id,
    ):
        return self._write(
            actor,
            engagement,
            view_id,
            payload,
            expected_version=expected_version,
            expected_engagement_revision=expected_engagement_revision,
            command_id=command_id,
        )

    def clear(
        self,
        actor,
        engagement,
        view_id,
        *,
        expected_version,
        expected_engagement_revision,
        command_id,
    ):
        return self._write(
            actor,
            engagement,
            view_id,
            None,
            expected_version=expected_version,
            expected_engagement_revision=expected_engagement_revision,
            command_id=command_id,
            clear=True,
        )
