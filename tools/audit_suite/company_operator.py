"""Trusted local company operator; never expose this command as an unauthenticated API."""

import argparse
import json
import os
from pathlib import Path

from enterprise.audit_suite.company_recovery import backup, restore
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError


def _output(path, content):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise CompanyStoreError("Output aliases forbidden")
    if not path.parent.is_dir() or path.parent.stat().st_mode & 0o077:
        raise CompanyStoreError("Existing private output parent required")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=["init", "register", "grant", "revoke", "discover", "collect", "backup", "restore"],
    )
    parser.add_argument("--private-root", type=Path)
    for name in (
        "company",
        "branch",
        "system",
        "owner",
        "principal",
        "engagement",
        "record",
        "as-of",
        "command-id",
    ):
        parser.add_argument("--" + name)
    parser.add_argument("--version", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--receipt-output", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--after-record")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)

    def require(*names):
        if any(getattr(args, n.replace("-", "_")) is None for n in names):
            parser.error("Required arguments: " + ", ".join("--" + n for n in names))

    if args.action == "restore":
        require("source", "destination")
        restore(args.source, args.destination)
    else:
        require("private-root")
        store = CompanyStore(args.private_root)
        key = (args.company, args.branch, args.system)
        if args.action == "register":
            require("company", "branch", "system", "owner")
            store.register_system(*key, args.owner)
        elif args.action in {"grant", "revoke"}:
            require("company", "branch", "system", "principal", "engagement")
            store.grant(args.principal, args.engagement, *key, active=args.action == "grant")
        elif args.action in {"discover", "collect"}:
            require("company", "branch", "system", "principal", "engagement", "as-of", "output")
            scoped = (args.principal, args.engagement, *key)
            if args.action == "discover":
                result = store.list_records(
                    *scoped, as_of=args.as_of, after_record=args.after_record, limit=args.limit
                )
                _output(args.output, (json.dumps(result, indent=2) + "\n").encode())
            else:
                require("record", "version", "command-id", "receipt-output")
                # Fail before recording collection when an output would overwrite prior evidence.
                if (
                    args.output.exists()
                    or args.receipt_output.exists()
                    or args.output.absolute() == args.receipt_output.absolute()
                ):
                    raise CompanyStoreError("New distinct collection outputs required")
                value = store.read_version(
                    *scoped, args.record, version=args.version, as_of=args.as_of
                )
                receipt = store.collect(
                    *scoped,
                    args.record,
                    version=args.version,
                    as_of=args.as_of,
                    command_id=args.command_id,
                )
                _output(args.output, value["content"])
                _output(args.receipt_output, (json.dumps(receipt, indent=2) + "\n").encode())
        elif args.action == "backup":
            require("destination")
            backup(store, args.destination)
    print(json.dumps({"action": args.action, "status": "COMPLETE"}))


if __name__ == "__main__":
    main()
