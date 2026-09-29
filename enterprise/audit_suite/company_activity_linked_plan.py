"""V2 existing pinned source routing; no producer-output derivation or audit activity."""

import copy
import hashlib
from pathlib import Path

from .company_activity_plan import (
    ID,
    MAX_JOBS,
    MAX_PLAN_BYTES,
    _bytes,
    _parse,
    _private,
    _recipe,
    _verify_job,
    _write,
    operator,
)
from .company_store import CompanyStoreError

FORMAT = "PRIVATE_COMPANY_ACTIVITY_LINKED_PLAN_V2"
SELECTED = {
    "identity-lifecycle",
    "nonhuman-identity",
    "risk-assessment",
    "access-remediation",
    "access-review-continuation",
}
KINDS = {
    "mover",
    "identity-period",
    "incident",
    "backup",
    "training",
    "change",
    "provider-intake",
} | SELECTED


def _read(path):
    from .company_activity_plan_sources import _file

    return _file(Path(path), limit=MAX_PLAN_BYTES, retain=True)[2]


def _verify_completed(value):
    directory, manifest, expected = value
    raw = _read(directory / "MANIFEST.json")
    if hashlib.sha256(raw).hexdigest() != expected or _parse(raw) != manifest:
        raise CompanyStoreError("Completed dependency manifest changed")
    _verify_job(directory, manifest)


def _pin(value):
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )


def _slots(job):
    recipe = job["recipe"]
    if job["kind"] == "access-review-continuation":
        groups = recipe["source_groups"]
        if len(groups) != 3 or {g["id"] for g in groups} != {
            "identity",
            "remediation_initial",
            "remediation_final",
        }:
            raise CompanyStoreError("Three exact access-review source groups required")
        return {g["id"]: g for g in groups}, recipe["population_at"]
    if job["kind"] == "risk-assessment":
        groups = recipe["source_groups"]
        if len(groups) != 4 or {g["id"] for g in groups} != {
            "incident",
            "provider",
            "log",
            "change",
        }:
            raise CompanyStoreError("Four exact risk source groups required")
        return {g["id"]: g for g in groups}, recipe["input_at"]
    if job["kind"] == "access-remediation":
        return {"source": recipe}, recipe["input_at"]
    if job["kind"] in SELECTED:
        return {"source": recipe}, recipe[
            "request_at" if job["kind"] == "identity-lifecycle" else "period_start"
        ]
    return {}, None


def validate_plan(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"format", "inputs", "jobs"}
        or value["format"] != FORMAT
    ):
        raise CompanyStoreError("Exact existing-source V2 plan required")
    inputs, jobs = value["inputs"], value["jobs"]
    if (
        not isinstance(inputs, dict)
        or len(inputs) > 16
        or not isinstance(jobs, list)
        or not 1 <= len(jobs) <= MAX_JOBS
    ):
        raise CompanyStoreError("Bounded explicit inputs and ordered jobs required")
    physical = set()
    for key, entry in inputs.items():
        if (
            not isinstance(key, str)
            or not ID.fullmatch(key)
            or not isinstance(entry, dict)
            or set(entry) != {"root", "manifest_sha256"}
        ):
            raise CompanyStoreError("Exact named operator source input required")
        root = entry["root"]
        if (
            not isinstance(root, str)
            or not Path(root).is_absolute()
            or ".." in Path(root).parts
            or str(Path(root)) != root
            or not _pin(entry["manifest_sha256"])
        ):
            raise CompanyStoreError("Absolute source root and exact manifest SHA required")
        if root in physical:
            raise CompanyStoreError("Duplicate physical source inputs forbidden")
        physical.add(root)
    prior, used = {}, set()
    for job in jobs:
        if not isinstance(job, dict) or set(job) != {
            "id",
            "kind",
            "depends_on",
            "recipe",
            "sources",
        }:
            raise CompanyStoreError("Exact V2 job fields required; source_job is not supported")
        key, kind = job["id"], job["kind"]
        if (
            not isinstance(key, str)
            or not ID.fullmatch(key)
            or key in prior
            or not isinstance(kind, str)
            or kind not in KINDS
        ):
            raise CompanyStoreError("Distinct job ID and supported explicit kind required")
        deps = job["depends_on"]
        if (
            not isinstance(deps, list)
            or any(not isinstance(d, str) or d not in prior for d in deps)
            or len(set(deps)) != len(deps)
        ):
            raise CompanyStoreError("Distinct prior dependency IDs required")
        _recipe(job["recipe"], operator.KINDS[kind][0])
        slots, _ = _slots(job)
        mapping = job["sources"]
        if (
            not isinstance(mapping, dict)
            or set(mapping) != set(slots)
            or any(not isinstance(i, str) or i not in inputs for i in mapping.values())
        ):
            raise CompanyStoreError("Exact named source routing required")
        if kind == "access-review-continuation":
            if not (
                mapping["remediation_initial"]
                == mapping["remediation_final"]
                != mapping["identity"]
            ):
                raise CompanyStoreError(
                    "Review needs one identity input and one shared removal input"
                )
        elif len(set(mapping.values())) != len(mapping):
            raise CompanyStoreError("Source groups require distinct original stores")
        labels, roots = {}, {}
        for slot, recipe in slots.items():
            source = mapping[slot]
            label = recipe["source_store_id"]
            if (label in labels and labels[label] != source) or (
                source in roots and roots[source] != label
            ):
                raise CompanyStoreError(
                    "Producer labels must identify one explicit input consistently"
                )
            labels[label], roots[source] = source, label
            used.add(source)
        prior[key] = job
    if used != set(inputs):
        raise CompanyStoreError("Unused input roots are not permitted")
    return copy.deepcopy(value)


def _resolve(plan, job, destination):
    from .company_activity_plan_sources import resolve_source

    slots, at = _slots(job)
    receipts, source_roots = {}, {}
    for slot, recipe in slots.items():
        entry = plan["inputs"][job["sources"][slot]]
        root = Path(entry["root"])
        if destination.resolve().is_relative_to(root.parent.resolve()):
            raise CompanyStoreError("Plan output must be outside every original operator output")
        resolved = resolve_source(
            source_root=root,
            source_manifest_path=root.parent / "MANIFEST.json",
            expected_manifest_sha256=entry["manifest_sha256"],
            binding={
                "source_store_id": recipe["source_store_id"],
                "expected_records": recipe["source_refs"],
                "expected_selected_metadata_sha256": recipe["source_versions_sha256"],
            },
            consumed_at=at,
            destination=destination,
        )
        if resolved["source_versions_sha256"] != recipe["source_versions_sha256"]:
            raise CompanyStoreError("Resolved source differs from exact recipe")
        receipts[slot] = resolved["receipt"]
        source_roots[slot] = root
    return receipts, source_roots


def run(plan_path, destination, *, repository):
    plan_path, destination = Path(plan_path).absolute(), Path(destination).absolute()
    raw = _read(plan_path)
    plan = validate_plan(_parse(raw))
    _private(destination.parent, True)
    if destination.exists() or destination.is_symlink():
        raise CompanyStoreError("New destination required; no resume")
    if any(p.is_symlink() for p in destination.parents):
        raise CompanyStoreError("Nonsymlink output required")
    # All selected existing inputs must validate before any job/output is created.
    for job in plan["jobs"]:
        _resolve(plan, job, destination)
    destination.mkdir(mode=0o700)
    _write(destination / "PLAN.json", raw)
    for child in ("jobs", "recipes", "events"):
        (destination / child).mkdir(mode=0o700)
    summary = {
        "format": "PRIVATE_COMPANY_ACTIVITY_LINKED_RUN_V2",
        "status": "RUNNING",
        "plan_sha256": hashlib.sha256(raw).hexdigest(),
        "jobs": [],
        "audit_created": False,
        "grants_created": False,
        "models_invoked": False,
        "input_contract": "EXISTING_PINNED_OPERATOR_OUTPUTS_ONLY_NO_SOURCE_JOB",
        "snapshot_isolation": "PER_SOURCE_NOT_GLOBAL",
        "code_pins": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in {
                "runner": Path(__file__),
                "v1_helpers": Path(__file__).with_name("company_activity_plan.py"),
                "source_resolver": Path(__file__).with_name("company_activity_plan_sources.py"),
                "operator": Path(operator.__file__),
            }.items()
        },
        "limits": [
            "No coherent operating year or professional sufficiency implied.",
            "No automatic latest selection, derived source references, retry, or resume.",
        ],
    }
    completed = {}
    stopped = False
    members = {"PLAN.json": summary["plan_sha256"]}
    for index, job in enumerate(plan["jobs"]):
        prefix = f"{index:02d}-{job['id']}"
        receipt = {
            "id": job["id"],
            "kind": job["kind"],
            "depends_on": job["depends_on"],
            "status": "NOT_RUN" if stopped else "STARTED",
        }

        def retain(name, value):
            body = _bytes(value)
            _write(destination / name, body)
            members[name] = hashlib.sha256(body).hexdigest()

        retain(f"events/{prefix}-started.json", receipt)
        if not stopped:
            stage = "VERIFY_EXACT_INPUTS"
            try:
                for item in completed.values():
                    _verify_completed(item)
                sources, source_roots = _resolve(plan, job, destination)
                receipt["sources"] = sources
                receipt["dependency_manifest_sha256"] = {
                    d: completed[d][2] for d in job["depends_on"]
                }
                retain(f"events/{prefix}-sources.json", sources)
                recipe_path = destination / "recipes" / f"{job['id']}.json"
                retain(str(recipe_path.relative_to(destination)), job["recipe"])
                receipt["resolved_recipe_sha256"] = members[
                    str(recipe_path.relative_to(destination))
                ]
                output = destination / "jobs" / job["id"]
                stage = "RUN_NATIVE_OPERATOR"
                kwargs = {}
                if job["kind"] in operator.MULTI_SOURCE_KINDS:
                    kwargs["source_roots"] = source_roots
                elif job["kind"] in SELECTED:
                    kwargs["source_root"] = source_roots["source"]
                manifest = operator.run(
                    job["kind"], recipe_path, output, repository=Path(repository), **kwargs
                )
                stage = "VERIFY_OUTPUT_AND_INPUTS_AFTER_JOB"
                receipt["published_output"] = {
                    "path": f"jobs/{job['id']}",
                    "acceptance": "PENDING_OUTPUT_VERIFICATION",
                }
                published = _read(output / "MANIFEST.json")
                output_pin = hashlib.sha256(published).hexdigest()
                members[f"jobs/{job['id']}/MANIFEST.json"] = output_pin
                receipt["published_output"]["manifest_sha256"] = output_pin
                _verify_job(output, manifest)
                if _parse(published) != manifest:
                    raise CompanyStoreError("Published operator result differs")
                for item in completed.values():
                    _verify_completed(item)
                stage = "REVERIFY_ALL_COMPLETED_INPUTS"
                for prior_job in plan["jobs"]:
                    if prior_job["id"] in completed:
                        receipt["source_recheck_job"] = prior_job["id"]
                        _resolve(plan, prior_job, destination)
                stage = "VERIFY_OUTPUT_AND_INPUTS_AFTER_JOB"
                receipt.pop("source_recheck_job", None)
                after, _ = _resolve(plan, job, destination)
                # Recheck exact source/native/manifest pins after generation.
                receipt["post_run_sources"] = after
                pin = hashlib.sha256(published).hexdigest()
                receipt["published_output"]["acceptance"] = "VERIFIED"
                completed[job["id"]] = (output, manifest, pin)
                members[f"jobs/{job['id']}/MANIFEST.json"] = pin
                receipt.update(status="COMPLETE", manifest_sha256=pin, counts=manifest["counts"])
            except Exception as error:
                if "published_output" in receipt:
                    receipt["published_output"]["acceptance"] = "POSTCHECK_FAILED_NOT_DEPENDENCY"
                receipt.update(
                    status="FAILED",
                    failure_stage=stage,
                    error_code="LINKED_ACTIVITY_JOB_FAILED",
                    error_type=type(error).__name__,
                    error_message="Activity failed; inspect retained private inputs and receipts.",
                )
                stopped = True
        retain(f"events/{prefix}-result.json", receipt)
        summary["jobs"].append(receipt)
    summary["status"] = "FAILED" if stopped else "COMPLETE"
    summary["counts"] = {
        s: sum(j["status"] == s for j in summary["jobs"]) for s in ("COMPLETE", "FAILED", "NOT_RUN")
    }
    body = _bytes(summary)
    _write(destination / "RECEIPT.json", body)
    members["RECEIPT.json"] = hashlib.sha256(body).hexdigest()
    _write(
        destination / "MANIFEST.json",
        _bytes({"format": "PRIVATE_ACTIVITY_LINKED_MANIFEST_V2", "members": members}),
    )
    return summary
