"""Trusted local read-only source reconciliation; no audit commands or model calls."""

import argparse
import json
import os
import sqlite3
import stat
from pathlib import Path
from types import SimpleNamespace

from enterprise.audit_suite.artifacts import Artifacts
from enterprise.audit_suite.company_federation import FederatedCompanyStore
from enterprise.audit_suite.inference import _json
from enterprise.audit_suite.service import load_company_bindings
from enterprise.audit_suite.source_dependency_reconciliation import write_report
from enterprise.audit_suite.store import DomainError, Store

LIMIT = 512 * 1024
FIELDS = {
    "audit_root",
    "actor_id",
    "engagement_id",
    "company_registry",
    "company_profile",
    "company_bindings",
    "plan",
}


def private_path(value, *, directory=False):
    if not isinstance(value, str):
        raise DomainError("Explicit absolute private path required")
    path = Path(value)
    if (
        not path.is_absolute()
        or ".." in path.parts
        or any(p.is_symlink() for p in (path, *path.parents))
    ):
        raise DomainError("Canonical private path required")
    info = path.stat()
    valid = (
        stat.S_ISDIR(info.st_mode)
        if directory
        else (stat.S_ISREG(info.st_mode) and info.st_nlink == 1)
    )
    if not valid or info.st_mode & 0o077:
        raise DomainError("Existing private regular input required")
    return path


def read_json(value):
    path = private_path(str(value))
    private_path(str(path.parent), directory=True)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
            raise DomainError("Private regular JSON input required")
        raw = stream.read(LIMIT + 1)
        final = os.fstat(stream.fileno())
    current = private_path(str(path)).stat()
    private_path(str(path.parent), directory=True)

    def stamp(item):
        return item.st_dev, item.st_ino, item.st_ctime_ns, item.st_size

    if stamp(info) != stamp(final) or stamp(info) != stamp(current):
        raise DomainError("Reconciliation JSON changed during read")
    if len(raw) > LIMIT:
        raise DomainError("Bounded reconciliation JSON required")
    try:
        result = _json(raw)
    except (ValueError, RecursionError) as error:
        raise DomainError("Strict finite reconciliation JSON required") from error
    if not isinstance(result, dict):
        raise DomainError("Reconciliation JSON object required")
    return result


class ReadOnlyStore(Store):
    def __init__(self, root):
        self.root = private_path(str(root), directory=True)
        self.db_path = private_path(str(self.root / "engagements.sqlite3"))

    def connect(self):
        private_path(str(self.root), directory=True)
        private_path(str(self.db_path))
        db = sqlite3.connect(self.db_path.as_uri() + "?mode=ro", uri=True, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        return db


class ReadOnlyArtifacts:
    def __init__(self, root):
        self.root = Path(root) / "artifacts"

    def read(self, manifest):
        pin = manifest.get("sha256")
        if (
            not isinstance(pin, str)
            or len(pin) != 64
            or any(c not in "0123456789abcdef" for c in pin)
        ):
            raise DomainError("Exact retained artifact SHA required")
        private_path(str(self.root), directory=True)
        private_path(str(self.root / pin))
        return Artifacts.read(self, manifest)


def run(config_path, output):
    config = read_json(config_path)
    if set(config) != FIELDS or any(not isinstance(v, str) or not v for v in config.values()):
        raise DomainError("Exact explicit reconciliation configuration required")
    root = private_path(config["audit_root"], directory=True)
    private_path(str(root / "engagements.sqlite3"))
    registry = private_path(config["company_registry"])
    bindings = private_path(config["company_bindings"])
    plan = read_json(config["plan"])
    engine = SimpleNamespace(
        store=ReadOnlyStore(root),
        artifacts=ReadOnlyArtifacts(root),
        company_store=FederatedCompanyStore(registry, config["company_profile"]),
        company_bindings=load_company_bindings(bindings),
    )
    return write_report(
        engine,
        config["actor_id"],
        config["engagement_id"],
        plan,
        output=output,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.config, args.output)
    print(json.dumps({"status": "REPORT_WRITTEN", **result}))


if __name__ == "__main__":
    main()
