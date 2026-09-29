"""Generic private corpus validation and immutable run bindings.

Authored facts, mechanisms, recipes, rubrics and private seeds are supplied from
protected storage. This module contains no answer bank and exposes no HTTP route.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import re
from pathlib import Path

from .configuration import selector_catalog
from .store import DomainError, digest

OPERATIONS = {"release_artifact", "statement", "scope_change", "availability", "record_change"}
TERMINALS = {
    "SUPPORTED_CONCLUSION",
    "SUPPORTED_LIMITATION",
    "REMEDIATION_AND_RETEST",
    "QUALIFIED_FINDING",
}


def obligations() -> list[str]:
    ids = [
        f"{o['id']}.V{i:02}" for s in selector_catalog() for o in s["options"] for i in range(1, 11)
    ]
    return sorted(ids + [f"MM-08.INTERNAL.V{i:02}" for i in range(1, 11)])


def validate_variant(value: dict) -> dict:
    required = {
        "schema_version",
        "id",
        "option_id",
        "selector_id",
        "title",
        "disciplines",
        "applicability",
        "mechanism",
        "facts",
        "actor_knowledge",
        "artifacts",
        "events",
        "playable_paths",
        "rubric",
        "clean_counterpart",
        "source_refs",
    }
    missing = required - value.keys()
    if missing:
        raise DomainError("Variant missing fields: " + ", ".join(sorted(missing)))
    custom = bool(re.fullmatch(r"CUSTOM-[A-Za-z0-9-]{1,100}", value["id"]))
    if value["schema_version"] != "1.0" or (value["id"] not in obligations() and not custom):
        raise DomainError("Unsupported variant identity/version")
    if not custom and (
        not value["id"].startswith(value["option_id"] + ".")
        or value["selector_id"] != value["id"][:5]
    ):
        raise DomainError("Variant selector/option identity mismatch")
    options = {s["id"]: {o["id"] for o in s["options"]} for s in selector_catalog()}
    if value["selector_id"] not in options or (
        value["selector_id"] != "MM-08" and value["option_id"] not in options[value["selector_id"]]
    ):
        raise DomainError("Unknown scenario option")
    if not value["disciplines"] or not set(value["disciplines"]) <= {"IT", "FINANCIAL"}:
        raise DomainError("Variant requires disciplinary applicability")
    if any(not value["applicability"].get(d) for d in ("IT", "FINANCIAL")):
        raise DomainError("Both applicable and non-applicable disciplines need rationale")
    mechanism = value["mechanism"]
    if any(
        not mechanism.get(k)
        for k in ("cause", "process", "control_domains", "objective", "failure_type")
    ):
        raise DomainError("Incomplete causal mechanism")
    facts = {r["id"]: r for r in value["facts"]}
    artifacts = {r["id"]: r for r in value["artifacts"]}
    events = {r["id"]: r for r in value["events"]}
    if (
        not facts
        or len(facts) != len(value["facts"])
        or len(artifacts) != len(value["artifacts"])
        or len(events) != len(value["events"])
        or len(artifacts) < 2
    ):
        raise DomainError("Missing or duplicate fact/artifact/event identifiers")
    for fact in facts.values():
        if (
            not fact.get("statement")
            or fact.get("source_class") not in {"SYNTHETIC_SCENARIO_FACT", "FICTIONAL_POLICY"}
            or fact.get("visibility") not in {"PRIVATE", "ON_REQUEST"}
        ):
            raise DomainError("Invalid fact authority or visibility")
    if not value["actor_knowledge"]:
        raise DomainError("Variant requires scoped actor knowledge")
    for actor in value["actor_knowledge"]:
        if not actor.get("role_ref") or not set(actor.get("knows_fact_ids", [])) <= facts.keys():
            raise DomainError("Actor knowledge references missing facts")
        if not set(actor.get("allowed_actions", [])) <= OPERATIONS | {
            "respond",
            "request",
            "clarify",
        }:
            raise DomainError("Unsupported actor action")
    for artifact in artifacts.values():
        from .artifacts import safe_name

        if (
            not isinstance(artifact.get("name"), str)
            or safe_name(artifact["name"]) != artifact["name"]
        ):
            raise DomainError("Artifact requires a safe native filename")
        if custom:
            from datetime import date

            try:
                date.fromisoformat(artifact["available_on"])
            except (KeyError, TypeError, ValueError) as exc:
                raise DomainError("Custom artifacts require an ISO available_on date") from exc
        if artifact.get("stage") not in {"INITIAL", "FOLLOWUP"} or not artifact.get(
            "request_purpose"
        ):
            raise DomainError("Artifact requires request purpose and release stage")
        if artifact.get("recipe", {}).get("format") not in {
            "csv",
            "xlsx",
            "json",
            "pdf",
            "html",
            "log",
            "png",
            "txt",
        }:
            raise DomainError("Unsupported artifact recipe")
        recipe = artifact["recipe"]
        for row in recipe.get("rows", []):
            if set(row) != set(recipe.get("columns", [])):
                raise DomainError("Artifact row fields differ from its declared columns")
    for event in events.values():
        if event.get("trigger") not in {"REQUEST", "FOLLOWUP", "CLOCK"}:
            raise DomainError("Unsupported event trigger")
        if type(event.get("offset_business_days")) is not int or event["offset_business_days"] < 0:
            raise DomainError("Invalid event timing")
        if not event.get("effects"):
            raise DomainError("Event has no effect")
        for effect in event["effects"]:
            if effect.get("operation") not in OPERATIONS:
                raise DomainError("Unsupported event operation")
            if effect["operation"] == "release_artifact" and effect.get("target") not in artifacts:
                raise DomainError("Event references missing artifact")
    if not value["playable_paths"]:
        raise DomainError("No playable endpoint")
    for path in value["playable_paths"]:
        if (
            not path.get("actions")
            or path.get("terminal_state") not in TERMINALS
            or not path.get("rationale")
        ):
            raise DomainError("Incomplete playable path")
    rubric = value["rubric"]
    if rubric.get("professional_validation") not in {"UNVALIDATED", "EXPERT_REVIEWED", "DISPUTED"}:
        raise DomainError("Invalid professional validation status")
    if not all(
        rubric.get(k)
        for k in ("supported_conclusions", "acceptable_alternatives", "unsupported_guesses")
    ):
        raise DomainError("Rubric must preserve alternatives and unsupported-guess boundaries")
    return {
        "id": value["id"],
        "sha256": digest(value),
        "structural": "PASS",
        "playability": "NOT_RUN",
        "professional_rubric": rubric["professional_validation"],
    }


def bind_tokens(value: object, bindings: dict[str, str]) -> object:
    if isinstance(value, dict):
        return {k: bind_tokens(v, bindings) for k, v in value.items()}
    if isinstance(value, list):
        return [bind_tokens(v, bindings) for v in value]
    if isinstance(value, str):

        def replace(match):
            key = match.group(1)
            if key not in bindings:
                raise DomainError("Missing scenario binding: " + key)
            return str(bindings[key])

        return re.sub(r"\{\{([a-z_]+)\}\}", replace, value)
    return value


def validate_bound_variant(value: dict, bindings: dict[str, str], scope: dict) -> dict:
    """Check executable references and renderability in an actual engagement.

    These are bounded engineering checks, not a semantic oracle. Date anomalies
    require an explicit author/critic explanation: old or contradictory records can
    be intentional, but must not enter a custom world accidentally.
    """
    from datetime import date

    from .artifacts import render
    from .composition import advance_events, instant

    validate_variant(value)
    bindings = dict(bindings)
    bindings.setdefault(
        "artifact_title", value["artifacts"][0]["recipe"].get("title", "Source record")
    )
    bound = bind_tokens(value, bindings)
    errors, observations, renders, paths = [], [], [], []
    start = date.fromisoformat(scope["period_start"][:10])
    end = date.fromisoformat(scope["period_end"][:10])
    anchor = start.isoformat() + "T09:00:00+00:00"
    timezone = scope.get("timezone", "UTC")
    for artifact in bound["artifacts"]:
        if value["id"].startswith("CUSTOM-"):
            available = date.fromisoformat(artifact["available_on"])
            if not start <= available <= end:
                errors.append(
                    {
                        "artifact_id": artifact["id"],
                        "error": "Custom artifact availability is outside its authored period",
                    }
                )
        try:
            data, media_type = render(artifact["recipe"])
            renders.append(
                {
                    "artifact_id": artifact["id"],
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "media_type": media_type,
                }
            )
        except (DomainError, ValueError, TypeError, KeyError) as exc:
            errors.append({"artifact_id": artifact["id"], "error": str(exc)})
        # Only inspect evidence values; rubric prose may legitimately compare years.
        dates = set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", json.dumps(artifact["recipe"])))
        for text in sorted(dates):
            try:
                observed = date.fromisoformat(text)
            except ValueError:
                errors.append({"artifact_id": artifact["id"], "error": "Invalid date: " + text})
                continue
            if not start <= observed <= end:
                observations.append(
                    {
                        "artifact_id": artifact["id"],
                        "kind": "OUTSIDE_PERIOD",
                        "date": text,
                        "requires_author_explanation": True,
                    }
                )
    known_artifacts = {a["id"] for a in bound["artifacts"]}
    for path in bound["playable_paths"]:
        progress, released, inspected, now = None, set(), set(), anchor
        path_errors = []
        for action in path["actions"]:
            if action in {"REQUEST", "FOLLOWUP", "CLOCK"}:
                try:
                    progress, effects = advance_events(
                        bound, progress, trigger=action, now=now, timezone=timezone
                    )
                    # A path implicitly waits for its requested company's response;
                    # follow-up events remain unarmed until FOLLOWUP is encountered.
                    pending = [
                        at
                        for key, at in progress["armed"].items()
                        if key not in progress["completed"]
                    ]
                    if pending:
                        now = max(pending, key=instant)
                        progress, later = advance_events(
                            bound, progress, trigger="CLOCK", now=now, timezone=timezone
                        )
                        effects += later
                    released.update(
                        e["target"] for e in effects if e["operation"] == "release_artifact"
                    )
                except (DomainError, ValueError) as exc:
                    path_errors.append(str(exc))
            elif action.startswith("INSPECT:"):
                target = action.split(":", 1)[1]
                if target not in known_artifacts or target not in released:
                    path_errors.append(
                        "Inspection requires an actually released artifact: " + target
                    )
                inspected.add(target)
            # Explicit manual intentions are metadata only: they neither release
            # evidence nor execute inquiry or substantiate a professional conclusion.
            elif action not in {
                "DOCUMENT_CONCLUSION",
                "DOCUMENT_SCOPED_CONCLUSION",
                "REQUEST_MISSING_CORROBORATION",
                "REQUEST_PRIMARY_AUTHORITY_AND_APPLICABILITY_REVIEW",
                "DOCUMENT_LIMITATION",
                "RECORD_LIMITATION",
                "PRESERVE_ORIGINAL_RESPONSE",
                "REQUEST_DIRECT_CUSTODIAN_CLARIFICATION",
                "ESCALATE_DOCUMENTED_OBSTRUCTION",
                "REQUEST_QUALIFIED_AUTHORITY_REVIEW",
                "ESCALATE",
                "RETEST",
                "REMEDIATE",
                "ASSESS",
                "RECONCILE",
            }:
                path_errors.append("Unsupported executable path action: " + action)
        paths.append(
            {
                "path_id": path["id"],
                "status": "FAIL" if path_errors else "PASS",
                "released_count": len(released),
                "inspected_count": len(inspected),
                "errors": path_errors,
                "terminal_state": path["terminal_state"],
            }
        )
        errors.extend({"path_id": path["id"], "error": item} for item in path_errors)
    return {
        "status": "FAIL" if errors else "REVIEW_REQUIRED" if observations else "PASS",
        "variant_digest": digest(value),
        "bound_digest": digest(bound),
        "scope_digest": digest(scope),
        "errors": errors,
        "observations": observations,
        "rendered_artifacts": renders,
        "event_paths": paths,
        "semantic_authority": "BOUNDED_ENGINEERING_CHECKS_ONLY",
        "professional_validation": value["rubric"]["professional_validation"],
        "full_engagement_playthrough": "NOT_RUN",
        "automatic_acceptance": False,
    }


class Corpus:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)

    def load(self, variant_id: str) -> dict:
        if variant_id not in obligations():
            raise DomainError("Unknown variant obligation")
        path = self.root / "definitions" / (variant_id + ".json")
        if path.is_symlink() or not path.is_file():
            raise DomainError("Authored variant not available", code="CORPUS_INCOMPLETE")
        if path.stat().st_size > 2_000_000:
            raise DomainError("Oversized scenario definition")
        value = json.loads(path.read_text())
        validate_variant(value)
        return value

    def select(
        self,
        option_id: str,
        private_seed: bytes,
        *,
        discipline: str,
        control_ids: set[str] | None = None,
        parameters: dict | None = None,
        allow_portable_source: bool = False,
    ) -> dict:
        candidates = [i for i in obligations() if i.startswith(option_id + ".")]
        ranked = sorted(
            candidates, key=lambda i: hmac.new(private_seed, i.encode(), hashlib.sha256).digest()
        )
        # Missing entries are an authoring defect, not permission to silently bias
        # selection toward the small subset which happens to have been written.
        definitions = [self.load(i) for i in ranked]
        selected_type = (parameters or {}).get("type")
        if option_id.startswith("MM-13.") and selected_type == "REAL_SOURCE":
            editions = []
            directory = self.root / "authority-editions" / "REAL_SOURCE"
            if directory.is_symlink() or directory.parent.is_symlink():
                raise DomainError("Unsafe authority edition directory", code="CORPUS_INCOMPLETE")
            for canonical in definitions:
                path = directory / (canonical["id"] + ".json")
                if not path.exists():
                    continue
                if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
                    raise DomainError("Invalid authority edition file", code="CORPUS_INCOMPLETE")
                edition = json.loads(path.read_text())
                validate_variant(edition)
                pins = edition.get("authority_source_pins", [])
                if (
                    any(edition[k] != canonical[k] for k in ("id", "option_id", "selector_id"))
                    or edition.get("binding_contract", {}).get("authority_mode") != "REAL_SOURCE"
                    or not isinstance(pins, list)
                    or not pins
                    or any(
                        not isinstance(p, dict)
                        or not re.fullmatch(r"[0-9a-f]{64}", str(p.get("sha256", "")))
                        or not isinstance(p.get("locator"), str)
                        or not p["locator"].strip()
                        or not isinstance(p.get("url"), str)
                        or not p["url"].startswith("https://")
                        for p in pins
                    )
                ):
                    raise DomainError(
                        "Authority edition identity or source pin invalid", code="CORPUS_INCOMPLETE"
                    )
                editions.append(edition)
            definitions = editions
        eligible = [v for v in definitions if discipline in v["disciplines"]]
        if selected_type:
            eligible = [
                v
                for v in eligible
                if (
                    v.get("binding_contract", {}).get("authority_mode") == selected_type
                    if v["selector_id"] == "MM-13"
                    else selected_type in v.get("binding_contract", {}).get("compatible_types", [])
                )
            ]
        if control_ids is not None:
            matched = [
                v
                for v in eligible
                if control_ids.intersection(
                    v.get("binding_contract", {}).get("applicable_control_ids", [])
                )
            ]
            eligible = matched if matched or not allow_portable_source else eligible
        if not eligible:
            raise DomainError(
                "Selected option has no applicable authored variant for the discipline, "
                "control scope and selected source/asset/system type",
                code="NO_APPLICABLE_AUTHORED_VARIANT",
            )
        return copy.deepcopy(eligible[0])

    def inventory(self) -> dict:
        results = []
        for variant_id in obligations():
            try:
                value = self.load(variant_id)
                results.append(validate_variant(value))
            except (DomainError, ValueError, KeyError, TypeError) as exc:
                results.append({"id": variant_id, "structural": "FAIL", "error": str(exc)})
        return {
            "required": len(results),
            "structurally_valid": sum(r["structural"] == "PASS" for r in results),
            "results": results,
            "completed": False,
        }
