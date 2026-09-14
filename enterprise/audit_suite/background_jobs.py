"""Durable bounded meeting jobs around the unchanged Engine.command API.

Interrupted model computation may repeat after explicit retry. Engine command
receipts protect audit mutations; this does not promise exactly-once inference.
"""

import fcntl
import json
import os
import sqlite3
import stat
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .store import DomainError, canonical, digest

PERMISSIONS = {"learn", "instruct"}
ERRORS = {
    "REVISION_CONFLICT": "Engagement changed. Inspect its state and submit a new command.",
    "ACCESS_DENIED": "Access changed. Restore authorized access before deciding whether to retry.",
    "INTERRUPTED": (
        "Execution interrupted. Inspect the engagement before retrying; "
        "model computation may repeat."
    ),
    "EXECUTION_FAILED": "Action failed. Inspect the engagement before explicitly retrying.",
    "INFERENCE_TIMEOUT": (
        "The local model exceeded its configured wait. No reply was saved. "
        "Inspect the engagement before explicitly retrying; model computation may repeat."
    ),
    "INVALID_COMMAND": "The original command is invalid. Correct it and submit a new command.",
    "INTEGRITY": "The retained command does not match its original digest.",
    "SOURCE_CONTEXT_UNAVAILABLE": (
        "Selected source records are unavailable or no longer valid for this contact. "
        "Inspect source access, versions and context limits before submitting a new command."
    ),
    "INVALID_SOURCE_SELECTION": (
        "The source selection is invalid. Choose one to four exact original versions "
        "or remove the explicit selection, then submit a new command."
    ),
}


def now():
    return datetime.now(UTC).isoformat()


class BackgroundJobs:
    def __init__(self, private_root: Path, engine, *, max_workers=2, max_pending=32):
        self.root = Path(private_root).absolute()
        if any(p.is_symlink() for p in [self.root, *self.root.parents]):
            raise DomainError("Job store aliases are forbidden")
        if not self.root.is_dir() or self.root.stat().st_mode & 0o077:
            raise DomainError("Existing private 0700 job directory required")
        if type(max_workers) is not int or not 1 <= max_workers <= 4:
            raise DomainError("Worker count must be1–4")
        if type(max_pending) is not int or not 1 <= max_pending <= 128:
            raise DomainError("Pending job quota must be1–128")
        self.engine, self.max_workers, self.max_pending = engine, max_workers, max_pending
        self.path = self.root / "jobs.sqlite3"
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        self.mutex, self.threads = threading.Lock(), {}
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS capacity(id INTEGER PRIMARY KEY CHECK(id=1),
                    workers INTEGER NOT NULL, pending INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs(
                    id TEXT PRIMARY KEY, actor TEXT, engagement TEXT, command_id TEXT,
                    command TEXT, command_digest TEXT, expected_revision INTEGER,
                    status TEXT, job_revision INTEGER, attempts INTEGER,
                    created_at TEXT, updated_at TEXT, result_revision INTEGER, error_code TEXT,
                    UNIQUE(engagement,command_id));
                CREATE TABLE IF NOT EXISTS transitions(
                    job TEXT, revision INTEGER, status TEXT, error_code TEXT, recorded_at TEXT,
                    PRIMARY KEY(job,revision));
                CREATE TRIGGER IF NOT EXISTS command_immutable BEFORE UPDATE OF
                  actor,engagement,command_id,command,command_digest,expected_revision ON jobs
                  BEGIN SELECT RAISE(ABORT,'Immutable job command'); END;
            """)
            db.execute("INSERT OR IGNORE INTO capacity VALUES(1,?,?)", (max_workers, max_pending))
            limits = db.execute("SELECT workers,pending FROM capacity WHERE id=1").fetchone()
            self.max_workers, self.max_pending = limits["workers"], limits["pending"]
            if (
                type(self.max_workers) is not int
                or not 1 <= self.max_workers <= 4
                or type(self.max_pending) is not int
                or not 1 <= self.max_pending <= 128
            ):
                raise DomainError("Stored worker capacity is invalid", status=503)
        self.recover()

    @contextmanager
    def _db(self):
        if (
            any(p.is_symlink() for p in [self.path, *self.path.parents])
            or not self.path.is_file()
            or self.path.stat().st_mode & 0o077
        ):
            raise DomainError("Private regular job database required")
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def _lock(self, job_id):
        path = self.root / ("worker-" + digest(job_id) + ".lock")
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        acquired = False
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except BlockingIOError:
                pass
            yield acquired
        finally:
            if acquired:
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _authorize(self, actor, engagement):
        if self.engine.store.membership(actor, engagement) not in PERMISSIONS:
            raise DomainError("Current learner or instructor access required", status=403)

    @staticmethod
    def _row(db, actor, engagement, job_id):
        row = db.execute(
            "SELECT * FROM jobs WHERE id=? AND actor=? AND engagement=?",
            (job_id, actor, engagement),
        ).fetchone()
        if row is None:
            raise DomainError("Job unavailable", status=404)
        return dict(row)

    @staticmethod
    def _transition(db, job_id, status, error=None, result=None):
        db.execute(
            "UPDATE jobs SET status=?,job_revision=job_revision+1,updated_at=?, "
            "error_code=?,result_revision=?,attempts=attempts+? WHERE id=?",
            (status, now(), error, result, int(status == "RUNNING"), job_id),
        )
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        db.execute(
            "INSERT INTO transitions VALUES(?,?,?,?,?)",
            (job_id, row["job_revision"], status, error, row["updated_at"]),
        )

    @staticmethod
    def _public(row):
        fields = (
            "id",
            "status",
            "job_revision",
            "expected_revision",
            "attempts",
            "created_at",
            "updated_at",
            "result_revision",
            "error_code",
        )
        return {
            **{k: row[k] for k in fields},
            "kind": "meeting.message",
            "error_message": ERRORS.get(row["error_code"]),
            "retry_requires_inspection": row["status"] in {"FAILED", "INTERRUPTED"},
        }

    def submit(self, actor, engagement, command):
        self._authorize(actor, engagement)
        if (
            not isinstance(command, dict)
            or set(command) != {"command_id", "expected_revision", "kind", "payload"}
            or command.get("kind") != "meeting.message"
            or len(canonical(command)) > 50000
        ):
            raise DomainError("Exact bounded meeting.message command required")
        fingerprint = digest(command)
        self.engine.store._validate_command(command)
        with self._db() as db:
            prior = db.execute(
                "SELECT * FROM jobs WHERE engagement=? AND command_id=?",
                (engagement, command["command_id"]),
            ).fetchone()
            if prior:
                if prior["actor"] != actor or prior["command_digest"] != fingerprint:
                    raise DomainError(
                        "Command ID already used", code="IDEMPOTENCY_CONFLICT", status=409
                    )
                return self._public(dict(prior))
        # This checks command syntax, current authorization and committed replay first.
        replay = self.engine.store.preflight(actor, engagement, command, permissions=PERMISSIONS)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute(
                "SELECT * FROM jobs WHERE engagement=? AND command_id=?",
                (engagement, command["command_id"]),
            ).fetchone()
            if prior:
                if prior["actor"] != actor or prior["command_digest"] != fingerprint:
                    raise DomainError(
                        "Command ID already used", code="IDEMPOTENCY_CONFLICT", status=409
                    )
                return self._public(dict(prior))
            count = db.execute(
                "SELECT COUNT(*) FROM jobs WHERE status IN ('PENDING','RUNNING')"
            ).fetchone()[0]
            if replay is None and count >= self.max_pending:
                raise DomainError("Pending job quota reached", code="JOB_QUOTA", status=429)
            jid = "JOB-" + digest([actor, engagement, command["command_id"]])[:32]
            timestamp = now()
            status = "COMPLETED" if replay is not None else "PENDING"
            db.execute(
                "INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    jid,
                    actor,
                    engagement,
                    command["command_id"],
                    canonical(command),
                    fingerprint,
                    command["expected_revision"],
                    status,
                    0,
                    0,
                    timestamp,
                    timestamp,
                    replay["revision"] if replay is not None else None,
                    None,
                ),
            )
            db.execute(
                "INSERT INTO transitions VALUES(?,?,?,?,?)", (jid, 0, status, None, timestamp)
            )
            return self._public(self._row(db, actor, engagement, jid))

    def read(self, actor, engagement, job_id):
        self._authorize(actor, engagement)
        with self._db() as db:
            return self._public(self._row(db, actor, engagement, job_id))

    def input(self, actor, engagement, job_id):
        """Explicit authorized inspection of the original command, never inference context."""
        self._authorize(actor, engagement)
        with self._db() as db:
            row = self._row(db, actor, engagement, job_id)
        command = json.loads(row["command"])
        if digest(command) != row["command_digest"] or command.get("kind") != "meeting.message":
            raise DomainError("Retained job input integrity failure", code="INTEGRITY", status=500)
        self._authorize(actor, engagement)
        return command

    def listing(self, actor, engagement):
        self._authorize(actor, engagement)
        with self._db() as db:
            rows = db.execute(
                "SELECT * FROM jobs WHERE actor=? AND engagement=? "
                "ORDER BY created_at DESC LIMIT 100",
                (actor, engagement),
            ).fetchall()
        return [self._public(dict(row)) for row in rows]

    def _reserve_worker(self):
        # A store retains its initially configured capacity across processes/restarts.
        for slot in range(self.max_workers):
            path = self.root / f"capacity-{slot}.lock"
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
                os.close(fd)
                raise DomainError("Private worker slot required", status=503)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fd
            except BlockingIOError:
                os.close(fd)
        raise DomainError(
            "Worker capacity reached; job remains pending", code="JOB_CAPACITY", status=429
        )

    def start(self, actor, engagement, job_id):
        current = self.read(actor, engagement, job_id)
        if current["status"] != "PENDING":
            return current
        with self.mutex:
            self.threads = {k: t for k, t in self.threads.items() if t.is_alive()}
            if job_id in self.threads:
                return current
            if len(self.threads) >= self.max_workers:
                raise DomainError(
                    "Worker capacity reached; job remains pending", code="JOB_CAPACITY", status=429
                )
            worker_fd = self._reserve_worker()
            thread = threading.Thread(
                target=self._execute, args=(actor, engagement, job_id, worker_fd), daemon=True
            )
            self.threads[job_id] = thread
            try:
                thread.start()
            except Exception:
                os.close(worker_fd)
                raise
        return self.read(actor, engagement, job_id)

    def _execute(self, actor, engagement, job_id, worker_fd):
        try:
            self._execute_job(actor, engagement, job_id)
        finally:
            fcntl.flock(worker_fd, fcntl.LOCK_UN)
            os.close(worker_fd)

    def _execute_job(self, actor, engagement, job_id):
        with self._lock(job_id) as acquired:
            if not acquired:
                return
            with self._db() as db:
                db.execute("BEGIN IMMEDIATE")
                row = self._row(db, actor, engagement, job_id)
                if row["status"] != "PENDING":
                    return
                self._transition(db, job_id, "RUNNING")
            try:
                self._authorize(actor, engagement)
                command = json.loads(row["command"])
                if digest(command) != row["command_digest"]:
                    raise DomainError("Command digest differs", code="INTEGRITY", status=500)
                result = self.engine.command(actor, engagement, command)
                status, error, revision = "COMPLETED", None, result["revision"]
            except DomainError as exc:
                if exc.code in {
                    "SOURCE_CONTEXT_UNAVAILABLE",
                    "INVALID_SOURCE_SELECTION",
                    "INFERENCE_TIMEOUT",
                }:
                    status, error = "FAILED", exc.code
                elif exc.status == 409:
                    status, error = "CONFLICTED", "REVISION_CONFLICT"
                elif exc.status in {401, 403, 404}:
                    status, error = "FAILED", "ACCESS_DENIED"
                elif getattr(exc, "code", None) == "INTEGRITY":
                    status, error = "FAILED", "INTEGRITY"
                elif exc.status in {400, 422}:
                    status, error = "FAILED", "INVALID_COMMAND"
                else:
                    status, error = "FAILED", "EXECUTION_FAILED"
                revision = None
            except Exception:
                status, error, revision = "FAILED", "EXECUTION_FAILED", None
            with self._db() as db:
                db.execute("BEGIN IMMEDIATE")
                self._transition(db, job_id, status, error, revision)

    def retry(self, actor, engagement, job_id, *, observed_job_revision):
        self._authorize(actor, engagement)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._row(db, actor, engagement, job_id)
            if (
                type(observed_job_revision) is not int
                or observed_job_revision != row["job_revision"]
                or row["status"] not in {"FAILED", "INTERRUPTED"}
            ):
                raise DomainError(
                    "Inspect a failed or interrupted job before retry",
                    code="JOB_CHANGED",
                    status=409,
                )
            count = db.execute(
                "SELECT COUNT(*) FROM jobs WHERE status IN ('PENDING','RUNNING')"
            ).fetchone()[0]
            if count >= self.max_pending:
                raise DomainError("Pending job quota reached", code="JOB_QUOTA", status=429)
            self._transition(db, job_id, "PENDING")
        return self.start(actor, engagement, job_id)

    def recover(self):
        """Mark abandoned RUNNING work interrupted; never replay computation on startup."""
        with self._db() as db:
            running = [r["id"] for r in db.execute("SELECT id FROM jobs WHERE status='RUNNING'")]
        for jid in running:
            with self._lock(jid) as acquired:
                if not acquired:
                    continue
                with self._db() as db:
                    db.execute("BEGIN IMMEDIATE")
                    if (
                        db.execute("SELECT status FROM jobs WHERE id=?", (jid,)).fetchone()[0]
                        == "RUNNING"
                    ):
                        self._transition(db, jid, "INTERRUPTED", "INTERRUPTED")
