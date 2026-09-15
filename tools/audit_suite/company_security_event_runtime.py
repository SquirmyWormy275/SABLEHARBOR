"""Trusted local security-event workflow operator; no network, audit or model activation."""

import argparse
from pathlib import Path

from enterprise.audit_suite import company_security_event_runtime as runtime
from enterprise.audit_suite.company_backup_runtime import private
from enterprise.audit_suite.store import DomainError
from tools.audit_suite.company_backup_runtime import (
    output_destination,
    parent_identity,
)
from tools.audit_suite.company_backup_runtime import (
    publish_receipt as _publish_receipt,
)
from tools.audit_suite.company_operating_period import new_destination
from tools.audit_suite.reconcile_source_dependencies import read_json

ROOT = Path(__file__).resolve().parents[2]
INITIAL = {
    "source_root",
    "source_pins",
    "expected_source_metadata_sha256",
    "as_of",
    "runtime_id",
    "period_start",
    "period_end",
    "local_rules",
}
COMMAND = {
    "expected_runtime_sha256",
    "expected_revision",
    "expected_state_sha256",
    "command_id",
    "operator_id",
    "event_at",
    "payload",
}
ACTIONS = {"INTAKE", "TRIAGE", "HANDOFF", "RECORD_ACTION", "RECONCILE"}


def publish_receipt(output, request, result, parent):
    return _publish_receipt(
        output,
        request,
        result,
        parent,
        receipt_format="COMPANY_SECURITY_EVENT_OPERATOR_RECEIPT_V1",
    )


def initialize(config_path, destination, output, repository=ROOT):
    config = read_json(config_path)
    if set(config) != INITIAL:
        raise DomainError("Exact local security-event initialization fields required")
    destination = new_destination(destination)
    output = output_destination(output, destination)
    output = output_destination(output, private(Path(config["source_root"]), True))
    parent = parent_identity(output)
    result = runtime.initialize(destination, repository=Path(repository), **config)
    try:
        publish_receipt(output, {"kind": "INITIALIZE", "configuration": config}, result, parent)
    except Exception as exc:
        raise DomainError(
            "RUNTIME_CREATED_RECEIPT_NOT_PUBLISHED: preserve the initialized runtime; "
            "inspect its RUNTIME.json using its exact SHA256. Do not initialize over it."
        ) from exc
    return result


def operate(root, action_path, output):
    root = private(Path(root), True)
    output = output_destination(output, root)
    parent = parent_identity(output)
    action = read_json(action_path)
    if (
        set(action) != {"kind", "parameters"}
        or not isinstance(action["kind"], str)
        or action["kind"] not in ACTIONS
        or not isinstance(action["parameters"], dict)
        or set(action["parameters"]) != COMMAND
    ):
        raise DomainError("Exact supported security-event action fields required")
    result = runtime.execute(root, action=action["kind"], **action["parameters"])
    try:
        publish_receipt(output, action, result, parent)
    except Exception as exc:
        raise DomainError(
            "OPERATION_COMMITTED_RECEIPT_NOT_PUBLISHED: preserve the runtime; "
            "replay the exact action into a new private receipt destination."
        ) from exc
    return result


def inspect(root, expected_runtime_sha256, output):
    root = private(Path(root), True)
    output = output_destination(output, root)
    parent = parent_identity(output)
    result = runtime.inspect(root, expected_runtime_sha256=expected_runtime_sha256)
    publish_receipt(
        output,
        {"kind": "INSPECT", "expected_runtime_sha256": expected_runtime_sha256},
        result,
        parent,
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("initialize")
    init.add_argument("--configuration", type=Path, required=True)
    init.add_argument("--destination", type=Path, required=True)
    init.add_argument("--repository", type=Path, default=ROOT)
    init.add_argument("--output", type=Path, required=True)
    op = commands.add_parser("operate")
    op.add_argument("--runtime", type=Path, required=True)
    op.add_argument("--action", type=Path, required=True)
    op.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("inspect")
    check.add_argument("--runtime", type=Path, required=True)
    check.add_argument("--runtime-sha256", required=True)
    check.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "initialize":
        initialize(args.configuration, args.destination, args.output, args.repository)
    elif args.command == "operate":
        operate(args.runtime, args.action, args.output)
    else:
        inspect(args.runtime, args.runtime_sha256, args.output)


if __name__ == "__main__":
    main()
