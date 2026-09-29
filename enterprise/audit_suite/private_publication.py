"""Publish staged private directories without leaving a failed partial destination."""

import os
from pathlib import Path


def _sync(path: Path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def publish(stage: Path, destination: Path):
    """Caller owns both private parent directories and all staged members.

    Reserve a new target, durably move staged members, and roll back our moves on
    failure. This is not a multi-store atomic snapshot or concurrent-reader API.
    Existing destinations are never overwritten; unexpected foreign entries are
    never removed by rollback.
    """
    for root, _directories, files in os.walk(stage, topdown=False):
        for name in files:
            _sync(Path(root) / name)
        _sync(Path(root))
    destination.mkdir(mode=0o700)
    moved = []
    try:
        for member in stage.iterdir():
            os.rename(member, destination / member.name)
            moved.append(member.name)
        _sync(destination)
        _sync(destination.parent)
    except BaseException:
        for name in reversed(moved):
            os.rename(destination / name, stage / name)
        destination.rmdir()
        raise
