"""Scope-aware deltas. Mappings, implementation and demonstrated support are distinct."""

from collections import Counter

from enterprise.ccf.registry import digest, validate

from .models import Assessment, Catalog


def data(record):
    return record.model_dump(mode="json")


def unique(values, label):
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {label}")


def index(records, label):
    unique([r.id for r in records], label)
    return {r.id: r for r in records}


def reviewed(review, known_on):
    return review is not None and review.reviewed_on <= known_on


def check_review_bindings(value):
    if isinstance(value, list):
        for item in value:
            check_review_bindings(item)
    elif isinstance(value, dict):
        subject = {k: v for k, v in value.items() if k not in {"review", "inventory_review"}}
        for key in ("review", "inventory_review"):
            if value.get(key) and value[key]["subject_digest"] != digest(subject):
                raise ValueError("Review is not bound to this record version")
        for key, item in subject.items():
            if key != "payload":
                check_review_bindings(item)


def validate_inputs(catalog, assessment, native):
    check_review_bindings(data(catalog))
    check_review_bindings(data(assessment))
    validate(native)
    if catalog.native_snapshot_id != digest(native):
        raise ValueError("Catalog is bound to a different native snapshot")
    if assessment.catalog_digest != digest(data(catalog)):
        raise ValueError("Assessment is bound to a different catalog version")
    sources = index(catalog.sources, "source")
    frameworks = index(catalog.frameworks, "framework")
    requirements = index(catalog.requirements, "requirement")
    index(catalog.mappings, "mapping")
    implementations = index(assessment.implementations, "implementation")
    evidence = index(assessment.evidence, "evidence")
    index(assessment.tests, "test")
    controls = {r["id"]: r for r in native["records"] if r["kind"] == "control"}
    roles = {r["id"] for r in native["records"] if r["kind"] == "role"}
    boundaries = {r["id"] for r in native["records"] if r["kind"] == "boundary"}
    for f in frameworks.values():
        unique(f.source_ids, "framework source")
        unique(f.categories, "framework category")
        unique(f.required_categories, "required category")
        unique(f.expected_requirement_ids, "expected requirement")
        if not set(f.source_ids) <= sources.keys():
            raise ValueError("Unknown framework source")
        if not set(f.required_categories) <= set(f.categories):
            raise ValueError("Unknown required category")
        actual = {r.id for r in requirements.values() if r.framework_id == f.id}
        if actual != set(f.expected_requirement_ids):
            raise ValueError(f"Requirement population differs for {f.id}")
        populated_categories = {r.category for r in requirements.values() if r.framework_id == f.id}
        if populated_categories != set(f.categories):
            raise ValueError(
                "Every selectable category requires an explicit inventory or source gate"
            )
        if f.inventory_complete and not f.inventory_review:
            raise ValueError("Complete inventory requires review")
    for r in requirements.values():
        if r.framework_id not in frameworks:
            raise ValueError("Unknown requirement framework")
        f = frameworks[r.framework_id]
        if r.source_id not in f.source_ids or r.category not in f.categories:
            raise ValueError("Requirement source/category outside framework")
        unique([a.id for a in r.attributes], "attribute")
    for m in catalog.mappings:
        if m.requirement_id not in requirements or m.control_id not in controls:
            raise ValueError("Unknown mapping requirement/control")
        if m.control_digest != digest(controls[m.control_id]):
            raise ValueError("Mapping control version changed")
        unique(m.attribute_ids, "mapping attribute")
        if not set(m.attribute_ids) <= {a.id for a in requirements[m.requirement_id].attributes}:
            raise ValueError("Unknown mapping attribute")
    unique(assessment.scope.boundaries, "scope boundary")
    if not set(assessment.scope.boundaries) <= boundaries:
        raise ValueError("Unknown scope boundary")
    for selections in (assessment.scope.baseline, assessment.scope.targets):
        unique([s.framework_id for s in selections], "framework selection")
        for selection in selections:
            if selection.framework_id not in frameworks:
                raise ValueError("Unknown selected framework")
            f = frameworks[selection.framework_id]
            unique(selection.categories, "selected category")
            if not set(f.required_categories) <= set(selection.categories) <= set(f.categories):
                raise ValueError("Invalid or missing mandatory categories")
    for impl in implementations.values():
        if impl.control_id not in controls or impl.control_digest != digest(
            controls[impl.control_id]
        ):
            raise ValueError("Implementation control identity/version changed")
        if impl.owner_role_id not in roles or impl.boundary_id not in boundaries:
            raise ValueError("Unknown implementation role/boundary")
    for e in evidence.values():
        if e.boundary_id not in boundaries:
            raise ValueError("Unknown evidence boundary")
        if digest(e.payload) != e.sha256:
            raise ValueError("Evidence content hash mismatch")
    for t in assessment.tests:
        if t.requirement_id not in requirements or t.implementation_id not in implementations:
            raise ValueError("Unknown test requirement/implementation")
        impl = implementations[t.implementation_id]
        if t.implementation_version != impl.version or t.boundary_id != impl.boundary_id:
            raise ValueError("Test implementation version/boundary changed")
        unique(t.attribute_ids, "test attribute")
        unique(t.evidence_ids, "test evidence")
        if not set(t.attribute_ids) <= {a.id for a in requirements[t.requirement_id].attributes}:
            raise ValueError("Unknown test attribute")
        if not set(t.evidence_ids) <= evidence.keys():
            raise ValueError("Unknown test evidence")
    unique([(a.requirement_id, a.boundary_id) for a in assessment.applicability], "applicability")
    for a in assessment.applicability:
        if a.requirement_id not in requirements or a.boundary_id not in boundaries:
            raise ValueError("Unknown applicability requirement/boundary")
    for d in assessment.disclosures:
        unique(d.requirement_ids, "disclosure requirement")
        if not set(d.requirement_ids) <= requirements.keys():
            raise ValueError("Unknown disclosure requirement")
    return sources, frameworks, requirements, controls


def test_issues(test, scope, evidence):
    issues = []
    if test.mode != scope.assessment_mode:
        issues.append("TEST_MODE_MISMATCH")
    if not test.period_start <= scope.period_start <= scope.period_end <= test.period_end:
        issues.append("TEST_PERIOD_GAP")
    if test.performed_on > scope.known_on or not reviewed(test.review, scope.known_on):
        issues.append("TEST_REVIEW_PENDING")
    if test.result != "PASS":
        issues.append(f"TEST_{test.result}")
    for eid in test.evidence_ids:
        e = evidence[eid]
        if e.boundary_id != test.boundary_id:
            issues.append("EVIDENCE_BOUNDARY_MISMATCH")
        if not e.period_start <= scope.period_start <= scope.period_end <= e.period_end:
            issues.append("EVIDENCE_PERIOD_GAP")
        if not e.period_start <= test.period_start <= test.period_end <= e.period_end:
            issues.append("TEST_EXCEEDS_EVIDENCE_PERIOD")
        if e.collected_on > test.performed_on or e.collected_on > scope.known_on:
            issues.append("EVIDENCE_NOT_AVAILABLE")
        if e.expires_on < scope.known_on:
            issues.append("EVIDENCE_EXPIRED")
        if e.origin != scope.origin:
            issues.append("EVIDENCE_ORIGIN_MISMATCH")
        if e.population_digest != test.expected_population_digest:
            issues.append("EVIDENCE_POPULATION_MISMATCH")
    return sorted(set(issues))


def plan(catalog: Catalog, assessment: Assessment, native):
    # Revalidate nested collections as well as the frozen outer models at the public API boundary.
    catalog = Catalog.model_validate(data(catalog))
    assessment = Assessment.model_validate(data(assessment))
    sources, frameworks, requirements, controls = validate_inputs(catalog, assessment, native)
    scope = assessment.scope
    evidence = {e.id: e for e in assessment.evidence}
    applicability = {(a.requirement_id, a.boundary_id): a for a in assessment.applicability}
    baseline = {s.framework_id: set(s.categories) for s in scope.baseline}
    selected = {fid: set(cats) for fid, cats in baseline.items()}
    for s in scope.targets:
        selected.setdefault(s.framework_id, set()).update(s.categories)
    baseline_controls = {
        m.control_id
        for m in catalog.mappings
        if requirements[m.requirement_id].category
        in baseline.get(requirements[m.requirement_id].framework_id, set())
    }
    rows = []
    for r in sorted(requirements.values(), key=lambda x: x.id):
        if r.category not in selected.get(r.framework_id, set()):
            continue
        f = frameworks[r.framework_id]
        for boundary in sorted(scope.boundaries):
            blockers = []
            if not reviewed(scope.review, scope.known_on):
                blockers.append("SCOPE_REVIEW_PENDING")
            if not f.inventory_complete or not reviewed(f.inventory_review, scope.known_on):
                blockers.append("FRAMEWORK_INVENTORY_INCOMPLETE")
            for sid in f.source_ids:
                s = sources[sid]
                if s.access not in {"AVAILABLE", "SYNTHETIC"}:
                    blockers.append("SOURCE_ACCESS_PENDING")
                if not reviewed(s.review, scope.known_on):
                    blockers.append("SOURCE_REVIEW_PENDING")
                if s.access == "SYNTHETIC" and scope.origin != "SYNTHETIC":
                    blockers.append("SYNTHETIC_SOURCE")
                if (
                    not s.effective_from
                    or s.effective_from > scope.period_start
                    or (s.effective_to and s.effective_to < scope.period_end)
                ):
                    blockers.append("SOURCE_EDITION_PERIOD_UNRESOLVED")
            if not reviewed(r.review, scope.known_on):
                blockers.append("REQUIREMENT_REVIEW_PENDING")
            a = applicability.get((r.id, boundary))
            if not a or not reviewed(a.review, scope.known_on) or a.disposition == "UNRESOLVED":
                blockers.append("APPLICABILITY_UNRESOLVED")
            excluded = a and a.disposition == "EXCLUDED" and reviewed(a.review, scope.known_on)
            mappings = [m for m in catalog.mappings if m.requirement_id == r.id]
            attributes = []
            for attribute in r.attributes:
                candidates = [m for m in mappings if attribute.id in m.attribute_ids]
                accepted = [m for m in candidates if reviewed(m.review, scope.known_on)]
                issues, passing, tested, owners, implemented = [], [], [], set(), set()
                owners.update(controls[m.control_id]["data"]["owner_role_id"] for m in candidates)
                if not candidates:
                    issues.append("NO_CONTROL_MAPPING")
                elif not accepted:
                    issues.append("MAPPING_REVIEW_PENDING")
                for m in accepted:
                    native_control = controls[m.control_id]
                    if (
                        native_control["effective_from"] > str(scope.period_start)
                        or native_control["recorded_on"] > str(scope.known_on)
                        or (
                            native_control["effective_to"]
                            and native_control["effective_to"] < str(scope.period_end)
                        )
                    ):
                        issues.append("NATIVE_CONTROL_PERIOD_GAP")
                        continue
                    impls = [
                        i
                        for i in assessment.implementations
                        if i.control_id == m.control_id and i.boundary_id == boundary
                    ]
                    for impl in impls:
                        owners.add(impl.owner_role_id)
                        if (
                            impl.state != "IMPLEMENTED"
                            or not reviewed(impl.review, scope.known_on)
                            or impl.effective_from > scope.period_start
                            or (impl.effective_to and impl.effective_to < scope.period_end)
                        ):
                            continue
                        implemented.add(impl.id)
                        for t in assessment.tests:
                            if (
                                t.requirement_id != r.id
                                or t.implementation_id != impl.id
                                or attribute.id not in t.attribute_ids
                            ):
                                continue
                            tested.append(t.id)
                            problems = test_issues(t, scope, evidence)
                            if problems:
                                issues.extend(problems)
                            else:
                                passing.append(t.id)
                if accepted and not implemented:
                    issues.append("IMPLEMENTATION_GAP")
                if implemented and not passing:
                    issues.append("EVIDENCE_OR_TEST_GAP")
                # A competing failure or invalid test remains visible. A later PASS cannot erase it.
                demonstrated = bool(passing) and not issues and not blockers and not excluded
                if demonstrated:
                    disposition = (
                        "DEMONSTRATED_SYNTHETIC"
                        if scope.origin == "SYNTHETIC"
                        else "SUPPORTED_BY_REVIEWED_RECORDS"
                    )
                elif attribute.kind != "CONTROL":
                    disposition = "ASSESSMENT_GAP"
                elif not candidates:
                    disposition = "NEW_CONTROL_OR_MAPPING_NEEDED"
                elif accepted and implemented:
                    disposition = "EVIDENCE_GAP"
                elif accepted:
                    disposition = "IMPLEMENT_CONTROL"
                else:
                    disposition = "REVIEW_OR_ENHANCE_CONTROL"
                attributes.append(
                    dict(
                        id=attribute.id,
                        objective=attribute.objective,
                        kind=attribute.kind,
                        evidence_expectation=attribute.evidence_expectation,
                        specification=attribute.specification,
                        disposition=disposition,
                        issues=sorted(set(issues)),
                        mapping_ids=sorted(m.id for m in candidates),
                        control_ids=sorted({m.control_id for m in candidates}),
                        implementation_ids=sorted(implemented),
                        owner_role_ids=sorted(owners),
                        test_ids=sorted(tested),
                        passing_test_ids=sorted(passing),
                    )
                )
            supported = all(
                x["disposition"] in {"DEMONSTRATED_SYNTHETIC", "SUPPORTED_BY_REVIEWED_RECORDS"}
                for x in attributes
            )
            status = (
                "EXCLUDED"
                if excluded
                else "SUPPORTED"
                if supported
                else "UNRESOLVED"
                if blockers
                else "GAP"
            )
            rows.append(
                dict(
                    requirement_id=r.id,
                    framework_id=r.framework_id,
                    category=r.category,
                    boundary_id=boundary,
                    summary=r.summary,
                    locator=r.locator,
                    source_id=r.source_id,
                    baseline=r.category in baseline.get(r.framework_id, set()),
                    status=status,
                    blockers=sorted(set(blockers)),
                    applicability_rationale=a.rationale if a else "No scoped disposition recorded",
                    candidate_reuse_from_baseline=sorted(
                        {m.control_id for m in mappings} & baseline_controls
                    ),
                    attributes=attributes,
                )
            )
    if not rows:
        raise ValueError("Selected assessment population is empty")
    return dict(
        schema_version="0.2.0",
        kind="CCF_SCOPED_DELTA",
        origin=scope.origin,
        native_snapshot_id=digest(native),
        catalog_digest=digest(data(catalog)),
        assessment_digest=digest(data(assessment)),
        scope=data(scope),
        framework_versions={k: frameworks[k].edition for k in sorted(selected)},
        source_hashes={
            s.id: s.content_sha256
            for s in catalog.sources
            if any(s.id in frameworks[k].source_ids for k in selected)
        },
        summary=dict(sorted(Counter(r["status"] for r in rows).items())),
        rows=rows,
        limitations=[
            "Planning/support record, not an external opinion or certification.",
            "Review identities are supplied records; this CLI does not authenticate reviewers.",
            "Candidate reuse is a catalog hint, not demonstrated requirement coverage.",
            "Unresolved source inventories cannot produce a complete framework delta.",
        ],
    )
