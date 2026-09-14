"""Scoped private review references; no scenario answers enter learner projections."""

from __future__ import annotations

import hashlib
import os

from .generation import epoch_directory, read_plan, read_world, run_directory
from .store import DomainError, canonical, digest


def resolve(engine, state, papers, observable):
    controls = {c["id"]: c for c in state.get("controls", [])}
    refs, selected = set(), set()
    for paper in papers:
        latest = paper.get("versions", [{}])[-1]
        for item in (paper, latest):
            if item.get("control_id") in controls:
                selected.add(item["control_id"])
            selected.update(c for c in item.get("control_ids", []) if c in controls)
        refs.update(latest.get("evidence_ids", []))
        if latest.get("artifact_id"):
            refs.add(latest["artifact_id"])
    for artifact in state.get("artifacts", []):
        if artifact["id"] in refs:
            for item in (artifact, artifact.get("coverage", {}), artifact.get("source", {})):
                if item.get("control_id") in controls:
                    selected.add(item["control_id"])
    for request in state.get("requests", []):
        if (
            refs.intersection(request.get("artifact_ids", []))
            and request.get("control_id") in controls
        ):
            selected.add(request["control_id"])
    tasks = [t for t in state.get("tasks", []) if t.get("control_id") in selected]
    pack = engine.program_pack
    if pack and state["scope"].get("program_pack_digest") != pack.get("digest"):
        raise DomainError("Review program pack differs from scoped source", code="SOURCE_INTEGRITY")
    authorities = []
    for task in tasks:
        passage = {
            k: task[k]
            for k in (
                "id",
                "control_id",
                "frameworks",
                "requirement_id",
                "source",
                "source_refs",
                "procedure",
                "title",
                "objective",
                "acceptance_test",
                "source_sha256",
                "version",
                "source_status",
            )
            if k in task
        }
        if passage:
            authorities.append(passage)
    if pack:
        for program in state["scope"].get("programs", []):
            key = program if program in pack["selections"] else "baseline"
            entry = pack["selections"].get(key, {})
            for action in entry.get("actions", []):
                if selected.intersection(action.get("control_ids", [])):
                    authorities.append(
                        {
                            "program": program,
                            "access": "RETAINED_CANDIDATE",
                            "source_kind": "AUTHORED_SOURCE_DERIVED_PROCEDURE",
                            "passage": action,
                        }
                    )
    units, rubrics, omissions = [], [], []
    for epoch in range(state.get("generation_epoch", 0) + 1):
        directory = epoch_directory(engine, state["id"], epoch)
        world_path = directory / "world.json"
        if not world_path.exists():
            omissions.append({"epoch": epoch, "reason": "NO_FROZEN_WORLD"})
            continue
        previous = next(
            (h for h in state.get("scope_history", []) if h.get("generation_epoch") == epoch), {}
        )
        pin = (
            state.get("generation", {}).get("world_digest")
            if epoch == state.get("generation_epoch", 0)
            else previous.get("world_digest")
        )
        world = read_world(world_path, pin)
        if world.get("world_integrity_version") != 1 or not pin:
            raise DomainError(
                "Review requires pinned frozen world integrity", code="SOURCE_INTEGRITY"
            )
        for path in sorted(directory.glob("unit-*.json")):
            plan = read_plan(path)
            if plan.get("control_id") not in selected:
                continue
            if plan.get("plan_integrity_version") != 1:
                raise DomainError("Review requires frozen plan integrity", code="SOURCE_INTEGRITY")
            requests = [
                r
                for r in state.get("requests", [])
                if r.get("plan_epoch", 0) == epoch and r.get("control_id") == plan["control_id"]
            ]
            cases = plan.get("scenario_cases", [])
            units.append(
                {
                    "epoch": epoch,
                    "control_id": plan["control_id"],
                    "plan_sha256": plan["plan_sha256"],
                    "facts": plan.get("facts", []),
                    "events": plan.get("events", []),
                    "cases": cases,
                    "requests": [
                        {
                            k: r.get(k)
                            for k in (
                                "id",
                                "status",
                                "artifact_ids",
                                "scenario_released",
                                "scenario_progress",
                                "issued_at",
                                "followups",
                            )
                        }
                        for r in requests
                    ],
                    "observable_cutoff": state["simulated_at"],
                    "availability_rule": (
                        "Only delivered observable evidence may support criticism; unreleased "
                        "facts are not learner knowledge"
                    ),
                }
            )
            for case in cases:
                definition = case.get("bound_definition") or case.get("definition", {})
                for pin in definition.get("authority_source_pins", []):
                    relative = pin.get("path", "")
                    source_path = engine.repository / relative
                    if (
                        not relative.startswith(
                            "enterprise/generated/audit-suite/source-documents/"
                        )
                        or source_path.resolve() != source_path.absolute()
                        or not source_path.is_file()
                        or hashlib.sha256(source_path.read_bytes()).hexdigest() != pin.get("sha256")
                    ):
                        raise DomainError(
                            "Scoped authority source integrity failure", code="SOURCE_INTEGRITY"
                        )
                    authorities.append(
                        {
                            "source_kind": "RETAINED_PRIMARY_SOURCE",
                            "access": "LOCAL_BYTES_HASH_VERIFIED",
                            "version": definition.get("authority_edition", {}).get("version"),
                            "url": pin.get("url"),
                            "locator": pin.get("locator"),
                            "sha256": pin["sha256"],
                            "passage_status": (
                                "LOCATOR_PINNED; FULL_LICENSED_TEXT_NOT_AUTO_EXTRACTED"
                            ),
                        }
                    )
                rubrics.append(
                    {
                        "epoch": epoch,
                        "control_id": plan["control_id"],
                        "case_id": definition.get("id"),
                        "rubric": definition.get("rubric", {}),
                        "playable_paths": definition.get("playable_paths", []),
                        "trigger_status": case.get("trigger_status"),
                        "professional_status": "UNVALIDATED",
                    }
                )
    owners = {p for control in selected for p in controls[control].get("owner_ids", [])}
    layers = {
        "A_authority": {
            "program_versions": state["scope"].get("program_versions", {}),
            "program_pack_digest": pack.get("digest") if pack else None,
            "status": "SOURCE_DERIVED_TRAINING_NOT_LICENSED_CRITERIA_SUBSTITUTE",
            "access": "PROGRAM_PACK_RETAINED"
            if pack
            else "NO_RETAINED_PROGRAM_PACK; SCOPED_TASKS_ONLY",
            "passages": authorities,
            "missing": [] if authorities else ["NO_SCOPED_AUTHORITY_PASSAGES"],
        },
        "B_policy_organization": {
            "controls": [controls[c] for c in sorted(selected)],
            "people": [p for p in state.get("people", []) if p["id"] in owners],
            "organization_provenance": state.get("organization", {}).get("provenance"),
            "policy_status": "BOUND_CONTROL_AND_PROCEDURE_FACTS; UNRETAINED_POLICIES_NOT_INFERRED",
        },
        "C_scenario": {"units": units, "omissions": omissions, "cutoff": state["simulated_at"]},
        "D_rubric": {
            "cases": rubrics,
            "status": "UNVALIDATED",
            "rule": (
                "Evidence-supported alternatives and legitimate samples that miss planted "
                "exceptions must not be penalized"
            ),
        },
        "E_observable": observable,
        "scope_resolution": {
            "control_ids": sorted(selected),
            "status": "RESOLVED" if selected else "UNRESOLVED_WORKPAPER_CONTROL_LINKS",
        },
    }
    return layers


def retain(engine, state, value):
    """Content-addressed private appendix outside state/history/public artifacts."""
    root = run_directory(engine, state["id"])
    directory = root / "review-inputs"
    if directory.is_symlink():
        raise DomainError("Private review directory alias rejected")
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.stat().st_mode & 0o077:
        raise DomainError("Private review directory permissions rejected")
    key = digest(value)
    path = directory / (key + ".json")
    data = (canonical(value) + "\n").encode()
    if path.exists():
        if path.is_symlink() or path.read_bytes() != data:
            raise DomainError("Private review appendix integrity failure")
    else:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
    return {"digest": key, "bytes": len(data), "audience": "REVIEWER_ONLY"}


def bounded(layers, budget=9500):
    """Include complete records only; every omitted record is counted and hashed."""
    result, omissions = {}, {}
    remaining = budget
    # E is separately supplied as citable sources; reserve budget for all A-D.
    for name in ("A_authority", "B_policy_organization", "C_scenario", "D_rubric"):
        value = layers[name]
        if name == "C_scenario":
            records = []
            for unit in value["units"]:
                base = {"epoch": unit["epoch"], "control_id": unit["control_id"]}
                for fact in unit["facts"]:
                    records.append({**base, "fact": fact})
                for case in unit["cases"]:
                    definition = case.get("bound_definition") or case.get("definition", {})
                    for fact in definition.get("facts", []):
                        records.append({**base, "fact": fact})
                    for event in definition.get("events", []):
                        records.append({**base, "event": event})
                for request in unit["requests"]:
                    records.append({**base, "observable_delivery": request})
            value = {
                "cutoff": value["cutoff"],
                "records": records,
                "rule": "Unreleased private facts are not learner knowledge",
            }
        if name == "B_policy_organization":
            value = {
                **value,
                "controls": [
                    {
                        k: v
                        for k, v in control.items()
                        if k
                        in {
                            "id",
                            "title",
                            "description",
                            "statement",
                            "objective",
                            "owner_ids",
                            "implementation_version",
                            "policy",
                            "procedure",
                            "source_refs",
                        }
                    }
                    for control in value["controls"]
                ],
            }
        encoded = canonical(value)
        allowance = min(remaining, budget // 4)
        if len(encoded) <= allowance:
            result[name] = value
            remaining -= len(encoded)
        else:
            summaries = {}
            omitted = 0
            for key, item in value.items():
                if isinstance(item, list):
                    summaries[key] = []
                    for record in item:
                        if (
                            len(canonical({**summaries, key: summaries[key] + [record]}))
                            <= allowance
                        ):
                            summaries[key].append(record)
                        else:
                            omitted += 1
                elif len(canonical({**summaries, key: item})) <= allowance:
                    summaries[key] = item
                else:
                    omitted += 1
            result[name] = summaries
            omissions[name] = {
                "omitted_records": omitted,
                "full_layer_digest": digest(layers[name]),
                "model_projection_digest": digest(value),
            }
    return result, omissions
