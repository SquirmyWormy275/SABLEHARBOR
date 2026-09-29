"""Typed source-preserving projections for incomplete-evidence scenarios.

The source is a bound synthetic company record. These functions cannot substitute
an unrelated authored case or infer missing semantic fields from display prose.
"""

from copy import deepcopy

from .store import DomainError, digest


def _scalars(value, *, include_keys=True):
    if isinstance(value, dict):
        for key, child in value.items():
            if include_keys:
                yield str(key)
            yield from _scalars(child, include_keys=include_keys)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _scalars(child, include_keys=include_keys)
    elif value is not None:
        yield value


def _leaks(secret, value):
    if isinstance(secret, str):
        return isinstance(value, str) and secret in value
    return (type(secret) is type(value) and secret == value) or (
        isinstance(value, str) and str(secret) == value
    )


def project(source: dict, contract: dict, *, alternates: dict | None = None) -> dict:
    binding = contract.get("runtime_binding")
    if not isinstance(binding, dict):
        raise DomainError("Typed source semantics are required", code="SOURCE_ADAPTER_REQUIRED")
    recipe = deepcopy(source["recipe"])
    columns = recipe.get("columns", [])
    rows = recipe.get("rows", [])
    if "document" in recipe:
        return _project_object(source, contract, alternates=alternates)
    required = binding.get("required_fields", [])
    targets = binding.get("target_fields", [])
    if (
        not isinstance(required, list)
        or not isinstance(targets, list)
        or any(not isinstance(f, str) for f in required + targets)
        or not set(required + targets) <= set(columns)
    ):
        raise DomainError("Required semantic fields are absent", code="SOURCE_NOT_APPLICABLE")
    kind = binding.get("required_artifact_kind")
    if kind and source.get("artifact_kind") != kind:
        raise DomainError("Required source record kind is absent", code="SOURCE_NOT_APPLICABLE")
    for field, value in binding.get("required_values", {}).items():
        if field not in columns or not any(row.get(field) == value for row in rows):
            raise DomainError("Required source condition is absent", code="SOURCE_NOT_APPLICABLE")
    initial_source = source
    operation = contract["kind"]
    recovery = contract["recovery_route"]
    if recovery not in {"ACTUAL_SOURCE_RELEASE", "SUPPORTED_LIMITATION"}:
        raise DomainError("Unsupported source recovery route")
    if operation == "OMIT_ARTIFACT":
        projected = None
    elif operation in {"REDACT_FIELDS", "REMOVE_PROVENANCE", "INCOMPLETE_APPROVAL"}:
        if not targets:
            raise DomainError("Field projection requires explicit semantic targets")
        if operation == "INCOMPLETE_APPROVAL":
            roles = binding.get("approval_roles", {})
            preparer, reviewer = roles.get("preparer"), roles.get("reviewer")
            if (
                preparer not in columns
                or reviewer not in targets
                or not rows
                or any(
                    not row.get(preparer) or not row.get(reviewer) or row[preparer] == row[reviewer]
                    for row in rows
                )
            ):
                raise DomainError("Source lacks distinct actual approval principals")
        # Remove the values before serialization, including any descriptive text
        # that would disclose them outside the selected columns.
        omitted = {
            scalar
            for row in rows
            for field in targets
            for scalar in _scalars(row.get(field), include_keys=False)
            if scalar is not None and scalar != ""
        }
        recipe["rows"] = [
            {k: ("[REDACTED]" if k in targets else v) for k, v in row.items()} for row in rows
        ]
        remainder = deepcopy(recipe)
        remainder["rows"] = [
            {k: v for k, v in row.items() if k not in targets} for row in recipe["rows"]
        ]
        if any(_leaks(secret, scalar) for scalar in _scalars(remainder) for secret in omitted):
            raise DomainError("Projection would leak removed values through another field")
        projected = recipe
    elif operation == "SUMMARY_ONLY":
        group_fields = binding.get("group_fields", [])
        if not group_fields or not set(group_fields) <= set(columns):
            raise DomainError("Summary requires explicit source grouping fields")
        counts = {}
        for row in rows:
            key = tuple(str(row.get(f, "")) for f in group_fields)
            counts[key] = counts.get(key, 0) + 1
        projected = {
            "format": recipe["format"],
            "title": recipe["title"] + " — summary",
            "columns": [*group_fields, "source_row_count"],
            "rows": [
                {**dict(zip(group_fields, key, strict=True)), "source_row_count": count}
                for key, count in sorted(counts.items())
            ],
            "paragraphs": [
                "Aggregate source counts; individual occurrence records are not included."
            ],
        }
    elif operation in {"SUBSTITUTE_DRAFT", "SUBSTITUTE_SCOPE", "SUBSTITUTE_OBSOLETE"}:
        alternate = (alternates or {}).get(binding.get("alternate_source_role"))
        if not alternate or alternate == source:
            raise DomainError("Required independently authored alternate source is absent")
        if not alternate.get("source_identity") or alternate["source_identity"] == source.get(
            "source_identity"
        ):
            raise DomainError("Alternate source must have its own retained identity")
        alternate_recipe = alternate["recipe"]
        alternate_fields = binding.get("alternate_required_fields", [])
        alternate_values = binding.get("alternate_required_values", {})
        alternate_kind = binding.get("alternate_required_artifact_kind")
        if not (alternate_fields or alternate_values or alternate_kind):
            raise DomainError("Alternate source requires explicit semantic predicates")
        if alternate_kind and alternate.get("artifact_kind") != alternate_kind:
            raise DomainError("Alternate source record kind does not match")
        if not set(alternate_fields) <= set(alternate_recipe.get("columns", [])):
            raise DomainError("Alternate source semantic fields are absent")
        for field, value in alternate_values.items():
            alternate_rows = alternate_recipe.get("rows", [])
            if not alternate_rows or any(row.get(field) != value for row in alternate_rows):
                raise DomainError("Alternate source condition does not match")
        for field in binding.get("alternate_required_different_fields", []):
            source_values = {str(row.get(field)) for row in rows if field in row}
            other_rows = alternate_recipe.get("rows", [])
            if (
                not source_values
                or not other_rows
                or any(field not in row or str(row[field]) in source_values for row in other_rows)
            ):
                raise DomainError("Alternate source scope/version is not independently distinct")
        initial_source = alternate
        projected = deepcopy(alternate_recipe)
    elif operation == "REFERENCE_SCREENSHOT":
        projected = {
            "format": "png",
            "title": "Document locator",
            "columns": ["document_title", "source_recipe_digest"],
            "rows": [{"document_title": recipe["title"], "source_recipe_digest": digest(recipe)}],
            "paragraphs": ["Locator metadata only; this image does not contain the document."],
        }
    elif operation == "DAMAGE_NATIVE":
        if recipe["format"] not in {"xlsx", "pdf", "png", "json"}:
            raise DomainError("Damage requires a parseable native container")
        recipe["damage"] = "INVALID_CONTAINER"
        projected = recipe
    elif operation == "DEMONSTRATE_ONLY":
        # A demonstration needs a separately authored current-action record. An
        # old occurrence cannot be relabeled as a live action.
        demo = (alternates or {}).get(binding.get("alternate_source_role"))
        if not demo or demo.get("artifact_kind") != "CURRENT_ACTION_DEMONSTRATION":
            raise DomainError("Current-action demonstration source is absent")
        initial_source = demo
        projected = deepcopy(demo["recipe"])
    else:
        raise DomainError("Unsupported evidence transformation")
    return {
        "initial_recipe": projected,
        "initial_source_private": deepcopy(initial_source),
        "followup_recipe": deepcopy(source["recipe"])
        if recovery == "ACTUAL_SOURCE_RELEASE"
        else None,
        "original_private": deepcopy(source),
        "source_recipe_digest": digest(source["recipe"]),
        "contract_digest": digest(contract),
        "operation": operation,
        "recovery_route": recovery,
        "professional_sufficiency": "NOT_ASSERTED",
    }


def _project_object(source, contract, *, alternates=None):
    """Project explicitly located object rows, preserving the native envelope."""
    binding = contract["runtime_binding"]
    path = binding.get("object_rows_path")
    fields = binding.get("object_fields")
    if (
        not isinstance(path, list)
        or any(type(part) not in (str, int) for part in path)
        or not isinstance(fields, list)
        or not fields
        or any(not isinstance(field, str) for field in fields)
    ):
        raise DomainError("Native object evidence requires explicit row path and fields")
    document = deepcopy(source["recipe"]["document"])
    rows = document
    try:
        for part in path:
            if isinstance(rows, list) and (type(part) is not int or part < 0):
                raise KeyError(part)
            rows = rows[part]
    except (KeyError, IndexError, TypeError) as exc:
        raise DomainError("Native object row path is absent") from exc
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise DomainError("Native object row path must identify retained object records")
    if any(not set(fields) <= set(row) for row in rows):
        raise DomainError("Native object semantic fields are absent")
    operation = contract["kind"]
    if operation not in {
        "REDACT_FIELDS",
        "REMOVE_PROVENANCE",
        "INCOMPLETE_APPROVAL",
        "OMIT_ARTIFACT",
        "SUMMARY_ONLY",
        "DAMAGE_NATIVE",
    }:
        raise DomainError("Object alternate projection requires a matching native schema")
    tabular = deepcopy(source)
    tabular["recipe"].pop("document")
    tabular["recipe"].update(columns=fields, rows=deepcopy(rows))
    result = project(tabular, contract, alternates=alternates)
    projected = result["initial_recipe"]
    if projected is not None and operation != "SUMMARY_ONLY":
        if operation != "DAMAGE_NATIVE":
            if path:
                parent = document
                for part in path[:-1]:
                    parent = parent[part]
                parent[path[-1]] = projected["rows"]
            else:
                document = projected["rows"]
            secrets = {
                scalar
                for row in rows
                for field in binding.get("target_fields", [])
                for scalar in _scalars(row.get(field), include_keys=False)
                if scalar is not None and scalar != ""
            }
            if any(_leaks(secret, scalar) for scalar in _scalars(document) for secret in secrets):
                raise DomainError("Native object envelope would leak removed values")
        projected = deepcopy(source["recipe"])
        projected["document"] = document
        if operation == "DAMAGE_NATIVE":
            projected["damage"] = "INVALID_CONTAINER"
    result.update(
        initial_recipe=projected,
        followup_recipe=deepcopy(source["recipe"])
        if contract["recovery_route"] == "ACTUAL_SOURCE_RELEASE"
        else None,
        original_private=deepcopy(source),
        initial_source_private=deepcopy(source),
        source_recipe_digest=digest(source["recipe"]),
    )
    return result
