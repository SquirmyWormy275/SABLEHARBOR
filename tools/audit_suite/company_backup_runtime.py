"""Trusted local backup operations and private receipts; no network or audit activation."""

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.store import DomainError
from tools.audit_suite.company_operating_period import new_destination
from tools.audit_suite.reconcile_source_dependencies import read_json

BASE = {"expected_runtime_sha256", "expected_revision", "command_id"}
FIELDS = {
    "DATASET": ({"dataset_id", "content_path", "expected_sha256", "event_at"}, {"previous_pin"}),
    "LEASE": (
        {"operation", "enabled", "valid_from", "expires_at", "event_at"},
        {"previous_pin"},
    ),
    "BACKUP": (
        {"occurrence_id", "source_pin", "lease_pin", "attempted_at", "rationale"},
        {"prior_attempt_pin"},
    ),
    "RESTORE": (
        {
            "occurrence_id",
            "backup_pin",
            "comparison_source_pin",
            "lease_pin",
            "attempted_at",
            "rationale",
        },
        {"prior_attempt_pin"},
    ),
}


def output_destination(value, runtime):
    output = new_destination(value)
    root = Path(runtime)
    if output == root or output.is_relative_to(root):
        raise DomainError("Operator receipt must be outside the company runtime")
    return output


def parent_identity(output):
    parent = backup.private(output.parent, True)
    info = parent.stat()
    return info.st_dev, info.st_ino


def publish_receipt(output, request, result, expected_parent):
    """Operation receipts also remain in the runtime if this publication fails."""
    if parent_identity(output) != expected_parent:
        raise DomainError("Receipt parent changed during operation; use exact replay")
    parent_fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    stage = None
    try:
        info = os.fstat(parent_fd)
        if (info.st_dev, info.st_ino) != expected_parent or info.st_mode & 0o077:
            raise DomainError("Receipt parent changed before publication; use exact replay")
        # Anchor all staging, moving and cleanup to the verified open directory.
        # /proc/self/fd is the Linux runtime's descriptor view, never an input alias.
        anchored_parent = Path("/proc/self/fd") / str(parent_fd)
        stage = Path(tempfile.mkdtemp(prefix=".backup-operator-receipt-", dir=anchored_parent))
        files = {"REQUEST.json": encoded(request), "RESULT.json": encoded(result)}
        files["MANIFEST.json"] = encoded(
            {
                "format": "COMPANY_BACKUP_OPERATOR_RECEIPT_V1",
                "files": {name: sha(raw) for name, raw in files.items()},
                "audit_created": False,
                "professional_acceptance": "NOT_PERFORMED",
            }
        )
        for name, raw in files.items():
            fd = os.open(stage / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
        if parent_identity(output) != expected_parent:
            raise DomainError("Receipt parent changed before publication; use exact replay")
        # Reserve a new receipt; the generic path publisher cannot fsync the
        # descriptor-view parent with O_NOFOLLOW. Keep the parent fd authoritative.
        os.mkdir(output.name, mode=0o700, dir_fd=parent_fd)
        target = anchored_parent / output.name
        moved = []
        try:
            for name in files:
                with (stage / name).open("rb") as stream:
                    os.fsync(stream.fileno())
                os.rename(stage / name, target / name)
                moved.append(name)
            target_fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(target_fd)
            finally:
                os.close(target_fd)
            os.fsync(parent_fd)
            if parent_identity(output) != expected_parent:
                raise DomainError("Receipt parent changed during publication; use exact replay")
        except BaseException:
            for name in reversed(moved):
                os.rename(target / name, stage / name)
            os.rmdir(output.name, dir_fd=parent_fd)
            raise
    finally:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        os.close(parent_fd)


def initialize(config_path, destination, repository, output):
    config = read_json(config_path)
    if set(config) != {"declaration_root", "declaration_ref", "bindings", "datasets", "service_id"}:
        raise DomainError("Exact backup initialization configuration required")
    destination = new_destination(destination)
    output = output_destination(output, destination)
    output = output_destination(output, backup.private(config["declaration_root"], True))
    expected_parent = parent_identity(output)
    result = backup.initialize(destination, repository=Path(repository), **config)
    try:
        publish_receipt(
            output, {"kind": "INITIALIZE", "configuration": config}, result, expected_parent
        )
    except Exception as exc:
        raise DomainError(
            "RUNTIME_CREATED_RECEIPT_NOT_PUBLISHED: preserve the initialized runtime; "
            "inspect its RUNTIME.json and reconcile with its exact configuration SHA256. "
            "Do not initialize over it."
        ) from exc
    return result


def operate(runtime, action_path, output):
    runtime = backup.private(runtime, True)
    output = output_destination(output, runtime)
    expected_parent = parent_identity(output)
    action = read_json(action_path)
    if (
        set(action) != {"kind", "parameters"}
        or not isinstance(action["kind"], str)
        or action["kind"] not in FIELDS
        or not isinstance(action["parameters"], dict)
    ):
        raise DomainError("Exact supported backup action required")
    kind, parameters = action["kind"], dict(action["parameters"])
    required, optional = FIELDS[kind]
    required_keys = BASE | required
    if not required_keys <= parameters.keys() or not parameters.keys() <= required_keys | optional:
        raise DomainError("Exact backup operation parameters required")
    if kind == "DATASET":
        parameters["content"] = backup.checked_bytes(parameters.pop("content_path"))
    method = {
        "DATASET": backup.append_dataset,
        "LEASE": backup.record_lease,
        "BACKUP": backup.run_backup,
        "RESTORE": backup.run_restore,
    }[kind]
    result = method(runtime, **parameters)
    try:
        publish_receipt(output, action, result, expected_parent)
    except Exception as exc:
        raise DomainError(
            "OPERATION_COMMITTED_RECEIPT_NOT_PUBLISHED: preserve runtime and action; "
            "replay the exact action with a new private receipt output."
        ) from exc
    return result


def reconcile(runtime, expected_runtime_sha256, as_of, output):
    runtime = backup.private(runtime, True)
    output = output_destination(output, runtime)
    expected_parent = parent_identity(output)
    result = backup.reconcile(runtime, expected_runtime_sha256=expected_runtime_sha256, as_of=as_of)
    publish_receipt(
        output,
        {
            "kind": "RECONCILE",
            "expected_runtime_sha256": expected_runtime_sha256,
            "as_of": as_of,
        },
        result,
        expected_parent,
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("initialize")
    init.add_argument("--config", type=Path, required=True)
    init.add_argument("--destination", type=Path, required=True)
    init.add_argument("--repository", type=Path, required=True)
    operation = commands.add_parser("operate")
    operation.add_argument("--runtime", type=Path, required=True)
    operation.add_argument("--action", type=Path, required=True)
    report = commands.add_parser("reconcile")
    report.add_argument("--runtime", type=Path, required=True)
    report.add_argument("--runtime-sha256", required=True)
    report.add_argument("--as-of", required=True)
    for sub in [init, operation, report]:
        sub.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "initialize":
        result = initialize(args.config, args.destination, args.repository, args.output)
    elif args.command == "operate":
        result = operate(args.runtime, args.action, args.output)
    else:
        result = reconcile(args.runtime, args.runtime_sha256, args.as_of, args.output)
    print(
        json.dumps(
            {
                "status": "RECEIPT_WRITTEN",
                "action": args.command,
                "result_status": result.get("status"),
                "audit_created": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
