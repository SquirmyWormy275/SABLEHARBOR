import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import FactState, JournalEntry, ScenarioValue
from sable_harbor.core.database import required_schema_head
from sable_harbor.core.ids import stable_id

from .identity import (
    COMMIT_SHA,
    RunIdentity,
    assumptions_digest,
    canon_source_lock_digest,
    generator_source_digest,
)
from .models import GenerationRun, LineageEdge, ModelAssumption, Scenario, SourceDocument

GENERATION_RUN_SESSION_KEY = "generation_run_id"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class RunContext:
    generation_run_id: str
    scenario_code: str
    included_run_ids: tuple[str, ...]


def _as_date(value: object) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def seed_provenance(
    session: Session,
    path: Path = REPOSITORY_ROOT / "config/finance/assumptions/quantitative.yml",
) -> int:
    payload: dict[str, Any] = yaml.safe_load(path.read_text())
    source_lock = json.loads((REPOSITORY_ROOT / "docs/finance/CANON_SOURCE_LOCK.json").read_text())
    controlling = source_lock["controlling_source"]
    controlling_files = set(controlling["files"])
    sources: dict[tuple[str, str], SourceDocument] = {}
    count = 0
    for item in payload["assumptions"]:
        code = str(item["id"])
        if session.scalar(
            select(ModelAssumption.id).where(ModelAssumption.assumption_code == code)
        ):
            continue
        source_metadata = item.get("source")
        if not isinstance(source_metadata, dict):
            raise ValueError(f"Assumption {code!r} requires structured source metadata")
        source_path = str(source_metadata["path"])
        source_branch = str(source_metadata["branch"])
        source_commit = str(source_metadata["commit"])
        source_key = (source_path, source_commit)
        source = sources.get(source_key)
        if source is None:
            source = session.scalar(
                select(SourceDocument).where(
                    SourceDocument.path == source_path,
                    SourceDocument.commit_sha == source_commit,
                )
            )
        is_controlling = (
            source_path in controlling_files
            and source_branch == controlling["branch"]
            and source_commit == controlling["commit"]
        )
        if source is None:
            source = SourceDocument(
                id=stable_id("source_document", f"{source_path}:{source_commit}"),
                path=source_path,
                branch=source_branch,
                commit_sha=source_commit,
                controlling=is_controlling,
                fact_state=(FactState.LOCKED_CANON if is_controlling else FactState.MODEL_PROPOSED),
            )
            session.add(source)
            session.flush()
        sources[source_key] = source
        session.add(
            ModelAssumption(
                id=stable_id("assumption", code),
                assumption_code=code,
                name=str(item["name"]),
                description=str(item["description"]),
                fact_state=FactState(str(item["fact_state"])),
                source_document_id=source.id,
                effective_from=_as_date(item["effective_from"]),
                base_value=str(item["value"]),
                low_value=str(item.get("low")) if item.get("low") is not None else None,
                high_value=str(item.get("high")) if item.get("high") is not None else None,
                units=str(item["units"]),
                rationale=str(item["rationale"]),
                sensitivity=str(item["sensitivity"]),
                reversible=bool(item["reversible"]),
                decision_owner=str(item["decision_owner"]),
                status=str(item["status"]),
                last_review_date=_as_date(item["last_review_date"]),
            )
        )
        count += 1
    session.flush()
    return count


def record_generation_run(
    session: Session, *, profile: str, scenario_code: str, seed: int, git_commit: str
) -> GenerationRun:
    if COMMIT_SHA.fullmatch(git_commit) is None:
        raise ValueError("Generation source commit must be a full lowercase Git SHA-1")
    identity = RunIdentity.build(profile=profile, scenario=scenario_code, seed=seed)
    profile, scenario_code = identity.profile, identity.scenario
    scenario = session.scalar(select(Scenario).where(Scenario.code == scenario_code))
    if scenario is None:
        scenario = Scenario(
            id=stable_id("scenario", scenario_code),
            code=scenario_code,
            name=scenario_code.replace("_", " ").title(),
            description=f"Versioned {scenario_code} financial scenario",
            fact_state=FactState.SCENARIO_INPUT,
        )
        session.add(scenario)
        session.flush()
    run_id = identity.run_id
    run = session.get(GenerationRun, run_id)
    now = datetime.now(UTC)
    source_digest = generator_source_digest()
    assumption_sha = assumptions_digest()
    canon_sha = canon_source_lock_digest()
    manifest_sha = identity.input_manifest_digest
    if run is None:
        run = GenerationRun(
            id=run_id,
            profile=profile,
            scenario_id=scenario.id,
            seed=seed,
            actual_dataset_id=identity.synthetic_calibration_dataset_id,
            build_id=identity.build_id,
            input_manifest_digest=manifest_sha,
            generator_version=identity.generator_version,
            git_commit=git_commit,
            generator_source_digest=source_digest,
            assumptions_digest=assumption_sha,
            canon_source_lock_digest=canon_sha,
            actual_through=identity.synthetic_calibration_through,
            forecast_from=identity.forecast_from,
            schema_head=required_schema_head(),
            started_at=now,
            completed_at=None,
            status="RUNNING",
        )
        session.add(run)
        session.flush()
    elif run.status == "COMPLETED":
        persisted = (
            run.generator_source_digest,
            run.assumptions_digest,
            run.canon_source_lock_digest,
            run.synthetic_calibration_through,
            run.forecast_from,
            run.schema_head,
            run.build_id,
            run.input_manifest_digest,
        )
        requested = (
            source_digest,
            assumption_sha,
            canon_sha,
            identity.synthetic_calibration_through,
            identity.forecast_from,
            required_schema_head(),
            identity.build_id,
            manifest_sha,
        )
        if persisted != requested:
            raise ValueError(
                "Completed generation run identity mismatch; completed runs are immutable"
            )
    session.info[GENERATION_RUN_SESSION_KEY] = run.id
    marker_id = stable_id("scenario_value", f"run:{run.id}:marker")
    if session.get(ScenarioValue, marker_id) is None:
        session.add(
            ScenarioValue(
                id=marker_id,
                generation_run_id=run.id,
                scenario_code=scenario_code,
                metric_code="run_marker",
                entity_code="CONSOLIDATED",
                period_code="RUN",
                amount=Decimal(1),
                unit="count",
                fact_state=FactState.DERIVED,
                provenance="generation-run lifecycle marker",
            )
        )
        session.flush()
    return run


def complete_generation_run(session: Session, run: GenerationRun) -> None:
    if run.status == "COMPLETED" and run.completed_at is not None:
        return
    if run.status != "RUNNING" or run.completed_at is not None:
        raise ValueError(
            f"Generation run {run.id!r} cannot transition from {run.status!r} to COMPLETED"
        )
    from sable_harbor.accounting.validation import assert_run_ready_for_completion

    assert_run_ready_for_completion(session, run)
    run.completed_at = datetime.now(UTC)
    run.status = "COMPLETED"
    session.flush()


def resolve_generation_run(session: Session, generation_run_id: str | None = None) -> str:
    if generation_run_id is not None:
        if session.get(GenerationRun, generation_run_id) is None:
            raise ValueError(f"Unknown generation run {generation_run_id!r}")
        return generation_run_id
    run_ids = list(session.scalars(select(GenerationRun.id).order_by(GenerationRun.id)))
    if len(run_ids) != 1:
        raise ValueError(
            f"An explicit generation run is required when the database contains {len(run_ids)} runs"
        )
    return run_ids[0]


def run_context(session: Session, generation_run_id: str | None = None) -> RunContext:
    selected_id = resolve_generation_run(session, generation_run_id)
    run = session.get(GenerationRun, selected_id)
    if run is None:
        raise ValueError(f"Unknown generation run {selected_id!r}")
    if run.status != "COMPLETED":
        raise ValueError(f"Generation run {selected_id!r} must be COMPLETED")
    scenario = session.get(Scenario, run.scenario_id)
    if scenario is None:
        raise ValueError(f"Generation run {selected_id!r} has no scenario")
    included = (
        (run.shared_synthetic_calibration_run_id, run.id)
        if run.shared_synthetic_calibration_run_id is not None
        else (run.id,)
    )
    if run.shared_synthetic_calibration_run_id is not None:
        calibration_run = session.get(GenerationRun, run.shared_synthetic_calibration_run_id)
        if calibration_run is None or calibration_run.status != "COMPLETED":
            raise ValueError(
                f"Generation run {selected_id!r} references an incomplete shared synthetic "
                "calibration run"
            )
        if calibration_run.synthetic_calibration_dataset_id != run.synthetic_calibration_dataset_id:
            raise ValueError(
                f"Generation run {selected_id!r} references an incompatible shared synthetic "
                "calibration run"
            )
    return RunContext(run.id, scenario.code, included)


def comparison_run_contexts(
    session: Session, left_generation_run_id: str, right_generation_run_id: str
) -> tuple[RunContext, RunContext]:
    """Resolve two distinct completed scenario runs under one comparable build contract."""
    if left_generation_run_id == right_generation_run_id:
        raise ValueError("Comparison requires two distinct generation runs")
    left_context = run_context(session, left_generation_run_id)
    right_context = run_context(session, right_generation_run_id)
    left_run = session.get(GenerationRun, left_context.generation_run_id)
    right_run = session.get(GenerationRun, right_context.generation_run_id)
    if left_run is None or right_run is None:  # guarded by run_context
        raise ValueError("Comparison generation run does not exist")
    if (
        left_run.profile != right_run.profile
        or left_run.seed != right_run.seed
        or left_run.synthetic_calibration_dataset_id != right_run.synthetic_calibration_dataset_id
        or left_run.shared_synthetic_calibration_run_id
        != right_run.shared_synthetic_calibration_run_id
        or left_run.synthetic_calibration_through != right_run.synthetic_calibration_through
        or left_run.forecast_from != right_run.forecast_from
        or left_run.schema_head != right_run.schema_head
        or left_run.generator_version != right_run.generator_version
        or left_run.input_manifest_digest != right_run.input_manifest_digest
    ):
        raise ValueError(
            "Comparison runs must use the same profile, synthetic calibration dataset, seed, "
            "shared calibration run, synthetic calibration boundary, forecast start, schema, "
            "generator version, and input manifest"
        )
    if left_context.scenario_code == right_context.scenario_code:
        raise ValueError("Comparison requires two distinct scenario codes")
    return left_context, right_context


def link_journals(session: Session, run: GenerationRun) -> int:
    count = 0
    included_run_ids = (
        (run.shared_synthetic_calibration_run_id, run.id)
        if run.shared_synthetic_calibration_run_id is not None
        else (run.id,)
    )
    for entry in session.scalars(
        select(JournalEntry).where(JournalEntry.generation_run_id.in_(included_run_ids))
    ):
        edge_id = stable_id(
            "lineage_edge",
            f"{entry.generation_run_id}:{entry.source_type}:{entry.source_id}:{entry.id}",
        )
        if session.get(LineageEdge, edge_id) is None:
            session.add(
                LineageEdge(
                    id=edge_id,
                    generation_run_id=entry.generation_run_id,
                    upstream_type=entry.source_type,
                    upstream_id=entry.source_id,
                    downstream_type="journal_entry",
                    downstream_id=entry.id,
                    transformation="versioned_posting_rule",
                )
            )
            count += 1
    session.flush()
    return count


def lineage_for(
    session: Session, record_id: str, generation_run_id: str | None = None
) -> list[dict[str, str]]:
    context = run_context(session, generation_run_id)
    edges = session.scalars(
        select(LineageEdge).where(
            LineageEdge.generation_run_id.in_(context.included_run_ids),
            (LineageEdge.upstream_id == record_id) | (LineageEdge.downstream_id == record_id),
        )
    )
    return [
        {
            "upstream_type": edge.upstream_type,
            "upstream_id": edge.upstream_id,
            "downstream_type": edge.downstream_type,
            "downstream_id": edge.downstream_id,
            "transformation": edge.transformation,
        }
        for edge in edges
    ]
