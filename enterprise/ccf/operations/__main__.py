"""CLI for private, authenticated evidence intake; no live vendor or assurance access."""

import argparse
import json
import os
import sqlite3
from pathlib import Path

from enterprise.ccf.assurance import assessment_run
from enterprise.ccf.registry import compile_registry

from . import selection, store


def private_write(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(text)


def read_credential(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_mode & 0o077:
        raise ValueError("Credential file must be a private regular file")
    return p.read_text().strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--reference", required=True)
    init.add_argument("--source-root", required=True)
    init.add_argument(
        "--principals",
        required=True,
        help="JSON array of local subject IDs, permissions, boundaries and credential validity",
    )
    init.add_argument(
        "--output", required=True, help="New private directory for workflow DB and credential files"
    )
    for name in ("command", "report", "revoke"):
        child = sub.add_parser(name)
        child.add_argument("--db", required=True)
        child.add_argument("--credential-file", required=True)
        if name == "command":
            child.add_argument("--case", required=True)
            child.add_argument(
                "--action",
                required=True,
                choices=[
                    "create",
                    "assign",
                    "population",
                    "intake",
                    "review",
                    "remediate",
                    "close_prospectively",
                ],
            )
            child.add_argument("--payload", required=True)
            child.add_argument("--revision", type=int, required=True)
        elif name == "report":
            child.add_argument("--output", required=True, help="New private JSON report file")
        else:
            child.add_argument("--subject", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--reference", required=True)
    demo.add_argument("--source-root", required=True)
    demo.add_argument("--output", required=True)
    for child in (init, demo):
        child.add_argument(
            "--framework", action="append", choices=sorted(selection.VARIANTS), default=[]
        )
    args = parser.parse_args()
    try:
        if args.command in {"init", "demo"}:
            output = Path(args.output)
            if output.exists() or output.is_symlink():
                raise ValueError("Output must be a new directory")
            assessment_run.verify(args.reference, compile_registry(), args.source_root)
            reference = json.loads((Path(args.reference) / "ASSESSMENT_RUN.json").read_text())
            plans = selection.plans(reference, args.framework)
            if args.command == "demo":
                from .examples import build

                print(json.dumps(build(output, plans), indent=2))
                return
            principals = json.loads(Path(args.principals).read_text())
            # Subject IDs never become unchecked filesystem paths.
            if any(
                not p["id"]
                or any(
                    c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
                    for c in p["id"]
                )
                for p in principals
            ):
                raise ValueError("Subject IDs must be alphanumeric, hyphen or underscore")
            output.mkdir(parents=True, mode=0o700)
            tokens = store.initialize(output / "workflow.sqlite3", plans, principals)
            for subject, token in tokens.items():
                private_write(output / f"{subject}.credential", token + "\n")
            private_write(output / "TEST_PLANS.json", json.dumps(plans, indent=2) + "\n")
            print(
                json.dumps(
                    dict(
                        plans=len(plans),
                        database=str(output / "workflow.sqlite3"),
                        credential_files=len(tokens),
                    )
                )
            )
        else:
            token = read_credential(args.credential_file)
            db = store.connect(args.db)
            try:
                if args.command == "command":
                    state = store.command(
                        db,
                        token,
                        args.case,
                        args.action,
                        json.loads(Path(args.payload).read_text()),
                        args.revision,
                    )
                    print(
                        json.dumps(
                            dict(case=state["id"], revision=state["revision"], state=state["state"])
                        )
                    )
                elif args.command == "report":
                    private_write(args.output, json.dumps(store.report(db, token), indent=2) + "\n")
                    print("Private report written")
                else:
                    store.revoke(db, token, args.subject)
                    print("Credential revoked")
            finally:
                db.close()
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
        parser.exit(2, f"CCF workflow error: {exc}\n")


if __name__ == "__main__":
    main()
