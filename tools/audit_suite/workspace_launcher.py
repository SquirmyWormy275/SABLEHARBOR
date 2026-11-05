"""Set up and run CLEAN and MESSY audit workrooms from an ordinary checkout.

The private workstation pair described in ``docs/audit-suite/LOCAL_WORKSPACE.md``
is started by a separately installed launcher and is not part of a clone. This
launcher builds an equivalent local pair from public repository inputs only:

* CLEAN reads company history 01 (branch ``HARBOR-OPERATIONS-A``) and MESSY reads
  company history 02 (branch ``HARBOR-OPERATIONS-B``) from
  ``docs/audit-suite/company-records``. Each history is verified, then imported
  with its native company, branch, system, record, version, owner, business-event
  time, availability time and provenance into its own private company store.
* Each mode gets its own private engagement history, its own ``operator``
  (instructor), ``auditor`` (learner) and ``reviewer`` credentials, and one
  engagement bound to its company branch and activated for company-source
  collection. Credentials are written to private mode-0600 files, never printed.
* ``start`` runs one unmodified ``python -m enterprise.audit_suite serve`` process
  per mode on loopback ports 8782 (CLEAN) and 8783 (MESSY).

Run ``python -m tools.audit_suite.workspace_launcher --help`` from the repository
root. The default private root is the Git-ignored ``var/audit-workspace``.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
RECORDS = REPOSITORY / "docs/audit-suite/company-records"
WEB_ROOT = REPOSITORY / "audit_suite_web/dist"
DEFAULT_ROOT = REPOSITORY / "var/audit-workspace"
MODES = {
    "CLEAN": {"port": 8782, "history": "history-01"},
    "MESSY": {"port": 8783, "history": "history-02"},
}
ROLES = {
    # Documented role name -> service role and engagement permission.
    "operator": ("instructor", "instruct"),
    "auditor": ("learner", "learn"),
    "reviewer": ("reviewer", "review"),
}
SCOPE = {
    "programs": ["SOC2"],
    "report_type": "Type 2",
    "period_start": "2027-01-01",
    "period_end": "2027-12-31",
    "fieldwork_start": "2028-01-01",
    "timezone": "UTC",
    "reporting_basis": "",
    "accounts": [],
    "materiality_rationale": "",
}


class LauncherError(RuntimeError):
    """A refused launcher operation with an operator-facing explanation."""


def private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise LauncherError(f"{path} must be a real directory")
    if path.stat().st_mode & 0o077:
        path.chmod(0o700)
    return path


def write_private_json(path: Path, value) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.unlink(missing_ok=True)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
    os.replace(temporary, path)


def mode_paths(root: Path, mode: str) -> dict[str, Path]:
    base = root / mode.lower()
    return {
        "base": base,
        "state": base / "state",
        "company": base / "company",
        "config": base / "config",
        "bindings": base / "config/company-bindings.json",
        "workspace": base / "config/workspace.json",
    }


def history_records(history: str) -> tuple[list[dict], list[dict], dict[tuple, dict]]:
    manifest = json.loads((RECORDS / "manifest.json").read_text())
    records = [r for r in manifest["records"] if r["history_id"] == history]
    branches = {r["branch"] for r in records}
    systems = [s for s in manifest["systems"] if s["branch"] in branches]
    provenance = {}
    with (RECORDS / history / "provenance.jsonl").open() as stream:
        for line in stream:
            value = json.loads(line)
            key = tuple(value[k] for k in ("company", "branch", "system", "record", "version"))
            provenance[key] = value
    return records, systems, provenance


def verify_records() -> None:
    from tools.audit_suite.company_record_delivery import verify

    try:
        verify(RECORDS)
    except Exception as error:
        raise LauncherError(f"Company record delivery did not verify: {error}") from error


def progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def import_history(company_store, history: str) -> tuple[str, str, list[str]]:
    import hashlib

    records, systems, provenance = history_records(history)
    for system in systems:
        company_store.register_system(
            system["company"], system["branch"], system["system"], system["owner"]
        )
    records.sort(key=lambda r: (r["system"], r["record"], r["version"]))
    for number, record in enumerate(records, 1):
        content = (RECORDS / record["path"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != record["sha256"]:
            raise LauncherError(f"Delivered bytes differ for {record['path']}")
        key = tuple(record[k] for k in ("company", "branch", "system", "record", "version"))
        source = provenance[key]
        company_store.append_version(
            record["company"],
            record["branch"],
            record["system"],
            record["record"],
            expected_version=record["version"] - 1,
            command_id=source["command_id"],
            event_at=record["event_at"],
            available_at=record["available_at"],
            content=content,
            provenance=source["provenance"],
            origin=record["origin"],
        )
        if number % 500 == 0 or number == len(records):
            progress(f"  {history}: imported {number}/{len(records)} source versions")
    (company,) = {s["company"] for s in systems}
    (branch,) = {s["branch"] for s in systems}
    return company, branch, sorted(s["system"] for s in systems)


def issue_principals(engine, root, mode, lifetime, engagement=None, systems=(), bound=None):
    """Provision the three documented roles and write their private credential files."""
    credentials = private_directory(root / "credentials")
    principals = {}
    for name, (role, permission) in ROLES.items():
        value = engine.store.provision(f"{mode.title()} {name}", [role], lifetime=lifetime)
        principals[name] = value
        if engagement is not None:
            grant_access(engine, engagement, value["id"], permission, systems, bound)
        write_private_json(credentials / f"{mode.lower()}-{name}.json", value)
    return principals


def grant_access(engine, engagement, principal, permission, systems, bound) -> None:
    engine.store.grant(engagement, principal, permission)
    for system in systems:
        engine.company_store.grant(principal, engagement, bound["company"], bound["branch"], system)


def setup_mode(root: Path, mode: str, lifetime_hours: int) -> dict:
    from enterprise.audit_suite.engine import Engine

    paths = mode_paths(root, mode)
    if paths["base"].exists():
        raise LauncherError(f"{paths['base']} already exists; choose a new --root")
    for name in ("base", "state", "company", "config"):
        private_directory(paths[name])
    progress(f"{mode}: importing company {MODES[mode]['history']} (this takes a few minutes)")
    engine = Engine(paths["state"], company_root=paths["company"])
    company, branch, systems = import_history(engine.company_store, MODES[mode]["history"])
    bound = {"company": company, "branch": branch}
    principals = issue_principals(engine, root, mode, lifetime_hours * 3600)
    operator = principals["operator"]["id"]
    boundaries = [
        b["id"]
        for b in engine.setup_boundaries
        if any(
            word in (b["id"] + " " + str(b.get("title", ""))).lower()
            for word in ("corporate", "reno", "boise")
        )
    ]
    state = engine.create(
        operator,
        {
            "command_id": f"workspace-{mode.lower()}",
            "title": f"Sable Harbor {mode} company-source engagement",
            "discipline": "IT",
            "mode": mode,
            "scope": {**SCOPE, "boundaries": boundaries},
            "configuration": {"selections": []},
        },
    )
    engagement = state["id"]
    for name, (_, permission) in ROLES.items():
        grant_access(engine, engagement, principals[name]["id"], permission, systems, bound)
    write_private_json(paths["bindings"], {engagement: bound})
    engine.company_bindings = {engagement: bound}
    state = engine.command(
        operator,
        engagement,
        {
            "command_id": f"workspace-{mode.lower()}-activate",
            "expected_revision": state["revision"],
            "kind": "company.activate",
            "payload": {},
        },
    )
    summary = {
        "mode": mode,
        "engagement_id": engagement,
        **bound,
        "history": MODES[mode]["history"],
        "systems": len(systems),
        "port": MODES[mode]["port"],
        "phase": state["phase"],
        "principals": {name: value["id"] for name, value in principals.items()},
    }
    write_private_json(paths["workspace"], summary)
    progress(f"{mode}: engagement {engagement} activated on {branch}")
    return summary


def reissue_credentials(root: Path, lifetime_hours: int) -> dict:
    """Revoke the previous role principals and issue new ones with the same grants."""
    from enterprise.audit_suite.engine import Engine

    issued = {}
    for mode in MODES:
        paths = mode_paths(root, mode)
        if not paths["workspace"].exists():
            raise LauncherError(f"Run setup first; {paths['workspace']} is missing")
        summary = json.loads(paths["workspace"].read_text())
        engine = Engine(paths["state"], company_root=paths["company"])
        systems = [s["system"] for s in history_records(summary["history"])[1]]
        bound = {"company": summary["company"], "branch": summary["branch"]}
        for principal in summary["principals"].values():
            engine.store.revoke(principal)
        principals = issue_principals(
            engine, root, mode, lifetime_hours * 3600, summary["engagement_id"], systems, bound
        )
        summary["principals"] = {name: value["id"] for name, value in principals.items()}
        write_private_json(paths["workspace"], summary)
        issued[mode] = sorted(principals)
    return issued


def process_start_time(pid: int) -> str | None:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return None
    return stat.rsplit(")", 1)[1].split()[19]


def run_file(root: Path, mode: str) -> Path:
    return root / "run" / f"{mode.lower()}.json"


def running(root: Path, mode: str) -> dict | None:
    path = run_file(root, mode)
    if not path.exists():
        return None
    value = json.loads(path.read_text())
    if process_start_time(value["pid"]) != value["start_time"]:
        return None
    return value


def responds(port: int) -> bool:
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/bootstrap", timeout=2)
    except urllib.error.HTTPError as error:
        return error.code == 401
    except OSError:
        return False
    return True


def start(root: Path, timeout: float) -> dict:
    if not (WEB_ROOT / "index.html").is_file():
        raise LauncherError(
            "Build the browser workroom first: cd audit_suite_web && npm ci && npm run build"
        )
    run = private_directory(root / "run")
    logs = private_directory(root / "logs")
    for mode, value in MODES.items():
        paths = mode_paths(root, mode)
        if not paths["workspace"].exists():
            raise LauncherError(f"Run setup first; {paths['workspace']} is missing")
        if running(root, mode):
            continue
        if responds(value["port"]):
            raise LauncherError(f"Port {value['port']} is already serving another process")
        argv = [
            sys.executable,
            "-m",
            "enterprise.audit_suite",
            "serve",
            "--private-root",
            str(paths["state"]),
            "--company-root",
            str(paths["company"]),
            "--company-bindings",
            str(paths["bindings"]),
            "--web-root",
            str(WEB_ROOT),
            "--local-http",
            "--port",
            str(value["port"]),
        ]
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(REPOSITORY), str(REPOSITORY / "src")]
            + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
        )
        log = open(logs / f"{mode.lower()}.log", "ab")
        with log:
            child = subprocess.Popen(
                argv,
                cwd=REPOSITORY,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
        write_private_json(
            run / f"{mode.lower()}.json",
            {"pid": child.pid, "start_time": process_start_time(child.pid), "port": value["port"]},
        )
    deadline = time.monotonic() + timeout
    pending = set(MODES)
    while pending and time.monotonic() < deadline:
        for mode in list(pending):
            if not running(root, mode):
                raise LauncherError(f"{mode} server exited; see {logs / (mode.lower() + '.log')}")
            if responds(MODES[mode]["port"]):
                pending.discard(mode)
        time.sleep(0.25)
    if pending:
        raise LauncherError(f"Timed out waiting for {', '.join(sorted(pending))}")
    return status(root)


def stop(root: Path, timeout: float) -> dict:
    for mode in MODES:
        value = running(root, mode)
        if value:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(value["pid"], signal.SIGTERM)
            deadline = time.monotonic() + timeout
            while running(root, mode) and time.monotonic() < deadline:
                time.sleep(0.1)
            if running(root, mode):
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(value["pid"], signal.SIGKILL)
        run_file(root, mode).unlink(missing_ok=True)
    return {"status": "STOPPED"}


def status(root: Path) -> dict:
    modes = {}
    for mode, value in MODES.items():
        paths = mode_paths(root, mode)
        if not paths["workspace"].exists():
            modes[mode] = {"status": "NOT_SET_UP"}
            continue
        summary = json.loads(paths["workspace"].read_text())
        alive = running(root, mode) is not None
        ready = alive and responds(value["port"])
        modes[mode] = {
            "status": "READY" if ready else ("STARTING" if alive else "STOPPED"),
            "url": f"http://127.0.0.1:{value['port']}",
            "engagement_id": summary["engagement_id"],
            "branch": summary["branch"],
        }
    states = {m["status"] for m in modes.values()}
    overall = states.pop() if len(states) == 1 else "PARTIAL"
    return {
        "status": overall,
        "root": str(root),
        "credentials": str(root / "credentials"),
        "modes": modes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.audit_suite.workspace_launcher", description=__doc__.split("\n")[0]
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(os.environ.get("SABLEHARBOR_WORKSPACE_ROOT", DEFAULT_ROOT)),
        help="private workspace directory (default: var/audit-workspace)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("setup", help="import company records and provision roles")
    setup.add_argument("--lifetime-hours", type=int, default=24 * 30)
    reissue = commands.add_parser("credentials", help="issue fresh role credential files")
    reissue.add_argument("--lifetime-hours", type=int, default=24 * 30)
    for name in ("start", "restart", "stop"):
        command = commands.add_parser(name)
        command.add_argument("--timeout", type=float, default=120.0)
    commands.add_parser("status")
    args = parser.parse_args(argv)
    root = args.root.absolute()
    try:
        if args.command == "setup":
            if not 1 <= args.lifetime_hours <= 24 * 30:
                raise LauncherError("--lifetime-hours must be between 1 and 720")
            private_directory(root)
            verify_records()
            result = {
                "status": "SET_UP",
                "root": str(root),
                "credentials": str(root / "credentials"),
                "modes": {mode: setup_mode(root, mode, args.lifetime_hours) for mode in MODES},
            }
        elif args.command == "credentials":
            if not 1 <= args.lifetime_hours <= 24 * 30:
                raise LauncherError("--lifetime-hours must be between 1 and 720")
            result = {
                "status": "ISSUED",
                "credentials": str(root / "credentials"),
                "modes": reissue_credentials(root, args.lifetime_hours),
            }
        elif args.command == "start":
            result = start(root, args.timeout)
        elif args.command == "restart":
            stop(root, args.timeout)
            result = start(root, args.timeout)
        elif args.command == "stop":
            result = stop(root, args.timeout)
        else:
            result = status(root)
    except Exception as error:
        message = {"status": "REFUSED", "error_type": type(error).__name__, "error": str(error)}
        if args.command == "setup":
            message["next_step"] = f"Remove the incomplete {root} or choose another --root"
        print(json.dumps(message), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
