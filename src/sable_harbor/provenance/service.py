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
    RunIdentity,
    assumptions_digest,
    canon_source_lock_digest,
    generator_source_digest,
)
from .models import GenerationRun, LineageEdge, ModelAssumption, Scenario, SourceDocument

GENERATION_RUN_SESSION_KEY = "generation_run_id"


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
    session: Session, path: Path = Path("config/finance/assumptions/quantitative.yml")
) -> int:
    source = session.scalar(
        select(SourceDocument).where(
            SourceDocument.path == str(path),
            SourceDocument.commit_sha == "5137c5abc025ad757a4e1af2a57279e4964578cf",
        )
    )
    if source is None:
        source = SourceDocument(
            id=stable_id("source_document", f"{path}:5137c5a"),
            path=str(path),
            branch="origin/canon/corporate-lore-v0.2",
            commit_sha="5137c5abc025ad757a4e1af2a57279e4964578cf",
            controlling=False,
            fact_state=FactState.MODEL_PROPOSED,
        )
        session.add(source)
        session.flush()
    payload: dict[str, Any] = yaml.safe_load(path.read_text())
    count = 0
    for item in payload["assumptions"]:
        code = str(item["id"])
        if session.scalar(
            select(ModelAssumption.id).where(ModelAssumption.assumption_code == code)
        ):
            continue
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
    if run is None:
        run = GenerationRun(
            id=run_id,
            profile=profile,
            scenario_id=scenario.id,
            seed=seed,
            actual_dataset_id=identity.actual_dataset_id,
            generator_version=identity.generator_version,
            git_commit=git_commit,
            generator_source_digest=source_digest,
            assumptions_digest=assumption_sha,
            canon_source_lock_digest=canon_sha,
            actual_through=identity.actual_through,
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
            run.git_commit,
            run.generator_source_digest,
            run.assumptions_digest,
            run.canon_source_lock_digest,
            run.actual_through,
            run.forecast_from,
            run.schema_head,
        )
        requested = (
            git_commit,
            source_digest,
            assumption_sha,
            canon_sha,
            identity.actual_through,
            identity.forecast_from,
            required_schema_head(),
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
            "An explicit generation run is required when the database contains "
            f"{len(run_ids)} runs"
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
        (run.actual_generation_run_id, run.id)
        if run.actual_generation_run_id is not None
        else (run.id,)
    )
    return RunContext(run.id, scenario.code, included)


def link_journals(session: Session, run: GenerationRun) -> int:
    count = 0
    for entry in session.scalars(
        select(JournalEntry).where(JournalEntry.generation_run_id == run.id)
    ):
        edge_id = stable_id(
            "lineage_edge", f"{run.id}:{entry.source_type}:{entry.source_id}:{entry.id}"
        )
        if session.get(LineageEdge, edge_id) is None:
            session.add(
                LineageEdge(
                    id=edge_id,
                    generation_run_id=run.id,
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


def lineage_for(session: Session, record_id: str) -> list[dict[str, str]]:
    edges = session.scalars(
        select(LineageEdge).where(
            (LineageEdge.upstream_id == record_id) | (LineageEdge.downstream_id == record_id)
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
