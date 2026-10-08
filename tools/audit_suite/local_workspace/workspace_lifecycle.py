"""Private local lifecycle primitives; no application construction at import."""

import ctypes
import hashlib
import json
import os
import stat
import uuid
from pathlib import Path


class Refused(RuntimeError):
    pass


def require(value, reason):
    if not value:
        raise Refused(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def same(left, right):
    return canonical(left) == canonical(right)


def metadata(path):
    s = Path(path).lstat()
    return tuple(
        getattr(s, "st_" + k)
        for k in ("dev", "ino", "mode", "nlink", "uid", "gid", "size", "mtime_ns", "ctime_ns")
    )


def unaliased(path):
    p = Path(path)
    require(
        p.is_absolute() and p == p.resolve() and not any(q.is_symlink() for q in (p, *p.parents)),
        "Aliased path refused",
    )
    return p


def read_pin(pin, *, private=False):
    require(type(pin) is dict and set(pin) >= {"path", "sha256"}, "Filled file pin required")
    p = unaliased(pin["path"])
    before = metadata(p)
    require(
        stat.S_ISREG(before[2]) and before[3] == 1 and before[6] <= 64 * 1024**2,
        "Ordinary bounded single-link input required",
    )
    if private:
        require(
            before[4] == os.getuid() and stat.S_IMODE(before[2]) == 0o600,
            "Owned private input required",
        )
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        require(
            tuple(
                getattr(os.fstat(stream.fileno()), "st_" + k)
                for k in (
                    "dev",
                    "ino",
                    "mode",
                    "nlink",
                    "uid",
                    "gid",
                    "size",
                    "mtime_ns",
                    "ctime_ns",
                )
            )
            == before,
            "Held input identity differs",
        )
        raw = stream.read(before[6] + 1)
        require(
            tuple(
                getattr(os.fstat(stream.fileno()), "st_" + k)
                for k in (
                    "dev",
                    "ino",
                    "mode",
                    "nlink",
                    "uid",
                    "gid",
                    "size",
                    "mtime_ns",
                    "ctime_ns",
                )
            )
            == before,
            "Held input changed",
        )
    require(
        len(raw) == before[6]
        and metadata(p) == before
        and hashlib.sha256(raw).hexdigest() == pin["sha256"],
        "Selected input changed",
    )
    return raw


def pinned_json(pin, **kwargs):
    return json.loads(read_pin(pin, **kwargs))


def file_pin(path):
    p = unaliased(path)
    before = metadata(p)
    require(
        stat.S_ISREG(before[2]) and before[3] == 1 and before[6] <= 64 * 1024**2,
        "Ordinary bounded single-link input required",
    )
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:

        def held():
            return tuple(
                getattr(os.fstat(stream.fileno()), "st_" + k)
                for k in (
                    "dev",
                    "ino",
                    "mode",
                    "nlink",
                    "uid",
                    "gid",
                    "size",
                    "mtime_ns",
                    "ctime_ns",
                )
            )

        require(held() == before, "Held input identity differs")
        raw = stream.read(before[6] + 1)
        require(held() == before, "Held input changed")
    require(len(raw) == before[6] and metadata(p) == before, "Current input changed")
    return {"path": str(p), "sha256": hashlib.sha256(raw).hexdigest()}


def private_output(path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    return os.fdopen(fd, "wb")


def write_once(path, value):
    p = Path(path)
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    tmp = p.parent / ("." + p.name + "-" + uuid.uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        publish_no_replace(tmp, p)
        directory = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if tmp.exists():
            tmp.unlink()
    return {"path": str(p), "sha256": hashlib.sha256(raw).hexdigest()}


def publish_no_replace(temporary, destination):
    """Linux atomic publication of an already fsynced file; no overwrite fallback."""
    library = ctypes.CDLL(None, use_errno=True)
    rename = library.renameat2
    rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    rename.restype = ctypes.c_int
    # AT_FDCWD=-100, RENAME_NOREPLACE=1. No final basename exists until complete.
    if rename(-100, os.fsencode(temporary), -100, os.fsencode(destination), 1) != 0:
        raise OSError(ctypes.get_errno(), "Atomic no-overwrite receipt publication refused")


def atomic_pointer(path, value):
    p = Path(path)
    tmp = p.parent / ("." + p.name + "-" + uuid.uuid4().hex)
    write_once(tmp, value)
    os.replace(tmp, p)
    fd = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def secure_directory(path, *, create=False):
    p = Path(path)
    if create:
        p.mkdir(mode=0o700, parents=False, exist_ok=True)
    p = unaliased(p)
    s = p.stat()
    require(
        stat.S_ISDIR(s.st_mode) and s.st_uid == os.getuid() and stat.S_IMODE(s.st_mode) == 0o700,
        "Owned private directory required",
    )
    return p


def process_identity(pid):
    p = Path("/proc") / str(pid)
    try:
        return {
            "pid": pid,
            "start_ticks": (p / "stat").read_text().rsplit(")", 1)[1].split()[19],
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "uid": p.stat().st_uid,
            "executable": os.readlink(p / "exe"),
        }
    except FileNotFoundError:
        return None


def require_same_process(identity):
    require(
        type(identity) is dict and same(process_identity(identity["pid"]), identity),
        "Stale process identity refused",
    )


def refresh_pair(rooms, previous_references, output, service, explanation):
    """Normal serializers, after graceful drain and while room lifetime locks remain held.

    All retained business/lifetime/Key/history choices remain identical. Only
    current signed authority and full logout inventories are carried forward.
    Never mutates a prior configuration or accepted base/checkpoint.
    """
    require(set(rooms) == set(previous_references) == {"CLEAN", "MESSY"}, "Exact pair required")
    out = Path(output)
    out.mkdir(mode=0o700)
    result = {}
    for mode in ("CLEAN", "MESSY"):
        room = rooms[mode]
        previous = pinned_json(previous_references[mode])
        require(
            same(
                previous["retained_workroom"],
                {"path": str(room.path), "sha256": room.expected_sha256},
            ),
            "Reference configuration belongs to another retained workroom",
        )
        store = room.sealed_store
        store.check_prefix()
        store.authority.read_head()
        store.session_authority.check_revocations(store.prefix["sha256"], room.engagement)
        head = dict(store.authority_head)
        revoked = dict(store.session_authority.known_revocations)
        old = room.config
        require("history_integrity" in old, "Selected managed lifetime required")
        with room.world.locked():
            base = service.configuration(
                room.world, room.binding_path, room.binding_sha256, repository=room.repository
            )
            retained = service.sealed_configuration(
                base,
                old["sealed_history"],
                head,
                repository=room.repository,
                session_revocations=revoked,
                compact_prefix=old.get("compact_prefix"),
                history_integrity=old["history_integrity"],
            )
        expected = old | {"authority_head": head, "session_revocations": revoked}
        require(same(retained, expected), "Serializer changed an unselected retained field")
        retained_pin = write_once(out / (mode + "_RETAINED_CONFIGURATION.json"), retained)
        settings = dict(previous["features"])
        args = (
            retained_pin["path"],
            retained_pin["sha256"],
            previous["explanation_bindings"]["path"],
            previous["explanation_bindings"]["sha256"],
        )
        require(
            "reference_archive" in previous and "reference_crosswalk" in previous,
            "Selected reference configuration required",
        )
        reference = explanation.reference_configuration(
            *args,
            repository=room.repository,
            reference_archive=previous["reference_archive"],
            reference_crosswalk=previous["reference_crosswalk"],
            **settings,
        )
        require(
            same(reference, previous | {"retained_workroom": retained_pin}),
            "Serializer changed an unselected Key, feature, crosswalk or Source field",
        )
        result[mode] = write_once(out / (mode + "_REFERENCE_CONFIGURATION.json"), reference)
    write_once(
        out / "HANDOFF.json",
        {
            "schema": "SH_LOCAL_WORKSPACE_NORMAL_STOP_CONFIGURATION_HANDOFF_V1",
            "modes": result,
            "normal_serializers_used": True,
            "same_accepted_base_ledger_Key_and_engagements": True,
            "all_signed_logout_records_and_current_heads_carried_forward": True,
            "prior_configuration_or_base_modified": False,
        },
    )
    return result
