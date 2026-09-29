"""Explicit personal investigation context; never formal audit work or inferred intent.

This separate private database must be backed up separately until service backup
integration registers it. Saved links pin records; they do not attest sufficiency.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .store import DomainError, canonical, digest

COLLECTIONS = {
    "control": "controls",
    "task": "tasks",
    "artifact": "artifacts",
    "population": "populations",
    "selection": "selections",
    "workpaper": "workpapers",
}


def _basis(state):
    """Capture the authority and source context without rewriting historical links."""
    return {
        "scope": state["scope"],
        "company_source_binding": state.get("company_source_binding"),
        "evidence_acquisition": state.get("evidence_acquisition"),
        "permissions": sorted(state.get("permissions", [])),
    }


def _resolve(state, kind, row_id, version):
    if (
        not isinstance(kind, str)
        or kind not in COLLECTIONS
        or not isinstance(row_id, str)
        or not row_id
        or (version is not None and type(version) is not int)
    ):
        raise DomainError("Choose an existing supported investigation link")
    row = next((r for r in state.get(COLLECTIONS[kind], []) if r["id"] == row_id), None)
    if row is None:
        raise DomainError("Linked record is missing", code="MISSING")
    control = row.get("control_id") or row.get("coverage", {}).get("control_id")
    if control and control not in {c["id"] for c in state["controls"]}:
        raise DomainError("Linked record is outside current control scope", code="OUT_OF_SCOPE")
    boundary = row.get("boundary_id") or row.get("coverage", {}).get("boundary_id")
    if boundary and boundary not in state["scope"].get("boundaries", []):
        raise DomainError("Linked record is outside current boundary scope", code="OUT_OF_SCOPE")
    if kind in {"population", "selection"}:
        parent = (
            row
            if kind == "population"
            else next(
                (p for p in state.get("populations", []) if p["id"] == row.get("population_id")),
                None,
            )
        )
        if parent is None:
            raise DomainError("Linked selection population is missing", code="MISSING_PARENT")
        try:
            scope = json.loads(parent["immutable"]["scope_json"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DomainError("Population scope cannot be resolved", code="INVALID_SCOPE") from exc
        if scope.get("boundary_id") not in state["scope"].get("boundaries", []):
            raise DomainError("Population boundary is outside current scope", code="OUT_OF_SCOPE")
        if all(k in state["scope"] for k in ("period_start", "period_end")):

            def instant(value, end=False):
                stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if end and len(value) == 10:
                    stamp += timedelta(days=1)
                return (
                    stamp
                    if stamp.tzinfo
                    else stamp.replace(tzinfo=ZoneInfo(state["scope"].get("timezone", "UTC")))
                )

            if instant(scope["period_start"]) < instant(state["scope"]["period_start"]) or instant(
                scope["period_end"]
            ) > instant(state["scope"]["period_end"], True):
                raise DomainError("Population period is outside current scope", code="OUT_OF_SCOPE")
    if kind == "workpaper":
        if type(version) is not int or version < 1:
            raise DomainError("Select an exact workpaper version")
        record = next((v for v in row.get("versions", []) if v["version"] == version), None)
        if record is None:
            raise DomainError("Linked version is missing", code="MISSING_VERSION")
        pin = digest(record)
        historical = version != max(v["version"] for v in row["versions"])
    else:
        if version != row.get("version") or isinstance(version, bool):
            raise DomainError("Linked version changed", code="VERSION_CHANGED")
        pin = row["sha256"] if kind == "artifact" else digest(row.get("immutable", row))
        historical = False
    return {"kind": kind, "id": row_id, "version": version, "sha256": pin}, historical


class WorkspaceContexts:
    def __init__(self, private_root: Path, engine, *, max_active=16):
        self.root = Path(private_root).absolute()
        self.engine = engine
        if any(p.is_symlink() for p in [self.root, *self.root.parents]):
            raise DomainError("Context directory aliases are forbidden")
        if not self.root.is_dir() or self.root.stat().st_mode & 0o077:
            raise DomainError("Existing private0700 context directory required")
        if type(max_active) is not int or not 1 <= max_active <= 32:
            raise DomainError("Active context limit must be1–32")
        self.max_active = max_active
        self.path = self.root / "contexts.sqlite3"
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with self._db() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS contexts(id TEXT PRIMARY KEY,actor TEXT,engagement TEXT,
                  version INTEGER,status TEXT,content TEXT,sha256 TEXT);
              CREATE TABLE IF NOT EXISTS history(
                  context TEXT,version INTEGER,content TEXT,sha256 TEXT,
                  PRIMARY KEY(context,version));
              CREATE TABLE IF NOT EXISTS commands(actor TEXT,engagement TEXT,command_id TEXT,
                  digest TEXT,context TEXT,version INTEGER,
                  PRIMARY KEY(actor,engagement,command_id));
              CREATE TRIGGER IF NOT EXISTS history_no_update BEFORE UPDATE ON history
                BEGIN SELECT RAISE(ABORT,'Immutable context history'); END;
              CREATE TRIGGER IF NOT EXISTS history_no_delete BEFORE DELETE ON history
                BEGIN SELECT RAISE(ABORT,'Immutable context history'); END;
            """)

    @contextmanager
    def _db(self):
        if (
            any(p.is_symlink() for p in [self.path, *self.path.parents])
            or self.path.stat().st_mode & 0o077
        ):
            raise DomainError("Private regular context database required")
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _state(self, actor, engagement):
        if self.engine.store.membership(actor, engagement) not in {"learn", "review", "instruct"}:
            raise DomainError("Current engagement membership required", status=403)
        return self.engine.get(actor, engagement)

    def make_link(self, actor, engagement, *, kind, record_id, version=None):
        return _resolve(self._state(actor, engagement), kind, record_id, version)[0]

    def _payload(self, state, payload):
        if not isinstance(payload, dict) or set(payload) != {
            "title",
            "question",
            "next_step",
            "links",
        }:
            raise DomainError("Explicit title, question, next step and typed links required")
        for field, limit in [("title", 200), ("question", 4000), ("next_step", 2000)]:
            if (
                not isinstance(payload[field], str)
                or len(payload[field]) > limit
                or (field != "next_step" and not payload[field].strip())
            ):
                raise DomainError(f"Bounded user-authored {field} required")
        if not isinstance(payload["links"], list) or len(payload["links"]) > 24:
            raise DomainError("At most24 explicitly chosen links allowed")
        seen = set()
        for link in payload["links"]:
            if not isinstance(link, dict) or set(link) != {"kind", "id", "version", "sha256"}:
                raise DomainError("Exact typed, version-pinned links required")
            expected, _ = _resolve(state, link["kind"], link["id"], link["version"])
            if link != expected:
                raise DomainError(
                    "Linked record changed; inspect before saving", code="STALE_LINK", status=409
                )
            key = canonical(link)
            if key in seen:
                raise DomainError("Duplicate investigation link")
            seen.add(key)
        return json.loads(canonical(payload))

    @staticmethod
    def _row(db, actor, engagement, context_id):
        row = db.execute(
            "SELECT * FROM contexts WHERE id=? AND actor=? AND engagement=?",
            (context_id, actor, engagement),
        ).fetchone()
        if row is None:
            raise DomainError("Context unavailable", status=404)
        if digest(json.loads(row["content"])) != row["sha256"]:
            raise DomainError("Context integrity failure", code="INTEGRITY", status=500)
        return row

    @staticmethod
    def _view(content, state):
        links = []
        for link in content["user"]["links"]:
            try:
                current, historical = _resolve(state, link["kind"], link["id"], link["version"])
                status = "EXACT_PIN_AVAILABLE" if current == link else "CONTENT_CHANGED"
                if current == link and historical:
                    status = "HISTORICAL_VERSION_AVAILABLE"
            except DomainError as exc:
                status = exc.code
            links.append({"reference": link, "status": status})
        return {
            **content,
            "scope_status": "CURRENT"
            if digest(state["scope"]) == content["scope_sha256"]
            else "SCOPE_CHANGED",
            "context_status": (
                "BASIS_UNRECORDED"
                if "context_basis_sha256" not in content
                else "CURRENT"
                if digest(_basis(state)) == content["context_basis_sha256"]
                else "CONTEXT_CHANGED"
            ),
            "link_status": links,
            "formal_work_mutated": False,
            "reference_validation": "RECORDED_METADATA_AND_VERSION_ONLY",
            "limits": ["Links do not prove artifact bytes were inspected or remain downloadable."],
            "backup_status": "SEPARATE_PRIVATE_STORE_NOT_YET_INTEGRATED",
        }

    def _write(
        self, actor, engagement, *, context_id, expected_version, payload, command_id, reset=False
    ):
        state = self._state(actor, engagement)
        if not isinstance(command_id, str) or not 1 <= len(command_id) <= 128:
            raise DomainError("Explicit save command identifier required")
        envelope = {
            "context_id": context_id,
            "expected_version": expected_version,
            "payload": payload,
            "reset": reset,
        }
        fingerprint = digest(envelope)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            replay = db.execute(
                "SELECT * FROM commands WHERE actor=? AND engagement=? AND command_id=?",
                (actor, engagement, command_id),
            ).fetchone()
            if replay:
                if replay["digest"] != fingerprint:
                    raise DomainError("Context command ID reused", status=409)
                row = db.execute(
                    "SELECT * FROM history WHERE context=? AND version=?",
                    (replay["context"], replay["version"]),
                ).fetchone()
                if digest(json.loads(row["content"])) != row["sha256"]:
                    raise DomainError("Context history changed")
                return self._view(json.loads(row["content"]), state)
            if context_id is None:
                if expected_version is not None or reset:
                    raise DomainError("Explicit new-context creation required")
                count = db.execute(
                    "SELECT COUNT(*) FROM contexts WHERE actor=? AND engagement=? "
                    "AND status='ACTIVE'",
                    (actor, engagement),
                ).fetchone()[0]
                if count >= self.max_active:
                    raise DomainError("Active context limit reached", status=429)
                context_id = "CTX-" + digest([actor, engagement, command_id])[:32]
                version = 1
            else:
                row = self._row(db, actor, engagement, context_id)
                if type(expected_version) is not int or row["version"] != expected_version:
                    raise DomainError(
                        "Context changed; reload before saving", code="CONTEXT_CONFLICT", status=409
                    )
                if row["status"] == "RESET":
                    raise DomainError("Create a new context after reset")
                if row["version"] >= 200:
                    raise DomainError("Context version limit reached", status=429)
                version = row["version"] + 1
            user = (
                {"title": "", "question": "", "next_step": "", "links": []}
                if reset
                else self._payload(state, payload)
            )
            current = self._state(actor, engagement)
            if current["revision"] != state["revision"] or digest(_basis(current)) != digest(
                _basis(state)
            ):
                raise DomainError(
                    "Engagement changed during save; inspect current links", status=409
                )
            content = {
                "id": context_id,
                "version": version,
                "status": "RESET" if reset else "ACTIVE",
                "user": user,
                "scope": state["scope"],
                "scope_sha256": digest(state["scope"]),
                "context_basis": _basis(state),
                "context_basis_sha256": digest(_basis(state)),
                "engagement_revision": state["revision"],
                "saved_at": datetime.now(UTC).isoformat(),
            }
            raw = canonical(content)
            pin = digest(content)
            db.execute(
                "INSERT INTO contexts VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                "version=excluded.version,status=excluded.status,content=excluded.content,sha256=excluded.sha256",
                (context_id, actor, engagement, version, content["status"], raw, pin),
            )
            db.execute("INSERT INTO history VALUES(?,?,?,?)", (context_id, version, raw, pin))
            db.execute(
                "INSERT INTO commands VALUES(?,?,?,?,?,?)",
                (actor, engagement, command_id, fingerprint, context_id, version),
            )
        return self._view(content, state)

    def create(self, actor, engagement, payload, *, command_id):
        return self._write(
            actor,
            engagement,
            context_id=None,
            expected_version=None,
            payload=payload,
            command_id=command_id,
        )

    def save(self, actor, engagement, context_id, payload, *, expected_version, command_id):
        return self._write(
            actor,
            engagement,
            context_id=context_id,
            expected_version=expected_version,
            payload=payload,
            command_id=command_id,
        )

    def reset(self, actor, engagement, context_id, *, expected_version, command_id):
        return self._write(
            actor,
            engagement,
            context_id=context_id,
            expected_version=expected_version,
            payload=None,
            command_id=command_id,
            reset=True,
        )

    def read(self, actor, engagement, context_id):
        state = self._state(actor, engagement)
        with self._db() as db:
            row = self._row(db, actor, engagement, context_id)
        return self._view(json.loads(row["content"]), state)

    def listing(self, actor, engagement):
        state = self._state(actor, engagement)
        with self._db() as db:
            ids = [
                r["id"]
                for r in db.execute(
                    "SELECT id FROM contexts WHERE actor=? AND engagement=? "
                    "AND status='ACTIVE' ORDER BY id",
                    (actor, engagement),
                )
            ]
            contents = [
                json.loads(self._row(db, actor, engagement, identifier)["content"])
                for identifier in ids
            ]
        return [self._view(c, state) for c in contents]
