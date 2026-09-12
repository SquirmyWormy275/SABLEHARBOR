"""Original public synthetic acceptance fixture; no external requirement text or opinions."""

from enterprise.ccf.registry import digest

from .engine import data
from .models import Assessment, Catalog


def review():
    return dict(
        author="SYNTHETIC-PREPARER",
        reviewer="SYNTHETIC-REVIEWER",
        reviewed_on="2026-09-11",
        rationale="Independent review in a public synthetic exercise only",
    )


def bind_fixture_reviews(value):
    """Bind fictional review records in examples/tests; never used to approve real input."""
    if isinstance(value, list):
        return [bind_fixture_reviews(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {k: bind_fixture_reviews(v) for k, v in value.items()}
    subject = {k: v for k, v in result.items() if k not in {"review", "inventory_review"}}
    for key in ("review", "inventory_review"):
        if result.get(key):
            result[key]["subject_digest"] = digest(subject)
    return result


def example(native):
    controls = {r["id"]: r for r in native["records"] if r["kind"] == "control"}
    definitions = [
        ("SOC2", "ACCESS", "SH-IAM-004", "CONTROL", "IMPLEMENTED", "PASS", True),
        ("HIPAA", "ACCESS", "SH-IAM-004", "CONTROL", "IMPLEMENTED", "PASS", True),
        ("ISO27001", "ACCESS", "SH-IAM-004", "CONTROL", "IMPLEMENTED", None, True),
        ("ISO27001", "REVIEW", "SH-IAM-007", "CONTROL", "PROPOSED", None, True),
        ("ISO27001", "UNMAPPED", None, "CONTROL", None, None, False),
        ("ISO42001", "AI", "SH-AIM-001", "CONTROL", "PROPOSED", None, False),
        ("ISO42001", "AIMS", None, "ASSESSMENT", None, None, False),
        ("C5", "RESTORE", "SH-BCM-003", "CONTROL", "IMPLEMENTED", "FAIL", True),
    ]
    sources, frameworks, requirements, mappings, tests = [], [], [], [], []
    implementations, evidence, applicability = {}, {}, []
    for fid in dict.fromkeys(d[0] for d in definitions):
        sources.append(
            dict(
                id=f"EXAMPLE-{fid}",
                publisher="Sable Harbor synthetic exercise",
                edition="EXAMPLE-1 (not publisher criteria)",
                url="https://example.invalid/synthetic-ccf",
                retrieved_on="2026-09-11",
                effective_from="2026-01-01",
                access="SYNTHETIC",
                content_sha256=digest([d for d in definitions if d[0] == fid]),
                rights_note="Original fictional acceptance data; no normative framework source",
                review=review(),
            )
        )
        frameworks.append(
            dict(
                id=fid,
                title=f"{fid} synthetic adapter exercise",
                edition="EXAMPLE-1",
                source_ids=[f"EXAMPLE-{fid}"],
                categories=["EXAMPLE"],
                required_categories=["EXAMPLE"],
                expected_requirement_ids=[
                    f"{f}:EXAMPLE-{ref}" for f, ref, *_ in definitions if f == fid
                ],
                inventory_complete=True,
                inventory_review=review(),
                limitation="Synthetic adapter fixture; not actual framework coverage",
            )
        )
    for fid, ref, cid, kind, state, result, accepted in definitions:
        rid = f"{fid}:EXAMPLE-{ref}"
        requirements.append(
            dict(
                id=rid,
                framework_id=fid,
                source_id=f"EXAMPLE-{fid}",
                locator="Fictional acceptance requirement",
                category="EXAMPLE",
                summary=f"Synthetic {ref.lower()} acceptance case",
                attributes=[
                    dict(
                        id="A1",
                        objective=f"Demonstrate the synthetic {ref.lower()} objective",
                        kind=kind,
                        evidence_expectation="Scoped source records, population reconciliation and independently reviewed test",
                    )
                ],
                review=review(),
            )
        )
        applicability.append(
            dict(
                requirement_id=rid,
                boundary_id="corporate",
                disposition="APPLICABLE",
                rationale="Selected for synthetic acceptance exercise",
                review=review(),
            )
        )
        if not cid:
            continue
        mappings.append(
            dict(
                id=f"MAP-{fid}-{ref}",
                requirement_id=rid,
                control_id=cid,
                control_digest=digest(controls[cid]),
                attribute_ids=["A1"],
                rationale="Synthetic attribute support",
                uncovered="No inference to real external criteria",
                review=review() if accepted else None,
            )
        )
        iid = f"EXAMPLE-IMPL-{cid}"
        implementations[iid] = dict(
            id=iid,
            version="1",
            control_id=cid,
            control_digest=digest(controls[cid]),
            boundary_id="corporate",
            owner_role_id=controls[cid]["data"]["owner_role_id"],
            state=state,
            effective_from="2026-01-01",
            effective_to=None,
            review=review() if state == "IMPLEMENTED" else None,
        )
        if result:
            eid = f"EXAMPLE-EVIDENCE-{cid}"
            payload = dict(
                case="Synthetic source records only",
                control=cid,
                rows=[{"id": "CASE-1", "condition_met": result == "PASS"}],
            )
            population = digest(["CASE-1"])
            evidence[eid] = dict(
                id=eid,
                sha256=digest(payload),
                boundary_id="corporate",
                period_start="2026-09-02",
                period_end="2026-09-10",
                collected_on="2026-09-11",
                expires_on="2026-10-01",
                origin="SYNTHETIC",
                classification="PUBLIC",
                source_system="PUBLIC-SYNTHETIC-FIXTURE",
                extraction="Complete one-record illustrative population",
                population_digest=population,
                payload=payload,
            )
            tests.append(
                dict(
                    id=f"EXAMPLE-TEST-{fid}-{ref}",
                    requirement_id=rid,
                    attribute_ids=["A1"],
                    implementation_id=iid,
                    implementation_version="1",
                    boundary_id="corporate",
                    mode="OPERATING",
                    period_start="2026-09-02",
                    period_end="2026-09-10",
                    performed_on="2026-09-11",
                    evidence_ids=[eid],
                    expected_population_digest=population,
                    result=result,
                    procedure="Inspect the synthetic case condition and reconcile the complete expected population",
                    selection_rationale="Entire synthetic one-record population; not a representative operating sample",
                    findings=[] if result == "PASS" else ["Synthetic restore condition failed"],
                    review=review(),
                )
            )
    catalog = Catalog.model_validate(
        dict(
            schema_version="0.2.0",
            id="CCF-SYNTHETIC-ADAPTER-EXERCISE",
            version="1",
            native_snapshot_id=digest(native),
            sources=sources,
            frameworks=frameworks,
            requirements=requirements,
            mappings=mappings,
        )
    )

    catalog = Catalog.model_validate(bind_fixture_reviews(data(catalog)))

    def selection(fid):
        return dict(framework_id=fid, categories=["EXAMPLE"])

    assessment = Assessment.model_validate(
        dict(
            schema_version="0.2.0",
            catalog_digest=digest(data(catalog)),
            scope=dict(
                id="EXAMPLE-SCOPE",
                boundaries=["corporate"],
                baseline=[selection("SOC2"), selection("HIPAA")],
                targets=[selection("ISO27001"), selection("ISO42001"), selection("C5")],
                period_start="2026-09-02",
                period_end="2026-09-10",
                known_on="2026-09-11",
                assessment_mode="OPERATING",
                origin="SYNTHETIC",
                assumptions=[
                    "Fictional acceptance criteria; no external framework conformity or actual implementation asserted"
                ],
                review=review(),
            ),
            implementations=list(implementations.values()),
            evidence=list(evidence.values()),
            tests=tests,
            applicability=applicability,
        )
    )
    assessment = Assessment.model_validate(bind_fixture_reviews(data(assessment)))
    return catalog, assessment


def blank_assessment(catalog):
    """Reviewable real-framework scope proposal, deliberately unapproved and without evidence."""
    return Assessment.model_validate(
        dict(
            schema_version="0.2.0",
            catalog_digest=digest(data(catalog)),
            scope=dict(
                id="PROPOSED-SOC2-HIPAA-BASELINE",
                boundaries=["corporate"],
                baseline=[
                    dict(framework_id="SOC2", categories=["SECURITY"]),
                    dict(
                        framework_id="HIPAA",
                        categories=["GENERAL", "SECURITY", "PRIVACY", "BREACH"],
                    ),
                ],
                targets=[
                    dict(framework_id="ISO27001", categories=["ISMS", "ANNEX_A"]),
                    dict(framework_id="ISO42001", categories=["AIMS", "ANNEX_A"]),
                    dict(framework_id="C5", categories=["BASIC", "ADDITIONAL"]),
                ],
                period_start="2026-09-02",
                period_end="2026-09-10",
                known_on="2026-09-11",
                assessment_mode="OPERATING",
                origin="SYNTHETIC",
                assumptions=[
                    "Corporate is a placeholder development boundary, not an approved service/report scope",
                    "Dates are an illustrative exercise period, not the selected external examination period",
                    "HIPAA entity role and data flows are unresolved; source inventories are incomplete",
                ],
            ),
            implementations=[],
            evidence=[],
            tests=[],
            applicability=[],
        )
    )
