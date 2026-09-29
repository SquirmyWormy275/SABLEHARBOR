"""V3 explicit selected producer routing with once-captured, frozen metadata bindings."""

import copy
import hashlib
from pathlib import Path

from . import company_activity_linked_plan as v2
from .company_activity_linked_plan import (
    SELECTED,
    _bytes,
    _parse,
    _private,
    _read,
    _verify_completed,
    _verify_job,
    _write,
    operator,
)
from .company_activity_linked_plan import (
    _slots as _selected_slots,
)
from .company_lifecycle_activity import FIELDS
from .company_store import CompanyStoreError, _id

FORMAT = "PRIVATE_COMPANY_ACTIVITY_PRODUCER_PLAN_V3"
CAPTURE = "CAPTURE_VERIFIED_PRODUCER"
WHOLE_MODE = "CAPTURE_VERIFIED_CHANGE_STORE"
WHOLE_KINDS = {"configuration", "security-logging"}


def _slots(job):
    if job["kind"] in WHOLE_KINDS:
        return {"source": job["recipe"]}, None
    return _selected_slots(job)


def _whole_check(job, entry):
    from .company_activity_plan_sources import _manifest
    from .company_configuration_activity import read_originals

    root = Path(entry["root"])
    manifest, _ = _manifest(root.parent / "MANIFEST.json", entry["manifest_sha256"], root)
    if manifest.get("kind") != "change":
        raise CompanyStoreError("Whole change capture requires a verified change producer")
    rows, pin = read_originals(root)
    if {r["company"] for r in rows} != {job["recipe"]["company_id"]}:
        raise CompanyStoreError("Whole source company differs from consumer")
    _manifest(root.parent / "MANIFEST.json", entry["manifest_sha256"], root)
    return pin, len(rows)


def _native(group, company):
    refs = group.get("source_refs")
    if not isinstance(refs, list) or not 2 <= len(refs) <= 8:
        raise CompanyStoreError("Two to eight explicit exact native source references required")
    seen = set()
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != set(FIELDS):
            raise CompanyStoreError("Exact native six-field source reference required")
        for key in FIELDS[:4]:
            _id(ref[key])
        if type(ref["version"]) is not int or ref["version"] < 1 or not v2._pin(ref["sha256"]):
            raise CompanyStoreError("Exact positive native version and SHA required")
        identity = tuple(ref[k] for k in FIELDS[:-1])
        if identity in seen:
            raise CompanyStoreError("Duplicate native source identity")
        seen.add(identity)
    if len({(r["company"], r["branch"]) for r in refs}) != 1 or refs[0]["company"] != company:
        raise CompanyStoreError("One exact source company and branch matching consumer required")


def validate_plan(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"format", "inputs", "jobs"}
        or value["format"] != FORMAT
    ):
        raise CompanyStoreError("Exact selected producer V3 plan required")
    if not isinstance(value["inputs"], dict) or not isinstance(value["jobs"], list):
        raise CompanyStoreError("Explicit input map and job array required")
    original = copy.deepcopy(value)
    shadow = copy.deepcopy(value)
    shadow["format"] = v2.FORMAT
    prior = {}
    virtual = {}
    for index, job in enumerate(shadow["jobs"]):
        if not isinstance(job, dict) or set(job) != {
            "id",
            "kind",
            "depends_on",
            "recipe",
            "sources",
        }:
            raise CompanyStoreError("Exact V3 job fields required")
        if (
            not isinstance(job["id"], str)
            or not v2.ID.fullmatch(job["id"])
            or job["id"] in prior
            or not isinstance(job["kind"], str)
            or job["kind"] not in v2.KINDS | WHOLE_KINDS
        ):
            raise CompanyStoreError("Distinct supported job identities required")
        if not isinstance(job["sources"], dict) or not isinstance(job["recipe"], dict):
            raise CompanyStoreError("Explicit source routing and recipe required")
        try:
            groups, _ = _slots(job)
        except (KeyError, TypeError) as error:
            raise CompanyStoreError("Complete source recipe structure required") from error
        if set(groups) != set(job["sources"]):
            raise CompanyStoreError("Exact recipe source slots required")
        if job["kind"] in WHOLE_KINDS:
            route = job["sources"].get("source")
            if (
                not isinstance(route, dict)
                or set(route) != {"source_job", "metadata_mode"}
                or route["metadata_mode"] != WHOLE_MODE
                or not isinstance(route["source_job"], str)
                or route["source_job"] not in prior
                or not isinstance(job["depends_on"], list)
                or route["source_job"] not in job["depends_on"]
                or prior[route["source_job"]]["kind"] != "change"
            ):
                raise CompanyStoreError(
                    "Explicit prior change dependency and whole-store mode required"
                )
            v2._recipe(job["recipe"], operator.KINDS[job["kind"]][0], derived=True)
            producer = prior[route["source_job"]]
            if producer["recipe"]["company_id"] != job["recipe"]["company_id"]:
                raise CompanyStoreError("Whole-change producer company differs")
            prior[job["id"]] = original["jobs"][index]
            # V2 validates common identity/order semantics; native whole recipe validated above.
            job["kind"] = "change"
            job["recipe"] = copy.deepcopy(producer["recipe"])
            job["sources"] = {}
            continue
        routing = {}
        for slot, group in groups.items():
            _native(group, job["recipe"].get("company_id"))
            route = job["sources"][slot]
            if not isinstance(route, dict):
                raise CompanyStoreError("Explicit V3 source route object required")
            if set(route) == {"input_id"}:
                if "source_versions_sha256" not in group:
                    raise CompanyStoreError("Existing source metadata must be explicit")
                routing[slot] = route["input_id"]
            elif set(route) == {"source_job", "metadata_mode"}:
                source = route["source_job"]
                if (
                    route["metadata_mode"] != CAPTURE
                    or not isinstance(source, str)
                    or source not in prior
                    or not isinstance(job["depends_on"], list)
                    or source not in job["depends_on"]
                ):
                    raise CompanyStoreError("Captured source must name explicit prior dependency")
                if "source_versions_sha256" in group:
                    raise CompanyStoreError(
                        "Capture-mode selected metadata field must be omitted, not null or supplied"
                    )
                if prior[source]["recipe"].get("company_id") != job["recipe"].get("company_id"):
                    raise CompanyStoreError("Producer and consumer company differ")
                if source not in virtual:
                    key = f"captured-producer-{index}"
                    while key in shadow["inputs"]:
                        key += "x"
                    virtual[source] = key
                    shadow["inputs"][key] = {
                        "root": f"/__v3_producer__/{source}/company",
                        "manifest_sha256": "0" * 64,
                    }
                routing[slot] = virtual[source]
                group["source_versions_sha256"] = "0" * 64
            else:
                raise CompanyStoreError("Unsupported source routing fields or metadata mode")
        job["sources"] = routing
        prior[job["id"]] = original["jobs"][index]
    v2.validate_plan(shadow)
    return original


def _strict(job, bindings, destination):
    from .company_activity_plan_sources import resolve_source

    groups, at = _slots(job)
    if job["kind"] in WHOLE_KINDS:
        entry = bindings["source"]
        root = Path(entry["root"])
        if destination.resolve().is_relative_to(root.parent.resolve()):
            raise CompanyStoreError("Consumer must be outside original change producer directory")
        pin, count = _whole_check(job, entry)
        if pin != job["recipe"]["source_versions_sha256"]:
            raise CompanyStoreError("Frozen whole-change metadata differs")
        return {
            "source": {
                "schema": "FROZEN_WHOLE_CHANGE_BINDING_V1",
                "source_root": str(root),
                "source_manifest_sha256": entry["manifest_sha256"],
                "source_store_id": job["recipe"]["source_store_id"],
                "source_versions_sha256": pin,
                "source_versions": count,
                "availability": "NATIVE_CONSUMER_CHECKPOINT_EVENT_RULES",
                "snapshot_isolation": "WHOLE_CHANGE_STORE_NOT_GLOBAL",
            }
        }, {"source": root}
    receipts, roots = {}, {}
    for slot, group in groups.items():
        entry = bindings[slot]
        root = Path(entry["root"])
        resolved = resolve_source(
            source_root=root,
            source_manifest_path=root.parent / "MANIFEST.json",
            expected_manifest_sha256=entry["manifest_sha256"],
            binding={
                "source_store_id": group["source_store_id"],
                "expected_records": group["source_refs"],
                "expected_selected_metadata_sha256": group["source_versions_sha256"],
            },
            consumed_at=at,
            destination=destination,
        )
        receipts[slot] = resolved["receipt"]
        roots[slot] = root
    return receipts, roots


def _prepare(plan, job, completed, destination, *, preflight=False):
    from .company_activity_source_capture import capture_source

    resolved = copy.deepcopy(job)
    groups, at = _slots(resolved)
    bindings, captures = {}, {}
    for slot, group in groups.items():
        route = job["sources"][slot]
        if "input_id" in route:
            entry = copy.deepcopy(plan["inputs"][route["input_id"]])
        elif preflight:
            continue
        else:
            directory, _, pin = completed[route["source_job"]]
            _verify_completed(completed[route["source_job"]])
            entry = {"root": str(directory / "company"), "manifest_sha256": pin}
            if job["kind"] in WHOLE_KINDS:
                pin, count = _whole_check(resolved, entry)
                group["source_versions_sha256"] = pin
                captures[slot] = {
                    "schema": "CAPTURED_WHOLE_CHANGE_BINDING_V1",
                    "capture_basis": "EXPLICIT_V1_WHOLE_CHANGE_SNAPSHOT_MODE",
                    "capture_count": 1,
                    "source_versions_sha256": pin,
                    "source_versions": count,
                    "source_job": route["source_job"],
                    "source_manifest_sha256": entry["manifest_sha256"],
                    "availability": "NATIVE_CONSUMER_CHECKPOINT_EVENT_RULES",
                }
            else:
                result = capture_source(
                    source_root=directory / "company",
                    source_manifest_path=directory / "MANIFEST.json",
                    expected_manifest_sha256=pin,
                    source_store_id=group["source_store_id"],
                    expected_records=group["source_refs"],
                    consumed_at=at,
                    destination=destination,
                )
                group["source_versions_sha256"] = result["source_versions_sha256"]
                captures[slot] = result["receipt"]
        bindings[slot] = entry
    if preflight:
        # Only caller-pinned existing sources can be checked before future producers run.
        from .company_activity_plan_sources import resolve_source

        for slot, entry in bindings.items():
            group = groups[slot]
            root = Path(entry["root"])
            resolve_source(
                source_root=root,
                source_manifest_path=root.parent / "MANIFEST.json",
                expected_manifest_sha256=entry["manifest_sha256"],
                binding={
                    "source_store_id": group["source_store_id"],
                    "expected_records": group["source_refs"],
                    "expected_selected_metadata_sha256": group["source_versions_sha256"],
                },
                consumed_at=at,
                destination=destination,
            )
        return None
    receipts, roots = _strict(resolved, bindings, destination)
    return resolved, bindings, receipts, roots, captures


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
        _prepare(plan, job, {}, destination, preflight=True)
    destination.mkdir(mode=0o700)
    _write(destination / "PLAN.json", raw)
    for child in ("jobs", "recipes", "events"):
        (destination / child).mkdir(mode=0o700)
    summary = {
        "format": "PRIVATE_COMPANY_ACTIVITY_PRODUCER_RUN_V3",
        "status": "RUNNING",
        "plan_sha256": hashlib.sha256(raw).hexdigest(),
        "jobs": [],
        "audit_created": False,
        "grants_created": False,
        "models_invoked": False,
        "input_contract": "EXACT_NATIVE_REFS_OPTIONAL_FROZEN_METADATA_CAPTURE",
        "snapshot_isolation": "PER_SOURCE_NOT_GLOBAL",
        "code_pins": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in {
                "runner": Path(__file__),
                "v1_helpers": Path(__file__).with_name("company_activity_plan.py"),
                "v2_helpers": Path(v2.__file__),
                "source_capture": Path(__file__).with_name("company_activity_source_capture.py"),
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
    frozen = {}
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
                output = destination / "jobs" / job["id"]
                resolved_job, bindings, sources, source_roots, captures = _prepare(
                    plan, job, completed, output
                )
                frozen[job["id"]] = (resolved_job, bindings)
                receipt["source_captures"] = captures
                receipt["original_recipe_sha256"] = hashlib.sha256(
                    _bytes(job["recipe"])
                ).hexdigest()
                receipt["sources"] = sources
                receipt["dependency_manifest_sha256"] = {
                    d: completed[d][2] for d in job["depends_on"]
                }
                retain(f"events/{prefix}-sources.json", sources)
                recipe_path = destination / "recipes" / f"{job['id']}.json"
                retain(str(recipe_path.relative_to(destination)), resolved_job["recipe"])
                receipt["resolved_recipe_sha256"] = members[
                    str(recipe_path.relative_to(destination))
                ]
                output = destination / "jobs" / job["id"]
                stage = "RUN_NATIVE_OPERATOR"
                kwargs = {}
                if job["kind"] in operator.MULTI_SOURCE_KINDS:
                    kwargs["source_roots"] = source_roots
                elif job["kind"] in SELECTED | WHOLE_KINDS:
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
                        _strict(*frozen[prior_job["id"]], destination / "jobs" / prior_job["id"])
                stage = "VERIFY_OUTPUT_AND_INPUTS_AFTER_JOB"
                receipt.pop("source_recheck_job", None)
                after, _ = _strict(resolved_job, bindings, output)
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
        _bytes({"format": "PRIVATE_ACTIVITY_PRODUCER_MANIFEST_V3", "members": members}),
    )
    return summary
