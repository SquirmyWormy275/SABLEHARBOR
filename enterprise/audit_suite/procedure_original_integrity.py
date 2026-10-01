"""Read-only byte check for retained originals cited by recorded sample traces.

The caller supplies an authorized Engine projection and its artifact reader. This
checks custody of cited bytes, not whether an observation, actor, population,
period, source record, or conclusion is true or sufficient.
"""

from __future__ import annotations

import hashlib
from collections import Counter

from . import procedure_trace_readiness
from .store import DomainError

MAX_ORIGINALS = 256
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_SINGLE_BYTES = 25 * 1024 * 1024


def summarize(projection: dict, read_artifact) -> dict:
    """Recheck visible trace references without changing an engagement or source."""
    if not isinstance(projection, dict) or not isinstance(projection.get("artifacts"), list):
        raise DomainError("Authorized engagement projection required")
    metadata = procedure_trace_readiness.summarize(projection)
    base = {
        "schema_version": "1.0",
        "engagement_id": projection.get("id"),
        "engagement_revision": projection.get("revision"),
        "metadata_status": metadata["status"],
        "automatic_testing_credit": False,
        "source_freshness": "NOT_QUERIED",
        "observation_content_match": "NOT_TESTED",
        "population_completeness_accuracy": "NOT_ESTABLISHED",
        "actor_authority_and_independent_review": "NOT_ESTABLISHED",
        "period_and_procedure_sufficiency": "NOT_ESTABLISHED",
    }
    if metadata["status"] == "INPUT_UNAVAILABLE":
        return {
            **base,
            "status": "METADATA_UNAVAILABLE",
            "artifacts": [],
            "traces": [],
            "counts": None,
        }
    traces = [
        (row, task["status"] == "RECORDED_TRACE_LINKS")
        for task_id, task in metadata["by_task"].items()
        for row in task["traces"]
        if isinstance(task_id, str)
    ]
    if not traces and metadata["unavailable_count"] == 0:
        return {
            **base,
            "status": "NO_RECORDED_TRACES",
            "artifacts": [],
            "traces": [],
            "counts": {
                "referenced": 0,
                "verified": 0,
                "missing": 0,
                "integrity_failure": 0,
                "read_unavailable": 0,
            },
        }
    refs = {}
    for trace, lineage_available in traces:
        if not lineage_available or trace["status"] != "EXACT_VISIBLE_METADATA_LINKS":
            continue
        for ref in trace["exact_refs"]:
            if ref["kind"] == "artifact":
                refs[ref["id"]] = ref["sha256"]
    manifests = {
        a["id"]: a
        for a in projection["artifacts"]
        if isinstance(a, dict) and isinstance(a.get("id"), str)
    }
    ambiguous_manifest_ids = len(manifests) != len(projection["artifacts"])
    valid_sizes = [
        manifests[aid]["bytes"]
        for aid in refs
        if aid in manifests and type(manifests[aid].get("bytes")) is int
    ]
    if (
        ambiguous_manifest_ids
        or len(refs) > MAX_ORIGINALS
        or any(
            aid not in manifests
            or type(manifests[aid].get("bytes")) is not int
            or not 0 <= manifests[aid]["bytes"] <= MAX_SINGLE_BYTES
            or manifests[aid].get("sha256") != sha
            for aid, sha in refs.items()
        )
        or sum(valid_sizes) > MAX_TOTAL_BYTES
    ):
        return {
            **base,
            "status": "RECHECK_INPUT_UNAVAILABLE",
            "artifacts": [],
            "traces": [{"id": row["id"], "status": "NOT_RECHECKED"} for row, _ in traces],
            "counts": None,
        }
    artifacts = []
    by_id = {}
    for aid, sha in sorted(refs.items()):
        try:
            content = read_artifact(manifests[aid])
            if (
                not isinstance(content, bytes)
                or len(content) != manifests[aid]["bytes"]
                or hashlib.sha256(content).hexdigest() != sha
            ):
                raise DomainError("Retained original bytes differ from reference")
            status = "VERIFIED_RETAINED_BYTES"
        except FileNotFoundError:
            status = "MISSING_RETAINED_BYTES"
        except DomainError:
            status = "RETAINED_BYTE_INTEGRITY_FAILURE"
        except (OSError, ValueError):
            status = "RETAINED_BYTE_READ_UNAVAILABLE"
        entry = {"artifact_id": aid, "sha256": sha, "status": status}
        artifacts.append(entry)
        by_id[aid] = status
    trace_rows = []
    for trace, lineage_available in traces:
        if not lineage_available or trace["status"] != "EXACT_VISIBLE_METADATA_LINKS":
            trace_rows.append({"id": trace["id"], "status": "METADATA_UNAVAILABLE"})
            continue
        aids = sorted({ref["id"] for ref in trace["exact_refs"] if ref["kind"] == "artifact"})
        status = (
            "NO_RETAINED_ORIGINAL_REFERENCED"
            if not aids
            else "VERIFIED_RETAINED_BYTES"
            if all(by_id[aid] == "VERIFIED_RETAINED_BYTES" for aid in aids)
            else "RETAINED_BYTES_UNAVAILABLE"
        )
        trace_rows.append({"id": trace["id"], "status": status, "artifact_ids": aids})
    counts = Counter(row["status"] for row in artifacts)
    status = (
        "PARTIAL_UNAVAILABLE"
        if metadata["status"] != "AVAILABLE"
        or any(
            row["status"] in {"METADATA_UNAVAILABLE", "RETAINED_BYTES_UNAVAILABLE"}
            for row in trace_rows
        )
        else "NO_RETAINED_ORIGINAL_REFERENCED"
        if not artifacts
        else "VERIFIED_RETAINED_BYTES_ONLY"
    )
    return {
        **base,
        "status": status,
        "artifacts": artifacts,
        "traces": trace_rows,
        "counts": {
            "referenced": len(artifacts),
            "verified": counts["VERIFIED_RETAINED_BYTES"],
            "missing": counts["MISSING_RETAINED_BYTES"],
            "integrity_failure": counts["RETAINED_BYTE_INTEGRITY_FAILURE"],
            "read_unavailable": counts["RETAINED_BYTE_READ_UNAVAILABLE"],
        },
    }


def report(engine, actor: str, engagement_id: str) -> dict:
    """Authorize before reading retained originals; never inspect company truth."""
    return summarize(engine.get(actor, engagement_id), engine.artifacts.read)
