"""Observable-work extraction and experimental review, with human review primary."""

from __future__ import annotations

import json
from pathlib import Path

from .inference import WARNING, LocalInference
from .store import DomainError, digest, identifier

PARSER_VERSION = "audit-review-1"


def extract(manifest: dict, data: bytes) -> dict:
    from .parser_sandbox import parse

    if manifest.get("status") != "AVAILABLE":
        return {"artifact_id": manifest["id"], "status": "QUARANTINED", "sources": []}
    return parse("extract", manifest, data)


def deterministic_checks(state: dict) -> list[dict]:
    available = {m["id"] for m in state["artifacts"]}
    results = []
    for workpaper in state["workpapers"]:
        for version in workpaper["versions"]:
            refs = list(version.get("evidence_ids") or [])
            if version.get("artifact_id"):
                refs.append(version["artifact_id"])
            missing = sorted(set(refs) - available)
            results.append(
                {
                    "id": workpaper["id"] + ":" + str(version["version"]),
                    "check": "REFERENCES_EXIST_IN_ENGAGEMENT",
                    "status": "MISSING_REFERENCE" if missing else "VERIFIED_IDENTIFIERS",
                    "missing_ids": missing,
                    "professional_sufficiency": "NOT_ASSERTED",
                }
            )
    populations = {p["id"]: p for p in state["populations"]}
    for selection in state["selections"]:
        population = populations.get(selection["population_id"])
        supplied = {r["id"] for r in population["rows"]} if population else set()
        missing = sorted(
            set(selection["selected_ids"] + selection.get("targeted_ids", [])) - supplied
        )
        results.append(
            {
                "id": selection["id"],
                "check": "SELECTION_REFERENCES_SUPPLIED_POPULATION",
                "status": "MISSING_REFERENCE"
                if missing or not population
                else "VERIFIED_IDENTIFIERS",
                "missing_ids": missing,
                "hidden_population_used": False,
                "professional_sufficiency": "NOT_ASSERTED",
            }
        )
    from .deterministic_review import checks

    return results + checks(state)


def prepare(
    state: dict, artifacts, *, selected_workpapers: list[str] | None = None, engine=None
) -> dict:
    if selected_workpapers is not None and (
        not isinstance(selected_workpapers, list)
        or any(not isinstance(x, str) for x in selected_workpapers)
    ):
        raise DomainError("Workpaper selection must be an array of identifiers")
    selected = set(selected_workpapers or [w["id"] for w in state["workpapers"]])
    if len(selected) > 20:
        raise DomainError("Review at most 20 selected workpapers per request")
    known = {w["id"] for w in state["workpapers"]}
    if not selected <= known or not selected:
        raise DomainError("Select existing workpapers for experimental review")
    papers = [w for w in state["workpapers"] if w["id"] in selected]
    relevant = set()
    sources = []
    for paper in papers:
        latest = paper["versions"][-1] if paper["versions"] else {}
        refs = list(latest.get("evidence_ids") or [])
        if latest.get("artifact_id"):
            refs.append(latest["artifact_id"])
        relevant.update(refs)
        sources.append(
            {
                "id": paper["id"] + ":version:" + str(latest.get("version", 0)),
                "locator": "workpaper version",
                "text": json.dumps(latest)[:6000],
                "text_truncated": len(json.dumps(latest)) > 6000,
                "full_text_characters": len(json.dumps(latest)),
                "full_text_digest": digest(latest),
                "kind": "LEARNER_WORK",
            }
        )
    extraction = []
    for manifest in state["artifacts"]:
        if manifest["id"] in relevant and manifest.get("audience", "LEARNER") == "LEARNER":
            result = extract(manifest, artifacts.read(manifest))
            extraction.append({k: v for k, v in result.items() if k != "sources"})
            extraction[-1]["source_location_count"] = len(result["sources"])
            sources.extend(result["sources"])
    # Retain a complete extraction index separately; explicitly disclose bounded
    # model context rather than pretending every file/cell was model-reviewed.
    included, size = [], 0
    for source in sources:
        encoded = json.dumps(source)
        if size + len(encoded) > 8000 or len(included) >= 20:
            continue
        included.append(source)
        size += len(encoded)
    prepared = {
        "observable_layer": {
            "workpaper_ids": sorted(selected),
            "sources": included,
            "omitted_source_locations": len(sources) - len(included),
        },
        "extractions": extraction,
        "checks": deterministic_checks({**state, "workpapers": papers}),
    }
    if engine is not None:
        from .review_layers import bounded, resolve, retain

        layers = resolve(engine, state, papers, prepared["observable_layer"])
        model_layers, omissions = bounded(layers)
        private = {
            "layers": layers,
            "model_layers": model_layers,
            "omissions": omissions,
            "citable_source_ids": [s["id"] for s in included],
        }
        pin = retain(engine, state, private)
        prepared["five_layer_review"] = {
            "input_appendix": pin,
            "layers": list(layers)[:5],
            "scope_resolution": layers["scope_resolution"],
            "context_omissions": omissions,
            "channels": (
                "Private five-layer instructor review; separate observable-only learner feedback"
            ),
            "professional_status": "UNVALIDATED",
        }
        # Internal only: callers use public_prepared before storing state.
        prepared["_private"] = private
    else:
        prepared["five_layer_review"] = {"status": "UNAVAILABLE_WITHOUT_SCOPED_ENGINE"}
    return prepared


def public_prepared(prepared):
    return {key: value for key, value in prepared.items() if key != "_private"}


def run(state: dict, artifacts, config: Path, consent: dict, *, engine=None) -> dict:
    if consent.get("experimental_consent") is not True:
        raise DomainError("Experimental review requires explicit informed opt-in", status=403)
    prepared = prepare(
        state, artifacts, selected_workpapers=consent.get("workpaper_ids"), engine=engine
    )
    if consent.get("input_digest") != digest(public_prepared(prepared)):
        raise DomainError(
            "Review inputs changed; inspect the source list and consent again", status=409
        )
    source_ids = [s["id"] for s in prepared["observable_layer"]["sources"]]
    context = {
        "allowed_roles": ["experimental_reviewer"],
        "experimental_consent": True,
        "source_ids": source_ids,
        "observable_source_ids": source_ids,
        "sources": prepared["observable_layer"]["sources"],
        "scope": {k: state["scope"][k] for k in ("programs", "period_start", "period_end")},
        "review_boundary": {
            "status": "UNVALIDATED",
            "rule": (
                "Evidence-supported alternatives are valid. A legitimate sample may miss "
                "planted exceptions; never penalize that fact."
            ),
        },
        "limitations": {
            "omitted_source_locations": prepared["observable_layer"]["omitted_source_locations"],
            "hidden_truth": "Not supplied; do not infer it",
            "five_layer_channel": (
                "Private review is separate; private reviewer prose is not supplied here"
            ),
        },
    }
    private_result_pin = None
    if engine is not None:
        from .review_layers import retain

        private = prepared["_private"]
        private_context = {
            **context,
            "private_five_layers": private["model_layers"],
            "private_layer_omissions": private["omissions"],
            "review_channel": (
                "INSTRUCTOR_ONLY; never treat unreleased private facts as learner knowledge"
            ),
        }
        private_result = LocalInference(config).generate(
            "experimental_reviewer",
            private_context,
            [
                {
                    "role": "user",
                    "content": (
                        "Use the actual five scoped layers to review submitted work for an "
                        "instructor. Private facts and rubrics explain the case, not learner "
                        "obligations. Judge only obtainable observable evidence. Do not penalize "
                        "a legitimate sample that misses a planted exception. Cite only supplied "
                        "observable source IDs. Preserve alternatives and unresolved source "
                        "access. No whole-audit grade."
                    ),
                }
            ],
        )
        private_result_pin = retain(
            engine,
            state,
            {
                "input_digest": digest(public_prepared(prepared)),
                "input_appendix": prepared["five_layer_review"]["input_appendix"],
                "context": private_context,
                "result": private_result,
                "model": LocalInference(config).model,
                "warning": WARNING,
                "audience": "REVIEWER_ONLY",
                "automatic_training": False,
            },
        )
    result = LocalInference(config).generate(
        "experimental_reviewer",
        context,
        [
            {
                "role": "user",
                "content": (
                    "Review only this observable submitted work. Cite exact supplied locations, "
                    "identify uncertainty and alternatives. Do not assign a whole-audit "
                    "grade or infer unperformed work."
                ),
            }
        ],
    )
    return {
        "id": identifier("AI-REVIEW"),
        "kind": "EXPERIMENTAL_AI",
        "warning": WARNING,
        "input_digest": digest(public_prepared(prepared)),
        "input_layers": public_prepared(prepared),
        "private_review_appendix": private_result_pin,
        "result": result,
        "status": "SUGGESTIONS_ONLY",
        "appeals": [],
        "human_acceptance": "NOT_REVIEWED",
        "automatic_training": False,
        "whole_audit_grade": None,
    }
