"""Trusted local operating-period ledger; creates no audit or operating results."""

import argparse
import json
import os
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

from enterprise.audit_suite.company_operating_period import (
    create_period,
    record_occurrence,
    report_period,
)
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.private_publication import publish
from enterprise.audit_suite.store import DomainError
from tools.audit_suite.reconcile_source_dependencies import private_path, read_json

ACTION_FIELDS = {
    "period_id",
    "occurrence_id",
    "expected_version",
    "command_id",
    "recorded_at",
    "disposition",
    "sources",
    "reason",
    "predecessor_refs",
}
REPORT_MODULES = (
    "tools/audit_suite/company_operating_period.py",
    "tools/audit_suite/reconcile_source_dependencies.py",
    "enterprise/audit_suite/company_operating_period.py",
    "enterprise/audit_suite/company_store.py",
    "enterprise/audit_suite/inference.py",
    "enterprise/audit_suite/operating_source_bridge.py",
    "enterprise/audit_suite/private_publication.py",
)


def report_code_pins():
    repository = Path(__file__).resolve().parents[2]
    return {relative: sha((repository / relative).read_bytes()) for relative in REPORT_MODULES}


def new_destination(value):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise DomainError("Absolute new private destination required")
    private_path(str(path.parent), directory=True)
    if path.exists() or path.is_symlink():
        raise DomainError("New destination required; existing history is preserved")
    return path


class ReadOnlyCompanyStore(CompanyStore):
    """Read the maintained schema without constructor DDL or journal writes."""

    def __init__(self, root):
        root = private_path(str(root), directory=True)
        self.path = private_path(str(root / "company.sqlite3"))

    @contextmanager
    def _db(self):
        private_path(str(self.path.parent), directory=True)
        private_path(str(self.path))
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            yield db
        finally:
            db.close()


def create(plan_path, destination, repository):
    plan = read_json(plan_path)
    destination = new_destination(destination)
    stage = Path(tempfile.mkdtemp(prefix=".operating-period-", dir=destination.parent))
    try:
        result = create_period(CompanyStore(stage), repository=Path(repository), plan=plan)
        publish(stage, destination)
        return result
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def record(root, action_path):
    action = read_json(action_path)
    if set(action) != ACTION_FIELDS:
        raise DomainError("Exact operating-period action fields required")
    root = private_path(str(root), directory=True)
    private_path(str(root / "company.sqlite3"))
    return record_occurrence(CompanyStore(root), **action)


def report(root, period_id, as_of, destination):
    root = private_path(str(root), directory=True)
    destination = new_destination(destination)
    if destination == root or destination.is_relative_to(root):
        raise DomainError("Report output must be outside the company source store")
    pins = report_code_pins()
    result = report_period(ReadOnlyCompanyStore(root), period_id=period_id, as_of=as_of)
    stage = Path(tempfile.mkdtemp(prefix=".operating-period-report-", dir=destination.parent))
    try:
        raw = encoded(result)
        manifest = {
            "format": "COMPANY_OPERATING_PERIOD_REPORT_V1",
            "files": {"REPORT.json": sha(raw)},
            "analysis_modules_sha256": pins,
            "pin_scope": "MAINTAINED_FILES_NOT_LOADED_BINARY_ATTESTATION",
            "audit_created": False,
            "operation_executed_by_report": False,
        }
        for name, content in [("REPORT.json", raw), ("MANIFEST.json", encoded(manifest))]:
            fd = os.open(stage / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
        if pins != report_code_pins():
            raise DomainError("Report source code changed before publication")
        publish(stage, destination)
        return manifest
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create_args = sub.add_parser("create")
    create_args.add_argument("--plan", type=Path, required=True)
    create_args.add_argument("--destination", type=Path, required=True)
    create_args.add_argument("--repository", type=Path, required=True)
    record_args = sub.add_parser("record")
    record_args.add_argument("--store", type=Path, required=True)
    record_args.add_argument("--action", type=Path, required=True)
    report_args = sub.add_parser("report")
    report_args.add_argument("--store", type=Path, required=True)
    report_args.add_argument("--period-id", required=True)
    report_args.add_argument("--as-of", required=True)
    report_args.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "create":
        create(args.plan, args.destination, args.repository)
    elif args.command == "record":
        record(args.store, args.action)
    else:
        report(args.store, args.period_id, args.as_of, args.destination)
    print(json.dumps({"status": "COMPLETE", "action": args.command, "audit_created": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
