"""Run explicitly selected fictional company activity before any audit exists.

Trusted local operator command. Recipes and resulting stores remain private; no
engagement creation, grants, source collection, hosted service or model invocation.
"""

import argparse
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

from enterprise.audit_suite.company_activity import TransferRecipe, generate_pair
from enterprise.audit_suite.company_activity_period import PeriodRecipe, generate_period
from enterprise.audit_suite.company_backup_activity import BackupRecipe, generate_backup_pair
from enterprise.audit_suite.company_change_activity import ChangeRecipe
from enterprise.audit_suite.company_change_activity import generate_pair as generate_change_pair
from enterprise.audit_suite.company_configuration_activity import ConfigurationRecipe
from enterprise.audit_suite.company_configuration_activity import generate as generate_configuration
from enterprise.audit_suite.company_incident_activity import IncidentRecipe, generate_incident
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.company_training_activity import (
    TrainingCourse,
    TrainingMember,
    TrainingRecipe,
)
from enterprise.audit_suite.company_training_activity import (
    generate_pair as generate_training_pair,
)
from enterprise.audit_suite.private_publication import publish

KINDS = {
    "mover": (TransferRecipe, generate_pair),
    "identity-period": (PeriodRecipe, generate_period),
    "incident": (IncidentRecipe, generate_incident),
    "backup": (BackupRecipe, generate_backup_pair),
    "training": (TrainingRecipe, generate_training_pair),
    "change": (ChangeRecipe, generate_change_pair),
    "configuration": (ConfigurationRecipe, generate_configuration),
}
MAX_RECIPE_BYTES = 64 * 1024


def _private(path, directory=False):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CompanyStoreError("Activity recipe/output aliases forbidden")
    info = path.stat()
    if info.st_mode & 0o077 or not (
        stat.S_ISDIR(info.st_mode)
        if directory
        else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    ):
        raise CompanyStoreError("Private regular recipe and private output parent required")


def _write(path, content):
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(content)


def run(kind, recipe_path, destination, *, repository, source_root=None):
    recipe_path, destination = Path(recipe_path).absolute(), Path(destination).absolute()
    if kind not in KINDS:
        raise CompanyStoreError("Unknown company activity kind")
    _private(recipe_path)
    _private(destination.parent, True)
    if destination.exists() or destination.is_symlink():
        raise CompanyStoreError("New private activity destination required")
    if kind == "configuration":
        if source_root is None:
            raise CompanyStoreError("Configuration activity requires an explicit source root")
        source_root = Path(source_root).absolute()
        _private(source_root, True)
        _private(source_root / "company.sqlite3")
        if destination.is_relative_to(source_root):
            raise CompanyStoreError("Activity output must be outside its original source root")
    elif source_root is not None:
        raise CompanyStoreError("Source root is supported only for configuration activity")
    if recipe_path.stat().st_size > MAX_RECIPE_BYTES:
        raise CompanyStoreError("Activity recipe exceeds bounded size")
    fd = os.open(recipe_path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
            raise CompanyStoreError("Private regular recipe required")
        raw = stream.read(MAX_RECIPE_BYTES + 1)
    if len(raw) > MAX_RECIPE_BYTES:
        raise CompanyStoreError("Activity recipe exceeds bounded size")
    try:

        def unique_object(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("Duplicate recipe key")
                value[key] = item
            return value

        def reject_constant(_value):
            raise ValueError("Nonfinite recipe value")

        body = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
        if not isinstance(body, dict):
            raise ValueError("Recipe object required")
        cls, generate = KINDS[kind]
        if kind == "identity-period":
            body["movers"] = tuple(TransferRecipe(**row) for row in body["movers"])
        if kind == "training":
            body["cohort"] = tuple(TrainingMember(**row) for row in body["cohort"])
            body["courses"] = tuple(
                TrainingCourse(**{**row, "role_ids": tuple(row["role_ids"])})
                for row in body["courses"]
            )
        if kind == "configuration":
            for key in ("branch_ids", "checkpoints"):
                if not isinstance(body[key], list):
                    raise ValueError("Explicit JSON arrays required")
                body[key] = tuple(body[key])
        recipe = cls(**body)
    except (TypeError, ValueError, KeyError) as error:
        raise CompanyStoreError("Invalid explicit activity recipe") from error
    with tempfile.TemporaryDirectory(prefix=".company-activity-", dir=destination.parent) as temp:
        stage = Path(temp)
        if kind in {"training", "change", "configuration"}:
            result = generate(
                stage / "company",
                repository=Path(repository),
                recipe=recipe,
                **({"source_root": source_root} if kind == "configuration" else {}),
            )
            store = CompanyStore(stage / "company")
        else:
            (stage / "company").mkdir(mode=0o700)
            store = CompanyStore(stage / "company")
            result = generate(store, repository=Path(repository), recipe=recipe)
        with store._db() as db:
            counts = {
                table: db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                for table in ("systems", "versions", "grants", "collections")
            }
            for content, digest in db.execute("SELECT content,sha256 FROM versions"):
                if hashlib.sha256(content).hexdigest() != digest:
                    raise CompanyStoreError("Generated original integrity failure")
        if counts["grants"] or counts["collections"]:
            raise CompanyStoreError("Activity generation unexpectedly accessed audit sources")
        _write(stage / "RECIPE.json", raw)
        _write(
            stage / "RECEIPT.json", (json.dumps(result, sort_keys=True, indent=2) + "\n").encode()
        )
        members = {}
        for path in sorted(stage.rglob("*")):
            _private(path, directory=path.is_dir())
            if path.is_file():
                members[str(path.relative_to(stage))] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
        manifest = {
            "format": "PRIVATE_COMPANY_ACTIVITY_RUN_V1",
            "kind": kind,
            "counts": counts,
            "audit_created": False,
            "grants_created": False,
            "professional_validation": "NOT_ASSESSED",
            "recipe_sha256": hashlib.sha256(raw).hexdigest(),
            "members": members,
        }
        if kind == "configuration":
            manifest["source_input"] = {
                "root": str(source_root),
                "source_store_id": recipe.source_store_id,
                "source_versions_sha256": recipe.source_versions_sha256,
            }
        _write(stage / "MANIFEST.json", (json.dumps(manifest, indent=2) + "\n").encode())
        publish(stage, destination)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=KINDS)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--source-root", type=Path, help="Existing original change store; configuration only"
    )
    args = parser.parse_args(argv)
    result = run(
        args.kind,
        args.recipe,
        args.destination,
        repository=args.repository,
        source_root=args.source_root,
    )
    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "kind": args.kind,
                "counts": result["counts"],
                "audit_created": False,
            }
        )
    )


if __name__ == "__main__":
    main()
