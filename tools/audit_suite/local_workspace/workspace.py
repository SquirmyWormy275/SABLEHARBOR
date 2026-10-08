"""Private Source candidate for one local pair. Requires a Root-admitted release.

The public commands are start/status/stop/restart. No product work occurs at
import. No credentials, cookies, request bodies or exception messages are logged.
"""

import argparse
import asyncio
import contextlib
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from workspace_lifecycle import (
    Refused,
    atomic_pointer,
    canonical,
    file_pin,
    metadata,
    pinned_json,
    private_output,
    process_identity,
    read_pin,
    refresh_pair,
    require,
    require_same_process,
    same,
    secure_directory,
    unaliased,
    write_once,
)

PORTS = {"CLEAN": 8782, "MESSY": 8783}
URLS = {mode: "http://127.0.0.1:" + str(port) for mode, port in PORTS.items()}


def load_release(path):
    p = unaliased(path)
    release = pinned_json(file_pin(p), private=True)
    require(release.get("schema") == "SH_ROOT_LOCAL_WORKSPACE_RELEASE_V1", "Local release required")
    core = {k: v for k, v in release.items() if k != "admission"}
    admission = pinned_json(release["admission"], private=True)
    require(
        admission.get("schema") == "SH_ROOT_LOCAL_WORKSPACE_RELEASE_ADMISSION_V1"
        and admission.get("local_lifecycle_authorized") is True
        and admission.get("release_core_sha256")
        == hashlib.sha256(canonical(core).encode()).hexdigest(),
        "Actual Root local release admission required",
    )
    require(
        set(release["modes"]) == {"CLEAN", "MESSY"} and release["ports"] == PORTS,
        "Exact delivered local pair required",
    )
    require(
        Path(sys.executable).resolve() == Path(release["python"]).resolve()
        and sys.version_info[:3] == (3, 12, 14)
        and sys.dont_write_bytecode
        and sys.flags.optimize == 0
        and not any(k in os.environ for k in ("PYTHONPATH", "PYTHONOPTIMIZE")),
        "Ordinary selected P0 Python -B environment required",
    )
    return release


def source_closure(release, *, loaded=False):
    repository = unaliased(release["repository"])
    files = pinned_json(release["source_map"])
    require(
        type(files) is dict and len(files) == release["source_module_count"],
        "Delivered complete Source map required",
    )
    for pin in files.values():
        read_pin(pin)
    for relative, sha in release["launcher_sources"].items():
        read_pin({"path": str(Path(__file__).resolve().parent / relative), "sha256": sha})
    dist = repository / "audit_suite_web/dist"
    actual = {str(p.relative_to(dist)) for p in dist.rglob("*") if p.is_file()}
    require(actual == set(release["frontend_assets"]), "Frontend namespace changed")
    for relative, sha in release["frontend_assets"].items():
        read_pin({"path": str(dist / relative), "sha256": sha})
    if loaded:
        for name, module in tuple(sys.modules.items()):
            path = getattr(module, "__file__", None)
            if name in files:
                require(
                    path == files[name]["path"]
                    and getattr(module.__spec__, "origin", None) == path,
                    "Loaded product Source origin differs",
                )
            elif path and Path(path).is_relative_to(repository):
                raise Refused("Undeclared product Source loaded")
    return files


@contextlib.contextmanager
def state_lock(state):
    path = state / "CONTROL.lock"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        value = os.fstat(fd)
        require(
            value.st_uid == os.getuid()
            and value.st_nlink == 1
            and (value.st_mode & 0o777) == 0o600,
            "Owned private control lock required",
        )
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def current(state):
    p = state / "CURRENT.json"
    return None if not p.exists() else pinned_json(file_pin(p), private=True)


def configuration_choice(release, state):
    p = state / "CONFIGURATIONS.json"
    if not p.exists():
        return {mode: release["modes"][mode]["reference_configuration"] for mode in PORTS}
    saved = pinned_json(file_pin(p), private=True)
    require(
        saved["release_id"] == release["release_id"], "Configuration belongs to another release"
    )
    handoff = pinned_json(saved["normal_handoff"], private=True)
    require(
        handoff["normal_serializers_used"] is True and same(handoff["modes"], saved["modes"]),
        "Complete normal stopped configuration handoff required",
    )
    return saved["modes"]


def serve(release, state, session):
    """Same normal constructors and same locked room objects used by the reviewed viewer."""
    from workspace_serving import RootStop, serve_and_drain

    source_closure(release)
    repository = unaliased(release["repository"])
    require(
        not any(n == "enterprise" or n.startswith("enterprise.") for n in sys.modules),
        "Fresh product import required",
    )
    sys.path[:0] = [str(repository), str(repository / "src")]
    from enterprise.audit_suite import persistent_company_service as service
    from enterprise.audit_suite import retained_explanation_service as explanation

    source_closure(release, loaded=True)
    choice = configuration_choice(release, state)
    rooms = {}
    apps = {}
    stop = RootStop()
    signal.signal(signal.SIGTERM, stop.request)
    signal.signal(signal.SIGINT, stop.request)
    with contextlib.ExitStack() as held:
        for mode in ("CLEAN", "MESSY"):
            value = release["modes"][mode]
            lock = unaliased(value["writer_lock"])
            before = metadata(lock)
            fd = os.open(lock, os.O_RDWR | os.O_NOFOLLOW)
            held.callback(os.close, fd)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            require(
                metadata(lock) == before
                and os.fstat(fd).st_ino == before[1]
                and os.fstat(fd).st_dev == before[0]
                and os.fstat(fd).st_uid == os.getuid(),
                "Existing owned room lock changed",
            )
            held.callback(
                lambda path=lock, before=before: require(
                    metadata(path) == before, "Closing room lock changed"
                )
            )
            reference = pinned_json(choice[mode])
            retained_pin = reference["retained_workroom"]
            retained = pinned_json(retained_pin)
            require(
                same(retained["history_integrity"], value["history_integrity"]),
                "Accepted base, ledger or explicit runtime admission changed",
            )
            require(retained["workroom_binding"] == value["binding"], "Born binding changed")
            require(same(reference["features"], release["features"]), "Selected features changed")
            room = service.RetainedWorkroom(
                retained_pin["path"],
                retained_pin["sha256"],
                private_root=value["private_root"],
                repository=repository,
                owned_writer_lock_fd=fd,
            )
            rooms[mode] = room
            apps[mode] = explanation.create_explained_app(
                room.root,
                choice[mode]["path"],
                choice[mode]["sha256"],
                repository=repository,
                retained_workroom=room,
                web_root=repository / "audit_suite_web/dist",
                workspace_contexts=True,
                secure_cookie=False,
                allowed_hosts=["localhost", "127.0.0.1", "[::1]"],
            )
            require(
                apps[mode].state.engine is room.engine,
                "Normal factory did not reuse genuine Engine",
            )
        require(
            rooms["CLEAN"].world.root == rooms["MESSY"].world.root,
            "Shared company lifetime differs",
        )
        source_closure(release, loaded=True)

        def ready(observations):
            publish_actual_ready(session, release, rooms, apps, choice, observations)

        asyncio.run(serve_and_drain(apps, stop, ready, release["frontend_assets"]["index.html"]))
        require(
            stop.signals and set(stop.signals) <= {"SIGTERM", "SIGINT"},
            "Serving ended without an explicit normal stop",
        )
        for room in rooms.values():
            operator = room.binding["identities"]["operator"]
            room.check_pins()
            room.refresh_integrity(operator)
            room.close_protected_read(operator, room.engine.store._retained_typed_stamp)
        source_closure(release, loaded=True)
        new = refresh_pair(rooms, choice, session / "NEXT_CONFIGURATION", service, explanation)
        source_closure(release, loaded=True)
        handoff_pin = file_pin(session / "NEXT_CONFIGURATION/HANDOFF.json")
        atomic_pointer(
            state / "CONFIGURATIONS.json",
            {"release_id": release["release_id"], "modes": new, "normal_handoff": handoff_pin},
        )
        write_once(
            session / "NORMAL_STOP.json",
            {
                "normal_drain_complete": True,
                "next_start_configuration_published": True,
                "signals": stop.signals,
                "configuration_handoff": handoff_pin,
            },
        )


def owner(release_path, release, state, session):
    """Detached lifetime parent owns actual Popen.wait and saves it before reporting."""
    argv = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--manifest",
        str(release_path),
        "_serve",
        "--session",
        str(session),
    ]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with (
        private_output(session / "worker.stdout") as stdout,
        private_output(session / "worker.stderr") as stderr,
    ):
        child = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, env=env
        )
        identity = process_identity(child.pid)
        identity_error = None
        try:
            require(identity is not None, "Child ended before identity capture")
            write_once(
                session / "CHILD.json", {"child": identity, "parent": process_identity(os.getpid())}
            )
        except Exception as error:
            identity_error = type(error).__name__
        finally:
            code = child.wait()
    normal = session / "NORMAL_STOP.json"
    write_once(
        session / "WAIT.json",
        {
            "actual_Popen_wait_returncode": code,
            "child": identity,
            "child_absent": process_identity(child.pid) is None,
            "normal_stop": file_pin(normal) if normal.exists() else None,
            "identity_capture_error_type": identity_error,
            "safe_for_requested_restart": identity_error is None
            and type(code) is int
            and code == 0
            and normal.exists(),
        },
    )
    return code


def saved_owner(session):
    child_file = session / "CHILD.json"
    if child_file.exists():
        value = pinned_json(file_pin(child_file), private=True)
        require(
            type(value.get("parent")) is dict,
            "Missing saved wait-owner identity; reconciliation required",
        )
        return value["parent"]
    saved = current(session.parent)
    require(
        type(saved) is dict
        and saved.get("session") == str(session)
        and type(saved.get("owner")) is dict,
        "Missing saved wait-owner identity; reconciliation required",
    )
    return saved["owner"]


def owner_alive_for_receipt(session, filename, owner_identity=None):
    identity = saved_owner(session) if owner_identity is None else owner_identity
    require(type(identity) is dict, "Missing saved wait-owner identity; reconciliation required")
    if not same(process_identity(identity["pid"]), identity):
        # The owner may have atomically published the receipt before it exited.
        require(
            (session / filename).exists(),
            "Wait owner ended without its receipt; reconciliation required",
        )


def wait_stopped(session):
    while not (session / "WAIT.json").exists():
        owner_alive_for_receipt(session, "WAIT.json")
        time.sleep(0.1)
    value = pinned_json(file_pin(session / "WAIT.json"), private=True)
    require(
        type(value["actual_Popen_wait_returncode"]) is int
        and value["actual_Popen_wait_returncode"] == 0
        and value["child_absent"] is True
        and value["safe_for_requested_restart"] is True,
        "Previous run requires operator reconciliation; no automatic restart",
    )
    stop = pinned_json(value["normal_stop"], private=True)
    require(
        stop["normal_drain_complete"] is True
        and stop["next_start_configuration_published"] is True,
        "Stopped configuration handoff incomplete",
    )
    return value


def wait_child_identity(session, owner_identity):
    require(type(owner_identity) is dict, "Missing saved parent identity; reconciliation required")
    while not (session / "CHILD.json").exists():
        require(
            process_identity(owner_identity["pid"]) is not None,
            "Parent ended without a saved child identity; reconciliation required",
        )
        require_same_process(owner_identity)
        time.sleep(0.1)
    return pinned_json(file_pin(session / "CHILD.json"), private=True)["child"]


def wait_ready(session, release_path):
    while not (session / "READY.json").exists():
        require(
            not (session / "WAIT.json").exists(),
            "Startup failed; inspect private status and reconcile",
        )
        owner_alive_for_receipt(session, "READY.json")
        time.sleep(0.1)
    value = pinned_json(file_pin(session / "READY.json"), private=True)
    require(
        value.get("schema") == "SH_ROOT_LOCAL_WORKSPACE_ACTUAL_READY_V1"
        and value.get("status") == "READY"
        and same(value["source_release"], file_pin(release_path)),
        "Current actual local Ready required",
    )
    child = pinned_json(file_pin(session / "CHILD.json"), private=True)
    require(
        same(value["process"], child["child"]) and same(value["owner_process"], child["parent"]),
        "Ready ownership differs",
    )
    require_same_process(child["child"])
    require_same_process(child["parent"])
    return value


def publish_actual_ready(session, release, rooms, apps, choice, observations):
    require(
        all(apps[mode].state.engine is rooms[mode].engine for mode in PORTS),
        "Ready must use the same genuine room Engines",
    )
    modes = {}
    configurations = {}
    for mode in ("CLEAN", "MESSY"):
        room = rooms[mode]
        managed = getattr(room.engine.store, "_managed_history_integrity", None)
        require(
            managed is not None and managed.room is room and managed.store is room.sealed_store,
            "Genuine selected managed runtime required for Ready coordinates",
        )
        with managed.locked():
            observed = managed.validate_current(
                room.binding["identities"]["operator"], room.engagement
            )
            frame = dict(managed.catalogue.frames[-1])
            require(
                type(observed["count"]) is int
                and observed["count"] == len(managed.catalogue.frames)
                and type(frame["revision"]) is int
                and frame["revision"] >= 0
                and frame["revision"] == observed["latest"]["revision"] == observed["count"] - 1
                and frame["engagement_id"] == room.engagement
                and frame["event_sha256"] == observed["latest"]["hash"]
                and type(frame["state_sha256"]) is str
                and len(frame["state_sha256"]) == 64
                and all(c in "0123456789abcdef" for c in frame["state_sha256"]),
                "Fresh managed catalogue Ready coordinates differ",
            )
        configurations[mode] = {
            "reference_configuration": choice[mode],
            "retained_configuration": {"path": str(room.path), "sha256": room.expected_sha256},
        }
        modes[mode] = {
            "engagement_id": room.engagement,
            "retained_root": str(room.root),
            "current_revision": frame["revision"],
            "current_state_sha256": frame["state_sha256"],
            "coordinate_origin": "GENUINE_MANAGED_CATALOGUE_AFTER_FRESH_VALIDATE_CURRENT",
        }
    source_closure(release, loaded=True)
    source_release = file_pin(release["_selected_release_path"])
    require(
        same(
            pinned_json(source_release, private=True),
            {k: v for k, v in release.items() if k != "_selected_release_path"},
        ),
        "Selected release changed before Ready",
    )
    ownership = session / "CHILD.json"
    return write_once(
        session / "READY.json",
        {
            "schema": "SH_ROOT_LOCAL_WORKSPACE_ACTUAL_READY_V1",
            "status": "READY",
            "urls": URLS,
            "process": process_identity(os.getpid()),
            "owner_process": process_identity(os.getppid()),
            "ownership_coordinates": {
                "actual_ppid": os.getppid(),
                "process_group": os.getpgrp(),
                "session_id": os.getsid(0),
            },
            "child_ownership": file_pin(ownership) if ownership.exists() else None,
            "source_release": source_release,
            "configurations": configurations,
            "modes": modes,
            "same_genuine_room_engines": True,
            "workers_per_server": 1,
            "reload": False,
            "observations": observations,
            "authenticated_or_UI_acceptance": False,
        },
    )


def start(release_path, release, state):
    with state_lock(state):
        old = current(state)
        if old:
            session = unaliased(old["session"])
            child_file = session / "CHILD.json"
            if child_file.exists():
                identities = pinned_json(file_pin(child_file), private=True)
                if process_identity(identities["child"]["pid"]) is not None:
                    require_same_process(identities["child"])
                    return session
            if (
                not child_file.exists()
                and type(old.get("owner")) is dict
                and process_identity(old["owner"]["pid"]) is not None
            ):
                wait_child_identity(session, old["owner"])
                return session
            require(
                child_file.exists() or (session / "WAIT.json").exists(),
                "Parent ended without a saved wait or child identity; reconciliation required",
            )
            wait_stopped(session)
        source_closure(release)
        session = state / ("SESSION-" + uuid.uuid4().hex)
        session.mkdir(mode=0o700)
        argv = [
            sys.executable,
            "-B",
            str(Path(__file__).resolve()),
            "--manifest",
            str(release_path),
            "_owner",
            "--session",
            str(session),
        ]
        with (
            private_output(session / "parent.stdout") as stdout,
            private_output(session / "parent.stderr") as stderr,
        ):
            parent = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                env=dict(os.environ),
            )
        atomic_pointer(
            state / "CURRENT.json",
            {
                "session": str(session),
                "release_id": release["release_id"],
                "owner": process_identity(parent.pid),
            },
        )
        return session


def stop_once(state):
    with state_lock(state):
        saved = current(state)
        require(saved is not None, "Workspace has no saved local run")
        session = unaliased(saved["session"])
        if (session / "WAIT.json").exists():
            return session
        child = wait_child_identity(session, saved["owner"])
        if process_identity(child["pid"]) is None:
            return session  # Actual wait owner may be publishing the completed wait now.
        require_same_process(child)
        attempt = session / "STOP_ATTEMPT.json"
        if not attempt.exists():
            pidfd = os.pidfd_open(child["pid"])
            try:
                require_same_process(child)
                write_once(attempt, {"child": child, "signal": "SIGTERM", "automatic_retry": False})
                signal.pidfd_send_signal(pidfd, signal.SIGTERM, None, 0)
                write_once(
                    session / "STOP_SENT.json", {"signal_call_returned": True, "child": child}
                )
            finally:
                os.close(pidfd)
        elif not (session / "STOP_SENT.json").exists():
            raise Refused("Prior signal return unconfirmed; no automatic signal retry")
        return session


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "command", choices=("start", "status", "stop", "restart", "_owner", "_serve")
    )
    parser.add_argument("--session")
    args = parser.parse_args()
    release_path = unaliased(args.manifest)
    release = load_release(release_path)
    release["_selected_release_path"] = str(release_path)
    state = secure_directory(release["state_root"], create=True)
    if args.command in ("_owner", "_serve"):
        session = secure_directory(args.session)
        require(session.parent == state, "Private owned run directory required")
        if args.command == "_owner":
            return owner(release_path, release, state, session)
        serve(release, state, session)
        return 0
    if args.command in ("stop", "restart"):
        if current(state) is not None:
            session = stop_once(state)
            wait_stopped(session)
        if args.command == "stop":
            print(json.dumps({"status": "STOPPED"}))
            return 0
    if args.command in ("start", "restart"):
        session = start(release_path, release, state)
        require(
            not (session / "STOP_ATTEMPT.json").exists(),
            "Current run is stopping; wait for normal stop",
        )
        wait_ready(session, release_path)
        print(json.dumps({"status": "READY", "urls": URLS}))
        return 0
    saved = current(state)
    if saved is None:
        status = "STOPPED"
    else:
        session = Path(saved["session"])
        if (session / "WAIT.json").exists():
            settled = pinned_json(file_pin(session / "WAIT.json"), private=True)
            status = (
                "STOPPED"
                if settled["safe_for_requested_restart"] is True
                else "RECONCILIATION_REQUIRED"
            )
        elif (session / "STOP_ATTEMPT.json").exists():
            status = "STOPPING"
        else:
            owner_alive = type(saved.get("owner")) is dict and same(
                process_identity(saved["owner"]["pid"]), saved["owner"]
            )
            child_file = session / "CHILD.json"
            child_alive = False
            if child_file.exists():
                identity = pinned_json(file_pin(child_file), private=True)["child"]
                child_alive = same(process_identity(identity["pid"]), identity)
            status = (
                ("READY" if (session / "READY.json").exists() else "STARTING")
                if child_alive
                else (
                    "STARTING"
                    if owner_alive and not child_file.exists()
                    else "RECONCILIATION_REQUIRED"
                )
            )
    print(json.dumps({"status": status, "urls": URLS if status == "READY" else {}}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        # Only a type/code is retained; payload/header/credential-bearing messages are not logged.
        print(
            json.dumps({"status": "REFUSED", "error_type": type(error).__name__}), file=sys.stderr
        )
        raise SystemExit(1) from error
