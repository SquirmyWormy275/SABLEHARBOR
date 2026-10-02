"""Private personal drafts, excluded from engagement history and current backup/export.

No autosubmit: formal command success and explicit discard are separate client actions.
Signout does not delete drafts. The current operation supports exact idempotent retries;
older operations conflict after a successor, preserving optimistic concurrency.
"""

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime

from .store import DomainError, digest

FIELDS = {
    "note.create": {"title", "text", "source_message_id", "control_id"},
    "workpaper.add": {
        "title",
        "text",
        "objective",
        "procedures",
        "conclusion",
        "section",
        "evidence_ids",
        "task_ids",
        "artifact_id",
        "control_id",
    },
    "workpaper.update": {
        "text",
        "objective",
        "procedures",
        "conclusion",
        "section",
        "evidence_ids",
        "task_ids",
        "artifact_id",
    },
}
MAX_BYTES = 100_000
# A collected workpaper can retain several MiB of exact calculations and many
# original citations. Keep those editable without changing note or owner quotas.
MAX_WORKPAPER_BYTES = 8 * 1024 * 1024
MAX_WORKPAPER_EVIDENCE_IDS = 5000
LEGACY_NARRATIVE_FIELDS = {"title", "text", "objective", "procedures", "conclusion", "section"}


class DraftStore:
    def __init__(self, store):
        self.store = store
        self.path = store.root / "personal-drafts.sqlite3"
        self._paths()
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS drafts(
                principal TEXT, engagement TEXT, action TEXT, object_id TEXT,
                version INTEGER, fields TEXT, context_digest TEXT, base_version INTEGER,
                updated_at TEXT, command_id TEXT, command_digest TEXT,
                PRIMARY KEY(principal,engagement,action,object_id))""")

    def _paths(self):
        if (
            any(p.is_symlink() for p in [self.path, *self.path.parents])
            or self.path.parent.stat().st_mode & 0o077
            or self.path.exists()
            and (not self.path.is_file() or self.path.stat().st_mode & 0o077)
        ):
            raise DomainError("Private personal draft storage required")

    @contextmanager
    def _db(self):
        self._paths()
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA secure_delete=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def _context(self, actor, engagement, action, object_id):
        state = self.store.get(actor, engagement)
        permission = self.store.membership(actor, engagement)
        if permission not in {"learn", "instruct"}:
            raise DomainError(
                "Personal drafting requires learner or instructor membership", status=403
            )
        if (
            action not in FIELDS
            or not isinstance(object_id, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", object_id)
        ):
            raise DomainError("Invalid personal draft identity")
        latest = None
        if action == "workpaper.update":
            workpaper = next((w for w in state.get("workpapers", []) if w["id"] == object_id), None)
            if workpaper is None:
                raise DomainError("Workpaper unavailable", status=404)
            latest = workpaper["versions"][-1]["version"] if workpaper["versions"] else 0
        elif object_id != "new":
            raise DomainError("Creation draft requires object new")
        legacy_basis = [
            engagement,
            permission,
            state.get("scope"),
            state.get("generation_epoch", 0),
            state.get("company_source_binding"),
        ]
        legacy_context = digest(legacy_basis)
        context = digest([*legacy_basis, state.get("evidence_acquisition")])
        return context, legacy_context, latest

    @staticmethod
    def _projection(row, context, legacy_context, latest):
        if row is None:
            return {
                "status": "EMPTY",
                "version": 0,
                "fields": {},
                "base_workpaper_version": None,
                "workpaper_stale": False,
                "updated_at": None,
            }
        value = {
            "version": row["version"],
            "updated_at": row["updated_at"],
            "base_workpaper_version": row["base_version"],
            "workpaper_stale": latest is not None and latest != row["base_version"],
        }
        if row["fields"] is None:
            return {**value, "status": "EMPTY", "fields": {}}
        if row["context_digest"] != context:
            if row["context_digest"] == legacy_context:
                fields = json.loads(row["fields"])
                return {
                    **value,
                    "status": "STALE_SOURCE",
                    "fields": {
                        key: field
                        for key, field in fields.items()
                        if key in LEGACY_NARRATIVE_FIELDS and isinstance(field, str)
                    },
                    "reason": (
                        "Older saved draft lacks an acquisition pin. Narrative text is "
                        "available for explicit review; old source links are withheld. "
                        "Discard the old saved version before saving a successor."
                    ),
                }
            return {
                **value,
                "status": "STALE",
                "reason": (
                    "Saved draft context differs from current scope, permissions, "
                    "company source or acquisition; fields are withheld and explicit "
                    "discard is required. Older draft formats may also require discard."
                ),
            }
        return {**value, "status": "DRAFT", "fields": json.loads(row["fields"])}

    def get(self, actor, engagement, action, object_id):
        context, legacy_context, latest = self._context(actor, engagement, action, object_id)
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM drafts WHERE principal=? AND engagement=? "
                "AND action=? AND object_id=?",
                (actor, engagement, action, object_id),
            ).fetchone()
            return self._projection(row, context, legacy_context, latest)

    def write(self, actor, engagement, action, object_id, payload, *, discard=False):
        context, legacy_context, latest = self._context(actor, engagement, action, object_id)
        allowed = (
            {"command_id", "expected_version"}
            if discard
            else {"command_id", "expected_version", "fields", "base_workpaper_version"}
        )
        if not isinstance(payload, dict) or set(payload) != allowed:
            raise DomainError("Exact draft command fields required")
        command, expected = payload["command_id"], payload["expected_version"]
        if (
            not isinstance(command, str)
            or not 1 <= len(command) <= 128
            or type(expected) is not int
            or expected < 0
        ):
            raise DomainError("Draft command ID and nonnegative version required")
        encoded, base = None, None
        if not discard:
            fields, base = payload["fields"], payload["base_workpaper_version"]
            if isinstance(fields, dict) and fields.get("control_id") not in (None, ""):
                state = self.store.get(actor, engagement)
                if not any(
                    control.get("id") == fields["control_id"]
                    for control in state.get("controls", [])
                ):
                    raise DomainError("Draft control must belong to the engagement scope")

            if not isinstance(fields, dict) or set(fields) - FIELDS[action]:
                raise DomainError("Unsupported draft fields")
            byte_limit = MAX_BYTES if action == "note.create" else MAX_WORKPAPER_BYTES
            for name, value in fields.items():
                if name in {"evidence_ids", "task_ids"}:
                    id_limit = MAX_WORKPAPER_EVIDENCE_IDS if name == "evidence_ids" else 500
                    if (
                        not isinstance(value, list)
                        or len(value) > id_limit
                        or any(not isinstance(v, str) or len(v) > 128 for v in value)
                    ):
                        raise DomainError("Invalid draft evidence IDs")
                elif value is not None and (not isinstance(value, str) or len(value) > byte_limit):
                    raise DomainError("Draft fields must be bounded text")
            if "task_ids" in fields:
                from .workpaper_links import validate_task_ids

                state = self.store.get(actor, engagement)
                control_id = fields.get("control_id")
                if action == "workpaper.update":
                    control_id = next(w for w in state["workpapers"] if w["id"] == object_id).get(
                        "control_id"
                    )
                validate_task_ids(state, control_id, fields["task_ids"])
            if action == "workpaper.update":
                if type(base) is not int or base < 0 or base > latest:
                    raise DomainError("Explicit existing base workpaper version required")
            elif base is not None:
                raise DomainError("Creation draft has no workpaper base version")
            encoded = json.dumps(
                fields,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
                ensure_ascii=action == "note.create",
            )
            if len(encoded.encode()) > byte_limit:
                raise DomainError(f"Personal draft exceeds {byte_limit} byte limit", status=413)
        fingerprint = digest([discard, payload])
        key = (actor, engagement, action, object_id)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM drafts WHERE principal=? AND engagement=? "
                "AND action=? AND object_id=?",
                key,
            ).fetchone()
            if row is not None and row["command_id"] == command:
                if row["command_digest"] != fingerprint:
                    raise DomainError("Draft retry payload changed", status=409)
                return self._projection(row, context, legacy_context, latest)
            if row is None and discard and expected == 0:
                return self._projection(None, context, legacy_context, latest)
            if (row["version"] if row else 0) != expected:
                raise DomainError("Draft changed; reload before replacing", status=409)
            if (
                row is not None
                and row["fields"] is not None
                and row["context_digest"] != context
                and not discard
            ):
                raise DomainError("Stale draft requires explicit discard", status=409)
            count, total = db.execute(
                "SELECT COUNT(*),COALESCE(SUM(LENGTH(CAST(fields AS BLOB))),0) "
                "FROM drafts WHERE principal=?",
                (actor,),
            ).fetchone()
            old_size = len(row["fields"].encode()) if row and row["fields"] else 0
            if not discard and (
                (row is None and count >= 500)
                or total - old_size + len(encoded.encode()) > 10_000_000
            ):
                raise DomainError("Personal draft quota exceeded", status=413)
            stamp = datetime.now(UTC).isoformat()
            db.execute(
                "INSERT INTO drafts VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO UPDATE SET "
                "version=excluded.version,fields=excluded.fields,context_digest=excluded.context_digest,"
                "base_version=excluded.base_version,updated_at=excluded.updated_at,"
                "command_id=excluded.command_id,command_digest=excluded.command_digest",
                (*key, expected + 1, encoded, context, base, stamp, command, fingerprint),
            )
            row = db.execute(
                "SELECT * FROM drafts WHERE principal=? AND engagement=? "
                "AND action=? AND object_id=?",
                key,
            ).fetchone()
            return self._projection(row, context, legacy_context, latest)
