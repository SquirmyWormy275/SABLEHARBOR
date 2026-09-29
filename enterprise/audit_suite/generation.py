"""Resumable generation; private world files are never an HTTP static directory."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from .artifacts import render
from .configuration import allocate_incomplete, rounded_count
from .corpus import Corpus
from .store import DomainError, canonical, digest, identifier


def private_json(path: Path, value: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.exists():
        if path.is_symlink():
            raise DomainError("Private scenario symlink rejected")
        return json.loads(path.read_text())
    data = (canonical(value) + "\n").encode()
    temporary = path.with_name(path.name + "." + secrets.token_hex(8) + ".pending")
    with temporary.open("xb") as handle:
        os.chmod(temporary, 0o600)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    # Atomic no-overwrite publication protects retry identity.
    try:
        os.link(temporary, path)
    except FileExistsError:
        pass
    finally:
        temporary.unlink()
    return json.loads(path.read_text())


def _private_subdirectory(parent: Path, name: str, anchor: Path) -> Path:
    """Create one directory without following aliases at either boundary."""
    child = parent / name
    if (
        parent.is_symlink()
        or child.is_symlink()
        or parent.resolve() != parent
        or child.resolve() != child
        or not child.is_relative_to(anchor)
    ):
        raise DomainError("Private run directory symlink or containment violation")
    try:
        # dir_fd and O_NOFOLLOW also prevent a swapped final directory component
        # from being followed during creation/verification.
        parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            try:
                os.mkdir(name, mode=0o700, dir_fd=parent_fd)
            except FileExistsError:
                pass
            child_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
            try:
                actual = os.fstat(child_fd)
                visible = child.lstat()
                if (
                    child.is_symlink()
                    or child.resolve() != child
                    or (actual.st_dev, actual.st_ino) != (visible.st_dev, visible.st_ino)
                ):
                    raise DomainError("Private run directory alias changed during access")
            finally:
                os.close(child_fd)
        finally:
            os.close(parent_fd)
    except OSError:
        raise DomainError("Private run directory is not an isolated regular directory") from None
    return child


def run_directory(engine, engagement_id: str) -> Path:
    if (
        not isinstance(engagement_id, str)
        or not engagement_id.startswith("ENG-")
        or any(c not in "ENG-0123456789abcdef" for c in engagement_id)
    ):
        raise DomainError("Invalid private run identity")
    anchor = Path(engine.store.root).absolute()
    if anchor.is_symlink() or anchor.resolve() != anchor or not anchor.is_dir():
        raise DomainError("Private run root symlink or containment violation")
    worlds = _private_subdirectory(anchor, "worlds", anchor)
    return _private_subdirectory(worlds, engagement_id, anchor)


def epoch_directory(engine, engagement_id: str, epoch: int = 0) -> Path:
    if type(epoch) is not int or epoch < 0:
        raise DomainError("Invalid generation epoch")
    root = run_directory(engine, engagement_id)
    if epoch:
        root = _private_subdirectory(root, f"scope-{epoch:05}", Path(engine.store.root).absolute())
    return root


def read_plan(path: Path) -> dict:
    if path.is_symlink():
        raise DomainError("Private plan symlink rejected")
    plan = json.loads(path.read_text())
    if plan.get("plan_integrity_version") == 1 and plan.get("plan_sha256") != digest(
        {k: v for k, v in plan.items() if k != "plan_sha256"}
    ):
        raise DomainError("Frozen evidence plan integrity failure", code="SOURCE_INTEGRITY")
    return plan


def read_world(path: Path, expected_digest: str | None = None) -> dict:
    if path.is_symlink():
        raise DomainError("Private world symlink rejected")
    world = json.loads(path.read_text())
    if world.get("world_integrity_version") == 1 and world.get("world_sha256") != digest(
        {k: v for k, v in world.items() if k != "world_sha256"}
    ):
        raise DomainError("Frozen world integrity failure", code="SOURCE_INTEGRITY")
    if expected_digest is not None and digest(world) != expected_digest:
        raise DomainError("Frozen world differs from retained generation", code="SOURCE_INTEGRITY")
    return world


def initialize_world(engine, state: dict) -> dict:
    root = epoch_directory(engine, state["id"], state.get("generation_epoch", 0))
    path = root / "world.json"
    if path.exists():
        world = read_world(path, state.get("generation", {}).get("world_digest"))
        if world["configuration_digest"] != digest([state["configuration"], state["scope"]]):
            raise DomainError(
                "Frozen world scope/configuration changed; create a versioned successor"
            )
        return world
    seed_record = private_json(
        root / "binding-seed.json",
        {
            "private_seed": secrets.token_hex(32),
            "configuration_digest": digest([state["configuration"], state["scope"]]),
        },
    )
    if seed_record["configuration_digest"] != digest([state["configuration"], state["scope"]]):
        raise DomainError(
            "A started generation needs an explicit successor for changed configuration"
        )
    seed = bytes.fromhex(seed_record["private_seed"])
    corpus = Corpus(engine.corpus_root)
    variants = []
    units = [
        {
            "control_id": control["id"],
            "boundary_id": boundary,
            "implementation_version": control["implementation_version"],
        }
        for control in state["controls"]
        for boundary in state["scope"]["boundaries"]
    ]
    incomplete = state["configuration"].get("incomplete_evidence")
    allocation = (
        allocate_incomplete(units, incomplete["overall"], incomplete["shares"], private_seed=seed)
        if incomplete
        else None
    )
    for selection in state["configuration"].get("selections", []):
        option = selection.get("option_id") or "MM-08.INTERNAL"
        if option == "MM-08":
            option = "MM-08.INTERNAL"
        if selection.get("authoring_mode", "STANDARD") == "CUSTOM":
            from .custom import read

            draft_id = selection.get("draft_id")
            metadata = next(
                (d for d in state.get("custom_drafts", []) if d["id"] == draft_id), None
            )
            if metadata is None or metadata["status"] != "ACCEPTED":
                raise DomainError(
                    "Accept a validated custom draft before generation", code="CUSTOM_PENDING"
                )
            wrapper = read(engine, state, draft_id)
            if wrapper["scope_digest"] != digest(state["scope"]) or metadata[
                "scope_digest"
            ] != digest(state["scope"]):
                raise DomainError("Accepted custom draft belongs to an earlier scope")
            variant = wrapper["variant"]
            if state["discipline"] not in variant["disciplines"]:
                raise DomainError(
                    "Accepted custom draft is incompatible with this audit discipline"
                )
            variant_option = variant["option_id"] or "MM-08.INTERNAL"
            if variant_option == "MM-08":
                variant_option = "MM-08.INTERNAL"
            if (variant["selector_id"], variant_option) != (selection["selector_id"], option):
                raise DomainError("Accepted draft belongs to a different scenario option")
            if (
                digest(variant) != metadata["variant_digest"]
                or wrapper["validation"]["status"] != "PASS"
                or wrapper["critic"]["observations"]
            ):
                raise DomainError("Custom draft acceptance no longer matches its validation")
        else:
            variant = corpus.select(
                option,
                seed,
                discipline=state["discipline"],
                control_ids={u["control_id"] for u in units},
                allow_portable_source=selection["selector_id"] == "MM-02",
                parameters=selection.get("parameters", {}),
            )
        compatible = set(variant["binding_contract"]["applicable_control_ids"])
        eligible = [u for u in units if u["control_id"] in compatible]
        eligible.sort(
            key=lambda u: hmac.new(seed, canonical([option, u]).encode(), hashlib.sha256).digest()
        )
        encounter_pool = None
        if selection["selector_id"] in {"MM-08", "MM-09"}:
            from .encounters import pool

            encounter_pool = pool(variant, eligible, state["controls"], state["people"])
            eligible = [record["unit"] for record in encounter_pool["encounters"]]
        parameters = selection.get("parameters", {})
        if selection["selector_id"] == "MM-02":
            if allocation is None:
                raise DomainError("Incomplete evidence requires an overall allocation and shares")
            assigned = [
                {k: v for k, v in u.items() if k != "option_id"}
                for u in allocation["assignments"]
                if u["option_id"] == option
            ]
        else:
            count = (
                rounded_count(
                    parameters["frequency"],
                    len(eligible),
                    positive_minimum=selection["selector_id"] == "MM-08",
                )
                if "frequency" in parameters
                else min(1, len(eligible))
            )
            if parameters.get("intensity") == 0:
                count = 0
            assigned = eligible[:count]
        variants.append(
            {
                "definition": variant,
                "parameters": selection.get("parameters", {}),
                "definition_digest": digest(variant),
                "eligible_count": len(units)
                if selection["selector_id"] == "MM-02"
                else len(eligible),
                "assigned_units": assigned,
                "encounter_pool": encounter_pool,
                "trigger_status": "PLANNED" if assigned else "SELECTED_NOT_TRIGGERED",
            }
        )
    clean_sources = {}
    for control in state["controls"]:
        source = engine.corpus_root / "clean" / (control["id"] + ".json")
        if not source.is_file() or source.is_symlink():
            raise DomainError("Missing private clean source for " + control["id"])
        data = source.read_bytes()
        frozen = root / "clean-source" / source.name
        private_json(frozen, json.loads(data))
        clean_sources[control["id"]] = {
            "original_sha256": hashlib.sha256(data).hexdigest(),
            "frozen_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
        }
    world = {
        "schema_version": 1,
        "origin": "SYNTHETIC",
        "private_seed": seed.hex(),
        "configuration_digest": digest([state["configuration"], state["scope"]]),
        "variants": variants,
        "incomplete_allocation": allocation,
        "clean_sources": clean_sources,
        "organization": state["organization"],
        "scope": state["scope"],
        "professional_rubric": "UNVALIDATED",
    }
    world["world_integrity_version"] = 1
    world["runtime_sources"] = {
        file.name: hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted(Path(__file__).parent.glob("*.py"))
    }
    world["world_sha256"] = digest(world)
    private_json(path, world)
    return read_world(path)


def step(engine, actor: str, engagement_id: str) -> dict:
    state = engine.store.get(actor, engagement_id)
    if state["phase"] != "GENERATING":
        return state
    index = state["generation"]["completed"]
    epoch = state.get("generation_epoch", 0)
    command = {
        "command_id": f"generation-step-{index}"
        if not epoch
        else f"generation-{epoch}-step-{index}",
        "expected_revision": state["revision"],
        "kind": "generation.progress",
        "payload": {"index": index},
    }

    def generate(s, c, who):
        if s["phase"] != "GENERATING":
            raise DomainError("Generation has been cancelled")
        world = initialize_world(engine, s)
        s["generation"]["world_digest"] = digest(world)
        s["trainer_encounter_counts"] = [
            {
                "selector_id": entry["definition"]["selector_id"],
                "option_id": entry["definition"]["option_id"],
                "basis": entry["encounter_pool"]["basis"],
                "eligible": len(entry["encounter_pool"]["encounters"]),
                "planned": len(entry["assigned_units"]),
                "excluded": len(entry["encounter_pool"]["excluded"]),
            }
            for entry in world["variants"]
            if entry.get("encounter_pool")
        ]
        units = [
            (control, boundary)
            for control in s["controls"]
            for boundary in s["scope"]["boundaries"]
        ]
        if index >= len(units):
            raise DomainError("Generation index exceeds scoped units")
        control, boundary = units[index]
        root = epoch_directory(engine, engagement_id, epoch)
        path = root / f"unit-{index:05}.json"
        if path.exists():
            plan = read_plan(path)
        else:
            from .clean import build_control

            people = {p["id"]: p["name"] for p in s["people"]}
            scope = {
                **s["scope"],
                "boundary_id": boundary,
                "owner_names": people,
                "owner": people[control["assignment"]["primary_person_id"]],
                "repository": str(engine.repository),
            }
            frozen_source = root / "clean-source" / (control["id"] + ".json")
            expected_source = world["clean_sources"][control["id"]]["frozen_sha256"]
            if (
                frozen_source.is_symlink()
                or frozen_source.resolve() != frozen_source.absolute()
                or hashlib.sha256(frozen_source.read_bytes()).hexdigest() != expected_source
            ):
                raise DomainError(
                    "Frozen company source integrity failure", code="SOURCE_INTEGRITY"
                )
            plan = build_control(
                control,
                control["assignment"],
                scope,
                private_root=root / "clean-source",
            )
            cases = [
                entry
                for entry in world["variants"]
                if any(
                    u["control_id"] == control["id"] and u["boundary_id"] == boundary
                    for u in entry["assigned_units"]
                )
            ]
            if cases:
                from .composition import compose_control

                # Delivery requires the server's event adapter, never unconditional
                # release of all pre-rendered private originals.
                if not getattr(engine, "scenario_delivery_ready", False):
                    raise DomainError(
                        "Scenario event delivery integration is pending",
                        code="COMPOSITION_IN_PROGRESS",
                    )
                plan = compose_control(plan, cases, control, scope, people)
            # Pre-render originals while generation progress is observable. They
            # remain private until a request and their availability time permit release.
            for request in plan["requests"]:
                manifests = []
                for item in request["artifact_recipes"]:
                    data, _ = render(item["recipe"])
                    manifest = engine.artifacts.retain(
                        engagement_id,
                        item["name"],
                        data,
                        source={
                            "kind": "SYNTHETIC_COMPANY_RECORD",
                            "control_id": control["id"],
                            "boundary_id": boundary,
                            "recipe_digest": digest(item["recipe"]),
                        },
                        coverage=request.get("coverage", s["scope"]),
                        generated=True,
                    )
                    manifests.append(
                        {
                            **manifest,
                            "available_at": item.get("available_by", request.get("available_by")),
                            **(
                                {"scenario_artifact_id": item["scenario_artifact_id"]}
                                if "scenario_artifact_id" in item
                                else {}
                            ),
                        }
                    )
                request["prepared_artifacts"] = manifests
            plan["plan_integrity_version"] = 1
            plan["plan_sha256"] = digest({k: v for k, v in plan.items() if k != "plan_sha256"})
            plan = private_json(path, plan)
        for request_index, request in enumerate(plan["requests"]):
            prefix = "PBC" if not epoch else f"PBC-E{epoch}"
            request_id = f"{prefix}-{index:05}-{request_index:03}"
            s["requests"].append(
                {
                    "id": request_id,
                    "title": request["title"],
                    "purpose": request.get("purpose", request["title"]),
                    "control_id": control["id"],
                    "boundary_id": boundary,
                    "person_id": control["assignment"]["custodian_person_id"],
                    "status": "DRAFT",
                    "history": [],
                    "artifact_ids": [],
                    "unread": False,
                    "coverage": request.get("coverage", s["scope"]),
                    "due_at": request.get("due_at"),
                    "plan_unit": index,
                    "plan_request": request_index,
                    "plan_epoch": epoch,
                    "scope_version": epoch,
                }
            )
        s["generation"]["completed"] = index + 1
        s["generation"]["stage"] = f"Prepared {index + 1} of {len(units)} control implementations"
        if index + 1 == len(units):
            s["phase"] = "ACTIVE" if s.pop("resume_active_after_generation", False) else "READY"
            s["generation"]["state"] = "COMPLETE"
            s["scope_reconciliation_required"] = False
        return s

    try:
        return engine.store.command(
            actor, engagement_id, command, generate, permissions={"learn", "instruct"}
        )
    except Exception as exc:
        # Keep the exact pending unit and useful error; an incomplete corpus is an
        # implementation error, not simulated uncooperative-company behavior.
        current = engine.store.get(actor, engagement_id)
        if current["phase"] != "GENERATING":
            return current
        failure = {
            "command_id": identifier("GENFAIL"),
            "expected_revision": current["revision"],
            "kind": "generation.failure",
            "payload": {"unit": index, "reason": str(exc)[:500]},
        }

        def fail(s, c, who):
            s["phase"] = "GENERATION_FAILED"
            s["generation"]["state"] = "FAILED"
            s["generation"]["errors"] = [c["payload"]["reason"]]
            return s

        return engine.store.command(
            actor, engagement_id, failure, fail, permissions={"learn", "instruct"}
        )


def request_plan(engine, state: dict, request: dict) -> dict | None:
    if "plan_unit" not in request:
        return None
    path = epoch_directory(engine, state["id"], request.get("plan_epoch", 0)) / (
        f"unit-{request['plan_unit']:05}.json"
    )
    plan = read_plan(path)
    return plan["requests"][request["plan_request"]]
