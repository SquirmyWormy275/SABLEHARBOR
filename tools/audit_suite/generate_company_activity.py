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
from enterprise.audit_suite.company_lifecycle_activity import LifecycleRecipe, LifecycleSourceRef
from enterprise.audit_suite.company_lifecycle_activity import (
    generate_pair as generate_lifecycle_pair,
)
from enterprise.audit_suite.company_nonhuman_identity_activity import NonhumanIdentityRecipe
from enterprise.audit_suite.company_nonhuman_identity_activity import (
    generate_pair as generate_nonhuman_pair,
)
from enterprise.audit_suite.company_provider_intake_activity import ProviderIntakeRecipe
from enterprise.audit_suite.company_provider_intake_activity import (
    generate_pair as generate_provider_pair,
)
from enterprise.audit_suite.company_risk_assessment_activity import (
    RiskAssessmentRecipe,
    RiskScenario,
    RiskSourceGroup,
    RiskSourceRef,
)
from enterprise.audit_suite.company_risk_assessment_activity import (
    generate_pair as generate_risk_pair,
)
from enterprise.audit_suite.company_security_logging_activity import LoggingRecipe
from enterprise.audit_suite.company_security_logging_activity import (
    generate_pair as generate_logging_pair,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.company_training_activity import (
    TrainingCourse,
    TrainingMember,
    TrainingRecipe,
)
from enterprise.audit_suite.company_training_activity import (
    generate_pair as generate_training_pair,
)
from enterprise.audit_suite.inference import _json
from enterprise.audit_suite.private_publication import publish

KINDS = {
    "mover": (TransferRecipe, generate_pair),
    "identity-period": (PeriodRecipe, generate_period),
    "incident": (IncidentRecipe, generate_incident),
    "backup": (BackupRecipe, generate_backup_pair),
    "training": (TrainingRecipe, generate_training_pair),
    "change": (ChangeRecipe, generate_change_pair),
    "configuration": (ConfigurationRecipe, generate_configuration),
    "security-logging": (LoggingRecipe, generate_logging_pair),
    "provider-intake": (ProviderIntakeRecipe, generate_provider_pair),
    "identity-lifecycle": (LifecycleRecipe, generate_lifecycle_pair),
    "nonhuman-identity": (NonhumanIdentityRecipe, generate_nonhuman_pair),
    "risk-assessment": (RiskAssessmentRecipe, generate_risk_pair),
}
SOURCE_KINDS = {"configuration", "security-logging", "identity-lifecycle", "nonhuman-identity"}
MULTI_SOURCE_KINDS = {"risk-assessment"}
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


def _private_bytes(path):
    _private(path)
    if path.stat().st_size > MAX_RECIPE_BYTES:
        raise CompanyStoreError("Activity recipe exceeds bounded size")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
            raise CompanyStoreError("Private regular recipe required")
        raw = stream.read(MAX_RECIPE_BYTES + 1)
        final = os.fstat(stream.fileno())
    _private(path)
    current = path.stat()
    if any(
        getattr(info, key) != getattr(other, key)
        for other in (final, current)
        for key in ("st_dev", "st_ino", "st_ctime_ns", "st_size")
    ):
        raise CompanyStoreError("Private activity input changed during read")
    if len(raw) > MAX_RECIPE_BYTES:
        raise CompanyStoreError("Activity recipe exceeds bounded size")
    return raw


def load_source_roots(path):
    try:
        value = _json(_private_bytes(Path(path).absolute()))
        if (
            not isinstance(value, dict)
            or not 1 <= len(value) <= 8
            or any(
                not isinstance(k, str)
                or not k
                or not isinstance(v, str)
                or not Path(v).is_absolute()
                for k, v in value.items()
            )
        ):
            raise ValueError("Explicit bounded source-root map required")
        return {key: Path(value) for key, value in value.items()}
    except (TypeError, ValueError) as error:
        raise CompanyStoreError("Invalid explicit source-root map") from error


def run(kind, recipe_path, destination, *, repository, source_root=None, source_roots=None):
    recipe_path, destination = Path(recipe_path).absolute(), Path(destination).absolute()
    if kind not in KINDS:
        raise CompanyStoreError("Unknown company activity kind")
    _private(recipe_path)
    _private(destination.parent, True)
    if destination.exists() or destination.is_symlink():
        raise CompanyStoreError("New private activity destination required")
    if source_root is not None and source_roots is not None:
        raise CompanyStoreError("Choose one explicit source-root contract")
    if kind in MULTI_SOURCE_KINDS:
        if not isinstance(source_roots, dict) or not 1 <= len(source_roots) <= 8:
            raise CompanyStoreError("This activity requires an explicit source-root map")
        source_roots = {key: Path(value).absolute() for key, value in source_roots.items()}
        for root in source_roots.values():
            _private(root, True)
            _private(root / "company.sqlite3")
            if destination.resolve().is_relative_to(root.resolve()):
                raise CompanyStoreError(
                    "Activity output must be outside every original source root"
                )
    elif source_roots is not None:
        raise CompanyStoreError("Source-root map is supported only for multi-source activity")
    if kind in SOURCE_KINDS:
        if source_root is None:
            raise CompanyStoreError("This activity requires an explicit source root")
        source_root = Path(source_root).absolute()
        _private(source_root, True)
        _private(source_root / "company.sqlite3")
        if destination.resolve().is_relative_to(source_root.resolve()):
            raise CompanyStoreError("Activity output must be outside its original source root")
    elif source_root is not None:
        raise CompanyStoreError("Source root is supported only for source-dependent activity")
    raw = _private_bytes(recipe_path)
    try:
        body = _json(raw)
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
        if kind in {"identity-lifecycle", "nonhuman-identity"}:
            if not isinstance(body["source_refs"], list) or not isinstance(
                body["branch_ids"], list
            ):
                raise ValueError("Explicit JSON arrays required")
            body["source_refs"] = tuple(LifecycleSourceRef(**row) for row in body["source_refs"])
            body["branch_ids"] = tuple(body["branch_ids"])
        if kind == "risk-assessment":
            if any(
                not isinstance(body[key], list)
                for key in ("source_groups", "scenarios", "branch_ids")
            ):
                raise ValueError("Explicit JSON arrays required")
            groups = []
            for group in body["source_groups"]:
                if not isinstance(group, dict) or not isinstance(group["source_refs"], list):
                    raise ValueError("Exact grouped source arrays required")
                groups.append(
                    RiskSourceGroup(
                        **{
                            **group,
                            "source_refs": tuple(
                                RiskSourceRef(**ref) for ref in group["source_refs"]
                            ),
                        }
                    )
                )
            body["source_groups"] = tuple(groups)
            body["scenarios"] = tuple(RiskScenario(**row) for row in body["scenarios"])
            body["branch_ids"] = tuple(body["branch_ids"])
        recipe = cls(**body)
    except (TypeError, ValueError, KeyError) as error:
        raise CompanyStoreError("Invalid explicit activity recipe") from error
    with tempfile.TemporaryDirectory(prefix=".company-activity-", dir=destination.parent) as temp:
        stage = Path(temp)
        if kind in {"training", "change", "provider-intake", *SOURCE_KINDS, *MULTI_SOURCE_KINDS}:
            result = generate(
                stage / "company",
                repository=Path(repository),
                recipe=recipe,
                **({"source_root": source_root} if kind in SOURCE_KINDS else {}),
                **({"source_roots": source_roots} if kind in MULTI_SOURCE_KINDS else {}),
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
        if kind in SOURCE_KINDS:
            manifest["source_input"] = {
                "root": str(source_root),
                "source_store_id": recipe.source_store_id,
                "source_versions_sha256": recipe.source_versions_sha256,
            }
        if kind in MULTI_SOURCE_KINDS:
            manifest["source_inputs"] = {
                group.id: {
                    "root": str(source_roots[group.id]),
                    "source_store_id": group.source_store_id,
                    "source_versions_sha256": group.source_versions_sha256,
                }
                for group in recipe.source_groups
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
        "--source-root", type=Path, help="Existing original company store for dependent activities"
    )
    parser.add_argument(
        "--source-roots", type=Path, help="Private JSON map of explicit source groups to roots"
    )
    args = parser.parse_args(argv)
    result = run(
        args.kind,
        args.recipe,
        args.destination,
        repository=args.repository,
        source_root=args.source_root,
        source_roots=load_source_roots(args.source_roots)
        if args.source_roots is not None
        else None,
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
