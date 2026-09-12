"""Copy a private store only after old and new evaluators reproduce identical history."""

import argparse
import hashlib
import importlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import types
import uuid
from contextlib import contextmanager
from pathlib import Path

from enterprise.ccf.registry import ROOT, canonical, digest

from . import store


@contextmanager
def legacy_runtime(repository, revision):
    """Execute only code explicitly selected from the operator's trusted local Git history."""
    commit = subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "--verify", revision + "^{commit}"], text=True
    ).strip()
    name = "_ccf_migration_" + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix="ccf-legacy-") as tmp:
        for module in ("testing", "store"):
            source = subprocess.check_output(
                [
                    "git",
                    "-C",
                    str(repository),
                    "show",
                    f"{commit}:enterprise/ccf/operations/{module}.py",
                ]
            )
            (Path(tmp) / (module + ".py")).write_bytes(source)
        package = types.ModuleType(name)
        package.__path__ = [tmp]
        sys.modules[name] = package
        try:
            yield importlib.import_module(name + ".store"), commit
        finally:
            for key in list(sys.modules):
                if key == name or key.startswith(name + "."):
                    del sys.modules[key]


def migrate(source, output, legacy_revision, repository=ROOT):
    source, output = Path(source), Path(output)
    if source.is_symlink() or not source.is_file() or source.stat().st_mode & 0o077:
        raise ValueError("Source store must be a private regular file")
    if output.exists() or output.is_symlink():
        raise ValueError("Migration output must be a new directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    # One read transaction provides a stable snapshot even if another process appends later.
    original = sqlite3.connect(source.absolute().as_uri() + "?mode=ro", uri=True)
    original.row_factory = sqlite3.Row
    original.execute("BEGIN")
    try:
        with legacy_runtime(repository, legacy_revision) as (legacy, commit):
            before = legacy.replay(
                original
            )  # Also verifies the exact old implementation fingerprint.
            old_config = json.loads(
                original.execute("SELECT payload FROM config WHERE id=1").fetchone()[0]
            )
            head = original.execute(
                "SELECT event_hash FROM event ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            with tempfile.TemporaryDirectory(prefix=".ccf-migration-", dir=output.parent) as tmp:
                staged = Path(tmp) / "bundle"
                staged.mkdir(mode=0o700)
                dbpath = staged / "workflow.sqlite3"
                db = sqlite3.connect(dbpath)
                db.row_factory = sqlite3.Row
                try:
                    original.backup(db)
                    db.execute("DROP TRIGGER immutable_config_UPDATE")
                    config = dict(old_config, implementation_digest=store.implementation_digest())
                    db.execute("UPDATE config SET payload=? WHERE id=1", (canonical(config),))
                    db.execute(
                        "CREATE TRIGGER immutable_config_UPDATE BEFORE UPDATE ON config BEGIN SELECT RAISE(ABORT, 'immutable workflow history'); END"
                    )
                    db.commit()
                    after = store.replay(db)
                    if before != after:
                        raise ValueError(
                            "New evaluator changes retained assessment history; migration rejected"
                        )
                finally:
                    db.close()
                dbpath.chmod(0o600)
                receipt = dict(
                    schema_version=1,
                    legacy_commit=commit,
                    old_implementation_digest=old_config["implementation_digest"],
                    new_implementation_digest=config["implementation_digest"],
                    snapshot_event_head=head[0] if head else None,
                    verified_state_digest=digest(before),
                    cases=len(before),
                    retained_principals_and_credentials=True,
                    original_unchanged=True,
                    limitation="This copies the verified snapshot. Quiesce the old writer before cutover; later appends are not included. Existing credentials retain their grants/expiry/revocations.",
                )
                receipt["database_sha256"] = hashlib.sha256(dbpath.read_bytes()).hexdigest()
                path = staged / "MIGRATION_RECEIPT.json"
                path.write_text(json.dumps(receipt, indent=2) + "\n")
                path.chmod(0o600)
                staged.rename(output)
                return receipt
    finally:
        original.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--legacy-revision",
        required=True,
        help="Trusted local Git commit containing the exact prior evaluator files",
    )
    args = parser.parse_args()
    try:
        result = migrate(Path(args.source), args.output, args.legacy_revision)
    except (ValueError, OSError, sqlite3.Error, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"Migration failed: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
