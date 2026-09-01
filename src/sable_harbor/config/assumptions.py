from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from sable_harbor.accounting.models import FactState


class AssumptionSource(BaseModel):
    path: str
    decision_id: str | None = None
    branch: str | None = None
    commit: str | None = None


class Assumption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    fact_state: FactState
    source: AssumptionSource
    effective_from: date
    value: Any
    low: Any | None = None
    high: Any | None = None
    units: str
    rationale: str
    alternatives: list[Any] = Field(default_factory=list)
    affected_entities: list[str]
    affected_reports: list[str]
    affected_calculations: list[str]
    sensitivity: str
    materiality: str
    reversible: bool
    decision_owner: str
    status: str
    last_review_date: date


class AssumptionFile(BaseModel):
    assumptions: list[Assumption]


def load_assumptions(directory: Path) -> list[Assumption]:
    loaded: list[Assumption] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("*.yml")):
        document = AssumptionFile.model_validate(yaml.safe_load(path.read_text()))
        for assumption in document.assumptions:
            if assumption.id in seen:
                raise ValueError(f"Duplicate assumption ID: {assumption.id}")
            seen.add(assumption.id)
            loaded.append(assumption)
    return loaded
