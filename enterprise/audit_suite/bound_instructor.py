"""Operator-configured protected engagement explanation snapshots; no learner projection."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path

from .explanation_binding import verify_snapshot
from .instructor_access import InstructorAccessLog
from .store import DomainError, digest


def load_bindings(path: Path | None) -> dict:
    if path is None:
        return {}
    path = Path(path).absolute()
    try:
        if any(p.is_symlink() for p in [path, *path.parents]) or path.parent.stat().st_mode & 0o077:
            raise ValueError
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_size > 1024 * 1024:
                raise ValueError
            value = json.loads(stream.read())
        if not isinstance(value, dict):
            raise ValueError
        result = {}
        for engagement_id, binding in value.items():
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", engagement_id):
                raise ValueError
            if not isinstance(binding, dict) or set(binding) != {"path", "manifest_sha256"}:
                raise ValueError
            if not re.fullmatch(r"[a-f0-9]{64}", binding["manifest_sha256"]):
                raise ValueError
            target = Path(binding["path"])
            if not target.is_absolute():
                target = path.parent / target
            snapshot = verify_snapshot(target, expected_manifest_sha256=binding["manifest_sha256"])
            if snapshot["engagement"]["id"] != engagement_id:
                raise ValueError
            result[engagement_id] = {
                "path": target.absolute(),
                "manifest_sha256": binding["manifest_sha256"],
            }
        return result
    except Exception as error:
        raise DomainError(
            "Protected explanation binding configuration is invalid", status=503
        ) from error


def read_binding(engine, principal: dict, engagement_id: str, bindings: dict) -> dict:
    log = InstructorAccessLog(engine.store.root / "instructor-key-access")
    try:
        if engine.store.membership(principal["id"], engagement_id) != "instruct":
            raise DomainError("Instructor membership required", status=403)
        selected = bindings.get(engagement_id)
        if selected is None:
            raise DomainError("No protected explanation configured for this engagement", status=503)
        try:
            snapshot = verify_snapshot(
                selected["path"], expected_manifest_sha256=selected["manifest_sha256"]
            )
            if snapshot["engagement"]["id"] != engagement_id:
                raise ValueError
            snapshot_pin = hashlib.sha256(
                (selected["path"] / "snapshot.json").read_bytes()
            ).hexdigest()
            current = engine.store.get(principal["id"], engagement_id)
            bound_revision = snapshot["engagement"]["revision"]
            if (
                current["revision"] == bound_revision
                and digest(current) != snapshot["engagement"]["state_sha256"]
            ):
                raise ValueError
        except Exception as error:
            raise DomainError("Protected explanation integrity check failed", status=503) from error
        response = {
            "snapshot": snapshot,
            "binding": {
                "manifest_sha256": selected["manifest_sha256"],
                "engagement_id": engagement_id,
                "bound_revision": bound_revision,
                "current_revision": current["revision"],
                "status": "MATCHING_REVISION"
                if current["revision"] == bound_revision
                else "HISTORICAL_REVISION",
            },
        }
    except Exception as error:
        status = error.status if isinstance(error, DomainError) else 500
        log.append(
            actor=principal["id"],
            engagement=engagement_id,
            target="BOUND_SNAPSHOT",
            operation="BOUND_SNAPSHOT",
            outcome={403: "DENIED", 404: "NOT_FOUND", 503: "UNAVAILABLE"}.get(status, "ERROR"),
            http_status=status,
        )
        raise
    log.append(
        actor=principal["id"],
        engagement=engagement_id,
        target="BOUND_SNAPSHOT",
        operation="BOUND_SNAPSHOT",
        outcome="SUCCESS",
        http_status=200,
        key_sha256=snapshot_pin,
        binding_manifest_sha256=selected["manifest_sha256"],
    )
    return response
