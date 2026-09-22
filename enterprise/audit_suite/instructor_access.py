"""Private instructor access audit, separate from company history and immutable keys.

Hash chaining plus an independently retained head detects edited/truncated records.
This is local integrity checking, not protection against a privileged attacker able to
rewrite both files. Never stores credentials, source prose or caller-supplied error text.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .store import DomainError, digest

MAX_LOG_BYTES = 64 * 1024 * 1024
ZERO = "0" * 64


def identity_digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class InstructorAccessLog:
    def __init__(self, root: Path):
        self.root = Path(root).absolute()

    def _paths(self):
        if any(p.is_symlink() for p in [self.root, *self.root.parents]):
            raise ValueError("Unsafe audit path")
        if not self.root.exists():
            if self.root.parent.stat().st_mode & 0o077:
                raise ValueError("Audit parent is not private")
            self.root.mkdir(mode=0o700, exist_ok=True)
        if not self.root.is_dir() or self.root.stat().st_mode & 0o077:
            raise ValueError("Audit directory is not private")

    @staticmethod
    def _read_private(path: Path) -> bytes:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
                raise ValueError("Audit file is not private regular data")
            return stream.read(MAX_LOG_BYTES + 1)

    def _head(self, count: int, pin: str):
        temporary = self.root / (".head-" + uuid.uuid4().hex)
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(json.dumps({"count": count, "sha256": pin}, sort_keys=True).encode())
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.root / "head.json")
            directory = os.open(self.root, os.O_DIRECTORY | os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _verify(raw: bytes, head: dict) -> list[dict]:
        if len(raw) > MAX_LOG_BYTES or (raw and not raw.endswith(b"\n")):
            raise ValueError("Incomplete or oversized audit log")
        records, previous = [], ZERO
        for offset, line in enumerate(raw.splitlines(), 1):
            value = json.loads(line)
            pin = value.pop("sha256")
            if value["sequence"] != offset or value["previous_sha256"] != previous:
                raise ValueError("Audit chain mismatch")
            if digest(value) != pin:
                raise ValueError("Audit record mismatch")
            previous = pin
            records.append({**value, "sha256": pin})
        if head != {"count": len(records), "sha256": previous}:
            raise ValueError("Audit head mismatch")
        return records

    def append(
        self,
        *,
        actor: str,
        engagement: str,
        target: str | None,
        outcome: str,
        http_status: int,
        archive_sha256: str | None = None,
        key_sha256: str | None = None,
        source_sha256: str | None = None,
        binding_manifest_sha256: str | None = None,
        operation: str | None = None,
    ) -> dict:
        """Append a sanitized access result; failure prevents key response delivery."""
        try:
            if outcome not in {"SUCCESS", "DENIED", "NOT_FOUND", "UNAVAILABLE", "ERROR"}:
                raise ValueError("Unsupported audit outcome")
            if type(http_status) is not int or not 100 <= http_status <= 599:
                raise ValueError("Invalid HTTP status")
            pins = {
                "archive_sha256": archive_sha256,
                "key_sha256": key_sha256,
                "source_sha256": source_sha256,
                "binding_manifest_sha256": binding_manifest_sha256,
            }
            if any(v is not None and not re.fullmatch(r"[a-f0-9]{64}", v) for v in pins.values()):
                raise ValueError("Invalid audit pin")
            if outcome != "SUCCESS" and any(pins.values()):
                raise ValueError("Failed access cannot assert inspected source pins")
            if operation not in {None, "INDEX", "DETAIL", "BOUND_SNAPSHOT", "ORIGINAL"}:
                raise ValueError("Invalid audit operation")
            self._paths()
            path, head_path = self.root / "access.jsonl", self.root / "head.json"
            # Missing one side of an established log fails closed; never silently reset.
            if path.is_symlink() or head_path.is_symlink():
                raise ValueError("Audit aliases forbidden")
            if head_path.exists() and not path.exists():
                raise ValueError("Incomplete audit store")
            fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "r+b") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
                    raise ValueError("Invalid audit file")
                raw = stream.read(MAX_LOG_BYTES + 1)
                if not head_path.exists():
                    if raw:
                        raise ValueError("Missing audit head")
                    self._head(0, ZERO)
                head = json.loads(self._read_private(head_path))
                records = self._verify(raw, head)
                value = {
                    "schema": "INSTRUCTOR_ACCESS_V1",
                    "sequence": len(records) + 1,
                    "previous_sha256": head["sha256"],
                    "recorded_at": datetime.now(UTC).isoformat(),
                    "actor_digest": identity_digest(actor),
                    "engagement_digest": identity_digest(engagement),
                    "target_digest": identity_digest(target) if target is not None else None,
                    "operation": operation or ("DETAIL" if target is not None else "INDEX"),
                    "outcome": outcome,
                    "http_status": http_status,
                    **pins,
                }
                value["sha256"] = digest(value)
                encoded = (json.dumps(value, sort_keys=True) + "\n").encode()
                if len(raw) + len(encoded) > MAX_LOG_BYTES:
                    raise ValueError("Audit capacity reached")
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
                self._head(value["sequence"], value["sha256"])
                return value
        except Exception as error:
            raise DomainError(
                "Instructor access audit integrity unavailable", status=503
            ) from error

    def verify(self) -> list[dict]:
        """Private operator verification only; no HTTP/export projection."""
        try:
            self._paths()
            fd = os.open(self.root / "access.jsonl", os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
                    raise ValueError("Invalid audit file")
                return self._verify(
                    stream.read(MAX_LOG_BYTES + 1),
                    json.loads(self._read_private(self.root / "head.json")),
                )
        except Exception as error:
            raise DomainError(
                "Instructor access audit integrity unavailable", status=503
            ) from error
