from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sable_harbor.provenance.identity import (
    COMMIT_SHA,
    assumptions_digest,
    canon_source_lock_digest,
    canon_source_snapshot_digests,
    generation_input_manifest_digest,
    generator_source_digest,
)
from sable_harbor.provenance.models import GenerationRun

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CANON_SOURCE_LOCK = REPOSITORY_ROOT / "docs/finance/CANON_SOURCE_LOCK.json"
SCENARIO_INPUT = REPOSITORY_ROOT / "config/finance/scenarios/operating.yml"

EPISTEMIC_MODE = "RETROSPECTIVE_CURRENT_CANON"
INPUT_VERSION = "finance-generation-input-manifest/v1"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _required_mapping(document: dict[str, Any], key: str) -> dict[str, Any]:
    value = document.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Canon source lock must define {key!r}")
    return value


def _required_string(document: dict[str, Any], key: str, *, section: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Canon source lock {section!r} must define {key!r}")
    return value


def _snapshot_id(section: dict[str, Any], *, section_name: str) -> str:
    branch = _required_string(section, "branch", section=section_name)
    commit = _required_string(section, "commit", section=section_name)
    return f"{branch}@{commit}"


def source_snapshot_metadata() -> dict[str, Any]:
    """Return the output-facing epistemic contract pinned by the canon source lock."""
    document = json.loads(CANON_SOURCE_LOCK.read_text())
    if not isinstance(document, dict):
        raise ValueError("Canon source lock must be a JSON object")

    schema_version = _required_string(document, "schema_version", section="root")
    reconciled_at = _required_string(document, "reconciled_at", section="root")
    controlling = _required_mapping(document, "controlling_source")
    historical = _required_mapping(document, "historical_knowledge_snapshot")
    noncontrolling = _required_mapping(document, "noncontrolling_reference")
    canon_effective_through = _required_string(
        controlling, "effective_through", section="controlling_source"
    )

    source_snapshot_ids = {
        "current_canon": _snapshot_id(controlling, section_name="controlling_source"),
        "historical_context": _snapshot_id(
            historical, section_name="historical_knowledge_snapshot"
        ),
        "noncontrolling_legacy_calibration_reference": _snapshot_id(
            noncontrolling, section_name="noncontrolling_reference"
        ),
        "canon_source_lock": f"docs/finance/CANON_SOURCE_LOCK.json@{schema_version}",
    }
    snapshot_content_digests = canon_source_snapshot_digests()
    source_snapshot_digests = {
        "current_canon_git_commit": _required_string(
            controlling, "commit", section="controlling_source"
        ),
        "historical_context_git_commit": _required_string(
            historical, "commit", section="historical_knowledge_snapshot"
        ),
        "noncontrolling_legacy_calibration_reference_git_commit": _required_string(
            noncontrolling, "commit", section="noncontrolling_reference"
        ),
        "canon_source_lock_sha256": file_sha256(CANON_SOURCE_LOCK),
        "current_canon_content_sha256": snapshot_content_digests["controlling_source"],
        "historical_context_content_sha256": snapshot_content_digests[
            "historical_knowledge_snapshot"
        ],
        "noncontrolling_legacy_calibration_reference_content_sha256": (
            snapshot_content_digests["noncontrolling_reference"]
        ),
    }
    return {
        "epistemic_mode": EPISTEMIC_MODE,
        "canon_effective_through": canon_effective_through,
        "canon_reconciled_at": reconciled_at,
        "prepared_at": reconciled_at,
        "source_snapshot_ids": source_snapshot_ids,
        "source_snapshot_digests": source_snapshot_digests,
        "canon_source_lock_schema_version": schema_version,
    }


def public_profile(profile: str) -> str:
    """Translate compatibility/internal calibration profile names at output boundaries."""
    if profile in {"actual_common", "synthetic_common", "shared_synthetic_calibration"}:
        return "shared_synthetic_calibration"
    return profile


def utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def require_current_build_identity(run: GenerationRun) -> None:
    """Prevent a current-source manifest from being attached to stale persisted evidence."""
    comparisons = {
        "input manifest": (run.input_manifest_digest, generation_input_manifest_digest()),
        "generator source": (run.generator_source_digest, generator_source_digest()),
        "assumptions": (run.assumptions_digest, assumptions_digest()),
        "canon source lock": (run.canon_source_lock_digest, canon_source_lock_digest()),
    }
    mismatches = [
        name for name, (persisted, current) in comparisons.items() if persisted != current
    ]
    if COMMIT_SHA.fullmatch(run.git_commit) is None:
        mismatches.append("source commit")
    if mismatches:
        raise ValueError(
            "Selected generation run does not match the current governed build inputs: "
            + ", ".join(mismatches)
        )


def generation_manifest_metadata(
    run: GenerationRun,
    *,
    scenario_code: str,
    built_at: datetime,
    effective_from: str,
    effective_through: str,
    effective_period_basis: str,
) -> dict[str, Any]:
    require_current_build_identity(run)
    metadata = source_snapshot_metadata()
    metadata.update(
        {
            "scenario_id": run.scenario_id,
            "scenario_code": scenario_code,
            "scenario_version": f"operating-scenarios@sha256:{file_sha256(SCENARIO_INPUT)}",
            "generator_version": run.generator_version,
            "generator_source_digest": run.generator_source_digest,
            "package_builder_source_digest": run.generator_source_digest,
            "input_version": INPUT_VERSION,
            "input_manifest_digest": run.input_manifest_digest,
            "assumptions_digest": run.assumptions_digest,
            "canon_source_lock_digest": run.canon_source_lock_digest,
            "build_id": run.build_id,
            "built_at": utc_iso(built_at),
            "effective_period": {
                "from": effective_from,
                "through": effective_through,
                "basis": effective_period_basis,
            },
            "synthetic_calibration_through": (
                run.synthetic_calibration_through.isoformat()
                if run.synthetic_calibration_through
                else None
            ),
            "forecast_from": run.forecast_from.isoformat() if run.forecast_from else None,
        }
    )
    return metadata


def included_run_metadata(
    runs: list[GenerationRun], *, selected_run_id: str
) -> list[dict[str, Any]]:
    return [
        {
            "generation_run_id": run.id,
            "data_role": (
                "shared_synthetic_calibration"
                if public_profile(run.profile) == "shared_synthetic_calibration"
                else (
                    "selected_synthetic_scenario"
                    if run.id == selected_run_id
                    else "included_synthetic_scenario"
                )
            ),
            "profile": public_profile(run.profile),
            "scenario_id": run.scenario_id,
            "seed": run.seed,
            "status": run.status,
            "generator_version": run.generator_version,
            "build_id": run.build_id,
            "input_manifest_digest": run.input_manifest_digest,
            "synthetic_calibration_through": (
                run.synthetic_calibration_through.isoformat()
                if run.synthetic_calibration_through
                else None
            ),
            "forecast_from": run.forecast_from.isoformat() if run.forecast_from else None,
            "schema_head": run.schema_head,
        }
        for run in runs
    ]
