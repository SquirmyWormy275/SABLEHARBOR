"""Private, instructor-reviewed custom authoring; no model result becomes canon."""

from __future__ import annotations

import json
import os
import re

from .configuration import selector_catalog
from .corpus import validate_bound_variant
from .generation import run_directory
from .inference import LocalInference
from .store import DomainError, canonical, digest, identifier


def read(engine, state, draft_id):
    if not isinstance(draft_id, str) or not re.fullmatch(r"CUSTOM-[a-f0-9]{24}", draft_id):
        raise DomainError("Invalid private draft identity")
    metadata = next((d for d in state.get("custom_drafts", []) if d["id"] == draft_id), None)
    if metadata is None:
        raise DomainError("Unknown custom draft", status=404)
    path = run_directory(engine, state["id"]) / "custom-drafts" / (draft_id + ".json")
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise DomainError("Private draft storage is unavailable")
    value = json.loads(path.read_text())
    if digest(value["variant"]) != metadata["variant_digest"] or (
        metadata.get("wrapper_digest") and digest(value) != metadata["wrapper_digest"]
    ):
        raise DomainError("Private draft digest changed")
    return value


def composition_source_plan(engine, state, control):
    from .clean import build_control

    names = {person["id"]: person["name"] for person in state["people"]}
    if len(state["scope"]["boundaries"]) != 1:
        raise DomainError("Independent Custom packets currently require one explicit boundary")
    return build_control(
        control,
        control["assignment"],
        {
            **state["scope"],
            "boundary_id": state["scope"]["boundaries"][0],
            "owner_names": names,
            "owner": names[control["assignment"]["primary_person_id"]],
            "repository": str(engine.repository),
        },
        private_root=engine.corpus_root / "clean",
    )


def validated_encounter(variant, control, state):
    """Retain only explicit instructor-authored, scoped encounter identities."""
    from .encounters import pool

    contract = variant.get("binding_contract", {}).get("encounter")
    if not isinstance(contract, dict):
        raise DomainError("Encounter contract must be an object")
    common = {"kind", "purpose"}
    allowed = common | (
        {"participant_roles", "require_distinct_participants"}
        if variant["selector_id"] == "MM-08"
        else {"provider_identity", "participant_roles"}
    )
    if set(contract) - allowed:
        raise DomainError("Unsupported encounter contract fields")
    if (
        "require_distinct_participants" in contract
        and contract["require_distinct_participants"] is not True
    ):
        raise DomainError("Owner encounters require distinct participants")
    if variant["selector_id"] == "MM-09":
        if contract.get("participant_roles", ["custodian_person_id"]) != ["custodian_person_id"]:
            raise DomainError("Provider encounter requires its scoped custodian")
        provider = contract.get("provider_identity")
        if not isinstance(provider, dict) or set(provider) != {
            "id",
            "name",
            "relationship",
            "origin",
        }:
            raise DomainError("Provider identity fields must be explicit")
    units = [
        {"control_id": control["id"], "boundary_id": boundary}
        for boundary in state["scope"]["boundaries"]
    ]
    resolved = pool(variant, units, [control], state["people"])
    if not resolved["encounters"] or resolved["excluded"]:
        raise DomainError("Encounter participants do not resolve in the current scope")
    return json.loads(canonical(contract))


def prepare(engine, state, kind, payload):
    if state["phase"] != "CONFIGURING":
        raise DomainError("Custom authoring requires a configuring engagement")
    if kind == "scenario.custom.accept":
        value = read(engine, state, payload.get("draft_id"))
        if payload.get("accept") is not True:
            raise DomainError("Explicit instructor acceptance is required")
        if value["scope_digest"] != digest(state["scope"]):
            raise DomainError("Scope changed; author and validate a new draft")
        if value["validation"].get("status") != "PASS" or value["critic"].get("observations"):
            raise DomainError(
                "Resolve bounded validation and critic observations before acceptance"
            )
        if value["variant"].get("binding_contract", {}).get("causal_composition"):
            from .causal_composition import pin_contract

            control = next(
                c for c in state["controls"] if c["id"] == value["bindings"]["control_id"]
            )
            pin_contract(
                composition_source_plan(engine, state, control),
                {
                    "definition": value["variant"],
                    "parameters": next(
                        (
                            selection.get("parameters", {})
                            for selection in state["configuration"]["selections"]
                            if selection["selector_id"] == value["variant"]["selector_id"]
                            and selection.get("option_id", "")
                            == value["variant"].get("option_id", "")
                        ),
                        {},
                    ),
                },
                control,
                {**state["scope"], "boundary_id": value["bindings"]["boundary"]},
            )
        return {"id": payload["draft_id"], "accept": True}
    if kind not in {"scenario.custom.author", "scenario.custom.edit"}:
        raise DomainError("Unknown custom authoring command")
    if not engine.inference_config:
        raise DomainError("Local custom authoring model is not configured", status=503)
    selected = next(
        (
            s
            for s in state["configuration"]["selections"]
            if s["selector_id"] == payload.get("selector_id")
            and s.get("option_id", "") == payload.get("option_id", "")
            and s["authoring_mode"] == "CUSTOM"
        ),
        None,
    )
    if selected is None:
        raise DomainError("Select this option in Custom mode before authoring")
    text = payload.get("text", selected.get("custom_text", ""))
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 8000:
        raise DomainError("Describe the custom case in up to 8000 characters")
    control = next((c for c in state["controls"] if c["id"] == payload.get("control_id")), None)
    if control is None:
        raise DomainError("Choose a control from the agreed engagement scope")
    people = {p["id"]: p["name"] for p in state["people"]}
    assignment = control["assignment"]
    bindings = {
        role: people.get(assignment.get(key), "")
        for role, key in (
            ("owner", "primary_person_id"),
            ("reviewer", "operating_reviewer_person_id"),
            ("custodian", "custodian_person_id"),
        )
    }
    if not all(bindings.values()):
        raise DomainError("Resolve scoped owner, reviewer and custodian before authoring")
    bindings.update(
        control_id=control["id"],
        boundary=state["scope"]["boundaries"][0],
        period_start=state["scope"]["period_start"],
        period_end=state["scope"]["period_end"],
    )
    draft_id = identifier("CUSTOM")
    provider = LocalInference(engine.inference_config)
    context = {
        "allowed_roles": ["custom_authoring"],
        "source_ids": [],
        "scope": state["scope"],
        "bindings": bindings,
        "variant_identity": {
            "id": draft_id,
            "selector_id": selected["selector_id"],
            "option_id": selected.get("option_id", ""),
        },
    }
    prior_id = payload.get("prior_draft_id")
    if prior_id:
        prior = read(engine, state, prior_id)
        if (prior["variant"]["selector_id"], prior["variant"].get("option_id", "")) != (
            selected["selector_id"],
            selected.get("option_id", ""),
        ):
            raise DomainError("Prior draft belongs to another selector option")
        context["prior_draft"] = prior["variant"]
        context["prior_critic"] = prior["critic"]
        context["revision_instruction"] = (
            "Preserve prior facts and evidence except changes required by this correction, "
            "current bindings or identified defects. Explain uncertainty; do not silently "
            "replace the scenario. The new server identity is mandatory."
        )
    if kind == "scenario.custom.edit":
        if not prior_id or not isinstance(payload.get("variant"), dict):
            raise DomainError("Editing requires an existing private draft and a full draft object")
        variant = json.loads(canonical(payload["variant"]))
        if (variant.get("selector_id"), variant.get("option_id", "")) != (
            selected["selector_id"],
            selected.get("option_id", ""),
        ):
            raise DomainError("An edited draft must retain its selector option")
        variant["id"] = draft_id
        variant.setdefault("rubric", {})["professional_validation"] = "UNVALIDATED"
    else:
        result = provider.author_variant(context, [{"role": "user", "content": text}])
        variant = result["variant"]
    edited_composition = (
        variant.get("binding_contract", {}).get("causal_composition")
        if kind == "scenario.custom.edit"
        else None
    )
    edited_encounter = (
        variant.get("binding_contract", {}).get("encounter")
        if kind == "scenario.custom.edit"
        else None
    )
    if edited_encounter is not None:
        edited_encounter = validated_encounter(variant, control, state)
    variant["binding_contract"] = {"applicable_control_ids": [control["id"]]}
    if edited_encounter is not None:
        variant["binding_contract"]["encounter"] = edited_encounter
    if edited_composition is not None:
        from .causal_composition import pin_contract

        variant["binding_contract"]["causal_composition"] = edited_composition
        variant["binding_contract"]["causal_composition"] = pin_contract(
            composition_source_plan(engine, state, control),
            {"definition": variant, "parameters": selected.get("parameters", {})},
            control,
            {**state["scope"], "boundary_id": bindings["boundary"]},
        )
    validation = validate_bound_variant(variant, bindings, state["scope"])
    critic = provider.generate(
        "coherence_critic",
        {
            "allowed_roles": ["coherence_critic"],
            "source_ids": ["CUSTOM-DRAFT", "AUTHOR-INTENT"],
            "sources": [
                {"id": "CUSTOM-DRAFT", "value": variant},
                {"id": "AUTHOR-INTENT", "text": text},
            ],
            "scope": state["scope"],
            "validation": validation,
            "selector_definition": next(
                s for s in selector_catalog() if s["id"] == selected["selector_id"]
            ),
            "temporal_release_policy": (
                "Custom case originals withheld until period_end; "
                "no future facts or retroactive authorization."
            ),
        },
        [
            {
                "role": "user",
                "content": (
                    "Evaluate authoring coherence, not whether the "
                    "intentionally injected problem exists. "
                    "Intended missing evidence or control exceptions are not authoring defects. "
                    "Report only contradictions, selector mismatch, unsupported chronology or "
                    "unplayable conclusions as unresolved observations. "
                    "Check exact selector fit, apparent-fraud trigger if applicable, "
                    "deviation counts, actor identity, chronology, "
                    "no retroactive authorization, causal "
                    "coherence and evidence-backed playable conclusions. Report each "
                    "unresolved defect as an observation; do not grade an audit or "
                    "accept this draft."
                ),
            }
        ],
    )
    value = {
        "variant": variant,
        "bindings": bindings,
        "scope_digest": digest(state["scope"]),
        "variant_digest": digest(variant),
        "validation": validation,
        "critic": critic,
    }
    root = run_directory(engine, state["id"]) / "custom-drafts"
    root.mkdir(mode=0o700, exist_ok=True)
    path = root / (draft_id + ".json")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(canonical(value))
    return {
        "id": draft_id,
        "private_ref": path.name,
        "predecessor_id": prior_id,
        "selector_id": selected["selector_id"],
        "option_id": selected.get("option_id", ""),
        "status": "REVIEW_REQUIRED",
        "variant_digest": value["variant_digest"],
        "wrapper_digest": digest(value),
        "scope_digest": value["scope_digest"],
        "bounded_validation": validation["status"],
        "critic_observations": len(critic["observations"]),
    }


def apply(state, kind, result):
    if kind in {"scenario.custom.author", "scenario.custom.edit"}:
        state.setdefault("custom_drafts", []).append(result)
    else:
        draft = next(d for d in state["custom_drafts"] if d["id"] == result["id"])
        draft["status"] = "ACCEPTED"
        for selected in state["configuration"]["selections"]:
            if (selected["selector_id"], selected.get("option_id", "")) == (
                draft["selector_id"],
                draft["option_id"],
            ):
                selected["draft_id"] = draft["id"]
