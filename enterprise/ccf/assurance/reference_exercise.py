"""Fictional multi-boundary workflow; never supplies reviews for the real catalog."""

from copy import deepcopy

from enterprise.ccf.registry import digest

from .engine import data, plan
from .examples import bind_fixture_reviews, review
from .models import Assessment, Catalog
from .reference import BOUNDARIES

DEFINITIONS = [
    ("SOC2", "ACCESS", "SH-IAM-004"),
    ("HIPAA", "ACCESS", "SH-IAM-004"),
    ("SOC2", "RESTORE", "SH-BCM-003"),
    ("HIPAA", "RESTORE", "SH-BCM-003"),
    ("C5", "RESTORE", "SH-BCM-003"),
    ("C5", "NOTICE", "SH-TPR-003"),
]


def exercise(native):
    """Return immutable-input stages and a finding ledger with explicit period limits."""
    controls = {r["id"]: r for r in native["records"] if r["kind"] == "control"}
    sources, frameworks, requirements, mappings = [], [], [], []
    for fid in ("SOC2", "HIPAA", "C5"):
        sid = "FICTIONAL-" + fid
        sources.append(
            dict(
                id=sid,
                publisher="Sable Harbor fictional workflow",
                edition="FICTIONAL-REFERENCE-1; not external criteria",
                url="https://example.invalid/reference-exercise",
                retrieved_on="2026-09-11",
                effective_from="2026-09-01",
                access="SYNTHETIC",
                content_sha256=digest(fid),
                rights_note="Original synthetic exercise, no publisher requirement content.",
                review=review(),
            )
        )
        frameworks.append(
            dict(
                id=fid,
                title=fid + " fictional workflow adapter",
                edition="FICTIONAL-1",
                source_ids=[sid],
                categories=["EXAMPLE"],
                required_categories=["EXAMPLE"],
                expected_requirement_ids=[
                    f"{f}:FICTIONAL-{ref}" for f, ref, _ in DEFINITIONS if f == fid
                ],
                inventory_complete=True,
                inventory_review=review(),
                limitation="Complete only for these invented exercise objectives, never framework completeness.",
            )
        )
    for fid, ref, cid in DEFINITIONS:
        rid = f"{fid}:FICTIONAL-{ref}"
        requirements.append(
            dict(
                id=rid,
                framework_id=fid,
                source_id="FICTIONAL-" + fid,
                locator="Invented workflow objective " + ref,
                category="EXAMPLE",
                summary="Fictional " + ref.lower() + " demonstration",
                attributes=[
                    dict(
                        id="A1",
                        objective=(
                            "Recover from a cold dependency start within the invented 30-minute objective"
                            if fid == "C5" and ref == "RESTORE"
                            else "Recover the normal restore path within the invented 30-minute objective"
                            if ref == "RESTORE"
                            else "Validate fictional " + ref.lower() + " condition for the boundary"
                        ),
                        kind="DOCUMENT" if ref == "NOTICE" else "CONTROL",
                        evidence_expectation="Fictional source population and separate scoped test",
                    )
                ],
                review=review(),
            )
        )
        mappings.append(
            dict(
                id="MAP-" + rid,
                requirement_id=rid,
                control_id=cid,
                control_digest=digest(controls[cid]),
                attribute_ids=["A1"],
                rationale="Fictional workflow routing only",
                uncovered="No conclusion about actual criteria.",
                review=review(),
            )
        )
    c = Catalog.model_validate(
        bind_fixture_reviews(
            dict(
                schema_version="0.2.0",
                id="FICTIONAL-RENO-BOISE-WORKFLOW",
                version="1",
                native_snapshot_id=digest(native),
                sources=sources,
                frameworks=frameworks,
                requirements=requirements,
                mappings=mappings,
            )
        )
    )

    c = Catalog.model_validate(bind_fixture_reviews(data(c)))

    def initial():
        return dict(
            schema_version="0.2.0",
            catalog_digest=digest(data(c)),
            scope=dict(
                id="FICTIONAL-RENO-BOISE",
                boundaries=BOUNDARIES,
                baseline=[dict(framework_id=f, categories=["EXAMPLE"]) for f in ("SOC2", "HIPAA")],
                targets=[],
                period_start="2026-09-09",
                period_end="2026-09-09",
                known_on="2026-09-11",
                assessment_mode="OPERATING",
                origin="SYNTHETIC",
                review=review(),
                assumptions=[
                    "All identities, operations, objectives, dates, records and reviews are fictional.",
                    "One-day invented populations demonstrate software behavior, not Type 2 readiness or sample sufficiency.",
                    "Shared corporate payloads require separate local scope validation; provider support is never automatic.",
                ],
            ),
            implementations=[],
            evidence=[],
            tests=[],
            applicability=[],
            disclosures=[],
        )

    a = initial()
    for b in BOUNDARIES:
        for cid in sorted({x[2] for x in DEFINITIONS}):
            a["implementations"].append(
                dict(
                    id=f"IMPL-{b}-{cid}",
                    version="1",
                    control_id=cid,
                    control_digest=digest(controls[cid]),
                    boundary_id=b,
                    owner_role_id=controls[cid]["data"]["owner_role_id"],
                    state="PROPOSED" if cid == "SH-TPR-003" else "IMPLEMENTED",
                    effective_from="2026-09-01",
                    effective_to=None,
                    review=None if cid == "SH-TPR-003" else review(),
                )
            )
        for fid, ref, _ in DEFINITIONS:
            a["applicability"].append(
                dict(
                    requirement_id=f"{fid}:FICTIONAL-{ref}",
                    boundary_id=b,
                    disposition="APPLICABLE",
                    rationale="Invented exercise scope only",
                    review=review(),
                )
            )

    def add_test(target, fid, ref, cid, b, result="PASS", suffix="", date="2026-09-09", iid=None):
        # SOC/HIPAA share one scoped artifact, but receive distinct requirement tests.
        scenario = "COLD-DEPENDENCY" if fid == "C5" and ref == "RESTORE" else "NORMAL"
        eid = f"EVIDENCE-{b}-{ref}-{scenario}-{date}{suffix}"
        ids = [f"{ref}-{scenario}-CASE-1-{date}"]
        pop = digest(ids)
        shared = dict(id="CORPORATE-LEAVER-1", disabled=True, date=date)
        payload = dict(
            origin="FICTIONAL",
            scenario=scenario,
            rows=[dict(id=ids[0], condition_met=result == "PASS")],
            shared_corporate_record=shared if ref == "ACCESS" else None,
            shared_corporate_sha256=digest(shared) if ref == "ACCESS" else None,
            local_validation=dict(
                boundary=b,
                checked_connected_accounts=ref == "ACCESS",
                restore_minutes=(25 if result == "PASS" else 90) if ref == "RESTORE" else None,
                invented_target_minutes=30 if ref == "RESTORE" else None,
            )
            if ref in {"ACCESS", "RESTORE"}
            else dict(boundary=b, notice_delivered=True),
        )
        if not any(e["id"] == eid for e in target["evidence"]):
            target["evidence"].append(
                dict(
                    id=eid,
                    sha256=digest(payload),
                    boundary_id=b,
                    period_start=date,
                    period_end=date,
                    collected_on="2026-09-11",
                    expires_on="2026-10-01",
                    origin="SYNTHETIC",
                    classification="PUBLIC",
                    source_system="FICTIONAL-SOURCE",
                    extraction="Entire invented one-record population with boundary validation",
                    population_digest=pop,
                    payload=payload,
                )
            )
        target["tests"].append(
            dict(
                id=f"TEST-{fid}-{ref}-{b}-{date}{suffix}",
                requirement_id=f"{fid}:FICTIONAL-{ref}",
                attribute_ids=["A1"],
                implementation_id=iid or f"IMPL-{b}-{cid}",
                implementation_version="2" if iid else "1",
                boundary_id=b,
                mode="OPERATING",
                period_start=date,
                period_end=date,
                performed_on="2026-09-11",
                evidence_ids=[eid],
                expected_population_digest=pop,
                result=result,
                procedure="Reconcile the entire invented population and inspect the condition and local boundary validation.",
                selection_rationale="All one-record fictional cases; not an assurance sampling recommendation.",
                findings=[]
                if result == "PASS"
                else ["FINDING-BOISE-RESTORE: 90 minutes exceeds fictional 30-minute objective."],
                review=review(),
            )
        )

    stages = []

    def save(name, value):
        assessed = Assessment.model_validate(bind_fixture_reviews(deepcopy(value)))
        assessed = Assessment.model_validate(bind_fixture_reviews(data(assessed)))
        stages.append((name, c, assessed, plan(c, assessed, native)))

    for fid, ref, cid in DEFINITIONS[:4]:
        for b in BOUNDARIES:
            add_test(a, fid, ref, cid, b)
    save("01-baseline", a)
    a["scope"]["targets"] = [dict(framework_id="C5", categories=["EXAMPLE"])]
    save("02-c5-delta", a)
    for i in a["implementations"]:
        if i["control_id"] == "SH-TPR-003":
            i.update(state="IMPLEMENTED", review=review())
    for fid, ref, cid in DEFINITIONS[4:]:
        for b in BOUNDARIES:
            add_test(
                a,
                fid,
                ref,
                cid,
                b,
                "FAIL" if ref == "RESTORE" and b == BOUNDARIES[2] else "PASS",
                suffix="-C5",
            )
    save("03-failed-test", a)
    add_test(a, "C5", "RESTORE", "SH-BCM-003", BOUNDARIES[2], suffix="-RETEST")
    save("04-same-period-retest", a)
    # Preserve the old failure and old version in the prospective assessment as well as history.
    next_a = deepcopy(a)
    next_a["scope"].update(
        id="FICTIONAL-RENO-BOISE-PROSPECTIVE", period_start="2026-09-10", period_end="2026-09-10"
    )
    next_a["scope"]["assumptions"].append(
        "Prospective one-day demonstration only; September 9 failure remains a historical finding and is not rewritten as passing."
    )
    old_id = f"IMPL-{BOUNDARIES[2]}-SH-BCM-003"
    old = next(i for i in next_a["implementations"] if i["id"] == old_id)
    old["effective_to"] = "2026-09-09"
    new = deepcopy(old)
    new.update(id=old_id + "-V2", version="2", effective_from="2026-09-10", effective_to=None)
    next_a["implementations"].append(new)
    next_a["tests"] = [t for t in next_a["tests"] if t["result"] == "FAIL"]
    retained = {e for t in next_a["tests"] for e in t["evidence_ids"]}
    next_a["evidence"] = [e for e in next_a["evidence"] if e["id"] in retained]
    for fid, ref, cid in DEFINITIONS:
        for b in BOUNDARIES:
            add_test(
                next_a,
                fid,
                ref,
                cid,
                b,
                date="2026-09-10",
                iid=new["id"] if b == BOUNDARIES[2] and cid == "SH-BCM-003" else None,
            )
    save("05-prospective-validation", next_a)
    ledger = dict(
        id="FINDING-BOISE-RESTORE",
        origin="FICTIONAL",
        state="CORRECTIVE_ACTION_VALIDATED_IN_LATER_PERIOD",
        original_failure="03-failed-test",
        same_period_result="04-same-period-retest remains GAP",
        cause="Invented recovery runbook omitted a dependency startup step.",
        corrective_action="Fictional version 2 adds dependency sequencing and validation.",
        prospective_validation="05-prospective-validation",
        limitation="The earlier period remains failed. A prospective PASS neither erases history nor proves operating effectiveness for a longer examination period.",
    )
    return stages, ledger
