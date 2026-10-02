"""Authorized workspace transport; retained audit records are never changed.

Callers must first apply Engine's existing membership and audience projection.
Summaries defer bodies explicitly. Detail reads bind the same engagement,
revision, permission/source epoch and complete stored-object digest.
"""

from __future__ import annotations

import hashlib
import re

from .store import DomainError, digest

SCHEMA = "SH_WORKSPACE_SUMMARY_V1"
HEADER = "summary-v1"
COLLECTIONS = frozenset({"workpapers", "sample_executions"})


def epoch(state: dict) -> str:
    return digest(
        {
            "engagement_id": state["id"],
            "scope": state.get("scope"),
            "permissions": state.get("permissions"),
            "simulated_at": state.get("simulated_at"),
            "company_source_binding": state.get("company_source_binding"),
            "evidence_acquisition": state.get("evidence_acquisition"),
        }
    )


def _descriptor(state: dict, row: dict, collection: str) -> dict:
    return {
        "schema": SCHEMA,
        "engagement_id": state["id"],
        "engagement_revision": state["revision"],
        "source_epoch_sha256": epoch(state),
        "collection": collection,
        "object_id": row["id"],
        "object_sha256": digest(row),
    }


def _paper(state: dict, row: dict, *, selected_version: int | None = None) -> dict:
    result = dict(row)
    versions = []
    for original in row.get("versions", []):
        version = dict(original)
        version["_workspace_version_sha256"] = digest(original)
        if "text" in original and isinstance(original["text"], str):
            text = original["text"]
            version["_workspace_text"] = {
                "loaded": type(original.get("version")) is int
                and original["version"] == selected_version,
                "characters": len(text),
                "bytes": len(text.encode()),
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
            if type(original.get("version")) is not int or original["version"] != selected_version:
                version.pop("text", None)
        versions.append(version)
    result["versions"] = versions
    result["_workspace_detail"] = _descriptor(state, row, "workpapers")
    return result


def summary(state: dict) -> dict:
    """Keep every row, version and relationship; defer only explicit heavy bodies."""
    result = dict(state)
    result["workpapers"] = [_paper(state, row) for row in state.get("workpapers", [])]
    traces = []
    for row in state.get("sample_executions", []):
        value = dict(row)
        if isinstance(row.get("items"), list):
            value.pop("items")
            value["_workspace_items"] = {"loaded": False, "count": len(row["items"])}
        value["_workspace_detail"] = _descriptor(state, row, "sample_executions")
        traces.append(value)
    result["sample_executions"] = traces
    result["workspace_transport"] = {
        "schema": SCHEMA,
        "source_epoch_sha256": epoch(state),
        "complete_collection_rows": True,
        "deferred_fields": ["workpapers.versions.text", "sample_executions.items"],
        "stored_records_or_history_changed": False,
    }
    return result


def _pin(state: dict, revision: int, source_epoch: str) -> None:
    if type(revision) is not int or revision < 0:
        raise DomainError("Exact workspace revision required")
    if not isinstance(source_epoch, str) or not re.fullmatch(r"[a-f0-9]{64}", source_epoch):
        raise DomainError("Exact workspace source epoch required")
    if state["revision"] != revision or epoch(state) != source_epoch:
        raise DomainError("Workspace changed; reload before reading retained details", status=409)


def _unique(state: dict, collection: str, object_id: str) -> dict:
    matches = [row for row in state.get(collection, []) if row.get("id") == object_id]
    if len(matches) != 1:
        raise DomainError("Retained object unavailable in this workspace", status=404)
    return matches[0]


def detail(
    state: dict,
    collection: str,
    object_id: str,
    *,
    revision: int,
    source_epoch: str,
    object_sha256: str,
    version: int | None = None,
) -> dict:
    _pin(state, revision, source_epoch)
    if collection not in COLLECTIONS:
        raise DomainError("Retained detail collection unavailable", status=404)
    row = _unique(state, collection, object_id)
    if not isinstance(object_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", object_sha256):
        raise DomainError("Exact retained object digest required")
    if digest(row) != object_sha256:
        raise DomainError("Retained object changed; reload before reading it", status=409)
    if collection == "workpapers":
        if type(version) is not int or version < 1:
            raise DomainError("Choose an exact retained workpaper version")
        if (
            len(
                [
                    v
                    for v in row.get("versions", [])
                    if type(v.get("version")) is int and v["version"] == version
                ]
            )
            != 1
        ):
            raise DomainError("Retained workpaper version unavailable", status=404)
        value = _paper(state, row, selected_version=version)
    else:
        if version is not None:
            raise DomainError("Sample traces use their exact stored revision")
        value = dict(row)
        value["_workspace_detail"] = _descriptor(state, row, collection)
        value["_workspace_items"] = {"loaded": True, "count": len(row.get("items", []))}
    return {"context": _descriptor(state, row, collection), "row": value}


def sample_original_context(
    state: dict,
    artifact_id: str,
    *,
    revision: int,
    source_epoch: str,
    artifact_sha256: str,
) -> dict:
    """Select all exact-original citations and their direct correction successors."""
    _pin(state, revision, source_epoch)
    artifact = _unique(state, "artifacts", artifact_id)
    if artifact.get("status") != "AVAILABLE" or artifact.get("sha256") != artifact_sha256:
        raise DomainError("Exact original unavailable in this workspace", status=409)
    traces = state.get("sample_executions", [])
    ids = [row["id"] for row in traces]
    if len(ids) != len(set(ids)):
        raise DomainError("Retained sample history is ambiguous", status=409)
    selected = {
        row["id"]
        for row in traces
        if any(
            ref.get("artifact_id") == artifact_id and ref.get("sha256") == artifact_sha256
            for item in row.get("items", [])
            for ref in item.get("evidence", [])
        )
    }
    related = selected | {row["id"] for row in traces if row.get("predecessor_id") in selected}
    return {
        "engagement_id": state["id"],
        "engagement_revision": state["revision"],
        "source_epoch_sha256": epoch(state),
        "artifact_id": artifact_id,
        "artifact_sha256": artifact_sha256,
        "complete_exact_original_selection": True,
        "retained_trace_count": len(traces),
        "traces": [row for row in traces if row["id"] in related],
    }
