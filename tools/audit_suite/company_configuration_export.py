"""Export actual local configuration bytes into company records with a private receipt."""

import argparse
from pathlib import Path

from enterprise.audit_suite import company_configuration_export as exporter
from enterprise.audit_suite.company_backup_runtime import private
from enterprise.audit_suite.store import DomainError
from tools.audit_suite.company_backup_runtime import (
    output_destination,
    parent_identity,
    publish_receipt,
)
from tools.audit_suite.company_configuration_runtime import BASE
from tools.audit_suite.reconcile_source_dependencies import read_json


def run(root, action_path, output):
    root = private(Path(root), True)
    output = output_destination(output, root)
    parent = parent_identity(output)
    action = read_json(action_path)
    if (
        set(action) != {"kind", "parameters"}
        or action["kind"] != "EXPORT_CURRENT"
        or not isinstance(action["parameters"], dict)
        or set(action["parameters"]) != BASE
    ):
        raise DomainError("Exact current-configuration export action required")
    result = exporter.export_current(root, **action["parameters"])
    try:
        publish_receipt(
            output,
            action,
            result,
            parent,
            receipt_format="COMPANY_CONFIGURATION_EXPORT_RECEIPT_V1",
        )
    except Exception as exc:
        raise DomainError(
            "EXPORT_COMMITTED_RECEIPT_NOT_PUBLISHED: preserve the runtime; "
            "replay the exact export action into a new private receipt destination."
        ) from exc
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--action", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run(args.runtime, args.action, args.output)


if __name__ == "__main__":
    main()
