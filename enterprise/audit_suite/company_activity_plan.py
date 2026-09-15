"""Explicit private company operations; no audit, grants, model or dynamic code dispatch."""

import copy
import dataclasses
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import get_args, get_origin, get_type_hints

from enterprise.audit_suite.company_configuration_activity import read_originals
from enterprise.audit_suite.company_store import CompanyStoreError
from tools.audit_suite import generate_company_activity as operator

FORMAT = "PRIVATE_COMPANY_ACTIVITY_PLAN_V1"
MAX_PLAN_BYTES = 512 * 1024
MAX_JOBS = 24
ID = re.compile(r"[a-z][a-z0-9-]{0,47}\Z")


def _private(path, directory=False):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CompanyStoreError("Private nonsymlink plan paths required")
    mode = path.stat()
    if mode.st_mode & 0o077 or not (
        stat.S_ISDIR(mode.st_mode)
        if directory
        else stat.S_ISREG(mode.st_mode) and mode.st_nlink == 1
    ):
        raise CompanyStoreError("Private regular plan files/directories required")


def _bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def _write(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _read(path, limit=MAX_PLAN_BYTES):
    _private(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if info.st_mode & 0o077 or info.st_nlink != 1 or not stat.S_ISREG(info.st_mode):
            raise CompanyStoreError("Private regular plan file required")
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise CompanyStoreError("Plan file size limit exceeded")
    return raw


def _parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate key")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("Nonfinite value")

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, RecursionError) as error:
        raise CompanyStoreError("Strict finite JSON plan required") from error


def _typed(value, annotation):
    if dataclasses.is_dataclass(annotation):
        _recipe(value, annotation)
    elif get_origin(annotation) is tuple:
        args = get_args(annotation)
        if not isinstance(value, list) or len(value) > 1000:
            raise CompanyStoreError("Bounded explicit recipe array required")
        for item in value:
            _typed(item, args[0])
    elif annotation in (str, int, bool, float):
        if type(value) is not annotation:
            raise CompanyStoreError("Exact recipe field type required")
    else:
        raise CompanyStoreError("Unsupported maintained recipe field schema")


def _recipe(value, cls, derived=False):
    if not isinstance(value, dict):
        raise CompanyStoreError("Recipe object required")
    fields = {f.name: f for f in dataclasses.fields(cls)}
    supplied = set(value)
    expected = set(fields) - ({"source_versions_sha256"} if derived else set())
    required = {
        f.name
        for f in fields.values()
        if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
    }
    if derived:
        required.discard("source_versions_sha256")
    if not required <= supplied or not supplied <= expected:
        raise CompanyStoreError("Exact recipe fields required; source hash is derived only")
    hints = get_type_hints(cls)
    for key, item in value.items():
        _typed(item, hints[key])
    if len(_bytes(value)) > operator.MAX_RECIPE_BYTES:
        raise CompanyStoreError("Recipe size limit exceeded")


def validate_plan(value):
    """Validate complete structure/types/order; native generator semantics run separately."""
    if not isinstance(value, dict) or set(value) != {"format", "jobs"} or value["format"] != FORMAT:
        raise CompanyStoreError("Exact company activity plan format required")
    jobs = value["jobs"]
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= MAX_JOBS:
        raise CompanyStoreError("Plan requires 1 to 24 ordered jobs")
    prior = {}
    source_labels, label_sources = {}, {}
    for job in jobs:
        if not isinstance(job, dict) or not {"id", "kind", "depends_on", "recipe"} <= set(job):
            raise CompanyStoreError("Explicit job identity/kind/dependencies/recipe required")
        if set(job) - {"id", "kind", "depends_on", "recipe", "source_job"}:
            raise CompanyStoreError("Unknown job field")
        identity, kind = job["id"], job["kind"]
        if not isinstance(identity, str) or not ID.fullmatch(identity) or identity in prior:
            raise CompanyStoreError("Distinct safe job IDs required")
        if not isinstance(kind, str) or kind not in operator.KINDS:
            raise CompanyStoreError("Unknown company activity kind")
        deps = job["depends_on"]
        if (
            not isinstance(deps, list)
            or any(not isinstance(d, str) for d in deps)
            or len(deps) != len(set(deps))
            or any(d not in prior for d in deps)
        ):
            raise CompanyStoreError(
                "Distinct prior dependencies required; cycles/forward refs forbidden"
            )
        dependent = kind in operator.SOURCE_KINDS
        if dependent:
            source = job.get("source_job")
            if (
                not isinstance(source, str)
                or source not in deps
                or prior[source]["kind"] != "change"
            ):
                raise CompanyStoreError("Source job must be an explicit prior change dependency")
        elif "source_job" in job:
            raise CompanyStoreError("Source job allowed only for source-dependent kinds")
        _recipe(job["recipe"], operator.KINDS[kind][0], derived=dependent)
        if dependent:
            label = job["recipe"]["source_store_id"]
            source = job["source_job"]
            if (source in source_labels and source_labels[source] != label) or (
                label in label_sources and label_sources[label] != source
            ):
                raise CompanyStoreError("Source labels must identify exactly one plan source job")
            if job["recipe"]["company_id"] != prior[source]["recipe"]["company_id"]:
                raise CompanyStoreError("Dependent recipe company differs from source job")
            source_labels[source], label_sources[label] = label, source
        prior[identity] = job
    return copy.deepcopy(value)


def _verify_job(directory, manifest):
    """Verify only explicit maintained manifest members; never discover source directories."""
    if not isinstance(manifest.get("members"), dict) or len(manifest["members"]) > 5000:
        raise CompanyStoreError("Bounded activity manifest required")
    for name, pin in manifest["members"].items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise CompanyStoreError("Invalid activity manifest member")
        path = directory / relative
        _private(path)
        # Original per-source blobs are bounded by maintained operator/source readers.
        if hashlib.sha256(path.read_bytes()).hexdigest() != pin:
            raise CompanyStoreError("Completed activity manifest integrity failure")
    if manifest.get("audit_created") is not False or manifest.get("grants_created") is not False:
        raise CompanyStoreError("Activity boundary violated")
    if manifest["counts"]["grants"] or manifest["counts"]["collections"]:
        raise CompanyStoreError("Activity unexpectedly used source grants or collections")


def _verify_completed(completed):
    directory, manifest, expected = completed
    raw = _read(directory / "MANIFEST.json")
    if hashlib.sha256(raw).hexdigest() != expected or _parse(raw) != manifest:
        raise CompanyStoreError("Completed dependency manifest changed")
    _verify_job(directory, manifest)


def run(plan_path, destination, *, repository):
    """New-only execution, stops on first failure; returns retained bounded status summary."""
    plan_path, destination = Path(plan_path).absolute(), Path(destination).absolute()
    raw = _read(plan_path)
    plan = validate_plan(_parse(raw))
    _private(destination.parent, True)
    if destination.exists() or destination.is_symlink():
        raise CompanyStoreError("New private plan destination required; resume is not supported")
    destination.mkdir(mode=0o700)
    _write(destination / "PLAN.json", raw)
    for child in ("jobs", "recipes", "events"):
        (destination / child).mkdir(mode=0o700)
    summary = {
        "format": "PRIVATE_COMPANY_ACTIVITY_PLAN_RUN_V1",
        "status": "RUNNING",
        "plan_sha256": hashlib.sha256(raw).hexdigest(),
        "jobs": [],
        "audit_created": False,
        "grants_created": False,
        "models_invoked": False,
        "runner_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "operator_source_sha256": hashlib.sha256(Path(operator.__file__).read_bytes()).hexdigest(),
        "validation": "STRUCTURE_AND_TYPES_BEFORE_RUN_NATIVE_SEMANTICS_PER_JOB",
        "limits": [
            "Explicit fictional recipe assumptions retained per job.",
            "Branches remain separate; no coherent operating year or merged world implied.",
            "No automatic retry or resume; completed outputs are never overwritten.",
        ],
    }
    completed = {}
    stopped = False
    for index, job in enumerate(plan["jobs"]):
        receipt = {
            "id": job["id"],
            "kind": job["kind"],
            "depends_on": job["depends_on"],
            "status": "NOT_RUN" if stopped else "STARTED",
        }
        prefix = f"{index:02d}-{job['id']}"
        _write(destination / "events" / f"{prefix}-started.json", _bytes(receipt))
        if not stopped:
            stage = "RESOLVE_RECIPE_AND_DEPENDENCY"
            try:
                for dependency_id in job["depends_on"]:
                    _verify_completed(completed[dependency_id])
                receipt["dependency_manifest_sha256"] = {
                    dependency_id: completed[dependency_id][2]
                    for dependency_id in job["depends_on"]
                }
                recipe = copy.deepcopy(job["recipe"])
                source_root = None
                if "source_job" in job:
                    source_id = job["source_job"]
                    source_dir, source_manifest, manifest_pin = completed[source_id]
                    current_manifest = _read(source_dir / "MANIFEST.json")
                    if hashlib.sha256(current_manifest).hexdigest() != manifest_pin:
                        raise CompanyStoreError("Completed dependency manifest changed")
                    _verify_job(source_dir, source_manifest)
                    source_root = source_dir / "company"
                    originals, pin = read_originals(source_root)
                    if {r["company"] for r in originals} != {recipe["company_id"]}:
                        raise CompanyStoreError("Dependent recipe company differs from source job")
                    recipe["source_versions_sha256"] = pin
                    receipt["dependency"] = {
                        "source_job": source_id,
                        "source_root": str(source_root),
                        "source_store_id": recipe["source_store_id"],
                        "source_versions_sha256": pin,
                        "source_versions": len(originals),
                        "source_job_manifest_sha256": manifest_pin,
                        "store_label_basis": "EXPLICIT_RECIPE_LABEL_BOUND_TO_THIS_SOURCE_JOB",
                    }
                    _write(
                        destination / "events" / f"{prefix}-dependency.json",
                        _bytes(receipt["dependency"]),
                    )
                recipe_path = destination / "recipes" / f"{job['id']}.json"
                recipe_raw = _bytes(recipe)
                _write(recipe_path, recipe_raw)
                receipt["resolved_recipe_sha256"] = hashlib.sha256(recipe_raw).hexdigest()
                output = destination / "jobs" / job["id"]
                stage = "RUN_NATIVE_OPERATOR"
                manifest = operator.run(
                    job["kind"],
                    recipe_path,
                    output,
                    repository=Path(repository),
                    source_root=source_root,
                )
                stage = "VERIFY_PUBLISHED_OUTPUT"
                _verify_job(output, manifest)
                published = _read(output / "MANIFEST.json")
                if _parse(published) != manifest:
                    raise CompanyStoreError(
                        "Published activity manifest differs from operator result"
                    )
                pin = hashlib.sha256(published).hexdigest()
                stage = "VERIFY_PRIOR_OUTPUTS_AFTER_JOB"
                for previous in completed.values():
                    _verify_completed(previous)
                completed[job["id"]] = (output, manifest, pin)
                receipt.update(
                    status="COMPLETE",
                    manifest_sha256=pin,
                    counts=manifest["counts"],
                    output=f"jobs/{job['id']}",
                )
            except Exception as error:
                # Keep source data and native error detail out of generic status receipts.
                receipt.update(
                    status="FAILED",
                    error_code="ACTIVITY_JOB_FAILED",
                    error_type=type(error).__name__,
                    error_message="Activity failed; inspect retained inputs and prior outputs.",
                    failure_stage=stage,
                )
                stopped = True
        _write(destination / "events" / f"{prefix}-result.json", _bytes(receipt))
        summary["jobs"].append(receipt)
    summary["status"] = "FAILED" if stopped else "COMPLETE"
    summary["counts"] = {
        s: sum(j["status"] == s for j in summary["jobs"]) for s in ("COMPLETE", "FAILED", "NOT_RUN")
    }
    _write(destination / "RECEIPT.json", _bytes(summary))
    # Explicit known run members and job manifest pins, without filesystem discovery.
    members = {
        "PLAN.json": summary["plan_sha256"],
        "RECEIPT.json": hashlib.sha256(_bytes(summary)).hexdigest(),
    }
    for index, receipt in enumerate(summary["jobs"]):
        prefix = f"{index:02d}-{receipt['id']}"
        names = [f"events/{prefix}-started.json", f"events/{prefix}-result.json"]
        if "dependency" in receipt:
            names.append(f"events/{prefix}-dependency.json")
        if "resolved_recipe_sha256" in receipt:
            names.append(f"recipes/{receipt['id']}.json")
        if "manifest_sha256" in receipt:
            names.append(f"jobs/{receipt['id']}/MANIFEST.json")
        for name in names:
            members[name] = hashlib.sha256(_read(destination / name)).hexdigest()
    _write(
        destination / "MANIFEST.json",
        _bytes({"format": "PRIVATE_ACTIVITY_PLAN_MANIFEST_V1", "members": members}),
    )
    return summary
