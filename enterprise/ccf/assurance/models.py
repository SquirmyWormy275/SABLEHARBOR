"""Strict, versioned input contract for scoped CCF assessment and delta planning."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/()-]*$")]
Sha = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Review(Record):
    author: Identifier
    reviewer: Identifier
    reviewed_on: date
    rationale: Text
    subject_digest: Sha | None = None

    @model_validator(mode="after")
    def independent(self):
        if self.author == self.reviewer:
            raise ValueError("Review requires a distinct subject identity")
        return self


class Source(Record):
    id: Identifier
    publisher: Text
    edition: Text
    url: Annotated[str, Field(pattern=r"^https://")]
    retrieved_on: date
    effective_from: date | None
    effective_to: date | None = None
    access: Literal["METADATA_ONLY", "AVAILABLE", "LICENSED_COPY_REQUIRED", "SYNTHETIC"]
    content_sha256: Sha | None = None
    rights_note: Text
    review: Review | None = None

    @model_validator(mode="after")
    def source_dates(self):
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Source effective interval is reversed")
        if self.access in {"AVAILABLE", "SYNTHETIC"} and not self.content_sha256:
            raise ValueError("Available sources require a content hash")
        if self.review and self.review.reviewed_on < self.retrieved_on:
            raise ValueError("Source cannot be reviewed before retrieval")
        return self


class Framework(Record):
    id: Identifier
    title: Text
    edition: Text
    source_ids: Annotated[list[Identifier], Field(min_length=1)]
    categories: Annotated[list[Identifier], Field(min_length=1)]
    required_categories: list[Identifier] = []
    expected_requirement_ids: Annotated[list[Identifier], Field(min_length=1)]
    inventory_complete: StrictBool
    inventory_review: Review | None = None
    limitation: Text


class Attribute(Record):
    id: Identifier
    objective: Text
    kind: Literal["CONTROL", "DOCUMENT", "ASSESSMENT"]
    evidence_expectation: Text
    specification: Literal["UNRESOLVED", "STANDARD", "REQUIRED", "ADDRESSABLE"] = "UNRESOLVED"


class Requirement(Record):
    id: Identifier
    framework_id: Identifier
    source_id: Identifier
    locator: Text
    category: Identifier
    summary: Text
    attributes: Annotated[list[Attribute], Field(min_length=1)]
    review: Review | None = None


class Mapping(Record):
    id: Identifier
    requirement_id: Identifier
    control_id: Identifier
    control_digest: Sha
    attribute_ids: Annotated[list[Identifier], Field(min_length=1)]
    rationale: Text
    uncovered: Text
    review: Review | None = None


class Catalog(Record):
    schema_version: Literal["0.2.0"]
    id: Identifier
    version: Text
    native_snapshot_id: Sha
    sources: Annotated[list[Source], Field(min_length=1)]
    frameworks: Annotated[list[Framework], Field(min_length=1)]
    requirements: Annotated[list[Requirement], Field(min_length=1)]
    mappings: list[Mapping]


class Selection(Record):
    framework_id: Identifier
    categories: Annotated[list[Identifier], Field(min_length=1)]


class Scope(Record):
    id: Identifier
    boundaries: Annotated[list[Identifier], Field(min_length=1)]
    baseline: Annotated[list[Selection], Field(min_length=1)]
    targets: list[Selection]
    period_start: date
    period_end: date
    known_on: date
    assessment_mode: Literal["DESIGN", "OPERATING"]
    origin: Literal["SYNTHETIC", "OPERATING_RECORDS"]
    assumptions: Annotated[list[Text], Field(min_length=1)]
    review: Review | None = None

    @model_validator(mode="after")
    def interval(self):
        if not self.period_start <= self.period_end <= self.known_on:
            raise ValueError("Scope requires start <= end <= known_on")
        if self.assessment_mode == "DESIGN" and self.period_start != self.period_end:
            raise ValueError("Design assessment requires a single as-of date")
        return self


class Implementation(Record):
    id: Identifier
    version: Text
    control_id: Identifier
    control_digest: Sha
    boundary_id: Identifier
    owner_role_id: Identifier
    state: Literal["PROPOSED", "IMPLEMENTED"]
    effective_from: date
    effective_to: date | None
    review: Review | None = None

    @model_validator(mode="after")
    def interval(self):
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Implementation interval is reversed")
        return self


class Evidence(Record):
    id: Identifier
    sha256: Sha
    boundary_id: Identifier
    period_start: date
    period_end: date
    collected_on: date
    expires_on: date
    origin: Literal["SYNTHETIC", "OPERATING_RECORDS"]
    classification: Literal["PUBLIC", "INTERNAL", "RESTRICTED"]
    source_system: Text
    extraction: Text
    population_digest: Sha
    payload: dict

    @model_validator(mode="after")
    def interval(self):
        if not self.period_start <= self.period_end <= self.collected_on <= self.expires_on:
            raise ValueError("Evidence requires period start <= end <= collection <= expiry")
        return self


class Test(Record):
    id: Identifier
    requirement_id: Identifier
    attribute_ids: Annotated[list[Identifier], Field(min_length=1)]
    implementation_id: Identifier
    implementation_version: Text
    boundary_id: Identifier
    mode: Literal["DESIGN", "OPERATING"]
    period_start: date
    period_end: date
    performed_on: date
    evidence_ids: Annotated[list[Identifier], Field(min_length=1)]
    expected_population_digest: Sha
    result: Literal["PASS", "FAIL", "NOT_RUN"]
    procedure: Text
    selection_rationale: Text
    findings: list[Text]
    review: Review | None = None

    @model_validator(mode="after")
    def interval(self):
        if not self.period_start <= self.period_end <= self.performed_on:
            raise ValueError("Test period or performance date is invalid")
        if self.review and self.review.reviewed_on < self.performed_on:
            raise ValueError("Review predates test performance")
        if self.result != "PASS" and not self.findings:
            raise ValueError("FAIL and NOT_RUN require a finding")
        return self


class Applicability(Record):
    requirement_id: Identifier
    boundary_id: Identifier
    disposition: Literal["APPLICABLE", "EXCLUDED", "UNRESOLVED"]
    rationale: Text
    review: Review | None = None


class Disclosure(Record):
    audience: Text
    statement: Text
    requirement_ids: Annotated[list[Identifier], Field(min_length=1)]
    review: Review


class Assessment(Record):
    schema_version: Literal["0.2.0"]
    catalog_digest: Sha
    scope: Scope
    implementations: list[Implementation]
    evidence: list[Evidence]
    tests: list[Test]
    applicability: list[Applicability]
    disclosures: list[Disclosure] = []
