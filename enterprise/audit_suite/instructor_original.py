"""Bounded private reads for explicitly selected protected archive originals."""

import os
import stat
from pathlib import Path

from .store import DomainError

MAX_ORIGINAL_BYTES = 4 * 1024 * 1024


def read_original(root: Path, scenario_id: str) -> bytes:
    path = root / "sources" / f"{scenario_id}.json"
    try:
        if any(p.is_symlink() for p in [path, *path.parents]):
            raise ValueError
        if any(p.stat().st_mode & 0o077 for p in [root, path.parent]):
            raise ValueError
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_mode & 0o077
                or before.st_nlink != 1
                or before.st_size > MAX_ORIGINAL_BYTES
            ):
                raise ValueError
            raw = stream.read(MAX_ORIGINAL_BYTES + 1)
            after = os.fstat(stream.fileno())
            current = path.stat(follow_symlinks=False)

            def identity(s):
                return (
                    s.st_dev,
                    s.st_ino,
                    s.st_mode,
                    s.st_nlink,
                    s.st_size,
                    s.st_mtime_ns,
                    s.st_ctime_ns,
                )

            if (
                len(raw) > MAX_ORIGINAL_BYTES
                or identity(before) != identity(after)
                or identity(after) != identity(current)
            ):
                raise ValueError
            return raw
    except (OSError, ValueError) as error:
        raise DomainError(
            "Instructor original unavailable or integrity check failed", status=503
        ) from error
